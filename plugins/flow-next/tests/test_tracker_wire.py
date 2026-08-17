"""Wire verbs: locator addressing + pre-mutation durable check (fn-140.1).

Fake transport = the injected executor seam from fn-139.2. Every test drives
the real wire package against recorded response shapes — no live API.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import wire as W  # noqa: E402
from flowctl_tracker.types import ErrorClass, Response, TrackerError  # noqa: E402


def ok(body) -> Response:
    return Response(200, {}, json.dumps(body).encode() if body is not None else b"", 0.01)


def empty() -> Response:
    return Response(204, {}, b"", 0.01)


def fake_execute(responses: dict):
    """Route by op; record every request. Lists consume one response per call."""
    calls = []

    def execute(request):
        calls.append(request)
        if request.op not in responses:
            raise AssertionError(f"unexpected op {request.op!r}; have {sorted(responses)}")
        out = responses[request.op]
        if isinstance(out, list):
            if not out:
                raise AssertionError(f"no more responses for op {request.op!r}")
            out = out.pop(0)
        return out(request) if callable(out) else out

    execute.calls = calls
    return execute


def loc(durable: str, display: str) -> dict:
    return {"durable": durable, "display": display}


def cli_endpoint(request) -> str:
    """Last non-flag argv element is the REST path (`gh`/`glab api`)."""
    argv = list(request.url_or_argv)
    if len(argv) >= 2 and argv[-2:] == ["--input", "-"]:
        argv = argv[:-2]
    if len(argv) >= 2 and argv[-2] == "-H":
        argv = argv[:-2]
    return argv[-1]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GH_NODE = "I_kwDOTestNode1"
GH_ISSUE = {"id": 999001, "node_id": GH_NODE, "number": 42, "title": "T",
            "body": "B", "html_url": "https://github.com/o/r/issues/42",
            "labels": [{"name": "bug"}], "state": "open"}

GL_ID = 84817009
GL_ISSUE = {"id": GL_ID, "iid": 12, "title": "T", "description": "B",
            "web_url": "https://gitlab.com/g/p/-/issues/12",
            "labels": ["bug"], "assignees": [{"id": 7, "username": "u"}],
            "state": "opened"}

LN_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
LN_ISSUE = {"id": LN_UUID, "identifier": "WOR-17", "title": "T",
            "description": "B", "url": "https://linear.app/x/issue/WOR-17",
            "labels": {"nodes": [{"id": "lbl-1", "name": "bug"}]},
            "assignee": {"id": "user-1", "name": "Ada"}}

JR_ID = "10042"
JR_ISSUE = {"id": JR_ID, "key": "SCRUM-1",
            "fields": {"summary": "T", "description": "B",
                       "labels": ["bug"], "assignee": {"accountId": "acct-1"}}}


def gh_cfg() -> dict:
    return {"tracker": {"type": "github",
                        "readyState": "Ready",
                        "resolved": {"destination": {"owner": "o", "repo": "r"}}}}


def gl_cfg() -> dict:
    return {"tracker": {"type": "gitlab",
                        "readyState": "Ready",
                        "perTracker": {"project": "g/p", "host": "gitlab.com"},
                        "resolved": {"destination": {
                            "projectId": 1, "projectPath": "g/p",
                            "host": "gitlab.com", "namespaceId": 9}}}}


def ln_cfg() -> dict:
    return {"tracker": {"type": "linear",
                        "readyState": "Ready",
                        "perTracker": {"teamId": "team-1"},
                        "resolved": {"destination": {
                            "teamId": "team-1", "teamKey": "WOR",
                            "labelIds": {"bug": "lbl-1", "ready": "lbl-2"},
                            "stateIds": {}}}}}


def jr_cfg() -> dict:
    return {"tracker": {"type": "jira",
                        "readyState": "Ready for Work",
                        "perTracker": {"baseUrl": "https://ex.atlassian.net",
                                       "projectKey": "SCRUM"},
                        "resolved": {"destination": {
                            "baseUrl": "https://ex.atlassian.net",
                            "projectKey": "SCRUM", "projectId": "10000",
                            "issueTypeId": "10001", "apiVersion": 2,
                            "style": "classic", "statusIds": {}}}}}


def gql_issue(issue) -> Response:
    return ok({"data": {"issue": issue}})


# ---------------------------------------------------------------------------
# Locator + no-local-state guards
# ---------------------------------------------------------------------------

class LocatorParsing(unittest.TestCase):
    def test_requires_durable_and_display(self) -> None:
        for raw in ({}, {"durable": "x"}, {"display": "#1"},
                    {"durable": "", "display": "#1"},
                    {"durable": "x", "display": ""}):
            with self.subTest(raw=raw):
                out = W.parse_locator(raw)
                self.assertIsInstance(out, TrackerError)
                self.assertIs(out.cls, ErrorClass.INVALID_INPUT)

    def test_json_string_accepted(self) -> None:
        out = W.parse_locator(json.dumps(loc(GH_NODE, "#42")))
        self.assertEqual(out, loc(GH_NODE, "#42"))


class NoLocalState(unittest.TestCase):
    def test_wire_source_imports_no_receipt_and_writes_no_config(self) -> None:
        wire_dir = ROOT / "scripts" / "flowctl_tracker" / "wire"
        src = "\n".join(p.read_text(encoding="utf-8") for p in sorted(wire_dir.glob("*.py")))
        self.assertNotRegex(src, r"(?m)^\s*(from|import)\s+.*receipt")
        self.assertNotIn("resolve_transaction", src)
        # Reads config.json for destination; must never WRITE it.
        self.assertNotIn("write_text", src)
        self.assertNotIn("atomic", src.lower())
        self.assertNotRegex(src, r"open\([^)]*['\"]w")
        import flowctl_tracker.wire as mod
        self.assertFalse(hasattr(mod, "write_receipt"))
        self.assertFalse(hasattr(mod, "resolve_transaction"))


# ---------------------------------------------------------------------------
# Pre-mutation parent read (the load-bearing acceptance item)
# ---------------------------------------------------------------------------

class PreMutationGate(unittest.TestCase):
    """Write verbs validate BEFORE mutating; mismatch → conflict, no mutation."""

    def _mismatch_case(self, provider, cfg, locator, parent_resp, mut_op):
        ex = fake_execute({"wire-parent-read": parent_resp})
        out = W.dispatch("update", cfg, locator=locator, title="X", execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        ops = [c.op for c in ex.calls]
        self.assertEqual(ops, ["wire-parent-read"],
                         "mismatch must abort before any mutation request")
        self.assertNotIn(mut_op, ops)

    def test_github_mismatch_aborts_with_no_mutation(self) -> None:
        wrong = dict(GH_ISSUE, node_id="I_kwDOOther")
        self._mismatch_case("github", gh_cfg(), loc(GH_NODE, "#42"),
                            ok(wrong), "wire-update")

    def test_gitlab_mismatch_aborts_with_no_mutation(self) -> None:
        wrong = dict(GL_ISSUE, id=1)
        self._mismatch_case("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"),
                            ok(wrong), "wire-update")

    def test_linear_mismatch_aborts_with_no_mutation(self) -> None:
        wrong = dict(LN_ISSUE, id="other-uuid")
        self._mismatch_case("linear", ln_cfg(), loc(LN_UUID, "WOR-17"),
                            gql_issue(wrong), "wire-update")

    def test_jira_mismatch_aborts_with_no_mutation(self) -> None:
        wrong = dict(JR_ISSUE, id="99999")
        self._mismatch_case("jira", jr_cfg(), loc(JR_ID, "SCRUM-1"),
                            ok(wrong), "wire-update")

    def test_every_write_verb_issues_parent_read_first(self) -> None:
        writes = [
            ("update", {"title": "X"}),
            ("comment-add", {"body": "hi"}),
            ("comment-update", {"comment_id": "c1", "body": "hi"}),
            ("comment-delete", {"comment_id": "c1"}),
            ("label", {"add": ["bug"]}),
            ("assign", {"add": ["alice"]}),
        ]
        for verb, kwargs in writes:
            with self.subTest(verb=verb):
                ex = fake_execute({
                    "wire-parent-read": ok(dict(GH_ISSUE, node_id="I_other")),
                })
                out = W.dispatch(verb, gh_cfg(), locator=loc(GH_NODE, "#42"),
                                 execute=ex, **kwargs)
                self.assertIs(out.cls, ErrorClass.CONFLICT)
                self.assertEqual([c.op for c in ex.calls], ["wire-parent-read"])


class PullRequestLink(unittest.TestCase):
    URL = "https://github.com/o/r/pull/7"

    def test_rejects_invalid_url_before_transport(self) -> None:
        for url in ("relative/pull/7", "https://example.test/pull/7\nspoof"):
            with self.subTest(url=url):
                ex = fake_execute({})
                out = W.link_pr(
                    "github", gh_cfg(), loc(GH_NODE, "#42"), ex,
                    url=url,
                )
                self.assertIsInstance(out, TrackerError)
                self.assertEqual(out.subtype, "pr_url")
                self.assertEqual(ex.calls, [])

    def test_github_uses_native_pr_body_ref(self) -> None:
        ex = fake_execute({
            "wire-pr-link-parent-read": ok(GH_ISSUE),
        })
        out = W.link_pr(
            "github", gh_cfg(), loc(GH_NODE, "#42"), ex, url=self.URL)
        self.assertEqual(out["kind"], "native-pr-body-ref")
        self.assertTrue(out["deduped"])

    def test_gitlab_posts_then_deduplicates_exact_url_note(self) -> None:
        note = {
            "id": 9,
            "body": f"Flow-Next PR: {self.URL}",
            "noteable_id": GL_ID,
            "created_at": "2026-07-29T00:00:00Z",
        }
        ex = fake_execute({
            "wire-pr-link-parent-read": [ok(GL_ISSUE), ok(GL_ISSUE)],
            "wire-parent-read": [ok(GL_ISSUE), ok(GL_ISSUE), ok(GL_ISSUE)],
            "wire-comment-list": [ok([]), ok([note])],
            "wire-comment-add": ok(note),
        })
        first = W.link_pr(
            "gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"), ex, url=self.URL)
        second = W.link_pr(
            "gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"), ex, url=self.URL)
        self.assertTrue(first["linked"])
        self.assertFalse(second["linked"])
        self.assertTrue(second["deduped"])
        self.assertEqual(
            [c.op for c in ex.calls].count("wire-comment-add"), 1)

    def test_jira_upserts_remote_link_with_stable_global_id(self) -> None:
        captured = {}

        def capture(request):
            captured.update(json.loads(request.body))
            return empty()

        ex = fake_execute({
            "wire-pr-link-parent-read": ok(JR_ISSUE),
            "wire-pr-link": capture,
        })
        out = W.link_pr(
            "jira", jr_cfg(), loc(JR_ID, "SCRUM-1"), ex, url=self.URL)
        self.assertEqual(out["kind"], "remote-link")
        self.assertEqual(captured["globalId"], f"flow-next:pr:{self.URL}")
        self.assertEqual(captured["object"]["url"], self.URL)

    def test_linear_creates_then_deduplicates_rich_url_attachment(self) -> None:
        attachment = {"id": "att-1", "url": self.URL}
        ex = fake_execute({
            "wire-pr-link-parent-read": [
                gql_issue(LN_ISSUE),
                gql_issue(LN_ISSUE),
            ],
            "wire-pr-link-list": [
                ok({"data": {"issue": {"attachments": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }}}}),
                ok({"data": {"issue": {"attachments": {
                    "nodes": [attachment],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }}}}),
            ],
            "wire-pr-link": ok({"data": {
                "attachmentLinkURL": {
                    "success": True,
                    "attachment": attachment,
                },
            }}),
        })
        first = W.link_pr(
            "linear", ln_cfg(), loc(LN_UUID, "WOR-17"), ex, url=self.URL)
        second = W.link_pr(
            "linear", ln_cfg(), loc(LN_UUID, "WOR-17"), ex, url=self.URL)
        self.assertTrue(first["linked"])
        self.assertFalse(first["deduped"])
        self.assertFalse(second["linked"])
        self.assertTrue(second["deduped"])
        self.assertEqual(second["attachment"], attachment)
        self.assertEqual(
            [c.op for c in ex.calls].count("wire-pr-link"),
            1,
        )
        mutation = next(c for c in ex.calls if c.op == "wire-pr-link")
        payload = json.loads(mutation.body)
        self.assertIn("attachmentLinkURL", payload["query"])
        self.assertEqual(payload["variables"]["url"], self.URL)

    def test_linear_rereads_after_mutation_race(self) -> None:
        attachment = {"id": "att-1", "url": self.URL}
        ex = fake_execute({
            "wire-pr-link-parent-read": gql_issue(LN_ISSUE),
            "wire-pr-link-list": [
                ok({"data": {"issue": {"attachments": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }}}}),
                ok({"data": {"issue": {"attachments": {
                    "nodes": [attachment],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }}}}),
            ],
            "wire-pr-link": TrackerError(
                ErrorClass.INVALID_INPUT,
                "unable to create issue attachment",
                subtype="graphql",
            ),
        })
        out = W.link_pr(
            "linear", ln_cfg(), loc(LN_UUID, "WOR-17"), ex, url=self.URL)
        self.assertFalse(out["linked"])
        self.assertTrue(out["deduped"])
        self.assertEqual(out["attachment"], attachment)


# ---------------------------------------------------------------------------
# Parent-identity availability (response-side; never faked)
# ---------------------------------------------------------------------------

class ParentIdentityAvailability(unittest.TestCase):
    def test_github_comment_add_marks_parent_identity_not_available(self) -> None:
        comment = {"id": 55, "body": "hi", "html_url": "https://x",
                   "issue_url": "https://api.github.com/repos/o/r/issues/42"}
        ex = fake_execute({
            "wire-parent-read": ok(GH_ISSUE),
            "wire-comment-add": ok(comment),
        })
        out = W.dispatch("comment-add", gh_cfg(), locator=loc(GH_NODE, "#42"),
                         body="hi", execute=ex)
        self.assertEqual(out["parent_identity"], "not_available")

    def test_jira_comment_add_marks_parent_identity_not_available(self) -> None:
        ex = fake_execute({
            "wire-parent-read": ok(JR_ISSUE),
            "wire-comment-add": ok({"id": "c1", "body": "hi"}),
        })
        out = W.dispatch("comment-add", jr_cfg(), locator=loc(JR_ID, "SCRUM-1"),
                         body="hi", execute=ex)
        self.assertEqual(out["parent_identity"], "not_available")

    def test_gitlab_comment_validates_via_noteable_id(self) -> None:
        note = {"id": 9, "body": "hi", "noteable_id": GL_ID, "system": False}
        ex = fake_execute({
            "wire-parent-read": ok(GL_ISSUE),
            "wire-comment-add": ok(note),
        })
        out = W.dispatch("comment-add", gl_cfg(),
                         locator=loc(str(GL_ID), "g/p#12"), body="hi", execute=ex)
        self.assertEqual(out["parent_identity"], "validated")

    def test_linear_comment_validates_via_issue_selection(self) -> None:
        ex = fake_execute({
            "wire-parent-read": gql_issue(LN_ISSUE),
            "wire-comment-add": ok({"data": {"commentCreate": {
                "success": True,
                "comment": {"id": "c1", "body": "hi",
                            "issue": {"id": LN_UUID}}}}}),
        })
        out = W.dispatch("comment-add", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                         body="hi", execute=ex)
        self.assertEqual(out["parent_identity"], "validated")

    def test_github_issue_update_validates_on_response(self) -> None:
        updated = dict(GH_ISSUE, title="New")
        ex = fake_execute({
            "wire-parent-read": ok(GH_ISSUE),
            "wire-update": ok(updated),
        })
        out = W.dispatch("update", gh_cfg(), locator=loc(GH_NODE, "#42"),
                         title="New", execute=ex)
        self.assertEqual(out["parent_identity"], "validated")
        self.assertEqual(out["title"], "New")


# ---------------------------------------------------------------------------
# comment-update / comment-delete require parent locator
# ---------------------------------------------------------------------------

class CommentMutationsRequireParent(unittest.TestCase):
    def test_comment_update_rejects_missing_locator(self) -> None:
        out = W.dispatch("comment-update", gh_cfg(), locator=None,
                         comment_id="c1", body="x", execute=fake_execute({}))
        self.assertIs(out.cls, ErrorClass.INVALID_INPUT)

    def test_comment_delete_rejects_missing_locator(self) -> None:
        out = W.dispatch("comment-delete", gh_cfg(), locator=None,
                         comment_id="c1", execute=fake_execute({}))
        self.assertIs(out.cls, ErrorClass.INVALID_INPUT)

    def test_comment_update_rejects_missing_comment_id(self) -> None:
        out = W.dispatch("comment-update", gh_cfg(),
                         locator=loc(GH_NODE, "#42"), body="x",
                         execute=fake_execute({}))
        self.assertIs(out.cls, ErrorClass.INVALID_INPUT)

    def test_gitlab_comment_update_path_includes_issue_and_note(self) -> None:
        ex = fake_execute({
            "wire-parent-read": ok(GL_ISSUE),
            "wire-comment-update": ok({"id": 9, "body": "x",
                                       "noteable_id": GL_ID}),
        })
        W.dispatch("comment-update", gl_cfg(),
                   locator=loc(str(GL_ID), "g/p#12"),
                   comment_id="9", body="x", execute=ex)
        mut = [c for c in ex.calls if c.op == "wire-comment-update"][0]
        self.assertIn("issues/12/notes/9", cli_endpoint(mut))

    def test_jira_comment_delete_path_includes_issue_and_comment(self) -> None:
        ex = fake_execute({
            "wire-parent-read": ok(JR_ISSUE),
            "wire-comment-delete": empty(),
        })
        W.dispatch("comment-delete", jr_cfg(), locator=loc(JR_ID, "SCRUM-1"),
                   comment_id="99", execute=ex)
        mut = [c for c in ex.calls if c.op == "wire-comment-delete"][0]
        self.assertIn(f"/issue/{JR_ID}/comment/99", mut.url_or_argv)


# ---------------------------------------------------------------------------
# list-open: locator-free + GitHub PR filter
# ---------------------------------------------------------------------------

class ListOpen(unittest.TestCase):
    def test_list_open_takes_no_locator(self) -> None:
        ex = fake_execute({"wire-list-open": ok([GH_ISSUE])})
        out = W.dispatch("list-open", gh_cfg(), locator=None, execute=ex)
        self.assertIn("issues", out)
        self.assertEqual([c.op for c in ex.calls], ["wire-list-open"])

    def test_github_filters_pull_requests(self) -> None:
        pr = dict(GH_ISSUE, number=99, node_id="I_pr",
                  pull_request={"url": "https://api.github.com/repos/o/r/pulls/99"})
        ex = fake_execute({"wire-list-open": ok([GH_ISSUE, pr])})
        out = W.dispatch("list-open", gh_cfg(), execute=ex)
        self.assertEqual(len(out["issues"]), 1)
        self.assertEqual(out["issues"][0]["identifier"], "#42")

    def test_gitlab_uses_opened_not_open(self) -> None:
        ex = fake_execute({"wire-list-open": ok([GL_ISSUE])})
        W.dispatch("list-open", gl_cfg(), execute=ex)
        endpoint = cli_endpoint(ex.calls[0])
        self.assertIn("state=opened", endpoint)

    def test_ready_state_unset_is_transport_free_noop_for_all_providers(self) -> None:
        # Linear refuses instead (fn-182.2 / #311) - covered separately below.
        for name, cfg in (
            ("github", gh_cfg()),
            ("gitlab", gl_cfg()),
            ("jira", jr_cfg()),
        ):
            with self.subTest(provider=name):
                del cfg["tracker"]["readyState"]
                ex = fake_execute({})
                out = W.dispatch("list-open", cfg, execute=ex)
                self.assertEqual(out, {"issues": [], "truncated": False})
                self.assertEqual(ex.calls, [])

    def test_linear_list_open_unset_ready_state_refuses(self) -> None:
        """#311: a silent empty against a populated board is unhandleable."""
        for label, mutate in (
            ("absent", lambda c: c["tracker"].pop("readyState")),
            ("null", lambda c: c["tracker"].__setitem__("readyState", None)),
            ("blank", lambda c: c["tracker"].__setitem__("readyState", " ")),
        ):
            with self.subTest(readyState=label):
                cfg = ln_cfg()
                mutate(cfg)
                ex = fake_execute({})
                out = W.dispatch("list-open", cfg, execute=ex)
                self.assertIsInstance(out, TrackerError)
                self.assertEqual(out.cls, ErrorClass.UNRESOLVED)
                self.assertEqual(out.subtype, "ready_state")
                self.assertEqual(out.details, {"key": "tracker.readyState"})
                # Names WHAT is unresolved and HOW to resolve it...
                self.assertIn("tracker.readyState", out.message)
                self.assertIn("flowctl config set tracker.readyState", out.message)
                # ...without telling the user to arm the projection.
                self.assertIn("valid configuration", out.message)
                self.assertEqual(ex.calls, [])

    def test_github_and_gitlab_filter_the_exact_ready_label(self) -> None:
        for cfg, response in (
            (gh_cfg(), ok([GH_ISSUE])),
            (gl_cfg(), ok([GL_ISSUE])),
        ):
            cfg["tracker"]["readyState"] = "Ready & Queued"
            ex = fake_execute({"wire-list-open": response})
            W.dispatch("list-open", cfg, execute=ex)
            params = parse_qs(urlparse(cli_endpoint(ex.calls[0])).query)
            self.assertEqual(params["labels"], ["Ready & Queued"])

    def test_linear_list_open(self) -> None:
        ex = fake_execute({"wire-list-open": ok({"data": {"issues": {
            "nodes": [LN_ISSUE]}}})})
        out = W.dispatch("list-open", ln_cfg(), execute=ex)
        self.assertEqual(out["issues"][0]["id"], LN_UUID)
        variables = json.loads(ex.calls[0].body)["variables"]
        self.assertEqual(
            variables["filter"]["state"],
            {"name": {"eqIgnoreCase": "Ready"}},
        )
        self.assertNotIn("type", variables["filter"]["state"])

    def test_jira_list_open(self) -> None:
        ex = fake_execute({"wire-list-open": ok({"issues": [JR_ISSUE]})})
        out = W.dispatch("list-open", jr_cfg(), execute=ex)
        self.assertEqual(out["issues"][0]["id"], JR_ID)
        request = ex.calls[0]
        self.assertEqual(request.method, "GET")
        self.assertIn("/rest/api/2/search?", str(request.url_or_argv))
        params = parse_qs(urlparse(str(request.url_or_argv)).query)
        self.assertEqual(
            params["jql"],
            ['project = SCRUM AND status = "Ready for Work"'],
        )

    def test_jira_jql_escapes_ready_state_and_rejects_invalid_project(self) -> None:
        cfg = jr_cfg()
        cfg["tracker"]["readyState"] = 'Ready \\\\ "Now"'
        ex = fake_execute({"wire-list-open": ok({"issues": []})})
        W.dispatch("list-open", cfg, execute=ex)
        params = parse_qs(urlparse(str(ex.calls[0].url_or_argv)).query)
        self.assertEqual(
            params["jql"],
            ['project = SCRUM AND status = "Ready \\\\\\\\ \\"Now\\""'],
        )

        cfg["tracker"]["resolved"]["destination"]["projectKey"] = 'SCRUM" OR 1=1'
        bad_ex = fake_execute({})
        out = W.dispatch("list-open", cfg, execute=bad_ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
        self.assertEqual(bad_ex.calls, [])

    def test_jira_cloud_list_open_uses_cursor_search(self) -> None:
        cfg = jr_cfg()
        cfg["tracker"]["resolved"]["destination"]["apiVersion"] = 3
        first = {"issues": [JR_ISSUE], "isLast": False, "nextPageToken": "next-1"}
        last = {"issues": [dict(JR_ISSUE, id="10043")], "isLast": True}
        ex = fake_execute({"wire-list-open": [ok(first), ok(last)]})
        out = W.dispatch("list-open", cfg, execute=ex)

        self.assertEqual(len(out["issues"]), 2)
        self.assertFalse(out["truncated"])
        self.assertEqual([call.method for call in ex.calls], ["POST", "POST"])
        self.assertTrue(all(str(call.url_or_argv).endswith(
            "/rest/api/3/search/jql") for call in ex.calls))
        first_body = json.loads(ex.calls[0].body)
        second_body = json.loads(ex.calls[1].body)
        self.assertNotIn("nextPageToken", first_body)
        self.assertEqual(second_body["nextPageToken"], "next-1")
        self.assertEqual(
            first_body["jql"],
            'project = SCRUM AND status = "Ready for Work"',
        )

    def test_jira_cloud_cursor_without_progress_is_tracker_error(self) -> None:
        cfg = jr_cfg()
        cfg["tracker"]["resolved"]["destination"]["apiVersion"] = 3
        ex = fake_execute({"wire-list-open": ok({
            "issues": [], "isLast": False, "nextPageToken": "",
        })})
        out = W.dispatch("list-open", cfg, execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.TRANSPORT)
        self.assertEqual(out.subtype, "malformed_body")


# ---------------------------------------------------------------------------
# list-states: context-free workflow-state enumeration (linear/jira; read-only)
# ---------------------------------------------------------------------------

class ListStates(unittest.TestCase):
    def test_linear_success_shape(self) -> None:
        ex = fake_execute({"wire-list-states": ok({"data": {"workflowStates": {
            "nodes": [
                {"id": "s1", "name": "Todo", "type": "unstarted"},
                {"id": "s2", "name": "Done", "type": "completed"},
            ],
            "pageInfo": {"hasNextPage": False}}}})})
        out = W.dispatch("list-states", ln_cfg(), execute=ex)
        self.assertEqual(out, {
            "states": [
                {"id": "s1", "name": "Todo", "type": "unstarted"},
                {"id": "s2", "name": "Done", "type": "completed"},
            ],
            "complete": True,
        })
        self.assertEqual(set(out), {"states", "complete"})
        for state in out["states"]:
            self.assertEqual(set(state), {"id", "name", "type"})

    def test_linear_truncated_is_success_with_complete_false(self) -> None:
        page = {
            "nodes": [{"id": "s1", "name": "Todo", "type": "unstarted"}],
            "pageInfo": {"hasNextPage": True},
        }
        responses = {"wire-list-states": ok({"data": {"workflowStates": page}})}
        out = W.dispatch("list-states", ln_cfg(), execute=fake_execute(responses))
        self.assertEqual(out["states"], [
            {"id": "s1", "name": "Todo", "type": "unstarted"},
        ])
        self.assertIs(out["complete"], False)
        self.assertEqual(set(out), {"states", "complete"})

        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            (flow / "config.json").write_text(
                json.dumps(ln_cfg()), encoding="utf-8")
            payload, code = W.run(
                flow, "list-states",
                execute=fake_execute(responses))
            self.assertEqual(code, 0)
            data = json.loads(payload)
            self.assertIs(data["success"], True)
            self.assertIs(data["data"]["complete"], False)
            self.assertEqual(data["data"]["states"], [
                {"id": "s1", "name": "Todo", "type": "unstarted"},
            ])

    def test_linear_malformed_node_is_transport_never_a_short_complete_list(
            self) -> None:
        # A shape-broken node must fail loudly - a quietly shrunken list
        # flagged complete:true is the exact failure `complete` guards.
        ex = fake_execute({"wire-list-states": ok({"data": {"workflowStates": {
            "nodes": [
                {"id": "s1", "name": "Todo", "type": "unstarted"},
                {"name": "orphan without id"},
            ],
            "pageInfo": {"hasNextPage": False}}}})})
        out = W.dispatch("list-states", ln_cfg(), execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.TRANSPORT)
        self.assertEqual(out.subtype, "malformed_body")

    def test_linear_missing_page_info_is_transport_never_complete(
            self) -> None:
        # Valid nodes with absent pagination metadata must fail loudly -
        # coercing missing hasNextPage to complete:true asserts exhaustion
        # that was never proven.
        ex = fake_execute({"wire-list-states": ok({"data": {"workflowStates": {
            "nodes": [
                {"id": "s1", "name": "Todo", "type": "unstarted"},
            ]}}})})
        out = W.dispatch("list-states", ln_cfg(), execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.TRANSPORT)
        self.assertEqual(out.subtype, "malformed_body")

    def test_jira_success_scopes_to_resolved_issue_type_and_is_complete(
            self) -> None:
        # destination.statusIds is pinned to issueTypeId (10001 in jr_cfg) -
        # the Bug type's extra status must NOT leak into the answer, or the
        # documented liveness check would validate a status that never
        # applied to the pinned type.
        ex = fake_execute({"wire-list-states": ok([
            {"id": "10001", "name": "Task", "statuses": [
                {"id": "1", "name": "To Do",
                 "statusCategory": {"key": "new"}},
                {"id": "3", "name": "Done",
                 "statusCategory": {"key": "done"}},
            ]},
            {"id": "10002", "name": "Bug", "statuses": [
                {"id": "1", "name": "To Do",
                 "statusCategory": {"key": "new"}},
                {"id": "7", "name": "Triage",
                 "statusCategory": {"key": "new"}},
            ]},
        ])})
        out = W.dispatch("list-states", jr_cfg(), execute=ex)
        self.assertEqual(out, {
            "states": [
                {"id": "1", "name": "To Do", "type": "new"},
                {"id": "3", "name": "Done", "type": "done"},
            ],
            "complete": True,
        })
        self.assertEqual(set(out), {"states", "complete"})
        for state in out["states"]:
            self.assertEqual(set(state), {"id", "name", "type"})
        self.assertTrue(str(ex.calls[0].url_or_argv).endswith(
            "/rest/api/2/project/SCRUM/statuses"))

    def test_jira_missing_issue_type_id_is_unresolved_no_transport_call(
            self) -> None:
        # NEVER "first entry": without the pinned issue type the answer
        # would be some other type's workflow.
        cfg = jr_cfg()
        cfg["tracker"]["resolved"]["destination"].pop("issueTypeId")
        ex = fake_execute({})
        out = W.dispatch("list-states", cfg, execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.UNRESOLVED)
        self.assertEqual(out.subtype, "statusIds")
        self.assertEqual(ex.calls, [])

    def test_jira_no_entry_for_issue_type_is_unresolved(self) -> None:
        # The pinned type vanished from the project (type retired /
        # destination stale) - refuse rather than answer from another type.
        ex = fake_execute({"wire-list-states": ok([
            {"id": "10002", "name": "Bug", "statuses": [
                {"id": "1", "name": "To Do",
                 "statusCategory": {"key": "new"}},
            ]},
        ])})
        out = W.dispatch("list-states", jr_cfg(), execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.UNRESOLVED)
        self.assertEqual(out.subtype, "statusIds")

    def test_jira_malformed_status_entry_is_transport_never_a_short_list(
            self) -> None:
        # Same guarantee as the Linear twin: broken entries fail loudly.
        ex = fake_execute({"wire-list-states": ok([
            {"id": "10001", "name": "Task", "statuses": [
                {"id": "1", "name": "To Do",
                 "statusCategory": {"key": "new"}},
                {"name": "orphan without id"},
            ]},
        ])})
        out = W.dispatch("list-states", jr_cfg(), execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.TRANSPORT)
        self.assertEqual(out.subtype, "malformed_body")

    def test_github_and_gitlab_refuse_before_transport(self) -> None:
        for name, cfg in (("github", gh_cfg()), ("gitlab", gl_cfg())):
            with self.subTest(provider=name):
                ex = fake_execute({})
                out = W.dispatch("list-states", cfg, execute=ex)
                self.assertIsInstance(out, TrackerError)
                self.assertIs(out.cls, ErrorClass.CAPABILITY)
                self.assertEqual(out.subtype, "workflow_states")
                self.assertEqual(ex.calls, [])

    def test_unresolved_destination_makes_no_transport_call(self) -> None:
        ln_missing = ln_cfg()
        ln_missing["tracker"].pop("resolved")
        ln_no_team = ln_cfg()
        ln_no_team["tracker"]["resolved"]["destination"].pop("teamId")
        jr_no_key = jr_cfg()
        jr_no_key["tracker"]["resolved"]["destination"].pop("projectKey")
        jr_no_key["tracker"]["perTracker"].pop("projectKey")
        cases = (
            ("linear-missing-destination", ln_missing),
            ("linear-missing-teamId", ln_no_team),
            ("jira-missing-projectKey", jr_no_key),
        )
        for label, cfg in cases:
            with self.subTest(case=label):
                ex = fake_execute({})
                out = W.dispatch("list-states", cfg, execute=ex)
                self.assertIsInstance(out, TrackerError)
                self.assertIs(out.cls, ErrorClass.UNRESOLVED)
                self.assertEqual(ex.calls, [])

    def test_malformed_body_is_transport(self) -> None:
        cases = (
            ("linear", ln_cfg(), {"wire-list-states": ok(
                {"data": {"workflowStates": "nope"}})}),
            ("jira", jr_cfg(), {"wire-list-states": ok({"not": "a list"})}),
        )
        for name, cfg, responses in cases:
            with self.subTest(provider=name):
                out = W.dispatch("list-states", cfg,
                                 execute=fake_execute(responses))
                self.assertIsInstance(out, TrackerError)
                self.assertIs(out.cls, ErrorClass.TRANSPORT)
                self.assertEqual(out.subtype, "malformed_body")

    def test_run_writes_no_flow_files_on_success_truncated_or_error(self) -> None:
        ln_ok = {"wire-list-states": ok({"data": {"workflowStates": {
            "nodes": [{"id": "s1", "name": "Todo", "type": "unstarted"}],
            "pageInfo": {"hasNextPage": False}}}})}
        ln_trunc = {"wire-list-states": ok({"data": {"workflowStates": {
            "nodes": [{"id": "s1", "name": "Todo", "type": "unstarted"}],
            "pageInfo": {"hasNextPage": True}}}})}
        ln_bad = {"wire-list-states": ok({"data": {"workflowStates": "nope"}})}
        cases = (
            ("success", ln_cfg(), ln_ok),
            ("truncated", ln_cfg(), ln_trunc),
            ("capability", gh_cfg(), {}),
            ("malformed", ln_cfg(), ln_bad),
        )
        for label, cfg, responses in cases:
            with self.subTest(outcome=label):
                with tempfile.TemporaryDirectory() as tmp:
                    flow = Path(tmp)
                    (flow / "config.json").write_text(
                        json.dumps(cfg), encoding="utf-8")
                    before_cfg = (flow / "config.json").read_bytes()
                    before_tree = sorted(
                        p.relative_to(flow) for p in flow.rglob("*"))
                    W.run(flow, "list-states",
                          execute=fake_execute(responses))
                    self.assertEqual(
                        (flow / "config.json").read_bytes(), before_cfg)
                    after_tree = sorted(
                        p.relative_to(flow) for p in flow.rglob("*"))
                    self.assertEqual(after_tree, before_tree)


# ---------------------------------------------------------------------------
# All verbs × 4 providers (happy path via fake transport)
# ---------------------------------------------------------------------------

class AllVerbsAllProviders(unittest.TestCase):
    """One green path per (verb, provider) — regresses a missing adapter."""

    def test_read_all(self) -> None:
        cases = [
            ("github", gh_cfg(), loc(GH_NODE, "#42"),
             {"wire-read": ok(GH_ISSUE)}, GH_NODE),
            ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"),
             {"wire-read": ok(GL_ISSUE)}, str(GL_ID)),
            ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"),
             {"wire-read": gql_issue(LN_ISSUE)}, LN_UUID),
            ("jira", jr_cfg(), loc(JR_ID, "SCRUM-1"),
             {"wire-read": ok(JR_ISSUE)}, JR_ID),
        ]
        for provider, cfg, locator, responses, expect_id in cases:
            with self.subTest(provider=provider):
                out = W.dispatch("read", cfg, locator=locator,
                                 execute=fake_execute(responses))
                self.assertEqual(str(out["id"]), expect_id)
                self.assertEqual(out["parent_identity"], "validated")

    def test_update_all(self) -> None:
        cases = [
            ("github", gh_cfg(), loc(GH_NODE, "#42"),
             {"wire-parent-read": ok(GH_ISSUE),
              "wire-update": ok(dict(GH_ISSUE, title="N"))}),
            ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"),
             {"wire-parent-read": ok(GL_ISSUE),
              "wire-update": ok(dict(GL_ISSUE, title="N"))}),
            ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"),
             {"wire-parent-read": gql_issue(LN_ISSUE),
              "wire-update": ok({"data": {"issueUpdate": {
                  "success": True, "issue": dict(LN_ISSUE, title="N")}}})}),
            ("jira", jr_cfg(), loc(JR_ID, "SCRUM-1"),
             {"wire-parent-read": ok(JR_ISSUE), "wire-update": empty()}),
        ]
        for provider, cfg, locator, responses in cases:
            with self.subTest(provider=provider):
                out = W.dispatch("update", cfg, locator=locator, title="N",
                                 execute=fake_execute(responses))
                self.assertNotIsInstance(out, TrackerError)
                # Jira PUT is a 204: no response-side identity to validate.
                expected = "not_available" if provider == "jira" else "validated"
                self.assertEqual(out["parent_identity"], expected)

    def test_comment_add_all(self) -> None:
        cases = [
            ("github", gh_cfg(), loc(GH_NODE, "#42"),
             {"wire-parent-read": ok(GH_ISSUE),
              "wire-comment-add": ok({"id": 1, "body": "hi"})}),
            ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"),
             {"wire-parent-read": ok(GL_ISSUE),
              "wire-comment-add": ok({"id": 1, "body": "hi",
                                      "noteable_id": GL_ID})}),
            ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"),
             {"wire-parent-read": gql_issue(LN_ISSUE),
              "wire-comment-add": ok({"data": {"commentCreate": {
                  "success": True,
                  "comment": {"id": "c", "body": "hi",
                              "issue": {"id": LN_UUID}}}}})}),
            ("jira", jr_cfg(), loc(JR_ID, "SCRUM-1"),
             {"wire-parent-read": ok(JR_ISSUE),
              "wire-comment-add": ok({"id": "c", "body": "hi"})}),
        ]
        for provider, cfg, locator, responses in cases:
            with self.subTest(provider=provider):
                out = W.dispatch("comment-add", cfg, locator=locator, body="hi",
                                 execute=fake_execute(responses))
                self.assertNotIsInstance(out, TrackerError)
                self.assertIn(out["parent_identity"],
                              ("validated", "not_available"))

    def test_comment_list_all(self) -> None:
        cases = [
            ("github", gh_cfg(), loc(GH_NODE, "#42"),
             {"wire-comment-list": ok([{"id": 1, "body": "a"}])},
             "not_available"),
            ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"),
             {"wire-comment-list": ok([
                 {"id": 1, "body": "a", "noteable_id": GL_ID, "system": False},
                 {"id": 2, "body": "sys", "noteable_id": GL_ID, "system": True},
             ])}, "validated"),
            ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"),
             {"wire-comment-list": ok({"data": {"issue": {
                 "id": LN_UUID,
                 "comments": {"nodes": [{"id": "c", "body": "a"}]}}}})},
             "validated"),
            ("jira", jr_cfg(), loc(JR_ID, "SCRUM-1"),
             {"wire-comment-list": ok({"comments": [{"id": "c", "body": "a"}]})},
             "not_available"),
        ]
        for provider, cfg, locator, responses, identity in cases:
            with self.subTest(provider=provider):
                out = W.dispatch("comment-list", cfg, locator=locator,
                                 execute=fake_execute(responses))
                self.assertEqual(out["parent_identity"], identity)
                self.assertEqual(len(out["comments"]), 1,
                                 "gitlab must filter system notes")

    def test_comment_update_all(self) -> None:
        cases = [
            ("github", gh_cfg(), loc(GH_NODE, "#42"),
             {"wire-parent-read": ok(GH_ISSUE),
              "wire-comment-belong": ok({
                  "id": 1, "body": "x",
                  "issue_url": "https://api.github.com/repos/o/r/issues/42"}),
              "wire-comment-update": ok({"id": 1, "body": "x"})}),
            ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"),
             {"wire-parent-read": ok(GL_ISSUE),
              "wire-comment-update": ok({"id": 1, "body": "x",
                                         "noteable_id": GL_ID})}),
            ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"),
             {"wire-parent-read": gql_issue(LN_ISSUE),
              "wire-comment-belong": ok({"data": {"comment": {
                  "id": "c", "issue": {"id": LN_UUID}}}}),
              "wire-comment-update": ok({"data": {"commentUpdate": {
                  "success": True,
                  "comment": {"id": "c", "body": "x",
                              "issue": {"id": LN_UUID}}}}})}),
            ("jira", jr_cfg(), loc(JR_ID, "SCRUM-1"),
             {"wire-parent-read": ok(JR_ISSUE),
              "wire-comment-update": ok({"id": "c", "body": "x"})}),
        ]
        for provider, cfg, locator, responses in cases:
            with self.subTest(provider=provider):
                out = W.dispatch("comment-update", cfg, locator=locator,
                                 comment_id="1", body="x",
                                 execute=fake_execute(responses))
                self.assertNotIsInstance(out, TrackerError)

    def test_comment_delete_all(self) -> None:
        cases = [
            ("github", gh_cfg(), loc(GH_NODE, "#42"),
             {"wire-parent-read": ok(GH_ISSUE),
              "wire-comment-belong": ok({
                  "id": 1, "body": "x",
                  "issue_url": "https://api.github.com/repos/o/r/issues/42"}),
              "wire-comment-delete": empty()}),
            ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"),
             {"wire-parent-read": ok(GL_ISSUE), "wire-comment-delete": empty()}),
            ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"),
             {"wire-parent-read": gql_issue(LN_ISSUE),
              "wire-comment-belong": ok({"data": {"comment": {
                  "id": "1", "issue": {"id": LN_UUID}}}}),
              "wire-comment-delete": ok({"data": {"commentDelete": {
                  "success": True}}})}),
            ("jira", jr_cfg(), loc(JR_ID, "SCRUM-1"),
             {"wire-parent-read": ok(JR_ISSUE), "wire-comment-delete": empty()}),
        ]
        for provider, cfg, locator, responses in cases:
            with self.subTest(provider=provider):
                out = W.dispatch("comment-delete", cfg, locator=locator,
                                 comment_id="1", execute=fake_execute(responses))
                self.assertEqual(out["deleted"], "1")

    def test_label_all(self) -> None:
        cases = [
            ("github", gh_cfg(), loc(GH_NODE, "#42"),
             {"wire-parent-read": ok(GH_ISSUE),
              "wire-label": ok([{"name": "bug"}]),
              "wire-label-readback": ok(GH_ISSUE)}, ["ready"]),
            ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"),
             {"wire-parent-read": ok(GL_ISSUE),
              "wire-label": ok(dict(GL_ISSUE, labels=["bug", "ready"]))},
             ["ready"]),
            ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"),
             {"wire-parent-read": gql_issue(LN_ISSUE),
              "wire-label": ok({"data": {"issueUpdate": {
                  "success": True, "issue": LN_ISSUE}}})}, ["ready"]),
            ("jira", jr_cfg(), loc(JR_ID, "SCRUM-1"),
             {"wire-parent-read": ok(JR_ISSUE), "wire-label": empty()},
             ["ready"]),
        ]
        for provider, cfg, locator, responses, add in cases:
            with self.subTest(provider=provider):
                out = W.dispatch("label", cfg, locator=locator, add=add,
                                 execute=fake_execute(responses))
                self.assertNotIsInstance(out, TrackerError)

    def test_assign_all(self) -> None:
        cases = [
            ("github", gh_cfg(), loc(GH_NODE, "#42"),
             {"wire-parent-read": ok(GH_ISSUE),
              "wire-assign": ok({"assignees": [{"login": "alice"}]}),
              "wire-assign-readback": ok(GH_ISSUE)}, ["alice"]),
            ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"),
             {"wire-parent-read": ok(GL_ISSUE),
              "wire-assign": ok(GL_ISSUE)}, ["8"]),
            ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"),
             {"wire-parent-read": gql_issue(LN_ISSUE),
              "wire-assign": ok({"data": {"issueUpdate": {
                  "success": True, "issue": LN_ISSUE}}})}, ["user-2"]),
            ("jira", jr_cfg(), loc(JR_ID, "SCRUM-1"),
             {"wire-parent-read": ok(JR_ISSUE), "wire-assign": empty()},
             ["acct-2"]),
        ]
        for provider, cfg, locator, responses, add in cases:
            with self.subTest(provider=provider):
                out = W.dispatch("assign", cfg, locator=locator, add=add,
                                 execute=fake_execute(responses))
                self.assertNotIsInstance(out, TrackerError)

    def test_list_open_all(self) -> None:
        cases = [
            ("github", gh_cfg(), {"wire-list-open": ok([GH_ISSUE])}),
            ("gitlab", gl_cfg(), {"wire-list-open": ok([GL_ISSUE])}),
            ("linear", ln_cfg(), {"wire-list-open": ok({"data": {"issues": {
                "nodes": [LN_ISSUE]}}})}),
            ("jira", jr_cfg(), {"wire-list-open": ok({"issues": [JR_ISSUE]})}),
        ]
        for provider, cfg, responses in cases:
            with self.subTest(provider=provider):
                out = W.dispatch("list-open", cfg, execute=fake_execute(responses))
                self.assertEqual(len(out["issues"]), 1)


