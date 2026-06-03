"""Sync receipt + Ralph-deferral schema tests (fn-52.1, R11 + R12).

Asserts:
  * `sync receipt` writes `type: "sync"` + a status from the enum
    {pushed,pulled,merged,updated,diverged,queued,errored,noop}, records each
    body merge for rollback, and lands at a path the review-receipt guard does
    NOT validate (no `receipts/` substring; not REVIEW_RECEIPT_PATH).
  * The ralph-guard's review-receipt validator REJECTS a sync receipt
    (missing/invalid verdict) — proving the distinct namespace is load-bearing
    — and its shell-write detector does NOT match a write to `.flow/sync-runs/`.
  * An invalid status is rejected by the handler.
  * `sync defer` appends a genuine conflict to the deferred-decisions sink and
    never blocks (no SystemExit), so an autonomous loop keeps running.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"
RALPH_GUARD_PY = HERE.parent.parent / "scripts" / "hooks" / "ralph-guard.py"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class TrackerReceiptTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self.flowctl = _load_module("flowctl_tracker_receipt_under_test", FLOWCTL_PY)
        self.guard = _load_module("ralph_guard_under_test", RALPH_GUARD_PY)
        self._call(func=self.flowctl.cmd_init)
        self.spec_id = self._call(
            func=self.flowctl.cmd_spec_create, title="Receipt subject", branch=None
        )["id"]

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _call(self, *, func, **kwargs) -> dict:
        kwargs.setdefault("json", True)
        ns = argparse.Namespace(**kwargs)
        buf = io.StringIO()
        with redirect_stdout(buf):
            func(ns)
        out = buf.getvalue().strip()
        return json.loads(out) if out else {}

    def _receipt(self, status: str, **kw) -> dict:
        return self._call(
            func=self.flowctl.cmd_sync_receipt,
            id=self.spec_id,
            status=status,
            tracker_id=kw.get("tracker_id"),
            transport=kw.get("transport"),
            merges_file=kw.get("merges_file"),
            note=kw.get("note"),
        )

    # --- receipt schema -----------------------------------------------------

    def test_receipt_writes_type_sync_and_status(self) -> None:
        res = self._receipt("pushed", tracker_id="uuid-x", transport="graphql")
        self.assertEqual(res["status"], "pushed")
        self.assertEqual(res["type"], "sync")
        data = json.loads(Path(res["receipt"]).read_text(encoding="utf-8"))
        self.assertEqual(data["type"], "sync")
        self.assertEqual(data["status"], "pushed")
        self.assertEqual(data["id"], self.spec_id)
        self.assertEqual(data["tracker_id"], "uuid-x")
        self.assertEqual(data["transport"], "graphql")
        self.assertIn("timestamp", data)

    def test_receipt_status_enum_covers_all_states(self) -> None:
        expected = {
            "pushed",
            "pulled",
            "merged",
            "updated",
            "diverged",
            "queued",
            "errored",
            "noop",
        }
        self.assertEqual(self.flowctl.TRACKER_RECEIPT_STATES, expected)
        for status in sorted(expected):
            res = self._receipt(status)
            self.assertEqual(res["status"], status)

    def test_receipt_records_merges_for_rollback(self) -> None:
        merges_path = self.tmpdir / "merges.json"
        merges_path.write_text(
            json.dumps(
                [
                    {"section": "Goal", "resolution": "auto-merged"},
                    {"section": "Acceptance", "resolution": "flow-wins"},
                ]
            ),
            encoding="utf-8",
        )
        res = self._receipt("merged", merges_file=str(merges_path))
        self.assertEqual(res["merges"], 2)
        data = json.loads(Path(res["receipt"]).read_text(encoding="utf-8"))
        self.assertEqual(len(data["merges"]), 2)
        self.assertEqual(data["merges"][0]["section"], "Goal")

    def test_receipt_rejects_invalid_status(self) -> None:
        with self.assertRaises(SystemExit):
            self._receipt("bogus")

    # --- guard isolation (R12: distinct path/type) --------------------------

    def test_receipt_path_is_guard_safe(self) -> None:
        res = self._receipt("noop")
        receipt_path = res["receipt"]
        # No `receipts/` substring → the guard's shell-write detector won't fire.
        self.assertNotIn("receipts/", receipt_path)
        self.assertIn(".flow/sync-runs/", receipt_path.replace(os.sep, "/"))
        self.assertFalse(
            self.guard.is_receipt_write_command(f"echo x > {receipt_path}", "")
        )

    def test_review_guard_would_reject_sync_receipt(self) -> None:
        # The review-receipt validator demands a SHIP/NEEDS_WORK/MAJOR_RETHINK
        # verdict; a sync receipt has none. Proves WHY the sync receipt needs a
        # path the guard never inspects.
        res = self._receipt("pulled")
        err = self.guard.validate_receipt_file(res["receipt"])
        self.assertTrue(err, "sync receipt should not validate as a review receipt")

    # --- Ralph deferral (R11) -----------------------------------------------

    def test_defer_queues_conflict_and_never_blocks(self) -> None:
        res = self._call(
            func=self.flowctl.cmd_sync_defer,
            id=self.spec_id,
            summary="Both sides rewrote Goal differently",
            suggested=None,
            reason=None,
            branch="feature-x",
        )
        self.assertTrue(res["queued"])
        sink = Path(res["sink_path"])
        self.assertTrue(sink.exists())
        body = sink.read_text(encoding="utf-8")
        self.assertIn("tracker-sync", body)
        self.assertIn("Both sides rewrote Goal differently", body)

    def test_defer_appends_across_runs(self) -> None:
        for summary in ("First conflict", "Second conflict"):
            self._call(
                func=self.flowctl.cmd_sync_defer,
                id=self.spec_id,
                summary=summary,
                suggested=None,
                reason=None,
                branch="feature-y",
            )
        sink = self.tmpdir / ".flow" / "review-deferred" / "feature-y.md"
        body = sink.read_text(encoding="utf-8")
        self.assertIn("First conflict", body)
        self.assertIn("Second conflict", body)


if __name__ == "__main__":
    unittest.main()
