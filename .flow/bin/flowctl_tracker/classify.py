"""Per-provider response classification (fn-139.2).

`401/403 = auth` is NOT sufficient, which is the whole reason this is a table
and not a global rule:

  * GitLab returns **403 for two unrelated things** - a bad token, and a
    licence-gated feature (`is_blocked_by` on Free returns
    "Blocked issues not available for current license"). One is `auth`, the
    other is `capability`, and degrading the wrong one silently is how a Free
    repo ends up looking unauthenticated.
  * Linear reports **rate limiting as a GraphQL error over HTTP 200/400**, not
    429, so a status-code-only classifier never sees it.

Every provider table is total: anything unmatched falls through
`_fallback`, so no response is ever left unclassified.
"""

from __future__ import annotations

import json
import re
import time
from typing import Optional

from .credentials import redact
from .types import ErrorClass, Response, TrackerError

_LICENCE_RE = re.compile(rb"not available for current license", re.I)


def _fallback(resp: Response) -> TrackerError:
    """Total rule. Retryability follows the SUBTYPE, not the class."""
    if resp.status >= 500:
        return TrackerError(ErrorClass.TRANSPORT, f"server error {resp.status}",
                            subtype="5xx", auto_retryable=True)
    if resp.status in (401, 403):
        return TrackerError(ErrorClass.AUTH, f"unauthorized ({resp.status})", subtype="http")
    if resp.status == 404:
        return TrackerError(ErrorClass.NOT_FOUND, "not found", subtype="http")
    if resp.status == 429:
        return TrackerError(ErrorClass.RATE_LIMITED, "rate limited", subtype="http",
                            retry_after_s=_retry_after(resp), auto_retryable=True)
    if 400 <= resp.status < 500:
        return TrackerError(ErrorClass.INVALID_INPUT, f"rejected ({resp.status})", subtype="http")
    return TrackerError(ErrorClass.TRANSPORT, f"unexpected status {resp.status}",
                        subtype="unknown")


def _retry_after(resp: Response) -> Optional[float]:
    v = resp.headers.get("retry-after") or resp.headers.get("Retry-After")
    try:
        return float(v) if v else None
    except (TypeError, ValueError):
        return None


_LINEAR_BUCKETS = ("requests", "endpoint-requests", "complexity")


def _linear_retry_after(resp: Response) -> Optional[float]:
    """Linear never sends `Retry-After`; it sends per-bucket reset timestamps.

    Three independent buckets can exhaust (`requests`, `endpoint-requests`, and
    the complexity budget), each with its own `x-ratelimit-<bucket>-remaining` /
    `-reset` pair, where reset is **epoch milliseconds**. Falling back to the
    fixed 1s/2s ladder meant every retry landed inside the same limit window and
    burned the whole budget without ever waiting long enough to clear it.

    Only an EXHAUSTED bucket constrains us, and the buckets are INDEPENDENT: the
    request is blocked until the LAST of them clears, so the delay is `max`, not
    `min`. Taking the soonest reset retried while a slower bucket was still
    limiting - burning the retry budget inside one window, which is the exact
    failure the header parsing was added to prevent. `_sleep_backoff` still clamps.
    """
    lowered = {str(k).lower(): v for k, v in (resp.headers or {}).items()}
    waits: list[float] = []
    now = time.time()
    for bucket in _LINEAR_BUCKETS:
        try:
            remaining = float(lowered[f"x-ratelimit-{bucket}-remaining"])
            reset_ms = float(lowered[f"x-ratelimit-{bucket}-reset"])
        except (KeyError, TypeError, ValueError):
            continue
        if remaining > 0:
            continue
        # `reset_ms != reset_ms` is the NaN test, not a typo.
        if reset_ms != reset_ms or reset_ms in (float("inf"), float("-inf")):  # noqa: PLR0124
            continue
        waits.append(max(0.0, reset_ms / 1000.0 - now))
    if waits:
        return max(waits)
    return _retry_after(resp)


class _Malformed(Exception):
    """The body is not a GraphQL document we can reason about."""


def _graphql_errors(resp: Response) -> Optional[list[dict]]:
    """GraphQL puts failures in a 200/400 body; the executor normalizes here.

    Raises `_Malformed` rather than returning None for unparseable input:
    returning None made invalid JSON over HTTP 200 look like SUCCESS, and a
    non-dict entry in `errors` (e.g. `{"errors":["bad"]}`) raised AttributeError
    out of the classifier.
    """
    try:
        payload = json.loads(resp.body or b"{}")
    except (ValueError, TypeError) as exc:
        raise _Malformed(str(exc)) from exc
    if not isinstance(payload, dict):
        raise _Malformed("GraphQL payload is not an object")
    errs = payload.get("errors")
    if errs is None:
        return None
    if not isinstance(errs, list) or not all(isinstance(e, dict) for e in errs):
        raise _Malformed("GraphQL 'errors' is not a list of objects")
    for e in errs:
        ext = e.get("extensions")
        # `extensions` is server-controlled and may be any JSON value. Assuming
        # dict raised AttributeError on `{"extensions": ["bad"]}`.
        if ext is not None and not isinstance(ext, dict):
            raise _Malformed("GraphQL 'extensions' is not an object")
    return errs or None


#: Ops whose 2xx body is raw bytes, not an API document. The Linear rule
#: parses every 2xx body as GraphQL, which misclassified a binary asset
#: download from uploads.linear.app as transport/malformed_body (measured
#: live 2026-07-28). These ops classify on status alone.
_RAW_BODY_OPS = frozenset({"wire-attach-get"})


