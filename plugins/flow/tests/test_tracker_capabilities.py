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
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flow" / "scripts"))

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


def gitlab_body_echo(request) -> Response:
    description = json.loads(request.body.decode())["description"]
    return ok({"id": int(GL_ID), "iid": 12, "description": description})


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
                                       "projectKey": "SCRUM",
                                       "blocksLinkType": "Blocks"},
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
    for sid, tr in ((a_id, a_tracker), (b_id, b_tracker)):
        tr = tr or {}
        lines = ["---", f"id: {sid}", f"title: {sid}"]
        if any(tr.get(k) for k in ("id", "identifier", "url", "snapshot")):
            lines.append("tracker:")
            for k in ("id", "identifier", "url", "snapshot"):
                if tr.get(k):
                    lines.append(f"  {k}: {json.dumps(str(tr[k]))}")
        lines.extend(["---", ""])
        (flow / "specs" / f"{sid}.md").write_text(
            "\n".join(lines), encoding="utf-8")


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
    def test_attachment_create_failure_retains_landed_asset_evidence(self) -> None:
        for create_result in (
            TrackerError(
                ErrorClass.TRANSPORT, "attachment create timed out",
                subtype="timeout", auto_retryable=True),
            ok({"data": {"attachmentCreate": {"success": False}}}),
        ):
            with self.subTest(result=type(create_result).__name__):
                with tempfile.TemporaryDirectory() as tmp:
                    src = Path(tmp) / "shot.png"
                    src.write_bytes(PAYLOAD)
                    asset = "https://uploads.linear.app/asset/landed"
                    parent = {
                        "id": LN_UUID, "identifier": "WOR-17", "title": "T",
                        "description": "B", "labels": {"nodes": []},
                    }
                    ex = fake_execute({
                        "wire-parent-read": ok({
                            "data": {"issue": parent},
                        }),
                        "wire-attach-fileUpload": ok({
                            "data": {"fileUpload": {
                                "success": True,
                                "uploadFile": {
                                    "uploadUrl": (
                                        "https://storage.example/presigned"),
                                    "assetUrl": asset,
                                    "headers": [],
                                },
                            }},
                        }),
                        "wire-attach-presigned-put": ok(b""),
                        "wire-attach-create": create_result,
                    })

                    out = W.dispatch(
                        "attach", ln_cfg(),
                        locator=loc(LN_UUID, "WOR-17"),
                        file_path=str(src), execute=ex)

                    self.assertIsInstance(out, TrackerError)
                    details = out.details or {}
                    self.assertEqual(
                        details["completed_steps"], ["asset-upload"])
                    self.assertEqual(details["asset_url"], asset)
                    self.assertEqual(details["size"], len(PAYLOAD))
                    self.assertTrue(details["recoverable"])

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


