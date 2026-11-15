"""Typed transport contracts for the tracker executor (fn-139.2).

Every field here is load-bearing and several are the result of a measurement
rather than a preference - the comments say which, because the next reader will
otherwise "simplify" them back into the bug.
"""

from __future__ import annotations

import enum
import functools
from dataclasses import dataclass, field
from typing import Any, Optional

# Default request deadline. There is exactly ONE, not a connect/read pair:
# `urllib.request.urlopen` accepts a single `timeout`, and `gh api` / `glab api`
# expose none at all, so a split contract could not be honoured on either route.
# HTTP applies it per socket operation; CLI applies it as a total process
# deadline via `subprocess.run(timeout=)`.
DEFAULT_TIMEOUT_S = 30.0

MAX_RETRIES = 2          # rate_limited only, and only when idempotent
BACKOFF_CAP_S = 30.0
CONCURRENCY_CAP = 4


class ErrorClass(str, enum.Enum):
    """Exhaustive. Callers branch on this, never on message text."""

    INACTIVE = "inactive"
    UNRESOLVED = "unresolved"
    STALE_ID = "stale_id"
    AUTH = "auth"
    RATE_LIMITED = "rate_limited"
    TRANSPORT = "transport"
    NOT_FOUND = "not_found"
    CAPABILITY = "capability"
    CONFLICT = "conflict"
    INVALID_INPUT = "invalid_input"
    # fn-140's MCP continuation: flowctl cannot complete the operation and the
    # agent must act. NOT a failure of the request, and never retryable.
    EXTERNAL_ACTION_REQUIRED = "external_action_required"


#: Fixed, numeric, 1:1 with ErrorClass so a caller can branch on exit status
#: alone without parsing stdout.
EXIT_CODES: dict[ErrorClass, int] = {
    ErrorClass.INVALID_INPUT: 2,
    ErrorClass.INACTIVE: 3,
    ErrorClass.UNRESOLVED: 4,
    ErrorClass.AUTH: 5,
    ErrorClass.RATE_LIMITED: 6,
    ErrorClass.TRANSPORT: 7,
    ErrorClass.NOT_FOUND: 8,
    ErrorClass.CAPABILITY: 9,
    ErrorClass.CONFLICT: 10,
    ErrorClass.STALE_ID: 11,
    ErrorClass.EXTERNAL_ACTION_REQUIRED: 12,
}


class CredentialPolicy(str, enum.Enum):
    """Per REQUEST, not per provider - an always-inject executor leaks.

    Linear's attachment upload is a presigned PUT to a third-party asset host.
    Attaching the Linear API key there would hand the credential to a host with
    no business seeing it, so the policy is explicit rather than inferred.
    """

    PROVIDER_AUTH = "provider-auth"
    PRESIGNED_ANONYMOUS = "presigned-anonymous"
    NONE = "none"


@dataclass(frozen=True)
class Request:
    provider: str                 # github | gitlab | linear | jira
    op: str                       # logical operation, for classification + logs
    method: str
    url_or_argv: Any              # str for HTTP, list[str] for CLI
    headers: dict[str, str] = field(default_factory=dict)
    body: Optional[bytes] = None
    timeout_s: float = DEFAULT_TIMEOUT_S
    idempotent: bool = False
    credential_policy: CredentialPolicy = CredentialPolicy.PROVIDER_AUTH
    env: Optional[dict[str, str]] = None  # CLI route: added to the child's environment

    def __post_init__(self) -> None:
        # An adapter that sets its own authorization header has already carried
        # the credential across the boundary redaction exists to protect.
        for k in self.headers:
            if k.lower() in {"authorization", "private-token", "x-api-key"}:
                raise ValueError(
                    f"adapter set credential header {k!r}; credentials are attached "
                    "by the executor after the adapter boundary"
                )


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str]
    body: bytes
    elapsed_s: float


@dataclass(frozen=True)
class TrackerError:
    """Normalized failure. Adapters never raise transport-native exceptions."""

    cls: ErrorClass
    message: str
    #: Distinguishes cases that share a class but not a retry policy -
    #: `transport/timeout` is auto-retryable, `transport/malformed_body` is not.
    subtype: Optional[str] = None
    retry_after_s: Optional[float] = None
    details: Optional[dict[str, Any]] = None
    #: Governs the EXECUTOR's internal retry. Distinct from the envelope's
    #: `retryable`, which tells the CALLER whether re-invoking could help.
    #: Different questions, so different fields.
    auto_retryable: bool = False

    @property
    def exit_code(self) -> int:
        return EXIT_CODES[self.cls]


@functools.lru_cache(maxsize=None)
def glab_logged_in(host: str) -> Optional[bool]:
    """`glab auth status` for one host key: True, False (glab's logged-out
    answer) or None (unknown: offline host, timeout). Same rule as flowctl's
    forge `_gitlab_owns_host`."""
    import subprocess  # noqa: PLC0415
    try:
        proc = subprocess.run(["glab", "auth", "status", "--hostname", host],
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                              text=True, timeout=5, check=False)
    except subprocess.TimeoutExpired:
        return None
    except OSError:
        return False
    if proc.returncode == 0:
        return True
    return False if "has not been authenticated" in " ".join((proc.stderr or "").split()) else None


def gitlab_cli_host(host: str) -> tuple[list[str], Optional[dict[str, str]]]:
    """How glab reaches perTracker.host: (extra argv, child environment).

    perTracker.host stores the origin (the HTTP route derives its API base
    from it). glab keys a host on a non-default port as `host:port`, the form
    `glab auth login --hostname localhost:8929` stores, yet `glab api
    --hostname` rejects any value carrying a port (measured live 2026-11-15,
    glab 1.124: "invalid hostname"). Such a host goes through glab's own
    GITLAB_HOST, as make-pr-gitlab.sh does. A login made without the port is
    keyed by the bare hostname, so glab's logged-out answer for `host:port`
    sends the call there (flowctl's forge rule since 9.9.1). Any other host
    stays a bare --hostname. The login is probed once per process."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(host if "://" in host else f"https://{host}")
        port = parsed.port
    except ValueError:
        return ["--hostname", host], None
    hostname = parsed.hostname or host
    if port is not None and port != (80 if parsed.scheme == "http" else 443):
        if glab_logged_in(f"{hostname}:{port}") is False:
            return [], {"GITLAB_HOST": hostname}
        return [], {"GITLAB_HOST": f"{hostname}:{port}"}
    return ["--hostname", hostname], None
