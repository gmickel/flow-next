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

    def test_qa_receipt_ignores_a_legacy_resolved_feature(self):
        # fn-274 R4: a payload from before the field was removed still writes.
        data = {"id": "fn-1-example", "qa_outcome": "SHIP", "findings": [], "rid_coverage": {"rids": []},
                "resolved_feature": "unmapped"}
        path = Path(self.cli("qa", "receipt", data=data)["receipt"])
        self.assertNotIn("resolved_feature", json.loads(path.read_text()))

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

    def test_qa_receipt_extends_a_legacy_rp_mode_receipt(self):
        # A receipt-driven QA receipt written before 8.0.0 records mode "rp";
        # the next one (mode "receipt") still supersedes it.
        target = str(self.root / "qa-receipt.json")
        data = {"id": "fn-1-example", "qa_outcome": "NEEDS_WORK", "mode": "rp", "findings": [{"id": "bug-one", "severity": "P1", "confidence": 100, "classification": "introduced", "reason": "broken", "file": "app.py:1"}], "rid_coverage": {"rids": []}}
        self.cli("qa", "receipt", "--receipt", target, data=data)
        legacy = json.loads(Path(target).read_text())
        del data["mode"]
        self.cli("qa", "receipt", "--receipt", target, data=data)
        current = json.loads(Path(target).read_text())
        self.assertEqual((legacy["mode"], current["mode"]), ("rp", "receipt"))
        self.assertEqual(current["findings"]["round"], 2)
        self.assertEqual(current["findings"]["supersedesReceiptId"], legacy["findings"]["sourceReceiptId"])
        self.assertEqual(current["findings"]["items"][0]["status"], "not_fixed")

    def test_qa_receipt_without_findings_writes_needs_work_and_blocked(self):
        # 7.1.1 refused these with "QA findings could not be parsed; receipt unchanged".
        for outcome, extra in (("NEEDS_WORK", {}), ("BLOCKED", {"blocked_reason": "no app to drive"})):
            data = {"id": f"fn-2-{outcome.lower().replace('_', '-')}", "qa_outcome": outcome, "findings": [],
                    "rid_coverage": {"rids": [{"id": "R1", "coverage": "no_live_scenario"}]}, **extra}
            receipt = json.loads(Path(self.cli("qa", "receipt", data=data)["receipt"]).read_text())
            self.assertEqual(receipt["qa_outcome"], outcome)
            self.assertEqual(receipt["verdict"], "NEEDS_WORK")
            self.assertEqual(receipt["findings"]["items"], [])

    def commit(self):
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.test", "-c", "commit.gpgsign=false",
                        "-c", "core.hooksPath=/dev/null", "commit", "--allow-empty", "-qm", "fix"],
                       cwd=self.root, env=self.env, check=True, capture_output=True)
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def test_qa_receipt_carries_prior_passes_with_their_head_and_evidence(self):
        first = {"id": "fn-3-shop", "qa_outcome": "NEEDS_WORK", "findings": [{"id": "coupon-expired", "severity": "P1", "confidence": 100, "classification": "introduced", "reason": "accepted", "file": "coupon"}],
                 "rid_coverage": {"rids": [{"id": "R1", "coverage": "live"}, {"id": "R2", "coverage": "live"}]},
                 "scenarios": [{"id": "S1 add to cart", "rids": ["R1"], "outcome": "PASS", "run": "live", "evidence": ["qa/s1.png"]},
                               {"id": "S2 expired coupon", "rids": ["R2"], "outcome": "FAIL", "run": "live", "evidence": ["qa/s2.png"]}]}
        path = Path(self.cli("qa", "receipt", data=first)["receipt"])
        prior = json.loads(path.read_text())
        self.assertEqual({row["head_sha"] for row in prior["scenarios"]}, {prior["head_sha"]})
        new_head = self.commit()
        second = {"id": "fn-3-shop", "qa_outcome": "SHIP", "findings": [],
                  "rid_coverage": {"rids": [{"id": "R1", "coverage": "carried"}, {"id": "R2", "coverage": "live"}]},
                  "scenarios": [{"id": "S1 add to cart", "run": "carried"},
                                {"id": "S2 expired coupon", "rids": ["R2"], "outcome": "PASS", "run": "live", "evidence": ["qa/s2-fixed.png"]}]}
        self.cli("qa", "receipt", data=second)
        receipt = json.loads(path.read_text())
        carried, live = receipt["scenarios"]
        self.assertEqual(carried, {"id": "S1 add to cart", "rids": ["R1"], "outcome": "PASS", "run": "carried",
                                   "evidence": ["qa/s1.png"], "head_sha": prior["head_sha"]})
        self.assertEqual((live["run"], live["head_sha"]), ("live", new_head))
        self.assertEqual(receipt["rid_coverage"]["covered"], 2)
        self.commit()
        self.cli("qa", "receipt", data={**second, "scenarios": [{"id": "S1 add to cart", "run": "carried"}]})
        self.assertEqual(json.loads(path.read_text())["scenarios"][0]["head_sha"], prior["head_sha"])

    def test_qa_receipt_refuses_a_carry_the_prior_receipt_does_not_back(self):
        base = {"id": "fn-4-shop", "qa_outcome": "SHIP", "findings": [], "rid_coverage": {"rids": []}}
        carry = lambda *ids: {**base, "scenarios": [{"id": i, "run": "carried"} for i in ids]}
        path = self.root / ".flow/review-receipts/qa-fn-4-shop.json"
        self.assertIn("no prior receipt", json.dumps(self.cli("qa", "receipt", data=carry("S1"), code=2)))
        self.assertFalse(path.exists())
        self.cli("qa", "receipt", data={**base, "scenarios": [
            {"id": "S1", "outcome": "FAIL", "run": "live"}, {"id": "S2", "outcome": "PASS", "run": "live"}]})
        self.assertIn("did not pass", json.dumps(self.cli("qa", "receipt", data=carry("S1"), code=2)))
        self.assertIn("not in the prior receipt", json.dumps(self.cli("qa", "receipt", data=carry("S9"), code=2)))
        self.assertIn("same head", json.dumps(self.cli("qa", "receipt", data=carry("S2"), code=2)))
        self.commit()
        subprocess.run(["git", "checkout", "-qb", "other"], cwd=self.root, env=self.env, check=True)
        self.assertIn("another branch", json.dumps(self.cli("qa", "receipt", data=carry("S2"), code=2)))
        before = path.read_bytes()
        error = self.cli("qa", "receipt", data={**base, "scenarios": [{"id": "S3", "outcome": "MAYBE", "run": "live"}, {"run": "replayed"}]}, code=2)
        self.assertGreaterEqual(len(error["errors"]), 2)
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
