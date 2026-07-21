"""fn-114.3 - Ralph guard defect fixes (structured done-signal, dual-platform,
gated debug, file-tool receipt gate).

Pins the section-C guard fixes without touching the fn-55 canonical-delegation
assertions in test_ralph_guard_codex_delegation.py.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from typing import Optional
from unittest import mock


HERE = pathlib.Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent
GUARD_PY = PLUGIN_DIR / "scripts" / "hooks" / "ralph-guard.py"


def _load_guard():
    spec = importlib.util.spec_from_file_location("ralph_guard_fn114", GUARD_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _drive_hook(
    payload: dict,
    env_extra: Optional[dict] = None,
    *,
    flow_ralph: str = "1",
) -> subprocess.CompletedProcess:
    env = {**os.environ, "FLOW_RALPH": flow_ralph}
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(GUARD_PY)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


class DoneDetectionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.guard = _load_guard()

    def test_json_status_done_accepted(self) -> None:
        ok = self.guard.is_flowctl_done_success(
            "fn-1.2",
            "flowctl done fn-1.2 --summary-file s.md --evidence-json e.json --json",
            {"stdout": json.dumps({"success": True, "id": "fn-1.2", "status": "done"}), "exit_code": 0},
            json.dumps({"success": True, "id": "fn-1.2", "status": "done"}),
        )
        self.assertTrue(ok)

    def test_word_sniff_rejected(self) -> None:
        # The old sniff matched any response containing "done"/"updated"/"completed".
        ok = self.guard.is_flowctl_done_success(
            "fn-1.2",
            "flowctl done fn-1.2 --summary-file s.md --evidence-json e.json",
            {"stdout": "something was updated and completed, status ok"},
            "something was updated and completed, status ok",
        )
        self.assertFalse(ok)

    def test_nonzero_exit_rejected(self) -> None:
        ok = self.guard.is_flowctl_done_success(
            "fn-1.2",
            "flowctl done fn-1.2 --json",
            {"stdout": json.dumps({"id": "fn-1.2", "status": "done"}), "exit_code": 1},
            json.dumps({"id": "fn-1.2", "status": "done"}),
        )
        self.assertFalse(ok)

    def test_exact_plain_text_contract(self) -> None:
        ok = self.guard.is_flowctl_done_success(
            "fn-1.2",
            "flowctl done fn-1.2 --summary-file s.md --evidence-json e.json",
            {"stdout": "Task fn-1.2 completed\n"},
            "Task fn-1.2 completed\n",
        )
        self.assertTrue(ok)

    def test_json_flag_without_status_rejected(self) -> None:
        ok = self.guard.is_flowctl_done_success(
            "fn-1.2",
            "flowctl done fn-1.2 --json",
            {"stdout": "Task fn-1.2 completed", "exit_code": 0},
            "Task fn-1.2 completed",
        )
        self.assertFalse(ok)


class DualPlatformMatchersTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.guard = _load_guard()

    def test_shell_and_file_tool_sets(self) -> None:
        self.assertEqual(self.guard.SHELL_TOOLS, frozenset({"Bash", "Execute"}))
        self.assertEqual(
            self.guard.FILE_TOOLS,
            frozenset({"Edit", "Write", "Create", "ApplyPatch"}),
        )

    def test_execute_pretool_runs_command_checks(self) -> None:
        # Execute (Droid shell) must reach the same codex block path as Bash.
        proc = _drive_hook(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Execute",
                "session_id": "dual-shell",
                "tool_input": {"command": "codex exec --output-schema x.json"},
            }
        )
        self.assertEqual(proc.returncode, 2)

    def test_create_file_tool_protected_path(self) -> None:
        proc = _drive_hook(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Create",
                "session_id": "dual-file",
                "tool_input": {"file_path": "/repo/scripts/hooks/ralph-guard.py", "content": "x"},
            }
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("protected file", proc.stderr)


class FileToolReceiptGateTestCase(unittest.TestCase):
    def test_write_receipt_blocked_pre_review(self) -> None:
        receipt = "/tmp/flow-next-test-receipts/impl-fn-1.2.json"
        proc = _drive_hook(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Write",
                "session_id": "receipt-pre",
                "tool_input": {
                    "file_path": receipt,
                    "content": '{"type":"impl_review","id":"fn-1.2","verdict":"SHIP"}',
                },
            },
            env_extra={"REVIEW_RECEIPT_PATH": receipt},
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("before review completes", proc.stderr)


class DebugLogGatingTestCase(unittest.TestCase):
    def test_no_debug_log_without_env(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = {
                **os.environ,
                "FLOW_RALPH": "1",
                "TMPDIR": td,
                "TMP": td,
                "TEMP": td,
            }
            env.pop("RALPH_GUARD_DEBUG", None)
            debug_path = pathlib.Path(td) / "ralph-guard-debug.log"
            if debug_path.exists():
                debug_path.unlink()
            proc = subprocess.run(
                [sys.executable, str(GUARD_PY)],
                input=json.dumps(
                    {
                        "hook_event_name": "PreToolUse",
                        "tool_name": "Bash",
                        "session_id": "dbg-off",
                        "tool_input": {"command": "echo hi"},
                    }
                ),
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertFalse(debug_path.exists())

    def test_debug_log_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = {
                **os.environ,
                "FLOW_RALPH": "1",
                "RALPH_GUARD_DEBUG": "1",
                "TMPDIR": td,
                "TMP": td,
                "TEMP": td,
            }
            debug_path = pathlib.Path(td) / "ralph-guard-debug.log"
            proc = subprocess.run(
                [sys.executable, str(GUARD_PY)],
                input=json.dumps(
                    {
                        "hook_event_name": "PreToolUse",
                        "tool_name": "Bash",
                        "session_id": "dbg-on",
                        "tool_input": {"command": "echo hi"},
                    }
                ),
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertTrue(debug_path.is_file())
            self.assertIn("Hook called", debug_path.read_text(encoding="utf-8"))

    def test_state_file_uses_tempdir(self) -> None:
        guard = _load_guard()
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(guard.tempfile, "gettempdir", return_value=td):
                path = guard.get_state_file("sess-x")
            self.assertEqual(path, pathlib.Path(td) / "ralph-guard-sess-x.json")
            self.assertNotEqual(str(path), "/tmp/ralph-guard-sess-x.json")


class DeadWeightTestCase(unittest.TestCase):
    def test_no_ralph_guard_version(self) -> None:
        guard = _load_guard()
        self.assertFalse(hasattr(guard, "RALPH_GUARD_VERSION"))

    def test_local_dev_points_at_e2e(self) -> None:
        local_dev = PLUGIN_DIR.parent.parent / "agent_docs" / "local-dev.md"
        text = local_dev.read_text(encoding="utf-8")
        self.assertIn("ralph_e2e_test.sh", text)


if __name__ == "__main__":
    unittest.main()


class TestProtectedRegistrationFiles(unittest.TestCase):
    """fn-114 review: the guard must block edits to its own hook registration."""

    def _blocks(self, file_path: str) -> bool:
        import io, contextlib
        guard = _load_guard()
        data = {"tool_name": "Edit", "tool_input": {"file_path": file_path}}
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                guard.handle_protected_file_check(data)
            except SystemExit:
                pass
        return "BLOCKED" in (out.getvalue() + err.getvalue())

    def test_blocks_claude_settings(self) -> None:
        self.assertTrue(self._blocks("/repo/.claude/settings.json"))

    def test_blocks_factory_hooks(self) -> None:
        self.assertTrue(self._blocks("/repo/.factory/hooks.json"))

    def test_blocks_project_codex_hooks(self) -> None:
        self.assertTrue(self._blocks("/repo/.codex/hooks.json"))

    def test_allows_ordinary_file(self) -> None:
        self.assertFalse(self._blocks("/repo/src/app.py"))
