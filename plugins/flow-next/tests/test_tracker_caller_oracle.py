"""Immutable pre-teardown tracker caller oracle and matrix guards."""

from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_COMMIT = "410756ef8f27d14c3cfbcbffe66356c67fd255ad"
ORACLE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "tracker_callers"
    / f"oracle-{SOURCE_COMMIT}.json"
)
EVENTS = {
    "capture",
    "interview",
    "plan",
    "work.firstClaim",
    "work.done",
    "completionReview",
    "makePr",
    "resolvePr",
    "qa",
    "land.merged",
}
REQUIRED_CALLER_FIELDS = {
    "id",
    "file",
    "event",
    "config_key",
    "legal_config_values",
    "resolved_facade_op",
    "unconditional_behavior",
    "content_input",
    "expected_receipt",
    "config_reads",
    "argv",
    "imports",
    "stdout",
    "stderr",
}
RUNNER_TOKENS = ("tracker-runner", "tracker_runner", "tracker-dispatch")
CURRENT_TEARDOWN_ADDITIONS = (
    "plugins/flow-next/docs/tracker-sync.md",
    "plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md",
)


class TrackerCallerOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.oracle = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
        cls.callers = {
            caller["id"]: caller for caller in cls.oracle["callers"]
        }

    def _source_at_oracle_commit(self, relative: str) -> str:
        result = subprocess.run(
            ["git", "show", f"{SOURCE_COMMIT}:{relative}"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout

    def test_oracle_is_commit_addressed_and_precedes_caller_rewire(self) -> None:
        self.assertIn(SOURCE_COMMIT, ORACLE_PATH.name)
        self.assertEqual(self.oracle["source_commit"], SOURCE_COMMIT)
        self.assertEqual(
            self.oracle["source_commit_name"],
            "post-fn-140 / pre-fn-141-C caller baseline",
        )
        self.assertIs(self.oracle["captured_before_caller_rewire"], True)
        self.assertIn("byte-exact", self.oracle["observation_scope"])
        self.assertRegex(SOURCE_COMMIT, r"^[0-9a-f]{40}$")

        for relative, blob in self.oracle["source_blobs"].items():
            resolved = subprocess.run(
                ["git", "rev-parse", f"{SOURCE_COMMIT}:{relative}"],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(resolved, blob, relative)

    def test_matrix_is_authoritative_and_complete(self) -> None:
        self.assertEqual(set(self.callers), EVENTS)
        self.assertEqual(
            {caller["event"] for caller in self.callers.values()},
            EVENTS,
        )
        self.assertEqual(
            self.oracle["per_event_enum"],
            ["off", "pull", "push", "reconcile", "comment"],
        )

        for caller in self.callers.values():
            self.assertEqual(set(caller), REQUIRED_CALLER_FIELDS, caller["id"])
            self.assertTrue((REPO_ROOT / caller["file"]).is_file(), caller["file"])
            self.assertTrue(caller["expected_receipt"])
            self.assertIn("off", caller["legal_config_values"])
            self.assertTrue(caller["resolved_facade_op"])
            self.assertTrue(caller["content_input"])
            for observation in ("argv", "imports"):
                self.assertEqual(
                    set(caller[observation]),
                    {"inactive", "active"},
                    f"{caller['id']}:{observation}",
                )
            self.assertEqual(
                set(caller["config_reads"]),
                {"inactive", "active"},
                caller["id"],
            )
            for stream in ("stdout", "stderr"):
                self.assertEqual(
                    caller[stream],
                    {"inactive": "", "active_success": ""},
                    f"{caller['id']}:{stream}",
                )
            self.assertEqual(caller["argv"]["inactive"], [])
            self.assertEqual(caller["imports"]["inactive"], [])

    def test_exception_semantics_are_explicit(self) -> None:
        for caller_id in ("interview", "plan"):
            caller = self.callers[caller_id]
            self.assertNotIn(
                f"event:{caller['event']}",
                caller["argv"]["active"],
            )
            self.assertEqual(
                caller["expected_receipt"],
                "sync receipt without an event tag",
            )

        interview_source = self._source_at_oracle_commit(
            "plugins/flow-next/skills/flow-next-interview/SKILL.md"
        )
        plan_source = self._source_at_oracle_commit(
            "plugins/flow-next/skills/flow-next-plan/steps.md"
        )
        self.assertNotIn("event: interview", interview_source)
        self.assertNotIn("event: plan", plan_source)

        qa = self.callers["qa"]
        self.assertEqual(qa["legal_config_values"], ["off", "comment"])
        self.assertEqual(qa["resolved_facade_op"], "comment")
        for value in ("pull", "push", "reconcile", "comment"):
            self.assertIn(value, qa["unconditional_behavior"])

        make_pr = self.callers["makePr"]
        self.assertEqual(
            make_pr["config_reads"],
            {
                "inactive": [["sync", "active", "--json"]],
                "active": [["sync", "active", "--json"]],
            },
        )
        self.assertEqual(make_pr["resolved_facade_op"], "reconcile")
        self.assertIn("regardless of the leaf", make_pr["unconditional_behavior"])

        land = self.callers["land.merged"]
        self.assertEqual(
            land["config_reads"],
            {
                "inactive": [["sync", "active", "--json"]],
                "active": [["sync", "active", "--json"]],
            },
        )
        self.assertEqual(
            land["resolved_facade_op"],
            "push_if_merged_else_comment",
        )
        self.assertIn("ignores the leaf", land["unconditional_behavior"])
        self.assertIn("MERGED", land["unconditional_behavior"])

        fixed_work_ops = {
            "work.firstClaim": "push",
            "work.done": "comment",
            "completionReview": "comment",
        }
        for caller_id, expected_op in fixed_work_ops.items():
            caller = self.callers[caller_id]
            self.assertEqual(caller["resolved_facade_op"], expected_op)
            self.assertIn("fixed", caller["unconditional_behavior"])
            self.assertEqual(
                caller["config_reads"]["inactive"],
                [["sync", "active", "--json"]],
            )
            self.assertGreater(
                len(caller["config_reads"]["active"]),
                len(caller["config_reads"]["inactive"]),
            )

    def test_caller_inventory_and_event_tokens_match_real_files(self) -> None:
        sweep = self.oracle["teardown_sweep"]
        self.assertEqual(
            set(sweep["canonical_caller_paths"]),
            {caller["file"] for caller in self.callers.values()}
            | {"plugins/flow-next/skills/flow-next-work/phases.md"},
        )
        for caller in self.callers.values():
            text = (REPO_ROOT / caller["file"]).read_text(encoding="utf-8")
            self.assertIn(caller["event"], text, caller["id"])
            self.assertIn(caller["config_key"], text, caller["id"])

    def test_sweep_inventory_is_explicit_and_matches_pinned_tree(self) -> None:
        sweep = self.oracle["teardown_sweep"]
        path_groups = (
            "canonical_caller_paths",
            "runner_artifacts",
            "runner_specific_tests",
            "documentation_paths",
        )
        inventory_paths: list[str] = []
        for group in path_groups:
            paths = sweep[group]
            self.assertEqual(len(paths), len(set(paths)), group)
            inventory_paths.extend(paths)
        inventory_paths.append(sweep["sync_codex_path"])
        self.assertEqual(len(inventory_paths), len(set(inventory_paths)))

        for relative in inventory_paths:
            self._source_at_oracle_commit(relative)

        script = self._source_at_oracle_commit(sweep["sync_codex_path"])
        lines = script.splitlines()
        declared = sweep["sync_codex_token_lines"]
        self.assertEqual(len(declared), len({row["line"] for row in declared}))

        actual_lines = []
        for line_number, line in enumerate(lines, start=1):
            tokens = [
                token
                for token in RUNNER_TOKENS
                for _ in range(line.count(token))
            ]
            if tokens:
                actual_lines.append({"line": line_number, "tokens": tokens})
        self.assertEqual(actual_lines, declared)

        token_line_pattern = re.compile("|".join(map(re.escape, RUNNER_TOKENS)))
        undeclared = [
            line_number
            for line_number, line in enumerate(lines, start=1)
            if token_line_pattern.search(line)
            and line_number not in {row["line"] for row in declared}
        ]
        self.assertEqual(undeclared, [])

    def test_current_tree_uses_facade_and_has_no_runner_machinery(self) -> None:
        sweep = self.oracle["teardown_sweep"]

        for relative in sweep["runner_artifacts"]:
            self.assertFalse((REPO_ROOT / relative).exists(), relative)

        current_paths = [
            *sweep["canonical_caller_paths"],
            *sweep["runner_specific_tests"],
            *sweep["documentation_paths"],
            sweep["sync_codex_path"],
            *CURRENT_TEARDOWN_ADDITIONS,
        ]
        for relative in current_paths:
            text = (REPO_ROOT / relative).read_text(encoding="utf-8")
            for token in RUNNER_TOKENS:
                self.assertNotIn(token, text, f"{relative}: {token}")

        for caller in self.callers.values():
            text = (REPO_ROOT / caller["file"]).read_text(encoding="utf-8")
            self.assertIn("sync active --json", text, caller["id"])
            self.assertIn("tracker sync", text, caller["id"])
            self.assertIn(f"--event {caller['event']}", text, caller["id"])
            for value in self.oracle["per_event_enum"]:
                self.assertIn(value, text, f"{caller['id']}: {value}")

        synthesized_comments = EVENTS - {"work.firstClaim"}
        for caller_id in synthesized_comments:
            text = (REPO_ROOT / self.callers[caller_id]["file"]).read_text(
                encoding="utf-8"
            )
            self.assertRegex(text.lower(), r"synthesi[sz]es?", caller_id)


if __name__ == "__main__":
    unittest.main()