# ---------------------------------------------------------------------------
# Addressing + transport routing
# ---------------------------------------------------------------------------

class Addressing(unittest.TestCase):
    def test_github_addresses_by_number_never_node_id(self) -> None:
        ex = fake_execute({"wire-read": ok(GH_ISSUE)})
        W.dispatch("read", gh_cfg(), locator=loc(GH_NODE, "#42"), execute=ex)
        endpoint = cli_endpoint(ex.calls[0])
        self.assertEqual(endpoint, "repos/o/r/issues/42")
        self.assertNotIn(GH_NODE, endpoint)

    def test_gitlab_addresses_by_iid_never_global_id(self) -> None:
        ex = fake_execute({"wire-read": ok(GL_ISSUE)})
        W.dispatch("read", gl_cfg(), locator=loc(str(GL_ID), "g/p#12"), execute=ex)
        endpoint = cli_endpoint(ex.calls[0])
        self.assertEqual(endpoint, "projects/1/issues/12")
        self.assertNotIn(str(GL_ID), endpoint.split("issues/")[-1])

    def test_github_gitlab_use_cli_argv(self) -> None:
        ex = fake_execute({"wire-read": ok(GH_ISSUE)})
        W.dispatch("read", gh_cfg(), locator=loc(GH_NODE, "#42"), execute=ex)
        self.assertEqual(ex.calls[0].url_or_argv[:2], ["gh", "api"])

        ex2 = fake_execute({"wire-read": ok(GL_ISSUE)})
        W.dispatch("read", gl_cfg(), locator=loc(str(GL_ID), "g/p#12"), execute=ex2)
        self.assertEqual(ex2.calls[0].url_or_argv[:2], ["glab", "api"])

    def test_linear_uses_graphql_http(self) -> None:
        ex = fake_execute({"wire-read": gql_issue(LN_ISSUE)})
        W.dispatch("read", ln_cfg(), locator=loc(LN_UUID, "WOR-17"), execute=ex)
        self.assertEqual(ex.calls[0].url_or_argv, W.LINEAR_GQL)
        self.assertEqual(ex.calls[0].method, "POST")

    def test_jira_uses_rest_http_with_base_url(self) -> None:
        ex = fake_execute({"wire-read": ok(JR_ISSUE)})
        W.dispatch("read", jr_cfg(), locator=loc(JR_ID, "SCRUM-1"), execute=ex)
        self.assertTrue(str(ex.calls[0].url_or_argv).startswith(
            "https://ex.atlassian.net/rest/api/2/issue/"))


