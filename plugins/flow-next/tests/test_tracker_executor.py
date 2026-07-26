"""Executor, classification, credential and envelope contracts (fn-139.2).

Every test here targets a behavior that was either measured against a live API
or found by review. The fake transport is the injected executor seam itself,
which is why spec A builds that seam before any adapter exists.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import classify as C  # noqa: E402
from flowctl_tracker import credentials as CR  # noqa: E402
from flowctl_tracker import envelope as E  # noqa: E402
from flowctl_tracker import executor as X  # noqa: E402
from flowctl_tracker.types import (EXIT_CODES, CredentialPolicy, ErrorClass,  # noqa: E402
                                   Request, Response, TrackerError)


def resp(status: int, body: bytes = b"", headers: dict | None = None) -> Response:
    return Response(status, headers or {}, body, 0.01)


class Schema(unittest.TestCase):
    def test_exactly_one_timeout_field(self) -> None:
        f = {x.name for x in Request.__dataclass_fields__.values()}
        self.assertIn("timeout_s", f)
        self.assertNotIn("connect_timeout_s", f)
        self.assertNotIn("read_timeout_s", f)

    def test_request_carries_provider_and_op(self) -> None:
        f = set(Request.__dataclass_fields__)
        self.assertTrue({"provider", "op"} <= f)

    def test_adapter_cannot_set_a_credential_header(self) -> None:
        for h in ("Authorization", "PRIVATE-TOKEN", "x-api-key"):
            with self.subTest(header=h), self.assertRaises(ValueError):
                Request(provider="p", op="o", method="GET", url_or_argv="u", headers={h: "v"})

    def test_exit_codes_are_total_and_unique(self) -> None:
        self.assertEqual(set(EXIT_CODES), set(ErrorClass))
        self.assertEqual(len(set(EXIT_CODES.values())), len(EXIT_CODES))

    def test_external_action_required_is_in_the_enum(self) -> None:
        self.assertEqual(EXIT_CODES[ErrorClass.EXTERNAL_ACTION_REQUIRED], 12)


class Classification(unittest.TestCase):
    def test_gitlab_403_licence_is_capability_not_auth(self) -> None:
        e = C.classify("gitlab", resp(403, b'{"message":"Blocked issues not available for current license"}'))
        self.assertIs(e.cls, ErrorClass.CAPABILITY)

    def test_gitlab_bare_403_is_auth(self) -> None:
        self.assertIs(C.classify("gitlab", resp(403, b"{}")).cls, ErrorClass.AUTH)

    def test_linear_rate_limit_arrives_as_graphql_over_200(self) -> None:
        e = C.classify("linear", resp(200, b'{"errors":[{"message":"rate limit exceeded"}]}'))
        self.assertIs(e.cls, ErrorClass.RATE_LIMITED)
        self.assertTrue(e.auto_retryable)

    def test_jira_missing_xsrf_404_is_not_reported_as_not_found(self) -> None:
        e = C.classify("jira", resp(404, b"XSRF check failed"))
        self.assertIs(e.cls, ErrorClass.INVALID_INPUT)
        self.assertEqual(e.subtype, "xsrf")

    def test_success_returns_none(self) -> None:
        self.assertIsNone(C.classify("github", resp(200, b"{}")))

    def test_fallback_is_total(self) -> None:
        for status in (418, 500, 502, 301, 204):
            with self.subTest(status=status):
                r = C.classify("github", resp(status))
                self.assertTrue(r is None or isinstance(r, TrackerError))

    def test_malformed_body_is_transport_but_not_auto_retryable(self) -> None:
        e = C.malformed_body("bad json")
        self.assertIs(e.cls, ErrorClass.TRANSPORT)
        self.assertFalse(e.auto_retryable)

    def test_5xx_is_auto_retryable_but_4xx_is_not(self) -> None:
        self.assertTrue(C.classify("github", resp(503)).auto_retryable)
        self.assertFalse(C.classify("github", resp(400)).auto_retryable)


class Credentials(unittest.TestCase):
    def test_no_generic_keyring_rung_exists(self) -> None:
        src = (ROOT / "scripts" / "flowctl_tracker" / "credentials.py").read_text()
        self.assertNotIn("keyring.get_password", src)
        self.assertIn("no keyring", src.lower())

    def test_jira_selects_by_persisted_auth_scheme_not_by_racing(self) -> None:
        env = {"JIRA_EMAIL": "e@x", "JIRA_API_TOKEN": "t", "JIRA_PAT": "p"}
        with mock.patch.dict(os.environ, env, clear=False):
            h = {}
            CR.resolve("jira", auth_scheme="bearer-pat").attach(h)
            self.assertTrue(h["Authorization"].startswith("Bearer "))
            h2 = {}
            CR.resolve("jira", auth_scheme="cloud-basic").attach(h2)
            self.assertTrue(h2["Authorization"].startswith("Basic "))

    def test_credential_never_appears_in_repr(self) -> None:
        with mock.patch.dict(os.environ, {"LINEAR_API_KEY": "lin_secret_value_1234"}):
            self.assertNotIn("lin_secret", repr(CR.resolve("linear")))

    def test_redaction_strips_secrets_from_messages(self) -> None:
        with mock.patch.dict(os.environ, {"GITLAB_TOKEN": "glpat-abcdefghijkl"}):
            self.assertNotIn("glpat-abcdefghijkl", CR.redact("failed: glpat-abcdefghijkl"))


class CredentialPolicyHonoured(unittest.TestCase):
    """The presigned case: an always-inject executor leaks the key to the asset host."""

    def _capture(self, policy: CredentialPolicy) -> dict:
        seen = {}

        class FakeResp:
            status, headers = 200, {}
            def read(self): return b"{}"
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def fake_open(r, timeout=None, **kw):
            seen.update(dict(r.header_items()))
            return FakeResp()

        req = Request(provider="linear", op="upload", method="PUT",
                      url_or_argv="https://uploads.example.com/x",
                      credential_policy=policy)
        with mock.patch.dict(os.environ, {"LINEAR_API_KEY": "lin_secret_value_1234"}), \
             mock.patch("urllib.request.OpenerDirector.open", side_effect=fake_open):
            X.execute(req)
        return seen

    def test_presigned_put_carries_no_provider_credential(self) -> None:
        seen = self._capture(CredentialPolicy.PRESIGNED_ANONYMOUS)
        joined = " ".join(f"{k}:{v}" for k, v in seen.items())
        self.assertNotIn("lin_secret_value_1234", joined)

    def test_provider_auth_does_carry_the_credential(self) -> None:
        seen = self._capture(CredentialPolicy.PROVIDER_AUTH)
        joined = " ".join(f"{k}:{v}" for k, v in seen.items())
        self.assertIn("lin_secret_value_1234", joined)


class Bounds(unittest.TestCase):
    def test_retries_only_rate_limited_and_only_when_idempotent(self) -> None:
        calls = {"n": 0}

        def fake(req, cred, verify):
            calls["n"] += 1
            return resp(200, b'{"errors":[{"message":"rate limit exceeded"}]}')

        with mock.patch.object(X, "_http", side_effect=fake), \
             mock.patch.object(X.time, "sleep"):
            X.execute(Request(provider="linear", op="q", method="POST",
                              url_or_argv="https://api.linear.app/graphql", idempotent=True))
        self.assertEqual(calls["n"], 3, "1 attempt + 2 retries")

        calls["n"] = 0
        with mock.patch.object(X, "_http", side_effect=fake), \
             mock.patch.object(X.time, "sleep"):
            X.execute(Request(provider="linear", op="q", method="POST",
                              url_or_argv="https://api.linear.app/graphql", idempotent=False))
        self.assertEqual(calls["n"], 1, "a non-idempotent write must NEVER be replayed")

    def test_auth_failure_is_never_retried(self) -> None:
        calls = {"n": 0}

        def fake(req, cred, verify):
            calls["n"] += 1
            return resp(401)

        with mock.patch.object(X, "_http", side_effect=fake), mock.patch.object(X.time, "sleep"):
            X.execute(Request(provider="github", op="r", method="GET",
                              url_or_argv="https://api.github.com/x", idempotent=True))
        self.assertEqual(calls["n"], 1)


class CliRoute(unittest.TestCase):
    def test_body_goes_to_stdin_never_argv(self) -> None:
        captured = {}

        def fake_run(argv, **kw):
            captured["argv"] = argv
            captured["input"] = kw.get("input")
            return subprocess.CompletedProcess(argv, 0, b"{}", b"")

        body = b'{"title":"$(rm -rf /) `whoami` & ; |"}'
        with mock.patch.object(X.subprocess, "run", side_effect=fake_run):
            X.execute(Request(provider="github", op="create", method="POST",
                              url_or_argv=["gh", "api", "repos/x/y/issues"], body=body))
        self.assertEqual(captured["input"], body)
        self.assertNotIn(body.decode(), " ".join(captured["argv"]))

    def test_no_shell_is_used(self) -> None:
        src = (ROOT / "scripts" / "flowctl_tracker" / "executor.py").read_text()
        self.assertNotIn("shell=True", src)

    def test_glab_stdout_warning_does_not_corrupt_json(self) -> None:
        noisy = b'Warning: Multiple config files found.\n  Using: /x\n{"iid": 7}'

        def fake_run(argv, **kw):
            return subprocess.CompletedProcess(argv, 0, noisy, b"")

        with mock.patch.object(X.subprocess, "run", side_effect=fake_run):
            r = X.execute(Request(provider="gitlab", op="read", method="GET",
                                  url_or_argv=["glab", "api", "x"]))
        self.assertEqual(json.loads(r.body)["iid"], 7)

    def test_cli_timeout_becomes_a_transport_error_not_an_exception(self) -> None:
        def fake_run(argv, **kw):
            raise subprocess.TimeoutExpired(argv, 1)

        with mock.patch.object(X.subprocess, "run", side_effect=fake_run):
            r = X.execute(Request(provider="github", op="r", method="GET",
                                  url_or_argv=["gh", "api", "x"]))
        self.assertIsInstance(r, TrackerError)
        self.assertIs(r.cls, ErrorClass.TRANSPORT)


class Envelope(unittest.TestCase):
    def test_success_shape(self) -> None:
        payload, code = E.success({"id": 1})
        d = json.loads(payload)
        self.assertTrue(d["success"])
        self.assertIsNone(d["degraded"])
        self.assertIsNone(d["probe"])
        self.assertEqual(code, 0)

    def test_failure_maps_class_to_its_exit_code(self) -> None:
        for cls, code in EXIT_CODES.items():
            with self.subTest(cls=cls):
                _, got = E.failure(TrackerError(cls, "x"))
                self.assertEqual(got, code)

    def test_probe_is_distinct_from_degraded(self) -> None:
        """A failed re-probe must not read as a capability change."""
        payload, _ = E.success({}, probe={"scope": "capabilities", "ok": False, "reason": "timeout"})
        d = json.loads(payload)
        self.assertIsNone(d["degraded"])
        self.assertFalse(d["probe"]["ok"])

    def test_inactive_is_a_class_not_a_crash(self) -> None:
        payload, code = E.inactive()
        self.assertEqual(json.loads(payload)["class"], "inactive")
        self.assertEqual(code, 3)


if __name__ == "__main__":
    unittest.main()
