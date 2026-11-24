"""Parent issue at creation: the spec's tracker.parent (fn-329).

The parent is a creation input. Each adapter's create carries it in the one
create request (GitLab may add one read to resolve an epic reference); a spec
without one sends the same request bytes as before; GitHub and Jira Data
Center refuse it before any request; and no operation after creation sends it.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "plugins" / "flow"
sys.path.insert(0, str(ROOT / "skills" / "flow" / "scripts"))

from flowctl_tracker import classify  # noqa: E402
from flowctl_tracker import lifecycle as L  # noqa: E402
from flowctl_tracker import spec_store as SS  # noqa: E402
from flowctl_tracker import status as S  # noqa: E402
from flowctl_tracker.types import ErrorClass, Response, TrackerError  # noqa: E402

FLOWCTL = ROOT / "skills" / "flow" / "scripts" / "edge.py"
GH_NODE = "I_kwDOTestNode1"
GL_ID = 84817009
LN_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
JR_ID = "10042"
PROJECT = "11111111-2222-3333-4444-555555555555"

#: The field each adapter would carry a parent in.
PARENT_KEYS = ("parent", "parentId", "epic_id")


def ok(body) -> Response:
    return Response(200, {}, json.dumps(body).encode() if body is not None else b"", 0.01)


def empty() -> Response:
    return Response(204, {}, b"", 0.01)


def rejected(provider: str, status: int, body: dict) -> TrackerError:
    """What the real executor hands back: the response through the shared
    classifier, not a pre-digested error."""
    err = classify.classify(
        provider, Response(status, {}, json.dumps(body).encode(), 0.01))
    assert isinstance(err, TrackerError)
    return err


def fake_execute(responses: dict):
    calls = []

    def execute(request):
        calls.append(request)
        if request.op == "lifecycle-create-meta" and request.op not in responses:
            return ok({})
        if request.op == "merge-evidence" and request.op not in responses:
            return ok([])
        if request.op not in responses:
            raise AssertionError(
                f"unexpected op {request.op!r}; have {sorted(responses)}")
        out = responses[request.op]
        if isinstance(out, list):
            out = out.pop(0)
        return out(request) if callable(out) else out

    execute.calls = calls
    return execute


def gh_cfg() -> dict:
    return {"tracker": {"type": "github",
                        "resolved": {"destination": {"owner": "o", "repo": "r"}}}}


def gl_cfg() -> dict:
    return {"tracker": {"type": "gitlab",
                        "resolved": {"destination": {
                            "projectId": 1, "projectPath": "g/p",
                            "host": "gitlab.com", "namespaceId": 9}}}}


def ln_cfg(*, preferred: str | None = None) -> dict:
    per = {"teamId": "team-1"}
    if preferred is not None:
        per["preferredTransport"] = preferred
    return {"tracker": {"type": "linear", "perTracker": per,
                        "resolved": {"destination": {
                            "teamId": "team-1", "teamKey": "WOR",
                            "stateIds": {"todo": "st-1", "in_progress": "st-2",
                                         "in_review": "st-3", "done": "st-4"}}}}}


def jr_cfg(*, auth_scheme: str | None = None) -> dict:
    per = {"blocksLinkType": "Blocks"}
    if auth_scheme is not None:
        per["authScheme"] = auth_scheme
    return {"tracker": {"type": "jira", "perTracker": per,
                        "resolved": {"destination": {
                            "baseUrl": "https://ex.atlassian.net",
                            "projectKey": "SCRUM", "projectId": "10000",
                            "issueTypeId": "10001", "apiVersion": 2,
                            "statusIds": {"todo": "1", "in_progress": "2",
                                          "in_review": "3", "done": "4"}}}}}


def _write_flow(flow: Path, config: dict, *, tracker: dict | None = None) -> Path:
    (flow / "specs").mkdir(parents=True, exist_ok=True)
    (flow / "config.json").write_text(json.dumps(config), encoding="utf-8")
    tr = tracker or {}
    lines = ["---", "id: fn-1-demo", "title: Demo"]
    if any(tr.get(k) for k in ("id", "identifier", "url", "snapshot")):
        lines.append("tracker:")
        for k in ("id", "identifier", "url", "snapshot"):
            if tr.get(k):
                lines.append(f"  {k}: {json.dumps(str(tr[k]))}")
    lines.extend(["---", ""])
    path = flow / "specs" / "fn-1-demo.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _saved(flow: Path) -> dict:
    loaded = SS.load_spec_doc(flow / "specs" / "fn-1-demo.md", spec_id="fn-1-demo")
    assert not isinstance(loaded, TrackerError), loaded
    return L.helpers.merged_tracker(loaded[0])


def _create_call(ex):
    return next(c for c in ex.calls if c.op == "lifecycle-create")


def _create_json(ex) -> dict:
    return json.loads(_create_call(ex).body.decode())


def _gh_issue(body: str) -> dict:
    return {"id": 999001, "node_id": GH_NODE, "number": 42, "title": "T",
            "body": body, "html_url": "https://github.com/o/r/issues/42",
            "labels": [], "state": "open"}


def _gl_issue(body: str) -> dict:
    return {"id": GL_ID, "iid": 12, "title": "T", "description": body,
            "web_url": "https://gitlab.com/g/p/-/issues/12",
            "references": {"full": "g/p#12"}, "labels": [], "state": "opened"}


def _ln_issue(body: str) -> dict:
    return {"id": LN_UUID, "identifier": "WOR-17", "title": "T",
            "description": body, "url": "https://linear.app/x/issue/WOR-17",
            "state": {"id": "st-1", "name": "Todo", "type": "unstarted"},
            "labels": {"nodes": []}, "assignee": None}


def _jr_issue(body: str) -> dict:
    return {"id": JR_ID, "key": "SCRUM-1",
            "fields": {"summary": "T", "description": body, "labels": [],
                       "status": {"id": "1", "name": "To Do",
                                  "statusCategory": {"key": "new"}},
                       "priority": None, "assignee": None}}


def _create_responses(provider: str) -> dict:
    """A successful create plus the readback that seeds the paired base."""
    if provider == "github":
        return {"lifecycle-create": ok(_gh_issue("B")),
                "sync-body-parent-read": ok(_gh_issue("B"))}
    if provider == "gitlab":
        return {"lifecycle-create": ok(_gl_issue("B")),
                "sync-body-parent-read": ok(_gl_issue("B"))}
    if provider == "linear":
        return {"lifecycle-create": ok({"data": {"issueCreate": {
                    "success": True, "issue": _ln_issue("B")}}}),
                "sync-body-parent-read": ok({"data": {"issue": _ln_issue("B")}})}
    return {"lifecycle-create": ok({"id": JR_ID, "key": "SCRUM-1"}),
            "sync-body-parent-read": ok(_jr_issue("B"))}


CFG = {"github": gh_cfg, "gitlab": gl_cfg, "linear": ln_cfg, "jira": jr_cfg}


def _sent_parent_keys(ex) -> list:
    """Every parent-carrying key any request body sent, at any depth."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in PARENT_KEYS:
                    found.append(key)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for call in ex.calls:
        if call.body:
            walk(json.loads(call.body.decode()))
    return found


