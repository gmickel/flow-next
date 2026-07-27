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
from flowctl_tracker.relate import providers as RP  # noqa: E402
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
            # Second call: presence is RE-PROBED (4-way rule) - ledger+remote
            # noops, and no mutation request is issued.
            listed = ok({"data": {"issue": {
                "id": LN_UUID,
                "relations": {"nodes": []},
                "inverseRelations": {"nodes": [
                    {"type": "blocks", "issue": {"id": LN_UUID_B}},
                ]},
            }}})
            ex2 = fake_execute({"relate-list": [listed]})
            second = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex2)
            self.assertEqual(second["kind"], "noop")
            self.assertEqual(second["key"], key)
            self.assertEqual([c.op for c in ex2.calls], ["relate-list"],
                             "probe only - never a second create")

    def test_completed_blocker_still_projects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr,
                        b_status="done")
            # fn-64 (docs/tracker-sync.md): a completed blocker stays VISIBLE
            # on the tracker; only readiness gating treats it as satisfied.
            list_empty = ok({"data": {"issue": {
                "id": LN_UUID,
                "relations": {"nodes": []},
                "inverseRelations": {"nodes": []},
            }}})
            create = ok({"data": {"issueRelationCreate": {
                "success": True, "issueRelation": {"id": "rel-1"}}}})
            ex = fake_execute({"relate-list": [list_empty],
                               "relate-create": create})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
            self.assertEqual(out["kind"], "applied")
            self.assertTrue(out["completed_blocker"],
                            "annotated for readiness, still projected")

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
            self.assertEqual(out["kind"], "queued")
            self.assertEqual(out["reason"], "foreign_edge")
            # Ledger untouched; conflict QUEUED to the deferred-decisions sink.
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            self.assertEqual(spec["tracker"].get("depRelations") or [], [])
            sink = flow / "review-deferred" / "tracker-relate.md"
            self.assertTrue(sink.is_file())
            self.assertIn("foreign-edge", sink.read_text(encoding="utf-8"))
            receipts = _receipts(flow)
            self.assertTrue(any(r.get("status") == "queued" for r in receipts))


class LinearRelateProbeDrain(unittest.TestCase):
    """The probe drains BOTH relation connections before concluding absence."""

    def test_edge_on_second_page_is_found(self) -> None:
        # Page 1: no matching edge, inverseRelations reports hasNextPage.
        page1 = ok({"data": {"issue": {
            "id": LN_UUID,
            "relations": {"nodes": [],
                          "pageInfo": {"hasNextPage": False, "endCursor": None}},
            "inverseRelations": {
                "nodes": [{"type": "blocks", "issue": {"id": "other-uuid"}}],
                "pageInfo": {"hasNextPage": True, "endCursor": "cur-1"}},
        }}})
        page2 = ok({"data": {"issue": {
            "id": LN_UUID,
            "relations": {"nodes": [],
                          "pageInfo": {"hasNextPage": False, "endCursor": None}},
            "inverseRelations": {
                "nodes": [{"type": "blocks", "issue": {"id": LN_UUID_B}}],
                "pageInfo": {"hasNextPage": False, "endCursor": "cur-2"}},
        }}})
        ex = fake_execute({"relate-list": [page1, page2]})
        out = RP._linear_edge_exists(ex, LN_UUID, LN_UUID_B)
        self.assertIs(out, True)
        self.assertEqual([c.op for c in ex.calls],
                         ["relate-list", "relate-list"],
                         "cursor drain issues a second page request")

    def test_truncated_at_cap_does_not_report_absence(self) -> None:
        # Every page claims more with a fresh cursor; the edge never appears.
        counter = {"n": 0}

        def endless(_request):
            counter["n"] += 1
            return ok({"data": {"issue": {
                "id": LN_UUID,
                "relations": {"nodes": [],
                              "pageInfo": {"hasNextPage": False,
                                           "endCursor": None}},
                "inverseRelations": {
                    "nodes": [{"type": "blocks",
                               "issue": {"id": f"uuid-{counter['n']}"}}],
                    "pageInfo": {"hasNextPage": True,
                                 "endCursor": f"cur-{counter['n']}"}},
            }}})

        ex = fake_execute({"relate-list": endless})
        out = RP._linear_edge_exists(ex, LN_UUID, LN_UUID_B)
        self.assertIsInstance(out, TrackerError,
                              "a probe that cannot prove absence must not "
                              "report absence")
        self.assertEqual(out.cls, ErrorClass.TRANSPORT)
        self.assertEqual(out.subtype, "truncated")
        self.assertEqual(len(ex.calls), W._MAX_PAGES)

    def test_single_page_absence_still_reports_false(self) -> None:
        # Both connections exhausted on page 1 → honest False, one request.
        page = ok({"data": {"issue": {
            "id": LN_UUID,
            "relations": {"nodes": []},
            "inverseRelations": {"nodes": []},
        }}})
        ex = fake_execute({"relate-list": [page]})
        out = RP._linear_edge_exists(ex, LN_UUID, LN_UUID_B)
        self.assertIs(out, False)
        self.assertEqual(len(ex.calls), 1)


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
                "wire-relate-probe": ok([]),
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


