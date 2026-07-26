"""Persisted transport policy wiring, TTL re-probe reachability, provider
classification matrix, and stderr observability (fn-139 completion-review
gaps 1/2/4/5/6).
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import classify as C  # noqa: E402
from flowctl_tracker import executor as X  # noqa: E402
from flowctl_tracker import resolve_verb as RV  # noqa: E402
from flowctl_tracker.types import (DEFAULT_TIMEOUT_S, ErrorClass, Request,  # noqa: E402
                                   Response, TrackerError)


def resp(status: int, body: bytes = b"", headers: dict | None = None) -> Response:
    return Response(status, headers or {}, body, 0.01)


def iso_ago(hours: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat() \
        .replace("+00:00", "Z")


class BoundExecutorCarriesThePersistedPolicy(unittest.TestCase):
    """Gap 1/4: authScheme, sslVerify (+env override) and the R7 bounds must
    reach real requests - adapters calling execute bare dropped all of them."""

    def _bind_and_call(self, config: dict) -> dict:
        seen = {}

        def recorder(request, **kwargs):
            seen.update(kwargs)
            seen["timeout_s"] = request.timeout_s
            return resp(200, b"{}")

        with mock.patch.object(RV, "default_execute", recorder):
            bound = RV.bound_executor(config, RV.default_execute)
            bound(Request(provider="jira", op="read", method="GET",
                          url_or_argv="https://x.example.com/rest/api/2/x"))
        return seen

    def test_auth_scheme_and_ssl_verify_reach_the_executor(self) -> None:
        seen = self._bind_and_call({"tracker": {"type": "jira", "perTracker": {
            "authScheme": "bearer-pat", "sslVerify": False}}})
        self.assertEqual(seen["auth_scheme"], "bearer-pat")
        self.assertFalse(seen["verify_tls"])
        self.assertIsNotNone(seen["on_event"], "the stderr sink is always bound")

    def test_jira_ssl_verify_env_override_wins(self) -> None:
        cfg = {"tracker": {"type": "jira", "perTracker": {"sslVerify": True}}}
        with mock.patch.dict(os.environ, {"JIRA_SSL_VERIFY": "false"}):
            seen = self._bind_and_call(cfg)
        self.assertFalse(seen["verify_tls"])

    def test_env_override_is_jira_only(self) -> None:
        cfg = {"tracker": {"type": "gitlab", "perTracker": {"sslVerify": True}}}
        with mock.patch.dict(os.environ, {"JIRA_SSL_VERIFY": "false"}):
            seen = self._bind_and_call(cfg)
        self.assertTrue(seen["verify_tls"])

    def test_transport_bounds_are_wired_and_validated(self) -> None:
        seen = self._bind_and_call({"tracker": {"type": "jira", "perTracker": {},
                                    "transport": {"timeoutS": 12.5, "maxRetries": 1,
                                                  "backoffCapS": 5, "concurrency": 2}}})
        self.assertEqual(seen["timeout_s"], 12.5)
        self.assertEqual(seen["max_retries"], 1)
        self.assertEqual(seen["backoff_cap_s"], 5.0)
        self.assertEqual(seen["concurrency"], 2)

    def test_garbage_bounds_fall_back_to_defaults(self) -> None:
        seen = self._bind_and_call({"tracker": {"type": "jira", "perTracker": {},
                                    "transport": {"timeoutS": "soon", "maxRetries": 99,
                                                  "backoffCapS": -1, "concurrency": 0}}})
        self.assertEqual(seen["timeout_s"], DEFAULT_TIMEOUT_S)
        self.assertIsNone(seen["max_retries"])
        self.assertIsNone(seen["backoff_cap_s"])
        self.assertIsNone(seen["concurrency"])

    def test_executor_clamps_override_abuse(self) -> None:
        self.assertEqual(X._backoff_delay(0, 9999, 5.0), 5.0)
        self.assertIs(X._slots_for(0), X._SLOTS, "invalid cap keeps the default")
        self.assertIs(X._slots_for(None), X._SLOTS)


class TtlReprobeIsReachable(unittest.TestCase):
    """Gap 2: capabilities_stale/ttl-reprobe had no production caller."""

    def _cfg(self, stamp_hours_ago: float) -> dict:
        return {"tracker": {"type": "gitlab",
                            "perTracker": {"project": "g/p", "host": "gitlab.com"},
                            "resolved": {
                                "resolvedAt": iso_ago(stamp_hours_ago),
                                "scopeResolvedAt": {
                                    "destination": iso_ago(stamp_hours_ago),
                                    "capabilities": iso_ago(stamp_hours_ago)},
                                "destination": {"projectId": 1, "projectPath": "g/p",
                                                "host": "gitlab.com", "namespaceId": 7},
                                "capabilities": {"attachments": True, "blockedBy": True,
                                                 "subIssues": False, "deleteIssue": True,
                                                 "_source": {"gitlabPlan": "ultimate_trial"}},
                            }}}

    def _run(self, cfg: dict, probe_result) -> tuple:
        with tempfile.TemporaryDirectory() as td:
            flow = Path(td)
            (flow / "config.json").write_text(json.dumps(cfg), encoding="utf-8")

            def execute(request):
                assert request.op == "probe-plan", request.op
                return probe_result

            with mock.patch.object(sys, "stderr", io.StringIO()) as err:
                payload, code = RV.run(flow, execute=execute)
            on_disk = json.loads((flow / "config.json").read_text(encoding="utf-8"))
        return json.loads(payload), code, on_disk, err.getvalue()

    def test_stale_capabilities_trigger_exactly_one_probe(self) -> None:
        out, code, on_disk, err = self._run(
            self._cfg(48), resp(200, json.dumps({"id": 7, "plan": "free"}).encode()))
        self.assertEqual(code, 0)
        caps = on_disk["tracker"]["resolved"]["capabilities"]
        self.assertFalse(caps["blockedBy"], "trial expired -> degraded")
        self.assertEqual(out["degraded"]["capability"], "blockedBy")
        self.assertTrue(out["probe"]["ok"])
        self.assertIn("ttl-reprobe", err)

    def test_fresh_capabilities_do_not_probe(self) -> None:
        calls = {"n": 0}

        def execute(request):
            calls["n"] += 1
            return resp(200, b"{}")

        cfg = self._cfg(1)
        with tempfile.TemporaryDirectory() as td:
            flow = Path(td)
            (flow / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
            with mock.patch.object(sys, "stderr", io.StringIO()):
                RV.run(flow, execute=execute)
        self.assertEqual(calls["n"], 0)

    def test_failed_probe_keeps_prior_and_reports_probe_never_degraded(self) -> None:
        out, code, on_disk, _ = self._run(
            self._cfg(48), TrackerError(ErrorClass.AUTH, "transient 403"))
        self.assertEqual(code, 0, "a failed re-probe is NOT a failed resolve")
        caps = on_disk["tracker"]["resolved"]["capabilities"]
        self.assertTrue(caps["blockedBy"], "prior value intact")
        self.assertFalse(out["probe"]["ok"])
        self.assertIsNone(out["degraded"])

    def test_non_gitlab_never_reprobes(self) -> None:
        cfg = {"tracker": {"type": "github", "perTracker": {}, "resolved": {
            "resolvedAt": iso_ago(999),
            "scopeResolvedAt": {"destination": iso_ago(999),
                                "capabilities": iso_ago(999)},
            "destination": {"owner": "g", "repo": "r"},
            "capabilities": {"attachments": False, "blockedBy": False,
                             "subIssues": True, "deleteIssue": False}}}}
        calls = {"n": 0}

        def execute(request):
            calls["n"] += 1
            return resp(200, b"{}")

        with tempfile.TemporaryDirectory() as td:
            flow = Path(td)
            (flow / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
            with mock.patch.object(sys, "stderr", io.StringIO()):
                RV.run(flow, execute=execute)
        self.assertEqual(calls["n"], 0)


class ProviderClassificationMatrix(unittest.TestCase):
    """Gap 5: table-driven recorded shapes - success/auth/rate-limit/not-found
    for every provider, plus each provider's measured oddity."""

    MATRIX = {
        "github": {
            "success": (resp(200, b'{"id": 1}'), None),
            "auth": (resp(401, b'{"message":"Bad credentials"}'), ErrorClass.AUTH),
            "rate_limited": (resp(403, b'{"message":"API rate limit exceeded"}',
                                  {"x-ratelimit-remaining": "0"}),
                             ErrorClass.RATE_LIMITED),
            "not_found": (resp(404, b'{"message":"Not Found"}'), ErrorClass.NOT_FOUND),
        },
        "gitlab": {
            "success": (resp(201, b'{"iid": 5}'), None),
            "auth": (resp(401, b'{"message":"401 Unauthorized"}'), ErrorClass.AUTH),
            "rate_limited": (resp(429, b"", {"Retry-After": "7"}),
                             ErrorClass.RATE_LIMITED),
            "not_found": (resp(404, b'{"message":"404 Project Not Found"}'),
                          ErrorClass.NOT_FOUND),
            "capability": (resp(403, b'{"message":"Blocked issues not available '
                                      b'for current license"}'),
                           ErrorClass.CAPABILITY),
        },
        "linear": {
            "success": (resp(200, b'{"data":{"issue":{"id":"x"}}}'), None),
            "auth": (resp(200, b'{"errors":[{"extensions":'
                               b'{"code":"AUTHENTICATION_ERROR"}}]}'),
                     ErrorClass.AUTH),
            "rate_limited": (resp(200, b'{"errors":[{"extensions":'
                                       b'{"code":"RATELIMITED"}}]}'),
                             ErrorClass.RATE_LIMITED),
            "not_found": (resp(200, b'{"errors":[{"message":'
                                    b'"Entity not found: Issue"}]}'),
                          ErrorClass.NOT_FOUND),
            "malformed": (resp(200, b"<html>gateway error</html>"),
                          ErrorClass.TRANSPORT),
        },
        "jira": {
            "success": (resp(204, b""), None),
            "auth": (resp(401, b'{"errorMessages":["auth"]}'), ErrorClass.AUTH),
            "rate_limited": (resp(429, b"", {"Retry-After": "3"}),
                             ErrorClass.RATE_LIMITED),
            "not_found": (resp(404, b'{"errorMessages":["Issue does not exist"]}'),
                          ErrorClass.NOT_FOUND),
            "xsrf": (resp(404, b"XSRF check failed"), ErrorClass.INVALID_INPUT),
        },
    }

    def test_every_provider_row(self) -> None:
        for provider, rows in self.MATRIX.items():
            for case, (response, expected) in rows.items():
                with self.subTest(provider=provider, case=case):
                    out = C.classify(provider, response)
                    if expected is None:
                        self.assertIsNone(out)
                    else:
                        self.assertIsInstance(out, TrackerError)
                        self.assertIs(out.cls, expected)


