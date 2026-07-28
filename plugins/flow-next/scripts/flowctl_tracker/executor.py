"""The injected request executor (fn-139.2).

This is the seam. Adapters call `execute(request)` and nothing else - no
`subprocess.run`, no sockets - which is what makes the whole suite testable
with an in-process fake instead of a live tracker.

It owns four things adapters must not: credential attachment (after the adapter
boundary), bounded retry, redirect safety, and turning any transport-native
explosion into a `TrackerError`.
"""

from __future__ import annotations

import http.client
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from typing import Callable, Optional, Protocol, Union
from urllib.parse import urlparse

from .classify import classify
from .credentials import Credential, redact, resolve
from .types import (BACKOFF_CAP_S, CONCURRENCY_CAP, MAX_RETRIES, CredentialPolicy,
                    ErrorClass, Request, Response, TrackerError)

Result = Union[Response, TrackerError]

#: The cap is enforced HERE, at the shared boundary, because a module constant
#: that nothing acquires is documentation, not a bound. Adapters get bounded
#: concurrency by construction rather than by remembering to ask for it.
#: Config-overridable (fn-139 R7: "defaults, config-overridable"): one
#: semaphore per distinct cap, created on first use and shared process-wide.
_SLOTS = threading.BoundedSemaphore(CONCURRENCY_CAP)
_SLOTS_BY_CAP = {CONCURRENCY_CAP: _SLOTS}
_SLOTS_LOCK = threading.Lock()


def _slots_for(cap: Optional[int]) -> threading.BoundedSemaphore:
    if not isinstance(cap, int) or cap < 1 or cap == CONCURRENCY_CAP:
        return _SLOTS
    with _SLOTS_LOCK:
        if cap not in _SLOTS_BY_CAP:
            _SLOTS_BY_CAP[cap] = threading.BoundedSemaphore(cap)
        return _SLOTS_BY_CAP[cap]


def concurrency_slots_available() -> int:
    """Test seam: how many transports may still start."""
    return _SLOTS._value  # noqa: SLF001 - deliberate introspection for tests


class Executor(Protocol):
    def __call__(self, request: Request) -> Result: ...


def _backoff_delay(attempt: int, retry_after: Optional[float],
                   cap_s: float = BACKOFF_CAP_S) -> float:
    """Server-supplied hints are untrusted input.

    `Retry-After: -1` reached `time.sleep(-1)` and raised ValueError - another
    breach of "never raises", caused by a hostile-or-broken header rather than
    by our own code. Pure so the ACTUAL delay can be emitted before sleeping.
    """
    delay: Optional[float] = None
    if retry_after is not None:
        try:
            candidate = float(retry_after)
        except (TypeError, ValueError):
            candidate = float("nan")
        # `candidate == candidate` is the NaN test, not a typo.
        if candidate == candidate and candidate >= 0 and candidate != float("inf"):  # noqa: PLR0124
            delay = candidate
    if delay is None:
        delay = min(2.0 ** attempt, cap_s)
    return max(0.0, min(delay, cap_s))


def _origin(url: str) -> tuple[str, str, int]:
    u = urlparse(url)
    default_port = 443 if u.scheme == "https" else 80
    return (u.scheme, (u.hostname or "").lower(), u.port or default_port)


class _GuardedRedirect(urllib.request.HTTPRedirectHandler):
    """Follow redirects, but never carry a credential to a NEW host.

    Refusing every redirect was too blunt: presigned uploads and CDN-backed
    asset fetches legitimately redirect, and an anonymous request has no secret
    to protect. The rule is about credentials, not about redirects:

      * no credential attached -> follow normally
      * same host              -> follow, credential may stay
      * cross host WITH a credential -> strip it before following
    """

    def __init__(self, authenticated: bool) -> None:
        super().__init__()
        self._authenticated = authenticated

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is None:
            return None
        # Compare ORIGIN (scheme + host + port), not just host: an HTTPS->HTTP
        # downgrade on the same host would otherwise carry the token in clear.
        if self._authenticated and _origin(newurl) != _origin(req.full_url):
            for h in list(new.headers):
                if h.lower() in {"authorization", "private-token", "x-api-key"}:
                    del new.headers[h]
        return new