class Round1HostFixes(unittest.TestCase):
    def test_linear_attach_get_refuses_untrusted_origins(self) -> None:
        """The retrieval carries LINEAR_API_KEY - an arbitrary URL is a
        credential-exfiltration primitive."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_pair(flow, ln_cfg())
            from flowctl_tracker import attach as A
            cfg = json.loads((flow / "config.json").read_text())
            ex = fake_execute({})  # any request would AssertionError
            for url in ("https://attacker.example/x",
                        "http://uploads.linear.app/x",
                        "https://uploads.linear.app.evil.com/x"):
                with self.subTest(url=url):
                    out = A.attach_get(cfg, attachment_id=url,
                                       out_path=str(Path(tmp) / "out.bin"),
                                       execute=ex)
                    self.assertIsInstance(out, TrackerError)
                    self.assertEqual(out.subtype, "untrusted_origin")
            self.assertEqual(ex.calls, [], "no request may leave the process")

    def test_multipart_boundary_never_collides_with_payload(self) -> None:
        from flowctl_tracker.attach import providers as AP
        evil = b"x" * 10
        body, ctype = AP._multipart("f.bin", evil)
        boundary = ctype.split("boundary=")[-1]
        # adversarial: payload CONTAINING a candidate boundary still round-trips
        body2, ctype2 = AP._multipart("f.bin", boundary.encode() + b"tail")
        b2 = ctype2.split("boundary=")[-1]
        self.assertNotIn(b2.encode(), boundary.encode() + b"tail")
        self.assertIn(evil, body)

    def test_human_removed_edge_is_queued_not_recreated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            key = R.dep_relation_key(LN_UUID, LN_UUID_B)
            a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                    "linkState": "linked",
                    "depRelations": [{"key": key, "dep_spec": "fn-2-dep",
                                      "from_tracker_id": LN_UUID,
                                      "to_tracker_id": LN_UUID_B,
                                      "type": "blocks", "source": "flow",
                                      "updatedAt": "2026-01-01T00:00:00Z"}]}
            b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            # Remote edge GONE (human removed it) while our ledger has it.
            listed = ok({"data": {"issue": {
                "id": LN_UUID,
                "relations": {"nodes": []},
                "inverseRelations": {"nodes": []},
            }}})
            ex = fake_execute({"relate-list": [listed]})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
            self.assertEqual(out["kind"], "queued")
            self.assertEqual(out["reason"], "human_removed_edge")
            self.assertEqual([c.op for c in ex.calls], ["relate-list"],
                             "default NOT re-created - no mutation issued")
            sink = flow / "review-deferred" / "tracker-relate.md"
            self.assertIn("removed", sink.read_text(encoding="utf-8"))


class Round2HostFixes(unittest.TestCase):
    def test_jira_relate_probe_and_create(self) -> None:
        """The probe signature bug made EVERY jira relate raise TypeError."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": "10042", "identifier": "SCRUM-1", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": "10043", "identifier": "SCRUM-2", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, jr_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            probe = ok({"fields": {"issuelinks": []}})
            ex = fake_execute({"relate-list": [probe], "relate-create": ok(None)})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["kind"], "applied")
            self.assertEqual(out["form"], "blocks")
            # Idempotency: ledger + remote-present -> noop, no create.
            present = ok({"fields": {"issuelinks": [
                {"type": {"name": "Blocks"},
                 "inwardIssue": {"id": "10042"},
                 "outwardIssue": {"id": "10043"}}]}})
            ex2 = fake_execute({"relate-list": [present]})
            again = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex2)
            self.assertEqual(again["kind"], "noop")

    def test_concurrent_relates_lose_no_ledger_entry(self) -> None:
        """Barrier-driven: two relates to different deps race; both entries
        must survive (serialized by the shared .flow writer lock)."""
        import threading
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            # third spec as a second dep target
            c_id = "cccccccc-1111-2222-3333-444444444444"
            (flow / "specs" / "fn-3-dep2.json").write_text(json.dumps({
                "id": "fn-3-dep2", "status": "open",
                "tracker": {"id": c_id, "identifier": "WOR-19", "url": "u",
                            "linkState": "linked", "depRelations": []}}),
                encoding="utf-8")
            barrier = threading.Barrier(2)
            results = {}

            def go(dep, uuid):
                empty = ok({"data": {"issue": {"id": LN_UUID,
                            "relations": {"nodes": []},
                            "inverseRelations": {"nodes": []}}}})
                create = ok({"data": {"issueRelationCreate": {
                    "success": True, "issueRelation": {"id": f"rel-{dep}"}}}})

                def execute(request):
                    if request.op == "relate-list":
                        barrier.wait(timeout=10)  # both probe pre-write state
                        return empty
                    return create
                results[dep] = R.relate(flow, "fn-1-demo", blocked_by=dep,
                                        execute=execute)

            t1 = threading.Thread(target=go, args=("fn-2-dep", LN_UUID_B))
            t2 = threading.Thread(target=go, args=("fn-3-dep2", c_id))
            t1.start(); t2.start(); t1.join(); t2.join()
            for dep, out in results.items():
                self.assertNotIsInstance(out, TrackerError, (dep, out))
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            keys = {e["dep_spec"] for e in spec["tracker"]["depRelations"]}
            self.assertEqual(keys, {"fn-2-dep", "fn-3-dep2"},
                             "a lost update dropped a ledger entry")


