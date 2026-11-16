"""Tracker credential from a configured token command (fn-328 R1).

Every request goes through `bound_executor`, the configured transport a sync
uses, so these tests see what a developer without the env var would see.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import credentials as CR  # noqa: E402
from flowctl_tracker import resolve_verb as RV  # noqa: E402
from flowctl_tracker.facade import helpers as H  # noqa: E402
from flowctl_tracker.types import ErrorClass, Request, TrackerError  # noqa: E402

CRED_VARS = ("JIRA_API_TOKEN", "JIRA_PAT", "LINEAR_API_KEY")
SEEN_SECRET = "leak-me-9999"


def py(code: str, *args: str) -> list[str]:
    return [sys.executable, "-c", code, *args]


class TokenCommand(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = {k: v for k, v in os.environ.items() if k not in CRED_VARS}
        env["JIRA_EMAIL"] = "dev@example.test"
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        seen = mock.patch.object(CR, "_SEEN", set())
        seen.start()
        self.addCleanup(seen.stop)

    def counted(self, token: str) -> tuple[list[str], Path]:
        """A command that prints `token` and logs each run to a fresh file."""
        log = Path(self.tmp.name) / f"runs-{token}.log"
        code = ("import sys; open(sys.argv[1], 'a').write('run\\n'); "
                "print(sys.argv[2])")
        return py(code, str(log), token), log

    def send(self, tracker_type: str, per: dict, url: str, provider: str | None = None):
        seen: list[dict] = []

        class FakeResp:
            status, headers = 200, {}
            def read(self): return b"{}"
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def fake_open(r, timeout=None, **kw):
            seen.append(dict(r.header_items()))
            return FakeResp()

        config = {"tracker": {"type": tracker_type, "perTracker": per}}
        execute = RV.bound_executor(config, RV.default_execute, on_event=lambda _e: None)
        request = Request(provider=provider or tracker_type, op="probe", method="GET",
                          url_or_argv=url)
        with mock.patch("urllib.request.OpenerDirector.open", side_effect=fake_open):
            result = execute(request)
        return result, seen

    def test_jira_cloud_token_comes_from_the_command(self) -> None:
        argv, _log = self.counted("cloud-token-1234")
        result, seen = self.send("jira", {"authScheme": "cloud-basic", "tokenCommand": argv},
                                 "https://acme.atlassian.net/rest/api/2/myself")
        self.assertNotIsInstance(result, TrackerError)
        import base64
        want = "Basic " + base64.b64encode(b"dev@example.test:cloud-token-1234").decode()
        self.assertEqual(seen[0].get("Authorization"), want)

    def test_jira_data_center_pat_comes_from_the_command(self) -> None:
        argv, _log = self.counted("dc-pat-56789")
        _result, seen = self.send("jira", {"authScheme": "bearer-pat", "tokenCommand": argv},
                                  "https://jira.example.test/rest/api/2/myself")
        self.assertEqual(seen[0].get("Authorization"), "Bearer dc-pat-56789")

    def test_linear_key_comes_from_the_command_without_a_shell(self) -> None:
        # A shell would split on ';' and run `b`; argv keeps it one literal word.
        argv = py("import sys; print(sys.argv[1])", "lin_key;echo-x")
        _result, seen = self.send("linear", {"tokenCommand": argv},
                                  "https://api.linear.app/graphql")
        self.assertEqual(seen[0].get("Authorization"), "lin_key;echo-x")

    def test_command_runs_once_per_process(self) -> None:
        argv, log = self.counted("once-token-4321")
        per = {"authScheme": "cloud-basic", "tokenCommand": argv}
        for _ in range(3):
            self.send("jira", per, "https://acme.atlassian.net/rest/api/2/myself")
        self.assertEqual(log.read_text().count("run") if log.exists() else 0, 1)

    def test_concurrent_requests_run_the_command_once(self) -> None:
        # Linear dependency probes send requests from a thread pool on a cold cache.
        import threading
        slow = ("import sys, time; open(sys.argv[1], 'a').write('run\\n'); time.sleep(0.3); "
                "print(sys.argv[2]) if sys.argv[2] != 'fail' else sys.exit(4)")
        for token in ("parallel-token-5555", "fail"):
            with self.subTest(token=token):
                log = Path(self.tmp.name) / f"parallel-{token}.log"
                argv = py(slow, str(log), token)
                gate = threading.Barrier(4)

                def probe() -> None:
                    gate.wait()
                    self.send("linear", {"tokenCommand": argv}, "https://api.linear.app/graphql")

                threads = [threading.Thread(target=probe) for _ in range(4)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
                self.assertEqual(log.read_text().count("run") if log.exists() else 0, 1)

    def test_environment_variable_wins(self) -> None:
        argv, log = self.counted("unused-token-1111")
        with mock.patch.dict(os.environ, {"JIRA_API_TOKEN": "env-token-2222"}):
            _result, seen = self.send("jira", {"authScheme": "cloud-basic", "tokenCommand": argv},
                                      "https://acme.atlassian.net/rest/api/2/myself")
        import base64
        want = "Basic " + base64.b64encode(b"dev@example.test:env-token-2222").decode()
        self.assertEqual(seen[0].get("Authorization"), want)
        self.assertFalse(log.exists())

    def test_resolved_token_is_redacted(self) -> None:
        argv, _log = self.counted("redact-token-7777")
        self.send("linear", {"tokenCommand": argv}, "https://api.linear.app/graphql")
        self.assertEqual(CR.redact("echo redact-token-7777"), "echo <redacted>")

    def assert_auth_failure(self, argv: list[str], cause: str) -> None:
        result, seen = self.send("linear", {"tokenCommand": argv},
                                 "https://api.linear.app/graphql")
        self.assertIsInstance(result, TrackerError)
        self.assertIs(result.cls, ErrorClass.AUTH)
        self.assertEqual(result.subtype, "resolve")
        self.assertIn("token command", result.message)
        self.assertIn(cause, result.message)
        self.assertNotIn(SEEN_SECRET, result.message)
        self.assertEqual(seen, [])  # nothing was sent

    def test_non_zero_exit_fails_without_echoing_output(self) -> None:
        code = ("import sys; print(sys.argv[1]); sys.stderr.write(sys.argv[1]); "
                "sys.exit(3)")
        self.assert_auth_failure(py(code, SEEN_SECRET), "exited 3")

    def test_missing_executable_fails(self) -> None:
        self.assert_auth_failure(["/nonexistent/flow-token-helper"], "not found")

    def test_empty_output_fails(self) -> None:
        self.assert_auth_failure(py("print('  ')"), "empty")

    def test_timeout_fails(self) -> None:
        with mock.patch.object(CR, "TOKEN_COMMAND_TIMEOUT_S", 0.5, create=True):
            self.assert_auth_failure(py("import time; time.sleep(5)"), "timed out")

    def test_linear_with_a_token_command_is_not_on_the_mcp_rung(self) -> None:
        argv, _log = self.counted("mcp-check-3333")
        config = {"tracker": {"type": "linear", "perTracker": {"tokenCommand": argv}}}
        self.assertFalse(H.on_mcp_rung(config))


if __name__ == "__main__":
    unittest.main()