class StderrObservability(unittest.TestCase):
    """Gap 6: attempts, actual backoff delay, scopes, downgrades and probe
    failures all land on stderr, redacted; stdout stays the envelope."""

    def test_attempt_and_backoff_events_carry_the_actual_delay(self) -> None:
        events = []
        calls = {"n": 0}

        def fake_http(*a, **kw):
            calls["n"] += 1
            return resp(429, b"", {"Retry-After": "2"})

        with mock.patch.object(X, "_http", side_effect=fake_http), \
             mock.patch.object(X.time, "sleep"):
            X.execute(Request(provider="github", op="read", method="GET",
                              url_or_argv="https://api.github.com/x",
                              idempotent=True),
                      on_event=events.append)
        attempts = [e for e in events if e.startswith("attempt")]
        backoffs = [e for e in events if "backoff_s=" in e]
        self.assertEqual(len(attempts), 3, events)
        self.assertEqual(len(backoffs), 2, events)
        self.assertIn("backoff_s=2.00", backoffs[0], "the ACTUAL delay, not a hint")

    def test_scope_events_reach_stderr_and_stdout_stays_json(self) -> None:
        cfg = {"tracker": {"type": "github", "perTracker": {}}}
        with tempfile.TemporaryDirectory() as td:
            flow = Path(td)
            (flow / "config.json").write_text(json.dumps(cfg), encoding="utf-8")

            def execute(request):
                return resp(200, json.dumps(
                    {"name": "r", "owner": {"login": "o"}}).encode())

            with mock.patch.object(sys, "stderr", io.StringIO()) as err:
                payload, code = RV.run(flow, execute=execute)
        self.assertEqual(code, 0)
        json.loads(payload)  # stdout payload parses clean
        self.assertIn("scope=destination", err.getvalue())
        self.assertIn("scope=capabilities", err.getvalue())

    def test_sink_output_is_redacted(self) -> None:
        from flowctl_tracker import credentials as CR
        saved = set(CR._SEEN)
        self.addCleanup(lambda: (CR._SEEN.clear(), CR._SEEN.update(saved)))
        CR._remember("s3cret-token-value")
        with mock.patch.object(sys, "stderr", io.StringIO()) as err:
            RV._stderr_sink("event mentioning s3cret-token-value")
        self.assertNotIn("s3cret-token-value", err.getvalue())


if __name__ == "__main__":
    unittest.main()
