"""fn-114.4 - Ralph docs truth-up pins (shipped .1-.3 state).

Pins prose contracts on the three public surfaces + flowctl CLI ref:
  * ralph.md: opt-in zero-default, ralphctl control, soft-probe, no plugin hooks.json path
  * platforms.md: zero-default + retained [features] hooks=true note
  * CLAUDE.md checklist: ralph-init owns registration (no plugin-level hooks)
  * flowctl.md: no flowctl ralph subcommand; points at ralphctl.py
  * CHANGELOG Unreleased: upgrade re-run-ralph-init note

Pin shape (agent_docs/adding-skills.md, "Prose-contract tests — pin content +
reachability"): the POSITIVE pins below assert the fact is stated in whichever
docs page carries it today AND that the page is reachable from the always-read
spine (root `CLAUDE.md` / `README.md`, transitively through
`plugins/flow-next/docs/README.md`). A fact that moves from `ralph.md` to
`running-lean.md` is not a regression; a fact that vanishes, or lands in a page
nothing routes to, is. The NEGATIVE sweeps stay welded to their file on
purpose — "this claim must not appear on THIS surface" is a location assertion
by construction (cold-path negative exception).
"""

from __future__ import annotations

import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent
REPO_ROOT = PLUGIN_DIR.parent.parent

RALPH_MD = PLUGIN_DIR / "docs" / "ralph.md"
PLATFORMS_MD = PLUGIN_DIR / "docs" / "platforms.md"
FLOWCTL_MD = PLUGIN_DIR / "docs" / "flowctl.md"
SYNC_CODEX_MD = PLUGIN_DIR / "docs" / "sync-codex.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

