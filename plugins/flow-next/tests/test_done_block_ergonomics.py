"""fn-257 R18/R19: `done` / `block` evidence, lock, hint and output contracts.

R18: `done` warns on unknown evidence keys, rejects evidence carrying none of
commits/tests/prs, records the plan-sync skip stage line when planSync is off,
and `done` / `block` decide on status inside the task lock.
R19: error hints name the next step, a closed stdout pipe exits without a
traceback, and `atomic_write` retries a Windows sharing violation a bounded
number of times.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_done_block_ergonomics -q
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import flowctl  # noqa: E402

FLOWCTL_PY = SCRIPTS / "flowctl.py"
SPEC_ID = "fn-1-sample"
TASK_ID = f"{SPEC_ID}.1"
SKIP_LINE = "stage: plan-sync - skipped(config: planSync.enabled != true)"


class _Repo(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.state = self.root / "state"
        self.env = {**os.environ, "FLOW_STATE_DIR": str(self.state)}
        self.run_ok("init")
        self.run_ok("spec", "create", "--title", "Sample")
        self.run_ok("task", "create", "--spec", SPEC_ID, "--title", "T one")

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

    def done(self, evidence: str, summary: str = "- did it") -> subprocess.CompletedProcess:
        return self.run_cli(
            "done", TASK_ID, "--summary", summary, "--evidence", evidence
        )

    def status(self) -> str:
        return json.loads(self.run_ok("show", TASK_ID, "--json").stdout)["status"]

    def task_md(self) -> str:
        return (self.root / ".flow" / "tasks" / f"{TASK_ID}.md").read_text(
            encoding="utf-8"
        )


class DoneEvidenceTest(_Repo):
    def setUp(self) -> None:
        super().setUp()
        self.run_ok("start", TASK_ID)

    def test_unknown_key_warns_on_stderr_and_succeeds(self) -> None:
        result = self.done('{"commits": ["abc"], "commit": "abc"}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("commit", result.stderr)
        self.assertEqual(self.status(), "done")

    def test_base_commit_is_not_warned(self) -> None:
        result = self.done('{"commits": ["abc"], "base_commit": "def"}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("base_commit", result.stderr)

    def test_no_known_key_is_an_error(self) -> None:
        result = self.done('{"commit": "abc", "test": "pytest"}')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.status(), "in_progress")


class DonePlanSyncStageLineTest(_Repo):
    def setUp(self) -> None:
        super().setUp()
        self.run_ok("start", TASK_ID)

    def test_disabled_plan_sync_records_skip_line(self) -> None:
        self.assertEqual(self.done('{"commits": ["abc"]}').returncode, 0)
        self.assertEqual(self.task_md().count(SKIP_LINE), 1)

    def test_existing_plan_sync_line_is_not_duplicated(self) -> None:
        summary = "- did it\n\nstage: plan-sync - skipped(empty: no downstream todo tasks)"
        self.assertEqual(self.done('{"commits": ["abc"]}', summary).returncode, 0)
        self.assertNotIn(SKIP_LINE, self.task_md())
        self.assertEqual(self.task_md().count("stage: plan-sync"), 1)

    def test_enabled_plan_sync_records_nothing(self) -> None:
        self.run_ok("config", "set", "planSync.enabled", "true")
        self.assertEqual(self.done('{"commits": ["abc"]}').returncode, 0)
        self.assertNotIn("stage: plan-sync", self.task_md())


class StatusCheckedInsideLockTest(_Repo):
    """A status change made while the caller waits on the lock is honored."""

    def _race(self, *args: str, flip_to: str) -> subprocess.CompletedProcess:
        lock = self.state / "locks" / f"{TASK_ID}.lock"
        runtime = self.state / "tasks" / f"{TASK_ID}.state.json"
        with flowctl.cross_process_lock(lock):
            proc = subprocess.Popen(
                [sys.executable, str(FLOWCTL_PY), *args],
                cwd=self.root, env=self.env, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            time.sleep(1.5)  # let the command reach the lock wait
            data = json.loads(runtime.read_text(encoding="utf-8"))
            runtime.write_text(json.dumps({**data, "status": flip_to}), encoding="utf-8")
        out, err = proc.communicate(timeout=60)
        return subprocess.CompletedProcess(args, proc.returncode, out, err)

    def test_done_rechecks_status_under_lock(self) -> None:
        self.run_ok("start", TASK_ID)
        result = self._race(
            "done", TASK_ID, "--summary", "x", "--evidence", '{"commits": ["a"]}',
            flip_to="blocked",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.status(), "blocked")

    def test_block_rechecks_status_under_lock(self) -> None:
        self.run_ok("start", TASK_ID)
        reason = self.root / "reason.md"
        reason.write_text("stuck\n", encoding="utf-8")
        result = self._race("block", TASK_ID, "--reason-file", str(reason), flip_to="done")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.status(), "done")


class ErrorHintTest(_Repo):
    def test_done_on_todo_names_start_before_force(self) -> None:
        err = self.done('{"commits": ["a"]}').stderr
        start = err.find(f"flowctl start {TASK_ID}")
        self.assertGreaterEqual(start, 0, err)
        self.assertLess(start, err.find("--force"), err)

    def test_missing_task_names_listing_command(self) -> None:
        err = self.run_cli("show", f"{SPEC_ID}.9").stderr
        self.assertIn(f"flowctl tasks --spec {SPEC_ID}", err)

    def test_missing_spec_names_listing_command(self) -> None:
        err = self.run_cli("show", "fn-9-nope").stderr
        self.assertIn("flowctl specs", err)


class ClosedPipeTest(_Repo):
    def test_json_to_closed_pipe_has_no_traceback(self) -> None:
        proc = subprocess.Popen(
            [sys.executable, str(FLOWCTL_PY), "specs", "--json"],
            cwd=self.root, env=self.env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        proc.stdout.close()  # the reader goes away before flowctl writes
        with proc.stderr:
            err = proc.stderr.read()
        proc.wait(timeout=60)
        self.assertNotIn("Traceback", err)
        self.assertNotIn("BrokenPipeError", err)


class AtomicWriteRetryTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.target = Path(self._tmp.name) / "f.txt"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    @staticmethod
    def _sharing_violation() -> PermissionError:
        err = PermissionError(13, "The process cannot access the file")
        err.winerror = 32
        return err

    def test_retries_then_succeeds(self) -> None:
        real_replace = os.replace
        calls = []

        def flaky(src, dst):
            calls.append(src)
            if len(calls) < 3:
                raise self._sharing_violation()
            return real_replace(src, dst)

        with mock.patch.object(flowctl.os, "replace", flaky), \
                mock.patch.object(flowctl, "_sleep_secs"):
            flowctl.atomic_write(self.target, "ok\n")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "ok\n")
        self.assertEqual(len(calls), 3)

    def test_gives_up_with_the_original_error(self) -> None:
        err = self._sharing_violation()
        replace = mock.Mock(side_effect=err)
        with mock.patch.object(flowctl.os, "replace", replace), \
                mock.patch.object(flowctl, "_sleep_secs"):
            with self.assertRaises(PermissionError) as ctx:
                flowctl.atomic_write(self.target, "ok\n")
        self.assertIs(ctx.exception, err)
        self.assertGreater(replace.call_count, 1)
        self.assertLess(replace.call_count, 20)
        self.assertEqual(list(self.target.parent.iterdir()), [])

    def test_other_permission_errors_are_not_retried(self) -> None:
        replace = mock.Mock(side_effect=PermissionError(13, "denied"))
        with mock.patch.object(flowctl.os, "replace", replace):
            with self.assertRaises(PermissionError):
                flowctl.atomic_write(self.target, "ok\n")
        self.assertEqual(replace.call_count, 1)


if __name__ == "__main__":
    unittest.main()
