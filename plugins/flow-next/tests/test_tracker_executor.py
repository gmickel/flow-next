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
        env = {"JIRA_EMAIL": "e@x", "JIRA_API_TOKEN": "cloud-token-1234",
               "JIRA_PAT": "datacenter-pat-1234"}
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
        """Amended acceptance: the executor CANNOT honour sslVerify=false on a
        CLI route - gh/glab expose no TLS flag, and rewriting the call into its
        HTTP equivalent needs endpoint knowledge that lives in the adapters
        (.4/.6). Rejecting is the honest option here; silently proceeding would
        claim a guarantee this layer cannot deliver.

        A sink is supplied so this reaches the CLI-specific branch: the
        "downgrade must be recordable" check fires first and is tested
        separately in TlsDowngradeCannotBeSilent.
        """
        r = X.execute(Request(provider="github", op="r", method="GET",
                              url_or_argv=["gh", "api", "x"]),
                      verify_tls=False, on_event=lambda _e: None)
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


class GithubRateLimitIs403(unittest.TestCase):
    """GitHub serves rate limiting as 403, not 429 - generic handling called it auth."""

    def test_403_with_remaining_zero_is_rate_limited(self) -> None:
        e = C.classify("github", resp(403, b"API rate limit exceeded",
                                      {"X-RateLimit-Remaining": "0"}))
        self.assertIs(e.cls, ErrorClass.RATE_LIMITED)
        self.assertTrue(e.auto_retryable)

    def test_bare_403_is_still_auth(self) -> None:
        self.assertIs(C.classify("github", resp(403, b"{}")).cls, ErrorClass.AUTH)

    def test_429_also_rate_limited(self) -> None:
        self.assertIs(C.classify("github", resp(429, b"slow down")).cls, ErrorClass.RATE_LIMITED)

    def test_retries_through_execute(self) -> None:
        calls = {"n": 0}

        def fake(req, cred, verify):
            calls["n"] += 1
            return resp(403, b"API rate limit exceeded", {"X-RateLimit-Remaining": "0"})

        with mock.patch.object(X, "_http", side_effect=fake), mock.patch.object(X.time, "sleep"):
            X.execute(Request(provider="github", op="r", method="GET",
                              url_or_argv="https://api.github.com/x", idempotent=True))
        self.assertEqual(calls["n"], 3)


class MalformedGraphQL(unittest.TestCase):
    """Invalid JSON over HTTP 200 previously read as SUCCESS."""

    def test_invalid_json_is_not_success(self) -> None:
        e = C.classify("linear", resp(200, b"not json at all"))
        self.assertIsNotNone(e)
        self.assertEqual(e.subtype, "malformed_body")
        self.assertFalse(e.auto_retryable)

    def test_errors_of_wrong_shape_does_not_raise(self) -> None:
        e = C.classify("linear", resp(200, b'{"errors":["bad"]}'))
        self.assertEqual(e.subtype, "malformed_body")

    def test_through_execute(self) -> None:
        with mock.patch.object(X, "_http", return_value=resp(200, b"{{{")):
            r = X.execute(Request(provider="linear", op="q", method="GET",
                                  url_or_argv="https://api.linear.app/graphql"))
        self.assertIsInstance(r, TrackerError)
        self.assertEqual(r.subtype, "malformed_body")


class UntrustedRetryAfter(unittest.TestCase):
    def test_negative_retry_after_does_not_raise(self) -> None:
        """Retry-After is server-controlled; -1 reached time.sleep(-1)."""
        slept = []
        with mock.patch.object(X.time, "sleep", side_effect=slept.append):
            X._sleep_backoff(0, -1)
            X._sleep_backoff(0, float("inf"))
            X._sleep_backoff(0, float("nan"))
            X._sleep_backoff(0, "garbage")
        self.assertTrue(all(0 <= s <= 30 for s in slept), slept)


