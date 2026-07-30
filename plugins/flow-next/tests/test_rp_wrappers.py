"""RepoPrompt CE discovery, schema compatibility, and wrapper regressions."""

from __future__ import annotations

import argparse
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402


def _executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _result(stdout: str = "", stderr: str = "", returncode: int = 0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


class RepoPromptDiscoveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.bin = self.root / "bin"
        self.home.mkdir()
        self.bin.mkdir()
        self.non_executable: set[Path] = set()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    @contextmanager
    def env(self):
        # Model PATH and X_OK deterministically. Windows does not preserve POSIX
        # execute bits on these extensionless fixtures, while the production CE
        # links are macOS paths; discovery policy should not depend on the host
        # running this unit test.
        def which(name: str):
            candidate = self.bin / name
            return str(candidate) if candidate.is_file() else None

        def executable(path, _mode):
            candidate = Path(path)
            return candidate.is_file() and candidate not in self.non_executable

        with mock.patch.dict(
            os.environ,
            {"HOME": str(self.home), "PATH": str(self.bin)},
            clear=False,
        ), mock.patch.object(
            flowctl.Path, "home", return_value=self.home
        ), mock.patch.object(flowctl.shutil, "which", side_effect=which), mock.patch.object(
            flowctl.os, "access", side_effect=executable
        ):
            yield

    def test_ladder_prefers_path_ce_over_every_classic_candidate(self) -> None:
        ce = _executable(self.bin / "rpce-cli")
        _executable(self.bin / "rp-cli")
        _executable(self.home / "RepoPrompt" / "repoprompt_ce_cli")
        with self.env():
            self.assertEqual(flowctl.require_rp_cli(), str(ce))

    def test_current_then_legacy_ce_user_links_precede_classic(self) -> None:
        classic = _executable(self.bin / "rp-cli")
        current = _executable(self.home / "RepoPrompt" / "repoprompt_ce_cli")
        with self.env():
            self.assertEqual(flowctl.require_rp_cli(), str(current))

        current.unlink()
        current.symlink_to(self.root / "missing-current-target")
        legacy = _executable(
            self.home
            / "Library"
            / "Application Support"
            / "RepoPrompt CE"
            / "repoprompt_ce_cli"
        )
        with self.env():
            self.assertEqual(flowctl.require_rp_cli(), str(legacy))

        legacy.chmod(stat.S_IRUSR | stat.S_IWUSR)
        self.non_executable.add(legacy)
        with self.env():
            self.assertEqual(flowctl.require_rp_cli(), str(classic))

    def test_missing_diagnostic_names_ce_and_rpce_cli(self) -> None:
        err = io.StringIO()
        with self.env(), redirect_stderr(err), self.assertRaises(SystemExit) as raised:
            flowctl.require_rp_cli()
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("RepoPrompt CE", err.getvalue())
        self.assertIn("rpce-cli", err.getvalue())

    def test_selected_ce_runtime_failure_never_executes_classic(self) -> None:
        ce = _executable(self.bin / "rpce-cli")
        classic = _executable(self.bin / "rp-cli")
        failure = subprocess.CalledProcessError(
            7, [str(ce)], stderr="CE connection refused"
        )
        err = io.StringIO()
        with self.env(), mock.patch.object(
            flowctl.subprocess, "run", side_effect=failure
        ) as run, redirect_stderr(err), self.assertRaises(SystemExit):
            flowctl.run_rp_cli(["-e", "windows"])
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][0], str(ce))
        self.assertNotEqual(run.call_args.args[0][0], str(classic))
        self.assertIn("CE connection refused", err.getvalue())


