"""Unit tests for the migrate-rename lockfile primitive (fn-43.17 / R8 + R32).

Covers the cross-platform `os.mkdir(".flow/.migrating")` lockfile that gates
parallel `flowctl migrate-rename` invocations. The mkdir is atomic on both
POSIX and Windows; the PID file inside lets crashed peers be reclaimed.

Run:
    python3 -m unittest plugins.flow-next.tests.test_lockfile -v

Scenarios covered:
  - Atomic mkdir succeeds on first call; PID file written inside.
  - Second concurrent invocation hits FileExistsError; live holder forces wait
    + eventual error after `MIGRATE_LOCK_WAIT_SECS`.
  - Stale PID (process gone) reclaim succeeds (POSIX path: ProcessLookupError).
  - Live foreign-user PID (POSIX `PermissionError`) is treated as alive — wait.
  - Windows path (`OpenProcess` ctypes) — dead pid (handle == 0) reclaims; live
    pid (handle non-null + STILL_ACTIVE) waits.
  - PID-grace window — lock dir present without PID file, age < grace → wait;
    age >= grace → reclaim.
  - Release deletes both the pid file and the lock dir; idempotent on repeat.

The cross-platform PID-liveness branch is parametrized: POSIX paths use mocks
on `os.kill`, Windows paths mock `ctypes.WinDLL` and friends. The Windows
path runs on POSIX runners (we only stub the ctypes layer) so the OS-specific
branch is exercised on every CI matrix slot.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest import mock


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_lockfile_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


def _make_flow_dir(tmp_path: Path) -> Path:
    flow_dir = tmp_path / ".flow"
    flow_dir.mkdir()
    return flow_dir


# --- Atomic mkdir + PID-file invariants ---------------------------------


class TestAcquireLockBasic(unittest.TestCase):
    """`os.mkdir` is the atomic-create gate; PID is written inside."""

    def setUp(self) -> None:
        self._tmp = Path(__file__).resolve().parent / f"_tmp_lockbasic_{os.getpid()}"
        self._tmp.mkdir(exist_ok=True)
        self.flow_dir = _make_flow_dir(self._tmp)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_first_acquire_creates_lockdir_with_pid(self) -> None:
        lock_dir = flowctl._migrate_acquire_lock(self.flow_dir, use_json=False)
        try:
            self.assertTrue(lock_dir.exists())
            self.assertEqual(lock_dir.name, flowctl.MIGRATE_LOCK_DIR)
            pid_file = lock_dir / "pid"
            self.assertTrue(pid_file.exists())
            self.assertEqual(int(pid_file.read_text(encoding="utf-8").strip()), os.getpid())
        finally:
            flowctl._migrate_release_lock(lock_dir)

    def test_release_removes_lockdir_and_pid(self) -> None:
        lock_dir = flowctl._migrate_acquire_lock(self.flow_dir, use_json=False)
        flowctl._migrate_release_lock(lock_dir)
        self.assertFalse(lock_dir.exists())

    def test_release_idempotent(self) -> None:
        lock_dir = flowctl._migrate_acquire_lock(self.flow_dir, use_json=False)
        flowctl._migrate_release_lock(lock_dir)
        # Second release: no exception even though dir is gone.
        flowctl._migrate_release_lock(lock_dir)


# --- Live-holder contention forces wait + error ----------------------------


class TestAcquireLockContention(unittest.TestCase):
    """When the holder is alive, second acquire waits then errors out."""

    def setUp(self) -> None:
        self._tmp = Path(__file__).resolve().parent / f"_tmp_lockconten_{os.getpid()}"
        self._tmp.mkdir(exist_ok=True)
        self.flow_dir = _make_flow_dir(self._tmp)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_live_holder_waits_then_errors_after_deadline(self) -> None:
        # Pre-create the lock dir + pid file with a "live" pid (we'll mock
        # `_migrate_pid_alive` to return True so it's treated as alive).
        lock_dir = self.flow_dir / flowctl.MIGRATE_LOCK_DIR
        lock_dir.mkdir()
        (lock_dir / "pid").write_text("99999", encoding="utf-8")

        # Fake monotonic clock: each call advances by 60s so the deadline (30s)
        # is exceeded immediately on the second iteration. Avoids real sleep.
        time_seq = iter([0.0, 0.0, 60.0, 60.0, 120.0])
        with (
            mock.patch.object(flowctl, "_migrate_pid_alive", return_value=True),
            mock.patch.object(flowctl, "_migrate_sleep", lambda _s: None),
            mock.patch.object(flowctl, "_monotonic_now", lambda: next(time_seq)),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            with self.assertRaises(SystemExit) as cm:
                flowctl._migrate_acquire_lock(self.flow_dir, use_json=False)
        # error_exit returns code=1 by default for this path.
        self.assertEqual(cm.exception.code, 1)


# --- Stale-PID reclaim — POSIX branch ------------------------------------


@unittest.skipIf(sys.platform == "win32", "POSIX-only os.kill semantics")
class TestStalePidReclaimPOSIX(unittest.TestCase):
    """POSIX: `os.kill(pid, 0)` raises ProcessLookupError when pid is gone."""

    def setUp(self) -> None:
        self._tmp = Path(__file__).resolve().parent / f"_tmp_lockstale_{os.getpid()}"
        self._tmp.mkdir(exist_ok=True)
        self.flow_dir = _make_flow_dir(self._tmp)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_dead_pid_reclaim_succeeds(self) -> None:
        lock_dir = self.flow_dir / flowctl.MIGRATE_LOCK_DIR
        lock_dir.mkdir()
        (lock_dir / "pid").write_text("99999", encoding="utf-8")

        # Mock os.kill to raise ProcessLookupError → liveness probe says dead.
        def fake_kill(pid: int, sig: int) -> None:
            raise ProcessLookupError(f"no such process {pid}")

        with mock.patch("os.kill", side_effect=fake_kill):
            new_lock = flowctl._migrate_acquire_lock(self.flow_dir, use_json=False)
        try:
            self.assertTrue(new_lock.exists())
            # Our PID is now in the file (we reclaimed and re-acquired).
            self.assertEqual(
                int((new_lock / "pid").read_text(encoding="utf-8").strip()),
                os.getpid(),
            )
        finally:
            flowctl._migrate_release_lock(new_lock)

    def test_live_foreign_pid_treated_as_alive(self) -> None:
        """`PermissionError` from os.kill means PID exists but unsignalable."""
        lock_dir = self.flow_dir / flowctl.MIGRATE_LOCK_DIR
        lock_dir.mkdir()
        (lock_dir / "pid").write_text("99999", encoding="utf-8")

        def fake_kill(pid: int, sig: int) -> None:
            raise PermissionError(f"not permitted to signal {pid}")

        time_seq = iter([0.0, 0.0, 60.0, 60.0, 120.0])
        with (
            mock.patch("os.kill", side_effect=fake_kill),
            mock.patch.object(flowctl, "_migrate_sleep", lambda _s: None),
            mock.patch.object(flowctl, "_monotonic_now", lambda: next(time_seq)),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            with self.assertRaises(SystemExit):
                flowctl._migrate_acquire_lock(self.flow_dir, use_json=False)

    def test_pid_alive_helper_zero_or_negative(self) -> None:
        """`_migrate_pid_alive(<=0)` is False — defensive contract."""
        self.assertFalse(flowctl._migrate_pid_alive(0))
        self.assertFalse(flowctl._migrate_pid_alive(-1))


# --- Stale-PID reclaim — Windows branch ----------------------------------


class TestStalePidReclaimWindows(unittest.TestCase):
    """Windows path: `OpenProcess` returns NULL (dead) or non-null + STILL_ACTIVE.

    We patch `sys.platform` and `ctypes.WinDLL` so the Windows-only branch is
    exercised on POSIX CI runners. ctypes itself is a stdlib module on every
    supported platform.
    """

    def test_windows_dead_pid_returns_false(self) -> None:
        """OpenProcess returns 0 (NULL handle) → process is gone → dead."""
        import ctypes
        from ctypes import wintypes  # noqa: F401 — only used to satisfy attr lookup

        fake_kernel32 = mock.MagicMock()
        # OpenProcess returns 0 (NULL handle).
        fake_kernel32.OpenProcess.return_value = 0
        with (
            mock.patch.object(sys, "platform", "win32"),
            mock.patch("ctypes.WinDLL", return_value=fake_kernel32, create=True),
        ):
            self.assertFalse(flowctl._migrate_pid_alive(99999))

    def test_windows_live_pid_returns_true(self) -> None:
        """OpenProcess returns a non-null handle + GetExitCodeProcess says STILL_ACTIVE."""
        self._run_windows_branch(open_handle=0xDEADBEEF, exit_code_value=259, expected=True)

    def test_windows_exited_pid_returns_false(self) -> None:
        """Non-null handle + exit code != STILL_ACTIVE → dead."""
        self._run_windows_branch(open_handle=0xDEADBEEF, exit_code_value=0, expected=False)

    def _run_windows_branch(
        self, *, open_handle: int, exit_code_value: int, expected: bool
    ) -> None:
        """Drive _migrate_pid_alive through the Windows branch with controlled
        OpenProcess + GetExitCodeProcess return shapes.

        We need real ctypes types (OpenProcess.restype assignment expects a
        ctypes type, not a MagicMock attribute), so we fake just the function
        call results. GetExitCodeProcess gets called with `ctypes.byref(dword)`;
        we wire the side_effect to reach into the real DWORD object via the
        cell our patched byref captures.
        """
        import ctypes
        from ctypes import wintypes

        # Capture the DWORD that the helper allocates so our side_effect can
        # mutate it to express liveness/exitcode. ctypes.byref returns an
        # opaque object — but the underlying object reference is preserved on
        # the .contents attribute of a POINTER. Use a list-cell to capture.
        captured: dict[str, ctypes.c_uint32] = {}

        original_byref = ctypes.byref

        def capturing_byref(obj):
            # obj is the real DWORD; remember it.
            captured["dword"] = obj
            return original_byref(obj)

        def fake_get_exit_code(handle, lp_exit_code):
            captured["dword"].value = exit_code_value
            return 1  # nonzero = success

        # Build a kernel32 fake. Function-attr assignments (.restype/.argtypes)
        # need to be settable; MagicMock attributes accept assignment by default.
        fake_kernel32 = mock.MagicMock()
        fake_kernel32.OpenProcess.return_value = open_handle
        fake_kernel32.GetExitCodeProcess.side_effect = fake_get_exit_code
        fake_kernel32.CloseHandle.return_value = 1

        with (
            mock.patch.object(sys, "platform", "win32"),
            mock.patch("ctypes.WinDLL", return_value=fake_kernel32, create=True),
            mock.patch("ctypes.byref", side_effect=capturing_byref),
        ):
            self.assertEqual(flowctl._migrate_pid_alive(99999), expected)


# --- PID-grace window for crashed-mid-write peers ------------------------


class TestPidGraceWindow(unittest.TestCase):
    """Lock-dir present + no pid file → reclaim only after grace expires."""

    def setUp(self) -> None:
        self._tmp = Path(__file__).resolve().parent / f"_tmp_lockgrace_{os.getpid()}"
        self._tmp.mkdir(exist_ok=True)
        self.flow_dir = _make_flow_dir(self._tmp)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_lockdir_without_pid_within_grace_waits(self) -> None:
        """Fresh lock-dir without pid — crashed peer hypothesis only kicks in
        after grace expires. Within the grace window we wait."""
        lock_dir = self.flow_dir / flowctl.MIGRATE_LOCK_DIR
        lock_dir.mkdir()
        # No pid file. mtime is "now" → age == 0s, < MIGRATE_LOCK_PID_GRACE_SECS.

        time_seq = iter([0.0, 0.0, 60.0, 60.0, 120.0])
        with (
            mock.patch.object(flowctl, "_migrate_sleep", lambda _s: None),
            mock.patch.object(flowctl, "_monotonic_now", lambda: next(time_seq)),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            with self.assertRaises(SystemExit):
                # Within the grace window we never reclaim → loop runs to deadline.
                flowctl._migrate_acquire_lock(self.flow_dir, use_json=False)

    def test_lockdir_without_pid_past_grace_reclaims(self) -> None:
        """Old lock-dir without pid → past grace → reclaim succeeds."""
        lock_dir = self.flow_dir / flowctl.MIGRATE_LOCK_DIR
        lock_dir.mkdir()
        # Backdate the lock dir so its mtime is older than the grace window.
        old = (
            os.path.getmtime(self.flow_dir)
            - (flowctl.MIGRATE_LOCK_PID_GRACE_SECS + 30)
        )
        os.utime(lock_dir, (old, old))

        new_lock = flowctl._migrate_acquire_lock(self.flow_dir, use_json=False)
        try:
            self.assertTrue(new_lock.exists())
            self.assertEqual(
                int((new_lock / "pid").read_text(encoding="utf-8").strip()),
                os.getpid(),
            )
        finally:
            flowctl._migrate_release_lock(new_lock)


if __name__ == "__main__":
    unittest.main()
