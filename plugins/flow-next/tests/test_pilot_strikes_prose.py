"""fn-184.2 (#325) - prose contracts for the pilot strikes recovery verb.

What is pinned, and why only this much:

* The armed-`tracker.readyState` escape clause in the pilot skill must name a
  recovery a human can actually perform. Before fn-184 it named "an explicit
  re-ready made after the failure is understood (not a projection echo)" -
  unimplementable, because a deliberate board move and a projection echo are
  byte-identical in every durable artifact. The pin is the VERB being reachable
  from that clause, plus the retired unimplementable phrasing being absent.
* The strike-2/2 terminal reason must carry the same verb, so a
  transcript-only driver or human sees the recovery without reading a doc.
* `docs/tracker-sync.md` must no longer claim a board re-ready clears strikes.

Pin shape (agent_docs/adding-skills.md): smallest distinctive tokens plus
reachability - never a sentence. Skill-prose pins are welded to their file
(a skill workflow is a location by construction). Doc-side POSITIVE pins assert
the fact is stated on SOME page a reader reaches from the always-read spine;
the NEGATIVE sweep stays welded to `tracker-sync.md` because "this claim must
not appear on THIS surface" is a location assertion.
"""

from __future__ import annotations

import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PLUGIN_DIR.parent.parent

PILOT_SKILL = PLUGIN_DIR / "skills" / "flow-next-pilot"
PILOT_MIRROR = PLUGIN_DIR / "codex" / "skills" / "flow-next-pilot"
WORKFLOW = PILOT_SKILL / "workflow.md"
BACKLOG_MODE = PILOT_SKILL / "references" / "backlog-mode.md"
TRACKER_SYNC_MD = PLUGIN_DIR / "docs" / "tracker-sync.md"

CLEAR_VERB = "flowctl pilot strikes clear"
LIST_VERB = "flowctl pilot strikes list"
LEDGER_FILE = "pilot-strikes.json"

SPINES = ("CLAUDE.md", "README.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _docs_corpus() -> dict[str, str]:
    paths = [
        *sorted(REPO_ROOT.glob("*.md")),
        *sorted((PLUGIN_DIR / "docs").glob("*.md")),
    ]
    return {
        p.relative_to(REPO_ROOT).as_posix(): _read(p) for p in paths if p.is_file()
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


def _paragraph_with(text: str, anchor: str) -> str:
    """The blank-line-delimited block (or list item) carrying `anchor`."""
    for block in text.split("\n\n"):
        if anchor in block:
            return block
    return ""


class PilotStrikesProseTests(unittest.TestCase):
    def test_armed_ready_state_escape_clause_names_the_verb(self) -> None:
        """The exception that keeps a strike alive under a projection-set
        ready must, in the same breath, name the clear a human can run."""
        for path, anchor in (
            (WORKFLOW, "survives a projection-set ready"),
            (BACKLOG_MODE, "do NOT clear a `count >= 2` strike on"),
        ):
            with self.subTest(surface=path.name):
                block = _paragraph_with(_read(path), anchor)
                self.assertTrue(block, f"{path.name}: escape clause anchor gone")
                self.assertIn(
                    CLEAR_VERB,
                    block,
                    f"{path.name}: the armed-readyState escape clause must name "
                    f"{CLEAR_VERB!r} as the recognized human clear",
                )

    def test_unimplementable_re_ready_escape_is_retired(self) -> None:
        """No pilot surface may still promise a recovery keyed on a board
        re-ready - flowctl stores no readiness provenance, so the skill cannot
        tell a deliberate re-ready from a projection echo."""
        for path in sorted(PILOT_SKILL.rglob("*.md")):
            with self.subTest(surface=path.name):
                text = _read(path)
                self.assertNotIn("non-projection re-ready", text)
                self.assertNotIn("not a projection echo", text)

    def test_null_ready_state_clear_on_ready_path_survives(self) -> None:
        """The exception is scoped to an ARMED `tracker.readyState`; on a repo
        without it, a ready-again spec still clears its own ledger entry."""
        for path, needle in (
            (WORKFLOW, "Clear that ledger entry"),
            (BACKLOG_MODE, "clear the entry and treat the spec as fresh"),
        ):
            with self.subTest(surface=path.name):
                self.assertIn(needle, _read(path))

    def test_strike_two_terminal_reason_carries_the_recovery(self) -> None:
        """The strikeout verdict is the one terminal a human must undo by
        hand; the reason string carries the command."""
        block = _paragraph_with(_read(WORKFLOW), "strike 2/2, spec unreadied")
        self.assertTrue(block, "workflow.md: strike 2/2 terminal line gone")
        self.assertIn(CLEAR_VERB, block)

    def test_ledger_ownership_is_the_shared_contract(self) -> None:
        """flowctl owns read + clear; the skill keeps its record write sites."""
        block = _paragraph_with(_read(WORKFLOW), "Ledger schema:")
        self.assertTrue(block, "workflow.md: ledger schema paragraph gone")
        self.assertNotIn("no flowctl plumbing", block)
        self.assertIn(LIST_VERB, block)
        self.assertIn(CLEAR_VERB, block)

    def test_tracker_sync_no_longer_claims_the_board_clears_strikes(self) -> None:
        text = _read(TRACKER_SYNC_MD)
        self.assertNotIn("human re-blessed (strikes cleared)", text)
        self.assertNotIn("strikes cleared", text)
        self.assertIn(CLEAR_VERB, text)

    def test_recovery_is_documented_on_a_reachable_page(self) -> None:
        """The verb and the ledger location are stated where a reader lands."""
        for needle in (CLEAR_VERB, LIST_VERB, LEDGER_FILE):
            with self.subTest(fact=needle):
                hits = [rel for rel, txt in CORPUS.items() if needle in txt]
                self.assertTrue(hits, f"no docs page states {needle!r}")
                self.assertTrue(
                    [rel for rel in hits if rel in REACHABLE],
                    f"{needle!r} only lives in unreachable page(s) {hits}",
                )

    def test_codex_mirror_carries_the_same_recovery(self) -> None:
        for rel in ("workflow.md", "references/backlog-mode.md"):
            with self.subTest(mirror=rel):
                self.assertIn(CLEAR_VERB, _read(PILOT_MIRROR / rel))


if __name__ == "__main__":
    unittest.main()