# Always-read entry points. Everything else has to be routed to from here.
SPINES = ("CLAUDE.md", "README.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _docs_corpus() -> dict[str, str]:
    """Root-level markdown + the flow-next docs set, keyed repo-relative."""
    paths = [
        *sorted(REPO_ROOT.glob("*.md")),
        *sorted((PLUGIN_DIR / "docs").glob("*.md")),
    ]
    return {
        p.relative_to(REPO_ROOT).as_posix(): p.read_text(encoding="utf-8")
        for p in paths
        if p.is_file()
    }


def _reachable(corpus: dict[str, str]) -> set[str]:
    """Docs a reader reaches from the spine by following file mentions."""
    seen = {s for s in SPINES if s in corpus}
    queue = list(seen)
    while queue:
        text = corpus[queue.pop()]
        for rel in corpus:
            if rel in seen:
                continue
            if rel in text or rel.rsplit("/", 1)[-1] in text:
                seen.add(rel)
                queue.append(rel)
    return seen


CORPUS = _docs_corpus()
REACHABLE = _reachable(CORPUS)


def assert_stated_and_reachable(
    case: unittest.TestCase, needle: str, *, lower: bool = False
) -> str:
    """The fact is stated in SOME doc, and that doc is on the read path."""
    def carries(text: str) -> bool:
        return needle in (text.lower() if lower else text)

    hits = [rel for rel, text in CORPUS.items() if carries(text)]
    case.assertTrue(
        hits,
        f"no documentation page states {needle!r} — scanned {sorted(CORPUS)}",
    )
    reachable_hits = [rel for rel in hits if rel in REACHABLE]
    case.assertTrue(
        reachable_hits,
        f"{needle!r} only lives in unreachable page(s) {hits} — nothing on "
        f"the path from {SPINES} routes a reader there",
    )
    return reachable_hits[0]


class TestRalphDocsTruth(unittest.TestCase):
    def test_ralph_md_opt_in_and_control_surface(self) -> None:
        """Ralph's opt-in / control-surface facts stay stated and reachable
        (they live on `ralph.md` today; the contract is the statement, not
        the page). Negatives stay pinned to `ralph.md` itself."""
        for needle in ("fully opt-in", "zero hooks", "soft-probe", "no word sniff"):
            with self.subTest(fact=needle):
                assert_stated_and_reachable(self, needle, lower=True)
        for needle in (
            "ralphctl.py",
            "promise=COMPLETE",
            "key=value",
            "ApplyPatch",
            "RALPH_GUARD_DEBUG=1",
        ):
            with self.subTest(fact=needle):
                assert_stated_and_reachable(self, needle)

        text = _read(RALPH_MD)
        # Control is NOT flowctl ralph after extraction
        self.assertNotRegex(
            text,
            r"flowctl\s+ralph\s+(pause|resume|stop|status)",
            "ralph.md must not document removed flowctl ralph subcommands",
        )
        # Plugin-level hooks.json location is gone
        self.assertNotIn("hooks/hooks.json              # Config", text)
        self.assertNotIn("plugins/flow-next/\n  hooks/hooks.json", text)

    def test_platforms_md_codex_zero_default_and_hooks_flag(self) -> None:
        """Codex zero-default + the retained `hooks = true` feature-flag note
        stay stated on a reachable page."""
        for needle in ("ship `hooks/hooks.json`", "hooks = true"):
            with self.subTest(fact=needle):
                assert_stated_and_reachable(self, needle)
        assert_stated_and_reachable(self, "feature flag only", lower=True)

        text = _read(PLATFORMS_MD)
        self.assertNotIn(
            "A pre-built `codex/hooks.json` may exist",
            text,
            "Codex zero-default is complete; no mirror hooks.json",
        )

    def test_claude_md_checklist_ralph_init_owns_registration(self) -> None:
        """ralph-init owns hook registration — stated and reachable. The
        checklist sits in root `CLAUDE.md` today, which is itself a spine."""
        for needle in ("No plugin-level hooks", "ralph-init", "plugins/flow-next/hooks/"):
            with self.subTest(fact=needle):
                assert_stated_and_reachable(self, needle)

    def test_flowctl_md_points_at_ralphctl(self) -> None:
        """The ralphctl control surface stays documented and reachable; the
        flowctl reference itself must not re-grow a `ralph` command group."""
        for needle in ("ralphctl.py",):
            with self.subTest(fact=needle):
                assert_stated_and_reachable(self, needle)
        assert_stated_and_reachable(self, "soft-probe", lower=True)

        text = _read(FLOWCTL_MD)
        self.assertNotRegex(
            text,
            r"flowctl\s+ralph\s+(status|pause|resume|stop)",
            "flowctl.md must not list flowctl ralph commands",
        )
        # Available Commands list must not advertise ralph group
        avail = text.split("## Available Commands", 1)[1].split("##", 1)[0]
        self.assertNotRegex(avail, r"\bralph\b")

    def test_sync_codex_md_zero_default_hooks(self) -> None:
        """The mirror ships no hooks.json — stated and reachable; the
        generate-hooks steps stay absent from `sync-codex.md`."""
        assert_stated_and_reachable(self, "No `hooks.json`")

        text = _read(SYNC_CODEX_MD)
        self.assertNotIn("Generate hooks.json", text)
        self.assertNotIn("plugins/flow-next/hooks/hooks.json", text)

    def test_changelog_upgrade_note(self) -> None:
        text = _read(CHANGELOG)
        # Positionally immune (fn-121 broke a top-1 scan; the 3.1.0 release
        # broke the top-2 fix hours later): the loud ralph re-init upgrade
        # note must live TOGETHER inside a single release section, wherever
        # the changelog's growth has pushed that section.
        sections = text.split("\n## [")
        pins = (
            "fn-114",
            "re-run `/flow-next:ralph-init`",
            "Upgrade note",
            "ralphctl.py",
            "hooks = true",
        )
        carrier = [s for s in sections if all(pin in s for pin in pins)]
        self.assertTrue(
            carrier,
            "no single changelog release section carries the full ralph "
            "re-init upgrade note (pins: %r)" % (pins,),
        )


if __name__ == "__main__":
    unittest.main()
