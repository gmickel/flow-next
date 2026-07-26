"""The injected request executor (fn-139.2).

This is the seam. Adapters call `execute(request)` and nothing else - no
`subprocess.run`, no sockets - which is what makes the whole suite testable
with an in-process fake instead of a live tracker.

It owns four things adapters must not: credential attachment (after the adapter
boundary), bounded retry, redirect safety, and turning any transport-native
explosion into a `TrackerError`.
"""

from __future__ import annotations

import json
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from typing import Callable, Optional, Protocol, Union
from urllib.parse import urlparse

from .classify import classify, malformed_body
from .credentials import Credential, redact, resolve
from .types import (BACKOFF_CAP_S, CONCURRENCY_CAP, MAX_RETRIES, CredentialPolicy,
                    ErrorClass, Request, Response, TrackerError)

Result = Union[Response, TrackerError]

#: The cap is enforced HERE, at the shared boundary, because a module constant
#: that nothing acquires is documentation, not a bound. Adapters get bounded
#: concurrency by construction rather than by remembering to ask for it.
_SLOTS = threading.BoundedSemaphore(CONCURRENCY_CAP)


def concurrency_slots_available() -> int:
    """Test seam: how many transports may still start."""
    return _SLOTS._value  # noqa: SLF001 - deliberate introspection for tests


class Executor(Protocol):
    def __call__(self, request: Request) -> Result: ...


def _sleep_backoff(attempt: int, retry_after: Optional[float]) -> None:
    delay = retry_after if retry_after is not None else min(2.0 ** attempt, BACKOFF_CAP_S)
    time.sleep(min(delay, BACKOFF_CAP_S))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect while holding a credential.

    A cross-host redirect carrying an Authorization header hands the secret to
    whatever host the first one names. Rather than try to decide which hops are
    safe, the executor refuses to follow any redirect implicitly and surfaces it.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        raise _Redirect(newurl)


class _Redirect(Exception):
    def __init__(self, url: str) -> None:
        super().__init__(url)
        self.url = url


def _attach(req: Request, headers: dict[str, str], cred: Optional[Credential]) -> None:
    if req.credential_policy is CredentialPolicy.PROVIDER_AUTH and cred is not None:
        cred.attach(headers)
    # PRESIGNED_ANONYMOUS and NONE attach nothing. This is the branch that keeps
    # the Linear API key off a third-party presigned asset host.


def _http(req: Request, cred: Optional[Credential], verify_tls: bool) -> Result:
    headers = dict(req.headers)
    _attach(req, headers, cred)
    started = time.monotonic()
    handlers: list = [_NoRedirect]
    if not verify_tls:
        import ssl

        # `OpenerDirector.open()` takes no `context` kwarg - it must be installed
        # on an HTTPSHandler. Passing it to open() raises TypeError, which is
        # exactly how the opt-out was broken.
        handlers.append(urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))  # noqa: S323
    try:
        # Request construction is INSIDE the try: a malformed persisted URL or a
        # non-str target raises here, and the contract says this function returns
        # a TrackerError rather than letting an exception escape.
        opener = urllib.request.build_opener(*handlers)
        r = urllib.request.Request(req.url_or_argv, data=req.body, headers=headers,
                                   method=req.method)
        with opener.open(r, timeout=req.timeout_s) as resp:
            return Response(resp.status, dict(resp.headers), resp.read(), time.monotonic() - started)
    except _Redirect as exc:
        same_host = urlparse(exc.url).netloc == urlparse(req.url_or_argv).netloc
        return TrackerError(
            ErrorClass.TRANSPORT,
            f"refused to follow {'same' if same_host else 'cross'}-host redirect while authenticated",
            subtype="redirect", auto_retryable=False, details={"location": exc.url},
        )
    except urllib.error.HTTPError as exc:
        return Response(exc.code, dict(exc.headers or {}), exc.read() or b"", time.monotonic() - started)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return TrackerError(ErrorClass.TRANSPORT, redact(str(exc)), subtype="timeout",
                            auto_retryable=True)
    except (ValueError, TypeError) as exc:
        return TrackerError(ErrorClass.INVALID_INPUT, redact(f"bad request target: {exc}"),
                            subtype="construction")


