"""fn-257 R17 - prime's bounded-probe helper kills the whole process group.

Every `run_bounded` definition in flow-next-prime/workflow.md is EXTRACTED and
EXECUTED (not copied): a probe that outlives its bound must take its whole
process tree down (a dev server started through npm/pnpm survives a kill aimed
at the `sh -c` wrapper and keeps the port and the output pipe), and must report
the timeout (exit 124 plus a `TIMEOUT` line) instead of passing its killed
exit status off as the probe's own result.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_prime_run_bounded -q
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
PRIME_WF = HERE.parent.parent / "skills" / "flow-next-prime" / "workflow.md"

SHELLS = [s for s in ("bash", "zsh") if shutil.which(s)]


def _definitions() -> list[str]:
    lines = PRIME_WF.read_text(encoding="utf-8").splitlines()
    defs = []
    for i, line in enumerate(lines):
        if not line.startswith("run_bounded() {"):
            continue
        if line.rstrip().endswith("}"):
            defs.append(line)
            continue
        end = lines.index("}", i)
        defs.append("\n".join(lines[i : end + 1]))
    return defs


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@unittest.skipIf(os.name == "nt" or not SHELLS, "POSIX shell required")
class RunBoundedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.defs = _definitions()
        self.assertTrue(self.defs, "no run_bounded definition found in prime workflow.md")

    def _run(self, shell: str, definition: str, call: str) -> subprocess.CompletedProcess:
        script = f'{definition}\n{call}\necho "rc=$?"\n'
        return subprocess.run(
            [shell, "-c", script], capture_output=True, text=True, timeout=10
        )

    def test_timeout_kills_process_group_and_reports(self) -> None:
        for shell in SHELLS:
            for n, definition in enumerate(self.defs):
                with self.subTest(shell=shell, definition=n), tempfile.TemporaryDirectory() as tmp:
                    pidfile = Path(tmp) / "grandchild.pid"
                    # The descendant ignores TERM, so only the KILL escalation ends it.
                    call = (
                        f"run_bounded 1 sh -c '( trap \"\" TERM; sleep 30 ) & "
                        f"echo $! > {pidfile}; wait'"
                    )
                    proc = self._run(shell, definition, call)
                    self.assertIn("rc=124", proc.stdout, proc.stdout + proc.stderr)
                    self.assertIn("TIMEOUT", proc.stdout)
                    pid = int(pidfile.read_text().strip())
                    deadline = time.monotonic() + 3
                    while _alive(pid) and time.monotonic() < deadline:
                        time.sleep(0.1)
                    self.assertFalse(_alive(pid), "grandchild survived the timeout")

    def test_fast_probe_keeps_its_exit_status(self) -> None:
        for shell in SHELLS:
            for n, definition in enumerate(self.defs):
                with self.subTest(shell=shell, definition=n):
                    proc = self._run(shell, definition, "run_bounded 5 sh -c 'exit 3'")
                    self.assertIn("rc=3", proc.stdout, proc.stdout + proc.stderr)
                    self.assertNotIn("TIMEOUT", proc.stdout)

    def test_probe_crossing_a_second_boundary_is_not_a_timeout(self) -> None:
        for shell in SHELLS:
            for n, definition in enumerate(self.defs):
                with self.subTest(shell=shell, definition=n):
                    time.sleep((0.8 - time.time() % 1) % 1)  # start late in a second
                    proc = self._run(shell, definition, "run_bounded 1 sh -c 'sleep 0.4'")
                    self.assertIn("rc=0", proc.stdout, proc.stdout + proc.stderr)
                    self.assertNotIn("TIMEOUT", proc.stdout)


if __name__ == "__main__":
    unittest.main()
