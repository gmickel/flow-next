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
                "relate-parent-read": [ok({"id": int(GL_ID), "iid": 12}),
                                       ok({"id": int(GL_ID_B), "iid": 13})],
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
                "relate-parent-read": [
                    ok({"id": 999001, "node_id": GH_NODE, "number": 42}),
                    ok({"id": 999002, "node_id": GH_NODE_B, "number": 43})],
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
            # Epic contract: the receipt note never carries a degradation
            # sentence - degradation lives exclusively in the structured
            # `degraded` field. The note stays a neutral record of what
            # landed (and never presents sub_issues as blocked-by, R15).
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            note = receipts[0]["note"] or ""
            self.assertNotIn("degraded", note.lower())
            self.assertNotIn("blocked-by", note)
            self.assertIn("sub_issues", note)
            self.assertEqual(receipts[0]["degraded"]["kind"], "hierarchy")
            self.assertEqual(receipts[0]["degraded"]["form"], "sub_issues")
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
            "wire-label-team-lookup": ok({"data": {"team": {"labels": {
                "nodes": [],
                "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}),
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

    def test_linear_attach_get_malformed_url_rejected_without_raising(self) -> None:
        """urlparse raises ValueError on input like "https://["; wire.run has
        no exception guard, so the reject must happen at the validation
        boundary and fail CLOSED - structured invalid-input envelope, never a
        traceback, never an allowlist bypass."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_pair(flow, ln_cfg())
            from flowctl_tracker import attach as A
            cfg = json.loads((flow / "config.json").read_text())
            ex = fake_execute({})  # any request would AssertionError
            # Direct validation boundary: TrackerError, not ValueError.
            out = A.attach_get(cfg, attachment_id="https://[",
                               out_path=str(flow / "out.bin"), execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
            self.assertEqual(out.subtype, "untrusted_origin")
            # Unguarded wire.run route: structured envelope, no exception.
            payload, code = W.run(flow, "attach-get",
                                  attachment_id="https://[",
                                  out_path=str(flow / "out.bin"), execute=ex)
            env = json.loads(payload)
            self.assertFalse(env["success"])
            self.assertEqual(env["class"], "invalid_input")
            self.assertNotEqual(code, 0)
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
            # GET issuelinks on blocked A carries only the OTHER issue:
            # blocker B (10043) in inwardIssue (jira.md listIssueRelations).
            present = ok({"fields": {"issuelinks": [
                {"type": {"name": "Blocks"},
                 "inwardIssue": {"id": "10043"}}]}})
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

    def test_create_failure_releases_claim_and_retry_creates_once(self) -> None:
        # PR #246 review wave 6: a DEFINITE create failure (parsed rejection,
        # known not to have landed) RELEASES the pending claim - wave 1 left
        # it behind, which made an immediate retry under a new pid fail
        # concurrent_claim for the full stale window. Ambiguous transport
        # failures still keep the entry (RelatePendingClaim covers that).
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair(flow)
            boom = ok({"data": {"issueRelationCreate": {"success": False}}})
            ex = fake_execute({"relate-list": [self._list_empty()],
                               "relate-create": boom})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
            self.assertIsInstance(out, TrackerError)
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            self.assertEqual(spec["tracker"]["depRelations"], [],
                             "definite not-landed failure releases the claim")

            # RETRY: entry absent + remote-absent -> a clean create; the
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


class RelateDisplayDurableGuard(unittest.TestCase):
    """PR #246 review: GitHub/GitLab relate paths address issues by DISPLAY
    (number/IID). Both display locators must be validated against the linked
    durable ids BEFORE any probe or mutation - a moved, repointed, or stale
    identifier aborts instead of relating unrelated issues (wire parity)."""

    def test_gitlab_stale_display_aborts_before_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": GL_ID, "identifier": "g/p#12", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": GL_ID_B, "identifier": "g/p#13", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, gl_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            # IID 12 now resolves to a DIFFERENT issue (destination move /
            # repoint / stale stored identifier).
            ex = fake_execute({
                "relate-parent-read": [ok({"id": 555000, "iid": 12})],
            })
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "durable_mismatch")
            self.assertEqual([c.op for c in ex.calls], ["relate-parent-read"],
                             "abort BEFORE any probe or mutation request")
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            self.assertEqual(spec["tracker"].get("depRelations") or [], [],
                             "no ledger intent recorded on identity abort")

    def test_gitlab_target_end_is_also_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": GL_ID, "identifier": "g/p#12", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": GL_ID_B, "identifier": "g/p#13", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, gl_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            ex = fake_execute({
                "relate-parent-read": [ok({"id": int(GL_ID), "iid": 12}),
                                       ok({"id": 555001, "iid": 13})],
            })
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertEqual(out.subtype, "durable_mismatch")
            self.assertEqual([c.op for c in ex.calls],
                             ["relate-parent-read", "relate-parent-read"],
                             "both ends read, nothing else issued")

    def test_github_stale_display_aborts_before_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": GH_NODE, "identifier": "#42", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": GH_NODE_B, "identifier": "#43", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, gh_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            # Issue #42 now carries a different node id.
            ex = fake_execute({
                "relate-parent-read": [ok({"id": 111, "node_id": "I_kwDOOther",
                                           "number": 42})],
            })
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "durable_mismatch")
            self.assertEqual([c.op for c in ex.calls], ["relate-parent-read"],
                             "abort BEFORE any probe or mutation request")


class RelateRelinkGuard(unittest.TestCase):
    """PR #246 review: the claim's critical section must revalidate BOTH
    linked identities against the from/to ids loaded at start. A spec
    relinked between the pair load and _ledger_claim would otherwise get an
    old-ID ledger key appended to its NEW identity, and the remote edge would
    be created between the OLD issues (orphaned relation, ledger attached to
    the wrong identity)."""

    NEW_UUID = "99999999-8888-7777-6666-555555555555"

    def _pair(self, flow: Path) -> None:
        a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                "depRelations": [], "linkState": "linked"}
        b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                "depRelations": [], "linkState": "linked"}
        _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)

    @staticmethod
    def _relink(flow: Path, spec_id: str, new_id: str) -> None:
        path = flow / "specs" / f"{spec_id}.json"
        spec = json.loads(path.read_text(encoding="utf-8"))
        spec["tracker"]["id"] = new_id
        spec["tracker"]["identifier"] = "WOR-99"
        path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

    def _probe_and_relink(self, flow: Path, spec_id: str):
        # Injection hook: the probe runs AFTER the pair load / classification
        # snapshot and BEFORE _ledger_claim's locked section - the exact
        # window the guard closes. Relink one spec to a different issue here.
        body = {"data": {"issue": {
            "id": LN_UUID,
            "relations": {"nodes": []},
            "inverseRelations": {"nodes": []},
        }}}

        def hook(request):
            self._relink(flow, spec_id, self.NEW_UUID)
            return ok(body)
        return hook

    def _assert_aborted(self, flow: Path, out, ex) -> None:
        self.assertIsInstance(out, TrackerError, msg=repr(out))
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual(out.subtype, "relinked")
        self.assertTrue((out.details or {}).get("recoverable"))
        self.assertEqual([c.op for c in ex.calls], ["relate-list"],
                         "probe only - the provider create is never issued")
        spec = json.loads(
            (flow / "specs" / "fn-1-demo.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["tracker"].get("depRelations") or [], [],
                         "no ledger entry written under the stale identity")

    def test_blocked_spec_relinked_between_pair_load_and_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair(flow)
            ex = fake_execute(
                {"relate-list": [self._probe_and_relink(flow, "fn-1-demo")]})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=ex)
            self._assert_aborted(flow, out, ex)

    def test_blocker_spec_relinked_between_pair_load_and_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair(flow)
            ex = fake_execute(
                {"relate-list": [self._probe_and_relink(flow, "fn-2-dep")]})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=ex)
            self._assert_aborted(flow, out, ex)

    def test_normal_path_unchanged(self) -> None:
        # No relink: the claim proceeds and the relate applies as before.
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair(flow)
            list_empty = ok({"data": {"issue": {
                "id": LN_UUID,
                "relations": {"nodes": []},
                "inverseRelations": {"nodes": []},
            }}})
            create = ok({"data": {"issueRelationCreate": {
                "success": True, "issueRelation": {"id": "rel-1"}}}})
            ex = fake_execute({"relate-list": [list_empty],
                               "relate-create": create})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=ex)
            self.assertNotIsInstance(out, TrackerError, msg=repr(out))
            self.assertEqual(out["kind"], "applied")


class RelatePostProbeIdentityGuard(unittest.TestCase):
    """A relation probe can overlap a relink. Collision side effects must
    revalidate both durable identities after that network read, otherwise an
    old ledger entry plus an old-edge-absent result queues a false human
    removal and writes a receipt carrying the old tracker ID."""

    NEW_UUID = "99999999-8888-7777-6666-555555555555"

    def _pair_with_ledger(self, flow: Path) -> None:
        key = dep_relation_key(LN_UUID, LN_UUID_B)
        a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                "linkState": "linked",
                "depRelations": [{
                    "key": key, "dep_spec": "fn-2-dep",
                    "from_tracker_id": LN_UUID,
                    "to_tracker_id": LN_UUID_B,
                    "type": "blocks", "source": "flow",
                    "updatedAt": "2026-01-01T00:00:00Z",
                }]}
        b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                "depRelations": [], "linkState": "linked"}
        _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)

    def test_relink_during_probe_refuses_false_human_removal_side_effects(
            self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair_with_ledger(flow)

            def probe_then_relink(request):
                RelateRelinkGuard._relink(
                    flow, "fn-1-demo", self.NEW_UUID)
                return ok({"data": {"issue": {
                    "id": LN_UUID,
                    "relations": {"nodes": []},
                    "inverseRelations": {"nodes": []},
                }}})

            ex = fake_execute({"relate-list": [probe_then_relink]})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=ex)

            self.assertIsInstance(out, TrackerError, msg=repr(out))
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "relinked")
            self.assertEqual((out.details or {}).get("expected"),
                             {"from": LN_UUID, "to": LN_UUID_B})
            self.assertEqual((out.details or {}).get("current"),
                             {"from": self.NEW_UUID, "to": LN_UUID_B})
            self.assertEqual([c.op for c in ex.calls], ["relate-list"])
            self.assertFalse((flow / "review-deferred").exists(),
                             "no false human-removal queue entry")
            self.assertFalse((flow / "sync-runs").exists(),
                             "no receipt written with old tracker IDs")


class RelateFinalizeRelinkGuard(unittest.TestCase):
    """PR #246 review: locks never span the provider mutation, so a relink
    can land between _ledger_claim's release and the finalize. The finalize
    must recheck both identities under the lock (wave-11 recheck, one step
    later); on drift it must NOT finalize the old-ID pending entry onto the
    relinked spec - the claim is removed and the already-landed remote
    create (which cannot be un-sent) is surfaced as structured CONFLICT
    evidence (completed_steps + edge identity) instead of silently recorded
    under the wrong identity."""

    NEW_UUID = "99999999-8888-7777-6666-555555555555"

    def _pair(self, flow: Path) -> None:
        a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                "depRelations": [], "linkState": "linked"}
        b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                "depRelations": [], "linkState": "linked"}
        _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)

    def _run(self, flow: Path, relink_spec: str):
        # Injection hook on the CREATE response: the relink lands after the
        # claim's lock released and the provider mutation succeeded, but
        # before the finalize re-acquires the lock - the exact window the
        # finalize-time recheck closes.
        list_empty = ok({"data": {"issue": {
            "id": LN_UUID,
            "relations": {"nodes": []},
            "inverseRelations": {"nodes": []},
        }}})
        create_body = {"data": {"issueRelationCreate": {
            "success": True, "issueRelation": {"id": "rel-1"}}}}

        def create_hook(request):
            RelateRelinkGuard._relink(flow, relink_spec, self.NEW_UUID)
            return ok(create_body)

        ex = fake_execute({"relate-list": [list_empty],
                           "relate-create": [create_hook]})
        out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
        return out, ex

    def _assert_refused(self, flow: Path, out, ex) -> None:
        self.assertIsInstance(out, TrackerError, msg=repr(out))
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual(out.subtype, "relinked")
        details = out.details or {}
        # The remote create against the OLD issues landed - it is carried as
        # evidence, never hidden (wave-8 decoration shape).
        self.assertEqual(details.get("completed_steps"), ["relate-create"])
        self.assertEqual(details.get("key"),
                         dep_relation_key(LN_UUID, LN_UUID_B))
        self.assertEqual(details.get("from"), "fn-1-demo")
        self.assertEqual(details.get("to"), "fn-2-dep")
        self.assertIs(details.get("recoverable"), False,
                      "a re-run cannot un-send the orphan edge")
        # The cleanup write succeeded: the removal claim is backed by an
        # explicit, symmetric marker (never asserted implicitly).
        self.assertEqual(details.get("cleanup"), {"released": True})
        self.assertEqual([c.op for c in ex.calls],
                         ["relate-list", "relate-create"],
                         "the create WAS issued before the relink landed")
        # The pending entry must NOT be finalized onto the relinked spec:
        # no applied (status-less) entry, and the stale-identity claim is
        # removed rather than left to linger.
        spec = json.loads(
            (flow / "specs" / "fn-1-demo.json").read_text(encoding="utf-8"))
        entries = spec["tracker"].get("depRelations") or []
        self.assertEqual(entries, [],
                         "old-ID entry neither finalized nor left pending")

    def test_blocked_spec_relinked_between_create_and_finalize(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair(flow)
            out, ex = self._run(flow, "fn-1-demo")
            self._assert_refused(flow, out, ex)

    def test_blocker_spec_relinked_between_create_and_finalize(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair(flow)
            out, ex = self._run(flow, "fn-2-dep")
            self._assert_refused(flow, out, ex)

    def test_normal_path_finalizes_as_before(self) -> None:
        # No relink: the guarded finalize applies the entry exactly as the
        # unguarded finalize did.
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair(flow)
            list_empty = ok({"data": {"issue": {
                "id": LN_UUID,
                "relations": {"nodes": []},
                "inverseRelations": {"nodes": []},
            }}})
            create = ok({"data": {"issueRelationCreate": {
                "success": True, "issueRelation": {"id": "rel-1"}}}})
            ex = fake_execute({"relate-list": [list_empty],
                               "relate-create": create})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=ex)
            self.assertNotIsInstance(out, TrackerError, msg=repr(out))
            self.assertEqual(out["kind"], "applied")
            spec = json.loads(
                (flow / "specs" / "fn-1-demo.json").read_text(encoding="utf-8"))
            entries = spec["tracker"]["depRelations"]
            self.assertEqual(len(entries), 1)
            self.assertNotIn("status", entries[0],
                             "entry finalized (claim fields dropped)")


class GitlabProbeDirection(unittest.TestCase):
    """PR #246 review: GitLab link_type is relative to the QUERIED issue.
    A reverse `blocks` link (A blocks B) must never satisfy an
    A blocked-by B request."""

    def test_reverse_blocks_link_does_not_match(self) -> None:
        ex = fake_execute({"relate-list": ok([
            {"iid": 13, "link_type": "blocks"}])})
        out = RP.gitlab_probe_pair(gl_cfg(), ex, from_display="g/p#12",
                                   to_display="g/p#13")
        self.assertIs(out, False,
                      "A-blocks-B is the OPPOSITE of A-blocked-by-B")

    def test_forward_is_blocked_by_matches(self) -> None:
        ex = fake_execute({"relate-list": ok([
            {"iid": 13, "link_type": "is_blocked_by"}])})
        out = RP.gitlab_probe_pair(gl_cfg(), ex, from_display="g/p#12",
                                   to_display="g/p#13")
        self.assertIs(out, True)

    def test_degraded_relates_to_still_matches(self) -> None:
        # flow's own degraded projection on tiers without blockedBy is
        # symmetric - it stays in the match set.
        ex = fake_execute({"relate-list": ok([
            {"iid": 13, "link_type": "relates_to"}])})
        out = RP.gitlab_probe_pair(gl_cfg(), ex, from_display="g/p#12",
                                   to_display="g/p#13")
        self.assertIs(out, True)

    def test_reverse_edge_end_to_end_creates_required_relation(self) -> None:
        # A blocks B already on the tracker; requesting A blocked-by B must
        # CREATE the missing relation - not noop and not queue it as a
        # false foreign collision.
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": GL_ID, "identifier": "g/p#12", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": GL_ID_B, "identifier": "g/p#13", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, gl_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            ex = fake_execute({
                "relate-parent-read": [ok({"id": int(GL_ID), "iid": 12}),
                                       ok({"id": int(GL_ID_B), "iid": 13})],
                "relate-list": ok([{"iid": 13, "link_type": "blocks"}]),
                "relate-create": ok({"id": 2, "link_type": "is_blocked_by"}),
            })
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=ex)
            self.assertNotIsInstance(out, TrackerError, msg=repr(out))
            self.assertEqual(out["kind"], "applied")
            self.assertEqual(out["form"], "is_blocked_by")
            self.assertIn("relate-create", [c.op for c in ex.calls])
            sink = flow / "review-deferred" / "tracker-relate.md"
            self.assertFalse(sink.exists(),
                             "no false foreign collision queued")


class JiraProbeDirection(unittest.TestCase):
    """PR #246 review: querying blocked issue A, Jira carries the blocker B
    in inwardIssue (jira.md listIssueRelations). The old probe checked
    outwardIssue, so a link exactly as jira_set() creates it read as absent -
    falsely queueing a ledgered edge as a human removal (or re-creating an
    unledgered one)."""

    def _probe(self, links):
        ex = fake_execute({"relate-list": ok({"fields": {"issuelinks": links}})})
        return RP.jira_probe(jr_cfg(), ex, from_id=JR_ID, to_id=JR_ID_B)

    def test_link_as_jira_set_created_is_found(self) -> None:
        # jira_set posts inwardIssue=B(blocker)/outwardIssue=A(blocked); GET
        # on A then shows the blocker B in inwardIssue (measured live
        # 2026-07-28, JQL linkedIssues tiebreak).
        out = self._probe([{"type": {"name": "Blocks"},
                            "inwardIssue": {"id": JR_ID_B}}])
        self.assertIs(out, True,
                      "edge jira_set created must be found by the probe")

    def test_reverse_orientation_does_not_match(self) -> None:
        # outwardIssue=B on A means "A blocks B" - the REVERSE edge; it
        # must never satisfy an A blocked-by B probe (mirrors
        # GitlabProbeDirection).
        out = self._probe([{"type": {"name": "Blocks"},
                            "outwardIssue": {"id": JR_ID_B}}])
        self.assertIs(out, False,
                      "A-blocks-B is the OPPOSITE of A-blocked-by-B")

    def test_other_link_types_ignored(self) -> None:
        out = self._probe([{"type": {"name": "Relates"},
                            "inwardIssue": {"id": JR_ID_B}}])
        self.assertIs(out, False)


class RelatePendingClaim(unittest.TestCase):
    """PR #246 review wave 4: the pending write is a CLAIM. Two relates of
    the SAME pair racing past the absent-probe must not both reach the
    provider create - only the invocation that inserts the pending entry
    mutates; the other backs off as CONFLICT/concurrent_claim."""

    def test_concurrent_same_pair_relates_create_once(self) -> None:
        import threading
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            barrier = threading.Barrier(2)
            results = {}
            creates = []
            creates_lock = threading.Lock()

            def go(worker: str) -> None:
                empty = ok({"data": {"issue": {"id": LN_UUID,
                            "relations": {"nodes": []},
                            "inverseRelations": {"nodes": []}}}})
                created = ok({"data": {"issueRelationCreate": {
                    "success": True, "issueRelation": {"id": "rel-1"}}}})

                def execute(request):
                    if request.op == "relate-list":
                        # BOTH workers probe the edge as absent before either
                        # reaches the claim - the exact reviewed race.
                        barrier.wait(timeout=10)
                        return empty
                    if request.op == "relate-create":
                        with creates_lock:
                            creates.append(worker)
                        return created
                    raise AssertionError(f"unexpected op {request.op!r}")
                results[worker] = R.relate(flow, "fn-1-demo",
                                           blocked_by="fn-2-dep",
                                           execute=execute)

            t1 = threading.Thread(target=go, args=("w1",))
            t2 = threading.Thread(target=go, args=("w2",))
            t1.start(); t2.start(); t1.join(); t2.join()

            self.assertEqual(len(creates), 1,
                             "exactly ONE worker may perform the provider "
                             f"create; got {creates}")
            winners = [w for w, out in results.items()
                       if not isinstance(out, TrackerError)]
            losers = [out for out in results.values()
                      if isinstance(out, TrackerError)]
            self.assertEqual(len(winners), 1, repr(results))
            self.assertEqual(results[winners[0]]["kind"], "applied")
            self.assertEqual(len(losers), 1)
            self.assertIs(losers[0].cls, ErrorClass.CONFLICT)
            self.assertEqual(losers[0].subtype, "concurrent_claim")
            self.assertTrue((losers[0].details or {}).get("recoverable"))
            # Ledger converged on ONE finalized entry - no duplicate, no
            # orphaned pending marker.
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            entries = spec["tracker"]["depRelations"]
            self.assertEqual(len(entries), 1)
            self.assertNotIn("status", entries[0])
            self.assertFalse(
                (flow / "review-deferred" / "tracker-relate.md").exists(),
                "a live concurrent claim is not a human-review collision")

    def test_stale_pending_entry_still_repairs_not_backs_off(self) -> None:
        # Interrupted-run repair semantics preserved: a pending entry that
        # existed at snapshot time takes the repair path (finalize, no
        # mutation) - the claim back-off applies only to entries that
        # appeared AFTER the snapshot.
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            key = R.dep_relation_key(LN_UUID, LN_UUID_B)
            a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                    "linkState": "linked",
                    "depRelations": [{"key": key, "dep_spec": "fn-2-dep",
                                      "from_tracker_id": LN_UUID,
                                      "to_tracker_id": LN_UUID_B,
                                      "type": "blocks", "source": "flow",
                                      "status": "pending",
                                      "updatedAt": "2026-01-01T00:00:00Z"}]}
            b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            present = ok({"data": {"issue": {
                "id": LN_UUID,
                "relations": {"nodes": []},
                "inverseRelations": {"nodes": [
                    {"type": "blocks", "issue": {"id": LN_UUID_B}}]},
            }}})
            ex = fake_execute({"relate-list": [present]})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=ex)
            self.assertNotIsInstance(out, TrackerError, msg=repr(out))
            self.assertEqual(out["kind"], "applied")
            self.assertEqual(out["reason"], "ledger_repaired")
            self.assertEqual([c.op for c in ex.calls], ["relate-list"],
                             "repair issues no mutation")

    def _pair_with_pending(self, flow: Path, *, pid: int,
                           claimed_at: float) -> str:
        import socket
        key = R.dep_relation_key(LN_UUID, LN_UUID_B)
        a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                "linkState": "linked",
                "depRelations": [{"key": key, "dep_spec": "fn-2-dep",
                                  "from_tracker_id": LN_UUID,
                                  "to_tracker_id": LN_UUID_B,
                                  "type": "blocks", "source": "flow",
                                  "status": "pending",
                                  "pid": pid,
                                  "host": socket.gethostname(),
                                  "claimedAt": claimed_at,
                                  "updatedAt": "2026-01-01T00:00:00Z"}]}
        b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                "depRelations": [], "linkState": "linked"}
        _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)
        return key

    @staticmethod
    def _probe(nodes: list):
        return ok({"data": {"issue": {
            "id": LN_UUID,
            "relations": {"nodes": []},
            "inverseRelations": {"nodes": nodes},
        }}})

    def test_staggered_live_pending_claim_backs_off(self) -> None:
        # PR #246 review wave 6 (staggered variant of the claim race): worker 2
        # starts AFTER worker 1's pending entry landed but BEFORE worker 1's
        # create is visible - snapshot sees pending + remote-absent. The old
        # code took the wave-1 retry branch and created AGAIN. A LIVE owner
        # (recent claim, foreign pid) must back off with no provider mutation.
        import os
        import time
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            other_pid = os.getpid() + 1  # not us; recency alone keeps it live
            self._pair_with_pending(flow, pid=other_pid,
                                    claimed_at=time.time())
            ex = fake_execute({"relate-list": [self._probe([])]})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=ex)
            self.assertIsInstance(out, TrackerError, msg=repr(out))
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "concurrent_claim")
            self.assertTrue((out.details or {}).get("recoverable"))
            self.assertEqual([c.op for c in ex.calls], ["relate-list"],
                             "probe only - worker 2 must NOT create: worker "
                             "1's create is the ONE provider create overall")
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            entries = spec["tracker"]["depRelations"]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["status"], "pending")
            self.assertEqual(entries[0]["pid"], other_pid,
                             "worker 1's claim is untouched")
            self.assertFalse(
                (flow / "review-deferred" / "tracker-relate.md").exists(),
                "a live concurrent claim is not a human-review collision")

            # Once worker 1's create becomes visible, the back-off re-run
            # HEALS the ledger (repair path) - still no second create.
            ex2 = fake_execute({"relate-list": [self._probe(
                [{"type": "blocks", "issue": {"id": LN_UUID_B}}])]})
            again = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                             execute=ex2)
            self.assertNotIsInstance(again, TrackerError, msg=repr(again))
            self.assertEqual(again["reason"], "ledger_repaired")
            self.assertEqual([c.op for c in ex2.calls], ["relate-list"])

    def test_stale_dead_pid_pending_still_retries_create(self) -> None:
        # Interrupted-run retry semantics preserved: a pending entry whose
        # owner is past the stale window with a dead pid ON THIS HOST is a
        # crashed run's leftover - reclaimed and the create retried.
        import time
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            # pid 0 is never alive; claimedAt is past the stale window.
            self._pair_with_pending(flow, pid=0,
                                    claimed_at=time.time() - 999)
            created = ok({"data": {"issueRelationCreate": {
                "success": True, "issueRelation": {"id": "rel-1"}}}})
            ex = fake_execute({"relate-list": [self._probe([])],
                               "relate-create": created})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=ex)
            self.assertNotIsInstance(out, TrackerError, msg=repr(out))
            self.assertEqual(out["kind"], "applied")
            self.assertIn("relate-create", [c.op for c in ex.calls])
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            entries = spec["tracker"]["depRelations"]
            self.assertEqual(len(entries), 1)
            for field in ("status", "pid", "host", "claimedAt"):
                self.assertNotIn(field, entries[0],
                                 "finalized entry matches the fn-64 shape")

    def test_definite_create_failure_releases_claim_for_retry(self) -> None:
        # PR #246 review wave 6 (immediate-retry variant): a DEFINITE provider
        # create failure (parsed rejection - here linear success!=true) must
        # release the pending claim before returning. The old code left the
        # dead prior owner's claim behind, and a retry under a NEW pid failed
        # concurrent_claim for the full STALE_OWNER_S window.
        import os
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            rejected = ok({"data": {"issueRelationCreate": {
                "success": False}}})
            ex = fake_execute({"relate-list": [self._probe([])],
                               "relate-create": [rejected]})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=ex)
            self.assertIsInstance(out, TrackerError, msg=repr(out))
            self.assertEqual(out.subtype, "mutation_failed")
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            self.assertEqual(spec["tracker"]["depRelations"], [],
                             "definite not-landed failure releases the "
                             "pending claim")
            # Immediate same-host retry under a NEW pid (the failed run's
            # process is gone): must claim and create - no concurrent_claim.
            created = ok({"data": {"issueRelationCreate": {
                "success": True, "issueRelation": {"id": "rel-1"}}}})
            ex2 = fake_execute({"relate-list": [self._probe([])],
                                "relate-create": [created]})
            with mock.patch("os.getpid", return_value=os.getpid() + 7):
                again = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                                 execute=ex2)
            self.assertNotIsInstance(again, TrackerError, msg=repr(again))
            self.assertEqual(again["kind"], "applied")
            self.assertIn("relate-create", [c.op for c in ex2.calls])
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            entries = spec["tracker"]["depRelations"]
            self.assertEqual(len(entries), 1)
            self.assertNotIn("status", entries[0])

    def test_ambiguous_create_failure_keeps_claim_for_repair(self) -> None:
        # An AMBIGUOUS transport failure (timeout: the create may have landed)
        # must LEAVE the pending entry so a retry classifies against the
        # remote probe - repair (finalize, no second create) when the edge
        # turns out to exist.
        import os
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            boom = TrackerError(ErrorClass.TRANSPORT, "timed out",
                                subtype="timeout", auto_retryable=True)
            ex = fake_execute({"relate-list": [self._probe([])],
                               "relate-create": [boom]})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=ex)
            self.assertIsInstance(out, TrackerError, msg=repr(out))
            self.assertEqual(out.subtype, "timeout")
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            entries = spec["tracker"]["depRelations"]
            self.assertEqual(len(entries), 1,
                             "ambiguous failure must keep the pending entry")
            self.assertEqual(entries[0]["status"], "pending")
            self.assertEqual(entries[0]["pid"], os.getpid())
            # The create HAD landed: the retry repairs the ledger against the
            # remote probe instead of creating a duplicate.
            ex2 = fake_execute({"relate-list": [self._probe(
                [{"type": "blocks", "issue": {"id": LN_UUID_B}}])]})
            again = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                             execute=ex2)
            self.assertNotIsInstance(again, TrackerError, msg=repr(again))
            self.assertEqual(again["reason"], "ledger_repaired")
            self.assertEqual([c.op for c in ex2.calls], ["relate-list"],
                             "repair issues no second create")


class RelateReceiptFailurePreservesEvidence(unittest.TestCase):
    """PR #246 review wave 8: create + finalize succeeded but the receipt
    write failed. A bare error read as "nothing happened", yet a retry takes
    the in_ledger+remote no-op path and never re-attempts the receipt - the
    error must carry the completed steps + edge identity (mirrors
    lifecycle's create/persist-external receipt-failure decoration)."""

    def _pair(self, flow: Path) -> None:
        a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                "depRelations": [], "linkState": "linked"}
        b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                "depRelations": [], "linkState": "linked"}
        _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)

    def test_receipt_failure_carries_completed_steps_and_edge(self) -> None:
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair(flow)
            key = R.dep_relation_key(LN_UUID, LN_UUID_B)
            empty_probe = ok({"data": {"issue": {"id": LN_UUID,
                              "relations": {"nodes": []},
                              "inverseRelations": {"nodes": []}}}})
            created = ok({"data": {"issueRelationCreate": {
                "success": True, "issueRelation": {"id": "rel-1"}}}})
            ex = fake_execute({"relate-list": [empty_probe],
                               "relate-create": [created]})
            boom = TrackerError(ErrorClass.TRANSPORT,
                                "receipt write failed: disk full",
                                subtype="write")
            with mock.patch.object(R, "write_sync_receipt",
                                   return_value=boom):
                out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                               execute=ex)
            self.assertIsInstance(out, TrackerError, msg=repr(out))
            self.assertIs(out.cls, ErrorClass.TRANSPORT)
            details = out.details or {}
            self.assertEqual(details.get("completed_steps"),
                             ["relate-create", "ledger-finalize"])
            self.assertEqual(details.get("key"), key)
            self.assertEqual(details.get("from"), "fn-1-demo")
            self.assertEqual(details.get("to"), "fn-2-dep")
            self.assertEqual(details.get("form"), "blocks")
            # The ledger stays finalized - nothing is rolled back.
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            entries = spec["tracker"]["depRelations"]
            self.assertEqual(len(entries), 1)
            self.assertNotIn("status", entries[0])

    def test_repair_receipt_failure_carries_completed_steps(self) -> None:
        # Same partial-success shape on the repair path: the edge is on the
        # tracker (earlier run) and the finalize landed; the receipt failure
        # must still report the completed step + edge identity.
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            key = R.dep_relation_key(LN_UUID, LN_UUID_B)
            a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                    "linkState": "linked",
                    "depRelations": [{"key": key, "dep_spec": "fn-2-dep",
                                      "from_tracker_id": LN_UUID,
                                      "to_tracker_id": LN_UUID_B,
                                      "type": "blocks", "source": "flow",
                                      "status": "pending",
                                      "updatedAt": "2026-01-01T00:00:00Z"}]}
            b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            present = ok({"data": {"issue": {
                "id": LN_UUID,
                "relations": {"nodes": []},
                "inverseRelations": {"nodes": [
                    {"type": "blocks", "issue": {"id": LN_UUID_B}}]},
            }}})
            ex = fake_execute({"relate-list": [present]})
            boom = TrackerError(ErrorClass.TRANSPORT,
                                "receipt write failed: disk full",
                                subtype="write")
            with mock.patch.object(R, "write_sync_receipt",
                                   return_value=boom):
                out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                               execute=ex)
            self.assertIsInstance(out, TrackerError, msg=repr(out))
            details = out.details or {}
            self.assertEqual(details.get("completed_steps"),
                             ["ledger-finalize"])
            self.assertEqual(details.get("key"), key)
            self.assertEqual(details.get("from"), "fn-1-demo")
            self.assertEqual(details.get("to"), "fn-2-dep")
            spec = json.loads((flow / "specs" / "fn-1-demo.json").read_text())
            entries = spec["tracker"]["depRelations"]
            self.assertEqual(len(entries), 1)
            self.assertNotIn("status", entries[0],
                             "finalize is NOT rolled back")


