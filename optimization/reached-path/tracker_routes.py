"""Offline tracker-sync selected-adapter route traces.

This is evaluation plumbing, not a runtime tracker client.  It models the
production prompt router and records the production command/wire *shape* that
the selected adapter reference owns.  ``FakeTransport`` never executes a
command or opens a network connection.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = "plugins/flow-next/skills/flow-next-tracker-sync"
COMMON_REFS = (
    f"{ROOT}/steps.md",
    f"{ROOT}/references/adapter-interface.md",
    f"{ROOT}/references/body-merge.md",
    f"{ROOT}/references/status-sync.md",
    f"{ROOT}/references/comments-sync.md",
    f"{ROOT}/references/identity.md",
)
ADAPTER_REFS = {
    "github": (f"{ROOT}/references/github.md",),
    "gitlab": (f"{ROOT}/references/gitlab.md",),
    "jira": (f"{ROOT}/references/jira.md",),
    "linear-mcp": (
        f"{ROOT}/references/linear-ladder.md",
        f"{ROOT}/references/linear-mcp.md",
    ),
    "linear-graphql": (
        f"{ROOT}/references/linear-ladder.md",
        f"{ROOT}/references/linear-graphql.md",
    ),
    "linear-none": (f"{ROOT}/references/linear-ladder.md",),
}
ALL_ADAPTER_REFS = frozenset(path for refs in ADAPTER_REFS.values() for path in refs)

# Representative production forms, asserted against the selected canonical
# adapter reference.  The fake records these strings but never invokes them.
PRODUCTION_FORMS = {
    "github": "gh issue edit",
    "gitlab": 'glab api --method PUT "projects/$ENC/issues/$IID"',
    "jira": "$JIRA_BASE/rest/api/$APIV/issue/",
    "linear-mcp": "save_issue",
    "linear-graphql": "https://api.linear.app/graphql",
    "linear-none": "sync receipt",
}


@dataclass(frozen=True)
class Route:
    state: str
    common_reads: tuple[str, ...]
    adapter_reads: tuple[str, ...]
    forbidden_reads: tuple[str, ...]
    safe_stop: bool

    @property
    def reached_reads(self) -> tuple[str, ...]:
        return self.common_reads + self.adapter_reads


def resolve_route(
    *,
    active: bool | None,
    provider: str | None,
    linear_mcp: bool = False,
    linear_api_key: bool = False,
) -> Route:
    """Resolve the prompt route; ``None`` means malformed/unreadable state."""
    normalized = provider.strip().lower() if isinstance(provider, str) else ""
    if active is False:
        state = "inactive"
        selected: tuple[str, ...] = ()
        safe_stop = True
    elif active is not True or normalized not in {"linear", "github", "gitlab", "jira"}:
        state = "unknown"
        selected = ()
        safe_stop = True
    elif normalized == "linear":
        if linear_mcp:
            state = "linear-mcp"
        elif linear_api_key:
            state = "linear-graphql"
        else:
            state = "linear-none"
        selected = ADAPTER_REFS[state]
        safe_stop = state == "linear-none"
    else:
        state = normalized
        selected = ADAPTER_REFS[state]
        safe_stop = False

    forbidden = tuple(sorted(ALL_ADAPTER_REFS.difference(selected)))
    return Route(state, COMMON_REFS, selected, forbidden, safe_stop)


class FakeTransport:
    """Capture a production-shaped call without executing it."""

    def __init__(self, route: Route, *, available: bool = True) -> None:
        self.route = route
        self.available = available
        self.calls: list[dict[str, Any]] = []

    def call(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.route.safe_stop or not self.available:
            transport = "none"
            status = "noop"
            wire_form = None
        elif operation.startswith("conflict-"):
            transport = {
                "github": "gh",
                "gitlab": "glab",
                "jira": "rest",
                "linear-mcp": "mcp",
                "linear-graphql": "graphql",
            }[self.route.state]
            status = "queued"
            wire_form = PRODUCTION_FORMS[self.route.state]
        else:
            transport = {
                "github": "gh",
                "gitlab": "glab",
                "jira": "rest",
                "linear-mcp": "mcp",
                "linear-graphql": "graphql",
            }[self.route.state]
            status = "updated"
            wire_form = PRODUCTION_FORMS[self.route.state]
        trace = {
            "operation": operation,
            "normalized_request": dict(payload),
            "wire_form": wire_form,
            "transport": transport,
            "receipt_status": status,
            "external_writes": 0,
            "fake": True,
        }
        self.calls.append(trace)
        return trace


def assert_production_form(repo_root: Path, route: Route) -> None:
    """Prove a fake's wire marker comes from the selected canonical reference."""
    marker = PRODUCTION_FORMS.get(route.state)
    if marker is None:
        return
    selected_text = "\n".join(
        (repo_root / path).read_text(encoding="utf-8") for path in route.adapter_reads
    )
    if marker not in selected_text:
        raise AssertionError(
            f"{route.state}: production form {marker!r} missing from selected adapter"
        )
