"""Backlog and question-valve contracts: the wire verbs exist, and an unset
ready state never executes transport.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from flowctl_tracker.wire import WIRE_VERBS  # noqa: E402
from flowctl_tracker.types import ErrorClass, TrackerError  # noqa: E402
from flowctl_tracker.wire import github, gitlab, jira, linear  # noqa: E402


class BacklogWireContractTests(unittest.TestCase):
    def test_list_open_is_a_deterministic_wire_verb(self) -> None:
        self.assertIn("list-open", WIRE_VERBS)

    def test_relation_and_question_ops_have_executable_wire_verbs(self) -> None:
        self.assertIn("relation-list", WIRE_VERBS)
        self.assertIn("question", WIRE_VERBS)

    def test_unset_ready_state_is_a_noop_for_every_provider(self) -> None:
        def forbidden_execute(_request):
            raise AssertionError("unset readyState must not execute transport")

        for provider in (github, gitlab, jira):
            with self.subTest(provider=provider.__name__):
                self.assertEqual(
                    provider.list_open({"tracker": {}}, forbidden_execute),
                    {"issues": [], "truncated": False},
                )
        # Linear refuses instead of returning a silent empty (fn-182.2 / #311):
        # a caller can handle a refusal, it cannot detect a blind enumeration.
        out = linear.list_open({"tracker": {}}, forbidden_execute)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.UNRESOLVED)
        self.assertEqual(out.subtype, "ready_state")


if __name__ == "__main__":
    unittest.main()
