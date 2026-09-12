"""Capture saved-spec review and refine ratification contracts.

Canonical option tokens and reachable references only; generated mirrors are
checked by the normal sync and install tests. These checks do not claim to
execute the host-agent workflow.
"""

from __future__ import annotations

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "plugins" / "flow-next"
SKILLS = PLUGIN / "skills"

CAPTURE_SKILL = SKILLS / "flow-next-capture" / "SKILL.md"
CAPTURE_WORKFLOW = SKILLS / "flow-next-capture" / "workflow.md"
CAPTURE_PHASES = SKILLS / "flow-next-capture" / "phases.md"
INTERVIEW_DOC_AWARE = (
    SKILLS / "flow-next-refine" / "references" / "doc-aware.md"
)
INTERVIEW_WRITE_BACK = (
    SKILLS / "flow-next-refine" / "references" / "write-back.md"
)

ALL_FILES = (
    CAPTURE_SKILL,
    CAPTURE_WORKFLOW,
    CAPTURE_PHASES,
    INTERVIEW_DOC_AWARE,
    INTERVIEW_WRITE_BACK,
)

# Old embed-in-body wording that made long drafts unreadable — must be gone.
# (Negative guards kept: embedding drafts in ask bodies is the dangerous class.)
FORBIDDEN_EMBED_PHRASES = (
    # Capture Phase 4 old ask body that listed every criterion inside the question.
    "Full draft in the Write render above (expand if collapsed)",
    "Every acceptance criterion's substance, one short plain line each",
    "the user must see what they are approving inside the question",
    # Interview decision-entry old allowance (explicit R13 target).
    "inline in the question or in the message preceding",
    "Show the full body inline in the question",
    # Old capture overview that put the summary payload / criteria in the ask.
    "the `AskUserQuestion` body carries the plain-language summary payload",
    "every criterion in one plain line",
    # fn-123 review hardening additions.
    "the question body must say the full draft is in the Write render above",
    "rides in the §4.2 question body",
)


SPINE = "SKILL.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _corpus(skill_dir: pathlib.Path) -> dict[str, str]:
    """Every markdown file a skill ships, keyed by path relative to the skill."""
    return {
        p.relative_to(skill_dir).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(skill_dir.rglob("*.md"))
        if p.is_file()
    }


def _reachable(corpus: dict[str, str]) -> set[str]:
    """Files reachable from `SKILL.md` by following file mentions (BFS)."""
    seen = {SPINE}
    queue = [SPINE]
    while queue:
        text = corpus[queue.pop()]
        for rel in corpus:
            if rel in seen:
                continue
            if rel in text or rel.rsplit("/", 1)[-1] in text:
                seen.add(rel)
                queue.append(rel)
    return seen


CAPTURE_CORPUS = _corpus(SKILLS / "flow-next-capture")
CAPTURE_REACHABLE = _reachable(CAPTURE_CORPUS)
INTERVIEW_CORPUS = _corpus(SKILLS / "flow-next-refine")
INTERVIEW_REACHABLE = _reachable(INTERVIEW_CORPUS)