#: `gh`/`glab` surface the upstream status in their diagnostics ("HTTP 401",
#: "status code 429"). Without this the CLI route cannot be classified at all.
_CLI_STATUS_RE = re.compile(rb"(?:HTTP|status(?:\s+code)?)[^0-9]{0,8}([1-5][0-9]{2})", re.I)


def _cli(req: Request, verify_tls: bool) -> Result:
    """CLI route. `timeout_s` is a TOTAL process deadline here - `gh`/`glab`
    expose no timeout flag of their own."""
    if not verify_tls:
        # gh/glab expose no TLS-verification flag. Silently ignoring the opt-out
        # would claim a guarantee the route cannot honour.
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"sslVerify=false is not supported on the {req.provider} CLI route; "
            "use the HTTP route or restore TLS verification",
            subtype="tls_unsupported",
        )
    started = time.monotonic()
    try:
        # No shell. Body goes on stdin, never argv, so a body containing shell
        # metacharacters or a very long payload cannot become an argument.
        proc = subprocess.run(  # noqa: S603 - argv list, shell=False
            list(req.url_or_argv), input=req.body, capture_output=True,
            timeout=req.timeout_s, check=False,
        )
    except subprocess.TimeoutExpired:
        return TrackerError(ErrorClass.TRANSPORT, "CLI process deadline exceeded",
                            subtype="timeout", auto_retryable=True)
    except (OSError, ValueError) as exc:
        return TrackerError(ErrorClass.TRANSPORT, redact(str(exc)), subtype="spawn",
                            auto_retryable=False)
    elapsed = time.monotonic() - started
    # `glab` prints its "Multiple config files found" warning to STDOUT, which
    # corrupts JSON parsing (measured). Strip leading non-JSON noise.
    out = proc.stdout or b""
    if req.provider == "gitlab":
        idx = min((i for i in (out.find(b"{"), out.find(b"[")) if i != -1), default=-1)
        if idx > 0:
            out = out[idx:]
    if proc.returncode == 0:
        return Response(200, {}, out, elapsed)
    # A non-zero exit collapsed to a synthetic 400 made every CLI failure
    # `invalid_input` and left the classifier's auth / rate-limit / licence /
    # 5xx branches unreachable on the ordinary CLI route. `gh` and `glab` both
    # print the upstream status, so extract it and classify on the real thing.
    diag = (proc.stderr or b"") + b"\n" + (proc.stdout or b"")
    m = _CLI_STATUS_RE.search(diag)
    status = int(m.group(1)) if m else 400
    return Response(status, {}, diag.strip() or b"", elapsed)


def execute(
    request: Request,
    *,
    auth_scheme: Optional[str] = None,
    verify_tls: bool = True,
    on_event: Optional[Callable[[str], None]] = None,
) -> Result:
    """Run one request. Returns `Response | TrackerError` - never raises."""
    cred = resolve(request.provider, auth_scheme=auth_scheme)
    is_cli = isinstance(request.url_or_argv, (list, tuple))
    if not verify_tls and on_event:
        # sslVerify=false is honoured but never silent.
        on_event(f"tls-verification-disabled provider={request.provider} op={request.op}")

    attempt = 0
    while True:
        with _SLOTS:
            raw = _cli(request, verify_tls) if is_cli else _http(request, cred, verify_tls)
        if isinstance(raw, TrackerError):
            err = raw
        else:
            err = classify(request.provider, raw)
            if err is None:
                return raw
        # Retry ONLY when the class says rate-limited AND the caller declared the
        # request idempotent. Replaying a non-idempotent write is how duplicates
        # get created - and no tracker dedups on create (measured).
        retryable = err.auto_retryable and err.cls is ErrorClass.RATE_LIMITED and request.idempotent
        if not retryable or attempt >= MAX_RETRIES:
            return err
        if on_event:
            on_event(f"retry attempt={attempt + 1}/{MAX_RETRIES} class={err.cls.value} op={request.op}")
        _sleep_backoff(attempt, err.retry_after_s)
        attempt += 1