class ParentField(unittest.TestCase):
    def test_trimmed_value_is_sent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg())
            ex = fake_execute(_create_responses("linear"))
            L.create(flow, "fn-1-demo", title="T", body="B", parent=" WOR-40 ", execute=ex)
            self.assertEqual(_create_json(ex)["variables"]["input"]["parentId"],
                             "WOR-40")

    def test_null_is_unmanaged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg())
            ex = fake_execute(_create_responses("linear"))
            L.create(flow, "fn-1-demo", title="T", body="B", parent=None, execute=ex)
            self.assertNotIn("parentId", _create_json(ex)["variables"]["input"])

    def test_unusable_value_errors_before_any_request(self) -> None:
        for bad in ("", "  ", 12, {"key": "WOR-40"}):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp) / ".flow"
                _write_flow(flow, ln_cfg())
                ex = fake_execute({})
                out = L.create(flow, "fn-1-demo", title="T", body="B", parent=bad, execute=ex)
                self.assertIsInstance(out, TrackerError, bad)
                self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
                self.assertEqual(out.subtype, "parent")
                self.assertEqual(ex.calls, [])


class NoParentKeepsTheRequestBytes(unittest.TestCase):
    """R7: without a parent every create request is the pre-parent request."""

    EXPECTED = {
        "github": {"title": "T", "body": "B"},
        "gitlab": {"title": "T", "description": "B"},
        "linear": {"query": "mutation($input: IssueCreateInput!) { "
                            "issueCreate(input: $input) { success "
                            "issue { id identifier url description } } }",
                   "variables": {"input": {"teamId": "team-1", "title": "T",
                                           "description": "B"}}},
        "jira": {"fields": {"project": {"id": "10000"},
                            "issuetype": {"id": "10001"},
                            "summary": "T", "description": "B"}},
    }

    def test_create_request_bytes_and_count_per_tracker(self) -> None:
        for provider, cfg in CFG.items():
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp) / ".flow"
                _write_flow(flow, cfg())
                ex = fake_execute(_create_responses(provider))
                out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
                self.assertNotIsInstance(out, TrackerError, f"{provider}: {out}")
                self.assertEqual(_create_call(ex).body,
                                 json.dumps(self.EXPECTED[provider]).encode())
                expected_ops = ["lifecycle-create"]
                if provider == "jira":
                    expected_ops.insert(0, "lifecycle-create-meta")
                self.assertEqual([c.op for c in ex.calls], expected_ops)
                self.assertNotIn("parent", out)
                self.assertNotIn("parent", _saved(flow))