class RelateProbeDrain(unittest.TestCase):
    """Every provider's relate probe drains EVERY page to the shared wire cap
    before concluding absence: a single-page probe would falsely report a
    later-page edge absent (false human-removal queue / duplicate create)."""

    @staticmethod
    def _linear_page(other: str, *, more: bool, cursor) -> dict:
        return ok({"data": {"issue": {
            "id": LN_UUID,
            "relations": {"nodes": [],
                          "pageInfo": {"hasNextPage": False, "endCursor": None}},
            "inverseRelations": {
                "nodes": [{"type": "blocks", "issue": {"id": other}}],
                "pageInfo": {"hasNextPage": more, "endCursor": cursor}},
        }}})

    @staticmethod
    def _github_full_page(start: int) -> list:
        return [{"number": start + i} for i in range(W._PAGE_SIZE)]

    @staticmethod
    def _gitlab_full_page(start: int) -> list:
        return [{"iid": start + i, "link_type": "is_blocked_by"}
                for i in range(W._PAGE_SIZE)]

    def _providers(self) -> list:
        """(name, op, probe, second-page pages, endless page, lone short page, paged-argv)."""
        lp = self._linear_page
        return [
            ("linear", "relate-list",
             lambda ex: RP._linear_edge_exists(ex, LN_UUID, LN_UUID_B),
             [lp("other-uuid", more=True, cursor="cur-1"),
              lp(LN_UUID_B, more=False, cursor="cur-2")],
             lambda n: lp(f"uuid-{n}", more=True, cursor=f"cur-{n}"),
             ok({"data": {"issue": {"id": LN_UUID, "relations": {"nodes": []},
                                    "inverseRelations": {"nodes": []}}}}),
             False),
            ("github", "wire-relate-probe",
             lambda ex: RP.github_probe(gh_cfg(), ex, from_display="#42",
                                        to_display="#43"),
             [ok(self._github_full_page(1000)),
              ok([{"number": 999}, {"number": 42}])],
             lambda n: ok(self._github_full_page(n * 1000)),
             ok([{"number": 7}]),
             True),
            ("gitlab", "relate-list",
             lambda ex: RP.gitlab_probe_pair(gl_cfg(), ex, from_display="g/p#12",
                                             to_display="g/p#13"),
             [ok(self._gitlab_full_page(1000)),
              ok([{"iid": 999, "link_type": "relates_to"},
                  {"iid": 13, "link_type": "is_blocked_by"}])],
             lambda n: ok(self._gitlab_full_page(n * 1000)),
             ok([{"iid": 7, "link_type": "is_blocked_by"}]),
             True),
        ]

    def test_edge_on_second_page_is_found(self) -> None:
        for name, op, probe, pages, _endless, _lone, paged in self._providers():
            with self.subTest(provider=name):
                ex = fake_execute({op: pages})
                self.assertIs(probe(ex), True)
                self.assertEqual([c.op for c in ex.calls], [op, op],
                                 "drain issues a second page request")
                if paged:
                    argv = list(ex.calls[0].url_or_argv)
                    self.assertIn(f"per_page={W._PAGE_SIZE}", argv[-1])
                    self.assertIn("page=1", argv[-1])

    def test_truncated_at_cap_does_not_report_absence(self) -> None:
        for name, op, probe, _pages, endless, _lone, _paged in self._providers():
            with self.subTest(provider=name):
                counter = {"n": 0}

                def respond(_request, endless=endless, counter=counter):
                    counter["n"] += 1
                    return endless(counter["n"])

                ex = fake_execute({op: respond})
                out = probe(ex)
                self.assertIsInstance(out, TrackerError,
                                      "a probe that cannot prove absence must "
                                      "not report absence")
                self.assertIs(out.cls, ErrorClass.TRANSPORT)
                self.assertEqual(out.subtype, "truncated")
                self.assertEqual(len(ex.calls), W._MAX_PAGES)

    def test_single_short_page_absence_still_reports_false(self) -> None:
        for name, op, probe, _pages, _endless, lone, _paged in self._providers():
            with self.subTest(provider=name):
                ex = fake_execute({op: [lone]})
                self.assertIs(probe(ex), False)
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
                "relate-parent-read": [ok({"id": int(GL_ID), "iid": 12,
                                           "description": "Stale snapshot"}),
                                       ok({"id": int(GL_ID_B), "iid": 13})],
                "relate-list": ok([]),
                "relate-create": ok({"id": 1, "link_type": "relates_to"}),
                "relate-body-read": ok({
                    "id": int(GL_ID), "iid": 12,
                    "description": "Existing body"}),
                "relate-body-write": gitlab_body_echo,
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
            update = next(c for c in ex.calls if c.op == "relate-body-write")
            description = json.loads(update.body.decode())["description"]
            self.assertTrue(description.startswith("Existing body\n\n"))
            self.assertNotIn("Stale snapshot", description)
            self.assertIn(FLOW_DEPS_OPEN, description)
            self.assertIn("**Blocked by:** g/p#13", description)
            self.assertIn(FLOW_DEPS_CLOSE, description)


