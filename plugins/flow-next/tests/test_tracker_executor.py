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


def _deep_json() -> bytes:
    """A rejection body nested deep enough that `json.loads` raises
    RecursionError rather than ValueError. Python 3.14 decodes far deeper than
    3.11-3.13 before overflowing, so the depth is generous and checked."""
    body = b'{"message":' + b"[" * 1_000_000
    try:
        json.loads(body)
    except RecursionError:
        return body
    raise AssertionError("body no longer makes json.loads raise RecursionError")


def _rejection(provider: str, status: int, body) -> TrackerError:
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()
    err = C.classify(provider, resp(status, raw))
    assert isinstance(err, TrackerError)
    return err


class RejectionReason(unittest.TestCase):
    """fn-331: a Jira or GitLab rejection carries the tracker's own reason."""

    def assertRejected(self, err: TrackerError, message: str) -> None:
        self.assertIs(err.cls, ErrorClass.INVALID_INPUT)
        self.assertEqual(err.subtype, "http")
        self.assertEqual(err.message, message)

    def test_jira_wrong_level_parent_names_each_field(self) -> None:
        # Jira Cloud's answer for a story given as the parent of a story.
        err = _rejection("jira", 400, {"errorMessages": [], "errors": {
            "parent": "Please select valid parent issue.",
            "parentId": "Please select valid parent issue."}})
        self.assertRejected(
            err, "rejected (400): parent: Please select valid parent issue.; "
                 "parentId: Please select valid parent issue.")

    def test_jira_error_messages_come_before_field_errors(self) -> None:
        err = _rejection("jira", 400, {
            "errorMessages": ["Issue type is invalid.", "Try again."],
            "errors": {"summary": "You must specify a summary."}})
        self.assertRejected(
            err, "rejected (400): Issue type is invalid.; Try again.; "
                 "summary: You must specify a summary.")

    def test_gitlab_reason_shapes(self) -> None:
        cases = [
            ({"error": "title is missing"}, "rejected (400): title is missing"),
            ({"message": "Epic not found"}, "rejected (400): Epic not found"),
            ({"message": ["title is too long", "label is invalid"]},
             "rejected (400): title is too long; label is invalid"),
            ({"message": {"title": ["can't be blank", "is too short"],
                          "base": ["Epic is invalid"]}},
             "rejected (400): title: can't be blank; title: is too short; "
             "base: Epic is invalid"),
        ]
        for body, message in cases:
            with self.subTest(body=body):
                self.assertRejected(_rejection("gitlab", 400, body), message)

    def test_status_stays_at_the_start(self) -> None:
        for provider, body in (("jira", {"errorMessages": ["No."]}),
                               ("gitlab", {"message": "No."})):
            for status in (400, 409, 422):
                with self.subTest(provider=provider, status=status):
                    err = _rejection(provider, status, body)
                    self.assertTrue(err.message.startswith(f"rejected ({status})"))
                    self.assertEqual(err.message, f"rejected ({status}): No.")

    def test_no_reason_keeps_the_bare_message(self) -> None:
        bodies = [b"", b"not json", b"\xff\xfe", b'["a list"]', b'"text"', b"null",
                  b"{}", b'{"errorMessages":[],"errors":{}}',
                  b'{"message":[],"error":""}', b'{"other":"field"}',
                  b'{"errorMessages":[42],"errors":{"f":null}}',
                  b'{"errors":{"parent":""," ":" "}}', b'{"message":{"title":["", " "]}}',
                  b'[\n{"errorMessages":["nested"],"message":"nested"}\n]',
                  b'{"errorMessages":["no"],"message":"no"} trailing garbage',
                  b'glab: oops\n{"errorMessages":["no"],"message":"no"}']
        for provider in ("jira", "gitlab"):
            for body in bodies:
                with self.subTest(provider=provider, body=body):
                    self.assertRejected(_rejection(provider, 400, body),
                                        "rejected (400)")

    def test_echoed_credential_is_redacted(self) -> None:
        secret = "test-only-token-12345678"
        with mock.patch.object(CR, "_SEEN", set()), \
                mock.patch.dict(os.environ, {"JIRA_API_TOKEN": secret,
                                             "GITLAB_TOKEN": secret}):
            for provider, body in (
                    ("jira", {"errors": {"token": f"bad token {secret}"}}),
                    ("gitlab", {"error": f"bad token {secret}"})):
                with self.subTest(provider=provider):
                    err = _rejection(provider, 400, body)
                    self.assertNotIn(secret, err.message)
                    self.assertIn("<redacted>", err.message)

    def test_echoed_ci_job_token_is_redacted(self) -> None:
        secret = "test-only-job-token-12345678"
        env = {k: v for k, v in os.environ.items() if k != "GITLAB_TOKEN"}
        env["CI_JOB_TOKEN"] = secret
        with mock.patch.object(CR, "_SEEN", set()), \
                mock.patch.dict(os.environ, env, clear=True):
            err = _rejection("gitlab", 400, {"error": f"bad token {secret}"})
        self.assertNotIn(secret, err.message)
        self.assertEqual(err.message, "rejected (400): bad token <redacted>")

    def test_deeply_nested_body_keeps_the_bare_message(self) -> None:
        self.assertRejected(_rejection("jira", 400, _deep_json()), "rejected (400)")

    def test_reason_is_bounded(self) -> None:
        for provider, body in (("jira", {"errorMessages": ["x" * 5000]}),
                               ("gitlab", {"message": "x" * 5000})):
            with self.subTest(provider=provider):
                err = _rejection(provider, 400, body)
                self.assertTrue(err.message.startswith("rejected (400): x"))
                self.assertEqual(len(err.message), len("rejected (400): ") + 200)

    def test_other_classifications_are_unchanged(self) -> None:
        reason = {"errorMessages": ["why"], "errors": {"f": "why"},
                  "message": "why", "error": "why"}
        expected = {401: (ErrorClass.AUTH, "unauthorized (401)"),
                    403: (ErrorClass.AUTH, "unauthorized (403)"),
                    404: (ErrorClass.NOT_FOUND, "not found"),
                    429: (ErrorClass.RATE_LIMITED, "rate limited"),
                    500: (ErrorClass.TRANSPORT, "server error 500")}
        for provider in ("jira", "gitlab"):
            for status, (cls, message) in expected.items():
                with self.subTest(provider=provider, status=status):
                    err = _rejection(provider, status, reason)
                    self.assertIs(err.cls, cls)
                    self.assertEqual(err.message, message)
        xsrf = C.classify("jira", resp(404, b'{"errorMessages":["XSRF check failed"]}'))
        self.assertEqual((xsrf.subtype, xsrf.message),
                         ("xsrf", "Jira rejected the request: missing "
                                  "X-Atlassian-Token header"))
        licence = _rejection("gitlab", 403, {
            "message": "Blocked issues not available for current license"})
        self.assertEqual((licence.cls, licence.subtype),
                         (ErrorClass.CAPABILITY, "licence"))
        self.assertEqual(licence.message, "feature not available on this GitLab tier")

    def test_github_and_linear_messages_are_unchanged(self) -> None:
        gh = _rejection("github", 422, {"message": "Validation Failed",
                                        "errors": [{"message": "one parent"}]})
        self.assertRejected(gh, "rejected (422)")
        lin = _rejection("linear", 400, {"errors": [{"message": "Parent Is Invalid"}]})
        self.assertEqual((lin.cls, lin.subtype, lin.message),
                         (ErrorClass.INVALID_INPUT, "graphql", "parent is invalid"))