class GithubRelateProbeDrain(unittest.TestCase):
    """PR #246 review wave 4: the sub_issues probe drains EVERY page to the
    shared wire cap - a single-page probe would falsely report a later-page
    child absent (false human-removal queue / duplicate create attempt)."""

    @staticmethod
    def _full_page(start: int) -> list:
        return [{"number": start + i} for i in range(W._PAGE_SIZE)]

    def test_child_on_second_page_is_found(self) -> None:
        page1 = ok(self._full_page(1000))
        page2 = ok([{"number": 999}, {"number": 42}])
        ex = fake_execute({"wire-relate-probe": [page1, page2]})
        out = RP.github_probe(gh_cfg(), ex, from_display="#42",
                              to_display="#43")
        self.assertIs(out, True)
        self.assertEqual([c.op for c in ex.calls],
                         ["wire-relate-probe", "wire-relate-probe"],
                         "drain issues a second page request")
        first = ex.calls[0]
        argv = list(first.url_or_argv)
        self.assertIn(f"per_page={W._PAGE_SIZE}", argv[-1])
        self.assertIn("page=1", argv[-1])

    def test_truncated_at_cap_does_not_report_absence(self) -> None:
        counter = {"n": 0}

        def endless(_request):
            counter["n"] += 1
            return ok(self._full_page(counter["n"] * 1000))

        ex = fake_execute({"wire-relate-probe": endless})
        out = RP.github_probe(gh_cfg(), ex, from_display="#42",
                              to_display="#43")
        self.assertIsInstance(out, TrackerError,
                              "a probe that cannot prove absence must not "
                              "report absence")
        self.assertIs(out.cls, ErrorClass.TRANSPORT)
        self.assertEqual(out.subtype, "truncated")
        self.assertEqual(len(ex.calls), W._MAX_PAGES)

    def test_single_short_page_absence_still_reports_false(self) -> None:
        ex = fake_execute({"wire-relate-probe": [ok([{"number": 7}])]})
        out = RP.github_probe(gh_cfg(), ex, from_display="#42",
                              to_display="#43")
        self.assertIs(out, False)
        self.assertEqual(len(ex.calls), 1)