class JiraCloudParent(unittest.TestCase):
    def test_parent_rides_the_one_create_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, jr_cfg(auth_scheme="cloud-basic"))
            ex = fake_execute(_create_responses("jira"))
            out = L.create(flow, "fn-1-demo", title="T", body="B",
                           parent="SCRUM-12", execute=ex)
            self.assertEqual(out["identifier"], "SCRUM-1")
            self.assertEqual(out["parent"], "SCRUM-12")
            self.assertEqual(_create_json(ex)["fields"]["parent"],
                             {"key": "SCRUM-12"})
            self.assertEqual(
                [c.op for c in ex.calls],
                ["lifecycle-create-meta", "lifecycle-create"])
            self.assertNotIn("parent", _saved(flow))

    def test_rejected_parent_returns_jiras_error_and_links_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, jr_cfg())
            ex = fake_execute({"lifecycle-create": rejected(
                "jira", 400, {"errorMessages": [],
                              "errors": {"parent": "Could not find issue by id or key."}})})
            out = L.create(flow, "fn-1-demo", title="T", body="B",
                           parent="SCRUM-999", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
            self.assertEqual(
                [c.op for c in ex.calls].count("lifecycle-create"), 1)
            self.assertIsNone(_saved(flow)["id"])


class LinearParent(unittest.TestCase):
    def test_parent_id_rides_the_create_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg())
            ex = fake_execute(_create_responses("linear"))
            out = L.create(flow, "fn-1-demo", title="T", body="B",
                           parent="WOR-40", execute=ex)
            self.assertEqual(out["parent"], "WOR-40")
            self.assertEqual(
                _create_json(ex)["variables"]["input"],
                {"teamId": "team-1", "title": "T", "description": "B",
                 "parentId": "WOR-40"})
            self.assertEqual([c.op for c in ex.calls],
                             ["lifecycle-create"])

    def test_parent_and_project_fields_both_ride(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg())
            ex = fake_execute(_create_responses("linear"))
            L.create(flow, "fn-1-demo", title="T", body="B",
                     parent="WOR-40", project_id=PROJECT, execute=ex)
            self.assertEqual(
                _create_json(ex)["variables"]["input"],
                {"teamId": "team-1", "title": "T", "description": "B",
                 "projectId": PROJECT, "parentId": "WOR-40"})

    def test_unknown_parent_returns_linears_error_and_links_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg())
            ex = fake_execute({"lifecycle-create": rejected(
                "linear", 400,
                {"errors": [{"message": "Entity not found: Issue - WOR-999"}]})})
            out = L.create(flow, "fn-1-demo", title="T", body="B",
                           parent="WOR-999", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.NOT_FOUND)
            self.assertIsNone(_saved(flow)["id"])


