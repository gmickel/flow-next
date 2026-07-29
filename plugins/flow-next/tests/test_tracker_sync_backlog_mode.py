"""Backlog and question-valve contracts after tracker prose teardown."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from flowctl_tracker.wire import WIRE_VERBS  # noqa: E402
from flowctl_tracker.wire import github, gitlab, jira, linear  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO_ROOT / "plugins/flow-next/skills/flow-next-tracker-sync"
SKILL = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
STEPS = (SKILL_ROOT / "steps.md").read_text(encoding="utf-8")
ADAPTER = (SKILL_ROOT / "references/adapter-interface.md").read_text(
    encoding="utf-8"
)
COMMENTS = (SKILL_ROOT / "references/comments-sync.md").read_text(encoding="utf-8")
PILOT_ROOT = REPO_ROOT / "plugins/flow-next/skills/flow-next-pilot"
PILOT_WORKFLOW = (PILOT_ROOT / "workflow.md").read_text(encoding="utf-8")
PILOT_BACKLOG = (
    PILOT_ROOT / "references/backlog-mode.md"
).read_text(encoding="utf-8")


def collapsed(text: str) -> str:
    return re.sub(r"\s+", " ", text)


class BacklogWireContractTests(unittest.TestCase):
    def test_list_open_is_a_deterministic_wire_verb(self) -> None:
        self.assertIn("list-open", WIRE_VERBS)
        self.assertIn("deterministic `wire list-open` contract", STEPS)

    def test_relation_and_question_ops_have_executable_wire_verbs(self) -> None:
        self.assertIn("relation-list", WIRE_VERBS)
        self.assertIn("question", WIRE_VERBS)
        self.assertIn("tracker wire relation-list --locator", STEPS)
        self.assertIn("tracker wire question --locator", STEPS)
        for flag in (
            "--subject-id",
            "--blocked-stage",
            "--reason-code",
            "--question-slug",
        ):
            self.assertIn(flag, STEPS)

    def test_tracker_only_parked_scan_executes_comment_read(self) -> None:
        self.assertIn("list-comments", PILOT_WORKFLOW)
        self.assertIn(
            "tracker wire comment-list --locator", PILOT_BACKLOG)
        self.assertIn(
            "tracker wire comment-list --locator", STEPS)
        self.assertIn("fails closed", PILOT_BACKLOG)

    def test_every_provider_implements_list_open(self) -> None:
        for provider in (github, gitlab, jira, linear):
            with self.subTest(provider=provider.__name__):
                self.assertTrue(callable(provider.list_open))

    def test_unset_ready_state_is_a_noop_for_every_provider(self) -> None:
        def forbidden_execute(_request):
            raise AssertionError("unset readyState must not execute transport")

        for provider in (github, gitlab, jira, linear):
            with self.subTest(provider=provider.__name__):
                self.assertEqual(
                    provider.list_open({"tracker": {}}, forbidden_execute),
                    {"issues": [], "truncated": False},
                )

    def test_docs_keep_exact_ready_lane_and_no_implicit_spec_creation(self) -> None:
        self.assertIn("resolved ready lane", STEPS)
        self.assertIn("does not create Flow specs by itself", collapsed(STEPS))


class QuestionValveContractTests(unittest.TestCase):
    def test_question_content_remains_an_explicit_judgment_surface(self) -> None:
        self.assertIn("**Comment content synthesis.**", SKILL)
        self.assertIn(
            "For `question`, the caller owns the semantic body", STEPS)

    def test_closed_marker_families_remain_in_semantic_reference(self) -> None:
        for marker in (
            "flow-next:sync",
            "flow-next:question",
            "flow-next:answer",
            "flow-next:status",
        ):
            self.assertIn(marker, COMMENTS)

    def test_question_identity_excludes_free_prose(self) -> None:
        self.assertIn("free-prose reason is OUTSIDE", COMMENTS)
        self.assertIn("subjectId", COMMENTS)
        self.assertIn("questionSlug", COMMENTS)

    def test_flat_tracker_answer_matches_by_id(self) -> None:
        self.assertIn("answer id=<hash>", COMMENTS)
        self.assertIn("matched to the open question", COMMENTS)
        self.assertIn("parentId == null", COMMENTS)

    def test_wire_and_semantic_comment_shapes_are_not_conflated(self) -> None:
        self.assertIn('"parent_identity": "validated or not_available"', ADAPTER)
        self.assertIn('"created_at": "immutable provider timestamp or null"', ADAPTER)
        self.assertIn("stable subset `id`, `body`, and `parent_identity`", ADAPTER)
        self.assertIn("semantic comment layer", collapsed(ADAPTER))

    def test_question_reopens_only_after_latest_answer(self) -> None:
        self.assertIn("latest question", COMMENTS)
        self.assertIn("latest answer", COMMENTS)
        self.assertIn("created_at", COMMENTS)


class AutonomousBoundaryTests(unittest.TestCase):
    def test_forked_decisions_queue_instead_of_prompting(self) -> None:
        self.assertIn("In Ralph or a forked lifecycle call", SKILL)
        self.assertIn("Never attempt an interactive prompt from the fork", SKILL)

    def test_no_legacy_setup_precheck(self) -> None:
        self.assertNotIn("FLOW_SETUP_ASK", SKILL)
        self.assertNotIn("setup_version", SKILL)

    def test_no_stale_agentic_transport_claim(self) -> None:
        self.assertIn("`flowctl tracker` owns tracker transport", SKILL)
        self.assertNotIn("skill-level, never flowctl transport", SKILL)


if __name__ == "__main__":
    unittest.main()