class RedirectOriginNotHost(unittest.TestCase):
    def test_https_to_http_downgrade_strips_credentials(self) -> None:
        """Same host, different scheme - the token would have gone out in clear."""
        import urllib.request

        req = urllib.request.Request("https://api.example.com/a",
                                     headers={"Authorization": "Bearer secret"})
        new = X._GuardedRedirect(True).redirect_request(
            req, None, 302, "Found", {}, "http://api.example.com/b")
        self.assertNotIn("Authorization", dict(new.headers))

    def test_same_origin_keeps_credentials(self) -> None:
        import urllib.request

        req = urllib.request.Request("https://api.example.com/a",
                                     headers={"Authorization": "Bearer secret"})
        new = X._GuardedRedirect(True).redirect_request(
            req, None, 302, "Found", {}, "https://api.example.com/b")
        self.assertIn("Authorization", dict(new.headers))


class ErrorBodyReadFailure(unittest.TestCase):
    def test_incomplete_read_of_an_error_body_is_normalized(self) -> None:
        import http.client
        import urllib.error

        class BadErr(urllib.error.HTTPError):
            def __init__(self):
                super().__init__("u", 500, "err", {}, None)
            def read(self):
                raise http.client.IncompleteRead(b"partial")

        with mock.patch("urllib.request.OpenerDirector.open", side_effect=BadErr()):
            r = X.execute(Request(provider="linear", op="q", method="GET",
                                  url_or_argv="https://api.linear.app/graphql"))
        self.assertIsInstance(r, TrackerError)
        self.assertEqual(r.subtype, "read")


class GitlabTokenIsHostScoped(unittest.TestCase):
    CFG = """hosts:
    gitlab.com:
        token: glpat-dotcom
    gitlab.internal.corp:
        token: glpat-internal
"""

    def _token(self, host):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as fh:
            fh.write(self.CFG)
            path = fh.name
        with mock.patch.object(CR.os.path, "expanduser", return_value=path):
            return CR._glab_config_token(host)

    def test_picks_the_matching_host(self) -> None:
        self.assertEqual(self._token("gitlab.com"), "glpat-dotcom")
        self.assertEqual(self._token("gitlab.internal.corp"), "glpat-internal")

    def test_fails_closed_on_unknown_host(self) -> None:
        """Returning the first token would send one host's secret to another."""
        self.assertIsNone(self._token("gitlab.someone-else.com"))


class NeverRaisesHoles(unittest.TestCase):
    """Each of these escaped execute() at some point despite the contract."""

    def test_malformed_ipv6_target(self) -> None:
        r = X.execute(Request(provider="linear", op="q", method="GET",
                              url_or_argv="http://[::1"))
        self.assertIsInstance(r, TrackerError)
        self.assertEqual(r.subtype, "construction")

    def test_graphql_extensions_of_any_shape(self) -> None:
        for ext in (b'["bad"]', b'"str"', b"42", b"true"):
            with self.subTest(extensions=ext):
                body = b'{"errors":[{"message":"m","extensions":' + ext + b"}]}"
                e = C.classify("linear", resp(200, body))
                self.assertEqual(e.subtype, "malformed_body")


class TlsDowngradeCannotBeSilent(unittest.TestCase):
    def test_refused_when_there_is_no_event_sink(self) -> None:
        """The default API passes no on_event, so the downgrade was silent -
        which is precisely what 'never silent' forbids."""
        r = X.execute(Request(provider="linear", op="q", method="GET",
                              url_or_argv="https://api.linear.app/graphql"),
                      verify_tls=False)
        self.assertIsInstance(r, TrackerError)
        self.assertEqual(r.subtype, "tls_unrecorded")

    def test_allowed_and_recorded_when_a_sink_is_present(self) -> None:
        events = []
        with mock.patch.object(X, "_http", return_value=resp(200, b"{}")):
            r = X.execute(Request(provider="linear", op="q", method="GET",
                                  url_or_argv="https://api.linear.app/graphql"),
                          verify_tls=False, on_event=events.append)
        self.assertIsInstance(r, Response)
        self.assertTrue(any("tls-verification-disabled" in e for e in events))


