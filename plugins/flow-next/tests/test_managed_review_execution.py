"""Packaged adapters consume the local provider without invoking ambient CLIs."""

import argparse
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import flowctl


class ManagedReviewExecutionTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.response = {"schemaVersion": 1, "output": "<verdict>SHIP</verdict>",
                         "stderr": "", "sessionId": "managed-1", "exitCode": 0}
        self.status = 200
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.requests.append((self.headers.get("Authorization"),
                                       json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                self.send_response(owner.status)
                if owner.status == 307:
                    self.send_header("Location", "/leaked-credential")
                self.end_headers()
                self.wfile.write(json.dumps(owner.response).encode())

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.environment = mock.patch.dict(os.environ, {
            "FLOW_REVIEW_EXECUTION_URL": f"http://127.0.0.1:{self.server.server_port}/review",
            "FLOW_REVIEW_EXECUTION_TOKEN": "session-secret",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.thread.join)
        self.addCleanup(self.server.shutdown)

    def call(self, backend="codex", session_id=None, **kwargs):
        adapter = getattr(flowctl, f"_{backend}_run_exec")
        return adapter("review this", session_id=session_id, repo_root=Path.cwd(),
                       spec=flowctl.BackendSpec(backend, "chosen-model", "high"),
                       resolution_out=kwargs.pop("resolution_out", {}),
                       args=argparse.Namespace(json=True, sandbox="read-only"), **kwargs)

    def test_all_packaged_adapters_use_scoped_provider(self):
        for backend in ("codex", "claude", "cursor", "copilot"):
            with self.subTest(backend=backend), mock.patch.object(
                flowctl, f"run_{backend}_exec", side_effect=AssertionError("ambient CLI")
            ):
                output, sid, rc, err = self.call(backend)
                self.assertEqual((sid, rc, err), ("managed-1", 0, ""))
                self.assertEqual(flowctl.parse_codex_verdict(output), "SHIP")
                auth, request = self.requests[-1]
                self.assertEqual(auth, "Bearer session-secret")
                self.assertEqual((request["backend"], request["model"], request["effort"]),
                                 (backend, "chosen-model", "high"))
                self.assertEqual(request["permissionMode"], "read-only")

    def test_repeat_request_has_same_id(self):
        self.call()
        self.call()
        self.assertEqual(self.requests[0][1]["requestId"], self.requests[1][1]["requestId"])
        self.call(session_id="managed-1")
        self.assertNotEqual(self.requests[0][1]["requestId"], self.requests[2][1]["requestId"])

    def test_new_review_round_does_not_reuse_previous_execution(self):
        for scope in ("reservation-one", "reservation-two"):
            flowctl._codex_run_exec(
                "same review", session_id=None, repo_root=Path.cwd(),
                spec=flowctl.BackendSpec("codex", "chosen-model", "high"), resolution_out={},
                args=argparse.Namespace(json=True, managed_review_request_scope=scope),
            )
        self.assertNotEqual(self.requests[0][1]["requestId"], self.requests[1][1]["requestId"])

    def test_adapter_backend_wins_over_lenient_foreign_spec(self):
        flowctl._codex_run_exec(
            "review", session_id=None, repo_root=Path.cwd(),
            spec=flowctl.BackendSpec("copilot", "chosen-model", "high"), resolution_out={},
            args=argparse.Namespace(json=True),
        )
        self.assertEqual(self.requests[0][1]["backend"], "codex")

    def test_resume_failure_is_explicit_and_cannot_carry_verdict(self):
        self.response.update(exitCode=2, resumeFailed=True, stderr="cannot resume")
        resolution = {}
        output, _, rc, _ = self.call(session_id="managed-1", resume_only=True, resolution_out=resolution)
        self.assertEqual((output, rc), ("", 2))
        self.assertTrue(resolution["resume_failed"])
        self.assertTrue(self.requests[0][1]["resumeOnly"])

    def test_invalid_provider_response_never_falls_back(self):
        for response in ({}, {**self.response, "exitCode": False},
                         {**self.response, "resumeFailed": True}):
            self.response = response
            with mock.patch.object(flowctl, "run_codex_exec", side_effect=AssertionError("CLI")):
                output, _, rc, err = self.call()
                self.assertEqual((output, rc), ("", 2))
                self.assertNotIn("session-secret", err)

    def test_nonlocal_and_empty_urls_fail_without_request(self):
        for url in ("", "https://example.com/review", "http://example.com/review"):
            with mock.patch.dict(os.environ, {"FLOW_REVIEW_EXECUTION_URL": url}):
                self.assertEqual(self.call()[2], 2)
        self.assertEqual(self.requests, [])

    def test_absent_configuration_preserves_cli(self):
        with mock.patch.dict(os.environ, clear=True), mock.patch.object(
            flowctl, "run_codex_exec", return_value=("standalone", None, 0, "")
        ) as run:
            self.assertEqual(self.call()[0], "standalone")
            run.assert_called_once()

    def test_redirect_does_not_forward_scoped_credential(self):
        self.status = 307
        self.assertEqual(self.call()[2], 2)
        self.assertEqual(len(self.requests), 1)

    def test_missing_token_refuses_before_request(self):
        with mock.patch.dict(os.environ, {"FLOW_REVIEW_EXECUTION_TOKEN": ""}):
            self.assertEqual(self.call()[2], 2)
        self.assertEqual(self.requests, [])

    def test_invalid_ports_and_control_characters_refuse_before_pipeline(self):
        from test_claude_review_commands import _run_cli
        for endpoint in ("http://127.0.0.1:bogus/review", "http://127.0.0.1:65536/review",
                         "http://127.0.0.1:0/review", "http://127.0.0.1/review\n"):
            with self.subTest(endpoint=repr(endpoint)), mock.patch.dict(
                os.environ, {"FLOW_REVIEW_EXECUTION_URL": endpoint}
            ), mock.patch.object(flowctl, "_backend_completion_review") as pipeline:
                code, _, _ = _run_cli("codex", "completion-review", "fn-1", "--json",
                                      "--require-managed-execution")
                self.assertEqual(code, 2)
                pipeline.assert_not_called()

    def test_transport_timeout_truncation_and_oversize_fail_closed(self):
        for failure in (TimeoutError(), http.client.IncompleteRead(b"private", 20)):
            with mock.patch.object(flowctl.urllib.request.OpenerDirector, "open",
                                   side_effect=failure):
                self.assertEqual(self.call()[2], 2)
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"x" * (16 * 1024 * 1024 + 1)
        with mock.patch.object(flowctl.urllib.request.OpenerDirector, "open", return_value=response):
            self.assertEqual(self.call()[2], 2)
        response.__enter__.return_value.read.assert_called_once_with(16 * 1024 * 1024 + 1)
        for raw in (b"not-json", b"[" * 20000 + b"]" * 20000):
            response.__enter__.return_value.read.return_value = raw
            with mock.patch.object(flowctl.urllib.request.OpenerDirector, "open", return_value=response):
                self.assertEqual(self.call()[2], 2)

    def test_proxy_environment_is_ignored(self):
        with mock.patch.dict(os.environ, {"http_proxy": "http://127.0.0.1:1",
                                         "HTTP_PROXY": "http://127.0.0.1:1", "NO_PROXY": ""}):
            self.assertEqual(self.call()[2], 0)
        self.assertEqual(len(self.requests), 1)

    def test_boolean_schema_version_is_rejected(self):
        self.response["schemaVersion"] = True
        self.assertEqual(self.call()[2], 2)

    def test_continuation_only_passes_require_the_original_session(self):
        for backend in ("codex", "claude", "cursor", "copilot"):
            with self.subTest(backend=backend):
                output = flowctl._dispatch_session_pass(
                    backend, "continue review", session_id="managed-1",
                    spec_arg=backend, use_json=True, fail_label="pass",
                )
                self.assertEqual(flowctl.parse_codex_verdict(output), "SHIP")
                self.assertTrue(self.requests[-1][1]["resumeOnly"])
        self.response["sessionId"] = "different-session"
        self.assertEqual(self.call(session_id="managed-1", resume_only=True)[2], 2)

    def test_managed_command_does_not_probe_local_backend_cli(self):
        from test_claude_review_commands import _flow_repo, _run_cli, EPIC_ID
        real_which = shutil.which
        def which(name, *args, **kwargs):
            if name in ("codex", "claude", "cursor-agent", "copilot"):
                raise AssertionError("managed execution probed local CLI")
            return real_which(name, *args, **kwargs)
        for backend in ("codex", "claude", "cursor", "copilot"):
            with self.subTest(backend=backend), _flow_repo() as (repo, base), \
                    mock.patch.object(flowctl.shutil, "which", side_effect=which):
                code, _, err = _run_cli(backend, "completion-review", EPIC_ID,
                                        "--base", base, "--receipt", str(repo / "receipt.json"),
                                        "--json", "--require-managed-execution")
                self.assertEqual(code, 0, err)

    @unittest.skipIf(os.name == "nt", "Codex installer is a bash script")
    def test_real_codex_install_runs_managed_and_standalone_receipts(self):
        from test_claude_review_commands import _flow_repo, EPIC_ID
        source = Path(flowctl.__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as temporary:
            install = Path(temporary) / "codex-profile"
            install.mkdir()
            env = {**os.environ, "CODEX_HOME": str(install)}
            installed = subprocess.run(["bash", str(source / "scripts/install-codex.sh")],
                                       env=env, capture_output=True, text=True, timeout=120)
            self.assertEqual(installed.returncode, 0, installed.stderr)
            launcher = install / "scripts/flowctl"
            self.assertEqual((install / "scripts/flowctl.py").read_bytes(),
                             Path(flowctl.__file__).read_bytes())
            help_result = subprocess.run([str(launcher), "claude", "completion-review", "--help"],
                                         env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(help_result.returncode, 0, help_result.stderr)
            self.assertIn("--require-managed-execution", help_result.stdout)
            # An executable CLI double proves the full standalone subprocess path.
            binary = Path(temporary) / "bin"
            binary.mkdir()
            marker = binary / "called"
            stub = binary / "claude"
            stub.write_text(
                f"#!{sys.executable}\nimport json, pathlib, sys\n"
                f"pathlib.Path({str(marker)!r}).write_text(sys.stdin.read())\n"
                "print(json.dumps({'type':'result','subtype':'success','is_error':False,"
                "'result':'<verdict>SHIP</verdict>','session_id':'standalone-1'}))\n",
                encoding="utf-8",
            )
            stub.chmod(0o700)
            env["PATH"] = str(binary) + os.pathsep + env["PATH"]
            for mode in ("managed", "failed", "standalone", "required-missing"):
                with self.subTest(mode=mode), _flow_repo() as (repo, base):
                    receipt = repo / "receipt.json"
                    invocation_env = dict(env)
                    if mode in ("standalone", "required-missing"):
                        invocation_env.pop("FLOW_REVIEW_EXECUTION_URL", None)
                        invocation_env.pop("FLOW_REVIEW_EXECUTION_TOKEN", None)
                    self.response["exitCode"] = 2 if mode == "failed" else 0
                    argv = [str(launcher), "claude", "completion-review", EPIC_ID,
                            "--base", base, "--receipt", str(receipt), "--json"]
                    if mode != "standalone":
                        argv.append("--require-managed-execution")
                    result = subprocess.run(argv, env=invocation_env, cwd=repo,
                                            capture_output=True, text=True, timeout=30)
                    if mode in ("failed", "required-missing"):
                        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                        self.assertFalse(receipt.exists())
                    else:
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        published = json.loads(receipt.read_text())
                        self.assertEqual(published["verdict"], "SHIP")
                        self.assertEqual(published["session_id"],
                                         "standalone-1" if mode == "standalone" else "managed-1")
                    if mode in ("managed", "failed"):
                        self.assertFalse(marker.exists())
            self.assertIn("review", marker.read_text().lower())

    def test_claude_diff_delivery_precedes_hook(self):
        with mock.patch.object(flowctl, "_claude_materialise_review_diff", return_value=Path("/tmp/review.diff")):
            flowctl._claude_run_exec(
                "review", session_id=None, repo_root=Path.cwd(),
                spec=flowctl.BackendSpec("claude", "chosen-model", "high"), resolution_out={},
                args=argparse.Namespace(json=True, claude_range=("base", "head", "review")),
            )
        self.assertIn("/tmp/review.diff", self.requests[0][1]["prompt"])

    def test_real_packaged_command_keeps_receipt_and_refunds_failed_transport(self):
        from test_claude_review_commands import _flow_repo, _impl_review
        self.response["output"] = "<verdict>NEEDS_WORK</verdict>"
        with _flow_repo() as (repo, base):
            receipt = repo / "managed-receipt.json"
            with mock.patch.object(flowctl, "run_claude_exec", side_effect=AssertionError("ambient CLI")):
                code, output, err = _impl_review(repo, base, receipt)
            self.assertEqual(code, 0, err)
            result = json.loads(output)
            published = json.loads(receipt.read_text())
            self.assertEqual(result["verdict"], "NEEDS_WORK")
            self.assertEqual(published["mode"], "claude")
            self.assertEqual(published["session_id"], "managed-1")
            self.assertEqual(published["model"], self.requests[0][1]["model"])
            self.assertEqual(result["review_rounds"], 1)
        with _flow_repo() as (repo, base):
            self.response.update(exitCode=2, stderr="account unavailable")
            receipt = repo / "failed-receipt.json"
            code, _, _ = _impl_review(repo, base, receipt)
            self.assertEqual(code, 2)
            self.assertFalse(receipt.exists())
            self.assertEqual(flowctl._current_review_rounds(
                "fn-1-claude-demo", "impl", task_id="fn-1-claude-demo.1", use_json=True), 0)

    def test_required_managed_completion_refuses_before_pipeline_without_valid_scope(self):
        from test_claude_review_commands import _run_cli
        for backend in ("codex", "claude", "cursor", "copilot"):
            for environment in ({}, {"FLOW_REVIEW_EXECUTION_URL": "http://127.0.0.1/review"},
                                {"FLOW_REVIEW_EXECUTION_URL": "http://example.com/review",
                                 "FLOW_REVIEW_EXECUTION_TOKEN": "secret"}):
                with self.subTest(backend=backend, environment=list(environment)), \
                        mock.patch.dict(os.environ, environment, clear=True), \
                        mock.patch.object(flowctl, "_backend_completion_review") as pipeline:
                    code, output, _ = _run_cli(
                        backend, "completion-review", "fn-1", "--json",
                        "--require-managed-execution",
                    )
                    self.assertEqual(code, 2)
                    self.assertIn("managed execution required", json.loads(output)["error"])
                    pipeline.assert_not_called()
        self.assertEqual(self.requests, [])

    def test_required_managed_completion_publishes_upstream_receipt(self):
        from test_claude_review_commands import _flow_repo, _run_cli, EPIC_ID
        with _flow_repo() as (repo, base):
            receipt = repo / "managed-completion.json"
            with mock.patch.object(flowctl, "run_claude_exec", side_effect=AssertionError("ambient CLI")):
                code, output, err = _run_cli(
                    "claude", "completion-review", EPIC_ID, "--base", base,
                    "--receipt", str(receipt), "--json", "--require-managed-execution",
                )
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(output)["verdict"], "SHIP")
            published = json.loads(receipt.read_text())
            self.assertEqual(published["type"], "completion_review")
            self.assertEqual(published["mode"], "claude")
            self.assertEqual(published["session_id"], "managed-1")

    def test_flat_flowctl_install_contains_the_hook_and_required_scope_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            installed = Path(directory) / "flowctl.py"
            shutil.copy2(Path(flowctl.__file__), installed)
            script = (
                "import json, os, runpy, sys; namespace=runpy.run_path(sys.argv[1]); "
                "result=namespace['execute_review'](backend='claude', model='selected', "
                "effort='high', prompt='flat install', repository_path=os.getcwd(), "
                "session_id=None, resume_only=False, timeout=5, resolution_out={}); "
                "print(json.dumps(result))"
            )
            managed = subprocess.run(
                [sys.executable, "-c", script, str(installed)],
                cwd=directory, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(managed.returncode, 0, managed.stderr)
            self.assertEqual(json.loads(managed.stdout)[0], "<verdict>SHIP</verdict>")
            environment = dict(os.environ)
            environment.pop("FLOW_REVIEW_EXECUTION_URL", None)
            environment.pop("FLOW_REVIEW_EXECUTION_TOKEN", None)
            refused = subprocess.run(
                [sys.executable, str(installed), "codex", "completion-review", "fn-1",
                 "--require-managed-execution", "--json"],
                cwd=directory, capture_output=True, text=True, timeout=30, env=environment,
            )
            self.assertEqual(refused.returncode, 2)
            self.assertIn("managed execution required", json.loads(refused.stdout)["error"])


if __name__ == "__main__":
    unittest.main()