class Credentials(unittest.TestCase):

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

    def test_jira_basic_credential_is_redacted_after_environment_changes(self) -> None:
        with mock.patch.object(CR, "_SEEN", set()):
            with mock.patch.dict(os.environ, {
                "JIRA_EMAIL": "fake@example.test",
                "JIRA_API_TOKEN": "test-only-token-12345678",
            }):
                headers = {}
                CR.resolve("jira", auth_scheme="cloud-basic").attach(headers)
            authorization = headers["Authorization"]
            encoded = authorization.removeprefix("Basic ")
            self.assertEqual(CR.redact(f"echo: {authorization}"),
                             "echo: Basic <redacted>")
            self.assertEqual(CR.redact(encoded), "<redacted>")


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

    def test_anonymous_requests_do_not_resolve_provider_credentials(self) -> None:
        for policy in (CredentialPolicy.PRESIGNED_ANONYMOUS, CredentialPolicy.NONE):
            with self.subTest(policy=policy), \
                 mock.patch.object(X, "resolve", side_effect=ValueError("unavailable")) as resolve:
                request = Request(provider="linear", op="upload", method="PUT",
                                  url_or_argv="https://uploads.example.com/x",
                                  credential_policy=policy)
                response = mock.MagicMock()
                response.__enter__.return_value = response
                response.status, response.headers = 200, {}
                response.read.return_value = b"{}"
                with mock.patch("urllib.request.OpenerDirector.open", return_value=response) as send:
                    result = X.execute(request)
                self.assertIsInstance(result, Response)
                resolve.assert_not_called()
                sent = send.call_args.args[0]
                self.assertFalse({"authorization", "private-token", "x-api-key"}
                                 & {name.lower() for name, _ in sent.header_items()})


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

    def _cli(self, provider: str, stderr: bytes, rc: int = 1, stdout: bytes = b"",
             env: dict | None = None):
        def fake(argv, **kw):
            return subprocess.CompletedProcess(argv, rc, stdout, stderr)

        with mock.patch.object(X.subprocess, "run", side_effect=fake), \
             mock.patch.object(X.time, "sleep"):
            return X.execute(Request(provider=provider, op="r", method="GET",
                                     url_or_argv=[provider, "api", "x"], idempotent=True,
                                     env=env or {}))

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

    def test_gitlab_cli_rejection_carries_the_reason(self) -> None:
        # fn-331: glab's output for a create whose title is too long, as
        # measured: the body on stdout, a Go map rendering on stderr.
        e = self._cli(
            "gitlab",
            b"glab: map[message:map[title:[is too long (maximum is 255 characters)]]]\n",
            stdout=b'{"message":{"title":["is too long (maximum is 255 characters)"]}}\n')
        self.assertIs(e.cls, ErrorClass.INVALID_INPUT)
        self.assertEqual(e.subtype, "http")
        self.assertEqual(
            e.message, "rejected (400): title: is too long (maximum is 255 characters)")

    def test_gitlab_cli_rejection_redacts_glabs_stored_token(self) -> None:
        # The CLI route authenticates through glab's own login, so the token
        # never came from the environment; an echo of it is still redacted.
        secret = "glpat-stored-only-12345678"
        hosts = []

        def stored(host):
            hosts.append(host)
            return secret

        env = {k: v for k, v in os.environ.items() if k != "GITLAB_TOKEN"}
        with mock.patch.object(CR, "_SEEN", set()), \
                mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(CR, "_glab_config_token", side_effect=stored):
            e = self._cli("gitlab", b"glab: map[error:bad]\n",
                          stdout=json.dumps({"error": f"bad token {secret}"}).encode(),
                          env={"GITLAB_HOST": "localhost:8929"})
        self.assertEqual(e.message, "rejected (400): bad token <redacted>")
        self.assertEqual(hosts, ["localhost:8929"])

    def test_gitlab_cli_rejection_uses_an_inherited_gitlab_host(self) -> None:
        # glab honours GITLAB_HOST from the shell, so the token it used is the
        # one stored for that host, not for its default.
        secret = "glpat-inherited-host-12345678"
        hosts = []

        def stored(host):
            hosts.append(host)
            return secret

        env = {k: v for k, v in os.environ.items() if k != "GITLAB_TOKEN"}
        env["GITLAB_HOST"] = "gitlab.internal.corp"
        with mock.patch.object(CR, "_SEEN", set()), \
                mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(CR, "_glab_config_token", side_effect=stored):
            e = self._cli("gitlab", b"glab: map[error:bad]\n",
                          stdout=json.dumps({"error": f"bad token {secret}"}).encode())
        self.assertEqual(e.message, "rejected (400): bad token <redacted>")
        self.assertEqual(hosts, ["gitlab.internal.corp"])

    def test_glab_host_precedence(self) -> None:
        def host(argv, env):
            return X._glab_host(Request(provider="gitlab", op="r", method="GET",
                                        url_or_argv=argv, env=env))

        flagged = ["glab", "api", "--hostname", "flag.example", "x"]
        with mock.patch.dict(os.environ, {"GITLAB_HOST": "shell.example"}):
            self.assertEqual(host(["glab", "api", "x"], {"GITLAB_HOST": "req.example"}),
                             "req.example")
            self.assertEqual(host(flagged, {"GITLAB_HOST": "req.example"}), "req.example")
            self.assertEqual(host(flagged, {}), "flag.example")
            self.assertEqual(host(["glab", "api", "x"], {}), "shell.example")
        env = {k: v for k, v in os.environ.items() if k != "GITLAB_HOST"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertIsNone(host(["glab", "api", "x"], {}))

    def test_gitlab_cli_deeply_nested_body_keeps_the_bare_message(self) -> None:
        body = _deep_json()
        for stderr in (b"", b"glab: map[message:...]\n"):
            with self.subTest(stderr=stderr), \
                    mock.patch.object(X, "remember_glab_token"):
                e = self._cli("gitlab", stderr, stdout=body)
                self.assertIs(e.cls, ErrorClass.INVALID_INPUT)
                self.assertEqual(e.message, "rejected (400)")


class TlsOptOut(unittest.TestCase):
    def test_https_handler_carries_tls_policy(self) -> None:
        handler = X._KeepAliveHandler(False)
        self.assertFalse(handler.verify_tls)

    def test_http_reuses_connection_and_preserves_redirects_and_errors(self) -> None:
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import threading

        connections = []

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def setup(self):
                super().setup()
                connections.append(self.connection)

            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/ok")
                    body = b""
                else:
                    self.send_response(404 if self.path == "/missing" else 200)
                    body = self.path.encode()
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            for path, code, body in (("/ok", 200, b"/ok"),
                                     ("/redirect", 200, b"/ok"),
                                     ("/missing", 404, b"/missing")):
                req = Request(provider="jira", op="read", method="GET",
                              url_or_argv=f"http://127.0.0.1:{server.server_port}{path}",
                              credential_policy=CredentialPolicy.NONE)
                result = X._http(req, None, True)
                self.assertIsInstance(result, Response, result)
                self.assertEqual((result.status, result.body), (code, body))
            self.assertEqual(len(connections), 1)
        finally:
            for conn, lock in X._CONNECTIONS.values():
                with lock:
                    conn.close()
            server.shutdown()
            server.server_close()
            worker.join()


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

    def test_upload_credential_host_keeps_the_port(self) -> None:
        """glab keys a self-managed login by host:port; the bare hostname finds no login."""
        for url, host in (("http://localhost:8929/api/v4/projects/1/uploads", "localhost:8929"),
                          ("https://gitlab.com/api/v4/projects/1/uploads", "gitlab.com")):
            with self.subTest(url), mock.patch.dict(os.environ, {}, clear=True), \
                 mock.patch.object(CR, "_glab_config_token", return_value="glpat-fromconfig") as tok, \
                 mock.patch.object(CR, "_glab_cli_get", return_value=""), \
                 mock.patch.object(X, "_http", return_value=resp(201, b"{}")):
                r = X.execute(Request(provider="gitlab", op="upload", method="POST", url_or_argv=url))
                self.assertIsInstance(r, Response)
                tok.assert_called_once_with(host)


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

    def test_partial_response_with_data_and_errors_is_not_success(self) -> None:
        """GraphQL may return valid-looking data ALONGSIDE errors over HTTP 200.

        Our queries are single-purpose, so any provider-reported error makes the
        whole payload untrustworthy - it must classify as a failure, never reach
        wire._gql as a Response (which would let list-states report complete:true
        on a provider failure).
        """
        body = json.dumps({
            "data": {"workflowStates": {"nodes": [{"id": "s1"}],
                                        "pageInfo": {"hasNextPage": False}}},
            "errors": [{"message": "field team resolution failed"}],
        }).encode()
        with mock.patch.object(X, "_http", return_value=resp(200, body)):
            r = X.execute(Request(provider="linear", op="wire-list-states", method="POST",
                                  url_or_argv="https://api.linear.app/graphql"))
        self.assertIsInstance(r, TrackerError)
        self.assertIn("field team resolution failed", r.message)


class UntrustedRetryAfter(unittest.TestCase):
    def test_hostile_retry_after_hints_yield_bounded_delays(self) -> None:
        """Retry-After is server-controlled; -1 reached time.sleep(-1)."""
        for hint in (-1, float("inf"), float("nan"), "garbage"):
            with self.subTest(hint=hint):
                delay = X._backoff_delay(0, hint)
                self.assertEqual(delay, 1.0, "falls back to 2**attempt")
        self.assertLessEqual(X._backoff_delay(10, None), 30.0, "cap holds")
        self.assertLessEqual(X._backoff_delay(0, 9999), 30.0, "hint clamped")


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
        with mock.patch.object(CR, "_glab_cli_get", side_effect=AssertionError("no glab probe")):
            self.assertIsNone(self._token("gitlab.someone-else.com"))

    def test_keyring_stanza_reads_the_token_through_glab(self) -> None:
        """glab keeps a new login in the OS keyring: the stanza is there, its token is not."""
        import tempfile
        for empty in ("", ' ""', " ''"):
            cfg = self.CFG + f'    localhost:8929:\n        use_keyring: "true"\n        token:{empty}\n        api_protocol: http\n'
            with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as fh:
                fh.write(cfg)
            with self.subTest(token=empty), mock.patch.object(CR.os.path, "expanduser", return_value=fh.name), \
                 mock.patch.object(CR, "_glab_cli_get", return_value="glpat-keyring") as get:
                self.assertEqual(CR._glab_config_token("localhost:8929"), "glpat-keyring")
                get.assert_called_once_with("token", "localhost:8929")

    def test_oauth_login_goes_as_a_bearer_token(self) -> None:
        """GitLab refuses an OAuth token in PRIVATE-TOKEN (measured: 401) and takes it as Bearer."""
        for oauth, header, value in (("true", "Authorization", "Bearer oauth-tok"), ("", "PRIVATE-TOKEN", "oauth-tok")):
            with self.subTest(oauth=oauth), mock.patch.dict(os.environ, {}, clear=True), \
                 mock.patch.object(CR, "_glab_config_token", return_value="oauth-tok"), \
                 mock.patch.object(CR, "_glab_cli_get", return_value=oauth):
                h = {}
                CR.resolve("gitlab", host="localhost:8929").attach(h)
                self.assertEqual(h, {header: value})


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
        """stderr is captured by CI logs exactly like stdout."""
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


class RawBodyOpsSkipGraphQLParse(unittest.TestCase):
    """Measured live 2026-07-28: a Linear attach-get downloads raw asset
    bytes from uploads.linear.app; classifying that 200 body as GraphQL
    reported transport/malformed_body for every binary attachment. Raw-body
    ops classify on status alone; GraphQL ops keep the malformed contract."""

    def test_binary_200_attach_get_is_success(self) -> None:
        e = C.classify("linear", resp(200, b"\xa4\x00\xffbinary"),
                       op="wire-attach-get")
        self.assertIsNone(e)

    def test_binary_200_graphql_op_still_malformed(self) -> None:
        e = C.classify("linear", resp(200, b"\xa4\x00\xffbinary"))
        self.assertIsNotNone(e)
        self.assertEqual(e.subtype, "malformed_body")

    def test_attach_get_error_status_still_classifies(self) -> None:
        e = C.classify("linear", resp(500, b"boom"), op="wire-attach-get")
        self.assertIsNotNone(e)


class EnvelopeCarriesSubtype(unittest.TestCase):
    """fn-334 R5: the documented subtypes reach the caller of every command."""

    def test_subtype_is_in_the_failure_envelope_when_set(self) -> None:
        for subtype in ("several_parents", "delivery_link_type", "parent_mismatch"):
            with self.subTest(subtype=subtype):
                payload, _ = E.failure(TrackerError(ErrorClass.CONFLICT, "x",
                                                    subtype=subtype))
                self.assertEqual(json.loads(payload).get("subtype"), subtype)
        payload, _ = E.failure(TrackerError(ErrorClass.TRANSPORT, "x"))
        self.assertNotIn("subtype", json.loads(payload))

    def test_idea_parent_stop_reaches_the_cli_caller(self) -> None:
        import tempfile  # noqa: PLC0415
        from flowctl_tracker import idea  # noqa: PLC0415
        link_types = {"issueLinkTypes": [
            {"id": "1", "name": "Polaris work item link",
             "inward": "is implemented by", "outward": "implements"},
            {"id": "2", "name": "Polaris work item link (old)",
             "inward": "is implemented by", "outward": "implements"}]}
        config = {"tracker": {"type": "jira", "perTracker": {"ideaProjectKeys": ["IDEAS"]},
                              "resolved": {"destination": {
                                  "baseUrl": "https://ex.atlassian.net",
                                  "projectKey": "PROJ", "projectId": "1",
                                  "issueTypeId": "10001"}}}}
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            flow.mkdir()
            (flow / "config.json").write_text(json.dumps(config), encoding="utf-8")
            body = Path(tmp) / "b.md"
            body.write_text("B", encoding="utf-8")
            payload, code = idea.run(
                flow, "parent", idea="IDEAS-7", body_file=str(body),
                execute=lambda r: resp(200, json.dumps(link_types).encode()))
        out = json.loads(payload)
        self.assertEqual(code, EXIT_CODES[ErrorClass.UNRESOLVED])
        self.assertEqual(out.get("subtype"), "delivery_link_type")


class GlabCredentialsAreRedacted(unittest.TestCase):
    """fn-334 R11: every credential glab may have used is redacted."""

    def _cli(self, stdout: bytes, env: dict, req_env: dict | None = None):
        def fake(argv, **kw):
            return subprocess.CompletedProcess(argv, 1, stdout, b"glab: map[error:bad]\n")

        with mock.patch.object(CR, "_SEEN", set()), \
                mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(CR, "_glab_cli_get", return_value=""), \
                mock.patch.object(X.subprocess, "run", side_effect=fake):
            return X.execute(Request(provider="gitlab", op="r", method="GET",
                                     url_or_argv=["glab", "api", "x"],
                                     env=req_env or {}))

    def _env(self, home: str, **extra: str) -> dict:
        keep = {k: v for k, v in os.environ.items()
                if k not in ("GITLAB_TOKEN", "GITLAB_HOST", "GLAB_CONFIG_DIR",
                             "GITLAB_ACCESS_TOKEN", "OAUTH_TOKEN")}
        return {**keep, "HOME": home, **extra}

    def test_glab_environment_tokens_are_redacted(self) -> None:
        import tempfile  # noqa: PLC0415
        for name in ("GITLAB_ACCESS_TOKEN", "OAUTH_TOKEN"):
            secret = f"glpat-{name.lower()}-12345678"
            with self.subTest(name=name), tempfile.TemporaryDirectory() as home:
                e = self._cli(json.dumps({"error": f"bad token {secret}"}).encode(),
                              self._env(home, **{name: secret}))
                self.assertEqual(e.message, "rejected (400): bad token <redacted>")

    def test_glab_config_dir_and_every_host_when_the_host_is_unknown(self) -> None:
        import tempfile  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as home, \
                tempfile.TemporaryDirectory() as config_dir:
            Path(config_dir, "config.yml").write_text(
                "hosts:\n"
                "    gitlab.com:\n"
                "        token: glpat-first-host-12345678\n"
                "    localhost:8929:\n"
                "        token: glpat-second-host-12345678\n",
                encoding="utf-8")
            env = self._env(home, GLAB_CONFIG_DIR=config_dir)
            for secret in ("glpat-first-host-12345678", "glpat-second-host-12345678"):
                with self.subTest(secret=secret):
                    e = self._cli(json.dumps({"error": f"bad token {secret}"}).encode(),
                                  env)
                    self.assertEqual(e.message, "rejected (400): bad token <redacted>")
            e = self._cli(json.dumps(
                {"error": "bad token glpat-second-host-12345678"}).encode(),
                env, {"GITLAB_HOST": "localhost:8929"})
            self.assertEqual(e.message, "rejected (400): bad token <redacted>")


class AttachmentAndLicenceRejections(unittest.TestCase):
    """fn-334 R12: attachment downloads carry the reason; a licence marker in
    glab's diagnostic keeps the capability class."""

    def test_attachment_download_rejection_carries_the_reason(self) -> None:
        e = C.classify("jira", resp(400, b'{"errorMessages":["Attachment 9 is gone"]}'),
                       op="wire-attach-get")
        self.assertEqual(e.message, "rejected (400): Attachment 9 is gone")
        e = C.classify("gitlab", resp(400, b'{"message":"file too old"}'),
                       op="wire-attach-get")
        self.assertEqual(e.message, "rejected (400): file too old")
        e = C.classify("gitlab", resp(
            403, b'{"message":"403 Forbidden - Blocked issues not available for current license"}'),
            op="wire-attach-get")
        self.assertIs(e.cls, ErrorClass.CAPABILITY)

    def test_licence_marker_only_in_glabs_diagnostic_stays_capability(self) -> None:
        def fake(argv, **kw):
            return subprocess.CompletedProcess(
                argv, 1, b'{"message":"403 Forbidden"}',
                b"glab: Blocked issues not available for current license (HTTP 403)")

        with mock.patch.object(X, "remember_glab_token"), \
                mock.patch.object(X.subprocess, "run", side_effect=fake):
            e = X.execute(Request(provider="gitlab", op="relate", method="GET",
                                  url_or_argv=["glab", "api", "x"]))
        self.assertIs(e.cls, ErrorClass.CAPABILITY)
