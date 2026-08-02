"""Cross-adapter conformance matrix + fault injection (fn-140.6 / R18).

Same verb x all four adapters with one assertion set; plus the six fault
points no single task owns. Fixture shapes mirror the per-task suites.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import classify as C  # noqa: E402
from flowctl_tracker import envelope as E  # noqa: E402
from flowctl_tracker import executor as X  # noqa: E402
from flowctl_tracker import lifecycle as L  # noqa: E402
from flowctl_tracker import relate as R  # noqa: E402
from flowctl_tracker import resolve_verb as RV  # noqa: E402
from flowctl_tracker import status as S  # noqa: E402
from flowctl_tracker import syncbody as SB  # noqa: E402
from flowctl_tracker import wire as W  # noqa: E402
from flowctl_tracker.types import (  # noqa: E402
    ErrorClass, MAX_RETRIES, Request, Response, TrackerError,
)


# ---------------------------------------------------------------------------
# Shared harness (copied from per-task suites)
# ---------------------------------------------------------------------------

def ok(body) -> Response:
    if isinstance(body, (bytes, bytearray)):
        return Response(200, {}, bytes(body), 0.01)
    return Response(200, {}, json.dumps(body).encode() if body is not None else b"", 0.01)


def empty() -> Response:
    return Response(204, {}, b"", 0.01)


def fake_execute(responses: dict):
    calls = []

    def execute(request):
        calls.append(request)
        if request.op == "lifecycle-create-meta" and request.op not in responses:
            return ok({})
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
    argv = list(request.url_or_argv)
    if len(argv) >= 2 and argv[-2:] == ["--input", "-"]:
        argv = argv[:-2]
    if len(argv) >= 2 and argv[-2] == "-H":
        argv = argv[:-2]
    return argv[-1]


def gql_issue(issue) -> Response:
    return ok({"data": {"issue": issue}})


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

DC_KEY = "MY_LONG_PROJECT_KEY-7"
DC_PROJECT = "MY_LONG_PROJECT_KEY"
DC_ID = "20042"
DC_ISSUE = {"id": DC_ID, "key": DC_KEY,
            "fields": {"summary": "T", "description": "B",
                       "labels": [], "status": {"id": "1", "name": "To Do"},
                       "assignee": None}}

FLOW_BODY = "## Goal\nShip it.\n"
ATTACH_BYTES = b"hello-attach-conformance"


def gitlab_body_echo(request) -> Response:
    description = json.loads(request.body.decode())["description"]
    return ok({**GL_ISSUE, "description": description})


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
                            "host": "gitlab.com", "namespaceId": 9},
                            "capabilities": {
                                "attachments": True, "blockedBy": False,
                                "subIssues": False, "deleteIssue": True}}}}


def ln_cfg() -> dict:
    return {"tracker": {"type": "linear",
                        "readyState": "Ready",
                        "perTracker": {"teamId": "team-1"},
                        "resolved": {"destination": {
                            "teamId": "team-1", "teamKey": "WOR",
                            "labelIds": {"bug": "lbl-1", "ready": "lbl-2"},
                            "stateIds": {}},
                            "capabilities": {
                                "attachments": True, "blockedBy": True,
                                "subIssues": False, "deleteIssue": True}}}}


def jr_cfg(*, project_key: str = "SCRUM", status_ids=None) -> dict:
    return {"tracker": {"type": "jira",
                        "readyState": "Ready for Work",
                        "perTracker": {"baseUrl": "https://ex.atlassian.net",
                                       "projectKey": project_key,
                                       "blocksLinkType": "Blocks"},
                        "resolved": {"destination": {
                            "baseUrl": "https://ex.atlassian.net",
                            "projectKey": project_key, "projectId": "10000",
                            "issueTypeId": "10001", "apiVersion": 2,
                            "style": "classic",
                            "statusIds": status_ids if status_ids is not None else {
                                "todo": "1", "in_progress": "2",
                                "in_review": "3", "done": "4",
                            }},
                            "capabilities": {
                                "attachments": True, "blockedBy": True,
                                "subIssues": False, "deleteIssue": True}}}}


def _write_config(flow: Path, config: dict) -> None:
    flow.mkdir(parents=True, exist_ok=True)
    (flow / "config.json").write_text(json.dumps(config), encoding="utf-8")


def _write_flow(flow: Path, config: dict, *, spec_id: str = "fn-1-demo",
                tracker: dict | None = None) -> Path:
    (flow / "specs").mkdir(parents=True, exist_ok=True)
    (flow / "config.json").write_text(json.dumps(config), encoding="utf-8")
    base = {
        "id": GH_NODE, "identifier": "#42", "url": "https://x/42",
        "lastSyncedAt": None, "depRelations": [], "linkState": "linked",
        "baseHashFlow": None, "baseHashTracker": None,
        "mergeBaseFlow": None, "mergeBaseTracker": None,
    }
    if tracker:
        base.update(tracker)
    path = flow / "specs" / f"{spec_id}.json"
    path.write_text(json.dumps({
        "id": spec_id, "title": "Demo", "status": "open",
        "branch_name": spec_id, "tracker": base,
    }, indent=2) + "\n", encoding="utf-8")
    return path


def _saved(flow: Path, spec_id: str = "fn-1-demo") -> dict:
    return json.loads((flow / "specs" / f"{spec_id}.json").read_text(encoding="utf-8"))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _gh_issue(body: str) -> dict:
    return dict(GH_ISSUE, body=body)


def _gl_issue(body: str) -> dict:
    return dict(GL_ISSUE, description=body)


def _ln_issue(body: str) -> dict:
    return dict(LN_ISSUE, description=body)


def _jr_issue(body: str) -> dict:
    return {"id": JR_ID, "key": "SCRUM-1",
            "fields": {"summary": "T", "description": body, "labels": []}}


PROVIDERS = [
    ("github", gh_cfg, GH_NODE, "#42",
     lambda body: ok(_gh_issue(body)), _gh_issue),
    ("gitlab", gl_cfg, str(GL_ID), "g/p#12",
     lambda body: ok(_gl_issue(body)), _gl_issue),
    ("linear", ln_cfg, LN_UUID, "WOR-17",
     lambda body: gql_issue(_ln_issue(body)), _ln_issue),
    ("jira", jr_cfg, JR_ID, "SCRUM-1",
     lambda body: ok(_jr_issue(body)), _jr_issue),
]


WIRE_VERBS = (
    "read", "update", "comment-add", "comment-list", "comment-update",
    "comment-delete", "label", "assign", "list-open", "relation-list",
    "question", "attach", "attach-get",
)


# ---------------------------------------------------------------------------
# Conformance matrix
# ---------------------------------------------------------------------------

class ConformanceMatrix(unittest.TestCase):
    """Every WIRE verb x all four adapters; same assertion set per verb."""

    def _assert_no_local_state(self, flow: Path, before_cfg: str) -> None:
        after = (flow / "config.json").read_text(encoding="utf-8")
        self.assertEqual(after, before_cfg, "wire verbs must not write config")
        runs = flow / "sync-runs"
        self.assertFalse(runs.is_dir() and any(runs.iterdir()),
                         "wire verbs must write no receipt")

    def _matrix_case(self, provider, cfg, locator, responses, *,
                     verb, kwargs, expect_durable=None,
                     expect_capability=False):
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, cfg)
            before = (flow / "config.json").read_text(encoding="utf-8")
            ex = fake_execute(responses)
            payload, code = W.run(
                flow, verb, locator=json.dumps(locator) if locator else None,
                execute=ex, **kwargs)
            data = json.loads(payload)
            if expect_capability:
                self.assertFalse(data["success"])
                self.assertEqual(data["class"], ErrorClass.CAPABILITY.value)
                self.assertEqual(code, 9)  # CAPABILITY exit
                self.assertEqual(ex.calls, [])
            else:
                self.assertTrue(data["success"], f"{provider}/{verb}: {data}")
                self.assertEqual(code, 0)
                if expect_durable is not None:
                    body = data["data"]
                    got = body.get("id")
                    if got is None and isinstance(body.get("issues"), list):
                        got = body["issues"][0]["id"] if body["issues"] else None
                    if got is None and isinstance(body.get("comments"), list):
                        # comment verbs: durable checked pre-mutation; response
                        # may not carry parent id
                        pass
                    elif "deleted" in body or "sha256" in body:
                        pass
                    elif expect_durable and got is not None:
                        self.assertEqual(str(got), str(expect_durable))
            self._assert_no_local_state(flow, before)

    def test_read_all_four(self) -> None:
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
        for provider, cfg, locator, responses, durable in cases:
            with self.subTest(provider=provider):
                self._matrix_case(provider, cfg, locator, responses,
                                  verb="read", kwargs={},
                                  expect_durable=durable)

    def test_update_all_four(self) -> None:
        cases = [
            ("github", gh_cfg(), loc(GH_NODE, "#42"),
             {"wire-parent-read": ok(GH_ISSUE),
              "wire-update": ok(dict(GH_ISSUE, title="X"))}, GH_NODE),
            ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"),
             {"wire-parent-read": ok(GL_ISSUE),
              "wire-update": ok(dict(GL_ISSUE, title="X"))}, str(GL_ID)),
            ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"),
             {"wire-parent-read": gql_issue(LN_ISSUE),
              "wire-update": ok({"data": {"issueUpdate": {
                  "success": True, "issue": dict(LN_ISSUE, title="X")}}})},
             LN_UUID),
            ("jira", jr_cfg(), loc(JR_ID, "SCRUM-1"),
             {"wire-parent-read": ok(JR_ISSUE), "wire-update": empty()}, JR_ID),
        ]
        for provider, cfg, locator, responses, durable in cases:
            with self.subTest(provider=provider):
                self._matrix_case(provider, cfg, locator, responses,
                                  verb="update",
                                  kwargs={"title": "X"},
                                  expect_durable=durable)

    def test_comment_add_all_four(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "c.md"
            body.write_text("hi", encoding="utf-8")
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
                    self._matrix_case(
                        provider, cfg, locator, responses,
                        verb="comment-add",
                        kwargs={"body_file": str(body)})

    def test_comment_list_all_four(self) -> None:
        cases = [
            ("github", gh_cfg(), loc(GH_NODE, "#42"),
             {"wire-comment-list": ok([{"id": 1, "body": "a"}])}),
            ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"),
             {"wire-comment-list": ok([
                 {"id": 1, "body": "a", "noteable_id": GL_ID, "system": False},
                 {"id": 2, "body": "sys", "noteable_id": GL_ID, "system": True},
             ])}),
            ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"),
             {"wire-comment-list": ok({"data": {"issue": {
                 "id": LN_UUID,
                 "comments": {"nodes": [{"id": "c", "body": "a"}]}}}})}),
            ("jira", jr_cfg(), loc(JR_ID, "SCRUM-1"),
             {"wire-comment-list": ok({"comments": [{"id": "c", "body": "a"}]})}),
        ]
        for provider, cfg, locator, responses in cases:
            with self.subTest(provider=provider):
                self._matrix_case(provider, cfg, locator, responses,
                                  verb="comment-list", kwargs={})

    def test_comment_update_all_four(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "c.md"
            body.write_text("x", encoding="utf-8")
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
                    self._matrix_case(
                        provider, cfg, locator, responses,
                        verb="comment-update",
                        kwargs={"comment_id": "1", "body_file": str(body)})

    def test_comment_delete_all_four(self) -> None:
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
                self._matrix_case(provider, cfg, locator, responses,
                                  verb="comment-delete",
                                  kwargs={"comment_id": "1"})

    def test_label_all_four(self) -> None:
        cases = [
            ("github", gh_cfg(), loc(GH_NODE, "#42"),
             {"wire-parent-read": ok(GH_ISSUE),
              "wire-label": ok([{"name": "bug"}]),
              "wire-label-readback": ok(GH_ISSUE)}),
            ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"),
             {"wire-parent-read": ok(GL_ISSUE),
              "wire-label": ok(dict(GL_ISSUE, labels=["bug", "ready"]))}),
            ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"),
             {"wire-parent-read": gql_issue(LN_ISSUE),
              "wire-label": ok({"data": {"issueUpdate": {
                  "success": True, "issue": LN_ISSUE}}})}),
            ("jira", jr_cfg(), loc(JR_ID, "SCRUM-1"),
             {"wire-parent-read": ok(JR_ISSUE), "wire-label": empty()}),
        ]
        for provider, cfg, locator, responses in cases:
            with self.subTest(provider=provider):
                self._matrix_case(provider, cfg, locator, responses,
                                  verb="label", kwargs={"add": ["ready"]})

    def test_assign_all_four(self) -> None:
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
                self._matrix_case(provider, cfg, locator, responses,
                                  verb="assign", kwargs={"add": add})

    def test_list_open_all_four(self) -> None:
        cases = [
            ("github", gh_cfg(),
             {"wire-list-open": ok([GH_ISSUE])}, GH_NODE),
            ("gitlab", gl_cfg(),
             {"wire-list-open": ok([GL_ISSUE])}, str(GL_ID)),
            ("linear", ln_cfg(),
             {"wire-list-open": ok({"data": {"issues": {
                 "nodes": [LN_ISSUE]}}})}, LN_UUID),
            ("jira", jr_cfg(),
             {"wire-list-open": ok({"issues": [JR_ISSUE]})}, JR_ID),
        ]
        for provider, cfg, responses, durable in cases:
            with self.subTest(provider=provider):
                self._matrix_case(provider, cfg, None, responses,
                                  verb="list-open", kwargs={},
                                  expect_durable=durable)

    def test_list_open_exact_ready_lane_all_four(self) -> None:
        cases = [
            ("github", gh_cfg(), ok([GH_ISSUE])),
            ("gitlab", gl_cfg(), ok([GL_ISSUE])),
            ("linear", ln_cfg(), ok({"data": {"issues": {
                "nodes": [LN_ISSUE]}}})),
            ("jira", jr_cfg(), ok({"issues": [JR_ISSUE]})),
        ]
        for provider, cfg, response in cases:
            with self.subTest(provider=provider):
                ex = fake_execute({"wire-list-open": response})
                out = W.dispatch("list-open", cfg, execute=ex)
                self.assertNotIsInstance(out, TrackerError)
                request = ex.calls[0]
                if provider in ("github", "gitlab"):
                    params = parse_qs(urlparse(cli_endpoint(request)).query)
                    self.assertEqual(params["labels"], ["Ready"])
                elif provider == "linear":
                    variables = json.loads(request.body)["variables"]
                    self.assertEqual(
                        variables["filter"]["state"],
                        {"name": {"eqIgnoreCase": "Ready"}},
                    )
                else:
                    params = parse_qs(urlparse(str(request.url_or_argv)).query)
                    self.assertEqual(
                        params["jql"],
                        ['project = SCRUM AND status = "Ready for Work"'],
                    )

    def test_list_open_unset_ready_lane_is_noop_all_four(self) -> None:
        for provider, cfg in (
            ("github", gh_cfg()),
            ("gitlab", gl_cfg()),
            ("linear", ln_cfg()),
            ("jira", jr_cfg()),
        ):
            with self.subTest(provider=provider):
                cfg["tracker"]["readyState"] = " "
                ex = fake_execute({})
                out = W.dispatch("list-open", cfg, execute=ex)
                self.assertEqual(out, {"issues": [], "truncated": False})
                self.assertEqual(ex.calls, [])

    def test_relation_list_all_four(self) -> None:
        not_found = TrackerError(
            ErrorClass.NOT_FOUND, "no parent", subtype="http")
        jira_config = jr_cfg()
        jira_config["tracker"]["perTracker"]["blocksLinkType"] = "Blocks"
        cases = [
            ("github", gh_cfg(), loc(GH_NODE, "#42"), {
                "wire-relation-parent-read": ok(GH_ISSUE),
                "wire-relation-parent": not_found,
                "wire-relation-list": ok([]),
            }),
            ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"), {
                "wire-relation-parent-read": ok(GL_ISSUE),
                "relate-list": ok([]),
            }),
            ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"), {
                "wire-relation-list": ok({"data": {"issue": {
                    "id": LN_UUID,
                    "identifier": "WOR-17",
                    "relations": {"nodes": [], "pageInfo": {
                        "hasNextPage": False, "endCursor": None}},
                    "inverseRelations": {"nodes": [], "pageInfo": {
                        "hasNextPage": False, "endCursor": None}},
                }}}),
            }),
            ("jira", jira_config, loc(JR_ID, "SCRUM-1"), {
                "wire-relation-list": ok({
                    "id": JR_ID, "key": "SCRUM-1",
                    "fields": {"issuelinks": []},
                }),
            }),
        ]
        for provider, cfg, locator, responses in cases:
            with self.subTest(provider=provider):
                self._matrix_case(
                    provider, cfg, locator, responses,
                    verb="relation-list", kwargs={})

    def test_question_all_four(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "q.md"
            body.write_text("What should happen next?", encoding="utf-8")
            cases = [
                ("github", gh_cfg(), loc(GH_NODE, "#42"), {
                    "wire-comment-list": ok([]),
                    "wire-parent-read": ok(GH_ISSUE),
                    "wire-comment-add": ok({"id": 1, "body": "question"}),
                }),
                ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"), {
                    "wire-comment-list": ok([]),
                    "wire-parent-read": ok(GL_ISSUE),
                    "wire-comment-add": ok({
                        "id": 1, "body": "question", "noteable_id": GL_ID}),
                }),
                ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"), {
                    "wire-comment-list": ok({"data": {"issue": {
                        "id": LN_UUID, "comments": {"nodes": []}}}}),
                    "wire-parent-read": gql_issue(LN_ISSUE),
                    "wire-comment-add": ok({"data": {"commentCreate": {
                        "success": True,
                        "comment": {"id": "c", "body": "question",
                                    "issue": {"id": LN_UUID}},
                    }}}),
                }),
                ("jira", jr_cfg(), loc(JR_ID, "SCRUM-1"), {
                    "wire-comment-list": ok({"comments": []}),
                    "wire-parent-read": ok(JR_ISSUE),
                    "wire-comment-add": ok({"id": "c", "body": "question"}),
                }),
            ]
            for provider, cfg, locator, responses in cases:
                with self.subTest(provider=provider):
                    self._matrix_case(
                        provider, cfg, locator, responses,
                        verb="question",
                        kwargs={"body_file": str(body),
                                "subject_id": "subject-1",
                                "blocked_stage": "triage",
                                "reason_code": "needs-spec",
                                "question_slug": "capture-or-interview"})

    def test_attach_all_four_github_asserts_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "f.bin"
            src.write_bytes(ATTACH_BYTES)
            # GitHub: capability GATE, not a skip.
            self._matrix_case(
                "github", gh_cfg(), loc(GH_NODE, "#42"), {},
                verb="attach", kwargs={"file_path": str(src)},
                expect_capability=True)

            cases = [
                ("gitlab", gl_cfg(), loc(str(GL_ID), "g/p#12"),
                 {"wire-parent-read": ok(GL_ISSUE),
                  "upload": ok({"id": 9, "url": "/uploads/secret/f.bin",
                                "markdown": "![f](/uploads/secret/f.bin)"})}),
                ("linear", ln_cfg(), loc(LN_UUID, "WOR-17"),
                 {"wire-parent-read": gql_issue(LN_ISSUE),
                  "wire-attach-fileUpload": ok({"data": {"fileUpload": {
                      "success": True,
                      "uploadFile": {
                          "uploadUrl": "https://storage.example/presigned",
                          "assetUrl": "https://uploads.linear.app/asset",
                          "headers": [{"key": "Content-Type",
                                       "value": "application/octet-stream"}],
                      }}}}),
                  "wire-attach-presigned-put": ok(b""),
                  "wire-attach-create": ok({"data": {"attachmentCreate": {
                      "success": True,
                      "attachment": {"id": "att-1",
                                     "url": "https://uploads.linear.app/asset"
                                     }}}})}),
                ("jira", jr_cfg(), loc(JR_ID, "SCRUM-1"),
                 {"wire-parent-read": ok(JR_ISSUE),
                  "wire-attach": ok([{"id": "att-9",
                                      "content": "https://ex/att-9"}])}),
            ]
            for provider, cfg, locator, responses in cases:
                with self.subTest(provider=provider):
                    self._matrix_case(
                        provider, cfg, locator, responses,
                        verb="attach", kwargs={"file_path": str(src)})

    def test_attach_get_all_four_github_asserts_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.bin"
            self._matrix_case(
                "github", gh_cfg(), None, {},
                verb="attach-get",
                kwargs={"attachment_id": "1", "out_path": str(out)},
                expect_capability=True)

            cases = [
                ("gitlab", gl_cfg(),
                 {"wire-attach-get": ok(ATTACH_BYTES)}, "9"),
                ("linear", ln_cfg(),
                 {"wire-attach-get": ok(ATTACH_BYTES)},
                 "https://uploads.linear.app/asset/x"),
                ("jira", jr_cfg(),
                 {"wire-attach-get": ok(ATTACH_BYTES)}, "att-9"),
            ]
            for provider, cfg, responses, att_id in cases:
                with self.subTest(provider=provider):
                    out_p = Path(tmp) / f"out-{provider}.bin"
                    self._matrix_case(
                        provider, cfg, None, responses,
                        verb="attach-get",
                        kwargs={"attachment_id": att_id,
                                "out_path": str(out_p)})

    def test_matrix_covers_every_wire_verb(self) -> None:
        self.assertEqual(tuple(WIRE_VERBS), W.WIRE_VERBS)


# ---------------------------------------------------------------------------
# Spec-aware verb matrix (create / create-first / persist-external / status /
# relate / sync-body) - same verb, all four adapters, same assertion set.
# ---------------------------------------------------------------------------

#: The full granular verb surface fn-140 defines (R18 completeness guard).
SPEC_VERBS = ("create", "create-first", "persist-external", "status",
              "relate", "sync-body")


def _receipts(flow: Path) -> list:
    runs = flow / "sync-runs"
    if not runs.is_dir():
        return []
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(runs.glob("sync-*.json"))]


def _unlinked() -> dict:
    return {"id": None, "identifier": None, "url": None,
            "lastSyncedAt": None, "depRelations": [], "linkState": "unlinked"}


CREATE_CASES = [
    ("github", gh_cfg, GH_NODE, "#42",
     ok({"id": 999, "node_id": GH_NODE, "number": 42,
         "html_url": "https://github.com/o/r/issues/42"})),
    ("gitlab", gl_cfg, str(GL_ID), "g/p#12",
     ok({"id": GL_ID, "iid": 12,
         "web_url": "https://gitlab.com/g/p/-/issues/12",
         "references": {"full": "g/p#12"}})),
    ("linear", ln_cfg, LN_UUID, "WOR-17",
     ok({"data": {"issueCreate": {
         "success": True,
         "issue": {"id": LN_UUID, "identifier": "WOR-17",
                   "url": "https://linear.app/x/issue/WOR-17"}}}})),
    ("jira", jr_cfg, JR_ID, "SCRUM-1",
     ok({"id": JR_ID, "key": "SCRUM-1",
         "self": "https://ex.atlassian.net/rest/api/2/issue/10042"})),
]


class SpecVerbCreateAllFour(unittest.TestCase):
    """create: links the spec atomically + ONE receipt, on all four."""

    def test_create_all_four(self) -> None:
        for provider, cfg_fn, durable, display, resp in CREATE_CASES:
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp) / ".flow"
                path = _write_flow(flow, cfg_fn(), tracker=_unlinked())
                parent_resp = next(
                    case[4] for case in PROVIDERS if case[0] == provider)
                ex = fake_execute({
                    "lifecycle-create": resp,
                    "sync-body-parent-read": parent_resp("B"),
                })
                out = L.create(flow, "fn-1-demo", title="T", body="B",
                               execute=ex)
                self.assertNotIsInstance(out, TrackerError,
                                         f"{provider}: {out}")
                self.assertEqual(out["id"], durable)
                self.assertEqual(out["identifier"], display)
                self.assertEqual(out["linkState"], "linked")
                saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
                self.assertEqual(saved["id"], durable)
                self.assertEqual(saved["identifier"], display)
                self.assertEqual(len(_receipts(flow)), 1)


class SpecVerbCreateFirstAllFour(unittest.TestCase):
    """create-first: recovery record lands; retry replays with NO second create."""

    def test_create_first_retry_all_four(self) -> None:
        for provider, cfg_fn, durable, _display, resp in CREATE_CASES:
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp) / ".flow"
                _write_config(flow, cfg_fn())
                key = L.compute_create_first_key(provider, "T", "B")
                ex = fake_execute({"lifecycle-create": resp})
                first = L.create_first(flow, title="T", body="B",
                                       retry_key=key, execute=ex)
                self.assertNotIsInstance(first, TrackerError,
                                         f"{provider}: {first}")
                self.assertEqual(first["id"], durable)
                self.assertFalse(first["retried"])
                self.assertTrue(
                    (flow / "create-first" / f"{key}.json").is_file(),
                    f"{provider}: recovery record must exist")
                # Retry: record replays; the provider is NEVER called again.
                ex2 = fake_execute({})
                second = L.create_first(flow, title="T", body="B",
                                        retry_key=key, execute=ex2)
                self.assertNotIsInstance(second, TrackerError)
                self.assertEqual(second["id"], durable)
                self.assertTrue(second["retried"])
                self.assertEqual(ex2.calls, [])


class SpecVerbPersistExternalAllFour(unittest.TestCase):
    """persist-external: linear resolves + links; the other three refuse
    deterministically BEFORE any tracker request (provider gate, not a skip)."""

    def test_linear_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(flow, ln_cfg(), tracker=_unlinked())
            ex = fake_execute({"lifecycle-resolve-uuid": ok({
                "data": {"issue": {
                    "id": LN_UUID, "identifier": "WOR-17",
                    "url": "https://linear.app/x/issue/WOR-17"}},
            })})
            out = L.persist_external(flow, "fn-1-demo", identifier="WOR-17",
                                     source="mcp", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["id"], LN_UUID)
            self.assertEqual(out["linkState"], "linked")
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["id"], LN_UUID)

    def test_non_linear_providers_refuse_before_any_request(self) -> None:
        for provider, cfg_fn in (("github", gh_cfg), ("gitlab", gl_cfg),
                                 ("jira", jr_cfg)):
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp) / ".flow"
                _write_flow(flow, cfg_fn(), tracker=_unlinked())
                ex = fake_execute({})  # any request would AssertionError
                out = L.persist_external(flow, "fn-1-demo",
                                         identifier="X-1", source="mcp",
                                         execute=ex)
                self.assertIsInstance(out, TrackerError)
                self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
                self.assertEqual(out.subtype, "provider")
                self.assertEqual(ex.calls, [])


def _ln_status_cfg() -> dict:
    cfg = ln_cfg()
    cfg["tracker"]["resolved"]["destination"]["stateIds"] = {
        "todo": "st-1", "in_progress": "st-2",
        "in_review": "st-3", "done": "st-4",
    }
    return cfg


class SpecVerbStatusAllFour(unittest.TestCase):
    """status --to in_progress from tracker todo: applied on all four,
    lastSyncedAt advanced, exactly one receipt."""

    def _cases(self):
        gh_parent = {"node_id": GH_NODE, "number": 42, "state": "open",
                     "labels": [{"name": "status:todo"}],
                     "html_url": "https://x/42"}
        gl_parent = dict(GL_ISSUE, labels=["status:todo"], state="opened")
        ln_parent = dict(LN_ISSUE, state={"id": "st-1", "name": "Todo",
                                          "type": "unstarted"})
        jr_parent = {"id": JR_ID, "key": "SCRUM-1",
                     "fields": {"summary": "T", "description": "B",
                                "labels": [],
                                "status": {"id": "1", "name": "To Do",
                                           "statusCategory": {"key": "new"}}}}
        return [
            ("github", gh_cfg(), GH_NODE, "#42", {
                "status-parent-read": ok(gh_parent),
                "merge-evidence": ok([]),
                "status-set": ok(dict(gh_parent, state="open")),
                "status-label-rm": empty(),
                "status-label-add": ok([{"name": "status:in-progress"}]),
                "status-label-readback": ok([{"name": "status:in-progress"}]),
            }),
            ("gitlab", gl_cfg(), str(GL_ID), "g/p#12", {
                "status-parent-read": ok(gl_parent),
                "merge-evidence": ok([]),
                "status-set": ok(dict(gl_parent,
                                      labels=["status:in_progress"])),
            }),
            ("linear", _ln_status_cfg(), LN_UUID, "WOR-17", {
                "status-parent-read": gql_issue(ln_parent),
                "status-state-read": ok({"data": {"issue": {
                    "id": LN_UUID, "state": {"id": "st-1", "name": "Todo",
                                             "type": "unstarted"}}}}),
                "merge-evidence": ok([]),
                "status-set": ok({"data": {"issueUpdate": {
                    "success": True, "issue": {"id": LN_UUID}}}}),
            }),
            ("jira", jr_cfg(), JR_ID, "SCRUM-1", {
                "status-parent-read": ok(jr_parent),
                "status-current": ok(jr_parent),
                "merge-evidence": ok([]),
                "status-transitions": ok({"transitions": [
                    {"id": "11", "to": {"id": "2"}}]}),
                "status-set": empty(),
            }),
        ]

    def test_status_applied_all_four(self) -> None:
        for provider, cfg, durable, display, responses in self._cases():
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp)
                path = _write_flow(flow, cfg, tracker={
                    "id": durable, "identifier": display, "url": "https://x",
                    "lastSyncedAt": None, "depRelations": [],
                    "linkState": "linked",
                })
                tdir = flow / "tasks"
                tdir.mkdir(parents=True, exist_ok=True)
                (tdir / "fn-1-demo.1.json").write_text(json.dumps({
                    "id": "fn-1-demo.1", "status": "in_progress",
                    "spec": "fn-1-demo"}), encoding="utf-8")
                ex = fake_execute(responses)
                out = S.status(flow, "fn-1-demo", to="in_progress",
                               execute=ex)
                self.assertNotIsInstance(out, TrackerError,
                                         f"{provider}: {out}")
                self.assertEqual(out["kind"], "applied", f"{provider}: {out}")
                saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
                self.assertIsNotNone(saved["lastSyncedAt"],
                                     f"{provider}: lastSyncedAt must advance")
                self.assertEqual(len(_receipts(flow)), 1, provider)


class SpecVerbRelateAllFour(unittest.TestCase):
    """relate --blocked-by: applied + ledger key persisted on all four
    (provider-specific degraded forms are part of the contract)."""

    def _write_pair(self, flow: Path, cfg: dict, a_tr: dict, b_tr: dict) -> None:
        (flow / "specs").mkdir(parents=True, exist_ok=True)
        (flow / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
        for sid, tr in (("fn-1-demo", a_tr), ("fn-2-dep", b_tr)):
            (flow / "specs" / f"{sid}.json").write_text(json.dumps({
                "id": sid, "title": sid, "status": "open",
                "branch_name": sid, "tracker": tr,
            }, indent=2) + "\n", encoding="utf-8")

    def test_relate_applied_all_four(self) -> None:
        ln_b = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
        cases = [
            ("github", gh_cfg(),
             {"id": GH_NODE, "identifier": "#42"},
             {"id": "I_kwDOTestNode2", "identifier": "#43"},
             {"relate-parent-read": [
                 ok({"id": 999001, "node_id": GH_NODE, "number": 42}),
                 ok({"id": 999002, "node_id": "I_kwDOTestNode2",
                     "number": 43})],
              "wire-relate-probe": ok([]),
              "relate-child-read": ok({"id": 999001, "node_id": GH_NODE,
                                       "number": 42}),
              "relate-list": ok([]),
              "relate-create": ok({"id": 999001})},
             "sub_issues"),
            ("gitlab", gl_cfg(),
             {"id": str(GL_ID), "identifier": "g/p#12"},
             {"id": str(GL_ID + 1), "identifier": "g/p#13"},
             {"relate-parent-read": [
                 ok({"id": GL_ID, "iid": 12, "description": "B"}),
                 ok({"id": GL_ID + 1, "iid": 13})],
              "relate-list": ok([]),
              "relate-create": ok({"id": 1, "link_type": "relates_to"}),
              "relate-body-read": ok(GL_ISSUE),
              "relate-body-write": gitlab_body_echo},
             "relates_to"),  # gl_cfg pins blockedBy False (free tier)
            ("linear", ln_cfg(),
             {"id": LN_UUID, "identifier": "WOR-17"},
             {"id": ln_b, "identifier": "WOR-18"},
             {"relate-list": ok({"data": {"issue": {
                 "id": LN_UUID,
                 "relations": {"nodes": []},
                 "inverseRelations": {"nodes": []}}}}),
              "relate-create": ok({"data": {"issueRelationCreate": {
                  "success": True, "issueRelation": {"id": "rel-1"}}}})},
             None),
            ("jira", jr_cfg(),
             {"id": JR_ID, "identifier": "SCRUM-1"},
             {"id": "10043", "identifier": "SCRUM-2"},
             {"relate-list": ok({"fields": {"issuelinks": []}}),
              "relate-create": ok(None)},
             "blocks"),
        ]
        for provider, cfg, a_ids, b_ids, responses, form in cases:
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp)
                base = {"url": "u", "depRelations": [], "linkState": "linked"}
                self._write_pair(flow, cfg, {**base, **a_ids},
                                 {**base, **b_ids})
                ex = fake_execute(responses)
                out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                               execute=ex)
                self.assertNotIsInstance(out, TrackerError,
                                         f"{provider}: {out}")
                self.assertEqual(out["kind"], "applied", f"{provider}: {out}")
                self.assertEqual(len(out["key"]), 16)
                if form is not None:
                    self.assertEqual(out["form"], form, provider)
                saved = json.loads(
                    (flow / "specs" / "fn-1-demo.json").read_text(
                        encoding="utf-8"))["tracker"]
                self.assertTrue(
                    any(r.get("key") == out["key"]
                        for r in saved["depRelations"] if isinstance(r, dict)),
                    f"{provider}: ledger must persist the edge key")


class SpecVerbSyncBodyAllFour(unittest.TestCase):
    """sync-body push: pushed + paired merge base committed on all four."""

    def test_push_all_four(self) -> None:
        for provider, cfg_fn, durable, display, parent_resp, mk in PROVIDERS:
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp)
                _write_flow(flow, cfg_fn(), tracker={
                    "id": durable, "identifier": display, "url": "https://x",
                    "lastSyncedAt": None, "depRelations": [],
                    "linkState": "linked",
                    "mergeBaseFlow": None, "mergeBaseTracker": None,
                    "baseHashFlow": None, "baseHashTracker": None,
                })
                update_resp = (
                    ok({"data": {"issueUpdate": {
                        "success": True, "issue": mk("NEW FLOW\n")}}})
                    if provider == "linear"
                    else (empty() if provider == "jira"
                          else parent_resp("NEW FLOW\n"))
                )
                ex = fake_execute({
                    "sync-body-parent-read": parent_resp("old remote"),
                    "wire-parent-read": parent_resp("old remote"),
                    "wire-update": update_resp,
                    "wire-read": parent_resp("NEW FLOW\n"),
                })
                out = SB.sync_body(flow, "fn-1-demo",
                                   flow_file_body="NEW FLOW\n",
                                   direction="push", execute=ex)
                self.assertNotIsInstance(out, TrackerError,
                                         f"{provider}: {out}")
                self.assertEqual(out["kind"], "pushed", f"{provider}: {out}")
                saved = _saved(flow)["tracker"]
                self.assertEqual(saved["mergeBaseFlow"], "NEW FLOW\n")
                self.assertIsNotNone(saved["mergeBaseTracker"], provider)
                self.assertEqual(saved["baseHashFlow"], sha("NEW FLOW\n"))
                self.assertIsNotNone(saved["lastSyncedAt"], provider)


class FullVerbSurfaceGuard(unittest.TestCase):
    """R18 completeness: the matrix names EVERY granular verb the spec
    defines - the 11 wire verbs AND the 6 spec-aware verbs."""

    def test_wire_surface_matches_package(self) -> None:
        self.assertEqual(tuple(WIRE_VERBS), W.WIRE_VERBS)

    def test_spec_verb_surface_is_complete(self) -> None:
        self.assertEqual(
            SPEC_VERBS,
            ("create", "create-first", "persist-external", "status",
             "relate", "sync-body"))
        covered = {
            "create": SpecVerbCreateAllFour,
            "create-first": SpecVerbCreateFirstAllFour,
            "persist-external": SpecVerbPersistExternalAllFour,
            "status": SpecVerbStatusAllFour,
            "relate": SpecVerbRelateAllFour,
            "sync-body": SpecVerbSyncBodyAllFour,
        }
        self.assertEqual(set(covered), set(SPEC_VERBS))


# ---------------------------------------------------------------------------
# Fault injection (six points)
# ---------------------------------------------------------------------------

class PreCreateWindowOpen(unittest.TestCase):
    """Documents the create-first record window AFTER the PR #246 claim fix.

    An OBSERVED finalize failure (create landed, record write errored) no
    longer duplicates on retry: the pending claim stays on disk and the retry
    refuses (create_in_flight) while the error carries the created identity.
    The remaining ACCEPTED gap is the hard-crash window - a dead run's stale
    claim is reclaimed and the retry creates a second issue, exactly the
    pre-record window that existed before claims."""

    def _make_ex(self, created: dict):
        def responses_for(_req=None):
            created["n"] += 1
            node = f"I_node_{created['n']}"
            return ok({
                "id": created["n"], "node_id": node,
                "number": created["n"],
                "html_url": f"https://github.com/o/r/issues/{created['n']}",
            })
        return fake_execute({"lifecycle-create": responses_for})

    def test_observed_finalize_failure_refuses_retry_with_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_config(flow, gh_cfg())
            key = L.compute_create_first_key("github", "T", "B")
            created = {"n": 0}
            rec_path = flow / "create-first" / f"{key}.json"

            from flowctl_tracker.lifecycle import verbs as verbs_mod
            real_write = verbs_mod.atomic_write_json

            def fail_finalize(path, data):
                # The claim write goes through; only the FINAL record (the one
                # carrying the created id) dies.
                if isinstance(data, dict) and data.get("id"):
                    return TrackerError(ErrorClass.TRANSPORT,
                                        "simulated die after create",
                                        subtype="write")
                return real_write(path, data)

            with mock.patch(
                "flowctl_tracker.lifecycle.verbs.atomic_write_json",
                side_effect=fail_finalize,
            ):
                first = L.create_first(flow, title="T", body="B",
                                       retry_key=key,
                                       execute=self._make_ex(created))
            self.assertIsInstance(first, TrackerError)
            self.assertEqual(created["n"], 1)
            # The error carries the created identity so the caller can link
            # the existing issue instead of waiting out the stale window.
            details = first.details or {}
            self.assertEqual(details.get("completed_steps"), ["create"])
            self.assertEqual(details.get("id"), "I_node_1")
            claim = json.loads(rec_path.read_text(encoding="utf-8"))
            self.assertEqual(claim.get("status"), "pending",
                             "claim survives an observed finalize failure")

            # Retry same key: REFUSES instead of creating a duplicate.
            second = L.create_first(flow, title="T", body="B",
                                    retry_key=key, execute=self._make_ex(created))
            self.assertIsInstance(second, TrackerError)
            self.assertIs(second.cls, ErrorClass.CONFLICT)
            self.assertEqual(second.subtype, "create_in_flight")
            self.assertEqual(created["n"], 1, "no second remote create")

    def test_crash_window_retry_after_stale_claim_duplicates(self) -> None:
        import socket
        import time as time_mod
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_config(flow, gh_cfg())
            key = L.compute_create_first_key("github", "T", "B")
            rec_path = flow / "create-first" / f"{key}.json"
            rec_path.parent.mkdir(parents=True)
            # A hard crash between provider create and finalize leaves a
            # pending claim from a dead pid and NO recorded id.
            rec_path.write_text(json.dumps({
                "retryKey": key, "status": "pending", "pid": 0,
                "host": socket.gethostname(),
                "claimedAt": time_mod.time() - 999,
                "title": "T", "transport": "github"}), encoding="utf-8")
            created = {"n": 0}
            out = L.create_first(flow, title="T", body="B",
                                 retry_key=key, execute=self._make_ex(created))
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(created["n"], 1,
                             "accepted gap: the crash window stays open - the "
                             "stale claim is reclaimed and a second issue is "
                             "created (does not assert closed)")
            self.assertFalse(out["retried"])


class PostWriteReadbackFailureAllFour(unittest.TestCase):
    """sync-body push: wire-read fails after update -> prior merge base intact."""

    def test_readback_failure_across_all_four(self) -> None:
        prior_flow = "PRIOR FLOW\n"
        prior_tracker = "PRIOR TRACKER"
        for provider, cfg_fn, durable, display, parent_resp, _mk in PROVIDERS:
            with self.subTest(provider=provider), tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp)
                _write_flow(
                    flow, cfg_fn(),
                    tracker={
                        "id": durable, "identifier": display, "url": "https://x",
                        "lastSyncedAt": "OLD", "depRelations": [],
                        "linkState": "linked",
                        "mergeBaseFlow": prior_flow,
                        "mergeBaseTracker": prior_tracker,
                        "baseHashFlow": sha(prior_flow),
                        "baseHashTracker": sha(prior_tracker),
                    })
                update_resp = (
                    ok({"data": {"issueUpdate": {
                        "success": True, "issue": _ln_issue("written")}}})
                    if provider == "linear"
                    else (empty() if provider == "jira"
                          else parent_resp("written"))
                )
                ex = fake_execute({
                    "sync-body-parent-read": parent_resp("old remote"),
                    "wire-parent-read": parent_resp("old remote"),
                    "wire-update": update_resp,
                    "wire-read": TrackerError(ErrorClass.TRANSPORT,
                                              "readback boom",
                                              subtype="readback"),
                })
                out = SB.sync_body(
                    flow, "fn-1-demo", flow_file_body="NEW FLOW\n",
                    direction="push", execute=ex)
                self.assertIsInstance(out, TrackerError)
                self.assertEqual(out.details.get("completed_steps"),
                                 ["wire-update"])
                saved = _saved(flow)["tracker"]
                self.assertEqual(saved["mergeBaseFlow"], prior_flow)
                self.assertEqual(saved["mergeBaseTracker"], prior_tracker)
                self.assertEqual(saved["baseHashFlow"], sha(prior_flow))
                self.assertEqual(saved["baseHashTracker"], sha(prior_tracker))
                self.assertEqual(saved["lastSyncedAt"], "OLD")


class ScopedInvalidationViaResolveVerb(unittest.TestCase):
    """destination --scope refresh must not clobber ids nor freshen capabilities."""

    def test_gitlab_destination_scope_preserves_capabilities_stamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            old = "2026-01-01T00:00:00Z"
            cfg = {
                "tracker": {
                    "type": "gitlab",
                    "perTracker": {"project": "g/p", "host": "gitlab.com"},
                    "resolved": {
                        "resolvedAt": old,
                        "scopeResolvedAt": {
                            "destination": old, "capabilities": old,
                        },
                        "destination": {
                            "projectId": 1, "projectPath": "g/p",
                            "host": "gitlab.com", "namespaceId": 9,
                        },
                        "capabilities": {
                            "attachments": True, "blockedBy": False,
                            "subIssues": False, "deleteIssue": True,
                            "_source": {"gitlabPlan": "free"},
                        },
                    },
                },
            }
            _write_config(flow, cfg)
            ex = fake_execute({
                "resolve-destination": ok({
                    "id": 1, "path_with_namespace": "g/renamed",
                    "web_url": "https://gitlab.com/g/renamed",
                    "namespace": {"id": 9, "full_path": "g"},
                }),
            })
            payload, code = RV.run(flow, scope="destination", refresh=True,
                                   execute=ex)
            self.assertEqual(code, 0, payload)
            on_disk = json.loads((flow / "config.json").read_text(encoding="utf-8"))
            resolved = on_disk["tracker"]["resolved"]
            sra = resolved["scopeResolvedAt"]
            self.assertEqual(sra["capabilities"], old,
                             "destination refresh must not freshen capabilities")
            self.assertNotEqual(sra["destination"], old)
            self.assertEqual(resolved["capabilities"]["blockedBy"], False)
            self.assertNotIn("statusIds", resolved["destination"])
            self.assertNotIn("stateIds", resolved["destination"])

    def test_jira_destination_scope_preserves_status_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            old = "2026-01-01T00:00:00Z"
            status_ids = {"todo": "1", "done": "4"}
            cfg = {
                "tracker": {
                    "type": "jira",
                    "perTracker": {
                        "baseUrl": "https://ex.atlassian.net",
                        "projectKey": "SCRUM",
                    },
                    "resolved": {
                        "resolvedAt": old,
                        "scopeResolvedAt": {
                            "destination": old,
                            "destination.statusIds": old,
                            "capabilities": old,
                        },
                        "destination": {
                            "baseUrl": "https://ex.atlassian.net",
                            "projectKey": "SCRUM", "projectId": "10000",
                            "issueTypeId": "10001", "apiVersion": 2,
                            "style": "classic", "statusIds": dict(status_ids),
                        },
                        "capabilities": {
                            "attachments": True, "blockedBy": True,
                            "subIssues": False, "deleteIssue": True,
                        },
                    },
                },
            }
            _write_config(flow, cfg)
            ex = fake_execute({
                "resolve-destination": ok({
                    "id": "10000", "key": "SCRUM", "style": "classic",
                    "issueTypes": [{"id": "10001", "name": "Task",
                                    "subtask": False}],
                }),
            })
            payload, code = RV.run(flow, scope="destination", refresh=True,
                                   execute=ex)
            self.assertEqual(code, 0, payload)
            on_disk = json.loads((flow / "config.json").read_text(encoding="utf-8"))
            resolved = on_disk["tracker"]["resolved"]
            self.assertEqual(resolved["destination"]["statusIds"], status_ids,
                             "destination refresh must not clobber statusIds")
            sra = resolved["scopeResolvedAt"]
            self.assertEqual(sra["capabilities"], old)
            self.assertEqual(sra.get("destination.statusIds"), old)


class LockRaceViaResolveVerb(unittest.TestCase):
    """Two concurrent resolve_verb.run writers on DIFFERENT scopes both land."""

    def test_concurrent_destination_and_capabilities_via_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            cfg = {
                "tracker": {
                    "type": "gitlab",
                    "perTracker": {"project": "g/p", "host": "gitlab.com"},
                },
            }
            _write_config(flow, cfg)
            results = {}
            barrier = threading.Barrier(2)

            def dest_ex(request):
                # Rendezvous, not a performance assertion: the timeout only stops a
                # genuinely broken test from hanging, so it should be generous. Shared
                # CI runners schedule unpredictably regardless of how the suite is
                # parallelised - this has never failed, the headroom is precautionary.
                barrier.wait(timeout=120)
                time.sleep(0.02)
                return ok({
                    "id": 1, "path_with_namespace": "g/p",
                    "web_url": "https://gitlab.com/g/p",
                    "namespace": {"id": 9, "full_path": "g"},
                })

            def caps_ex(request):
                barrier.wait(timeout=120)
                time.sleep(0.02)
                return ok({"id": 9, "plan": "free"})

            def run_dest():
                results["destination"] = RV.run(
                    flow, scope="destination", refresh=True,
                    execute=fake_execute({"resolve-destination": dest_ex}))

            def run_caps():
                # capabilities needs destination.namespaceId; seed it first
                # then race the two refreshes after both scopes exist.
                results["capabilities"] = RV.run(
                    flow, scope="capabilities", refresh=True,
                    execute=fake_execute({"probe-plan": caps_ex}))

            # Seed destination so capabilities resolve can probe.
            seed_ex = fake_execute({
                "resolve-destination": ok({
                    "id": 1, "path_with_namespace": "g/p",
                    "web_url": "https://gitlab.com/g/p",
                    "namespace": {"id": 9, "full_path": "g"},
                }),
            })
            payload, code = RV.run(flow, scope="destination", execute=seed_ex)
            self.assertEqual(code, 0, payload)
            seed_caps = fake_execute({"probe-plan": ok({"id": 9, "plan": "free"})})
            payload, code = RV.run(flow, scope="capabilities", execute=seed_caps)
            self.assertEqual(code, 0, payload)

            t1 = threading.Thread(target=run_dest)
            t2 = threading.Thread(target=run_caps)
            t1.start(); t2.start()
            # The join bound must not be tighter than the barrier above: in the
            # slow-scheduling case the 120s rendezvous exists to tolerate, a 10s
            # join let the main thread read `results` while the workers were
            # still running - KeyError, plus a race with tempdir cleanup. Assert
            # the threads actually finished rather than trusting the timeout.
            t1.join(120); t2.join(120)
            self.assertFalse(t1.is_alive(), "destination worker did not finish")
            self.assertFalse(t2.is_alive(), "capabilities worker did not finish")
            self.assertEqual(results["destination"][1], 0, results["destination"][0])
            self.assertEqual(results["capabilities"][1], 0, results["capabilities"][0])
            on_disk = json.loads((flow / "config.json").read_text(encoding="utf-8"))
            resolved = on_disk["tracker"]["resolved"]
            self.assertEqual(resolved["destination"]["namespaceId"], 9)
            self.assertIn("attachments", resolved["capabilities"])
            self.assertIsNotNone(resolved.get("resolvedAt"))


class RetryExhaustion(unittest.TestCase):
    def test_rate_limited_idempotent_read_exhausts_and_surfaces_retry_after(self) -> None:
        calls = {"n": 0}
        sleeps = []

        def fake_http(req, cred, verify):
            calls["n"] += 1
            return Response(429, {"Retry-After": "7"}, b"slow", 0.01)

        with mock.patch.object(X, "_http", side_effect=fake_http), \
             mock.patch.object(X.time, "sleep", side_effect=lambda s: sleeps.append(s)):
            err = X.execute(Request(
                provider="jira", op="wire-read", method="GET",
                url_or_argv="https://ex.atlassian.net/rest/api/2/issue/SCRUM-1",
                idempotent=True,
            ))
        self.assertIsInstance(err, TrackerError)
        self.assertIs(err.cls, ErrorClass.RATE_LIMITED)
        self.assertEqual(calls["n"], MAX_RETRIES + 1)
        self.assertEqual(err.retry_after_s, 7.0)
        payload, code = E.failure(err)
        data = json.loads(payload)
        self.assertEqual(data["class"], "rate_limited")
        self.assertEqual(data["details"]["retry_after_s"], 7.0)
        self.assertEqual(len(sleeps), MAX_RETRIES)


class RateLimitBackoffPerAdapter(unittest.TestCase):
    """Each provider's header shape -> computed retry_after_s end-to-end."""

    def _run(self, provider: str, resp: Response) -> tuple[TrackerError, list]:
        sleeps = []
        calls = {"n": 0}

        def fake_http(req, cred, verify):
            calls["n"] += 1
            return resp

        with mock.patch.object(X, "_http", side_effect=fake_http), \
             mock.patch.object(X.time, "sleep", side_effect=lambda s: sleeps.append(s)):
            err = X.execute(Request(
                provider=provider, op="wire-read", method="GET",
                url_or_argv="https://example.test/x",
                idempotent=True,
            ))
        self.assertIsInstance(err, TrackerError)
        self.assertIs(err.cls, ErrorClass.RATE_LIMITED)
        self.assertEqual(calls["n"], MAX_RETRIES + 1)
        return err, sleeps

    def test_github_403_remaining_zero_reset_epoch_seconds(self) -> None:
        reset = time.time() + 18.0
        err, sleeps = self._run("github", Response(
            403, {"x-ratelimit-remaining": "0",
                  "x-ratelimit-reset": str(reset)},
            b"API rate limit exceeded", 0.01))
        self.assertAlmostEqual(err.retry_after_s, 18.0, delta=2.0)
        self.assertAlmostEqual(sleeps[0],
                               X._backoff_delay(0, err.retry_after_s), delta=0.5)

    def test_gitlab_429_retry_after(self) -> None:
        err, sleeps = self._run("gitlab", Response(
            429, {"Retry-After": "11"}, b"{}", 0.01))
        self.assertEqual(err.retry_after_s, 11.0)
        self.assertEqual(sleeps[0], X._backoff_delay(0, 11.0))

    def test_linear_ratelimited_complexity_epoch_milliseconds(self) -> None:
        now = time.time()
        # Two exhausted buckets; wait for the SLOWEST (complexity=22s).
        err, sleeps = self._run("linear", Response(
            200,
            {
                "X-RateLimit-Requests-Remaining": "0",
                "X-RateLimit-Requests-Reset": str((now + 5.0) * 1000.0),
                "X-RateLimit-Complexity-Remaining": "0",
                "X-RateLimit-Complexity-Reset": str((now + 22.0) * 1000.0),
            },
            b'{"errors":[{"extensions":{"code":"RATELIMITED"}}]}',
            0.01,
        ))
        self.assertAlmostEqual(err.retry_after_s, 22.0, delta=2.0)
        classified = C.classify("linear", Response(
            200,
            {
                "X-RateLimit-Requests-Remaining": "0",
                "X-RateLimit-Requests-Reset": str((now + 5.0) * 1000.0),
                "X-RateLimit-Complexity-Remaining": "0",
                "X-RateLimit-Complexity-Reset": str((now + 22.0) * 1000.0),
            },
            b'{"errors":[{"extensions":{"code":"RATELIMITED"}}]}',
            0.01,
        ))
        self.assertAlmostEqual(classified.retry_after_s, 22.0, delta=2.0)
        self.assertAlmostEqual(sleeps[0],
                               X._backoff_delay(0, err.retry_after_s), delta=0.5)

    def test_jira_429_retry_after_350_budget_noted(self) -> None:
        # Jira Cloud ~350 req / 10s budget; Retry-After is the backoff signal.
        err, sleeps = self._run("jira", Response(
            429, {"Retry-After": "9"}, b"Rate limit exceeded (350)", 0.01))
        self.assertEqual(err.retry_after_s, 9.0)
        self.assertEqual(sleeps[0], X._backoff_delay(0, 9.0))


