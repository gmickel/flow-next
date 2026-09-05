"""CI trigger filter must cover the unit suite's own read surface.

The #244 rule ("a filter narrower than the lint scope lets a violation land
without the gate ever running") applies to the unit suite exactly as it applies
to ruff: this suite pins content in repo-root trees outside
`plugins/flow-next/**` — prose contracts under `agent_docs/`, mirror-parity
against `scripts/sync-codex.sh`, eval harnesses under `optimization/` — and a
`paths:` filter that omits one of them
means a PR touching only that tree never runs the tests that pin it.

Measured 2026-08-13: `agent_docs/**.md` was omitted, so a conduct-checklist edit
violating `test_two_axis_audit_contract` classified tier-B locally
(`flowctl gate classify` → docs-only) AND triggered no workflow, leaving the pin
unrun on both paths.
"""

from __future__ import annotations

import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "test-flow-next.yml"
TESTS_DIR = pathlib.Path(__file__).resolve().parent

# Top-level repo entries a test may reference without a trigger pattern.
EXEMPT_TOP_LEVEL = frozenset(
    {
        ".git",  # probed for repository shape, never asserted on content
        ".flow",  # partially covered: assets/ (specs/tasks are bookkeeping)
        "plugins",  # plugins/flow-next/** is the primary trigger
        "ruff.toml",
    }
)


def _trigger_blocks(text: str) -> dict[str, list[str]]:
    """Return the `paths:` list under each of push: and pull_request:."""
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    in_paths = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if re.fullmatch(r"(push|pull_request):", stripped):
            current = stripped.rstrip(":")
            blocks[current] = []
            in_paths = False
            continue
        if current and stripped == "paths:":
            in_paths = True
            continue
        if current and in_paths:
            match = re.fullmatch(r'- "([^"]+)"', stripped)
            if match:
                blocks[current].append(match.group(1))
            elif stripped and not stripped.startswith("#"):
                in_paths = False
                if not re.fullmatch(r"(branches|paths):.*", stripped):
                    current = None
    return blocks


def _covered(pattern_list: list[str], top_level: str) -> bool:
    return any(p == top_level or p.startswith(f"{top_level}/") for p in pattern_list)


def _read_surface() -> set[str]:
    """Top-level repo entries the suite reads via REPO_ROOT."""
    tops: set[str] = set()
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r'REPO_ROOT ?/ ?"([^"]+)"', text):
            # A reference may be written as one joined string ("a/b/c") or as
            # chained segments; only the first segment names a repo-root entry.
            tops.add(match.group(1).split("/")[0])
    return tops


class TriggerCoverage(unittest.TestCase):
    def test_both_event_filters_cover_the_read_surface(self) -> None:
        blocks = _trigger_blocks(WORKFLOW.read_text(encoding="utf-8"))
        self.assertEqual({"push", "pull_request"}, set(blocks), "both event filters must parse")
        surface = _read_surface() - EXEMPT_TOP_LEVEL
        self.assertIn("agent_docs", surface, "the measured 2026-08-13 gap must stay covered")
        for event, patterns in blocks.items():
            if not patterns:  # No path filter triggers CI for every changed path.
                continue
            uncovered = sorted(top for top in surface if not _covered(patterns, top))
            self.assertEqual(
                [],
                uncovered,
                f"{event}: the suite reads these but no trigger pattern covers them - "
                "add the pattern or record the exemption with its reason",
            )

    def test_push_and_pull_request_filters_stay_in_step(self) -> None:
        blocks = _trigger_blocks(WORKFLOW.read_text(encoding="utf-8"))
        self.assertEqual(
            sorted(blocks["push"]),
            sorted(blocks["pull_request"]),
            "a tree gated on one event only runs its pins on that event",
        )


if __name__ == "__main__":
    unittest.main()