class GitlabRelateProbeDrain(unittest.TestCase):
    """PR #246 review wave 5: the GitLab issue-links probe drains EVERY page
    to the shared wire cap - a single-page probe would falsely report a
    later-page link absent (false human-removal queue on a ledgered edge /
    duplicate create attempt on an unledgered one)."""

    @staticmethod
    def _full_page(start: int) -> list:
        return [{"iid": start + i, "link_type": "is_blocked_by"}
                for i in range(W._PAGE_SIZE)]

    def test_link_on_second_page_is_found(self) -> None:
        page1 = ok(self._full_page(1000))
        page2 = ok([{"iid": 999, "link_type": "relates_to"},
                    {"iid": 13, "link_type": "is_blocked_by"}])
        ex = fake_execute({"relate-list": [page1, page2]})
        out = RP.gitlab_probe_pair(gl_cfg(), ex, from_display="g/p#12",
                                   to_display="g/p#13")
        self.assertIs(out, True)
        self.assertEqual([c.op for c in ex.calls],
                         ["relate-list", "relate-list"],
                         "drain issues a second page request")
        first = ex.calls[0]
        argv = list(first.url_or_argv)
        self.assertIn(f"per_page={W._PAGE_SIZE}", argv[-1])
        self.assertIn("page=1", argv[-1])

    def test_truncated_at_cap_does_not_report_absence(self) -> None:
        counter = {"n": 0}

        def endless(_request):
            counter["n"] += 1
            return ok(self._full_page(counter["n"] * 1000))

        ex = fake_execute({"relate-list": endless})
        out = RP.gitlab_probe_pair(gl_cfg(), ex, from_display="g/p#12",
                                   to_display="g/p#13")
        self.assertIsInstance(out, TrackerError,
                              "a probe that cannot prove absence must not "
                              "report absence")
        self.assertIs(out.cls, ErrorClass.TRANSPORT)
        self.assertEqual(out.subtype, "truncated")
        self.assertEqual(len(ex.calls), W._MAX_PAGES)

    def test_single_short_page_absence_still_reports_false(self) -> None:
        ex = fake_execute({"relate-list": [ok(
            [{"iid": 7, "link_type": "is_blocked_by"}])]})
        out = RP.gitlab_probe_pair(gl_cfg(), ex, from_display="g/p#12",
                                   to_display="g/p#13")
        self.assertIs(out, False)
        self.assertEqual(len(ex.calls), 1)