def _read_body(resp) -> bytes:
    """Single guarded reader. `.read()` can raise after the status line."""
    data = resp.read()
    return data if data is not None else b""


def _attach(req: Request, headers: dict[str, str], cred: Optional[Credential]) -> None:
    if req.credential_policy is CredentialPolicy.PROVIDER_AUTH and cred is not None:
        cred.attach(headers)
    # PRESIGNED_ANONYMOUS and NONE attach nothing. This is the branch that keeps
    # the Linear API key off a third-party presigned asset host.


def _http(req: Request, cred: Optional[Credential], verify_tls: bool) -> Result:
    headers = dict(req.headers)
    _attach(req, headers, cred)
    started = time.monotonic()
    authenticated = (req.credential_policy is CredentialPolicy.PROVIDER_AUTH
                     and cred is not None)
    handlers: list = [_GuardedRedirect(authenticated)]
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
            return Response(resp.status, dict(resp.headers), _read_body(resp),
                            time.monotonic() - started)
    except urllib.error.HTTPError as exc:
        # Reading the ERROR body can itself raise IncompleteRead, and doing it
        # inside this handler put it beyond the reach of the sibling handlers.
        # One guarded reader serves both the success and error paths.
        try:
            body = _read_body(exc)
        except (http.client.HTTPException, TimeoutError, OSError) as read_exc:
            # A sibling `except` cannot catch what is raised INSIDE this handler,
            # so a socket timeout while reading the error body escaped entirely.
            return TrackerError(ErrorClass.TRANSPORT,
                                redact(f"incomplete error body: {read_exc}"),
                                subtype="read", auto_retryable=True)
        return Response(exc.code, dict(exc.headers or {}), body, time.monotonic() - started)
    except http.client.HTTPException as exc:
        # `resp.read()` can raise IncompleteRead / HTTPException AFTER the status
        # line is parsed. Uncaught, these broke the "never raises" contract.
        return TrackerError(ErrorClass.TRANSPORT, redact(f"incomplete response: {exc}"),
                            subtype="read", auto_retryable=True)
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
    except (OSError, ValueError, TypeError) as exc:
        # subprocess.run raises TypeError for a non-str argv element or a
        # non-bytes body (e.g. ["gh", None]) - not OSError.
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


#: Operations that MUST NOT use the CLI route, per provider. `glab api -F file=@`
#: produces invalid multipart (measured), so GitLab uploads have no permitted CLI
#: path - documenting that was not enough, because nothing stopped an adapter
#: from passing argv anyway.
_CLI_FORBIDDEN = {("gitlab", "upload")}


def _validate_route(req: Request) -> Optional[TrackerError]:
    is_cli = isinstance(req.url_or_argv, (list, tuple))
    if is_cli and (req.provider, req.op) in _CLI_FORBIDDEN:
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"{req.provider} '{req.op}' must use the HTTP route; the CLI form is "
            "known-broken (glab api -F produces invalid multipart)",
            subtype="forbidden_route",
        )
    return None