class HttpStatusBeatsGraphqlBody(unittest.TestCase):
    """A GraphQL-shaped body must not override the codes GraphQL never owns."""

    GQL = b'{"errors":[{"message":"Internal server error"}]}'

    def test_500_with_graphql_body_is_transport(self) -> None:
        self.assertIs(C.classify("linear", resp(500, self.GQL)).cls, ErrorClass.TRANSPORT)

    def test_401_with_graphql_body_is_auth(self) -> None:
        self.assertIs(C.classify("linear", resp(401, self.GQL)).cls, ErrorClass.AUTH)

    def test_429_with_graphql_body_is_rate_limited(self) -> None:
        self.assertIs(C.classify("linear", resp(429, self.GQL)).cls, ErrorClass.RATE_LIMITED)

    def test_400_still_uses_the_graphql_document(self) -> None:
        body = json.dumps({"errors": [{"message": "e",
                                       "extensions": {"code": "RATELIMITED"}}]}).encode()
        self.assertIs(C.classify("linear", resp(400, body)).cls, ErrorClass.RATE_LIMITED)


class CredentialsNeverReachTheEnvelope(unittest.TestCase):
    """R6, end to end. The previous test exercised redact() in ISOLATION and so
    never covered the path that actually leaked: provider error text copied
    verbatim into TrackerError.message and emitted by the envelope."""

    TOKEN = "lin_secret_value_1234"

    def test_provider_echoed_token_is_absent_from_the_envelope(self) -> None:
        body = json.dumps({"errors": [{"message": f"invalid key {self.TOKEN}"}]}).encode()
        with mock.patch.dict(os.environ, {"LINEAR_API_KEY": self.TOKEN}):
            err = C.classify("linear", resp(200, body))
            payload, _ = E.failure(err)
        self.assertNotIn(self.TOKEN, payload)

    def test_redaction_also_applies_to_errors_from_any_other_source(self) -> None:
        with mock.patch.dict(os.environ, {"LINEAR_API_KEY": self.TOKEN}):
            payload, _ = E.failure(TrackerError(ErrorClass.TRANSPORT,
                                                f"connect failed using {self.TOKEN}"))
        self.assertNotIn(self.TOKEN, payload)

    def test_full_path_through_execute(self) -> None:
        body = json.dumps({"errors": [{"message": f"bad {self.TOKEN}"}]}).encode()
        with mock.patch.dict(os.environ, {"LINEAR_API_KEY": self.TOKEN}), \
             mock.patch.object(X, "_http", return_value=resp(200, body)):
            r = X.execute(Request(provider="linear", op="q", method="GET",
                                  url_or_argv="https://api.linear.app/graphql"))
        payload, _ = E.failure(r)
        self.assertNotIn(self.TOKEN, payload)


class ErrorBodyReadTimeout(unittest.TestCase):
    def test_timeout_reading_the_error_body_does_not_escape(self) -> None:
        """A sibling `except` cannot catch what is raised inside another handler."""
        import urllib.error

        class SlowErr(urllib.error.HTTPError):
            def __init__(self):
                super().__init__("u", 500, "err", {}, None)
            def read(self):
                raise TimeoutError("read timed out")

        with mock.patch("urllib.request.OpenerDirector.open", side_effect=SlowErr()):
            r = X.execute(Request(provider="linear", op="q", method="GET",
                                  url_or_argv="https://api.linear.app/graphql"))
        self.assertIsInstance(r, TrackerError)
        self.assertEqual(r.subtype, "read")


