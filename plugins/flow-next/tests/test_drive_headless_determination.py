"""Behavioral + prose-contract tests for the Cua native-rung headless/CI determination (fn-71).

The attended-vs-headless split (Cua Driver vs Cua Sandbox) hinges on "is a usable
display reachable?" — and `references/cua.md` ships the determination as a runnable
bash probe. Since it's a pure shell predicate, this test EXTRACTS the shipped probe
and EXECUTES it against a stubbed `cua-driver` so the documented snippet is verified,
not paraphrased. The probe is **3-way** (the load-bearing correctness property — a
missing driver must NOT be read as "headless"):

- driver present, display reachable (real dims, exit 0) → DISPLAY_PRESENT=1       (attended)
- driver present, no display (errors / zero dims)       → DISPLAY_PRESENT=0       (sandbox)
- driver ABSENT (`command -v cua-driver` fails)         → DISPLAY_PRESENT=unknown (fall back; NOT headless)

The behavioral run is POSIX-only (the host runs the probe under Git-bash on Windows,
but executing the extracted snippet via a Python subprocess + a PATH-stub on the
Windows runner tests shell plumbing, not probe logic — same posture as
test_codex_delegation_gates). The prose-contract test runs on ALL platforms
(incl. windows-latest) as the cross-platform drift guard.

Real no-display behavior of `cua-driver` on headless Linux/Windows hosts stays a
"verify at build" item (the driver is opt-in, not installed in CI).
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

_JQ = shutil.which("jq")
_BASH = shutil.which("bash")

_STUB = """#!/bin/sh
if [ "$1" = "call" ] && [ "$2" = "get_screen_size" ]; then
  case "$STUB_MODE" in
    present)        echo '{"width":5120,"height":1440,"scale_factor":1.0}'; exit 0 ;;
    headless_err)   exit 1 ;;
    headless_zero)  echo '{"width":0,"height":0}'; exit 0 ;;
    zero_height)    echo '{"width":5120,"height":0}'; exit 0 ;;
  esac
fi
exit 2
"""


def _cua_text() -> str:
    # Normalize CRLF→LF (no .gitattributes pins LF; Windows checks out CRLF, which
    # would break `bash -c` on the extracted snippet — same fix as the codex-
    # delegation gate test).
    return CUA_MD.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _extract_display_probe(text: str) -> str:
    """Pull the bash code fence under '## Determining headless / CI' that contains
    the get_screen_size probe — so the test runs the EXACT shipped snippet. The
    fence is indented under a list item; dedent so `bash -c` parses it cleanly."""
    heading = text.find("## Determining headless / CI")
    if heading == -1:
        raise AssertionError("'## Determining headless / CI' section not found in cua.md")
    for m in re.finditer(r"```bash\n(.*?)```", text[heading:], re.DOTALL):
        block = m.group(1)
        if "get_screen_size" in block and "DISPLAY_PRESENT" in block:
            lines = block.splitlines()
            indent = min(
                (len(ln) - len(ln.lstrip()) for ln in lines if ln.strip()), default=0
            )
            return "\n".join(ln[indent:] if ln.strip() else ln for ln in lines)
    raise AssertionError("get_screen_size display-probe bash fence not found under the section")


@unittest.skipUnless(_BASH, "bash required to execute the display probe")
@unittest.skipUnless(_JQ, "jq required by the display probe")
@unittest.skipIf(
    sys.platform == "win32",
    "POSIX-shell probe: the host runs it under Git-bash, but executing the extracted "
    "snippet via a Python subprocess + a PATH-stub on the Windows runner tests shell "
    "plumbing, not probe logic. Fully exercised on macOS + ubuntu; the prose-contract "
    "test runs on Windows.",
)
class HeadlessProbeExecution(unittest.TestCase):
    """Execute the shipped 3-way probe against a stubbed (or absent) cua-driver."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.probe = _extract_display_probe(_cua_text())

    def _run_probe(self, stub_mode: str) -> str:
        """Run the extracted probe with a controlled PATH. `absent` omits the stub so
        `command -v cua-driver` fails (the real driver, if any, is off this PATH)."""
        with tempfile.TemporaryDirectory() as d:
            bindir = pathlib.Path(d)
            os.symlink(_JQ, bindir / "jq")  # jq reachable; POSIX (class skipped on win32)
            if stub_mode != "absent":
                stub = bindir / "cua-driver"
                stub.write_text(_STUB, encoding="utf-8")
                stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            env = dict(os.environ)
            env["PATH"] = str(bindir)  # ONLY our dir → command -v sees only our stub (or nothing)
            env["STUB_MODE"] = stub_mode
            script = f"set -u\n{self.probe}\nprintf '%s' \"$DISPLAY_PRESENT\"\n"
            proc = subprocess.run(
                [_BASH, "-c", script], env=env, capture_output=True, text=True
            )
            self.assertEqual(proc.returncode, 0, f"probe failed: {proc.stderr}")
            return proc.stdout.strip()

    def test_display_present_is_attended(self) -> None:
        self.assertEqual(self._run_probe("present"), "1")

    def test_no_display_errors_is_headless(self) -> None:
        self.assertEqual(self._run_probe("headless_err"), "0")

    def test_zero_dims_is_headless(self) -> None:
        self.assertEqual(self._run_probe("headless_zero"), "0")

    def test_zero_height_is_headless(self) -> None:
        # Width>0 but height==0 must NOT count as a display (the probe checks both).
        self.assertEqual(self._run_probe("zero_height"), "0")

    def test_driver_absent_is_unknown_not_headless(self) -> None:
        # The load-bearing bug guard: a missing driver must NOT be read as headless.
        self.assertEqual(self._run_probe("absent"), "unknown")


class HeadlessDeterminationProseContract(unittest.TestCase):
    """Cross-platform (incl. windows) drift guard for the documented determination."""

    def test_cua_md_documents_the_determination(self) -> None:
        t = _cua_text()
        self.assertIn("## Determining headless / CI", t)
        self.assertIn("$CI", t)
        self.assertIn("cua-driver call get_screen_size", t)
        # Driver-presence guard + the absent→not-headless property (the real bug fix).
        self.assertIn("command -v cua-driver", t)
        self.assertIn("DISPLAY_PRESENT=unknown", t)
        # Defensive parse tolerates the MCP structuredContent envelope; checks BOTH dims.
        self.assertIn(".structuredContent.width", t)
        self.assertIn(".height", t)
        self.assertIn(".structuredContent.height", t)
        # TCC grants are NOT a headless signal; macOS $DISPLAY caveat; doctor≠display.
        self.assertRegex(t, r"grant[s]?[^\n]*not[^\n]*headless|NOT a headless signal")
        self.assertRegex(t, r"[Nn]ever use[^\n]*macOS")
        self.assertRegex(t, r"doctor[^\n]*not[^\n]*display")

    def test_cua_md_documents_telemetry_and_supply_chain_caveats(self) -> None:
        t = _cua_text()
        self.assertIn("CUA_TELEMETRY_ENABLED=false", t)  # local "zero-network" needs the opt-out
        self.assertRegex(t, r"[Ss]upply-chain")  # mutable curl|bash from main

    def test_skill_md_step4_points_at_the_determination(self) -> None:
        s = SKILL_MD.read_text(encoding="utf-8")
        self.assertIn("get_screen_size", s)
        self.assertRegex(s, r"Determining headless")


if __name__ == "__main__":
    unittest.main()