class GitlabRelateDependencyBody(unittest.TestCase):
    """GitLab relation projection is link + fenced direction/provenance body."""

    @staticmethod
    def _pair(flow: Path, *, entry=None) -> None:
        a_tr = {"id": GL_ID, "identifier": "g/p#12", "url": "u",
                "depRelations": [entry] if entry else [], "linkState": "linked"}
        b_tr = {"id": GL_ID_B, "identifier": "g/p#13", "url": "u",
                "depRelations": [], "linkState": "linked"}
        _write_pair(flow, gl_cfg(blocked_by=False, plan="free"),
                    a_tracker=a_tr, b_tracker=b_tr)

    @staticmethod
    def _parents(description: str):
        return [
            ok({"id": int(GL_ID), "iid": 12, "description": description}),
            ok({"id": int(GL_ID_B), "iid": 13, "description": "dep"}),
        ]

    def test_block_write_failure_preserves_landed_link_and_retry_repairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            self._pair(flow)
            failure = TrackerError(
                ErrorClass.TRANSPORT, "body update timed out",
                subtype="timeout", auto_retryable=True)
            first = fake_execute({
                "relate-parent-read": self._parents("Human body"),
                "relate-list": ok([]),
                "relate-create": ok({"id": 1, "link_type": "relates_to"}),
                "relate-body-read": ok({
                    "id": int(GL_ID), "iid": 12,
                    "description": "Human body"}),
                "relate-body-write": failure,
            })
            out = R.relate(
                flow, "fn-1-demo", blocked_by="fn-2-dep", execute=first)
            self.assertIsInstance(out, TrackerError, msg=repr(out))
            self.assertEqual((out.details or {}).get("completed_steps"),
                             ["relate-create"])
            self.assertTrue((out.details or {}).get("recoverable"))
            self.assertEqual((out.details or {}).get("key"),
                             dep_relation_key(GL_ID, GL_ID_B))
            self.assertEqual((out.details or {}).get("from"), "fn-1-demo")
            self.assertEqual((out.details or {}).get("to"), "fn-2-dep")
            self.assertEqual(
                list((flow / "create-first").glob("body-*.json")), [],
                "GitLab body claim releases on the body-write failure path")
            self.assertEqual(
                list((flow / "create-first").glob("relate-*.json")), [],
                "identity claims also release on the body-write failure path")

            retry = fake_execute({
                "relate-parent-read": self._parents("Human body"),
                "relate-list": ok([
                    {"iid": 13, "link_type": "relates_to"}]),
                "relate-body-read": ok({
                    "id": int(GL_ID), "iid": 12,
                    "description": "Human body"}),
                "relate-body-write": gitlab_body_echo,
            })
            again = R.relate(
                flow, "fn-1-demo", blocked_by="fn-2-dep", execute=retry)
            self.assertNotIsInstance(again, TrackerError, msg=repr(again))
            self.assertEqual(again["reason"], "deps_block_repaired")
            self.assertEqual(
                [call.op for call in retry.calls],
                ["relate-parent-read", "relate-parent-read", "relate-list",
                 "relate-body-read", "relate-body-write"],
                "retry repairs the body without another link POST")

    def test_applied_legacy_link_repairs_missing_block_instead_of_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            key = dep_relation_key(GL_ID, GL_ID_B)
            self._pair(flow, entry={
                "key": key,
                "dep_spec": "fn-2-dep",
                "from_tracker_id": GL_ID,
                "to_tracker_id": GL_ID_B,
                "type": "blocks",
                "source": "flow",
            })
            ex = fake_execute({
                "relate-parent-read": self._parents("Keep this text"),
                "relate-list": ok([
                    {"iid": 13, "link_type": "relates_to"}]),
                "relate-body-read": ok({
                    "id": int(GL_ID), "iid": 12,
                    "description": "Keep this text"}),
                "relate-body-write": gitlab_body_echo,
            })
            out = R.relate(
                flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
            self.assertNotIsInstance(out, TrackerError, msg=repr(out))
            self.assertEqual(out["kind"], "applied")
            self.assertEqual(out["reason"], "deps_block_repaired")
            self.assertNotIn("relate-create", [call.op for call in ex.calls])
            update = next(call for call in ex.calls
                          if call.op == "relate-body-write")
            description = json.loads(update.body.decode())["description"]
            self.assertTrue(description.startswith("Keep this text\n\n"))
            self.assertIn("**Blocked by:** g/p#13", description)

    def test_existing_fence_dedups_exact_ref_and_preserves_other_refs(self) -> None:
        body = (
            "Intro\n\n"
            f"{FLOW_DEPS_OPEN}\n"
            "**Blocked by:** g/p#3, g/p#13\n"
            f"{FLOW_DEPS_CLOSE}\n"
        )
        self.assertEqual(RP._gitlab_deps_body(body, "g/p#13"), body)
        updated = RP._gitlab_deps_body(body, "g/p#14")
        self.assertNotIsInstance(updated, TrackerError)
        self.assertIn("**Blocked by:** g/p#3, g/p#13, g/p#14", updated)
        self.assertTrue(updated.startswith("Intro\n\n"))

    def test_reversed_fence_is_rejected_without_appending_a_second_block(
            self) -> None:
        body = f"{FLOW_DEPS_CLOSE}\nHuman text\n{FLOW_DEPS_OPEN}"
        out = RP._gitlab_deps_body(body, "g/p#13")
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual(out.subtype, "deps_block")


class GithubSubIssuesHierarchy(unittest.TestCase):
    def test_sub_issues_reported_as_hierarchy_never_blocked_by(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": GH_NODE, "identifier": "#42", "url": "u"}
            b_tr = {"id": GH_NODE_B, "identifier": "#43", "url": "u"}
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


class Round2HostFixes(unittest.TestCase):
    def test_jira_relate_probe_and_create(self) -> None:
        """The probe signature bug made EVERY jira relate raise TypeError."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            a_tr = {"id": "10042", "identifier": "SCRUM-1", "url": "u"}
            b_tr = {"id": "10043", "identifier": "SCRUM-2", "url": "u"}
            _write_pair(flow, jr_cfg(), a_tracker=a_tr, b_tracker=b_tr)
            probe = ok({"fields": {"issuelinks": []}})
            ex = fake_execute({"relate-list": [probe], "relate-create": ok(None)})
            out = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["kind"], "applied")
            self.assertEqual(out["form"], "blocks")
            present = ok({"fields": {"issuelinks": [
                {"type": {"name": "Blocks"},
                 "inwardIssue": {"id": "10043"}}]}})
            ex2 = fake_execute({"relate-list": [present]})
            again = R.relate(flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex2)
            self.assertEqual(again["kind"], "noop")


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
                "relate-parent-read": [ok({"id": int(GL_ID), "iid": 12,
                                           "description": "B"}),
                                       ok({"id": int(GL_ID_B), "iid": 13})],
                "relate-list": ok([{"iid": 13, "link_type": "blocks"}]),
                "relate-create": ok({"id": 2, "link_type": "is_blocked_by"}),
                "relate-body-read": ok({
                    "id": int(GL_ID), "iid": 12, "description": "B"}),
                "relate-body-write": gitlab_body_echo,
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

    def test_configured_custom_link_type_is_used_for_probe(self) -> None:
        config = jr_cfg()
        config["tracker"]["perTracker"]["blocksLinkType"] = "Depends On"
        ex = fake_execute({"relate-list": ok({"fields": {"issuelinks": [{
            "type": {"name": "Depends On"},
            "inwardIssue": {"id": JR_ID_B},
        }]}})})
        out = RP.jira_probe(
            config, ex, from_id=JR_ID, to_id=JR_ID_B)
        self.assertIs(out, True)


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

    def test_jira_set_posts_configured_custom_link_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            config = jr_cfg()
            config["tracker"]["perTracker"]["blocksLinkType"] = "Depends On"
            a_tr = {"id": JR_ID, "identifier": "SCRUM-1", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": JR_ID_B, "identifier": "SCRUM-2", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, config, a_tracker=a_tr, b_tracker=b_tr)
            ex = fake_execute({
                "relate-parent-read": [
                    ok({"id": JR_ID, "key": "SCRUM-1", "fields": {}}),
                    ok({"id": JR_ID_B, "key": "SCRUM-2", "fields": {}})],
                "relate-list": ok({"fields": {"issuelinks": []}}),
                "relate-create": ok({}),
            })
            out = R.relate(
                flow, "fn-1-demo", blocked_by="fn-2-dep", execute=ex)
            self.assertEqual(out["kind"], "applied")
            create = next(c for c in ex.calls if c.op == "relate-create")
            self.assertEqual(
                json.loads(create.body)["type"], {"name": "Depends On"})

    def test_missing_blocks_semantics_defers_without_relation_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            config = jr_cfg()
            del config["tracker"]["perTracker"]["blocksLinkType"]
            a_tr = {"id": JR_ID, "identifier": "SCRUM-1", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            b_tr = {"id": JR_ID_B, "identifier": "SCRUM-2", "url": "u",
                    "depRelations": [], "linkState": "linked"}
            _write_pair(flow, config, a_tracker=a_tr, b_tracker=b_tr)
            ex = fake_execute({
                "relate-parent-read": [
                    ok({"id": JR_ID, "key": "SCRUM-1", "fields": {}}),
                    ok({"id": JR_ID_B, "key": "SCRUM-2", "fields": {}})],
                "relate-link-types": ok({
                    "issueLinkTypes": [{
                        "name": "Relates", "outward": "relates to"}]}),
            })
            out = R.relate(
                flow, "fn-1-demo", blocked_by="fn-2-dep",
                event="live.relate", execute=ex)
            self.assertEqual(out["kind"], "queued")
            self.assertEqual(out["reason"], "no_blocks_link_type")
            self.assertNotIn("relate-list", [c.op for c in ex.calls])
            self.assertNotIn("relate-create", [c.op for c in ex.calls])


class LeafIsSafeDivergentResolve(unittest.TestCase):
    """fn-120.4: `leaf_is_safe` used to resolve base and leaf INDEPENDENTLY.

    On Windows a non-strict `Path.resolve()` may stop expanding on a transient
    error (`ntpath._getfinalpathname_nonstrict` swallows SHARING_VIOLATION /
    ACCESS_DENIED), so under concurrent writers one call could keep the 8.3
    `RUNNER~1` spelling while the other expanded it. Two spellings of the SAME
    path then compared unequal and a legitimate write was refused with
    `INVALID_INPUT` "escapes" - a ~50% flake on `windows-latest`
    (run 30921678923 RED, identical re-run 30923544649 GREEN). Containment is
    now derived from ONE resolve; these tests keep the escape/symlink teeth.
    """

    def setUp(self) -> None:
        from flowctl_tracker.lifecycle.helpers import leaf_is_safe
        self.leaf_is_safe = leaf_is_safe
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        # A component that has a plausible 8.3 alias; the fake resolve below
        # abbreviates it for the leaf only, exactly as the flake did.
        self.root = Path(td.name) / "longdirname"
        self.base = self.root / "create-first"
        self.base.mkdir(parents=True)

    def _divergent_resolve(self):
        """Patch: the BASE resolves fully, the LEAF bails out unexpanded."""
        real_resolve = Path.resolve

        def fake_resolve(self, strict=False):
            resolved = real_resolve(self, strict=strict)
            if self.suffix == ".json":
                return Path(str(resolved).replace("longdirname", "LONGDI~1"))
            return resolved

        return mock.patch.object(Path, "resolve", fake_resolve)

    def test_divergent_resolve_does_not_fake_an_escape(self) -> None:
        leaf = self.base / ("a" * 16 + ".json")
        with self._divergent_resolve():
            self.assertIsNone(self.leaf_is_safe(self.base, leaf),
                              "a leaf INSIDE base must never be refused just "
                              "because resolve() spelled it differently")

    def test_real_escape_is_still_refused(self) -> None:
        victim = self.root / "victim.json"
        out = self.leaf_is_safe(self.base, self.base / ".." / "victim.json")
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
        self.assertEqual(out.subtype, "path")
        self.assertFalse(victim.exists())

    def test_absolute_outside_leaf_is_still_refused(self) -> None:
        out = self.leaf_is_safe(self.base, self.root / "victim.json")
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.INVALID_INPUT)

    def test_symlinked_component_is_still_refused(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        try:
            (self.base / "sub").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this platform/user")
        out = self.leaf_is_safe(self.base, self.base / "sub" / "x.json")
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
        self.assertIn("symlink", out.message)

    def test_symlinked_leaf_is_still_refused(self) -> None:
        victim = self.root / "victim.json"
        victim.write_text("{}", encoding="utf-8")
        leaf = self.base / ("b" * 16 + ".json")
        try:
            leaf.symlink_to(victim)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this platform/user")
        out = self.leaf_is_safe(self.base, leaf)
        self.assertIsInstance(out, TrackerError)
        self.assertIn("symlink", out.message)

    def _tagged_lstat(self, tagged: Path, tag: int):
        """Patch: os.lstat reports `tagged` the way Windows marks an NTFS
        junction - a nonzero st_reparse_tag on a component whose mode is NOT
        S_ISLNK (junctions are reparse points, not symlinks, so the symlink
        check alone never sees them). POSIX-runnable stand-in."""
        import os
        import types

        real_lstat = os.lstat

        def fake_lstat(path, *args, **kwargs):
            st = real_lstat(path, *args, **kwargs)
            if Path(path) == tagged:
                return types.SimpleNamespace(st_mode=st.st_mode,
                                             st_reparse_tag=tag)
            return st

        return mock.patch("os.lstat", fake_lstat)

    def test_reparse_point_component_is_refused(self) -> None:
        junction = self.base / "junction"
        junction.mkdir()
        io_reparse_tag_mount_point = 0xA0000003  # NTFS junction/mount point
        with self._tagged_lstat(junction, io_reparse_tag_mount_point):
            out = self.leaf_is_safe(self.base, junction / "x.json")
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
        self.assertEqual(out.subtype, "path")
        self.assertIn("reparse", out.message)

    def test_zero_reparse_tag_is_not_refused(self) -> None:
        plain = self.base / "plain"
        plain.mkdir()
        with self._tagged_lstat(plain, 0):
            self.assertIsNone(
                self.leaf_is_safe(self.base, plain / "x.json"),
                "st_reparse_tag == 0 (or absent, as on POSIX) must stay a "
                "no-op - only a real reparse point may be refused")