class JiraSetDirection(unittest.TestCase):
    """Measured live 2026-07-28 (JQL linkedIssues tiebreak on a sandbox
    Cloud site): POST /issueLink {inwardIssue: X, outwardIssue: Y, Blocks}
    creates "X blocks Y" - the jira.md create paragraph had the roles
    swapped, so jira_set created the REVERSE edge and the (correct) probe
    then queued every ledgered edge as a human removal on the next run.
    For "A blocked-by B" the blocker B must be inwardIssue."""

    def test_jira_set_posts_blocker_as_inward_issue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": JR_ID, "identifier": "SCRUM-1", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": JR_ID_B, "identifier": "SCRUM-2", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, jr_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            ex = fake_execute({
                "relate-parent-read": [
                    ok({"id": JR_ID, "key": "SCRUM-1", "fields": {}}),
                    ok({"id": JR_ID_B, "key": "SCRUM-2", "fields": {}})],
                "relate-list": ok({"fields": {"issuelinks": []}}),
                "relate-create": ok({}),
            })
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
            self.assertEqual(out["kind"], "applied")
            create = next(c for c in ex.calls if c.op == "relate-create")
            body = json.loads(create.body.decode())
            self.assertEqual(body["inwardIssue"], {"id": JR_ID_B},
                             "blocker (to) must be inwardIssue")
            self.assertEqual(body["outwardIssue"], {"id": JR_ID},
                             "blocked (from) must be outwardIssue")
            self.assertEqual(body["type"], {"name": "Blocks"})