# ---------------------------------------------------------------------------
# Jira DC custom-key path (R17)
# ---------------------------------------------------------------------------

class JiraDcCustomKey(unittest.TestCase):
    """MY_LONG_PROJECT_KEY-7 round-trips; marked unverified in package + spec."""

    def test_display_parse_accepts_underscore_long_key(self) -> None:
        self.assertEqual(W._jira_issue_key(DC_KEY), DC_KEY)
        self.assertEqual(W._jira_project_key(DC_PROJECT), DC_PROJECT)
        bad = W._jira_issue_key("not a key")
        self.assertIsInstance(bad, TrackerError)

    def test_wire_read_addresses_dc_display_key(self) -> None:
        cfg = jr_cfg(project_key=DC_PROJECT)
        ex = fake_execute({"wire-read": ok(DC_ISSUE)})
        out = W.dispatch("read", cfg, locator=loc(DC_ID, DC_KEY), execute=ex)
        self.assertNotIsInstance(out, TrackerError)
        self.assertEqual(out["id"], DC_ID)
        self.assertEqual(out["identifier"], DC_KEY)
        self.assertIn(DC_KEY, str(ex.calls[0].url_or_argv))

    def test_list_open_jql_accepts_dc_project_key(self) -> None:
        cfg = jr_cfg(project_key=DC_PROJECT)
        ex = fake_execute({"wire-list-open": ok({"issues": [DC_ISSUE]})})
        out = W.dispatch("list-open", cfg, execute=ex)
        self.assertNotIsInstance(out, TrackerError)
        url = str(ex.calls[0].url_or_argv)
        self.assertIn(DC_PROJECT, url)

    def test_lifecycle_create_persists_dc_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            path = _write_flow(flow, jr_cfg(project_key=DC_PROJECT), tracker={
                "id": None, "identifier": None, "url": None,
                "lastSyncedAt": None, "depRelations": [],
                "linkState": "unlinked",
            })
            ex = fake_execute({
                "lifecycle-create": ok({"id": DC_ID, "key": DC_KEY}),
                "sync-body-parent-read": ok({
                    "id": DC_ID,
                    "key": DC_KEY,
                    "fields": {
                        "summary": "T",
                        "description": "B",
                        "labels": [],
                    },
                }),
            })
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["identifier"], DC_KEY)
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["identifier"], DC_KEY)
            self.assertEqual(saved["id"], DC_ID)

    def test_status_addresses_dc_key_via_status_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            cfg = jr_cfg(project_key=DC_PROJECT, status_ids={
                "todo": "1", "in_progress": "2", "in_review": "3", "done": "4",
            })
            cfg["review"] = {"backend": "codex"}
            _write_flow(flow, cfg, tracker={
                "id": DC_ID, "identifier": DC_KEY, "url": f"https://ex/browse/{DC_KEY}",
                "lastSyncedAt": None, "depRelations": [], "linkState": "linked",
            })
            # Already at todo; request todo -> noop (addresses via display key
            # on the parent read / status-current path).
            parent = dict(DC_ISSUE)
            parent["fields"] = dict(DC_ISSUE["fields"], status={
                "id": "1", "name": "To Do",
                "statusCategory": {"key": "new"},
            })
            ex = fake_execute({
                "status-parent-read": ok(parent),
                "status-current": ok(parent),
                "merge-evidence": ok([]),
            })
            out = S.status(flow, "fn-1-demo", to="todo", execute=ex,
                           write_receipt=False)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["kind"], "noop")
            parent_url = str(ex.calls[0].url_or_argv)
            self.assertIn(DC_KEY, parent_url)


if __name__ == "__main__":
    unittest.main()