class GitLabEpicParent(unittest.TestCase):
    def _create(self, parent: str, responses: dict):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        flow = Path(tmp.name) / ".flow"
        _write_flow(flow, gl_cfg())
        ex = fake_execute(responses)
        return L.create(flow, "fn-1-demo", title="T", body="B",
                        parent=parent, execute=ex), ex, flow

    def test_epic_id_is_sent_without_a_read(self) -> None:
        responses = _create_responses("gitlab")
        responses["lifecycle-create"] = ok({**_gl_issue("B"), "epic": {"id": 42, "iid": 5}})
        out, ex, _flow = self._create("42", responses)
        self.assertEqual(out["parent"], "42")
        self.assertEqual(_create_json(ex),
                         {"title": "T", "description": "B", "epic_id": 42})
        self.assertEqual([c.op for c in ex.calls],
                         ["lifecycle-create"])

    def test_short_reference_resolves_in_the_projects_group(self) -> None:
        out, ex, _flow = self._create("&5", {
            "lifecycle-create-parent": ok({"id": 9005, "iid": 5}),
            **_create_responses("gitlab")})
        self.assertNotIsInstance(out, TrackerError)
        read = ex.calls[0]
        self.assertEqual(read.op, "lifecycle-create-parent")
        self.assertEqual(read.method, "GET")
        self.assertIn("groups/g/epics/5", read.url_or_argv)
        self.assertEqual(_create_json(ex)["epic_id"], 9005)
        self.assertEqual([c.op for c in ex.calls].count("lifecycle-create-parent"), 1)

    def test_full_reference_names_its_group(self) -> None:
        _out, ex, _flow = self._create("grp/sub&7", {
            "lifecycle-create-parent": ok({"id": 9007, "iid": 7}),
            **_create_responses("gitlab")})
        self.assertIn("groups/grp%2Fsub/epics/7", ex.calls[0].url_or_argv)
        self.assertEqual(_create_json(ex)["epic_id"], 9007)

    def test_value_that_is_no_epic_is_refused_before_any_request(self) -> None:
        out, ex, flow = self._create("g/p#3", {})
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
        self.assertEqual(out.subtype, "parent")
        self.assertEqual(ex.calls, [])
        self.assertIsNone(_saved(flow)["id"])

    def test_zero_epic_id_is_refused_not_sent_as_no_epic(self) -> None:
        for zero in ("0", "00"):
            with self.subTest(zero=zero):
                out, ex, flow = self._create(zero, {})
                self.assertIsInstance(out, TrackerError)
                self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
                self.assertEqual(ex.calls, [])
                self.assertIsNone(_saved(flow)["id"])

    def test_tier_without_epics_returns_gitlabs_error(self) -> None:
        out, ex, flow = self._create("&5", {
            "lifecycle-create-parent": rejected(
                "gitlab", 404, {"message": "404 Not found"})})
        self.assertIsInstance(out, TrackerError)
        self.assertNotIn("lifecycle-create", [c.op for c in ex.calls])
        self.assertIsNone(_saved(flow)["id"])

    def test_unknown_epic_id_returns_gitlabs_error_and_links_nothing(self) -> None:
        out, _ex, flow = self._create("4242", {
            "lifecycle-create": rejected(
                "gitlab", 404, {"message": "404 Epic Not Found"})})
        self.assertIsInstance(out, TrackerError)
        self.assertIsNone(_saved(flow)["id"])

    def test_epic_id_the_response_does_not_carry_is_reported_not_set(self) -> None:
        # fn-334 R8: GitLab may create the issue without the epic.
        for epic in (None, {"id": 7, "iid": 1}):
            with self.subTest(epic=epic):
                responses = _create_responses("gitlab")
                responses["lifecycle-create"] = ok({**_gl_issue("B"), "epic": epic})
                out, ex, _flow = self._create("42", responses)
                self.assertNotIsInstance(out, TrackerError, out)
                self.assertIsNone(out["parent"])
                self.assertEqual(out["degraded"]["kind"], "parent_not_set")
                self.assertEqual([c.op for c in ex.calls],
                                 ["lifecycle-create"])

    def test_digits_that_are_not_ascii_are_invalid_input(self) -> None:
        for parent in ("²", "４２", "٤٢"):
            with self.subTest(parent=parent), tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp) / ".flow"
                _write_flow(flow, gl_cfg())
                body = Path(tmp) / "b.md"
                body.write_text("B", encoding="utf-8")
                ex = fake_execute({})
                payload, _code = L.run(flow, "create", spec_id="fn-1-demo",
                                       title="T", body_file=str(body),
                                       parent=parent, execute=ex)
                self.assertEqual(json.loads(payload)["class"], "invalid_input", payload)
                self.assertEqual(ex.calls, [])


