"""Unattended config, receipt, and concurrent sidecar regression coverage."""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

FLOWCTL = Path(__file__).resolve().parents[1] / "scripts" / "flowctl.py"
spec = importlib.util.spec_from_file_location("flowctl_unattended_under_test", FLOWCTL)
f = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = f
spec.loader.exec_module(f)


class UnattendedCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.flow = self.root / ".flow"
        for directory in ("specs", "tasks", "memory"):
            (self.flow / directory).mkdir(parents=True)
        self.spec_id = "fn-1-demo"
        self.sidecar = self.flow / "specs" / f"{self.spec_id}.json"
        self.sidecar.write_text(json.dumps({"id": self.spec_id, "status": "open", "title": "Demo"}), encoding="utf-8")
        (self.flow / "meta.json").write_text(json.dumps({"schema_version": f.SCHEMA_VERSION}), encoding="utf-8")
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(f, "get_flow_dir", return_value=self.flow).start()
        mock.patch.object(f, "get_repo_root", return_value=self.root).start()

    def test_bad_config_is_preserved_and_validation_reports_root_error(self):
        path = self.flow / "config.json"
        bad = b'{"memory": {},}\n'
        path.write_bytes(bad)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as raised:
                f.cmd_config_set(argparse.Namespace(key="memory.enabled", value="true", json=False))
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(path.read_bytes(), bad)
        self.assertIn(str(path), err.getvalue())
        self.assertIn("line 1 column", err.getvalue())
        errors = f.validate_flow_root(self.flow)
        self.assertTrue(any(str(path) in error and "line 1 column" in error for error in errors))

    def test_tracker_spec_lock_is_the_review_sidecar_lock(self):
        from flowctl_tracker.lifecycle import helpers

        for spec_id in (self.spec_id, "wor-17-x", "fn-2"):
            with self.subTest(spec_id=spec_id):
                self.assertEqual(helpers.spec_sidecar_lock_path(self.flow, spec_id),
                                 f._review_sidecar_lock_path(self.flow, spec_id))
        self.assertEqual(helpers.SPEC_SIDECAR_LOCK_WAIT_SECS, f.CROSS_PROCESS_LOCK_WAIT_SECS)

    def test_standalone_config_reader_matches_tracker_config_io(self):
        # A copied flowctl without the tracker package reads config through its own
        # fallback; it must classify every file exactly as config_io does.
        from flowctl_tracker import config_io

        path = self.flow / "config.json"
        cases = {"missing": None, "valid": '{"a": 1}', "not-object": "[]",
                 "bad-json": '{"a": 1,}', "empty": ""}
        for name, body in cases.items():
            with self.subTest(case=name):
                path.unlink(missing_ok=True)
                if body is not None:
                    path.write_text(body, encoding="utf-8")
                results = []
                for reader in (config_io.read_config_file, None):
                    try:
                        if reader is None:
                            with mock.patch.dict(sys.modules, {"flowctl_tracker.config_io": None}):
                                results.append(("ok", f._read_flow_config_file(path)))
                        else:
                            results.append(("ok", reader(path)))
                    except ValueError as exc:
                        results.append(("error", str(exc)))
                self.assertEqual(results[0], results[1])

    def test_invalid_read_warns_once_and_missing_retains_defaults(self):
        path = self.flow / "config.json"
        self.assertIsNone(f._load_raw_flow_config())
        path.write_text("[]", encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(f._load_raw_flow_config(), {})
            self.assertEqual(f._load_raw_flow_config(), {})
        self.assertEqual(err.getvalue().count("Warning:"), 1)
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            f.set_config("memory.enabled", "true")
        self.assertEqual(path.read_text(encoding="utf-8"), "[]")

    def _record(self, output, payload):
        output_path, payload_path = self.root / "output.md", self.root / "payload.json"
        output_path.write_text(output, encoding="utf-8")
        payload_path.write_text(json.dumps(payload), encoding="utf-8")
        args = argparse.Namespace(id=self.spec_id, kind="plan", task=None, review_type="plan", backend="rp",
                                  output_file=str(output_path), exit_code=0, failure_class=None,
                                  receipt_target=str(self.root / "receipt.json"), receipt_payload_file=str(payload_path), json=True)
        with mock.patch.object(f, "record_review_attempt", return_value={}) as record, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                f.cmd_review_rounds_record(args)
            except SystemExit as exc:
                return exc.code, record
        return 0, record

    def test_record_rejects_contradictory_fields_before_any_state_change(self):
        output = '<verdict>NEEDS_WORK</verdict>\nClassification counts: 1 introduced, 0 pre_existing.\n'
        before = self.sidecar.read_bytes()
        for payload in ({"verdict": "SHIP"}, {"introduced_count": 0}, {"unaddressed": ["R1"]}):
            with self.subTest(payload=payload):
                code, record = self._record(output, payload)
                self.assertEqual(code, 2)
                record.assert_not_called()
                self.assertEqual(self.sidecar.read_bytes(), before)

    def test_record_derives_tallies_and_suffixed_ids_from_both_formats(self):
        outputs = [
            '<verdict>NEEDS_WORK</verdict>\nClassification counts: 1 introduced, 2 pre_existing.\nUnaddressed R-IDs: [R4a, R7]\n',
            '<verdict>NEEDS_WORK</verdict>\n```json\n' + json.dumps({"classification_counts": {"introduced": 1, "pre_existing": 2}, "suppressed_count": {"50": 3}, "unaddressed": ["R4a", "R7"]}) + '\n```\n',
        ]
        for output in outputs:
            with self.subTest(output=output):
                # A host payload embeds the review text; the recorded output wins.
                code, record = self._record(output, {"model": "reviewer", "review": output.rstrip()})
                self.assertEqual(code, 0)
                payload = record.call_args.kwargs["receipt_payload"]
                self.assertEqual(payload["verdict"], "NEEDS_WORK")
                self.assertEqual(payload["review"], output)
                self.assertEqual(payload["introduced_count"], 1)
                self.assertEqual(payload["pre_existing_count"], 2)
                self.assertEqual(payload["unaddressed"], ["R4a", "R7"])
                self.assertEqual(payload["model"], "reviewer")

    def test_blocked_only_route_stops_but_ready_task_proceeds(self):
        state = {"view": "live", "pr_exists": False, "status": "open", "tasks_total": 2,
                 "tasks_done": 1, "tasks_blocked": 1, "blocked_reasons": ["fn-1-demo.2: needs credentials"]}
        route = f.judge_route_lifecycle(state)
        self.assertEqual(route["value"], "host")
        self.assertIn("needs credentials", route["rule"])
        state["tasks_total"] = 3
        self.assertEqual(f.judge_route_lifecycle(state)["value"], "work_planned")

    def test_concurrent_branch_updates_preserve_every_review_reservation(self):
        # Two fresh interpreters exercise the actual cross-process lock. A
        # deliberate yield after the branch reader makes stale writes visible.
        script = '''
import argparse, importlib.util, pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(sys.argv[1]).parent))
spec = importlib.util.spec_from_file_location("flowctl_child", sys.argv[1])
f = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = f
spec.loader.exec_module(f)
root = pathlib.Path(sys.argv[2])
f.get_flow_dir = lambda: root / ".flow"
f.get_repo_root = lambda: root
original = f.load_json_or_exit
def slow(*a, **kw):
    result = original(*a, **kw)
    time.sleep(0.005)
    return result
f.load_json_or_exit = slow
for index in range(8):
    if sys.argv[3] == "branch":
        f.cmd_spec_set_branch(argparse.Namespace(id="fn-1-demo", branch="work-" + str(index), json=False))
    else:
        f.enforce_and_increment_review_cap("fn-1-demo", "plan", return_reservation=True)
'''
        env = dict(os.environ, MAX_REVIEW_ITERATIONS="30")
        children = [subprocess.Popen([sys.executable, "-c", script, str(FLOWCTL), str(self.root), mode],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=env)
                    for mode in ("branch", "round")]
        for child in children:
            out, err = child.communicate(timeout=40)
            self.assertEqual(child.returncode, 0, out + err)
        data = json.loads(self.sidecar.read_text(encoding="utf-8"))
        self.assertEqual(data["plan_review_rounds"], 8)
        self.assertEqual(data["review_pending_rounds"]["plan"], 8)
        self.assertEqual(len(data["review_reservations"]), 8)
        self.assertEqual(data["branch_name"], "work-7")

    def test_triage_preserves_open_needs_work_receipt(self):
        receipt = self.root / "review.json"
        original = '{"verdict":"NEEDS_WORK","id":"fn-1-demo.1"}\n'
        receipt.write_text(original, encoding="utf-8")
        args = argparse.Namespace(base="main", receipt=str(receipt), task="fn-1-demo.1", json=True,
                                  no_llm=True, backend=None, model=None, effort=None)
        result = subprocess.CompletedProcess([], 0, stdout="README.md\n", stderr="")
        with mock.patch.object(f.subprocess, "run", return_value=result), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                f.cmd_triage_skip(args)
        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(receipt.read_text(encoding="utf-8"), original)

    def test_triage_busy_receipt_lock_takes_full_review(self):
        receipt = self.root / "review.json"
        args = argparse.Namespace(base="main", receipt=str(receipt), task="fn-1-demo.1", json=True,
                                  no_llm=True, backend=None, model=None, effort=None)
        result = subprocess.CompletedProcess([], 0, stdout="README.md\n", stderr="")
        busy = mock.MagicMock(side_effect=f.CrossProcessLockError("timed out"))
        out = io.StringIO()
        with mock.patch.object(f.subprocess, "run", return_value=result), \
                mock.patch.object(f, "cross_process_lock", busy), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                f.cmd_triage_skip(args)
        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(json.loads(out.getvalue())["verdict"], "REVIEW")
        self.assertFalse(receipt.exists())


if __name__ == "__main__":
    unittest.main()