def execute(
    request: Request,
    *,
    auth_scheme: Optional[str] = None,
    verify_tls: bool = True,
    on_event: Optional[Callable[[str], None]] = None,
    max_retries: Optional[int] = None,
    backoff_cap_s: Optional[float] = None,
    concurrency: Optional[int] = None,
) -> Result:
    """Run one request. Returns `Response | TrackerError` - never raises.

    `max_retries` / `backoff_cap_s` / `concurrency` are the R7 bounds -
    config-overridable by the caller, defaulting to the module constants.
    Overrides are validated and CLAMPED (never raised past the defaults'
    spirit): a hostile/typo'd config must not unbound the executor.
    """
    route_err = _validate_route(request)
    if route_err is not None:
        return route_err
    try:
        # urlparse raises on malformed input (e.g. "http://[::1" - unterminated
        # IPv6), and this ran outside the guarded path, so it escaped execute().
        dest_host = (urlparse(request.url_or_argv).hostname
                     if isinstance(request.url_or_argv, str) else None)
    except ValueError as exc:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            redact(f"malformed request target: {exc}"),
                            subtype="construction")
    is_cli = isinstance(request.url_or_argv, (list, tuple))
    cred: Optional[Credential] = None
    if not is_cli:
        # HTTP route only. `_cli` never consumes the credential - gh/glab carry
        # their own auth - so resolving here anyway meant a garbage GITLAB_TOKEN
        # in the environment failed a glab CLI call with auth/resolve even
        # though the call would have succeeded. Unused state must not gate.
        try:
            # A corrupt glab config or an unreadable credential source must not
            # escape either - this sits outside every other guard.
            cred = resolve(request.provider, auth_scheme=auth_scheme, host=dest_host)
        except Exception as exc:  # noqa: BLE001 - boundary: nothing may escape execute()
            return TrackerError(ErrorClass.AUTH, redact(f"credential resolution failed: {exc}"),
                                subtype="resolve")
    if not verify_tls:
        # "Honoured but never silent" cannot depend on the caller happening to
        # pass a sink - with the default API (no on_event) the downgrade was
        # completely silent. Fail closed instead: an unrecordable downgrade is
        # refused rather than performed quietly.
        if on_event is None:
            return TrackerError(
                ErrorClass.INVALID_INPUT,
                "sslVerify=false requires an event sink so the downgrade is recorded; "
                "refusing to disable TLS verification silently",
                subtype="tls_unrecorded",
            )
        # Reject the unsupportable route BEFORE announcing a downgrade. Emitting
        # first made the audit stream claim TLS verification was disabled on a
        # request that was then refused and never sent - a false entry in the one
        # record that exists to prove when verification was actually off.
        if is_cli:
            return TrackerError(
                ErrorClass.INVALID_INPUT,
                f"sslVerify=false is not supported on the {request.provider} CLI route; "
                "use the HTTP route or restore TLS verification",
                subtype="tls_unsupported",
            )
        # The sink is caller-supplied and can itself raise. A sink that fails AT
        # RECORD TIME is exactly as unrecordable as a missing one, so the same
        # rule applies: refuse rather than downgrade with no record. Letting the
        # exception escape would also break the "never raises" contract.
        try:
            on_event(f"tls-verification-disabled provider={request.provider} op={request.op}")
        except Exception as exc:  # noqa: BLE001 - boundary: nothing may escape execute()
            return TrackerError(
                ErrorClass.INVALID_INPUT,
                redact(f"event sink failed while recording the TLS downgrade: {exc}; "
                       "refusing to disable TLS verification unrecorded"),
                subtype="tls_unrecorded",
            )

    retries_cap = MAX_RETRIES
    if isinstance(max_retries, int) and 0 <= max_retries <= 5:
        retries_cap = max_retries
    backoff_cap = BACKOFF_CAP_S
    if isinstance(backoff_cap_s, (int, float)) and 0 < backoff_cap_s <= 300:
        backoff_cap = float(backoff_cap_s)
    slots = _slots_for(concurrency)

    attempt = 0
    while True:
        if on_event:
            try:
                on_event(f"attempt {attempt + 1} provider={request.provider} "
                         f"op={request.op} route={'cli' if is_cli else 'http'}")
            except Exception:  # noqa: BLE001, S110 - diagnostics only
                pass
        with slots:
            raw = _cli(request, verify_tls) if is_cli else _http(request, cred, verify_tls)
        if isinstance(raw, TrackerError):
            err = raw
        else:
            err = classify(request.provider, raw, op=request.op)
            if err is None:
                return raw
        # Retry ONLY when the class says rate-limited AND the caller declared the
        # request idempotent. Replaying a non-idempotent write is how duplicates
        # get created - and no tracker dedups on create (measured).
        retryable = err.auto_retryable and err.cls is ErrorClass.RATE_LIMITED and request.idempotent
        if not retryable or attempt >= retries_cap:
            return err
        delay = _backoff_delay(attempt, err.retry_after_s, backoff_cap)
        if on_event:
            # Best-effort, unlike the downgrade record above: the retry event is
            # diagnostics, not the audit line a security property depends on.
            # The ACTUAL delay is emitted, not the server's untrusted hint.
            try:
                on_event(f"retry attempt={attempt + 1}/{retries_cap} "
                         f"class={err.cls.value} op={request.op} backoff_s={delay:.2f}")
            except Exception:  # noqa: BLE001, S110 - never raises; diagnostics only
                pass
        time.sleep(delay)
        attempt += 1
