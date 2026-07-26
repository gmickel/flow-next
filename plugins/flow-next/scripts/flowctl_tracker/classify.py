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
from typing import Optional

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


def _graphql_errors(resp: Response) -> Optional[list[dict]]:
    """GraphQL puts failures in a 200/400 body; the executor normalizes here."""
    try:
        payload = json.loads(resp.body or b"{}")
    except (ValueError, TypeError):
        return None
    errs = payload.get("errors") if isinstance(payload, dict) else None
    return errs if isinstance(errs, list) and errs else None


def classify(provider: str, resp: Response) -> Optional[TrackerError]:
    """None means success. Otherwise a normalized, classified failure."""
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
            subtype="licence", details={"required_plan": "premium"},
        )
    return _generic(resp)


def _linear(resp: Response) -> Optional[TrackerError]:
    errs = _graphql_errors(resp)
    if errs:
        joined = " ".join(str(e.get("message", "")) for e in errs).lower()
        # MEASURED: Linear rate-limits via a GraphQL error, often over HTTP 200,
        # and is complexity-based rather than request-count based.
        if "rate limit" in joined or "complexity" in joined:
            return TrackerError(ErrorClass.RATE_LIMITED, "linear rate limit",
                                subtype="graphql", retry_after_s=_retry_after(resp),
                                auto_retryable=True)
        if "authentication" in joined or "unauthorized" in joined:
            return TrackerError(ErrorClass.AUTH, "linear authentication failed",
                                subtype="graphql")
        if "not found" in joined:
            return TrackerError(ErrorClass.NOT_FOUND, "linear entity not found",
                                subtype="graphql")
        return TrackerError(ErrorClass.INVALID_INPUT, joined[:200] or "graphql error",
                            subtype="graphql")
    return _generic(resp)


def _jira(resp: Response) -> Optional[TrackerError]:
    # Jira returns 404 for a missing XSRF header on attachment upload, which
    # reads as a wrong endpoint. Surfaced with a subtype so the caller can tell.
    if resp.status == 404 and b"XSRF" in (resp.body or b""):
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "Jira rejected the request: missing X-Atlassian-Token header",
                            subtype="xsrf")
    return _generic(resp)


_TABLE = {"gitlab": _gitlab, "linear": _linear, "jira": _jira, "github": _generic}


def malformed_body(detail: str) -> TrackerError:
    """A body we could not parse is transport-class but NOT auto-retryable -
    replaying it produces the same garbage."""
    return TrackerError(ErrorClass.TRANSPORT, f"malformed response body: {detail}",
                        subtype="malformed_body", auto_retryable=False)