class RelateRepairRelinkGuard(unittest.TestCase):
    """PR #246 review: the REPAIR branch (pending entry + edge already on the
    tracker from an interrupted earlier run) must finalize through the same
    identity-rechecking guard as the create path. A relink landing during the
    remote probe must NOT finalize the old-ID pending entry onto the newly
    linked spec. Unlike the create path, THIS invocation performed no
    provider mutation - the refusal must carry NO completed_steps (the
    remote edge predates this run)."""

    NEW_UUID = "99999999-8888-7777-6666-555555555555"

    def _pair_with_pending(self, flow: Path) -> str:
        key = R.dep_relation_key(LN_UUID, LN_UUID_B)
        a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                "linkState": "linked",
                "depRelations": [{"key": key, "dep_spec": "fn-2-dep",
                                  "from_tracker_id": LN_UUID,
                                  "to_tracker_id": LN_UUID_B,
                                  "type": "blocks", "source": "flow",
                                  "status": "pending",
                                  "updatedAt": "2026-01-01T00:00:00Z"}]}
        b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                "depRelations": [], "linkState": "linked"}
        _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)
        return key

    def _probe_present_and_relink(self, flow: Path, relink_spec: str):
        # Injection hook on the PROBE response: the pending entry existed at
        # snapshot time and the edge is already on the tracker (interrupted
        # earlier create), so the repair branch finalizes with no mutation.
        # The relink lands during the probe - after the pair load, before the
        # finalize re-acquires the lock: the window the guard must close.
        body = {"data": {"issue": {
            "id": LN_UUID,
            "relations": {"nodes": []},
            "inverseRelations": {"nodes": [
                {"type": "blocks", "issue": {"id": LN_UUID_B}}]},
        }}}

        def hook(request):
            RelateRelinkGuard._relink(flow, relink_spec, self.NEW_UUID)
            return ok(body)
        return hook

    def _run(self, flow: Path, relink_spec: str):
        ex = fake_execute(
            {"relate-list": [self._probe_present_and_relink(flow,
                                                            relink_spec)]})
        out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
        return out, ex

    def _assert_refused(self, flow: Path, out, ex) -> None:
        self.assertIsInstance(out, TrackerError, msg=repr(out))
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual(out.subtype, "relinked")
        details = out.details or {}
        # HONEST evidence shape: no provider mutation was performed by this
        # invocation - the remote edge predates this run, so the refusal must
        # not claim relate-create as a completed step.
        self.assertNotIn("completed_steps", details,
                         "repair refusal must carry no mutation evidence")
        self.assertEqual(details.get("key"),
                         dep_relation_key(LN_UUID, LN_UUID_B))
        self.assertEqual(details.get("from"), "fn-1-demo")
        self.assertEqual(details.get("to"), "fn-2-dep")
        self.assertIs(details.get("recoverable"), False)
        # The cleanup write succeeded: explicit marker, same shape as the
        # create path.
        self.assertEqual(details.get("cleanup"), {"released": True})
        self.assertEqual([c.op for c in ex.calls], ["relate-list"],
                         "probe only - the repair path issues no mutation")
        # The old-ID pending entry must NOT be finalized onto the relinked
        # spec: the stale-identity claim is removed, never applied.
        spec = json.loads(
            (flow / "specs" / "fn-1-demo.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["tracker"].get("depRelations") or [], [],
                         "old-ID entry neither finalized nor left pending")

    def test_blocked_spec_relinked_during_repair_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair_with_pending(flow)
            out, ex = self._run(flow, "fn-1-demo")
            self._assert_refused(flow, out, ex)

    def test_blocker_spec_relinked_during_repair_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair_with_pending(flow)
            out, ex = self._run(flow, "fn-2-dep")
            self._assert_refused(flow, out, ex)

    def test_normal_repair_still_finalizes(self) -> None:
        # No relink: pending + remote-present still repairs the ledger with
        # no mutation, exactly the wave-1 semantics.
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair_with_pending(flow)
            present = ok({"data": {"issue": {
                "id": LN_UUID,
                "relations": {"nodes": []},
                "inverseRelations": {"nodes": [
                    {"type": "blocks", "issue": {"id": LN_UUID_B}}]},
            }}})
            ex = fake_execute({"relate-list": [present]})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                           execute=ex)
            self.assertNotIsInstance(out, TrackerError, msg=repr(out))
            self.assertEqual(out["kind"], "applied")
            self.assertEqual(out["reason"], "ledger_repaired")
            self.assertEqual([c.op for c in ex.calls], ["relate-list"],
                             "repair issues no mutation")
            spec = json.loads(
                (flow / "specs" / "fn-1-demo.json").read_text(encoding="utf-8"))
            entries = spec["tracker"]["depRelations"]
            self.assertEqual(len(entries), 1)
            self.assertNotIn("status", entries[0],
                             "entry finalized (claim fields dropped)")


