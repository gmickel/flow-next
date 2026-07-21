"""Cross-platform process-lock regressions for fn-122.2."""

from __future__ import annotations

import concurrent.futures
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
from typing import Optional
from unittest import mock


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl():
    spec = importlib.util.spec_from_file_location("flowctl_portable_locks", FLOWCTL_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


flowctl = _load_flowctl()


class KernelLockTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_lock_file_persists_after_release(self) -> None:
        lock = self.root / "locks" / "subject.lock"
        with flowctl.cross_process_lock(lock, timeout=0):
            self.assertTrue(lock.is_file())
        self.assertTrue(lock.is_file())

    def test_crashed_holder_is_recovered_by_kernel(self) -> None:
        lock = self.root / "locks" / "subject.lock"
        script = (
            "import importlib.util, pathlib, sys\n"
            f"p = pathlib.Path({str(FLOWCTL_PY)!r})\n"
            "s = importlib.util.spec_from_file_location('held_flowctl', p)\n"
            "m = importlib.util.module_from_spec(s); sys.modules[s.name] = m\n"
            "s.loader.exec_module(m)\n"
            f"with m.cross_process_lock(pathlib.Path({str(lock)!r})):\n"
            " print('ready', flush=True)\n"
            " sys.stdin.read()\n"
        )
        holder = subprocess.Popen(
            [sys.executable, "-c", script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(holder.stdout.readline().strip(), "ready")
            holder.kill()
            holder.communicate(timeout=5)
            with flowctl.cross_process_lock(lock, timeout=1):
                self.assertTrue(lock.is_file())
        finally:
            if holder.poll() is None:
                holder.kill()
            holder.communicate(timeout=5)

    def test_timeout_never_steals_a_live_lock(self) -> None:
        lock = self.root / "locks" / "subject.lock"
        with flowctl.cross_process_lock(lock, timeout=0):
            with self.assertRaises(flowctl.CrossProcessLockError) as raised:
                with flowctl.cross_process_lock(lock, timeout=0):
                    self.fail("live lock must not be stolen")
            self.assertIn("timed out acquiring live lock", str(raised.exception))
        self.assertTrue(lock.is_file())

    def test_non_file_lock_leaf_fails_explicitly(self) -> None:
        lock = self.root / "locks" / "subject.lock"
        lock.mkdir(parents=True)
        with self.assertRaises(flowctl.CrossProcessLockError) as raised:
            with flowctl.cross_process_lock(lock, timeout=0):
                self.fail("non-file leaf must not be accepted")
        self.assertIn("not a regular file", str(raised.exception))


class PortableLockSubprocessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(
            [sys.executable, str(FLOWCTL_PY), "init", "--json"],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _run(self, *args: str, env: Optional[dict] = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY), *args, "--json"],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
        )

    def test_parallel_start_has_exactly_one_actor_winner(self) -> None:
        spec = json.loads(
            self._run("spec", "create", "--title", "Runtime lock").stdout
        )["id"]
        task = json.loads(
            self._run("task", "create", "--spec", spec, "--title", "Claim me").stdout
        )["id"]

        def start(index: int) -> subprocess.CompletedProcess:
            env = os.environ.copy()
            env["FLOW_ACTOR"] = f"actor-{index}"
            return self._run("start", task, env=env)

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(start, range(16)))
        winners = [p for p in results if p.returncode == 0]
        self.assertEqual(len(winners), 1, [p.stdout + p.stderr for p in results])

        state_paths = list((self.repo / ".git" / "flow-state" / "tasks").glob("*.json"))
        self.assertEqual(len(state_paths), 1)
        state = json.loads(state_paths[0].read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "in_progress")
        winner_index = results.index(winners[0])
        self.assertEqual(state["assignee"], f"actor-{winner_index}")

    def test_parallel_setup_blocks_merge_hash_map_losslessly(self) -> None:
        meta = self.repo / ".flow" / "meta.json"
        first_template = self.repo / "first-template.md"
        second_template = self.repo / "second-template.md"
        first_template.write_text(
            "<!-- BEGIN FLOW-NEXT -->\nfirst\n<!-- END FLOW-NEXT -->\n",
            encoding="utf-8",
        )
        second_template.write_text(
            "<!-- BEGIN FLOW-NEXT -->\nsecond\n<!-- END FLOW-NEXT -->\n",
            encoding="utf-8",
        )

        def apply(target: str, template: Path) -> subprocess.CompletedProcess:
            return self._run(
                "setup-block",
                "apply",
                "--file",
                target,
                "--template",
                str(template),
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(apply, "CLAUDE.md", first_template),
                pool.submit(apply, "AGENTS.md", second_template),
            ]
            results = [future.result() for future in futures]
        self.assertTrue(all(p.returncode == 0 for p in results), results)
        hashes = json.loads(meta.read_text(encoding="utf-8"))["setup"]["block_hashes"]
        self.assertEqual(set(hashes), {"CLAUDE.md", "AGENTS.md"})

    def test_runtime_lock_timeout_uses_json_error_contract(self) -> None:
        spec = json.loads(
            self._run("spec", "create", "--title", "Timeout contract").stdout
        )["id"]
        task = json.loads(
            self._run("task", "create", "--spec", spec, "--title", "Hold me").stdout
        )["id"]
        lock = self.repo / ".git" / "flow-state" / "locks" / f"{task}.lock"
        previous_cwd = Path.cwd()
        output = io.StringIO()
        try:
            os.chdir(self.repo)
            with flowctl.cross_process_lock(lock), mock.patch.object(
                flowctl, "CROSS_PROCESS_LOCK_WAIT_SECS", 0.0
            ), mock.patch.object(sys, "argv", ["flowctl", "start", task, "--json"]), contextlib.redirect_stdout(output):
                with self.assertRaises(SystemExit) as raised:
                    flowctl.main()
            self.assertEqual(raised.exception.code, 1)
        finally:
            os.chdir(previous_cwd)
        payload = json.loads(output.getvalue())
        self.assertFalse(payload["success"])
        self.assertIn("Runtime lock unavailable", payload["error"])
        self.assertNotIn("Traceback", output.getvalue())


if __name__ == "__main__":
    unittest.main()