class RepoPromptSchemaAndReuseTest(unittest.TestCase):
    def test_binding_window_id_recurses_through_supported_wrappers(self) -> None:
        payload = {"result": {"data": {"binding": {"window_id": "55"}}}}
        self.assertEqual(flowctl.extract_response_window_id(payload), 55)
        self.assertEqual(flowctl.extract_response_window_id({"windowID": 7}), 7)

    def test_root_paths_combine_and_dedupe_legacy_and_ce_tabs(self) -> None:
        window = {
            "rootFolderPaths": ["/legacy", "/shared"],
            "tabs": [
                {"repo_paths": ["/shared", "/modern-a"]},
                None,
                {"repoPaths": "/modern-b"},
                {"repo_paths": [3, None]},
                "malformed",
            ],
        }
        self.assertEqual(
            flowctl.extract_root_paths(window),
            ["/legacy", "/shared", "/modern-a", "/modern-b"],
        )

    def _run_setup(
        self,
        repo_root: Path,
        run,
        try_run,
        *,
        context: dict | None = None,
    ) -> tuple[str, list[list[str]]]:
        calls: list[list[str]] = []
        usable_context = context or {
            "prompt": "Review the CE reuse changes.",
            "selection": {"files": [{"path": "src/reuse.py"}]},
        }

        def recording_run(args, timeout=None, *, rp_cli=None):
            self.assertEqual(rp_cli, "/bin/rpce-cli")
            calls.append(args)
            if args[-1].startswith("workspace_context "):
                return _result(json.dumps(usable_context))
            return run(args)

        output = io.StringIO()
        with mock.patch.object(flowctl, "require_rp_cli", return_value="/bin/rpce-cli"):
            with mock.patch.object(flowctl, "run_rp_cli", side_effect=recording_run):
                with mock.patch.object(flowctl, "try_run_rp_cli", side_effect=try_run):
                    with redirect_stdout(output):
                        flowctl.cmd_rp_setup_review(
                            argparse.Namespace(
                                repo_root=str(repo_root),
                                summary="Review CE reuse",
                                response_type=None,
                                response_file=None,
                                create=True,
                                json=False,
                            )
                        )
        return output.getvalue().strip(), calls

    def test_modern_bind_context_reuses_window_without_discovery_or_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()

            def try_run(args, timeout=None, *, rp_cli=None):
                payload = json.loads(args[-1].removeprefix("call bind_context "))
                self.assertTrue(payload["create_if_missing"])
                return _result(json.dumps({"binding": {"window_id": 41}}))

            def run(args):
                self.assertEqual(args[:2], ["-w", "41"])
                return _result(json.dumps({"context_id": "tab-bind"}))

            output, calls = self._run_setup(repo, run, try_run)
        self.assertEqual(output, "RP_MODE=context W=41 T=tab-bind")
        flattened = " ".join(" ".join(call) for call in calls)
        self.assertNotIn("manage_workspaces", flattened)
        self.assertNotIn("workspace create", flattened)
        self.assertEqual(
            sum(call[-1].startswith("workspace_context ") for call in calls), 1
        )
        builder_calls = [
            call for call in calls if call[-1].startswith("call context_builder ")
        ]
        self.assertEqual(len(builder_calls), 1)
        payload = json.loads(
            builder_calls[0][-1].removeprefix("call context_builder ")
        )
        self.assertEqual(payload, {"instructions": "Review CE reuse"})
        self.assertFalse(builder_calls[0][-1].startswith("builder "))

    def test_modern_window_tabs_reuse_root_without_workspace_or_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()

            def run(args):
                if args == ["--raw-json", "-e", "windows"]:
                    return _result(
                        json.dumps(
                            {
                                "windows": [
                                    {
                                        "window_id": 73,
                                        "tabs": [{"repo_paths": [str(repo)]}],
                                    }
                                ]
                            }
                        )
                    )
                self.assertEqual(args[:2], ["-w", "73"])
                return _result(json.dumps({"context_id": "tab-window"}))

            output, calls = self._run_setup(repo, run, lambda *_a, **_k: None)
        self.assertEqual(output, "RP_MODE=context W=73 T=tab-window")
        flattened = " ".join(" ".join(call) for call in calls)
        self.assertNotIn("manage_workspaces", flattened)
        self.assertNotIn("workspace create", flattened)
        self.assertEqual(
            sum(call[-1].startswith("workspace_context ") for call in calls), 1
        )

    def test_blank_summary_fails_before_repo_prompt_is_called(self) -> None:
        args = argparse.Namespace(
            repo_root=".",
            summary=" \t\n",
            response_type=None,
            response_file=None,
            create=True,
            json=False,
        )
        with mock.patch.object(flowctl, "try_run_rp_cli") as bind:
            with mock.patch.object(flowctl, "run_rp_cli") as run:
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    flowctl.cmd_rp_setup_review(args)
        bind.assert_not_called()
        run.assert_not_called()

    def test_ce_plain_review_requires_a_response_file_before_repo_prompt_call(
        self,
    ) -> None:
        args = argparse.Namespace(
            repo_root=".",
            summary="Review this",
            response_type="review",
            response_file=None,
            create=True,
            json=False,
        )
        with mock.patch.object(
            flowctl, "require_rp_cli", return_value="/bin/rpce-cli"
        ), mock.patch.object(flowctl, "bind_context_window") as bind, mock.patch.object(
            flowctl, "run_rp_cli"
        ) as run, redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            flowctl.cmd_rp_setup_review(args)
        bind.assert_not_called()
        run.assert_not_called()

    def test_setup_pins_one_resolved_cli_for_bind_and_builder(self) -> None:
        direct = {
            "context_id": "ctx-pinned",
            "status": "completed",
            "prompt": "Review this",
            "file_count": 1,
            "total_tokens": 10,
            "selection": "a.py",
            "response_type": "review",
            "review": {
                "chat_id": "chat-pinned",
                "mode": "review",
                "response": "<verdict>SHIP</verdict>",
            },
        }
        args = argparse.Namespace(
            repo_root=".",
            summary="Review this",
            response_type="review",
            response_file=None,
            create=True,
            json=True,
        )
        with mock.patch.object(
            flowctl, "require_rp_cli", return_value="/opt/pinned/rpce-cli"
        ) as resolve, mock.patch.object(
            flowctl, "bind_context_window", return_value=12
        ) as bind, mock.patch.object(
            flowctl, "run_rp_cli", return_value=_result(json.dumps(direct))
        ) as run, redirect_stdout(io.StringIO()):
            flowctl.cmd_rp_setup_review(args)
        resolve.assert_called_once_with()
        self.assertEqual(bind.call_args.kwargs["rp_cli"], "/opt/pinned/rpce-cli")
        self.assertEqual(run.call_args.kwargs["rp_cli"], "/opt/pinned/rpce-cli")

    def test_summary_file_supplies_complete_builder_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            instructions = Path(tmp) / "review.md"
            instructions.write_text(
                "Complete contract\n<verdict>SHIP</verdict>\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(
                repo_root=tmp,
                summary=None,
                summary_file=str(instructions),
                response_type="review",
                response_file=str(Path(tmp) / "response.md"),
                create=True,
                json=True,
            )
            direct = {
                "context_id": "ctx-1",
                "status": "completed",
                "prompt": "Complete contract",
                "file_count": 1,
                "total_tokens": 10,
                "selection": "a.py",
                "response_type": "review",
                "review": {
                    "chat_id": "chat-1",
                    "mode": "review",
                    "response": "<verdict>SHIP</verdict>",
                },
            }
            with mock.patch.object(
                flowctl, "require_rp_cli", return_value="/bin/rpce-cli"
            ), mock.patch.object(
                flowctl,
                "try_run_rp_cli",
                return_value=_result('{"binding":{"window_id":10}}'),
            ), mock.patch.object(
                flowctl, "run_rp_cli", return_value=_result(json.dumps(direct))
            ) as run, redirect_stdout(io.StringIO()):
                flowctl.cmd_rp_setup_review(args)
            self.assertIn(
                '"instructions": "Complete contract\\n<verdict>SHIP</verdict>\\n"',
                run.call_args.args[0][-1],
            )

    def test_context_id_only_is_not_success_when_builder_state_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()

            def try_run(_args, timeout=None, *, rp_cli=None):
                return _result(json.dumps({"binding": {"window_id": 41}}))

            def run(args):
                self.assertEqual(args[:2], ["-w", "41"])
                return _result(json.dumps({"context_id": "tab-bind"}))

            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self._run_setup(
                    repo,
                    run,
                    try_run,
                    context={"prompt": "", "selection": {"files": []}},
                )

    def test_classic_builder_context_requires_prompt_and_selection(self) -> None:
        invalid = (
            {"prompt": "", "selection": {"files": [{"path": "src/a.py"}]}},
            {"prompt": "Review this", "selection": {"files": []}},
        )
        for context in invalid:
            with self.subTest(context=context):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    flowctl.validate_rp_classic_builder_context(context)

    def test_ce_review_consumes_exact_direct_result_without_tab_query(self) -> None:
        # Schema source: RepoPrompt CE d42c2e30
        # MCPContextBuilderToolProvider.ContextBuilderToolResult + ChatSendReply.
        direct = {
            "context_id": "A1B2C3D4",
            "status": "completed",
            "prompt": "Review the CE direct-result changes.",
            "file_count": 7,
            "total_tokens": 18420,
            "selection": "### Selected Files\n- src/review.py",
            "response_type": "review",
            "review": {
                "chat_id": "review-42",
                "mode": "review",
                "response": "No blocking findings.\n<verdict>SHIP</verdict>",
            },
            "follow_up_hint": (
                'Continue this review conversation with ask_oracle('
                'chat_id: "review-42", new_chat: false)'
            ),
        }
        calls: list[list[str]] = []

        def run(args, timeout=None, *, rp_cli=None):
            calls.append(args)
            self.assertEqual(args[:2], ["-w", "10"])
            return _result(json.dumps(direct))

        with tempfile.TemporaryDirectory() as tmp:
            response_file = Path(tmp) / "review.md"
            args = argparse.Namespace(
                repo_root=tmp,
                summary="Review CE direct result",
                response_type="review",
                response_file=str(response_file),
                create=True,
                json=True,
            )
            with mock.patch.object(
                flowctl, "require_rp_cli", return_value="/bin/rpce-cli"
            ):
                with mock.patch.object(
                    flowctl,
                    "try_run_rp_cli",
                    return_value=_result('{"binding":{"window_id":10}}'),
                ):
                    with mock.patch.object(flowctl, "run_rp_cli", side_effect=run):
                        output = io.StringIO()
                        with redirect_stdout(output):
                            flowctl.cmd_rp_setup_review(args)

            result = json.loads(output.getvalue())
            self.assertEqual(result["mode"], "ce")
            self.assertEqual(result["window"], 10)
            self.assertEqual(result["context_id"], direct["context_id"])
            self.assertEqual(result["chat_id"], "review-42")
            self.assertEqual(result["prompt"], direct["prompt"])
            self.assertEqual(result["selection"], direct["selection"])
            self.assertEqual(result["file_count"], 7)
            self.assertEqual(result["total_tokens"], 18420)
            self.assertEqual(
                response_file.read_text(encoding="utf-8"),
                direct["review"]["response"],
            )

        self.assertEqual(len(calls), 1)
        expression = calls[0][-1]
        self.assertTrue(expression.startswith("call context_builder "))
        payload = json.loads(expression.removeprefix("call context_builder "))
        self.assertEqual(
            payload,
            {
                "instructions": "Review CE direct result",
                "response_type": "review",
            },
        )
        self.assertFalse(any("workspace_context" in " ".join(call) for call in calls))

    def test_ce_review_rejects_malformed_direct_results(self) -> None:
        valid = {
            "context_id": "A1B2C3D4",
            "status": "completed",
            "prompt": "Review the changes.",
            "file_count": 1,
            "total_tokens": 100,
            "selection": "### Selected Files\n- src/review.py",
            "response_type": "review",
            "review": {
                "chat_id": "review-42",
                "mode": "review",
                "response": "<verdict>SHIP</verdict>",
            },
        }
        invalid = [
            {},
            {**valid, "context_id": ""},
            {**valid, "status": "failed: unavailable"},
            {**valid, "prompt": " "},
            {**valid, "selection": ""},
            {**valid, "selection": {"files": ["src/review.py"]}},
            {**valid, "file_count": 0},
            {**valid, "total_tokens": 0},
            {**valid, "response_type": "plan"},
            {**valid, "review": None},
            {**valid, "review": {**valid["review"], "chat_id": ""}},
            {**valid, "review": {**valid["review"], "mode": "chat"}},
            {**valid, "review": {**valid["review"], "response": ""}},
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    flowctl.validate_rp_ce_builder_review(payload)

    def test_ce_bind_failures_never_reach_discovery_or_creation(self) -> None:
        failures = (
            subprocess.CalledProcessError(
                9, ["rpce-cli"], stderr="CE connection unavailable"
            ),
            subprocess.TimeoutExpired(["rpce-cli"], 1),
            _result("not-json"),
            _result("{}"),
            _result('{"binding":{}}'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            args = argparse.Namespace(
                repo_root=str(repo),
                summary="Must stop",
                response_type=None,
                response_file=None,
                create=True,
                json=False,
            )
            for failure in failures:
                with self.subTest(failure=type(failure).__name__):
                    with mock.patch.object(
                        flowctl, "require_rp_cli", return_value="/bin/rpce-cli"
                    ):
                        patch = (
                            mock.patch.object(
                                flowctl.subprocess, "run", return_value=failure
                            )
                            if not isinstance(failure, BaseException)
                            else mock.patch.object(
                                flowctl.subprocess, "run", side_effect=failure
                            )
                        )
                        with patch:
                            with mock.patch.object(flowctl, "run_rp_cli") as downstream:
                                with redirect_stderr(io.StringIO()):
                                    with self.assertRaises(SystemExit):
                                        flowctl.cmd_rp_setup_review(args)
                        downstream.assert_not_called()

    def test_classic_explicit_missing_bind_context_can_use_legacy_windows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            missing = subprocess.CalledProcessError(
                2,
                ["rp-cli"],
                stderr="Tool not found: bind_context",
            )

            def legacy_run(args, timeout=None, *, rp_cli=None):
                if args == ["--raw-json", "-e", "windows"]:
                    return _result(
                        json.dumps(
                            [{"windowID": 8, "rootFolderPaths": [str(repo)]}]
                        )
                    )
                if args[-1].startswith("workspace_context "):
                    return _result(
                        json.dumps(
                            {
                                "prompt": "Review Classic compatibility.",
                                "selection": {"files": [{"path": "src/classic.py"}]},
                            }
                        )
                    )
                self.assertEqual(args[:2], ["-w", "8"])
                self.assertEqual(args[-1], "builder 'Classic compatibility'")
                return _result(json.dumps({"context_id": "classic-tab"}))

            args = argparse.Namespace(
                repo_root=str(repo),
                summary="Classic compatibility",
                response_type="review",
                response_file=None,
                create=True,
                json=False,
            )
            output = io.StringIO()
            with mock.patch.object(
                flowctl, "require_rp_cli", return_value="/bin/rp-cli"
            ):
                with mock.patch.object(flowctl.subprocess, "run", side_effect=missing):
                    with mock.patch.object(flowctl, "run_rp_cli", side_effect=legacy_run):
                        with redirect_stdout(output):
                            flowctl.cmd_rp_setup_review(args)
            self.assertEqual(
                output.getvalue().strip(),
                "RP_MODE=classic W=8 T=classic-tab",
            )


class RepoPromptWrapperCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.message = Path(self._tmp.name) / "message.md"
        self.message.write_text("Review this change", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _call(self, handler, args, expected: list[str]) -> None:
        with mock.patch.object(
            flowctl, "run_rp_cli", return_value=_result("ok\n")
        ) as run, redirect_stdout(io.StringIO()):
            handler(args)
        self.assertEqual(run.call_args.args[0], expected)

    def test_prompt_get_set_select_get_add_and_export_wrappers(self) -> None:
        self._call(
            flowctl.cmd_rp_prompt_get,
            argparse.Namespace(window=2, tab="tab"),
            ["-w", "2", "-t", "tab", "-e", "prompt get"],
        )
        self._call(
            flowctl.cmd_rp_prompt_set,
            argparse.Namespace(window=2, tab="tab", message_file=str(self.message)),
            [
                "-w",
                "2",
                "-t",
                "tab",
                "-e",
                'call prompt {"op": "set", "text": "Review this change"}',
            ],
        )
        self._call(
            flowctl.cmd_rp_select_get,
            argparse.Namespace(window=2, tab="tab"),
            ["-w", "2", "-t", "tab", "-e", "select get"],
        )
        self._call(
            flowctl.cmd_rp_select_add,
            argparse.Namespace(window=2, tab="tab", paths=["src/a.py", "two words"]),
            ["-w", "2", "-t", "tab", "-e", "select add src/a.py 'two words'"],
        )
        self._call(
            flowctl.cmd_rp_prompt_export,
            argparse.Namespace(window=2, tab="tab", out="/tmp/review export.md"),
            [
                "-w",
                "2",
                "-t",
                "tab",
                "-e",
                "prompt export '/tmp/review export.md'",
            ],
        )

    def test_chat_send_uses_selected_runtime_once_on_modern_protocol(self) -> None:
        args = argparse.Namespace(
            window=2,
            tab="tab",
            message_file=str(self.message),
            chat_id=None,
            mode="chat",
            new_chat=False,
            chat_name=None,
            selected_paths=None,
            json=False,
        )
        with mock.patch.object(
            flowctl,
            "run_rp_cli_unchecked",
            return_value=_result('{"chat_id":"chat-1"}\n'),
        ) as run, redirect_stdout(io.StringIO()):
            flowctl.cmd_rp_chat_send(args)
        self.assertEqual(run.call_count, 1)
        self.assertIn("call oracle_send ", run.call_args.args[0][-1])

    def test_ce_chat_continuation_binds_context_and_chat_without_tab(self) -> None:
        args = argparse.Namespace(
            window=2,
            tab=None,
            context_id="0691CA88-A675-4ACA-8AB3-F92D1CA2BD6C",
            message_file=str(self.message),
            chat_id="review-42",
            mode="review",
            new_chat=False,
            chat_name=None,
            selected_paths=None,
            json=False,
        )
        with mock.patch.object(
            flowctl,
            "run_rp_cli",
            return_value=_result('{"chat_id":"review-42"}\n'),
        ) as run, redirect_stdout(io.StringIO()):
            flowctl.cmd_rp_chat_send(args)
        command = run.call_args.args[0]
        self.assertEqual(
            command[:2],
            ["--context-id", "0691CA88-A675-4ACA-8AB3-F92D1CA2BD6C"],
        )
        self.assertNotIn("-t", command)
        self.assertIn('"chat_id":"review-42"', command[-1])
        self.assertIn('"mode":"review"', command[-1])

    def test_chat_id_parser_accepts_ce_markdown_and_json(self) -> None:
        self.assertEqual(
            flowctl.parse_chat_id(
                "## Chat Send ✅\n- **Chat**: `untitled-chat-7741A9` | **Mode**: chat\n"
            ),
            "untitled-chat-7741A9",
        )
        self.assertEqual(
            flowctl.parse_chat_id('{"chat_id":"chat-json-1"}\n'),
            "chat-json-1",
        )


if __name__ == "__main__":
    unittest.main()
