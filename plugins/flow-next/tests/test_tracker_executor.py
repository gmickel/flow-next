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


class CliClassificationThroughExecute(unittest.TestCase):
    """The classifier branches must be reachable on the CLI route.

    Testing `classify()` directly proved nothing here: a non-zero gh/glab exit
    was collapsed to a synthetic HTTP 400, so auth / rate-limit / licence / 5xx
    were all unreachable through `execute()` and every CLI failure read as
    `invalid_input`.
    """

    def _cli(self, provider: str, stderr: bytes, rc: int = 1):
        def fake(argv, **kw):
            return subprocess.CompletedProcess(argv, rc, b"", stderr)

        with mock.patch.object(X.subprocess, "run", side_effect=fake), \
             mock.patch.object(X.time, "sleep"):
            return X.execute(Request(provider=provider, op="r", method="GET",
                                     url_or_argv=[provider, "api", "x"], idempotent=True))

    def test_cli_auth_failure(self) -> None:
        self.assertIs(self._cli("github", b"HTTP 401: Bad credentials").cls, ErrorClass.AUTH)

    def test_cli_not_found(self) -> None:
        self.assertIs(self._cli("github", b"HTTP 404: Not Found").cls, ErrorClass.NOT_FOUND)

    def test_cli_server_error(self) -> None:
        self.assertIs(self._cli("github", b"HTTP 502: Bad Gateway").cls, ErrorClass.TRANSPORT)

    def test_cli_rate_limited(self) -> None:
        self.assertIs(self._cli("github", b"HTTP 429: rate limited").cls, ErrorClass.RATE_LIMITED)

    def test_cli_gitlab_licence_gate_is_capability(self) -> None:
        e = self._cli("gitlab", b"HTTP 403: Blocked issues not available for current license")
        self.assertIs(e.cls, ErrorClass.CAPABILITY)

    def test_unparseable_cli_failure_falls_back(self) -> None:
        e = self._cli("github", b"something went wrong")
        self.assertIs(e.cls, ErrorClass.INVALID_INPUT)


class TlsOptOut(unittest.TestCase):
    def test_https_handler_carries_the_context_not_open(self) -> None:
        """`OpenerDirector.open()` takes no `context` kwarg; passing one raised
        TypeError and broke the documented opt-out entirely."""
        import inspect
        import urllib.request

        self.assertNotIn("context",
                         inspect.signature(urllib.request.OpenerDirector.open).parameters)
        src = (ROOT / "scripts" / "flowctl_tracker" / "executor.py").read_text()
        self.assertIn("HTTPSHandler(context=", src)
        self.assertNotIn("open(r, timeout=req.timeout_s, context=", src)

    def test_cli_route_rejects_tls_opt_out_rather_than_ignoring_it(self) -> None:
        r = X.execute(Request(provider="github", op="r", method="GET",
                              url_or_argv=["gh", "api", "x"]), verify_tls=False)
        self.assertIs(r.cls, ErrorClass.INVALID_INPUT)
        self.assertEqual(r.subtype, "tls_unsupported")

    def test_tls_opt_out_is_recorded_never_silent(self) -> None:
        events = []
        with mock.patch.object(X, "_http", return_value=resp(200, b"{}")):
            X.execute(Request(provider="linear", op="q", method="POST",
                              url_or_argv="https://api.linear.app/graphql"),
                      verify_tls=False, on_event=events.append)
        self.assertTrue(any("tls-verification-disabled" in e for e in events))


class MalformedTarget(unittest.TestCase):
    def test_bad_url_returns_error_not_exception(self) -> None:
        r = X.execute(Request(provider="linear", op="q", method="GET", url_or_argv="not-a-url"))
        self.assertIsInstance(r, TrackerError)


class ConcurrencyCap(unittest.TestCase):
    def test_cap_is_enforced_not_merely_declared(self) -> None:
        import threading

        peak = {"n": 0}
        live = {"n": 0}
        lock = threading.Lock()

        def slow(req, cred, verify):
            with lock:
                live["n"] += 1
                peak["n"] = max(peak["n"], live["n"])
            X.time.sleep(0.02)
            with lock:
                live["n"] -= 1
            return resp(200, b"{}")

        with mock.patch.object(X, "_http", side_effect=slow):
            ts = [threading.Thread(target=lambda: X.execute(
                Request(provider="linear", op="q", method="GET",
                        url_or_argv="https://api.linear.app/graphql"))) for _ in range(12)]
            for t_ in ts: t_.start()
            for t_ in ts: t_.join()
        self.assertLessEqual(peak["n"], 4, f"peak concurrency {peak['n']} exceeded the cap of 4")


class LinearStructuredCodes(unittest.TestCase):
    """linear-graphql.md documents extensions.code; message heuristics miss them."""

    def _err(self, code: str, message: str = "something went wrong"):
        body = json.dumps({"errors": [{"message": message,
                                       "extensions": {"code": code}}]}).encode()
        return C.classify("linear", resp(400, body))

    def test_ratelimited_code_over_http_400(self) -> None:
        e = self._err("RATELIMITED")
        self.assertIs(e.cls, ErrorClass.RATE_LIMITED)
        self.assertTrue(e.auto_retryable)

    def test_authentication_error_code(self) -> None:
        self.assertIs(self._err("AUTHENTICATION_ERROR").cls, ErrorClass.AUTH)

    def test_structured_code_wins_over_generic_message(self) -> None:
        """A generic message must not demote a structured code to invalid_input."""
        self.assertIs(self._err("RATELIMITED", "error").cls, ErrorClass.RATE_LIMITED)

    def test_ratelimited_retries_through_execute(self) -> None:
        body = json.dumps({"errors": [{"message": "e",
                                       "extensions": {"code": "RATELIMITED"}}]}).encode()
        calls = {"n": 0}

        def fake(req, cred, verify):
            calls["n"] += 1
            return resp(400, body)

        with mock.patch.object(X, "_http", side_effect=fake), mock.patch.object(X.time, "sleep"):
            X.execute(Request(provider="linear", op="q", method="POST",
                              url_or_argv="https://api.linear.app/graphql", idempotent=True))
        self.assertEqual(calls["n"], 3)