class RelateLedgerDurability(unittest.TestCase):
    """Two-phase intent write (PR #246 review): a ledger failure AFTER the
    provider create must not orphan ownership - the pending entry keeps the
    edge OURS, so a retry heals instead of queueing a false foreign collision."""

    def _pair(self, flow: Path) -> None:
        a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                "depRelations": [], "linkState": "linked"}
        b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                "depRelations": [], "linkState": "linked"}
        _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)

    @staticmethod
    def _list_empty():
        return ok({"data": {"issue": {
            "id": LN_UUID,
            "relations": {"nodes": []},
            "inverseRelations": {"nodes": []},
        }}})

    @staticmethod
    def _list_present():
        return ok({"data": {"issue": {
            "id": LN_UUID,
            "relations": {"nodes": []},
            "inverseRelations": {"nodes": [
                {"type": "blocks", "issue": {"id": LN_UUID_B}},
            ]},
        }}})

    @staticmethod
    def _create_ok():
        return ok({"data": {"issueRelationCreate": {
            "success": True, "issueRelation": {"id": "rel-1"}}}})

    def test_finalize_failure_is_recoverable_and_retry_heals(self) -> None:
        from unittest import mock
        from flowctl_tracker.lifecycle.helpers import (
            write_tracker_block as real_wtb,
        )
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair(flow)
            ex = fake_execute({"relate-list": [self._list_empty()],
                               "relate-create": self._create_ok()})
            calls = {"n": 0}

            def flaky(path, spec, tracker):
                calls["n"] += 1
                if calls["n"] == 2:  # the FINALIZE write, after the create
                    return TrackerError(ErrorClass.TRANSPORT, "disk full",
                                        subtype="write")
                return real_wtb(path, spec, tracker)

            with mock.patch.object(R, "write_tracker_block", flaky):
                out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                               execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertEqual(out.subtype, "ledger_finalize")
            self.assertTrue((out.details or {}).get("recoverable"))
            self.assertEqual((out.details or {}).get("completed_steps"),
                             ["relate-create"])
            # Ownership is durable: the pending entry landed BEFORE the create.
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            entries = spec["tracker"]["depRelations"]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["status"], "pending")

            # RETRY: pending + remote-present -> heal the ledger; never a
            # duplicate create, never a foreign-edge collision.
            ex2 = fake_execute({"relate-list": [self._list_present()]})
            again = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                             execute=ex2)
            self.assertNotIsInstance(again, TrackerError, msg=repr(again))
            self.assertEqual(again["kind"], "applied")
            self.assertEqual(again["reason"], "ledger_repaired")
            self.assertEqual([c.op for c in ex2.calls], ["relate-list"],
                             "probe only - never a second create")
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            entries = spec["tracker"]["depRelations"]
            self.assertEqual(len(entries), 1)
            self.assertNotIn("status", entries[0],
                             "finalized entry matches the fn-64 shape")
            self.assertFalse(
                (flow / "review-deferred" / "tracker-relate.md").exists(),
                "no false collision queued")

    def test_create_failure_leaves_pending_and_retry_creates_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair(flow)
            boom = ok({"data": {"issueRelationCreate": {"success": False}}})
            ex = fake_execute({"relate-list": [self._list_empty()],
                               "relate-create": boom})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
            self.assertIsInstance(out, TrackerError)
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            entries = spec["tracker"]["depRelations"]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["status"], "pending")

            # RETRY: pending + remote-absent -> the create is retried; the
            # idempotent append never duplicates the ledger entry.
            ex2 = fake_execute({"relate-list": [self._list_empty()],
                                "relate-create": self._create_ok()})
            again = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                             execute=ex2)
            self.assertNotIsInstance(again, TrackerError, msg=repr(again))
            self.assertEqual(again["kind"], "applied")
            self.assertIn("relate-create", [c.op for c in ex2.calls])
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            entries = spec["tracker"]["depRelations"]
            self.assertEqual(len(entries), 1)
            self.assertNotIn("status", entries[0])