class ReadOnlyMayValidateOnResponse(unittest.TestCase):
    def test_read_conflict_on_durable_mismatch(self) -> None:
        wrong = dict(GH_ISSUE, node_id="I_other")
        ex = fake_execute({"wire-read": ok(wrong)})
        out = W.dispatch("read", gh_cfg(), locator=loc(GH_NODE, "#42"), execute=ex)
        self.assertIs(out.cls, ErrorClass.CONFLICT)


class UnresolvedAndInactive(unittest.TestCase):
    def test_inactive_tracker(self) -> None:
        out = W.dispatch("list-open", {"tracker": {"type": "off"}},
                         execute=fake_execute({}))
        self.assertIs(out.cls, ErrorClass.INACTIVE)

    def test_missing_destination_is_unresolved(self) -> None:
        out = W.dispatch("read", {"tracker": {"type": "github"}},
                         locator=loc(GH_NODE, "#42"), execute=fake_execute({}))
        self.assertIs(out.cls, ErrorClass.UNRESOLVED)


class EnvelopeRun(unittest.TestCase):
    def test_run_emits_success_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            (flow / "config.json").write_text(json.dumps(gh_cfg()), encoding="utf-8")
            ex = fake_execute({"wire-read": ok(GH_ISSUE)})
            payload, code = W.run(flow, "read",
                                  locator=json.dumps(loc(GH_NODE, "#42")),
                                  execute=ex)
            self.assertEqual(code, 0)
            data = json.loads(payload)
            self.assertTrue(data["success"])
            self.assertEqual(data["data"]["id"], GH_NODE)

    def test_run_non_utf8_body_file_is_invalid_input_envelope(self) -> None:
        """UnicodeDecodeError at the --body-file read must yield the structured
        invalid-input envelope (nonzero exit, zero outbound), not a traceback."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            (flow / "config.json").write_text(json.dumps(gh_cfg()), encoding="utf-8")
            bf = flow / "body.md"
            bf.write_bytes(b"\xff\xfe garbage")
            ex = fake_execute({})
            payload, code = W.run(flow, "update",
                                  locator=json.dumps(loc(GH_NODE, "#42")),
                                  body_file=str(bf), execute=ex)
            self.assertNotEqual(code, 0)
            data = json.loads(payload)
            self.assertFalse(data["success"])
            self.assertEqual(data["class"], "invalid_input")
            self.assertEqual(ex.calls, [])

    def test_run_emits_conflict_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            (flow / "config.json").write_text(json.dumps(gh_cfg()), encoding="utf-8")
            wrong = dict(GH_ISSUE, node_id="I_other")
            ex = fake_execute({"wire-parent-read": ok(wrong)})
            payload, code = W.run(flow, "update",
                                  locator=json.dumps(loc(GH_NODE, "#42")),
                                  title="X", execute=ex)
            self.assertEqual(code, 10)  # CONFLICT
            self.assertFalse(json.loads(payload)["success"])
            self.assertEqual(json.loads(payload)["class"], "conflict")

    def test_body_update_failure_releases_resource_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            (flow / "config.json").write_text(
                json.dumps(gh_cfg()), encoding="utf-8")
            body = flow / "body.md"
            body.write_text("replacement", encoding="utf-8")
            failure = TrackerError(
                ErrorClass.TRANSPORT, "read failed", subtype="timeout",
                auto_retryable=True)
            payload, code = W.run(
                flow, "update",
                locator=json.dumps(loc(GH_NODE, "#42")),
                body_file=str(body),
                execute=fake_execute({"wire-parent-read": failure}))
            self.assertNotEqual(code, 0)
            self.assertFalse(json.loads(payload)["success"])
            self.assertEqual(
                list((flow / "create-first").glob("body-*.json")), [])


if __name__ == "__main__":
    unittest.main()


class ParentReadAddressesByDisplay(unittest.TestCase):
    """The check is display-address -> compare durable. Reading BY durable
    would compare durable to itself and always pass - vacuous validation that
    misses exactly the project-move the gate exists to catch."""

    def test_linear_parent_read_queries_the_display_identifier(self) -> None:
        ex = fake_execute({"wire-parent-read": gql_issue(LN_ISSUE),
                           "wire-comment-add": ok({"data": {"commentCreate": {
                               "success": True,
                               "comment": {"id": "c1", "body": "x",
                                           "issue": {"id": LN_UUID}}}}})})
        out = W.dispatch("comment-add", ln_cfg(),
                         locator=loc(LN_UUID, "WOR-17"), body="x", execute=ex)
        self.assertNotIsInstance(out, TrackerError)
        variables = json.loads(ex.calls[0].body)["variables"]
        self.assertEqual(variables["id"], "WOR-17",
                         "parent read must address by DISPLAY, not durable")

    def test_linear_moved_identifier_is_caught(self) -> None:
        """Display now resolves to a DIFFERENT issue: conflict, no mutation."""
        other = {**LN_ISSUE, "id": "other-uuid"}
        ex = fake_execute({"wire-parent-read": gql_issue(other)})
        out = W.dispatch("comment-add", ln_cfg(),
                         locator=loc(LN_UUID, "WOR-17"), body="x", execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual(len(ex.calls), 1, "the mutation must never be issued")

    def test_jira_parent_read_addresses_the_display_key(self) -> None:
        ex = fake_execute({"wire-parent-read": ok(JR_ISSUE),
                           "wire-comment-add": ok({"id": "c1", "body": "x"})})
        out = W.dispatch("comment-add", jr_cfg(),
                         locator=loc(JR_ID, "SCRUM-1"), body="x", execute=ex)
        self.assertNotIsInstance(out, TrackerError)
        self.assertIn("/rest/api/2/issue/SCRUM-1", str(ex.calls[0].url_or_argv),
                      "parent read must address by the DISPLAY key")

    def test_jira_moved_key_is_caught(self) -> None:
        moved = {**JR_ISSUE, "id": "99999"}
        ex = fake_execute({"wire-parent-read": ok(moved)})
        out = W.dispatch("update", jr_cfg(), locator=loc(JR_ID, "SCRUM-1"),
                         title="new", execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual(len(ex.calls), 1)


class JiraUpdateReturnsThePostUpdateState(unittest.TestCase):
    def test_updated_fields_are_reflected_not_the_stale_parent(self) -> None:
        ex = fake_execute({"wire-parent-read": ok(JR_ISSUE),
                           "wire-update": empty()})
        out = W.dispatch("update", jr_cfg(), locator=loc(JR_ID, "SCRUM-1"),
                         title="NEW TITLE", body="NEW BODY", execute=ex)
        self.assertNotIsInstance(out, TrackerError)
        self.assertEqual(out["title"], "NEW TITLE")
        self.assertEqual(out["body"], "NEW BODY")


class JiraAssignRemovePreservesUnrelatedAssignee(unittest.TestCase):
    def test_remove_nonmatching_identity_is_a_noop(self) -> None:
        # Current assignee acct-1; removing acct-2 must NOT clear acct-1.
        ex = fake_execute({"wire-parent-read": ok(JR_ISSUE)})
        out = W.dispatch("assign", jr_cfg(), locator=loc(JR_ID, "SCRUM-1"),
                         remove=["acct-2"], execute=ex)
        self.assertNotIsInstance(out, TrackerError, msg=repr(out))
        self.assertEqual([c.op for c in ex.calls], ["wire-parent-read"])
        deg = out.get("degraded")
        self.assertIsInstance(deg, dict)
        self.assertEqual(deg["kind"], "assignee_remove_skipped")
        self.assertEqual(deg["requested"], ["acct-2"])
        self.assertEqual(deg["current"], "acct-1")

    def test_remove_matching_identity_sends_null(self) -> None:
        # Current assignee acct-1; removing acct-1 clears the assignee.
        ex = fake_execute({"wire-parent-read": ok(JR_ISSUE),
                           "wire-assign": empty()})
        out = W.dispatch("assign", jr_cfg(), locator=loc(JR_ID, "SCRUM-1"),
                         remove=["acct-1"], execute=ex)
        self.assertNotIsInstance(out, TrackerError, msg=repr(out))
        assign_call = next(c for c in ex.calls if c.op == "wire-assign")
        body = json.loads(assign_call.body)
        self.assertIsNone(body["fields"]["assignee"])
        self.assertNotIn("degraded", out)


class JiraAssignFieldFollowsPersistedAuthScheme(unittest.TestCase):
    """accountId vs name is a DEPLOYMENT decision (perTracker.authScheme),
    never an identifier-shape heuristic: a valid DC username like `john-doe`
    must go out as `name`, not be misclassified as a Cloud account id."""

    def _cfg(self, scheme) -> dict:
        cfg = jr_cfg()
        if scheme is not None:
            cfg["tracker"]["perTracker"]["authScheme"] = scheme
        return cfg

    def _assign_body(self, cfg, user) -> dict:
        ex = fake_execute({"wire-parent-read": ok(JR_ISSUE),
                           "wire-assign": empty()})
        out = W.dispatch("assign", cfg, locator=loc(JR_ID, "SCRUM-1"),
                         add=[user], execute=ex)
        self.assertNotIsInstance(out, TrackerError, msg=repr(out))
        assign_call = next(c for c in ex.calls if c.op == "wire-assign")
        return json.loads(assign_call.body)

    def test_dc_hyphenated_username_goes_out_as_name(self) -> None:
        body = self._assign_body(self._cfg("bearer-pat"), "john-doe")
        self.assertEqual(body["fields"]["assignee"], {"name": "john-doe"})

    def test_dc_long_username_goes_out_as_name(self) -> None:
        body = self._assign_body(self._cfg("bearer-pat"),
                                 "a.very.long.directory.username")
        self.assertEqual(body["fields"]["assignee"],
                         {"name": "a.very.long.directory.username"})

    def test_cloud_scheme_sends_account_id(self) -> None:
        body = self._assign_body(self._cfg("cloud-basic"), "short")
        self.assertEqual(body["fields"]["assignee"], {"accountId": "short"})

    def test_absent_scheme_defaults_to_cloud_account_id(self) -> None:
        # Mirrors credentials.resolve(): every non-"bearer-pat" authScheme
        # (including absent) takes the Cloud path.
        body = self._assign_body(self._cfg(None), "john-doe")
        self.assertEqual(body["fields"]["assignee"], {"accountId": "john-doe"})


class LinearLabelReusesParentLabels(unittest.TestCase):
    """An auto-created label lives on the issue but not in the pinned config
    labelIds; a later `label --add <same-name>` must resolve its id from the
    parent read instead of running issueLabelCreate again."""

    def test_add_existing_parent_label_skips_create(self) -> None:
        # "urgent" is on the issue (returned by the parent read) but absent
        # from ln_cfg()'s labelIds map.
        issue = dict(LN_ISSUE, labels={"nodes": [
            {"id": "lbl-1", "name": "bug"},
            {"id": "lbl-9", "name": "urgent"}]})
        ex = fake_execute({
            "wire-parent-read": gql_issue(issue),
            "wire-label": ok({"data": {"issueUpdate": {
                "success": True, "issue": issue}}})})
        out = W.dispatch("label", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                         add=["urgent"], execute=ex)
        self.assertNotIsInstance(out, TrackerError, msg=repr(out))
        self.assertEqual([c.op for c in ex.calls],
                         ["wire-parent-read", "wire-label"])
        self.assertNotIn("labels_created", out)
        label_call = next(c for c in ex.calls if c.op == "wire-label")
        body = json.loads(label_call.body)
        self.assertIn("lbl-9", body["variables"]["input"]["labelIds"])

    def test_parent_label_name_matches_case_insensitively(self) -> None:
        # Linear label names are case-insensitively unique per team; the
        # pinned map is keyed lowercased, so the live-read fold must be too.
        issue = dict(LN_ISSUE, labels={"nodes": [
            {"id": "lbl-9", "name": "Urgent"}]})
        ex = fake_execute({
            "wire-parent-read": gql_issue(issue),
            "wire-label": ok({"data": {"issueUpdate": {
                "success": True, "issue": issue}}})})
        out = W.dispatch("label", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                         add=["urgent"], execute=ex)
        self.assertNotIsInstance(out, TrackerError, msg=repr(out))
        self.assertEqual([c.op for c in ex.calls],
                         ["wire-parent-read", "wire-label"])
        self.assertNotIn("labels_created", out)

    def test_remove_resolves_id_from_parent_labels(self) -> None:
        # Removing an auto-created label (absent from config) must find its
        # id via the parent read and drop it from labelIds.
        issue = dict(LN_ISSUE, labels={"nodes": [
            {"id": "lbl-1", "name": "bug"},
            {"id": "lbl-9", "name": "urgent"}]})
        ex = fake_execute({
            "wire-parent-read": gql_issue(issue),
            "wire-label": ok({"data": {"issueUpdate": {
                "success": True, "issue": issue}}})})
        out = W.dispatch("label", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                         remove=["urgent"], execute=ex)
        self.assertNotIsInstance(out, TrackerError, msg=repr(out))
        label_call = next(c for c in ex.calls if c.op == "wire-label")
        body = json.loads(label_call.body)
        self.assertNotIn("lbl-9", body["variables"]["input"]["labelIds"])
        self.assertIn("lbl-1", body["variables"]["input"]["labelIds"])

    def test_truly_unknown_label_still_auto_creates(self) -> None:
        ex = fake_execute({
            "wire-parent-read": gql_issue(LN_ISSUE),
            "wire-label-team-lookup": gql_team_labels([]),
            "wire-label-create": ok({"data": {"issueLabelCreate": {
                "success": True,
                "issueLabel": {"id": "lbl-new", "name": "brand-new"}}}}),
            "wire-label": ok({"data": {"issueUpdate": {
                "success": True, "issue": LN_ISSUE}}})})
        out = W.dispatch("label", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                         add=["brand-new"], execute=ex)
        self.assertNotIsInstance(out, TrackerError, msg=repr(out))
        self.assertEqual(out.get("labels_created"), ["brand-new"])
        self.assertIn("wire-label-create", [c.op for c in ex.calls])


def gql_team_labels(nodes, has_next=False) -> Response:
    return ok({"data": {"team": {"labels": {
        "nodes": nodes,
        "pageInfo": {"hasNextPage": has_next, "endCursor": None}}}}})


class LinearLabelResolvesFromTeamBeforeCreate(unittest.TestCase):
    """A label auto-created while updating issue A lives on the TEAM but on
    neither the pinned config labelIds nor issue B's parent read; adding it to
    issue B must resolve via a live team-labels query, and only a team read
    proving absence may fall through to issueLabelCreate."""

    def test_label_from_another_issue_resolves_via_team_query(self) -> None:
        # "urgent" (lbl-9) was auto-created for issue A; issue B's parent read
        # does not carry it and the config does not pin it.
        ex = fake_execute({
            "wire-parent-read": gql_issue(LN_ISSUE),
            "wire-label-team-lookup": gql_team_labels(
                [{"id": "lbl-9", "name": "urgent"}]),
            "wire-label": ok({"data": {"issueUpdate": {
                "success": True, "issue": LN_ISSUE}}})})
        out = W.dispatch("label", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                         add=["urgent"], execute=ex)
        self.assertNotIsInstance(out, TrackerError, msg=repr(out))
        ops = [c.op for c in ex.calls]
        self.assertNotIn("wire-label-create", ops,
                         "existing team label must be attached, never recreated")
        self.assertNotIn("labels_created", out)
        label_call = next(c for c in ex.calls if c.op == "wire-label")
        body = json.loads(label_call.body)
        self.assertIn("lbl-9", body["variables"]["input"]["labelIds"])

    def test_team_match_is_case_insensitive(self) -> None:
        ex = fake_execute({
            "wire-parent-read": gql_issue(LN_ISSUE),
            "wire-label-team-lookup": gql_team_labels(
                [{"id": "lbl-9", "name": "Urgent"}]),
            "wire-label": ok({"data": {"issueUpdate": {
                "success": True, "issue": LN_ISSUE}}})})
        out = W.dispatch("label", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                         add=["urgent"], execute=ex)
        self.assertNotIsInstance(out, TrackerError, msg=repr(out))
        self.assertNotIn("wire-label-create", [c.op for c in ex.calls])
        self.assertNotIn("labels_created", out)

    def test_truncated_team_listing_does_not_create(self) -> None:
        # Name-filtered yet hasNextPage: the match could sit on an unread
        # page. Unproven absence is never absence - refuse to create.
        ex = fake_execute({
            "wire-parent-read": gql_issue(LN_ISSUE),
            "wire-label-team-lookup": gql_team_labels([], has_next=True)})
        out = W.dispatch("label", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                         add=["urgent"], execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.TRANSPORT)
        self.assertEqual(out.subtype, "truncated")
        self.assertNotIn("wire-label-create", [c.op for c in ex.calls])

    def test_malformed_team_listing_does_not_create(self) -> None:
        ex = fake_execute({
            "wire-parent-read": gql_issue(LN_ISSUE),
            "wire-label-team-lookup": ok({"data": {"team": None}})})
        out = W.dispatch("label", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                         add=["urgent"], execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.TRANSPORT)
        self.assertEqual(out.subtype, "malformed_body")
        self.assertNotIn("wire-label-create", [c.op for c in ex.calls])

    def test_parent_fold_still_short_circuits_the_team_query(self) -> None:
        # Wave-4 economy holds: a label already on THIS issue resolves from
        # the parent read with no team lookup at all.
        issue = dict(LN_ISSUE, labels={"nodes": [
            {"id": "lbl-9", "name": "urgent"}]})
        ex = fake_execute({
            "wire-parent-read": gql_issue(issue),
            "wire-label": ok({"data": {"issueUpdate": {
                "success": True, "issue": issue}}})})
        out = W.dispatch("label", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                         add=["urgent"], execute=ex)
        self.assertNotIsInstance(out, TrackerError, msg=repr(out))
        self.assertEqual([c.op for c in ex.calls],
                         ["wire-parent-read", "wire-label"])


GH_COMMENT = {"id": 1, "body": "hi", "html_url": "https://github.com/c/1"}


class PaginationIsDrainedNeverSilentlyCapped(unittest.TestCase):
    def test_github_comment_list_drains_pages(self) -> None:
        page1 = [dict(GH_COMMENT, id=i) for i in range(W._PAGE_SIZE)]
        page2 = [dict(GH_COMMENT, id=999)]
        ex = fake_execute({"wire-comment-list": [ok(page1), ok(page2)]})
        out = W.dispatch("comment-list", gh_cfg(),
                         locator=loc(GH_NODE, "#42"), execute=ex)
        self.assertNotIsInstance(out, TrackerError)
        self.assertEqual(len(out["comments"]), W._PAGE_SIZE + 1)
        self.assertFalse(out["truncated"])
        self.assertIn("page=2", cli_endpoint(ex.calls[-1]))

    def test_linear_comment_list_drains_the_connection(self) -> None:
        probe = gql_issue({"id": LN_UUID})
        page1 = ok({"data": {"issue": {"comments": {
            "nodes": [{"id": "c1", "body": "a", "url": None}],
            "pageInfo": {"hasNextPage": True, "endCursor": "cur1"}}}}})
        page2 = ok({"data": {"issue": {"comments": {
            "nodes": [{"id": "c2", "body": "b", "url": None}],
            "pageInfo": {"hasNextPage": False, "endCursor": None}}}}})
        ex = fake_execute({"wire-comment-list": [probe, page1, page2]})
        out = W.dispatch("comment-list", ln_cfg(),
                         locator=loc(LN_UUID, "WOR-17"), execute=ex)
        self.assertNotIsInstance(out, TrackerError)
        self.assertEqual([c["id"] for c in out["comments"]], ["c1", "c2"])
        self.assertFalse(out["truncated"])

    def test_jira_list_open_drains_start_at(self) -> None:
        batch1 = {"total": W._PAGE_SIZE + 1,
                  "issues": [dict(JR_ISSUE, id=str(i)) for i in range(W._PAGE_SIZE)]}
        batch2 = {"total": W._PAGE_SIZE + 1, "issues": [dict(JR_ISSUE, id="last")]}
        ex = fake_execute({"wire-list-open": [ok(batch1), ok(batch2)]})
        out = W.dispatch("list-open", jr_cfg(), execute=ex)
        self.assertNotIsInstance(out, TrackerError)
        self.assertEqual(len(out["issues"]), W._PAGE_SIZE + 1)
        self.assertFalse(out["truncated"])
        self.assertEqual([call.method for call in ex.calls], ["GET", "GET"])
        self.assertTrue(all("/rest/api/2/search?" in str(call.url_or_argv)
                            for call in ex.calls))
        starts = [
            parse_qs(urlparse(str(call.url_or_argv)).query)["startAt"][0]
            for call in ex.calls
        ]
        self.assertEqual(starts, ["0", str(W._PAGE_SIZE)])

    def test_cap_is_reported_never_silent(self) -> None:
        from unittest import mock
        full = [dict(GH_COMMENT, id=i) for i in range(W._PAGE_SIZE)]
        with mock.patch.object(W, "_MAX_PAGES", 2):
            ex = fake_execute({"wire-comment-list": [ok(full), ok(full)]})
            out = W.dispatch("comment-list", gh_cfg(),
                             locator=loc(GH_NODE, "#42"), execute=ex)
        self.assertNotIsInstance(out, TrackerError)
        self.assertTrue(out["truncated"], "hitting the ceiling must be VISIBLE")


class NoAssertsInProductionPaths(unittest.TestCase):
    def test_wire_module_contains_no_assert_statements(self) -> None:
        import ast
        wire_dir = ROOT / "scripts" / "flowctl_tracker" / "wire"
        asserts = []
        for path in sorted(wire_dir.glob("*.py")):
            asserts.extend(
                n for n in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
                if isinstance(n, ast.Assert))
        self.assertEqual(asserts, [],
                         "asserts vanish under -O and raise across the never-raises boundary")


# ---------------------------------------------------------------------------
# Review follow-ups (fn-140.1): success honesty, comment parent bind, list aggregate
# ---------------------------------------------------------------------------


class LinearMutationSuccessRequired(unittest.TestCase):
    def test_comment_delete_success_false_is_mutation_failed(self) -> None:
        ex = fake_execute({
            "wire-parent-read": gql_issue(LN_ISSUE),
            "wire-comment-belong": ok({"data": {"comment": {
                "id": "c1", "issue": {"id": LN_UUID}}}}),
            "wire-comment-delete": ok({"data": {"commentDelete": {"success": False}}}),
        })
        out = W.dispatch("comment-delete", ln_cfg(),
                         locator=loc(LN_UUID, "WOR-17"), comment_id="c1", execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.TRANSPORT)
        self.assertEqual(out.subtype, "mutation_failed")
        self.assertNotIn("deleted", out.__dict__.get("details") or {})

    def test_comment_delete_null_payload_is_mutation_failed(self) -> None:
        ex = fake_execute({
            "wire-parent-read": gql_issue(LN_ISSUE),
            "wire-comment-belong": ok({"data": {"comment": {
                "id": "c1", "issue": {"id": LN_UUID}}}}),
            "wire-comment-delete": ok({"data": {"commentDelete": None}}),
        })
        out = W.dispatch("comment-delete", ln_cfg(),
                         locator=loc(LN_UUID, "WOR-17"), comment_id="c1", execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertEqual(out.subtype, "mutation_failed")

    def test_update_success_false_with_issue_present_is_error(self) -> None:
        ex = fake_execute({
            "wire-parent-read": gql_issue(LN_ISSUE),
            "wire-update": ok({"data": {"issueUpdate": {
                "success": False, "issue": dict(LN_ISSUE, title="N")}}}),
        })
        out = W.dispatch("update", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                         title="N", execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.TRANSPORT)
        self.assertEqual(out.subtype, "mutation_failed")


class CommentParentBelongCheck(unittest.TestCase):
    """comment-update/delete must bind comment_id to the locator parent."""

    def test_github_comment_update_mismatch_skips_mutation(self) -> None:
        ex = fake_execute({
            "wire-parent-read": ok(GH_ISSUE),
            "wire-comment-belong": ok({
                "id": 99, "body": "x",
                "issue_url": "https://api.github.com/repos/o/r/issues/999"}),
        })
        out = W.dispatch("comment-update", gh_cfg(), locator=loc(GH_NODE, "#42"),
                         comment_id="99", body="x", execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual(out.subtype, "comment_parent_mismatch")
        self.assertEqual([c.op for c in ex.calls],
                         ["wire-parent-read", "wire-comment-belong"])

    def test_github_comment_delete_mismatch_skips_mutation(self) -> None:
        ex = fake_execute({
            "wire-parent-read": ok(GH_ISSUE),
            "wire-comment-belong": ok({
                "id": 99, "body": "x",
                "issue_url": "https://api.github.com/repos/o/r/issues/7"}),
        })
        out = W.dispatch("comment-delete", gh_cfg(), locator=loc(GH_NODE, "#42"),
                         comment_id="99", execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertEqual(out.subtype, "comment_parent_mismatch")
        self.assertNotIn("wire-comment-delete", [c.op for c in ex.calls])

    def test_linear_comment_update_mismatch_skips_mutation(self) -> None:
        ex = fake_execute({
            "wire-parent-read": gql_issue(LN_ISSUE),
            "wire-comment-belong": ok({"data": {"comment": {
                "id": "c-other", "issue": {"id": "other-uuid"}}}}),
        })
        out = W.dispatch("comment-update", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                         comment_id="c-other", body="x", execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual(out.subtype, "comment_parent_mismatch")
        self.assertNotIn("wire-comment-update", [c.op for c in ex.calls])

    def test_linear_comment_delete_mismatch_skips_mutation(self) -> None:
        ex = fake_execute({
            "wire-parent-read": gql_issue(LN_ISSUE),
            "wire-comment-belong": ok({"data": {"comment": {
                "id": "c-other", "issue": {"id": "other-uuid"}}}}),
        })
        out = W.dispatch("comment-delete", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                         comment_id="c-other", execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertEqual(out.subtype, "comment_parent_mismatch")
        self.assertEqual([c.op for c in ex.calls],
                         ["wire-parent-read", "wire-comment-belong"])


class GitlabCommentListAggregateHonesty(unittest.TestCase):
    def test_empty_list_is_not_available(self) -> None:
        ex = fake_execute({"wire-comment-list": ok([])})
        out = W.dispatch("comment-list", gl_cfg(),
                         locator=loc(str(GL_ID), "g/p#12"), execute=ex)
        self.assertEqual(out["comments"], [])
        self.assertEqual(out["parent_identity"], "not_available")

    def test_note_without_noteable_id_is_not_available(self) -> None:
        ex = fake_execute({"wire-comment-list": ok([
            {"id": 1, "body": "a", "system": False},  # no noteable_id
        ])})
        out = W.dispatch("comment-list", gl_cfg(),
                         locator=loc(str(GL_ID), "g/p#12"), execute=ex)
        self.assertEqual(len(out["comments"]), 1)
        self.assertEqual(out["comments"][0]["parent_identity"], "not_available")
        self.assertEqual(out["parent_identity"], "not_available")


class JiraSyntheticResponsesAreHonest(unittest.TestCase):
    """Jira PUT verbs get a 204: the synthesized post-state carries NO
    response-side parent identity - saying validated there was a fake check
    (the pre-mutation gate is the real protection and already ran)."""

    def _run(self, verb: str, **kw):
        ex = fake_execute({"wire-parent-read": ok(JR_ISSUE),
                           f"wire-{verb}": empty()})
        out = W.dispatch(verb, jr_cfg(), locator=loc(JR_ID, "SCRUM-1"),
                         execute=ex, **kw)
        self.assertNotIsInstance(out, TrackerError)
        return out

    def test_update_label_assign_report_not_available(self) -> None:
        self.assertEqual(self._run("update", title="t")["parent_identity"],
                         "not_available")
        self.assertEqual(self._run("label", add=["x"])["parent_identity"],
                         "not_available")
        self.assertEqual(self._run("assign", add=["acct-123456789012345678901"])
                         ["parent_identity"], "not_available")

    def test_read_still_validates_on_its_response(self) -> None:
        ex = fake_execute({"wire-read": ok(JR_ISSUE)})
        out = W.dispatch("read", jr_cfg(), locator=loc(JR_ID, "SCRUM-1"), execute=ex)
        self.assertEqual(out["parent_identity"], "validated")


class GitlabCliJsonContentType(unittest.TestCase):
    """glab api sends NO Content-Type with --input (measured live 2026-07-28:
    GitLab replies 415 "provided content-type '' is not supported" on every
    JSON mutation). The argv builder must inject the header for glab bodies;
    gh api defaults to JSON already and needs nothing."""

    def _mutation_argvs(self, cfg, locator, responses):
        ex = fake_execute(responses)
        W.dispatch("update", cfg, locator=locator, title="t2", execute=ex)
        return [list(c.url_or_argv) for c in ex.calls if c.body is not None]

    def test_gitlab_body_requests_carry_json_content_type(self) -> None:
        argvs = self._mutation_argvs(
            gl_cfg(), loc(str(GL_ID), "g/p#12"),
            {"wire-parent-read": ok(GL_ISSUE), "wire-update": ok(GL_ISSUE)})
        self.assertTrue(argvs, "expected at least one body-carrying request")
        for argv in argvs:
            i = argv.index("-H")
            self.assertEqual(argv[i + 1], "Content-Type: application/json")
            self.assertEqual(argv[-2:], ["--input", "-"])

    def test_github_body_requests_stay_headerless(self) -> None:
        argvs = self._mutation_argvs(
            gh_cfg(), loc(GH_NODE, "#42"),
            {"wire-parent-read": ok(GH_ISSUE), "wire-update": ok(GH_ISSUE)})
        self.assertTrue(argvs, "expected at least one body-carrying request")
        for argv in argvs:
            self.assertNotIn("-H", argv)


class GitlabSelfHostedHostname(unittest.TestCase):
    """Measured live 2026-07-28 on a self-hosted EE instance at
    http://gitlab.localhost:8929: glab's --hostname wants its bare-hostname
    config key (a scheme-prefixed value is rejected 400), while the HTTP
    attach route needs the scheme-prefixed origin to derive its API base.
    perTracker.host stores the origin; the CLI argv builders normalize."""

    def test_scheme_prefixed_host_normalized_for_glab(self) -> None:
        from flowctl_tracker.types import gitlab_cli_hostname
        self.assertEqual(gitlab_cli_hostname("http://gitlab.localhost:8929"),
                         "gitlab.localhost")
        self.assertEqual(gitlab_cli_hostname("https://gl.corp/sub"), "gl.corp")
        self.assertEqual(gitlab_cli_hostname("gitlab.example.com"),
                         "gitlab.example.com")
        self.assertEqual(gitlab_cli_hostname("gitlab.localhost:8929"),
                         "gitlab.localhost")

    def test_wire_argv_carries_bare_hostname(self) -> None:
        cfg = gl_cfg()
        cfg["tracker"]["perTracker"]["host"] = "http://gitlab.localhost:8929"
        ex = fake_execute({"wire-read": ok(GL_ISSUE)})
        W.dispatch("read", cfg, locator=loc(str(GL_ID), "g/p#12"), execute=ex)
        argv = list(ex.calls[0].url_or_argv)
        i = argv.index("--hostname")
        self.assertEqual(argv[i + 1], "gitlab.localhost")


class DispatchEnvelopeBoundary(unittest.TestCase):
    """run() never leaks a traceback: an adapter exception on a malformed but
    syntactically-valid provider payload becomes the structured envelope."""

    def test_malformed_labels_shape_is_enveloped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            (flow / "config.json").write_text(json.dumps(gl_cfg()),
                                              encoding="utf-8")
            # gitlab issue with labels: 1 - list(1) raises TypeError inside
            # the adapter; run() must return the failure envelope, not raise.
            ex = fake_execute({"wire-read": ok(dict(GL_ISSUE, labels=1))})
            payload, code = W.run(
                flow, "read",
                locator=json.dumps(loc(str(GL_ID), "g/p#12")), execute=ex)
            data = json.loads(payload)
            self.assertFalse(data["success"])
            self.assertEqual(data["class"], "transport")
            self.assertEqual(data.get("subtype")
                             or (data.get("details") or {}).get("subtype"),
                             "malformed_body")
            self.assertNotEqual(code, 0)


class BacklogRelationAndQuestionWire(unittest.TestCase):
    _QUESTION = "<!-- flow-next:question id=a7f96309954a181b status=open -->"
    _ANSWER = "<!-- flow-next:answer id=a7f96309954a181b -->"

    def _flow_dir(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        flow = Path(tmp.name) / ".flow"
        flow.mkdir()
        return flow

    def _comment(self, provider: str, number: int, body: str,
                 created_at: str | None) -> dict:
        raw = {"id": str(number), "body": body}
        if provider == "github":
            raw.update({
                "created_at": created_at,
                "html_url": f"https://x/comments/{number}",
            })
        elif provider == "gitlab":
            raw.update({
                "created_at": created_at,
                "noteable_id": GL_ID,
                "system": False,
            })
        elif provider == "jira":
            raw["created"] = created_at
        else:
            raw.update({
                "createdAt": created_at,
                "url": f"https://linear.test/comments/{number}",
            })
        return raw

    def _question_case(self, provider: str, comments: list[dict]):
        added_body = "posted"
        if provider == "github":
            return (
                gh_cfg(),
                loc(GH_NODE, "#42"),
                {
                    "wire-comment-list": ok(comments),
                    "wire-question-parent-read": ok(GH_ISSUE),
                    "wire-parent-read": ok(GH_ISSUE),
                    "wire-comment-add": ok(self._comment(
                        provider, 99, added_body, "2026-07-29T12:00:00Z")),
                },
            )
        if provider == "gitlab":
            return (
                gl_cfg(),
                loc(str(GL_ID), "g/p#12"),
                {
                    "wire-comment-list": ok(comments),
                    "wire-parent-read": ok(GL_ISSUE),
                    "wire-comment-add": ok(self._comment(
                        provider, 99, added_body, "2026-07-29T12:00:00Z")),
                },
            )
        if provider == "jira":
            return (
                jr_cfg(),
                loc(JR_ID, "SCRUM-1"),
                {
                    "wire-comment-list": ok({
                        "comments": comments,
                        "total": len(comments),
                    }),
                    "wire-parent-read": ok(JR_ISSUE),
                    "wire-comment-add": ok(self._comment(
                        provider, 99, added_body, "2026-07-29T12:00:00Z")),
                },
            )
        return (
            ln_cfg(),
            loc(LN_UUID, "WOR-17"),
            {
                "wire-comment-list": ok({"data": {"issue": {
                    "id": LN_UUID,
                    "comments": {
                        "nodes": comments,
                        "pageInfo": {
                            "hasNextPage": False,
                            "endCursor": None,
                        },
                    },
                }}}),
                "wire-parent-read": gql_issue(LN_ISSUE),
                "wire-comment-add": ok({"data": {"commentCreate": {
                    "success": True,
                    "comment": {
                        **self._comment(
                            provider, 99, added_body,
                            "2026-07-29T12:00:00Z"),
                        "issue": {"id": LN_UUID},
                    },
                }}}),
            },
        )

    def _ask(self, provider: str, comments: list[dict]):
        cfg, locator, responses = self._question_case(provider, comments)
        ex = fake_execute(responses)
        out = W.dispatch(
            "question", cfg, locator=locator,
            subject_id="subject-1", blocked_stage="triage",
            reason_code="needs-spec", question_slug="capture-or-interview",
            body="What next?", flow_dir=self._flow_dir(), execute=ex,
        )
        return out, ex

    def test_question_rounds_follow_chronology_all_four(self) -> None:
        rounds = [
            ([(self._QUESTION, "2026-07-29T08:00:00Z")], False),
            ([
                (self._QUESTION, "2026-07-29T08:00:00Z"),
                (self._ANSWER, "2026-07-29T09:00:00Z"),
            ], True),
            ([
                (self._QUESTION, "2026-07-29T08:00:00Z"),
                (self._ANSWER, "2026-07-29T09:00:00Z"),
                (self._QUESTION, "2026-07-29T10:00:00Z"),
            ], False),
            ([
                (self._QUESTION, "2026-07-29T08:00:00Z"),
                (self._ANSWER, "2026-07-29T09:00:00Z"),
                (self._QUESTION, "2026-07-29T10:00:00Z"),
                (self._ANSWER, "2026-07-29T11:00:00Z"),
            ], True),
        ]
        for provider in ("github", "gitlab", "jira", "linear"):
            for markers, expected_posted in rounds:
                with self.subTest(
                    provider=provider, rounds=len(markers),
                    posted=expected_posted,
                ):
                    comments = [
                        self._comment(provider, index, body, created_at)
                        for index, (body, created_at) in enumerate(markers, 1)
                    ]
                    out, ex = self._ask(provider, comments)
                    self.assertNotIsInstance(out, TrackerError, out)
                    self.assertEqual(out["posted"], expected_posted)
                    self.assertEqual(
                        any(call.op == "wire-comment-add" for call in ex.calls),
                        expected_posted,
                    )
                    if expected_posted:
                        self.assertTrue(out["reopened"])

    def test_question_chronology_ignores_list_order_duplicates_and_other_ids(
            self) -> None:
        comments = [
            self._comment(
                "github", 4, self._ANSWER, "2026-07-29T11:00:00Z"),
            self._comment(
                "github", 1, self._QUESTION, "2026-07-29T08:00:00Z"),
            self._comment(
                "github", 3,
                "<!-- flow-next:answer id=other -->",
                "2026-07-29T12:00:00Z"),
            self._comment(
                "github", 2, self._ANSWER, "2026-07-29T09:00:00Z"),
        ]
        out, ex = self._ask("github", comments)
        self.assertNotIsInstance(out, TrackerError, out)
        self.assertTrue(out["posted"])
        self.assertTrue(out["reopened"])
        self.assertEqual(
            [call.op for call in ex.calls].count("wire-comment-add"),
            1,
        )

    def test_question_mixed_markers_fail_closed_without_clear_chronology(
            self) -> None:
        for provider in ("github", "gitlab", "jira", "linear"):
            cases = [
                [
                    self._comment(
                        provider, 1, self._QUESTION,
                        "2026-07-29T08:00:00Z"),
                    self._comment(provider, 2, self._ANSWER, None),
                ],
                [
                    self._comment(
                        provider, 1, self._QUESTION,
                        "2026-07-29T08:00:00Z"),
                    self._comment(
                        provider, 2, self._ANSWER,
                        "2026-07-29T08:00:00Z"),
                ],
            ]
            for comments in cases:
                with self.subTest(provider=provider, comments=comments):
                    out, ex = self._ask(provider, comments)
                    self.assertIsInstance(out, TrackerError)
                    self.assertIs(out.cls, ErrorClass.TRANSPORT)
                    self.assertEqual(out.subtype, "malformed_body")
                    self.assertFalse(
                        any(call.op == "wire-comment-add" for call in ex.calls),
                    )

    def test_relation_list_normalizes_direction_all_four(self) -> None:
        jira_config = jr_cfg()
        jira_config["tracker"]["perTracker"]["blocksLinkType"] = "Blocks"
        cases = [
            (
                "github",
                gh_cfg(),
                loc(GH_NODE, "#42"),
                {
                    "wire-relation-parent-read": ok(GH_ISSUE),
                },
                set(),
            ),
            (
                "gitlab",
                gl_cfg(),
                loc(str(GL_ID), "g/p#12"),
                {
                    "wire-relation-parent-read": ok(dict(
                        GL_ISSUE,
                        description=(
                            "<!-- flow:deps -->\n"
                            "**Blocked by:** g/p#9\n"
                            "<!-- /flow:deps -->"
                        ),
                    )),
                    "relate-list": ok([
                        {"iid": 9, "link_type": "is_blocked_by",
                         "references": {"full": "g/p#9"}},
                        {"iid": 13, "link_type": "blocks",
                         "references": {"full": "g/p#13"}},
                    ]),
                },
                {("g/p#12", "g/p#9"), ("g/p#13", "g/p#12")},
            ),
            (
                "linear",
                ln_cfg(),
                loc(LN_UUID, "WOR-17"),
                {
                    "wire-relation-list": ok({"data": {"issue": {
                        "id": LN_UUID,
                        "identifier": "WOR-17",
                        "relations": {
                            "nodes": [{"type": "blocks", "relatedIssue": {
                                "id": "dep-18", "identifier": "WOR-18"}}],
                            "pageInfo": {
                                "hasNextPage": False, "endCursor": None},
                        },
                        "inverseRelations": {
                            "nodes": [{"type": "blocks", "issue": {
                                "id": "dep-16", "identifier": "WOR-16"}}],
                            "pageInfo": {
                                "hasNextPage": False, "endCursor": None},
                        },
                    }}}),
                },
                {("WOR-18", "WOR-17"), ("WOR-17", "WOR-16")},
            ),
            (
                "jira",
                jira_config,
                loc(JR_ID, "SCRUM-1"),
                {
                    "wire-relation-list": ok({
                        "id": JR_ID,
                        "key": "SCRUM-1",
                        "fields": {"issuelinks": [
                            {
                                "type": {"name": "Blocks"},
                                "inwardIssue": {"id": "10041", "key": "SCRUM-2"},
                            },
                            {
                                "type": {"name": "Blocks"},
                                "outwardIssue": {"id": "10043", "key": "SCRUM-3"},
                            },
                        ]},
                    }),
                },
                {("SCRUM-1", "SCRUM-2"), ("SCRUM-3", "SCRUM-1")},
            ),
        ]
        for provider, cfg, locator, responses, expected in cases:
            with self.subTest(provider=provider):
                ex = fake_execute(responses)
                out = W.dispatch(
                    "relation-list", cfg, locator=locator,
                    execute=ex)
                self.assertNotIsInstance(out, TrackerError)
                pairs = {(row["from"], row["to"]) for row in out["relations"]}
                self.assertEqual(pairs, expected)
                self.assertTrue(all(
                    row["type"] == "blocks" and row["linkPresent"]
                    for row in out["relations"]))
                if provider == "gitlab":
                    native = next(
                        row for row in out["relations"]
                        if row["from"] == "g/p#12"
                        and row["to"] == "g/p#9"
                    )
                    self.assertEqual(native["source"], "unknown")
                    self.assertNotIn("degraded", native)
                if provider == "github":
                    self.assertEqual(
                        [call.op for call in ex.calls],
                        ["wire-relation-parent-read"],
                    )

    def test_gitlab_relation_list_keeps_relates_to_body_fallback_degraded(
            self) -> None:
        out = W.dispatch(
            "relation-list",
            gl_cfg(),
            locator=loc(str(GL_ID), "g/p#12"),
            execute=fake_execute({
                "wire-relation-parent-read": ok(dict(
                    GL_ISSUE,
                    description=(
                        "<!-- flow:deps -->\n"
                        "**Blocked by:** g/p#9\n"
                        "<!-- /flow:deps -->"
                    ),
                )),
                "relate-list": ok([
                    {"iid": 9, "link_type": "relates_to",
                     "references": {"full": "g/p#9"}},
                ]),
            }),
        )
        self.assertNotIsInstance(out, TrackerError, out)
        self.assertEqual(len(out["relations"]), 1)
        fallback = out["relations"][0]
        self.assertEqual(
            (fallback["from"], fallback["to"]), ("g/p#12", "g/p#9"))
        self.assertTrue(fallback["linkPresent"])
        self.assertEqual(fallback["source"], "flow")
        self.assertEqual(fallback["degraded"]["kind"], "relates_to")

    def test_relation_list_fails_closed_when_pages_are_truncated(self) -> None:
        full_gitlab_page = [
            {"iid": i + 1000, "link_type": "blocks",
             "references": {"full": f"g/p#{i + 1000}"}}
            for i in range(W._PAGE_SIZE)
        ]
        linear_pages = []
        for page in range(W._MAX_PAGES):
            linear_pages.append(ok({"data": {"issue": {
                "id": LN_UUID,
                "identifier": "WOR-17",
                "relations": {
                    "nodes": [],
                    "pageInfo": {
                        "hasNextPage": True,
                        "endCursor": f"rel-{page}",
                    },
                },
                "inverseRelations": {
                    "nodes": [],
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": None,
                    },
                },
            }}}))
        cases = [
            (
                "gitlab",
                gl_cfg(),
                loc(str(GL_ID), "g/p#12"),
                {
                    "wire-relation-parent-read": ok(GL_ISSUE),
                    "relate-list": [
                        ok(full_gitlab_page) for _ in range(W._MAX_PAGES)
                    ],
                },
            ),
            (
                "linear",
                ln_cfg(),
                loc(LN_UUID, "WOR-17"),
                {"wire-relation-list": linear_pages},
            ),
        ]
        for provider, cfg, locator, responses in cases:
            with self.subTest(provider=provider):
                out = W.dispatch(
                    "relation-list", cfg, locator=locator,
                    execute=fake_execute(responses))
                self.assertIsInstance(out, TrackerError)
                self.assertEqual(out.cls, ErrorClass.TRANSPORT)
                self.assertEqual(out.subtype, "truncated")

    def test_question_dedups_before_posting(self) -> None:
        marker = "<!-- flow-next:question id=a7f96309954a181b status=open -->"
        ex = fake_execute({
            "wire-comment-list": ok([{"id": 1, "body": f"{marker}\n\nOld"}]),
            "wire-question-parent-read": ok(GH_ISSUE),
        })
        out = W.dispatch(
            "question", gh_cfg(), locator=loc(GH_NODE, "#42"),
            subject_id="subject-1", blocked_stage="triage",
            reason_code="needs-spec", question_slug="capture-or-interview",
            body="Rephrased", flow_dir=self._flow_dir(), execute=ex)
        self.assertEqual(out["posted"], False)
        self.assertEqual(
            [call.op for call in ex.calls],
            ["wire-comment-list", "wire-question-parent-read"],
        )

    def test_question_concurrent_same_key_single_add_loser_conflicts(self) -> None:
        flow = self._flow_dir()
        inner: dict = {}
        posted = []

        def racing_list(_request):
            claim_files = list((flow / "create-first").glob("question-*.json"))
            self.assertEqual(len(claim_files), 1)
            self.assertEqual(
                json.loads(claim_files[0].read_text(encoding="utf-8"))["status"],
                "pending",
            )
            inner_ex = fake_execute({})
            inner["ex"] = inner_ex
            inner["out"] = W.dispatch(
                "question", gh_cfg(), locator=loc(GH_NODE, "#42"),
                subject_id="subject-1", blocked_stage="triage",
                reason_code="needs-spec",
                question_slug="capture-or-interview",
                body="What next?", flow_dir=flow, execute=inner_ex,
            )
            return ok([])

        def capture_add(request):
            posted.append(json.loads(request.body)["body"])
            return ok({"id": 2, "body": posted[-1]})

        ex = fake_execute({
            "wire-comment-list": racing_list,
            "wire-parent-read": ok(GH_ISSUE),
            "wire-comment-add": capture_add,
        })
        out = W.dispatch(
            "question", gh_cfg(), locator=loc(GH_NODE, "#42"),
            subject_id="subject-1", blocked_stage="triage",
            reason_code="needs-spec", question_slug="capture-or-interview",
            body="What next?", flow_dir=flow, execute=ex,
        )
        self.assertNotIsInstance(out, TrackerError, out)
        self.assertTrue(out["posted"])
        self.assertEqual(len(posted), 1)
        raced = inner["out"]
        self.assertIsInstance(raced, TrackerError)
        self.assertIs(raced.cls, ErrorClass.CONFLICT)
        self.assertEqual(raced.subtype, "question_in_flight")
        self.assertTrue(raced.auto_retryable)
        self.assertEqual(inner["ex"].calls, [])
        self.assertEqual(
            list((flow / "create-first").glob("question-*.json")), [])

    def test_question_dedup_rejects_stale_display_addressed_parents(self) -> None:
        marker = "<!-- flow-next:question id=a7f96309954a181b status=open -->"
        cases = [
            (
                "github",
                gh_cfg(),
                loc(GH_NODE, "#42"),
                {
                    "wire-comment-list": ok([
                        {"id": 1, "body": f"{marker}\n\nUnrelated"},
                    ]),
                    "wire-question-parent-read": ok(
                        dict(GH_ISSUE, node_id="OTHER_NODE")
                    ),
                },
            ),
            (
                "gitlab",
                gl_cfg(),
                loc(str(GL_ID), "g/p#12"),
                {
                    "wire-comment-list": ok([
                        {
                            "id": 1,
                            "body": f"{marker}\n\nUnrelated",
                            "system": False,
                        },
                    ]),
                    "wire-question-parent-read": ok(
                        dict(GL_ISSUE, id=GL_ID + 1)
                    ),
                },
            ),
        ]
        for provider, cfg, locator, responses in cases:
            with self.subTest(provider=provider):
                ex = fake_execute(responses)
                out = W.dispatch(
                    "question", cfg, locator=locator,
                    subject_id="subject-1", blocked_stage="triage",
                    reason_code="needs-spec",
                    question_slug="capture-or-interview",
                    body="Rephrased", flow_dir=self._flow_dir(), execute=ex)
                self.assertIsInstance(out, TrackerError)
                self.assertEqual(out.cls, ErrorClass.CONFLICT)
                self.assertEqual(
                    [call.op for call in ex.calls],
                    ["wire-comment-list", "wire-question-parent-read"],
                )

    def test_question_posts_canonical_marker_and_refuses_unproven_absence(self) -> None:
        ex = fake_execute({
            "wire-comment-list": ok([]),
            "wire-parent-read": ok(GH_ISSUE),
            "wire-comment-add": ok({"id": 2, "body": "posted"}),
        })
        out = W.dispatch(
            "question", gh_cfg(), locator=loc(GH_NODE, "#42"),
            subject_id="subject-1", blocked_stage="triage",
            reason_code="needs-spec", question_slug="capture-or-interview",
            body="What next?", flow_dir=self._flow_dir(), execute=ex)
        self.assertEqual(out["posted"], True)
        posted = next(call for call in ex.calls if call.op == "wire-comment-add")
        payload = json.loads(posted.body)
        self.assertEqual(
            payload["body"],
            "<!-- flow-next:question id=a7f96309954a181b status=open -->"
            "\n\nWhat next?",
        )

        full_page = [{"id": i, "body": "other"} for i in range(100)]
        truncated = fake_execute({
            "wire-comment-list": [ok(full_page) for _ in range(W._MAX_PAGES)],
        })
        out = W.dispatch(
            "question", gh_cfg(), locator=loc(GH_NODE, "#42"),
            subject_id="subject-1", blocked_stage="triage",
            reason_code="needs-spec", question_slug="capture-or-interview",
            body="What next?", flow_dir=self._flow_dir(), execute=truncated)
        self.assertIsInstance(out, TrackerError)
        self.assertEqual(out.subtype, "truncated")
        self.assertEqual(
            [call.op for call in truncated.calls],
            ["wire-comment-list"] * W._MAX_PAGES,
        )
