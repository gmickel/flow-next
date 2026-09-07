"""Packaged adapters consume the local provider without invoking ambient CLIs."""

import argparse
import json
import os
from pathlib import Path
import sys
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


if __name__ == "__main__":
    unittest.main()