class RefusedParent(unittest.TestCase):
    """R3, R5: refused before any request, never dropped."""

    def _assert_refused(self, cfg: dict, *, word: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, cfg)
            ex = fake_execute({})
            out = L.create(flow, "fn-1-demo", title="T", body="B",
                           parent="X-1", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CAPABILITY)
            self.assertEqual(out.subtype, "parent")
            self.assertIn(word, out.message)
            self.assertEqual(ex.calls, [])
            self.assertFalse((flow / "create-first" / "spec-fn-1-demo.json").exists())

    def test_github_refuses(self) -> None:
        self._assert_refused(gh_cfg(), word="GitHub")

    def test_jira_data_center_refuses(self) -> None:
        self._assert_refused(jr_cfg(auth_scheme="bearer-pat"), word="Jira Cloud")


class ParentOption(unittest.TestCase):
    """`tracker create --parent` passes the parent at creation and does not store it."""

    def test_option_overrides_and_is_not_stored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg())
            body = Path(tmp) / "body.md"
            body.write_text("B", encoding="utf-8")
            ex = fake_execute(_create_responses("linear"))
            payload, code = L.run(flow, "create", spec_id="fn-1-demo", title="T",
                                  body_file=str(body), parent="WOR-40",
                                  execute=ex)
            self.assertEqual(code, 0, payload)
            self.assertEqual(json.loads(payload)["data"]["parent"], "WOR-40")
            self.assertEqual(_create_json(ex)["variables"]["input"]["parentId"],
                             "WOR-40")
            self.assertNotIn("parent", _saved(flow))

    def test_empty_option_is_invalid_input_before_any_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg())
            ex = fake_execute({})
            out = L.create(flow, "fn-1-demo", title="T", body="B", parent=" ",
                           execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
            self.assertEqual(ex.calls, [])


class CreateFirstParent(unittest.TestCase):
    def _flow(self, tmp: str, cfg: dict) -> Path:
        flow = Path(tmp) / ".flow"
        flow.mkdir()
        (flow / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
        return flow

    def test_parent_is_sent_reported_and_survives_a_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = self._flow(tmp, ln_cfg())
            key = L.compute_create_first_key("linear", "T", "B")
            ex = fake_execute({"lifecycle-create": ok({"data": {"issueCreate": {
                "success": True, "issue": _ln_issue("B")}}})})
            first = L.create_first(flow, title="T", body="B", retry_key=key,
                                   parent="WOR-40", execute=ex)
            self.assertEqual(first["parent"], "WOR-40")
            self.assertEqual(_create_json(ex)["variables"]["input"]["parentId"],
                             "WOR-40")

            again = fake_execute({})  # a second create would AssertionError
            second = L.create_first(flow, title="T", body="B", retry_key=key,
                                    parent="WOR-40", execute=again)
            self.assertTrue(second["retried"])
            self.assertEqual(second["id"], LN_UUID)
            self.assertEqual(second["parent"], "WOR-40")
            self.assertEqual(again.calls, [])

    def test_retry_under_another_parent_refuses_instead_of_adopting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = self._flow(tmp, ln_cfg())
            key = L.compute_create_first_key("linear", "T", "B")
            ex = fake_execute({"lifecycle-create": ok({"data": {"issueCreate": {
                "success": True, "issue": _ln_issue("B")}}})})
            L.create_first(flow, title="T", body="B", retry_key=key,
                           parent="WOR-10", execute=ex)
            for other in ("WOR-20", None):
                with self.subTest(other=other):
                    again = fake_execute({})
                    out = L.create_first(flow, title="T", body="B",
                                         retry_key=key, parent=other,
                                         execute=again)
                    self.assertIsInstance(out, TrackerError)
                    self.assertIs(out.cls, ErrorClass.CONFLICT)
                    self.assertEqual(out.subtype, "parent_mismatch")
                    self.assertEqual(out.details["recordedParent"], "WOR-10")
                    self.assertEqual(out.details["id"], LN_UUID)
                    self.assertEqual(again.calls, [])

    def test_retry_key_separates_parents_and_keeps_no_parent_keys(self) -> None:
        no_parent = L.compute_create_first_key("linear", "T", "B")
        self.assertEqual(L.compute_create_first_key("linear", "T", "B", None),
                         no_parent)
        under_10 = L.compute_create_first_key("linear", "T", "B", "WOR-10")
        under_20 = L.compute_create_first_key("linear", "T", "B", "WOR-20")
        self.assertEqual(len({no_parent, under_10, under_20}), 3)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".flow").mkdir()
            body = Path(tmp) / "b.md"
            body.write_text("B", encoding="utf-8")
            for parent, expected in ((None, no_parent), ("WOR-10", under_10)):
                argv = [sys.executable, str(FLOWCTL), "tracker", "create-first-key",
                        "--type", "linear", "--title", "T",
                        "--body-file", str(body), "--json"]
                if parent:
                    argv += ["--parent", parent]
                out = subprocess.run(argv, cwd=tmp, capture_output=True,
                                     text=True, encoding="utf-8")
                self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
                self.assertEqual(json.loads(out.stdout)["key"], expected)

    def test_retry_replays_a_parent_gitlab_did_not_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = self._flow(tmp, gl_cfg())
            key = L.compute_create_first_key("gitlab", "T", "B", "42")
            ex = fake_execute({"lifecycle-create": ok({**_gl_issue("B"), "epic": None})})
            first = L.create_first(flow, title="T", body="B", retry_key=key,
                                   parent="42", execute=ex)
            self.assertIsNone(first["parent"])
            again = L.create_first(flow, title="T", body="B", retry_key=key,
                                   parent="42", execute=fake_execute({}))
            self.assertTrue(again["retried"])
            self.assertIsNone(again["parent"])
            self.assertEqual(again["degraded"]["kind"], "parent_not_set")

    def test_github_create_first_refuses_before_any_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = self._flow(tmp, gh_cfg())
            key = L.compute_create_first_key("github", "T", "B")
            ex = fake_execute({})
            out = L.create_first(flow, title="T", body="B", retry_key=key,
                                 parent="#7", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CAPABILITY)
            self.assertEqual(ex.calls, [])
            self.assertFalse((flow / "create-first" / f"{key}.json").exists())


class LaterOperationsNeverSendTheParent(unittest.TestCase):
    """R8: once linked, status carries no parent field on any tracker."""

    LINKED = {
        "github": (GH_NODE, "#42", _gh_issue),
        "gitlab": (str(GL_ID), "g/p#12", _gl_issue),
        "linear": (LN_UUID, "WOR-17", _ln_issue),
        "jira": (JR_ID, "SCRUM-1", _jr_issue),
    }

    def _linked_flow(self, tmp: str, provider: str) -> Path:
        flow = Path(tmp)
        durable, display, _mk = self.LINKED[provider]
        _write_flow(flow, CFG[provider](), tracker={
            "id": durable, "identifier": display, "url": "https://x"})
        return flow

    def test_status_sends_no_parent(self) -> None:
        gh = dict(_gh_issue("B"), labels=[{"name": "status:todo"}])
        gl = dict(_gl_issue("B"), labels=["status:todo"])
        cases = {
            "github": {
                "status-parent-read": ok(gh),
                "status-set": ok(gh),
                "status-label-rm": empty(),
                "status-label-add": ok([{"name": "status:in-progress"}]),
                "status-label-readback": ok([{"name": "status:in-progress"}]),
            },
            "gitlab": {
                "status-parent-read": ok(gl),
                "status-set": ok(dict(gl, labels=["status:in_progress"])),
            },
            "linear": {
                "status-parent-read": ok({"data": {"issue": _ln_issue("B")}}),
                "status-state-read": ok({"data": {"issue": {
                    "id": LN_UUID, "state": {"id": "st-1", "name": "Todo",
                                             "type": "unstarted"}}}}),
                "status-set": ok({"data": {"issueUpdate": {
                    "success": True, "issue": {"id": LN_UUID}}}}),
            },
            "jira": {
                "status-parent-read": ok(_jr_issue("B")),
                "status-current": ok(_jr_issue("B")),
                "status-transitions": ok({"transitions": [
                    {"id": "11", "to": {"id": "2"}}]}),
                "status-set": empty(),
            },
        }
        for provider, responses in cases.items():
            with self.subTest(provider=provider), \
                    tempfile.TemporaryDirectory() as tmp:
                flow = self._linked_flow(tmp, provider)
                ex = fake_execute(responses)
                out = S.status(flow, "fn-1-demo", to="in_progress",
                               branch="fn-1-demo", execute=ex)
                self.assertEqual(out["kind"], "applied", f"{provider}: {out}")
                self.assertEqual(_sent_parent_keys(ex), [], provider)


if __name__ == "__main__":
    unittest.main()