def classify(provider: str, resp: Response,
             op: Optional[str] = None) -> Optional[TrackerError]:
    """None means success. Otherwise a normalized, classified failure."""
    if op in _RAW_BODY_OPS:
        return _generic(resp)
    fn = _TABLE.get(provider, _generic)
    return fn(resp)


def _generic(resp: Response) -> Optional[TrackerError]:
    if 200 <= resp.status < 300:
        return None
    return _fallback(resp)


def _gitlab(resp: Response) -> Optional[TrackerError]:
    # MEASURED: a licence gate and a bad token both surface as 403. The body is
    # the only discriminator, so it is read before the status rule applies.
    if resp.status == 403 and _LICENCE_RE.search(resp.body or b""):
        return TrackerError(
            ErrorClass.CAPABILITY, "feature not available on this GitLab tier",
            subtype="licence", details={"capability": "blockedBy", "required_plan": "premium"},
        )
    return _generic(resp)


def _linear(resp: Response) -> Optional[TrackerError]:
    # STATUS FIRST for the codes GraphQL never owns. Parsing the body first meant
    # an HTTP 500 carrying {"errors":[...]} classified as invalid_input instead of
    # transport, and a 401 with a GraphQL-shaped body lost its auth class - the
    # total fallback was being bypassed by the body parse.
    if resp.status in (401, 403, 429) or resp.status >= 500:
        return _fallback(resp)
    try:
        errs = _graphql_errors(resp)
    except _Malformed as exc:
        return malformed_body(str(exc))
    if errs:
        # STRUCTURED CODES FIRST. `linear-graphql.md` documents
        # `errors[].extensions.code` of RATELIMITED (over HTTP 400, not 429) and
        # AUTHENTICATION_ERROR. Message-text heuristics miss both whenever the
        # message is generic, which silently demotes them to invalid_input.
        codes = {str((e.get("extensions") or {}).get("code", "")).upper() for e in errs}
        if "RATELIMITED" in codes:
            return TrackerError(ErrorClass.RATE_LIMITED, "linear rate limit (RATELIMITED)",
                                subtype="graphql_code", retry_after_s=_linear_retry_after(resp),
                                auto_retryable=True)
        if "AUTHENTICATION_ERROR" in codes:
            return TrackerError(ErrorClass.AUTH, "linear authentication failed",
                                subtype="graphql_code")
        joined = " ".join(str(e.get("message", "")) for e in errs).lower()
        # MEASURED: Linear rate-limits via a GraphQL error, often over HTTP 200,
        # and is complexity-based rather than request-count based.
        if "rate limit" in joined or "complexity" in joined:
            return TrackerError(ErrorClass.RATE_LIMITED, "linear rate limit",
                                subtype="graphql", retry_after_s=_linear_retry_after(resp),
                                auto_retryable=True)
        if "authentication" in joined or "unauthorized" in joined:
            return TrackerError(ErrorClass.AUTH, "linear authentication failed",
                                subtype="graphql")
        if "not found" in joined:
            return TrackerError(ErrorClass.NOT_FOUND, "linear entity not found",
                                subtype="graphql")
        # Provider text is untrusted and may echo the credential back. Redact
        # BEFORE it becomes a message; the envelope redacts again as depth.
        return TrackerError(ErrorClass.INVALID_INPUT,
                            redact(joined[:200]) or "graphql error", subtype="graphql")
    return _generic(resp)


def _jira(resp: Response) -> Optional[TrackerError]:
    # Jira returns 404 for a missing XSRF header on attachment upload, which
    # reads as a wrong endpoint. Surfaced with a subtype so the caller can tell.
    if resp.status == 404 and b"XSRF" in (resp.body or b""):
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "Jira rejected the request: missing X-Atlassian-Token header",
                            subtype="xsrf")
    return _generic(resp)


def _github(resp: Response) -> Optional[TrackerError]:
    # GitHub serves rate limiting as **403**, not 429, with X-RateLimit-Remaining: 0.
    # Falling through to the generic rule reported it as `auth`, so the caller
    # got false credential advice and no backoff ever happened.
    if resp.status in (403, 429):
        hdrs = {k.lower(): v for k, v in (resp.headers or {}).items()}
        remaining = hdrs.get("x-ratelimit-remaining")
        body = (resp.body or b"").lower()
        if remaining == "0" or b"rate limit" in body or b"secondary rate limit" in body:
            return TrackerError(
                ErrorClass.RATE_LIMITED, "github rate limit", subtype="http_403",
                retry_after_s=_retry_after(resp) or _reset_delay(hdrs), auto_retryable=True,
            )
    return _generic(resp)


def _reset_delay(hdrs: dict[str, str]) -> Optional[float]:
    """X-RateLimit-Reset is an absolute epoch; convert to a bounded delay."""
    import time as _t

    try:
        reset = float(hdrs.get("x-ratelimit-reset", ""))
    except (TypeError, ValueError):
        return None
    delay = reset - _t.time()
    return delay if 0 < delay < 3600 else None


_TABLE = {"gitlab": _gitlab, "linear": _linear, "jira": _jira, "github": _github}


def malformed_body(detail: str) -> TrackerError:
    """A body we could not parse is transport-class but NOT auto-retryable -
    replaying it produces the same garbage."""
    return TrackerError(ErrorClass.TRANSPORT, f"malformed response body: {detail}",
                        subtype="malformed_body", auto_retryable=False)
