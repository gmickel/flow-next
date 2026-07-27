"""Capabilities: attachments, relations, tier degradation (fn-140.4).

Fake transport = injected executor seam. Every acceptance bullet has a test.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import relate as R  # noqa: E402
from flowctl_tracker import wire as W  # noqa: E402
from flowctl_tracker.classify import classify  # noqa: E402
from flowctl_tracker.relate.ledger import (  # noqa: E402
    FLOW_DEPS_CLOSE, FLOW_DEPS_OPEN, dep_relation_key,
)
from flowctl_tracker.types import (  # noqa: E402
    CredentialPolicy, ErrorClass, Response, TrackerError,
)


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


GH_NODE = "I_kwDOTestNode1"
GH_NODE_B = "I_kwDOTestNode2"
GL_ID = "84817009"
GL_ID_B = "84817010"
LN_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
LN_UUID_B = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
JR_ID = "10042"
JR_ID_B = "10043"
PAYLOAD = b"hello-attach-bytes-fn140"


def gh_cfg(**extra) -> dict:
    caps = {"attachments": False, "blockedBy": False, "subIssues": True,
            "deleteIssue": False}
    caps.update(extra.pop("caps", {}))
    return {"tracker": {"type": "github",
                        "resolved": {"destination": {"owner": "o", "repo": "r"},
                                     "capabilities": caps}}}


def gl_cfg(*, blocked_by=True, plan="ultimate") -> dict:
    return {"tracker": {"type": "gitlab",
                        "perTracker": {"project": "g/p", "host": "gitlab.com"},
                        "resolved": {"destination": {
                            "projectId": 1, "projectPath": "g/p",
                            "host": "gitlab.com", "namespaceId": 9},
                            "capabilities": {
                                "attachments": True, "blockedBy": blocked_by,
                                "subIssues": False, "deleteIssue": True,
                                "_source": {"gitlabPlan": plan}}}}}


def ln_cfg() -> dict:
    return {"tracker": {"type": "linear",
                        "perTracker": {"teamId": "team-1"},
                        "resolved": {"destination": {
                            "teamId": "team-1", "teamKey": "WOR",
                            "labelIds": {"bug": "lbl-1"},
                            "stateIds": {}},
                            "capabilities": {
                                "attachments": True, "blockedBy": True,
                                "subIssues": False, "deleteIssue": True}}}}


def jr_cfg() -> dict:
    return {"tracker": {"type": "jira",
                        "perTracker": {"baseUrl": "https://ex.atlassian.net",
                                       "projectKey": "SCRUM"},
                        "resolved": {"destination": {
                            "baseUrl": "https://ex.atlassian.net",
                            "projectKey": "SCRUM", "projectId": "10000",
                            "issueTypeId": "10001", "apiVersion": 2,
                            "style": "classic", "statusIds": {}},
                            "capabilities": {
                                "attachments": True, "blockedBy": True,
                                "subIssues": False, "deleteIssue": True}}}}


def _write_pair(flow: Path, config: dict, *, a_id="fn-1-demo", b_id="fn-2-dep",
                a_tracker=None, b_tracker=None, b_status="open") -> None:
    (flow / "specs").mkdir(parents=True, exist_ok=True)
    (flow / "config.json").write_text(json.dumps(config), encoding="utf-8")
    for sid, tr, st in (
        (a_id, a_tracker, "open"),
        (b_id, b_tracker, b_status),
    ):
        spec = {
            "id": sid, "title": sid, "status": st, "branch_name": sid,
            "tracker": tr or {"id": None, "identifier": None, "url": None,
                              "depRelations": [], "linkState": "unlinked"},
        }
        (flow / "specs" / f"{sid}.json").write_text(
            json.dumps(spec, indent=2) + "\n", encoding="utf-8")


def _receipts(flow: Path) -> list[dict]:
    runs = flow / "sync-runs"
    if not runs.is_dir():
        return []
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(runs.glob("sync-*.json"))]


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------

class GithubAttachmentsCapability(unittest.TestCase):
    def test_attach_gated_before_any_request(self) -> None:
        ex = fake_execute({})
        out = W.dispatch("attach", gh_cfg(), locator=loc(GH_NODE, "#42"),
                         file_path=__file__, execute=ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.CAPABILITY)
        self.assertEqual(out.details.get("capability"), "attachments")
        self.assertIn("commit", out.message.lower())
        self.assertEqual(out.details.get("workaround"), "commit-and-link")
        self.assertEqual(ex.calls, [])


class JiraAttachRoundTrip(unittest.TestCase):
    def test_upload_and_byte_identical_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.bin"
            src.write_bytes(PAYLOAD)
            out_path = Path(tmp) / "out.bin"
            parent = {"id": JR_ID, "key": "SCRUM-1",
                      "fields": {"summary": "T", "description": "B"}}
            ex = fake_execute({
                "wire-parent-read": ok(parent),
                "wire-attach": ok([{"id": "att-9",
                                    "content": "https://ex.atlassian.net/secure/attachment/att-9/in.bin"}]),
                "wire-attach-get": ok(PAYLOAD),
            })
            up = W.dispatch("attach", jr_cfg(), locator=loc(JR_ID, "SCRUM-1"),
                            file_path=str(src), execute=ex)
            self.assertNotIsInstance(up, TrackerError)
            self.assertEqual(up["sha256"], hashlib.sha256(PAYLOAD).hexdigest())
            self.assertEqual(up["id"], "att-9")
            # XSRF header must be present on the upload request.
            attach_req = next(c for c in ex.calls if c.op == "wire-attach")
            self.assertEqual(attach_req.headers.get("X-Atlassian-Token"), "no-check")

            down = W.dispatch("attach-get", jr_cfg(), attachment_id=up["id"],
                              out_path=str(out_path), execute=ex)
            self.assertNotIsInstance(down, TrackerError)
            self.assertEqual(down["sha256"], up["sha256"])
            self.assertEqual(out_path.read_bytes(), PAYLOAD)

    def test_xsrf_404_surfaced_as_auth_shape_not_not_found(self) -> None:
        # Classifier path: 404 + XSRF body → INVALID_INPUT/xsrf, never NOT_FOUND.
        resp = Response(404, {}, b"XSRF check failed for request", 0.01)
        err = classify("jira", resp)
        self.assertIsInstance(err, TrackerError)
        self.assertIs(err.cls, ErrorClass.INVALID_INPUT)
        self.assertEqual(err.subtype, "xsrf")
        self.assertIn("X-Atlassian-Token", err.message)
        self.assertIsNot(err.cls, ErrorClass.NOT_FOUND)

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.bin"
            src.write_bytes(PAYLOAD)
            parent = {"id": JR_ID, "key": "SCRUM-1", "fields": {}}
            ex = fake_execute({
                "wire-parent-read": ok(parent),
                "wire-attach": resp,
            })
            out = W.dispatch("attach", jr_cfg(), locator=loc(JR_ID, "SCRUM-1"),
                             file_path=str(src), execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
            self.assertEqual(out.subtype, "xsrf")


class LinearAttachPresigned(unittest.TestCase):
    def test_presigned_put_anonymous_retrieval_with_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "shot.png"
            src.write_bytes(PAYLOAD)
            out_path = Path(tmp) / "got.png"
            asset = "https://uploads.linear.app/asset/abc"
            upload_url = "https://storage.example/presigned"
            parent = {"id": LN_UUID, "identifier": "WOR-17", "title": "T",
                      "description": "B", "labels": {"nodes": []}}
            ex = fake_execute({
                "wire-parent-read": ok({"data": {"issue": parent}}),
                "wire-attach-fileUpload": ok({"data": {"fileUpload": {
                    "success": True,
                    "uploadFile": {
                        "uploadUrl": upload_url,
                        "assetUrl": asset,
                        "headers": [{"key": "x-goog-content-length-range",
                                     "value": f"{len(PAYLOAD)},{len(PAYLOAD)}"}],
                    }}}}),
                "wire-attach-presigned-put": ok(b""),
                "wire-attach-create": ok({"data": {"attachmentCreate": {
                    "success": True, "attachment": {"id": "att-1", "url": asset}}}}),
                "wire-attach-get": ok(PAYLOAD),
            })
            # Linear parent_read goes through _gql which expects GraphQL envelope;
            # wire parent_read for linear uses _gql internally - our fake returns
            # Response; _gql json-loads. Provide GraphQL shape above.
            # But parent_read in attach uses wire.parent_read → linear.parent_read
            # which uses _gql. Good.
            up = W.dispatch("attach", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                            file_path=str(src), execute=ex)
            self.assertNotIsInstance(up, TrackerError, msg=repr(up))
            put = next(c for c in ex.calls if c.op == "wire-attach-presigned-put")
            self.assertIs(put.credential_policy, CredentialPolicy.PRESIGNED_ANONYMOUS)
            # No auth kwarg leakage on the Request object.
            self.assertNotIn("authorization", {k.lower() for k in put.headers})
            self.assertNotIn("Authorization", put.headers)
            self.assertEqual(put.body, PAYLOAD)
            self.assertEqual(put.url_or_argv, upload_url)

            down = W.dispatch("attach-get", ln_cfg(), attachment_id=up["id"],
                              out_path=str(out_path), execute=ex)
            self.assertNotIsInstance(down, TrackerError)
            get = next(c for c in ex.calls if c.op == "wire-attach-get")
            self.assertIs(get.credential_policy, CredentialPolicy.PROVIDER_AUTH)
            self.assertEqual(down["sha256"], up["sha256"])
            self.assertEqual(out_path.read_bytes(), PAYLOAD)


class GitlabAttachHttp(unittest.TestCase):
    def test_upload_uses_http_multipart_never_glab_argv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "f.txt"
            src.write_bytes(PAYLOAD)
            out_path = Path(tmp) / "got.txt"
            parent = {"id": int(GL_ID), "iid": 12, "title": "T",
                      "description": "B", "labels": []}
            ex = fake_execute({
                "wire-parent-read": ok(parent),
                "upload": ok({"id": 77, "url": "/uploads/secret/f.txt",
                              "markdown": "![f](/uploads/secret/f.txt)"}),
                "wire-attach-get": ok(PAYLOAD),
            })
            up = W.dispatch("attach", gl_cfg(), locator=loc(GL_ID, "g/p#12"),
                            file_path=str(src), execute=ex)
            self.assertNotIsInstance(up, TrackerError, msg=repr(up))
            upload_req = next(c for c in ex.calls if c.op == "upload")
            # HTTP route: url string, NOT argv list.
            self.assertIsInstance(upload_req.url_or_argv, str)
            self.assertIn("/projects/1/uploads", upload_req.url_or_argv)
            self.assertNotIsInstance(upload_req.url_or_argv, list)
            self.assertIn("multipart/form-data", upload_req.headers.get("Content-Type", ""))

            down = W.dispatch("attach-get", gl_cfg(), attachment_id=up["id"],
                              out_path=str(out_path), execute=ex)
            self.assertNotIsInstance(down, TrackerError)
            get = next(c for c in ex.calls if c.op == "wire-attach-get")
            self.assertIsInstance(get.url_or_argv, str)
            self.assertIn("/uploads/77", get.url_or_argv)
            self.assertNotIn("/uploads/secret/", get.url_or_argv)
            self.assertEqual(down["sha256"], up["sha256"])


# ---------------------------------------------------------------------------
# Relate
# ---------------------------------------------------------------------------

class RelateLedger(unittest.TestCase):
    def test_edge_key_matches_flowctl_semantics(self) -> None:
        # Same directed pair → same 16-hex key; order matters.
        a = dep_relation_key("from-1", "to-2")
        b = dep_relation_key("from-1", "to-2")
        c = dep_relation_key("to-2", "from-1")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(len(a), 16)
        self.assertTrue(FLOW_DEPS_OPEN.startswith("<!--"))
        self.assertIn("flow:deps", FLOW_DEPS_CLOSE)

    def test_idempotent_second_call_noops(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            list_empty = ok({"data": {"issue": {
                "id": LN_UUID,
                "relations": {"nodes": []},
                "inverseRelations": {"nodes": []},
            }}})
            create = ok({"data": {"issueRelationCreate": {
                "success": True, "issueRelation": {"id": "rel-1"}}}})
            ex = fake_execute({
                "relate-list": [list_empty],
                "relate-create": create,
            })
            first = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
            self.assertEqual(first["kind"], "applied")
            key = first["key"]
            # Second call: ledger hit → noop, no further network.
            ex2 = fake_execute({})
            second = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex2)
            self.assertEqual(second["kind"], "noop")
            self.assertEqual(second["key"], key)
            self.assertEqual(ex2.calls, [])

    def test_completed_blocker_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr,
                        b_status="done")
            ex = fake_execute({})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
            self.assertEqual(out["kind"], "skipped")
            self.assertEqual(out["reason"], "completed_blocker")
            self.assertEqual(ex.calls, [])
            receipts = _receipts(flow)
            self.assertTrue(any(r.get("status") == "noop" for r in receipts))

    def test_foreign_edge_defers_never_clobber(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            # Tracker already has the edge; ledger does not → foreign → defer.
            listed = ok({"data": {"issue": {
                "id": LN_UUID,
                "relations": {"nodes": []},
                "inverseRelations": {"nodes": [
                    {"type": "blocks", "issue": {"id": LN_UUID_B}},
                ]},
            }}})
            ex = fake_execute({"relate-list": listed})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
            self.assertEqual(out["kind"], "defer")
            self.assertEqual(out["reason"], "foreign_edge")
            # Ledger untouched.
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            self.assertEqual(spec["tracker"].get("depRelations") or [], [])


class GitlabRelateDegrade(unittest.TestCase):
    def test_free_tier_relates_to_with_structured_degraded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": GL_ID, "identifier": "g/p#12", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": GL_ID_B, "identifier": "g/p#13", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, gl_cfg(blocked_by=False, plan="free"),
                        a_tracker=a_tr, b_tracker=b_tr)
            ex = fake_execute({
                "relate-list": ok([]),
                "relate-create": ok({"id": 1, "link_type": "relates_to"}),
            })
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
            self.assertEqual(out["kind"], "applied")
            self.assertEqual(out["form"], "relates_to")
            self.assertIsInstance(out.get("degraded"), dict)
            self.assertEqual(out["degraded"]["kind"], "relates_to")
            self.assertEqual(out["degraded"]["plan"], "free")
            create = next(c for c in ex.calls if c.op == "relate-create")
            body = json.loads(create.body.decode())
            self.assertEqual(body["link_type"], "relates_to")


class GithubSubIssuesHierarchy(unittest.TestCase):
    def test_sub_issues_reported_as_hierarchy_never_blocked_by(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": GH_NODE, "identifier": "#42", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": GH_NODE_B, "identifier": "#43", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, gh_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            ex = fake_execute({
                "relate-child-read": ok({
                    "id": 999001, "node_id": GH_NODE, "number": 42}),
                "relate-list": ok([]),
                "relate-create": ok({"id": 999001}),
            })
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
            self.assertEqual(out["kind"], "applied")
            self.assertEqual(out["form"], "sub_issues")
            self.assertEqual(out["degraded"]["kind"], "hierarchy")
            self.assertEqual(out["degraded"]["form"], "sub_issues")
            self.assertNotIn("blocked-by", out["form"])
            self.assertIn("never blocked-by", out["degraded"]["note"])
            create = next(c for c in ex.calls if c.op == "relate-create")
            # Parent is the BLOCKER (#43); child is the blocked (#42).
            argv = list(create.url_or_argv)
            if len(argv) >= 2 and argv[-2:] == ["--input", "-"]:
                argv = argv[:-2]
            self.assertIn("/issues/43/sub_issues", argv[-1])
            body = json.loads(create.body.decode())
            self.assertEqual(body["sub_issue_id"], 999001)


# ---------------------------------------------------------------------------
# Label auto-create + single-assignee replace (R15)
# ---------------------------------------------------------------------------

class LinearLabelAutoCreate(unittest.TestCase):
    def test_unknown_label_auto_created(self) -> None:
        parent = {"id": LN_UUID, "identifier": "WOR-17", "title": "T",
                  "description": "B", "url": "u",
                  "labels": {"nodes": [{"id": "lbl-1", "name": "bug"}]}}
        ex = fake_execute({
            "wire-parent-read": ok({"data": {"issue": parent}}),
            "wire-label-create": ok({"data": {"issueLabelCreate": {
                "success": True,
                "issueLabel": {"id": "lbl-new", "name": "urgent"}}}}),
            "wire-label": ok({"data": {"issueUpdate": {
                "success": True,
                "issue": {**parent, "labels": {"nodes": [
                    {"id": "lbl-1", "name": "bug"},
                    {"id": "lbl-new", "name": "urgent"},
                ]}}}}}),
        })
        out = W.dispatch("label", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                         add=["urgent"], execute=ex)
        self.assertNotIsInstance(out, TrackerError, msg=repr(out))
        self.assertIn("urgent", out.get("labels_created", []))
        create = next(c for c in ex.calls if c.op == "wire-label-create")
        self.assertTrue(create.body)


class SingleAssigneeReplace(unittest.TestCase):
    def test_linear_replace_reports_degraded(self) -> None:
        parent = {"id": LN_UUID, "identifier": "WOR-17", "title": "T",
                  "description": "B", "url": "u",
                  "labels": {"nodes": []},
                  "assignee": {"id": "user-1", "name": "Ada"}}
        ex = fake_execute({
            "wire-parent-read": ok({"data": {"issue": parent}}),
            "wire-assign": ok({"data": {"issueUpdate": {
                "success": True,
                "issue": {**parent, "assignee": {"id": "user-2", "name": "Bea"}}}}}),
        })
        out = W.dispatch("assign", ln_cfg(), locator=loc(LN_UUID, "WOR-17"),
                         add=["user-2"], execute=ex)
        self.assertNotIsInstance(out, TrackerError)
        deg = out.get("degraded")
        self.assertIsInstance(deg, dict)
        self.assertEqual(deg["kind"], "assignee_replaced")
        self.assertEqual(deg["previous"], "user-1")
        self.assertEqual(deg["applied"], "user-2")

    def test_jira_replace_reports_degraded(self) -> None:
        parent = {"id": JR_ID, "key": "SCRUM-1",
                  "fields": {"summary": "T", "description": "B",
                             "labels": [],
                             "assignee": {"accountId": "acct-old"}}}
        ex = fake_execute({
            "wire-parent-read": ok(parent),
            "wire-assign": empty(),
        })
        out = W.dispatch("assign", jr_cfg(), locator=loc(JR_ID, "SCRUM-1"),
                         add=["acct-new-12345678901234567890"], execute=ex)
        self.assertNotIsInstance(out, TrackerError)
        deg = out.get("degraded")
        self.assertEqual(deg["kind"], "assignee_replaced")
        self.assertEqual(deg["previous"], "acct-old")


class UnresolvedRelate(unittest.TestCase):
    def test_identifier_only_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": None, "identifier": "WOR-17", "url": None,
                    "depRelations": [], "linkState": "identifier_only"}
            b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=fake_execute({}))
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.UNRESOLVED)
            self.assertEqual(out.subtype, "identifier_only")


if __name__ == "__main__":
    unittest.main()
