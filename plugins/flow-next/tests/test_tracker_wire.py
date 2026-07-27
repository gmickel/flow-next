"""Wire verbs: locator addressing + pre-mutation durable check (fn-140.1).

Fake transport = the injected executor seam from fn-139.2. Every test drives
the real wire.py against recorded response shapes — no live API.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

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
                        "resolved": {"destination": {"owner": "o", "repo": "r"}}}}


def gl_cfg() -> dict:
    return {"tracker": {"type": "gitlab",
                        "perTracker": {"project": "g/p", "host": "gitlab.com"},
                        "resolved": {"destination": {
                            "projectId": 1, "projectPath": "g/p",
                            "host": "gitlab.com", "namespaceId": 9}}}}


def ln_cfg() -> dict:
    return {"tracker": {"type": "linear",
                        "perTracker": {"teamId": "team-1"},
                        "resolved": {"destination": {
                            "teamId": "team-1", "teamKey": "WOR",
                            "labelIds": {"bug": "lbl-1", "ready": "lbl-2"},
                            "stateIds": {}}}}}


def jr_cfg() -> dict:
    return {"tracker": {"type": "jira",
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
        src = (ROOT / "scripts" / "flowctl_tracker" / "wire.py").read_text()
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

    def test_linear_list_open(self) -> None:
        ex = fake_execute({"wire-list-open": ok({"data": {"issues": {
            "nodes": [LN_ISSUE]}}})})
        out = W.dispatch("list-open", ln_cfg(), execute=ex)
        self.assertEqual(out["issues"][0]["id"], LN_UUID)

    def test_jira_list_open(self) -> None:
        ex = fake_execute({"wire-list-open": ok({"issues": [JR_ISSUE]})})
        out = W.dispatch("list-open", jr_cfg(), execute=ex)
        self.assertEqual(out["issues"][0]["id"], JR_ID)


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
                self.assertEqual(out["parent_identity"], "validated")

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
              "wire-comment-update": ok({"id": 1, "body": "x"})}),
            ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"),
             {"wire-parent-read": ok(GL_ISSUE),
              "wire-comment-update": ok({"id": 1, "body": "x",
                                         "noteable_id": GL_ID})}),
            ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"),
             {"wire-parent-read": gql_issue(LN_ISSUE),
              "wire-comment-update": ok({"data": {"commentUpdate": {
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
             {"wire-parent-read": ok(GH_ISSUE), "wire-comment-delete": empty()}),
            ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"),
             {"wire-parent-read": ok(GL_ISSUE), "wire-comment-delete": empty()}),
            ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"),
             {"wire-parent-read": gql_issue(LN_ISSUE),
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
                  "issue": LN_ISSUE}}})}, ["ready"]),
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
                  "issue": LN_ISSUE}}})}, ["user-2"]),
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
        src = (ROOT / "scripts" / "flowctl_tracker" / "wire.py").read_text(encoding="utf-8")
        asserts = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Assert)]
        self.assertEqual(asserts, [],
                         "asserts vanish under -O and raise across the never-raises boundary")
