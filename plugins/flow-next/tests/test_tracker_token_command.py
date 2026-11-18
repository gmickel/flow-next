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

CRED_VARS = ("JIRA_API_TOKEN", "JIRA_PAT", "LINEAR_API_KEY",
             "FLOW_TRACKER_TOKEN_COMMAND_LINEAR", "FLOW_TRACKER_TOKEN_COMMAND_JIRA")
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
                config = {"tracker": {"type": "linear",
                                      "perTracker": {"tokenCommand": py(slow, str(log), token)}}}
                execute = RV.bound_executor(config, RV.default_execute, on_event=lambda _e: None)
                gate = threading.Barrier(4)

                class FakeResp:
                    status, headers = 200, {}
                    def read(self): return b"{}"
                    def __enter__(self): return self
                    def __exit__(self, *a): return False

                def probe(gate=gate, execute=execute) -> None:
                    gate.wait()
                    execute(Request(provider="linear", op="probe", method="GET",
                                    url_or_argv="https://api.linear.app/graphql"))

                # One patch around every thread: patching per thread is not thread-safe.
                with mock.patch("urllib.request.OpenerDirector.open",
                                side_effect=lambda *a, **k: FakeResp()):
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


class MachineLocalTokenCommand(unittest.TestCase):
    """fn-332: FLOW_TRACKER_TOKEN_COMMAND_<TRACKER> comes before the tracked tokenCommand."""

    setUp = TokenCommand.setUp
    counted = TokenCommand.counted
    send = TokenCommand.send

    LINEAR = "https://api.linear.app/graphql"
    JIRA = "https://acme.atlassian.net/rest/api/2/myself"

    def local(self, tracker: str, argv: list[str]):
        import json
        return mock.patch.dict(os.environ, {f"FLOW_TRACKER_TOKEN_COMMAND_{tracker}": json.dumps(argv)})

    def test_linear_local_command_wins_over_the_tracked_one(self) -> None:
        local, _ = self.counted("local-lin-4444")
        tracked, tracked_log = self.counted("tracked-lin-5555")
        with self.local("LINEAR", local):
            _result, seen = self.send("linear", {"tokenCommand": tracked}, self.LINEAR)
        self.assertEqual(seen[0].get("Authorization"), "local-lin-4444")
        self.assertFalse(tracked_log.exists())

    def test_jira_local_command_needs_no_tracked_config(self) -> None:
        import base64
        local, _ = self.counted("local-jira-6666")
        with self.local("JIRA", local):
            _result, seen = self.send("jira", {"authScheme": "cloud-basic"}, self.JIRA)
        want = "Basic " + base64.b64encode(b"dev@example.test:local-jira-6666").decode()
        self.assertEqual(seen[0].get("Authorization"), want)

    def test_token_variable_still_wins_over_both(self) -> None:
        local, local_log = self.counted("local-unused-7777")
        tracked, tracked_log = self.counted("tracked-unused-8888")
        with self.local("LINEAR", local), \
             mock.patch.dict(os.environ, {"LINEAR_API_KEY": "env-key-9999"}):
            _result, seen = self.send("linear", {"tokenCommand": tracked}, self.LINEAR)
        self.assertEqual(seen[0].get("Authorization"), "env-key-9999")
        self.assertFalse(local_log.exists())
        self.assertFalse(tracked_log.exists())

    def test_empty_variable_counts_as_unset(self) -> None:
        tracked, _ = self.counted("tracked-used-1212")
        with mock.patch.dict(os.environ, {"FLOW_TRACKER_TOKEN_COMMAND_LINEAR": ""}):
            _result, seen = self.send("linear", {"tokenCommand": tracked}, self.LINEAR)
        self.assertEqual(seen[0].get("Authorization"), "tracked-used-1212")

    def test_failed_local_command_does_not_fall_back(self) -> None:
        tracked, tracked_log = self.counted("tracked-never-1313")
        failing = py("import sys; print(sys.argv[1]); sys.exit(3)", SEEN_SECRET)
        with self.local("LINEAR", failing):
            result, seen = self.send("linear", {"tokenCommand": tracked}, self.LINEAR)
        self.assertIsInstance(result, TrackerError)
        self.assertIs(result.cls, ErrorClass.AUTH)
        self.assertIn("exited 3", result.message)
        self.assertNotIn(SEEN_SECRET, result.message)
        self.assertEqual(seen, [])
        self.assertFalse(tracked_log.exists())

    def test_malformed_value_names_the_variable_without_echoing_it(self) -> None:
        tracked, tracked_log = self.counted("tracked-never-1414")
        for raw in ('["leak-me-9999"', '"leak-me-9999"', "[]", '["", "leak-me-9999"]', '[1, "leak-me-9999"]'):
            with self.subTest(raw=raw), \
                 mock.patch.dict(os.environ, {"FLOW_TRACKER_TOKEN_COMMAND_LINEAR": raw}):
                result, seen = self.send("linear", {"tokenCommand": tracked}, self.LINEAR)
                self.assertIsInstance(result, TrackerError)
                self.assertIs(result.cls, ErrorClass.AUTH)
                self.assertIn("FLOW_TRACKER_TOKEN_COMMAND_LINEAR", result.message)
                self.assertNotIn(SEEN_SECRET, result.message)
                self.assertEqual(seen, [])
        self.assertFalse(tracked_log.exists())

    def test_missing_local_executable_names_the_variable_not_the_path(self) -> None:
        with self.local("LINEAR", ["/nonexistent/fn332-private-machine/token-helper"]):
            result, seen = self.send("linear", {}, self.LINEAR)
        self.assertIsInstance(result, TrackerError)
        self.assertIs(result.cls, ErrorClass.AUTH)
        self.assertIn("not found", result.message)
        self.assertIn("FLOW_TRACKER_TOKEN_COMMAND_LINEAR", result.message)
        self.assertNotIn("fn332-private-machine", result.message)
        self.assertEqual(seen, [])

    def test_local_command_runs_once_per_process(self) -> None:
        local, log = self.counted("local-once-1515")
        with self.local("LINEAR", local):
            for _ in range(3):
                self.send("linear", {}, self.LINEAR)
        self.assertEqual(log.read_text().count("run") if log.exists() else 0, 1)

    def test_linear_with_a_local_command_is_not_on_the_mcp_rung(self) -> None:
        local, _ = self.counted("local-mcp-1616")
        with self.local("LINEAR", local):
            self.assertFalse(H.on_mcp_rung({"tracker": {"type": "linear", "perTracker": {}}}))


if __name__ == "__main__":
    unittest.main()
