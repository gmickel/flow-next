"""Typed transport contracts for the tracker executor (fn-139.2).

Every field here is load-bearing and several are the result of a measurement
rather than a preference - the comments say which, because the next reader will
otherwise "simplify" them back into the bug.
"""

from __future__ import annotations

import enum
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


def gitlab_cli_hostname(host: str) -> str:
    """glab's --hostname wants its config key: a BARE hostname. Self-managed
    instances on http and/or a non-default port store a scheme-prefixed
    origin in perTracker.host (the HTTP route derives its API base from it);
    glab carries protocol/port itself under the bare-hostname key (measured
    live 2026-07-28: --hostname http://gitlab.localhost:8929 is rejected 400,
    while the profile key is gitlab.localhost with api_protocol/api_host)."""
    if "://" in host:
        from urllib.parse import urlparse
        try:
            parsed = urlparse(host)
        except ValueError:
            return host
        return parsed.hostname or host
    return host.split(":", 1)[0] if host.count(":") == 1 and host.rsplit(":", 1)[-1].isdigit() else host