class RelateRelinkCleanupFailure(unittest.TestCase):
    """PR #246 review: when drift is detected at finalize time and the
    tracker-block write for the claim release FAILS (spec became unwritable),
    the returned CONFLICT/relinked must keep the relink evidence as the
    primary error AND report the cleanup failure honestly - the old-ID
    pending entry is still attached to the relinked spec, so no field (and
    no message text) may claim it was removed. The write failure must never
    mask or replace the relink conflict."""

    NEW_UUID = "99999999-8888-7777-6666-555555555555"

    def _pair(self, flow: Path) -> None:
        a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                "depRelations": [], "linkState": "linked"}
        b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                "depRelations": [], "linkState": "linked"}
        _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)

    def _pair_with_pending(self, flow: Path) -> str:
        key = R.dep_relation_key(LN_UUID, LN_UUID_B)
        a_tr = {"id": LN_UUID, "identifier": "WOR-17", "url": "u",
                "linkState": "linked",
                "depRelations": [{"key": key, "dep_spec": "fn-2-dep",
                                  "from_tracker_id": LN_UUID,
                                  "to_tracker_id": LN_UUID_B,
                                  "type": "blocks", "source": "flow",
                                  "status": "pending",
                                  "updatedAt": "2026-01-01T00:00:00Z"}]}
        b_tr = {"id": LN_UUID_B, "identifier": "WOR-18", "url": "u",
                "depRelations": [], "linkState": "linked"}
        _write_pair(flow, ln_cfg(), a_tracker=a_tr, b_tracker=b_tr)
        return key

    def _failing_writes_after_relink(self, relinked: dict):
        """Real write_tracker_block until the relink lands (the claim write
        must persist normally), then every write fails - the release write
        is the only one after the relink in these flows."""
        real = R.write_tracker_block
        boom = TrackerError(ErrorClass.TRANSPORT,
                            "tracker-block write failed: read-only filesystem",
                            subtype="write")

        def fake(path, spec_data, tracker):
            if relinked.get("done"):
                return boom
            return real(path, spec_data, tracker)
        return fake

    def _assert_conflict_with_cleanup_failure(self, out) -> None:
        self.assertIsInstance(out, TrackerError, msg=repr(out))
        # The relink conflict stays the primary error - the write failure
        # never masks or replaces it.
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual(out.subtype, "relinked")
        details = out.details or {}
        self.assertEqual(details.get("key"),
                         dep_relation_key(LN_UUID, LN_UUID_B))
        self.assertEqual(details.get("from"), "fn-1-demo")
        self.assertEqual(details.get("to"), "fn-2-dep")
        self.assertIs(details.get("recoverable"), False)
        # Structured cleanup-failure marker (receipt_write_failed shape).
        cleanup = details.get("cleanup") or {}
        self.assertIs(cleanup.get("released"), False,
                      "no field may claim the pending entry was removed")
        self.assertEqual(cleanup.get("error_class"),
                         ErrorClass.TRANSPORT.value)
        self.assertEqual(cleanup.get("subtype"), "write")
        self.assertIn("read-only filesystem", cleanup.get("message") or "")
        # And the prose must not claim removal either.
        self.assertNotIn("pending claim removed", out.message)

    def _assert_pending_still_on_disk(self, flow: Path) -> None:
        spec = json.loads(
            (flow / "specs" / "fn-1-demo.json").read_text(encoding="utf-8"))
        entries = spec["tracker"].get("depRelations") or []
        self.assertEqual(len(entries), 1,
                         "failed release leaves the old-ID entry on disk")
        self.assertEqual(entries[0].get("status"), "pending")

    def test_create_path_release_write_failure_reported(self) -> None:
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair(flow)
            relinked: dict = {}
            list_empty = ok({"data": {"issue": {
                "id": LN_UUID,
                "relations": {"nodes": []},
                "inverseRelations": {"nodes": []},
            }}})
            create_body = {"data": {"issueRelationCreate": {
                "success": True, "issueRelation": {"id": "rel-1"}}}}

            def create_hook(request):
                RelateRelinkGuard._relink(flow, "fn-1-demo", self.NEW_UUID)
                relinked["done"] = True
                return ok(create_body)

            ex = fake_execute({"relate-list": [list_empty],
                               "relate-create": [create_hook]})
            with mock.patch.object(
                    R, "write_tracker_block",
                    side_effect=self._failing_writes_after_relink(relinked)):
                out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                               execute=ex)
            self._assert_conflict_with_cleanup_failure(out)
            details = out.details or {}
            # Relink evidence intact: the landed remote create is still
            # carried (wave-8 decoration).
            self.assertEqual(details.get("completed_steps"),
                             ["relate-create"])
            self._assert_pending_still_on_disk(flow)

    def test_repair_path_release_write_failure_reported(self) -> None:
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair_with_pending(flow)
            relinked: dict = {}
            body = {"data": {"issue": {
                "id": LN_UUID,
                "relations": {"nodes": []},
                "inverseRelations": {"nodes": [
                    {"type": "blocks", "issue": {"id": LN_UUID_B}}]},
            }}}

            def probe_hook(request):
                RelateRelinkGuard._relink(flow, "fn-2-dep", self.NEW_UUID)
                relinked["done"] = True
                return ok(body)

            ex = fake_execute({"relate-list": [probe_hook]})
            with mock.patch.object(
                    R, "write_tracker_block",
                    side_effect=self._failing_writes_after_relink(relinked)):
                out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep",
                               execute=ex)
            self._assert_conflict_with_cleanup_failure(out)
            details = out.details or {}
            # Repair path: no mutation was performed by this run.
            self.assertNotIn("completed_steps", details)
            self._assert_pending_still_on_disk(flow)