class RedactorCoversEverySecretSource(unittest.TestCase):
    """Env-var scanning alone missed the glab-config token used by the
    mandatory GitLab HTTP upload route."""

    def test_glab_config_token_is_redacted(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(CR, "_glab_config_token", return_value="glpat-onlyinconfig"):
            CR.resolve("gitlab")
        payload, _ = E.failure(TrackerError(ErrorClass.TRANSPORT, "boom glpat-onlyinconfig"))
        self.assertNotIn("glpat-onlyinconfig", payload)

    def test_short_secrets_are_redacted_too(self) -> None:
        """An 8-char floor was a false economy - a short token is still a token."""
        with mock.patch.dict(os.environ, {"LINEAR_API_KEY": "abc123"}):
            payload, _ = E.failure(TrackerError(ErrorClass.AUTH, "bad key abc123"))
        self.assertNotIn("abc123", payload)


class MalformedCliRequest(unittest.TestCase):
    def test_non_string_argv_element_does_not_escape(self) -> None:
        r = X.execute(Request(provider="github", op="r", method="GET",
                              url_or_argv=["gh", None]))
        self.assertIsInstance(r, TrackerError)
        self.assertEqual(r.subtype, "spawn")

    def test_credential_resolution_failure_does_not_escape(self) -> None:
        with mock.patch.object(X, "resolve", side_effect=RuntimeError("corrupt config")):
            r = X.execute(Request(provider="gitlab", op="r", method="GET",
                                  url_or_argv="https://gitlab.com/api/v4/x"))
        self.assertIsInstance(r, TrackerError)
        self.assertEqual(r.subtype, "resolve")


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


class ErrorEnvelopeRedactsEveryOutboundString(unittest.TestCase):
    """Round-6 redaction covered `error` only, leaving two live channels open."""

    def setUp(self) -> None:
        self._saved = set(CR._SEEN)
        CR._remember("s3cret-token-value")
        self.addCleanup(lambda: (CR._SEEN.clear(), CR._SEEN.update(self._saved)))

    def test_nested_details_are_redacted(self) -> None:
        """A provider that echoes the token back lands in `conflict.candidates`."""
        err = TrackerError(
            ErrorClass.CONFLICT, "conflict",
            details={"normalized": "x",
                     "candidates": [{"why": "rejected for s3cret-token-value"}]},
        )
        payload, _ = E.failure(err)
        self.assertNotIn("s3cret-token-value", payload)

    def test_every_typed_variant_is_covered(self) -> None:
        for cls, details in (
            (ErrorClass.CAPABILITY, {"capability": "s3cret-token-value"}),
            (ErrorClass.EXTERNAL_ACTION_REQUIRED, {"payload": ["s3cret-token-value"]}),
            (ErrorClass.RATE_LIMITED, {"note": "s3cret-token-value"}),
        ):
            with self.subTest(cls=cls):
                payload, _ = E.failure(TrackerError(cls, "boom", details=details))
                self.assertNotIn("s3cret-token-value", payload)

    def test_stderr_note_is_redacted(self) -> None:
        """stderr is captured by CI logs and Ralph receipts exactly like stdout."""
        import io
        buf = io.StringIO()
        with mock.patch("sys.stderr", buf), mock.patch("sys.stdout", io.StringIO()):
            E.emit(E.success({}), note="using s3cret-token-value")
        self.assertNotIn("s3cret-token-value", buf.getvalue())


class LinearBackoffUsesBucketResetHeaders(unittest.TestCase):
    """Linear sends no Retry-After - only per-bucket epoch-MILLISECOND resets."""

    @staticmethod
    def _resp(headers):
        return resp(200, b'{"errors":[{"extensions":{"code":"RATELIMITED"}}]}', headers)

    def test_each_bucket_is_honoured(self) -> None:
        import time
        for bucket in ("requests", "endpoint-requests", "complexity"):
            with self.subTest(bucket=bucket):
                reset = (time.time() + 12.0) * 1000.0
                err = C.classify("linear", self._resp({
                    f"X-RateLimit-{bucket}-Remaining": "0",
                    f"X-RateLimit-{bucket}-Reset": str(reset),
                }))
                self.assertIs(err.cls, ErrorClass.RATE_LIMITED)
                self.assertAlmostEqual(err.retry_after_s, 12.0, delta=1.5)

    def test_only_exhausted_buckets_constrain_the_wait(self) -> None:
        """A bucket with headroom must not delay the retry."""
        import time
        now = time.time()
        err = C.classify("linear", self._resp({
            "X-RateLimit-Requests-Remaining": "500",
            "X-RateLimit-Requests-Reset": str((now + 900.0) * 1000.0),
            "X-RateLimit-Complexity-Remaining": "0",
            "X-RateLimit-Complexity-Reset": str((now + 8.0) * 1000.0),
        }))
        self.assertAlmostEqual(err.retry_after_s, 8.0, delta=1.5)

    def test_no_headers_falls_back_rather_than_raising(self) -> None:
        err = C.classify("linear", self._resp({}))
        self.assertIs(err.cls, ErrorClass.RATE_LIMITED)
        self.assertIsNone(err.retry_after_s)

    def test_github_seconds_reset_is_not_read_as_milliseconds(self) -> None:
        """GitHub's X-RateLimit-Reset is epoch SECONDS - a shared helper corrupts it."""
        import time
        err = C.classify("github", resp(403, b"rate limit", {
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": str(time.time() + 30.0)}))
        self.assertIs(err.cls, ErrorClass.RATE_LIMITED)
        self.assertAlmostEqual(err.retry_after_s, 30.0, delta=2.0)


class TlsDowngradeEventIsNotEmittedForRefusedRoutes(unittest.TestCase):
    """The audit stream must not claim a downgrade that never happened."""

    def test_cli_rejection_emits_no_downgrade_event(self) -> None:
        events: list[str] = []
        r = X.execute(Request(provider="github", op="r", method="GET",
                              url_or_argv=["gh", "api", "x"]),
                      verify_tls=False, on_event=events.append)
        self.assertIs(r.cls, ErrorClass.INVALID_INPUT)
        self.assertEqual(r.subtype, "tls_unsupported")
        self.assertEqual([e for e in events if "tls-verification-disabled" in e], [])


class ShortCredentialsAreRefusedNotExemptedFromRedaction(unittest.TestCase):
    """Round-7 exempted 1-3 char secrets from redaction while still SENDING them.

    That is the wrong end of the problem: the token reached the wire and the log.
    Refusing at resolution keeps `redact()` floorless and keeps a stray 1-char
    env value from shredding every message it appears inside.
    """

    def test_three_char_credential_is_refused_at_resolution(self) -> None:
        with mock.patch.dict(os.environ, {"LINEAR_API_KEY": "abc"}, clear=False):
            with self.assertRaises(CR.ShortCredential):
                CR.resolve("linear")

    def test_refusal_message_never_carries_the_value(self) -> None:
        with mock.patch.dict(os.environ, {"JIRA_PAT": "abc"}, clear=False):
            try:
                CR.resolve("jira", auth_scheme="bearer-pat")
            except CR.ShortCredential as exc:
                self.assertNotIn("abc", str(exc))
            else:
                self.fail("expected ShortCredential")

    def test_execute_maps_the_refusal_to_auth_rather_than_raising(self) -> None:
        with mock.patch.dict(os.environ, {"LINEAR_API_KEY": "abc"}, clear=False):
            r = X.execute(Request(provider="linear", op="q", method="POST",
                                  url_or_argv="https://api.linear.app/graphql"))
        self.assertIsInstance(r, TrackerError)
        self.assertIs(r.cls, ErrorClass.AUTH)
        self.assertNotIn("abc", r.message)

    def test_redactor_has_no_length_floor_for_accepted_secrets(self) -> None:
        """Everything that survives resolution must be fully redacted."""
        saved = set(CR._SEEN)
        self.addCleanup(lambda: (CR._SEEN.clear(), CR._SEEN.update(saved)))
        CR._remember("abcd")
        payload, _ = E.failure(TrackerError(
            ErrorClass.CONFLICT, "x", details={"candidates": [{"why": "abcd"}]}))
        self.assertNotIn("abcd", payload)

    def test_short_env_value_does_not_shred_unrelated_text(self) -> None:
        with mock.patch.dict(os.environ, {"JIRA_PAT": "p"}, clear=False):
            self.assertEqual(CR.redact("in_progress"), "in_progress")


class LinearWaitsForTheSlowestExhaustedBucket(unittest.TestCase):
    """Buckets are independent: the request is blocked until the LAST clears."""

    def test_two_exhausted_buckets_wait_for_the_later_reset(self) -> None:
        import time
        now = time.time()
        err = C.classify("linear", resp(
            200, b'{"errors":[{"extensions":{"code":"RATELIMITED"}}]}', {
                "X-RateLimit-Requests-Remaining": "0",
                "X-RateLimit-Requests-Reset": str((now + 5.0) * 1000.0),
                "X-RateLimit-Complexity-Remaining": "0",
                "X-RateLimit-Complexity-Reset": str((now + 25.0) * 1000.0),
            }))
        self.assertIs(err.cls, ErrorClass.RATE_LIMITED)
        self.assertAlmostEqual(err.retry_after_s, 25.0, delta=1.5)


class CliRouteDoesNotDependOnUnusedCredentialState(unittest.TestCase):
    """`_cli` never consumes the credential - gh/glab carry their own auth.

    Resolving anyway meant a garbage GITLAB_TOKEN in the environment failed a
    glab CLI call with auth/resolve even though the call would have succeeded.
    """

    def test_short_gitlab_token_in_env_does_not_fail_a_glab_cli_call(self) -> None:
        ok = mock.Mock(returncode=0, stdout=b'{"id": 1}', stderr=b"")
        with mock.patch.dict(os.environ, {"GITLAB_TOKEN": "ab"}, clear=False), \
             mock.patch.object(X.subprocess, "run", return_value=ok):
            r = X.execute(Request(provider="gitlab", op="read", method="GET",
                                  url_or_argv=["glab", "api", "projects/1"]))
        self.assertIsInstance(r, Response)
        self.assertEqual(r.status, 200)

    def test_http_route_still_fails_closed_on_a_bad_credential_source(self) -> None:
        with mock.patch.dict(os.environ, {"GITLAB_TOKEN": "ab"}, clear=False):
            r = X.execute(Request(provider="gitlab", op="upload", method="POST",
                                  url_or_argv="https://gitlab.com/api/v4/projects/1/uploads"))
        self.assertIsInstance(r, TrackerError)
        self.assertIs(r.cls, ErrorClass.AUTH)
        self.assertEqual(r.subtype, "resolve")


class ScrubCoversMappingKeys(unittest.TestCase):
    def test_secret_as_a_details_key_is_redacted(self) -> None:
        saved = set(CR._SEEN)
        self.addCleanup(lambda: (CR._SEEN.clear(), CR._SEEN.update(saved)))
        CR._remember("s3cret-token-value")
        payload, _ = E.failure(TrackerError(
            ErrorClass.CONFLICT, "x",
            details={"candidates": [{"s3cret-token-value": "rejected"}]}))
        self.assertNotIn("s3cret-token-value", payload)


class FailingDowngradeSinkRefusesTheRequest(unittest.TestCase):
    """A sink that fails at record time is as unrecordable as a missing one."""

    def test_raising_sink_refuses_and_sends_nothing(self) -> None:
        sent = {"n": 0}

        def sink(_e: str) -> None:
            raise RuntimeError("disk full")

        def fake_http(*a, **kw):
            sent["n"] += 1
            return resp(200, b"{}")

        with mock.patch.object(X, "_http", side_effect=fake_http):
            r = X.execute(Request(provider="jira", op="read", method="GET",
                                  url_or_argv="https://x.example.com/rest/api/2/issue/K-1"),
                          verify_tls=False, on_event=sink)
        self.assertIsInstance(r, TrackerError)
        self.assertEqual(r.subtype, "tls_unrecorded")
        self.assertEqual(sent["n"], 0, "request must not be sent unrecorded")

    def test_raising_sink_on_the_retry_event_is_best_effort(self) -> None:
        """The retry line is diagnostics - a broken sink must not break the retry."""
        calls = {"n": 0}

        def fake_http(*a, **kw):
            calls["n"] += 1
            return resp(429, b"", {"Retry-After": "0"})

        def sink(e: str) -> None:
            if "retry" in e:
                raise RuntimeError("boom")

        with mock.patch.object(X, "_http", side_effect=fake_http), \
             mock.patch.object(X.time, "sleep"):
            r = X.execute(Request(provider="github", op="read", method="GET",
                                  url_or_argv="https://api.github.com/x", idempotent=True),
                          on_event=sink)
        self.assertIsInstance(r, TrackerError)
        self.assertEqual(calls["n"], 3, "1 attempt + 2 retries despite the broken sink")
