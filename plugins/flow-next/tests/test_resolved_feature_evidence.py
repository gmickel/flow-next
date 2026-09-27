"""fn-261 R4: the resolved-feature record in task done evidence.

`done --resolved-feature` (and the evidence JSON's `resolved_feature` key)
accepts exactly the contract shape - an object with surface, sub_feature,
file, last_proven (string or null) and stage, or the string "unmapped" -
rejects any other shape before writing, renders a receipt line, and the
cognitive-aid export surfaces a recorded one per task and omits the key
otherwise, so old payload bytes are unchanged.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_resolved_feature_evidence -q
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import flowctl  # noqa: E402

FLOWCTL_PY = SCRIPTS / "flowctl.py"
SPEC_ID = "fn-1-sample"
TASK_ID = f"{SPEC_ID}.1"
RECORD = {
    "surface": "web",
    "sub_feature": "notes.list",
    "file": "notes-list.md",
    "last_proven": "2026-09-20 at 4f2c9ab",
    "stage": "flow",
}


class _Repo(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.env = {**os.environ, "FLOW_STATE_DIR": str(self.root / "state")}
        self.run_ok("init")
        self.run_ok("spec", "create", "--title", "Sample")
        self.run_ok("task", "create", "--spec", SPEC_ID, "--title", "T one")
        self.run_ok("start", TASK_ID)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY), *args],
            cwd=self.root, env=self.env, capture_output=True, text=True,
        )

    def run_ok(self, *args: str) -> subprocess.CompletedProcess:
        result = self.run_cli(*args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def show(self) -> dict:
        return json.loads(self.run_ok("show", TASK_ID, "--json").stdout)

    def task_md(self) -> str:
        return (self.root / ".flow" / "tasks" / f"{TASK_ID}.md").read_text(encoding="utf-8")


class DoneResolvedFeatureTest(_Repo):
    def test_object_flag_is_recorded_and_rendered(self) -> None:
        result = self.run_ok(
            "done", TASK_ID, "--evidence", '{"commits": ["abc"]}',
            "--resolved-feature", json.dumps(RECORD),
        )
        self.assertNotIn("unknown evidence key", result.stderr)
        self.assertEqual(self.show()["evidence"]["resolved_feature"], RECORD)
        self.assertIn(
            "- Resolved feature: web notes.list (notes-list.md; "
            "last proven 2026-09-20 at 4f2c9ab; resolved by flow)",
            self.task_md(),
        )

    def test_unmapped_is_recorded_and_rendered(self) -> None:
        for index, value in enumerate(("unmapped", '"unmapped"')):
            with self.subTest(value=value):
                if index:
                    self.tearDown()
                    self.setUp()
                self.run_ok(
                    "done", TASK_ID, "--evidence", '{"commits": ["abc"]}',
                    "--resolved-feature", value,
                )
                self.assertEqual(self.show()["evidence"]["resolved_feature"], "unmapped")
                self.assertIn("- Resolved feature: unmapped", self.task_md())

    def test_null_last_proven_renders_never(self) -> None:
        record = {**RECORD, "last_proven": None}
        self.run_ok(
            "done", TASK_ID, "--evidence", '{"commits": ["abc"]}',
            "--resolved-feature", json.dumps(record),
        )
        self.assertIn("last proven never", self.task_md())

    def test_malformed_record_is_rejected_before_any_write(self) -> None:
        bad = {
            "not json": "{surface",
            "list": "[]",
            "other string": '"mapped"',
            "missing key": json.dumps({k: v for k, v in RECORD.items() if k != "stage"}),
            "extra key": json.dumps({**RECORD, "route": "/notes"}),
            "empty surface": json.dumps({**RECORD, "surface": ""}),
            "null stage": json.dumps({**RECORD, "stage": None}),
            "numeric last_proven": json.dumps({**RECORD, "last_proven": 3}),
        }
        for label, value in bad.items():
            with self.subTest(label):
                result = self.run_cli(
                    "done", TASK_ID, "--evidence", '{"commits": ["abc"]}',
                    "--resolved-feature", value,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.show()["status"], "in_progress")
                self.assertNotIn("Resolved feature", self.task_md())

    def test_evidence_json_key_is_validated(self) -> None:
        result = self.run_cli(
            "done", TASK_ID, "--evidence",
            json.dumps({"commits": ["abc"], "resolved_feature": {"surface": "web"}}),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.show()["status"], "in_progress")
        self.run_ok(
            "done", TASK_ID, "--evidence",
            json.dumps({"commits": ["abc"], "resolved_feature": RECORD}),
        )
        self.assertEqual(self.show()["evidence"]["resolved_feature"], RECORD)

    def test_flag_combines_with_range(self) -> None:
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "base"], cwd=self.root, check=True)
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True, text=True, check=True).stdout.strip()
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "fix"], cwd=self.root, check=True)
        self.run_ok("done", TASK_ID, "--range", f"{base}..HEAD", "--resolved-feature", "unmapped")
        evidence = self.show()["evidence"]
        self.assertEqual(evidence["resolved_feature"], "unmapped")
        self.assertEqual(evidence["base_commit"], base)


class ExportResolvedFeatureTest(unittest.TestCase):
    def test_export_block_surfaces_only_a_valid_record(self) -> None:
        cases = {
            "object": (RECORD, RECORD),
            "unmapped": ("unmapped", "unmapped"),
            "absent": (None, None),
            "malformed": ({"surface": "web"}, None),
        }
        for label, (stored, expected) in cases.items():
            with self.subTest(label):
                runtime = {"commits": ["c1"]}
                if stored is not None:
                    runtime["resolved_feature"] = stored
                got = flowctl._export_task_evidence_block(runtime)
                self.assertEqual(got.get("resolved_feature"), expected)
                self.assertEqual("resolved_feature" in got, expected is not None)


class RecordContractParityTest(unittest.TestCase):
    """The contract's key list and flow's example line match what done accepts."""

    SKILLS = SCRIPTS.parent / "skills"

    def test_contract_keys_match_the_validator(self) -> None:
        contract = (self.SKILLS / "flow-next-features" / "references" / "feature-entry-contract.md").read_text(encoding="utf-8")
        section = contract.split("## Resolved-feature record", 1)[1].split("\n## ", 1)[0]
        bullet = next(line for line in section.splitlines() if "exactly these keys" in line)
        keys = re.findall(r"`([a-z_]+)` \(", bullet)
        self.assertEqual(tuple(keys), flowctl.RESOLVED_FEATURE_KEYS)

    def test_flow_example_line_is_a_valid_record(self) -> None:
        intake = (self.SKILLS / "flow-next-flow" / "references" / "defect-intake.md").read_text(encoding="utf-8")
        line = next(ln for ln in intake.splitlines() if ln.startswith("resolved_feature: {"))
        record = json.loads(line.split(": ", 1)[1])
        self.assertIsNone(flowctl.resolved_feature_error(record))
        self.assertEqual(record["stage"], "flow")


if __name__ == "__main__":
    unittest.main()