class RouteEnforcement(unittest.TestCase):
    def test_gitlab_upload_cannot_use_the_broken_cli_form(self) -> None:
        e = X.execute(Request(provider="gitlab", op="upload", method="POST",
                              url_or_argv=["glab", "api", "-F", "file=@x"]))
        self.assertIs(e.cls, ErrorClass.INVALID_INPUT)
        self.assertEqual(e.subtype, "forbidden_route")

    def test_gitlab_upload_over_http_is_allowed(self) -> None:
        with mock.patch.object(X, "_http", return_value=resp(201, b"{}")):
            r = X.execute(Request(provider="gitlab", op="upload", method="POST",
                                  url_or_argv="https://gitlab.com/api/v4/projects/1/uploads"))
        self.assertIsInstance(r, Response)

    def test_ordinary_gitlab_cli_calls_still_work(self) -> None:
        def fake(argv, **kw):
            return subprocess.CompletedProcess(argv, 0, b"{}", b"")

        with mock.patch.object(X.subprocess, "run", side_effect=fake):
            r = X.execute(Request(provider="gitlab", op="read", method="GET",
                                  url_or_argv=["glab", "api", "x"]))
        self.assertIsInstance(r, Response)


class RedirectPolicy(unittest.TestCase):
    """Refusing every redirect was too blunt - the rule is about credentials."""

    def _handler(self, authenticated: bool):
        return X._GuardedRedirect(authenticated)

    def _redirect(self, authenticated: bool, new_host: str):
        import urllib.request

        req = urllib.request.Request("https://api.example.com/a",
                                     headers={"Authorization": "Bearer secret"})
        h = self._handler(authenticated)
        return h.redirect_request(req, None, 302, "Found", {}, f"https://{new_host}/b")

    def test_cross_host_strips_the_credential(self) -> None:
        new = self._redirect(True, "cdn.other.com")
        self.assertIsNotNone(new)
        self.assertNotIn("Authorization", dict(new.headers))

    def test_same_host_keeps_it(self) -> None:
        new = self._redirect(True, "api.example.com")
        self.assertIn("Authorization", dict(new.headers))

    def test_anonymous_cross_host_is_allowed(self) -> None:
        """A presigned upload has no secret to protect and legitimately redirects."""
        new = self._redirect(False, "storage.googleapis.com")
        self.assertIsNotNone(new)


class ReadStageFailures(unittest.TestCase):
    def test_incomplete_read_becomes_a_transport_error(self) -> None:
        import http.client

        class Boom:
            status, headers = 200, {}
            def read(self): raise http.client.IncompleteRead(b"partial")
            def __enter__(self): return self
            def __exit__(self, *a): return False

        with mock.patch("urllib.request.OpenerDirector.open", return_value=Boom()):
            r = X.execute(Request(provider="linear", op="q", method="GET",
                                  url_or_argv="https://api.linear.app/graphql"))
        self.assertIsInstance(r, TrackerError)
        self.assertIs(r.cls, ErrorClass.TRANSPORT)
        self.assertEqual(r.subtype, "read")


class GitlabUploadCredential(unittest.TestCase):
    def test_http_upload_route_is_authenticated_without_env_token(self) -> None:
        """glab authenticates its own CLI calls, but the mandatory HTTP upload
        route would otherwise go out unauthenticated."""
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(CR, "_glab_config_token", return_value="glpat-fromconfig"):
            cred = CR.resolve("gitlab")
        self.assertIsNotNone(cred)
        h = {}
        cred.attach(h)
        self.assertEqual(h["PRIVATE-TOKEN"], "glpat-fromconfig")


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

    def test_rate_limited_details_carry_retry_after(self) -> None:
        payload, _ = E.failure(TrackerError(ErrorClass.RATE_LIMITED, "slow down",
                                            retry_after_s=12.5, auto_retryable=True))
        self.assertEqual(json.loads(payload)["details"]["retry_after_s"], 12.5)

    def test_capability_details_name_the_capability(self) -> None:
        payload, _ = E.failure(TrackerError(ErrorClass.CAPABILITY, "gated",
                                            details={"capability": "blockedBy",
                                                     "required_plan": "premium"}))
        d = json.loads(payload)["details"]
        self.assertEqual(d["capability"], "blockedBy")
        self.assertEqual(d["required_plan"], "premium")

    def test_conflict_details_carry_slot_and_candidates(self) -> None:
        payload, _ = E.failure(TrackerError(ErrorClass.CONFLICT, "ambiguous",
                                            details={"normalized": "in_progress",
                                                     "candidates": [{"id": "a"}, {"id": "b"}]}))
        d = json.loads(payload)["details"]
        self.assertEqual(d["normalized"], "in_progress")
        self.assertEqual(len(d["candidates"]), 2)

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
