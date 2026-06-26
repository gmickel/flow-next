"""Behavioral + prose-contract tests for the Cua native-rung headless/CI determination (fn-71).

The attended-vs-headless split (Cua Driver vs Cua Sandbox) hinges on "is a usable
display reachable?" — and `references/cua.md` ships the determination as a runnable
bash probe (`cua-driver call get_screen_size | jq -e '.width > 0 and .height > 0'`).
Since it's a pure shell predicate, this test EXTRACTS the shipped probe and EXECUTES
it against a stubbed `cua-driver` so the documented snippet is verified, not paraphrased:

- display present (stub returns real dims, exit 0)  → DISPLAY_PRESENT=1 (attended)
- headless: command errors (exit 1, no output)      → DISPLAY_PRESENT=0 (sandbox)
- headless: zero/negative dims                       → DISPLAY_PRESENT=0 (sandbox)

The behavioral run is POSIX-only (the host runs the probe under Git-bash on Windows,
but executing the extracted snippet via a Python subprocess + a PATH-stub on the
Windows runner tests shell plumbing, not probe logic — same posture as
test_codex_delegation_gates). The prose-contract test runs on ALL platforms
(incl. windows-latest) as the cross-platform drift guard.

Real no-display behavior of `cua-driver` on headless Linux/Windows hosts stays a
"verify at build" item (the driver is opt-in, not installed in CI) — see cua.md's
drift/verify-at-build note.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
DRIVE_SKILL = REPO_ROOT / "plugins" / "flow-next" / "skills" / "flow-next-drive"
CUA_MD = DRIVE_SKILL / "references" / "cua.md"
SKILL_MD = DRIVE_SKILL / "SKILL.md"


def _cua_text() -> str:
    # Normalize CRLF→LF (no .gitattributes pins LF; Windows checks out CRLF, which
    # would break `bash -c` on the extracted snippet — same fix as the codex-
    # delegation gate test).
    return CUA_MD.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _extract_display_probe(text: str) -> str:
    """Pull the bash code fence under '## Determining headless / CI' that contains
    the get_screen_size probe — so the test runs the EXACT shipped snippet."""
    heading = text.find("## Determining headless / CI")
    if heading == -1:
        raise AssertionError("'## Determining headless / CI' section not found in cua.md")
    for m in re.finditer(r"```bash\n(.*?)```", text[heading:], re.DOTALL):
        block = m.group(1)
        if "get_screen_size" in block and "DISPLAY_PRESENT" in block:
            return block
    raise AssertionError("get_screen_size display-probe bash fence not found under the section")


@unittest.skipUnless(shutil.which("bash"), "bash required to execute the display probe")
@unittest.skipUnless(shutil.which("jq"), "jq required by the display probe")
@unittest.skipIf(
    sys.platform == "win32",
    "POSIX-shell probe: the host runs it under Git-bash, but executing the extracted "
    "snippet via a Python subprocess + a PATH-stub on the Windows runner tests shell "
    "plumbing, not probe logic. Fully exercised on macOS + ubuntu; the prose-contract "
    "test runs on Windows.",
)
class HeadlessProbeExecution(unittest.TestCase):
    """Execute the shipped get_screen_size probe against a stubbed cua-driver."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.probe = _extract_display_probe(_cua_text())

    def _run_probe(self, stub_mode: str) -> int:
        """Run the extracted probe with a fake `cua-driver` on PATH; return DISPLAY_PRESENT."""
        with tempfile.TemporaryDirectory() as d:
            stub = pathlib.Path(d) / "cua-driver"
            # One stub, mode selected via env. `call get_screen_size` is the only path used.
            stub.write_text(
                "#!/bin/sh\n"
                'if [ "$1" = "call" ] && [ "$2" = "get_screen_size" ]; then\n'
                '  case "$STUB_MODE" in\n'
                '    present)      echo \'{"width":5120,"height":1440,"scale_factor":1.0}\'; exit 0 ;;\n'
                '    headless_err) exit 1 ;;\n'
                '    headless_zero) echo \'{"width":0,"height":0}\'; exit 0 ;;\n'
                "  esac\n"
                "fi\n"
                "exit 2\n",
                encoding="utf-8",
            )
            stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            env = dict(os.environ)
            env["PATH"] = f"{d}{os.pathsep}{env['PATH']}"
            env["STUB_MODE"] = stub_mode
            script = f"set -u\n{self.probe}\nprintf '%s' \"$DISPLAY_PRESENT\"\n"
            proc = subprocess.run(
                ["bash", "-c", script], env=env, capture_output=True, text=True
            )
            self.assertEqual(proc.returncode, 0, f"probe failed: {proc.stderr}")
            return int(proc.stdout.strip())

    def test_display_present_is_attended(self) -> None:
        self.assertEqual(self._run_probe("present"), 1)

    def test_no_display_errors_is_headless(self) -> None:
        self.assertEqual(self._run_probe("headless_err"), 0)

    def test_zero_dims_is_headless(self) -> None:
        self.assertEqual(self._run_probe("headless_zero"), 0)


class HeadlessDeterminationProseContract(unittest.TestCase):
    """Cross-platform (incl. windows) drift guard for the documented determination."""

    def test_cua_md_documents_the_determination(self) -> None:
        t = _cua_text()
        self.assertIn("## Determining headless / CI", t)
        # CI short-circuit + the empirical probe + the parseable check.
        self.assertIn("$CI", t)
        self.assertIn("cua-driver call get_screen_size", t)
        self.assertIn(".width > 0 and .height > 0", t)
        # The macOS caveat: $DISPLAY is unset on a displayed Mac → never use it there.
        self.assertRegex(t, r"[Nn]ever use it on macOS")
        self.assertIn("$DISPLAY", t)
        # doctor is install/TCC health, NOT a display verdict.
        self.assertRegex(t, r"doctor[^\n]*not[^\n]*display")

    def test_skill_md_step4_points_at_the_determination(self) -> None:
        s = SKILL_MD.read_text(encoding="utf-8")
        self.assertIn("get_screen_size", s)
        self.assertRegex(s, r"Determining headless")


if __name__ == "__main__":
    unittest.main()