class ReadbackAskContract(unittest.TestCase):
    """Print-then-ask tokens present; old long-question embed wording absent."""

    def setUp(self) -> None:
        for path in ALL_FILES:
            self.assertTrue(path.is_file(), f"missing canonical file: {path}")
        self.capture_skill = _read(CAPTURE_SKILL)
        self.capture_workflow = _read(CAPTURE_WORKFLOW)
        self.capture_phases = _read(CAPTURE_PHASES)
        self.doc_aware = _read(INTERVIEW_DOC_AWARE)
        self.write_back = _read(INTERVIEW_WRITE_BACK)
        self.combined = "\n".join(
            (
                self.capture_skill,
                self.capture_workflow,
                self.capture_phases,
                self.doc_aware,
                self.write_back,
            )
        )

    def _assert_reachable(
        self,
        corpus: dict[str, str],
        reachable: set[str],
        predicate,
        what: str,
        skill: str,
    ) -> str:
        """`what` is stated in some file of `skill` that `SKILL.md` reaches."""
        hits = [rel for rel, text in corpus.items() if predicate(text)]
        self.assertTrue(
            hits,
            f"no file in {skill} states {what} — scanned {sorted(corpus)}",
        )
        reachable_hits = [rel for rel in hits if rel in reachable]
        self.assertTrue(
            reachable_hits,
            f"{skill}: {what} only lives in unreachable file(s) {hits} — "
            f"nothing on the path from {SPINE} carries it",
        )
        return reachable_hits[0]

    def test_contract_tokens_present_in_owning_files(self) -> None:
        """The print-then-ask tokens stay stated and reachable in each skill.

        """
        interview_home = self._assert_reachable(
            INTERVIEW_CORPUS,
            INTERVIEW_REACHABLE,
            lambda text: "print-then-ask" in text.lower(),
            "the print-then-ask contract",
            "interview",
        )
        self.assertIn(
            interview_home,
            INTERVIEW_CORPUS[SPINE],
            f"interview {SPINE} must route to {interview_home}, which carries "
            f"the print-then-ask contract",
        )
        # Short-ask tally token stays somewhere capture routes to.
        self._assert_reachable(
            CAPTURE_CORPUS,
            CAPTURE_REACHABLE,
            lambda text: "[inferred]" in text,
            "the short-ask source tally token `[inferred]`",
            "capture",
        )
        # Refine keeps its existing edit-cycle contract.
        for skill, corpus, reachable in (
                        ("interview", INTERVIEW_CORPUS, INTERVIEW_REACHABLE),
        ):
            with self.subTest(skill=skill):
                self._assert_reachable(
                    corpus,
                    reachable,
                    lambda text: re.search(r"re-?print", text, re.IGNORECASE)
                    is not None,
                    "the edit-cycle reprint rule",
                    skill,
                )

    def test_old_embed_in_body_wording_absent(self) -> None:
        for phrase in FORBIDDEN_EMBED_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertNotIn(
                    phrase,
                    self.combined,
                    f"old embed-in-ask-body wording still present: {phrase!r}",
                )

    def test_autofix_path_still_non_interactive(self) -> None:
        """Autofix remains non-interactive; `--yes` is still the write
        gate — stated wherever capture documents the mode (the spine,
        `workflow.md`, or `references/autofix-mode.md`) and reachable from
        `SKILL.md`."""
        for token in ("mode:autofix", "--yes"):
            with self.subTest(token=token):
                self._assert_reachable(
                    CAPTURE_CORPUS,
                    CAPTURE_REACHABLE,
                    lambda text, token=token: token in text,
                    f"the autofix token {token!r}",
                    "capture",
                )
        self._assert_reachable(
            CAPTURE_CORPUS,
            CAPTURE_REACHABLE,
            lambda text: re.search(
                r"(?i)autofix.*--yes|`--yes`.*substitut", text
            )
            is not None,
            "the autofix `--yes` write gate",
            "capture",
        )


class CaptureSavedSpecContract(unittest.TestCase):
    """Public option tokens and the reached write/editor boundary."""

    def test_interactive_options_and_reference_reachability(self) -> None:
        for rel in CAPTURE_REACHABLE:
            with self.subTest(reference=rel):
                self.assertNotIn("`approve and write`", CAPTURE_CORPUS[rel])
                self.assertNotIn("`approve as-is`", CAPTURE_CORPUS[rel])
        workflow = _read(CAPTURE_WORKFLOW)
        for token in ("`open in editor`", "`continue`", "`mark-ready`", "`keep-draft`"):
            self.assertIn(token, workflow)
        self.assertIn("[docs/read-back.md](../../docs/read-back.md)", workflow)
        self.assertIn("references/split-proposal.md", CAPTURE_REACHABLE)
        split = CAPTURE_CORPUS["references/split-proposal.md"]
        for token in ("`split-as-proposed`", "`keep-one-spec`", "`abort`"):
            self.assertIn(token, split)

    def test_saved_review_follows_spec_write(self) -> None:
        workflow = _read(CAPTURE_WORKFLOW)
        review = workflow.index("### 5.6a")
        self.assertLess(workflow.index('spec set-plan "$SPEC_ID" --file'), review)
        self.assertLess(review, workflow.index("### 5.8"))
        self.assertLess(review, workflow.index("### 5.9"))
        # Refine retains the shared pre-write approval options.
        contract = _read(PLUGIN / "docs" / "read-back.md")
        ratification, saved_review = contract.split("## Capture: saved-spec review")
        self.assertIn("`approve and write`", ratification)
        self.assertNotIn("`approve and write`", saved_review)


class CodexEditorQuestionPlacement(unittest.TestCase):
    def test_negative_footer_is_not_an_ask_anchor(self) -> None:
        source = _read(REPO_ROOT / "scripts" / "sync-codex.sh")
        function = "def is_negative_context(line):" + source.split(
            "def is_negative_context(line):", 1
        )[1].split("\ndef is_table_line", 1)[0]
        namespace = {"re": re}
        # Execute only the repository-owned generator function extracted above.
        exec(compile(function, "sync-codex:is_negative_context", "exec"), namespace)  # noqa: S102
        negative = namespace["is_negative_context"]
        self.assertTrue(negative("Informational only — never a plain-text numbered prompt."))
        self.assertFalse(negative("Use `plain-text numbered prompt` for one short editor question:"))

    def test_mirror_instruction_belongs_to_saved_editor_offer(self) -> None:
        mirror = _read(PLUGIN / "codex" / "skills" / "flow-next-capture" / "workflow.md")
        instruction = "**Ask the user via plain text.**"
        self.assertEqual(mirror.count(instruction), 1)
        editor = mirror[mirror.index("### 5.6a"):mirror.index("### 5.7")]
        self.assertIn(instruction, editor)
        self.assertNotIn(instruction, mirror[mirror.index("### Biz-suggestion footer"):])


if __name__ == "__main__":
    unittest.main()
