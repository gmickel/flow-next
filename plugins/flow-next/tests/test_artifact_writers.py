"""Exercise the prospect/QA JSON writers through their installed CLI boundary."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

FLOWCTL = Path(__file__).resolve().parents[1] / "scripts/flowctl.py"


class ArtifactWritersTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = {k: v for k, v in os.environ.items() if k not in ("FLOW_STATE_DIR", "REVIEW_RECEIPT_PATH")}
        for command in (["git", "init", "-q"], ["git", "-c", "user.name=Test", "-c", "user.email=test@example.test", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "--allow-empty", "-qm", "base"]):
            subprocess.run(command, cwd=self.root, env=self.env, check=True, capture_output=True)
        self.cli("init")

    def cli(self, *args, data=None, code=0):
        argv = [sys.executable, str(FLOWCTL), *args]
        if data is not None:
            path = self.root / "payload.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            argv += ["--from-json", str(path)]
        result = subprocess.run(argv + ["--json"], cwd=self.root, env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_prospect_counts_collision_and_all_errors(self):
        data = self.cli("prospect", "write", "--skeleton")
        data["ranked"]["high_leverage"] = [{"position": 1, "title": "Improve", "summary": "A change", "leverage": "Small-diff lever because X; impact lands on Y.", "size": "S"}]
        data["drops"] = [{"title": "No", "taxonomy": "other", "reason": "No evidence"}]
        first = self.cli("prospect", "write", data=data)
        second = self.cli("prospect", "write", data=data)
        self.assertEqual(first["volume"], 2)
        self.assertEqual(first["rejection_rate"], .5)
        self.assertEqual(second["artifact_id"], first["artifact_id"] + "-2")
        self.assertIn("#### 1. Improve", Path(first["path"]).read_text())
        data["ranked"]["high_leverage"] = [{}, None]
        data["drops"] = [{}]
        error = self.cli("prospect", "write", data=data, code=2)
        self.assertGreaterEqual(len(error["errors"]), 8)
        self.assertEqual(len(list((self.root / ".flow/prospects").glob("*.md"))), 2)

    def test_qa_receipt_accepts_tracker_spec_id(self):
        result = self.cli("qa", "receipt", data={"id": "wor-12", "qa_outcome": "SHIP", "findings": [], "rid_coverage": {"rids": []}})
        self.assertEqual(json.loads(Path(result["receipt"]).read_text())["id"], "wor-12")

    def test_qa_carryover_and_invalid_payload_preserves_receipt(self):
        data = {"id": "fn-1-example", "qa_outcome": "NEEDS_WORK", "findings": [{"id": "bug-one", "severity": "P1", "confidence": 100, "classification": "introduced", "reason": 'quoted "snow" 雪', "file": "app.py:1"}], "rid_coverage": {"rids": [{"id": "R1", "coverage": "live"}]}}
        result = self.cli("qa", "receipt", data=data)
        path = Path(result["receipt"])
        first = json.loads(path.read_text())
        self.assertEqual(first["rid_coverage"]["covered"], 1)
        self.assertEqual(len(first["findings"]["items"]), 1)
        data.update(qa_outcome="BLOCKED", findings=[], blocked_reason="no app")
        self.cli("qa", "receipt", data=data)
        blocked = json.loads(path.read_text())
        self.assertEqual(blocked["findings"]["items"][0]["status"], "not_fixed")
        self.assertEqual(blocked["findings"]["round"], 2)
        before = path.read_bytes()
        data.update(qa_outcome="oops", findings=[{}, None], rid_coverage={"rids": [{}]})
        error = self.cli("qa", "receipt", data=data, code=2)
        self.assertGreater(len(error["errors"]), 6)
        self.assertEqual(path.read_bytes(), before)
        data.update(qa_outcome="SHIP", findings=[], rid_coverage={})
        self.cli("qa", "receipt", data=data)
        self.assertEqual(json.loads(path.read_text())["findings"]["items"][0]["status"], "fixed")


if __name__ == "__main__":
    unittest.main()
