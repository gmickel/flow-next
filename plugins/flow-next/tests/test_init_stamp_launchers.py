"""Unit tests for `_stamp_flow_bin_launchers` and its integration into
`cmd_init` (fn-77.3, R4). Covers the drift guard (in-module constants must be
byte-identical to the committed launcher sources), the sibling-target guard
(only stamp when .flow/bin/flowctl.py is present), the self-heal of a pre-fix
`exec python3` launcher, and idempotency (no tracked-file churn on re-run)."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location("flowctl", ROOT / "scripts" / "flowctl.py")
flowctl = importlib.util.module_from_spec(spec)
sys.modules["flowctl"] = flowctl
spec.loader.exec_module(flowctl)

# The committed launcher sources these constants must never drift from.
SRC_SH = ROOT / "scripts" / "flowctl"
SRC_CMD = ROOT / "scripts" / "flowctl.cmd"

# Pre-fix (broken) launcher shape existing installs may still carry: bare
# `exec python3` with no functionality probe — the exact form init self-heals.
OLD_BROKEN_SH = (
    '#!/bin/bash\n'
    'exec python3 "$(dirname "${BASH_SOURCE[0]}")/flowctl.py" "$@"\n'
)


def _seed_flowctl_py(bin_dir: Path) -> None:
    """Seed the launcher target the stamp guards on. Contents are irrelevant —
    only its presence gates stamping (fn-77 impl-review)."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    (bin_dir / "flowctl.py").write_text("# flowctl target\n", encoding="utf-8")


class TestLauncherConstantDriftGuard(unittest.TestCase):
    """DRIFT GUARD (R4): the in-module launcher bodies must be byte-identical
    to the committed sources so `init` self-heal stamps the real launchers."""

    def test_launcher_sh_matches_source_byte_for_byte(self) -> None:
        self.assertEqual(
            flowctl.LAUNCHER_SH.encode("utf-8"),
            SRC_SH.read_bytes(),
            "LAUNCHER_SH drifted from scripts/flowctl — edit both together.",
        )

    def test_launcher_cmd_matches_source_byte_for_byte(self) -> None:
        # .cmd is a Windows batch file: stored LF in-module, written CRLF.
        self.assertEqual(
            flowctl.LAUNCHER_CMD.encode("utf-8").replace(b"\n", b"\r\n"),
            SRC_CMD.read_bytes(),
            "LAUNCHER_CMD drifted from scripts/flowctl.cmd — edit both together.",
        )


class TestStampFlowBinLaunchers(unittest.TestCase):
    """`_stamp_flow_bin_launchers(flow_dir) -> list` invariants."""

    def test_stamps_when_flowctl_py_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            _seed_flowctl_py(flow_dir / "bin")
            actions = flowctl._stamp_flow_bin_launchers(flow_dir)
            sh = flow_dir / "bin" / "flowctl"
            cmd = flow_dir / "bin" / "flowctl.cmd"
            self.assertTrue(sh.exists() and cmd.exists())
            self.assertEqual(sh.read_bytes(), SRC_SH.read_bytes())
            self.assertEqual(cmd.read_bytes(), SRC_CMD.read_bytes())
            self.assertIn("stamped bin/flowctl", actions)
            self.assertIn("stamped bin/flowctl.cmd", actions)

    def test_skips_when_flowctl_py_absent(self) -> None:
        # Fresh/bare init: no launcher target on disk. Stamping must be a no-op
        # so we never leave orphan launchers pointing at a missing flowctl.py.
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            actions = flowctl._stamp_flow_bin_launchers(flow_dir)
            self.assertEqual(actions, [])
            self.assertFalse((flow_dir / "bin" / "flowctl").exists())
            self.assertFalse((flow_dir / "bin" / "flowctl.cmd").exists())

    def test_skips_when_bin_has_no_flowctl_py(self) -> None:
        # bin/ exists (e.g. holds unrelated files) but flowctl.py is absent —
        # still skip: the guard is on the target, not on the directory.
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            (flow_dir / "bin").mkdir(parents=True)
            actions = flowctl._stamp_flow_bin_launchers(flow_dir)
            self.assertEqual(actions, [])
            self.assertFalse((flow_dir / "bin" / "flowctl").exists())

    def test_self_heals_old_exec_python3_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            _seed_flowctl_py(flow_dir / "bin")
            # Pre-fix repo: broken bash launcher present, .cmd missing entirely.
            (flow_dir / "bin" / "flowctl").write_text(OLD_BROKEN_SH, encoding="utf-8")
            actions = flowctl._stamp_flow_bin_launchers(flow_dir)
            # Rewritten to the probe form + the missing .cmd is re-added.
            self.assertEqual((flow_dir / "bin" / "flowctl").read_bytes(), SRC_SH.read_bytes())
            self.assertEqual((flow_dir / "bin" / "flowctl.cmd").read_bytes(), SRC_CMD.read_bytes())
            self.assertIn("stamped bin/flowctl", actions)
            self.assertIn("stamped bin/flowctl.cmd", actions)

    def test_idempotent_no_churn_on_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            _seed_flowctl_py(flow_dir / "bin")
            flowctl._stamp_flow_bin_launchers(flow_dir)  # first stamp
            sh = flow_dir / "bin" / "flowctl"
            before = sh.read_bytes()
            second = flowctl._stamp_flow_bin_launchers(flow_dir)
            self.assertEqual(second, [], "re-run must report no action (no churn)")
            self.assertEqual(sh.read_bytes(), before)


class TestCmdInitStampsLaunchers(unittest.TestCase):
    """cmd_init wires the stamp on an existing install and stays idempotent;
    a fresh init leaves no orphan launchers (fn-77 impl-review)."""

    def _run_init(self, tmp: Path) -> dict:
        ns = mock.Mock()
        ns.json = True
        captured: dict = {}
        with mock.patch.object(flowctl, "json_output", side_effect=lambda d: captured.update(d)):
            with mock.patch.object(flowctl, "get_flow_dir", return_value=tmp / ".flow"):
                flowctl.cmd_init(ns)
        return captured

    def test_existing_install_stamps_and_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _seed_flowctl_py(tmp / ".flow" / "bin")  # existing install: target present
            result = self._run_init(tmp)
            self.assertTrue(result.get("success"))
            actions = result.get("actions", [])
            self.assertIn("stamped bin/flowctl", actions)
            self.assertIn("stamped bin/flowctl.cmd", actions)
            self.assertTrue((tmp / ".flow" / "bin" / "flowctl").exists())
            self.assertTrue((tmp / ".flow" / "bin" / "flowctl.cmd").exists())

    def test_fresh_init_skips_launchers(self) -> None:
        # A bare `flowctl init` (no flowctl.py yet) must not stamp launchers.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            result = self._run_init(tmp)
            self.assertTrue(result.get("success"))
            bin_actions = [a for a in result.get("actions", []) if "bin/flowctl" in a]
            self.assertEqual(bin_actions, [])
            self.assertFalse((tmp / ".flow" / "bin" / "flowctl").exists())
            self.assertFalse((tmp / ".flow" / "bin" / "flowctl.cmd").exists())

    def test_re_init_reports_no_bin_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _seed_flowctl_py(tmp / ".flow" / "bin")
            self._run_init(tmp)
            second = self._run_init(tmp)
            bin_actions = [a for a in second.get("actions", []) if "bin/" in a]
            self.assertEqual(bin_actions, [], "re-init must not churn .flow/bin")


if __name__ == "__main__":
    unittest.main()
