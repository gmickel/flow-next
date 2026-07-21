"""fn-121 R16 — flowctl setup-mode set state machine (plugin/copy stamp)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


FLOWCTL_PY = Path(__file__).resolve().parents[1] / "scripts" / "flowctl.py"

VALID_CLAUDE = (
    "<!-- BEGIN FLOW-NEXT -->\n"
    "<!-- flow-next:snippet:v1 -->\n"
    "body\n"
    "<!-- END FLOW-NEXT -->\n"
)


class SetupModeStampTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        flow = self.repo / ".flow"
        flow.mkdir()
        self.meta_path = flow / "meta.json"
        self.meta_path.write_text("{}", encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _run(self, mode: str, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(FLOWCTL_PY),
                "setup-mode",
                "set",
                mode,
                *extra,
            ],
            cwd=self.repo,
            capture_output=True,
            text=True,
        )

    def _run_json(self, mode: str) -> subprocess.CompletedProcess:
        return self._run(mode, "--json")

    def _payload(self, proc: subprocess.CompletedProcess) -> dict:
        self.assertTrue(
            proc.stdout.strip(),
            "expected JSON on stdout; stderr=%r" % proc.stderr,
        )
        return json.loads(proc.stdout)

    def _meta(self) -> dict:
        return json.loads(self.meta_path.read_text(encoding="utf-8"))

    def _write_claude(self, content: str) -> None:
        (self.repo / "CLAUDE.md").write_text(content, encoding="utf-8")

    def _touch_artifact(self, relpath: str) -> None:
        path = self.repo / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# artifact\n", encoding="utf-8")

    # --- plugin refusals ---

    def test_plugin_refuses_when_claude_md_missing(self) -> None:
        proc = self._run_json("plugin")
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        data = self._payload(proc)
        self.assertFalse(data["success"])
        self.assertTrue(
            any("CLAUDE.md missing" in f for f in data["failures"]),
            data["failures"],
        )

    def test_plugin_refuses_when_claude_has_no_block(self) -> None:
        self._write_claude("just some prose, no markers\n")
        proc = self._run_json("plugin")
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        data = self._payload(proc)
        self.assertFalse(data["success"])
        self.assertTrue(
            any("no FLOW-NEXT block" in f for f in data["failures"]),
            data["failures"],
        )

    def test_plugin_refuses_when_block_has_no_sentinel(self) -> None:
        self._write_claude(
            "<!-- BEGIN FLOW-NEXT -->\n"
            "body without sentinel\n"
            "<!-- END FLOW-NEXT -->\n"
        )
        proc = self._run_json("plugin")
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        data = self._payload(proc)
        self.assertFalse(data["success"])
        self.assertTrue(
            any("no snippet sentinel" in f for f in data["failures"]),
            data["failures"],
        )

    def test_plugin_refuses_on_stale_sentinel_v0(self) -> None:
        self._write_claude(
            "<!-- BEGIN FLOW-NEXT -->\n"
            "<!-- flow-next:snippet:v0 -->\n"
            "body\n"
            "<!-- END FLOW-NEXT -->\n"
        )
        proc = self._run_json("plugin")
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        data = self._payload(proc)
        self.assertFalse(data["success"])
        self.assertTrue(
            any("v0" in f for f in data["failures"]),
            data["failures"],
        )

    def test_plugin_refuses_when_copy_artifact_present(self) -> None:
        self._write_claude(VALID_CLAUDE)
        self._touch_artifact(".flow/bin/flowctl.py")
        proc = self._run_json("plugin")
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        data = self._payload(proc)
        self.assertFalse(data["success"])
        self.assertIn(
            "copy artifact present: .flow/bin/flowctl.py",
            data["failures"],
        )

    def test_plugin_refuses_when_bootstrap_copy_present(self) -> None:
        self._write_claude(VALID_CLAUDE)
        self._touch_artifact(".flow/bin/flowctl_bootstrap.py")
        proc = self._run_json("plugin")
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        data = self._payload(proc)
        self.assertIn(
            "copy artifact present: .flow/bin/flowctl_bootstrap.py",
            data["failures"],
        )

    def test_plugin_refuses_when_help_fast_path_copy_present(self) -> None:
        self._write_claude(VALID_CLAUDE)
        self._touch_artifact(".flow/bin/flowctl-help.txt")
        proc = self._run_json("plugin")
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        data = self._payload(proc)
        self.assertIn(
            "copy artifact present: .flow/bin/flowctl-help.txt",
            data["failures"],
        )

    # --- success paths ---

    def test_plugin_succeeds_in_clean_state(self) -> None:
        self._write_claude(VALID_CLAUDE)
        proc = self._run_json("plugin")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        data = self._payload(proc)
        self.assertTrue(data["success"])
        self.assertEqual(data["mode"], "plugin")
        self.assertEqual(data.get("sentinel"), "v1")
        self.assertEqual(self._meta().get("setup_mode"), "plugin")

    def test_copy_stamps_unconditionally_without_claude(self) -> None:
        # No CLAUDE.md at all.
        self.assertFalse((self.repo / "CLAUDE.md").exists())
        proc = self._run_json("copy")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        data = self._payload(proc)
        self.assertTrue(data["success"])
        self.assertEqual(data["mode"], "copy")
        self.assertEqual(self._meta().get("setup_mode"), "copy")

    # --- multi-failure + non-write ---

    def test_plugin_lists_multiple_failures_at_once(self) -> None:
        # No CLAUDE.md + two copy artifacts.
        self._touch_artifact(".flow/bin/flowctl.py")
        self._touch_artifact(".flow/usage.md")
        proc = self._run_json("plugin")
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        data = self._payload(proc)
        self.assertFalse(data["success"])
        failures = data["failures"]
        self.assertTrue(
            any("CLAUDE.md missing" in f for f in failures), failures
        )
        self.assertIn(
            "copy artifact present: .flow/bin/flowctl.py", failures
        )
        self.assertIn("copy artifact present: .flow/usage.md", failures)
        self.assertEqual(len(failures), 3, failures)

    def test_refusal_does_not_write_setup_mode(self) -> None:
        proc = self._run_json("plugin")
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        meta = self._meta()
        self.assertNotIn("setup_mode", meta)

    def test_flow_missing_entirely_nonzero_rc(self) -> None:
        bare = tempfile.TemporaryDirectory()
        try:
            bare_repo = Path(bare.name)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(FLOWCTL_PY),
                    "setup-mode",
                    "set",
                    "plugin",
                    "--json",
                ],
                cwd=bare_repo,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        finally:
            bare.cleanup()


if __name__ == "__main__":
    unittest.main()
