"""Lifecycle facade: tracker sync --op push|pull|reconcile|comment (fn-140.7).

Fake transport = injected executor seam (same harness as lifecycle/syncbody).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import facade as F  # noqa: E402
from flowctl_tracker import syncbody as SB  # noqa: E402
from flowctl_tracker import wire as W  # noqa: E402
from flowctl_tracker.lifecycle import verbs as LV  # noqa: E402
from flowctl_tracker.types import ErrorClass, Response, TrackerError  # noqa: E402


def ok(body) -> Response:
    return Response(200, {}, json.dumps(body).encode() if body is not None else b"", 0.01)


def empty_ok() -> Response:
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


GH_NODE = "I_kwDOTestNode1"
GL_ID = 84817009
LN_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
JR_ID = "10042"
FLOW_BODY = "## Goal\nShip it.\n"
SPEC_ID = "fn-1-demo"


def gh_cfg() -> dict:
    return {"tracker": {"type": "github",
                        "resolved": {"destination": {"owner": "o", "repo": "r"}}}}


def gl_cfg() -> dict:
    return {"tracker": {"type": "gitlab",
                        "resolved": {"destination": {
                            "projectId": 1, "projectPath": "g/p",
                            "host": "gitlab.com", "namespaceId": 9}}}}


def ln_cfg(*, preferred: str | None = None) -> dict:
    per = {"teamId": "team-1", "teamKey": "WOR"}
    if preferred is not None:
        per["preferredTransport"] = preferred
    return {"tracker": {"type": "linear", "perTracker": per,
                        "resolved": {"destination": {
                            "teamId": "team-1", "teamKey": "WOR",
                            "stateIds": {"backlog": "s-b", "todo": "s-t",
                                         "in_progress": "s-i", "in_review": "s-r",
                                         "done": "s-d"}}}}}


def jr_cfg() -> dict:
    return {"tracker": {"type": "jira",
                        "resolved": {"destination": {
                            "baseUrl": "https://ex.atlassian.net",
                            "projectKey": "SCRUM", "projectId": "10000",
                            "issueTypeId": "10001", "apiVersion": 2,
                            "statusIds": {"backlog": "1", "todo": "2",
                                          "in_progress": "3", "in_review": "4",
                                          "done": "5"}}}}}


def gql_issue(issue) -> Response:
    return ok({"data": {"issue": issue}})


def gql_update(issue) -> Response:
    return ok({"data": {"issueUpdate": {"success": True, "issue": issue}}})


def _gh_issue(body: str, *, labels=None) -> dict:
    return {"id": 999001, "node_id": GH_NODE, "number": 42, "title": "Demo",
            "body": body, "html_url": "https://github.com/o/r/issues/42",
            "labels": labels if labels is not None else [{"name": "status:backlog"}],
            "state": "open"}


def _gl_issue(body: str) -> dict:
    return {"id": GL_ID, "iid": 12, "title": "Demo", "description": body,
            "web_url": "https://gitlab.com/g/p/-/issues/12",
            "labels": ["status:backlog"], "state": "opened"}


def _ln_issue(body: str) -> dict:
    return {"id": LN_UUID, "identifier": "WOR-17", "title": "Demo",
            "description": body, "url": "https://linear.app/x/issue/WOR-17",
            "state": {"id": "s-b", "name": "Backlog", "type": "backlog"},
            "labels": {"nodes": []}, "assignee": None}


def _jr_issue(body: str) -> dict:
    return {"id": JR_ID, "key": "SCRUM-1",
            "fields": {"summary": "Demo", "description": body, "labels": [],
                       "status": {"id": "1", "name": "Backlog",
                                  "statusCategory": {"key": "new"}}}}


def _write_flow(flow: Path, config: dict, *, spec_id: str = SPEC_ID,
                tracker: dict | None = None, spec_md: str = FLOW_BODY,
                tasks: list | None = None) -> Path:
    (flow / "specs").mkdir(parents=True, exist_ok=True)
    (flow / "config.json").write_text(json.dumps(config), encoding="utf-8")
    base = {
        "id": None, "identifier": None, "url": None,
        "lastSyncedAt": None, "depRelations": [], "linkState": "unlinked",
        "baseHashFlow": None, "baseHashTracker": None,
        "mergeBaseFlow": None, "mergeBaseTracker": None,
    }
    if tracker is not None:
        base.update(tracker)
    spec = {
        "id": spec_id, "title": "Demo", "status": "open",
        "branch_name": spec_id, "tracker": base,
    }
    path = flow / "specs" / f"{spec_id}.json"
    path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    (flow / "specs" / f"{spec_id}.md").write_text(spec_md, encoding="utf-8")
    if tasks:
        (flow / "tasks").mkdir(parents=True, exist_ok=True)
        for i, t in enumerate(tasks, 1):
            tid = f"{spec_id}.{i}"
            (flow / "tasks" / f"{tid}.json").write_text(
                json.dumps({"id": tid, "status": t.get("status", "todo")}),
                encoding="utf-8")
    return path


def _linked(**kw) -> dict:
    d = {"id": GH_NODE, "identifier": "#42", "url": "https://x/42",
         "lastSyncedAt": None, "depRelations": [], "linkState": "linked",
         "mergeBaseFlow": None, "mergeBaseTracker": None,
         "baseHashFlow": None, "baseHashTracker": None}
    d.update(kw)
    return d


def _receipts(flow: Path) -> list[dict]:
    runs = flow / "sync-runs"
    if not runs.is_dir():
        return []
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(runs.glob("sync-*.json"))]


def _flow_file(tmp: Path, body: str = FLOW_BODY) -> str:
    p = tmp / "flow-body.md"
    p.write_text(body, encoding="utf-8")
    return str(p)


def _body_file(tmp: Path, body: str) -> str:
    p = tmp / "body.md"
    p.write_text(body, encoding="utf-8")
    return str(p)


# Shared parent-read responses for a no-op push (body already matches + status agree).
def _noop_push_responses(body: str = FLOW_BODY) -> dict:
    parent = _gh_issue(body)
    return {
        "sync-body-parent-read": ok(parent),
        "wire-parent-read": ok(parent),
        "status-parent-read": ok(parent),
        "merge-evidence": ok([]),
    }


# ---------------------------------------------------------------------------
# Cross-adapter fixture builders (shapes mirrored from syncbody/wire tests)
# ---------------------------------------------------------------------------

def _parent_resp(provider: str, issue: dict) -> Response:
    if provider == "linear":
        return gql_issue(issue)
    return ok(issue)


def _update_resp(provider: str, issue: dict) -> Response:
    if provider == "linear":
        return gql_update(issue)
    if provider == "jira":
        return empty_ok()
    return ok(issue)


def _comment_list_empty(provider: str) -> Response:
    if provider == "linear":
        return ok({"data": {"issue": {
            "id": LN_UUID,
            "comments": {"nodes": [],
                         "pageInfo": {"hasNextPage": False, "endCursor": None}},
        }}})
    if provider == "jira":
        return ok({"comments": [], "total": 0, "startAt": 0, "maxResults": 50})
    return ok([])


def _comment_list_with(provider: str, body: str) -> Response:
    if provider == "linear":
        return ok({"data": {"issue": {
            "id": LN_UUID,
            "comments": {"nodes": [{"id": "c1", "body": body, "url": "u"}],
                         "pageInfo": {"hasNextPage": False, "endCursor": None}},
        }}})
    if provider == "jira":
        return ok({"comments": [{"id": "c1", "body": body}],
                   "total": 1, "startAt": 0, "maxResults": 50})
    if provider == "gitlab":
        return ok([{"id": 1, "body": body, "system": False,
                    "noteable_id": GL_ID}])
    return ok([{"id": 99, "body": body, "html_url": "https://x/c/99"}])


def _comment_add_resp(provider: str, body: str):
    def capture(req):
        if provider == "linear":
            posted = json.loads(req.body)["variables"]["input"]["body"]
            return ok({"data": {"commentCreate": {
                "success": True,
                "comment": {"id": "c1", "body": posted, "url": "u",
                            "issue": {"id": LN_UUID}}}}})
        if provider == "gitlab":
            posted = json.loads(req.body)["body"]
            return ok({"id": 1, "body": posted, "noteable_id": GL_ID})
        if provider == "jira":
            posted = json.loads(req.body)["body"]
            return ok({"id": "c1", "body": posted})
        posted = json.loads(req.body)["body"]
        return ok({"id": 99, "body": posted, "html_url": "https://x/c/99"})
    return capture


def _posted_body(provider: str, req) -> str:
    payload = json.loads(req.body)
    if provider == "linear":
        return payload["variables"]["input"]["body"]
    return payload["body"]


ADAPTERS = [
    ("github", gh_cfg, GH_NODE, "#42", _gh_issue),
    ("gitlab", gl_cfg, str(GL_ID), "g/p#12", _gl_issue),
    ("linear", ln_cfg, LN_UUID, "WOR-17", _ln_issue),
    ("jira", jr_cfg, JR_ID, "SCRUM-1", _jr_issue),
]


def _status_noop_responses(provider: str, issue: dict) -> dict:
    """Parent already matches flow backlog; merge-evidence empty."""
    parent = _parent_resp(provider, issue)
    return {
        "sync-body-parent-read": parent,
        "wire-parent-read": parent,
        "wire-read": parent,
        "status-parent-read": parent,
        "merge-evidence": ok([]),
    }


# ---------------------------------------------------------------------------
# Input matrix
# ---------------------------------------------------------------------------

class InputMatrix(unittest.TestCase):
    def test_forbidden_inputs_invalid_before_any_request(self) -> None:
        cases = [
            ("push", {"body_file": "x"}, "body-file"),
            ("pull", {"flow_file": "x"}, "flow-file"),
            ("comment", {"flow_file": "x"}, "flow-file"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked())
            for op, kwargs, needle in cases:
                ex = fake_execute({})
                out = F.sync(flow, SPEC_ID, op=op, event="work.done",
                             execute=ex, **kwargs)
                self.assertIsInstance(out, TrackerError, op)
                self.assertIs(out.cls, ErrorClass.INVALID_INPUT, op)
                self.assertIn(needle, out.message, op)
                self.assertEqual(ex.calls, [], op)

    def test_required_inputs_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked())
            ex = fake_execute({})
            out = F.sync(flow, SPEC_ID, op="push", event="work.done", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
            self.assertIn("flow-file", out.message)
            self.assertEqual(ex.calls, [])

            out2 = F.sync(flow, SPEC_ID, op="comment", event="work.done",
                          execute=ex)
            self.assertIsInstance(out2, TrackerError)
            self.assertIn("body-file", out2.message)

            out3 = F.sync(flow, SPEC_ID, op="reconcile", event="work.done",
                          flow_file="x", execute=ex)
            self.assertIsInstance(out3, TrackerError)
            self.assertIn("body-file", out3.message)


# ---------------------------------------------------------------------------
# Push: create-if-unlinked + one aggregate receipt
# ---------------------------------------------------------------------------

class PushFacade(unittest.TestCase):
    def test_push_unlinked_creates_then_syncs_one_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg())  # unlinked
            ff = _flow_file(root)
            ex = fake_execute({
                "lifecycle-create": ok({
                    "id": 1, "node_id": GH_NODE, "number": 42,
                    "html_url": "https://github.com/o/r/issues/42",
                }),
                **_noop_push_responses(FLOW_BODY),
            })
            out = F.sync(flow, SPEC_ID, op="push", event="work.firstClaim",
                         flow_file=ff, execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["op"], "push")
            self.assertIn("create", out["completed_steps"])
            self.assertIn("sync-body", out["completed_steps"])
            self.assertIn("status", out["completed_steps"])
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1, receipts)
            self.assertEqual(receipts[0]["event"], "work.firstClaim")
            self.assertEqual(receipts[0]["type"], "sync")
            saved = json.loads(
                (flow / "specs" / f"{SPEC_ID}.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["tracker"]["id"], GH_NODE)
            self.assertEqual(saved["tracker"]["linkState"], "linked")

    def test_push_linked_is_idempotent_no_second_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked(
                mergeBaseFlow=FLOW_BODY,
                mergeBaseTracker=FLOW_BODY.rstrip("\n"),
            ))
            ff = _flow_file(root)
            ex = fake_execute(_noop_push_responses(FLOW_BODY))
            out = F.sync(flow, SPEC_ID, op="push", event="work.done",
                         flow_file=ff, execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertFalse(any(c.op == "lifecycle-create" for c in ex.calls))
            self.assertEqual(len(_receipts(flow)), 1)

    def test_partial_success_readback_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked(
                mergeBaseFlow="PRIOR\n", mergeBaseTracker="PRIOR",
            ))
            ff = _flow_file(root, "NEW BODY\n")
            parent = _gh_issue("old")
            ex = fake_execute({
                "sync-body-parent-read": ok(parent),
                "wire-parent-read": ok(parent),
                "wire-update": ok(_gh_issue("written")),
                "wire-read": TrackerError(ErrorClass.TRANSPORT, "readback boom",
                                          subtype="readback"),
            })
            payload, code = F.run(
                flow, spec_id=SPEC_ID, op="push", event="work.done",
                flow_file=ff, execute=ex)
            data = json.loads(payload)
            self.assertFalse(data["success"])
            self.assertIn("completed_steps", data["data"])
            self.assertIn("wire-update", data["data"]["completed_steps"])
            self.assertEqual(data["class"], "transport")
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["status"], "errored")
            self.assertEqual(receipts[0]["event"], "work.done")
            self.assertNotEqual(code, 0)


# ---------------------------------------------------------------------------
# Partial create failure: create lands, locked link write fails
# ---------------------------------------------------------------------------

class PartialCreateReceipt(unittest.TestCase):
    """lifecycle_create lands the provider issue but the locked link write
    fails. The facade must NOT return that TrackerError bare (no receipt):
    it must write ONE event-tagged aggregate receipt whose payload carries
    completed_steps=["create"] plus the created identity - durable evidence
    of what landed, so sync check sees the lifecycle event and an automated
    retry is not flying blind."""

    def _partial_create(self, *, op: str, event: str, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg())  # unlinked
            files = {}
            if "flow_file" in kw:
                files["flow_file"] = _flow_file(root)
            if "body_file" in kw:
                files["body_file"] = _body_file(
                    root, "evidence=abc1234\n**done** - shipped.\n")
            ex = fake_execute({
                "lifecycle-create": ok({
                    "id": 1, "node_id": GH_NODE, "number": 42,
                    "html_url": "https://github.com/o/r/issues/42",
                }),
            })
            boom = TrackerError(ErrorClass.TRANSPORT, "link write boom",
                                subtype="disk")
            with mock.patch.object(LV, "_locked_tracker_write",
                                   return_value=boom):
                out = F.sync(flow, SPEC_ID, op=op, event=event,
                             execute=ex, **files)
            return out, _receipts(flow)

    def _assert_partial_receipt(self, out, receipts, *, event: str) -> None:
        self.assertIsInstance(out, TrackerError)
        self.assertEqual(out.details["completed_steps"], ["create"])
        self.assertEqual(out.details["id"], GH_NODE)
        self.assertEqual(len(receipts), 1, receipts)
        receipt = receipts[0]
        self.assertEqual(receipt["type"], "sync")
        self.assertEqual(receipt["event"], event)
        self.assertEqual(receipt["status"], "errored")
        self.assertEqual(receipt["tracker_id"], GH_NODE)
        self.assertEqual(receipt["details"]["completed_steps"], ["create"])
        self.assertEqual(receipt["details"]["id"], GH_NODE)
        self.assertEqual(receipt["details"]["identifier"], "#42")

    def test_push_create_lands_link_write_fails_one_receipt(self) -> None:
        out, receipts = self._partial_create(
            op="push", event="work.firstClaim", flow_file=True)
        self._assert_partial_receipt(out, receipts, event="work.firstClaim")

    def test_comment_create_lands_link_write_fails_one_receipt(self) -> None:
        out, receipts = self._partial_create(
            op="comment", event="work.done", body_file=True)
        self._assert_partial_receipt(out, receipts, event="work.done")


# ---------------------------------------------------------------------------
# Receipt write failure: mutation landed but sync-runs is unwritable
# ---------------------------------------------------------------------------

class ReceiptWriteFailure(unittest.TestCase):
    """The remote mutation lands but the aggregate receipt write fails
    (unwritable sync-runs). ZERO receipts exist, so sync check reports the
    lifecycle event missing - the returned error must say so honestly
    (receipt_status "unwritten" + a structured receipt_write_failed marker)
    while keeping the original completed_steps and identity evidence
    verbatim. It must never claim an errored receipt was written."""

    def _block_sync_runs(self, flow: Path) -> None:
        # A regular file where the receipts dir belongs: mkdir(parents=True)
        # inside atomic_write_json raises FileExistsError (an OSError), the
        # deterministic cross-platform stand-in for an unwritable sync-runs.
        (flow / "sync-runs").write_text("not a directory", encoding="utf-8")

    def _assert_unwritten(self, out, flow: Path) -> None:
        self.assertIsInstance(out, TrackerError)
        self.assertEqual(out.details["receipt_status"], "unwritten")
        marker = out.details["receipt_write_failed"]
        self.assertEqual(marker["class"], "transport")
        self.assertEqual(marker["subtype"], "write")
        self.assertIn("atomic write failed", marker["message"])
        self.assertEqual(_receipts(flow), [])  # nothing claims a receipt exists

    def test_partial_create_then_receipt_write_fails(self) -> None:
        # create lands, locked link write fails, AND the partial-success
        # receipt write fails: original error + evidence survive verbatim.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg())  # unlinked
            self._block_sync_runs(flow)
            ff = _flow_file(root)
            ex = fake_execute({
                "lifecycle-create": ok({
                    "id": 1, "node_id": GH_NODE, "number": 42,
                    "html_url": "https://github.com/o/r/issues/42",
                }),
            })
            boom = TrackerError(ErrorClass.TRANSPORT, "link write boom",
                                subtype="disk")
            with mock.patch.object(LV, "_locked_tracker_write",
                                   return_value=boom):
                out = F.sync(flow, SPEC_ID, op="push",
                             event="work.firstClaim", flow_file=ff,
                             execute=ex)
            self._assert_unwritten(out, flow)
            # The original error and partial-success evidence are intact.
            self.assertIs(out.cls, ErrorClass.TRANSPORT)
            self.assertEqual(out.message, "link write boom")
            self.assertEqual(out.subtype, "disk")
            self.assertEqual(out.details["completed_steps"], ["create"])
            self.assertEqual(out.details["id"], GH_NODE)
            self.assertEqual(out.details["identifier"], "#42")

    def test_success_path_receipt_write_fails_surfaces_unwritten(self) -> None:
        # Every remote step succeeds; only the final aggregate receipt write
        # fails. The op must NOT return ok: the run surfaces the write
        # failure with completed_steps evidence and receipt_status unwritten.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg())  # unlinked
            self._block_sync_runs(flow)
            ff = _flow_file(root)
            ex = fake_execute({
                "lifecycle-create": ok({
                    "id": 1, "node_id": GH_NODE, "number": 42,
                    "html_url": "https://github.com/o/r/issues/42",
                }),
                **_noop_push_responses(FLOW_BODY),
            })
            payload, code = F.run(
                flow, spec_id=SPEC_ID, op="push", event="work.firstClaim",
                flow_file=ff, execute=ex)
            self.assertNotEqual(code, 0)
            data = json.loads(payload)
            self.assertFalse(data["success"])
            # sync-check surface: completed_steps evidence survives and
            # receipt_status says no receipt exists.
            for step in ("create", "sync-body", "status"):
                self.assertIn(step, data["data"]["completed_steps"])
            self.assertEqual(data["data"]["receipt_status"], "unwritten")
            self.assertEqual(
                data["details"]["receipt_write_failed"]["class"], "transport")
            self.assertEqual(_receipts(flow), [])


# ---------------------------------------------------------------------------
# Comment marker + dedup
# ---------------------------------------------------------------------------

class CommentFacade(unittest.TestCase):
    def test_comment_marker_dedup_second_run_posts_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked())
            evidence = "abc1234"
            bf = _body_file(root, f"evidence={evidence}\n**done** — shipped.\n")
            marker = (f"<!-- flow-next:sync issue={GH_NODE} spec={SPEC_ID} "
                      f"evt=work.done evidence={evidence} -->")
            parent = _gh_issue(FLOW_BODY)
            # First run: empty list → post
            posted_bodies = []

            def capture_add(req):
                posted_bodies.append(json.loads(req.body)["body"])
                return ok({"id": 99, "body": posted_bodies[-1],
                           "html_url": "https://x/c/99"})

            ex1 = fake_execute({
                "wire-parent-read": ok(parent),
                "wire-comment-list": ok([]),
                "wire-comment-add": capture_add,
            })
            out1 = F.sync(flow, SPEC_ID, op="comment", event="work.done",
                          body_file=bf, execute=ex1)
            self.assertNotIsInstance(out1, TrackerError)
            self.assertTrue(out1["posted"])
            self.assertEqual(len(posted_bodies), 1)
            self.assertTrue(posted_bodies[0].startswith(marker))
            self.assertEqual(len(_receipts(flow)), 1)

            # Second run: list returns the posted comment → dedup, no add
            ex2 = fake_execute({
                "wire-parent-read": ok(parent),
                "wire-comment-list": ok([{
                    "id": 99, "body": posted_bodies[0],
                    "html_url": "https://x/c/99",
                }]),
            })
            out2 = F.sync(flow, SPEC_ID, op="comment", event="work.done",
                          body_file=bf, execute=ex2)
            self.assertNotIsInstance(out2, TrackerError)
            self.assertFalse(out2["posted"])
            self.assertTrue(out2["deduped"])
            self.assertFalse(any(c.op == "wire-comment-add" for c in ex2.calls))
            self.assertEqual(len(_receipts(flow)), 2)

    def test_comment_truncated_scan_without_marker_refuses_post(self) -> None:
        """A truncated dedup scan proves nothing about marker absence:
        the facade must refuse to post rather than risk a duplicate."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked())
            bf = _body_file(root, "evidence=abc1234\n**done** - shipped.\n")

            # Every page comes back full (no marker anywhere), so the REST
            # drain hits _MAX_PAGES and reports truncated=True.
            def full_page(req):
                return ok([{"id": i, "body": f"noise {i}"} for i in range(100)])

            ex = fake_execute({
                "wire-parent-read": ok(_gh_issue(FLOW_BODY)),
                "wire-comment-list": full_page,
            })
            out = F.sync(flow, SPEC_ID, op="comment", event="work.done",
                         body_file=bf, execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertEqual(out.cls, ErrorClass.TRANSPORT)
            self.assertEqual(out.subtype, "dedup_truncated")
            self.assertFalse(out.auto_retryable)
            self.assertTrue((out.details or {}).get("truncated"))
            self.assertEqual((out.details or {}).get("event"), "work.done")
            self.assertEqual((out.details or {}).get("issue"), GH_NODE)
            self.assertFalse(any(c.op == "wire-comment-add" for c in ex.calls))
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["status"], "errored")
            # The marker claim is released on the refusal path too - a
            # leftover pending claim would force the next invocation to
            # wait out the stale window.
            self.assertEqual(
                list((flow / "create-first").glob("comment-*.json")), [])

    def test_comment_concurrent_same_marker_single_add_loser_conflicts(self) -> None:
        """Two workers running the comment facade for the same issue, event
        and evidence: the marker claim is taken BEFORE the dedup scan, so a
        second invocation arriving while the first is between its scan and
        its comment-add backs off with a structured CONFLICT instead of
        posting the same marked comment twice."""
        from flowctl_tracker.facade.ops import _comment_claim_path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked())
            evidence = "abc1234"
            bf = _body_file(root, f"evidence={evidence}\n**done** - shipped.\n")
            rec_path = _comment_claim_path(
                flow, issue=GH_NODE, spec=SPEC_ID, event="work.done",
                evidence=evidence)
            posted_bodies = []
            inner: dict = {}

            def capture_add(req):
                posted_bodies.append(json.loads(req.body)["body"])
                return ok({"id": 99, "body": posted_bodies[-1],
                           "html_url": "https://x/c/99"})

            def racing_list(req):
                # The claim must be durable BEFORE the scan runs...
                claim = json.loads(rec_path.read_text(encoding="utf-8"))
                self.assertEqual(claim.get("status"), "pending")
                # ...so a second worker racing in mid-sequence refuses
                # instead of posting a duplicate marked comment.
                inner["ex"] = fake_execute({})  # any wire call would raise
                inner["out"] = F.sync(
                    flow, SPEC_ID, op="comment", event="work.done",
                    body_file=bf, execute=inner["ex"])
                return ok([])

            ex = fake_execute({
                "wire-parent-read": ok(_gh_issue(FLOW_BODY)),
                "wire-comment-list": racing_list,
                "wire-comment-add": capture_add,
            })
            out = F.sync(flow, SPEC_ID, op="comment", event="work.done",
                         body_file=bf, execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertTrue(out["posted"])
            self.assertEqual(len(posted_bodies), 1, "exactly ONE comment-add")

            raced = inner["out"]
            self.assertIsInstance(raced, TrackerError)
            self.assertIs(raced.cls, ErrorClass.CONFLICT)
            self.assertEqual(raced.subtype, "comment_in_flight")
            self.assertTrue(raced.auto_retryable)
            self.assertEqual((raced.details or {}).get("specId"), SPEC_ID)
            self.assertIn("claim", raced.details or {})
            self.assertEqual(inner["ex"].calls, [],
                             "loser backs off before any wire call")
            # Winner released the claim on completion.
            self.assertFalse(rec_path.exists())

    def test_comment_stale_dead_pid_claim_is_reclaimed_and_posts(self) -> None:
        """A crashed run's leftover claim (dead pid on this host, past the
        stale window) must not wedge the marker: it is reclaimed and the
        comment posts."""
        import socket
        import time
        from flowctl_tracker.facade.ops import _comment_claim_path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked())
            evidence = "abc1234"
            bf = _body_file(root, f"evidence={evidence}\n**done** - shipped.\n")
            rec_path = _comment_claim_path(
                flow, issue=GH_NODE, spec=SPEC_ID, event="work.done",
                evidence=evidence)
            rec_path.parent.mkdir(parents=True)
            # pid 0 is never alive; claimedAt is past the stale window.
            rec_path.write_text(json.dumps({
                "specId": SPEC_ID, "status": "pending", "pid": 0,
                "host": socket.gethostname(),
                "claimedAt": time.time() - 999,
                "event": "work.done", "transport": "github"}),
                encoding="utf-8")
            posted_bodies = []

            def capture_add(req):
                posted_bodies.append(json.loads(req.body)["body"])
                return ok({"id": 99, "body": posted_bodies[-1],
                           "html_url": "https://x/c/99"})

            ex = fake_execute({
                "wire-parent-read": ok(_gh_issue(FLOW_BODY)),
                "wire-comment-list": ok([]),
                "wire-comment-add": capture_add,
            })
            out = F.sync(flow, SPEC_ID, op="comment", event="work.done",
                         body_file=bf, execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertTrue(out["posted"])
            self.assertEqual(len(posted_bodies), 1)
            self.assertFalse(rec_path.exists(), "reclaimed claim released")


class MarkerRoundTrip(unittest.TestCase):
    """Marker fields must round-trip through _MARKER_RE (single \\S+ tokens).
    A whitespace-embedded event/evidence posts fine once but every retry
    fails comments_have_marker() and posts a duplicate - so such values are
    rejected structurally BEFORE any wire call and before any claim file."""

    def _no_claims(self, flow: Path) -> None:
        cf = flow / "create-first"
        self.assertEqual(
            list(cf.glob("comment-*.json")) if cf.is_dir() else [], [])

    def test_comment_evidence_with_whitespace_rejected_before_wire(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked())
            bf = _body_file(root, "evidence=abc def\n**done** - shipped.\n")
            ex = fake_execute({})  # any wire call would raise
            out = F.sync(flow, SPEC_ID, op="comment", event="work.done",
                         body_file=bf, execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
            self.assertEqual(out.subtype, "evidence")
            self.assertEqual((out.details or {}).get("value"), "abc def")
            self.assertEqual(ex.calls, [], "rejected before any wire call")
            self._no_claims(flow)
            self.assertEqual(_receipts(flow), [])

    def test_event_with_whitespace_rejected_before_wire(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked())
            bf = _body_file(root, "evidence=abc1234\n**done** - shipped.\n")
            ex = fake_execute({})
            out = F.sync(flow, SPEC_ID, op="comment", event="work done",
                         body_file=bf, execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
            self.assertEqual(out.subtype, "event")
            self.assertEqual(ex.calls, [], "rejected before any wire call")
            self._no_claims(flow)
            self.assertEqual(_receipts(flow), [])
            # Non-comment ops share the same boundary (event is a receipt key).
            out2 = F.sync(flow, SPEC_ID, op="pull", event="work\tdone",
                          execute=ex)
            self.assertIsInstance(out2, TrackerError)
            self.assertEqual(out2.subtype, "event")
            self.assertEqual(ex.calls, [])

    def test_marker_safe_value_posts_and_dedups_on_retry(self) -> None:
        """Round-trip: the emitted marker parses under _MARKER_RE with the
        original field values, and the retry's scan dedups to a noop."""
        from flowctl_tracker.facade.helpers import _MARKER_RE, comments_have_marker
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked())
            evidence = "abc1234"
            bf = _body_file(root, f"evidence={evidence}\n**done** - shipped.\n")
            posted_bodies = []

            def capture_add(req):
                posted_bodies.append(json.loads(req.body)["body"])
                return ok({"id": 99, "body": posted_bodies[-1],
                           "html_url": "https://x/c/99"})

            ex1 = fake_execute({
                "wire-parent-read": ok(_gh_issue(FLOW_BODY)),
                "wire-comment-list": ok([]),
                "wire-comment-add": capture_add,
            })
            out1 = F.sync(flow, SPEC_ID, op="comment", event="work.done",
                          body_file=bf, execute=ex1)
            self.assertNotIsInstance(out1, TrackerError)
            self.assertTrue(out1["posted"])
            self.assertEqual(len(posted_bodies), 1)
            m = _MARKER_RE.search(posted_bodies[0])
            self.assertIsNotNone(m, "emitted marker must parse")
            self.assertEqual(m.group("issue"), GH_NODE)
            self.assertEqual(m.group("spec"), SPEC_ID)
            self.assertEqual(m.group("evt"), "work.done")
            self.assertEqual(m.group("evidence"), evidence)
            self.assertTrue(comments_have_marker(
                [{"body": posted_bodies[0]}], issue=GH_NODE, spec=SPEC_ID,
                event="work.done", evidence=evidence))

            ex2 = fake_execute({
                "wire-parent-read": ok(_gh_issue(FLOW_BODY)),
                "wire-comment-list": ok([{
                    "id": 99, "body": posted_bodies[0],
                    "html_url": "https://x/c/99",
                }]),
            })
            out2 = F.sync(flow, SPEC_ID, op="comment", event="work.done",
                          body_file=bf, execute=ex2)
            self.assertNotIsInstance(out2, TrackerError)
            self.assertFalse(out2["posted"])
            self.assertTrue(out2["deduped"])
            self.assertFalse(
                any(c.op == "wire-comment-add" for c in ex2.calls))


# ---------------------------------------------------------------------------
# MCP rung
# ---------------------------------------------------------------------------

class McpRung(unittest.TestCase):
    def test_mcp_push_create_returns_external_action_no_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, ln_cfg(preferred="mcp"))  # unlinked
            ff = _flow_file(root)
            ex = fake_execute({})
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("LINEAR_API_KEY", None)
                out = F.sync(flow, SPEC_ID, op="push", event="work.firstClaim",
                             flow_file=ff, execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.EXTERNAL_ACTION_REQUIRED)
            self.assertEqual(out.details["action"], "create")
            self.assertEqual(out.details["payload"]["title"], "Demo")
            self.assertEqual(out.details["payload"]["body"], FLOW_BODY)
            self.assertEqual(ex.calls, [])
            self.assertEqual(_receipts(flow), [])

    def test_mcp_detect_via_absent_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, ln_cfg())  # no preferredTransport
            ff = _flow_file(root)
            ex = fake_execute({})
            env = {k: v for k, v in os.environ.items() if k != "LINEAR_API_KEY"}
            with mock.patch.dict(os.environ, env, clear=True):
                out = F.sync(flow, SPEC_ID, op="push", event="capture",
                             flow_file=ff, execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.EXTERNAL_ACTION_REQUIRED)
            self.assertEqual(ex.calls, [])


# ---------------------------------------------------------------------------
# Reconcile completes identifier_only
# ---------------------------------------------------------------------------

class ReconcileFacade(unittest.TestCase):
    def test_reconcile_completes_identifier_only_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, ln_cfg(preferred="graphql"), tracker={
                "id": None, "identifier": "WOR-17", "url": None,
                "lastSyncedAt": None, "depRelations": [],
                "linkState": "identifier_only",
                "mergeBaseFlow": None, "mergeBaseTracker": None,
            })
            ff = _flow_file(root)
            bf = _body_file(root, FLOW_BODY)
            issue = {
                "id": LN_UUID, "identifier": "WOR-17", "title": "Demo",
                "description": FLOW_BODY,
                "url": "https://linear.app/x/issue/WOR-17",
                "state": {"id": "s-b", "name": "Backlog", "type": "backlog"},
            }

            def gql(req):
                payload = json.loads(req.body)
                q = payload.get("query") or ""
                if "issue(id:" in q and "IssueCreateInput" not in q:
                    # resolve UUID or wire read / parent
                    return ok({"data": {"issue": issue}})
                if "issueUpdate" in q:
                    return ok({"data": {"issueUpdate": {
                        "success": True, "issue": issue}}})
                return ok({"data": {"issue": issue}})

            ex = fake_execute({
                "lifecycle-resolve-uuid": gql,
                "wire-parent-read": gql,
                "sync-body-parent-read": gql,
                "wire-read": gql,
                "status-parent-read": gql,
                "status-state-read": gql,
                "merge-evidence": ok([]),
            })
            with mock.patch.dict(os.environ, {"LINEAR_API_KEY": "lin_test"}):
                out = F.sync(flow, SPEC_ID, op="reconcile", event="plan",
                             flow_file=ff, body_file=bf, execute=ex)
            self.assertNotIsInstance(out, TrackerError, out)
            self.assertIn("complete-identifier-only", out["completed_steps"])
            saved = json.loads(
                (flow / "specs" / f"{SPEC_ID}.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["tracker"]["id"], LN_UUID)
            self.assertEqual(saved["tracker"]["linkState"], "linked")
            self.assertEqual(len(_receipts(flow)), 1)


# ---------------------------------------------------------------------------
# Pull + conflict/degradation structural
# ---------------------------------------------------------------------------

class PullAndStructural(unittest.TestCase):
    def test_pull_snapshots_without_tracker_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked(),
                        spec_md=FLOW_BODY)
            parent = _gh_issue("tracker side body")
            ex = fake_execute({
                "wire-read": ok(parent),
            })
            out = F.sync(flow, SPEC_ID, op="pull", event="interview",
                         execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["op"], "pull")
            self.assertFalse(any(c.op == "wire-update" for c in ex.calls))
            self.assertEqual(len(_receipts(flow)), 1)
            self.assertEqual(_receipts(flow)[0]["status"], "pulled")

    def test_pull_reuses_wire_read_snapshot_no_second_parent_read(self) -> None:
        """Paired-snapshot invariant: returned body == stored mergeBaseTracker.

        Fake returns DIFFERENT bodies for wire-read vs sync-body-parent-read;
        after the fix only wire-read fires and the stored half matches it.
        """
        body_a = "first read body\n"
        body_b = "SECOND concurrent edit\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked(),
                        spec_md=FLOW_BODY)
            ex = fake_execute({
                "wire-read": ok(_gh_issue(body_a)),
                # Would poison the snapshot if sync_body re-read the parent.
                "sync-body-parent-read": ok(_gh_issue(body_b)),
            })
            out = F.sync(flow, SPEC_ID, op="pull", event="interview",
                         execute=ex)
            self.assertNotIsInstance(out, TrackerError, out)
            read_ops = [c.op for c in ex.calls
                        if c.op in ("wire-read", "sync-body-parent-read",
                                    "wire-parent-read")]
            self.assertEqual(read_ops, ["wire-read"])
            expected = SB.trackerBodyForMerge(body_a)
            self.assertEqual(out["wire_read"]["body"], body_a)
            self.assertEqual(out["sync_body"]["mergeBaseTracker"], expected)
            saved = json.loads(
                (flow / "specs" / f"{SPEC_ID}.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["tracker"]["mergeBaseTracker"], expected)
            self.assertEqual(saved["tracker"]["mergeBaseFlow"], FLOW_BODY)
            self.assertNotEqual(expected, SB.trackerBodyForMerge(body_b))

    def test_conflict_surfaces_structurally(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            # Linked, body matches, but status will conflict (done without merge)
            _write_flow(
                flow, gh_cfg(),
                tracker=_linked(mergeBaseFlow=FLOW_BODY,
                                mergeBaseTracker=FLOW_BODY.rstrip("\n")),
                tasks=[{"status": "done"}],
            )
            # Force flow_to_normalized toward in_review via done+no-merge:
            # set spec status done so rows 5–6 → in_review; tracker open+label
            # in_progress → decide conflict on --to in_review vs mismatch...
            # Simpler: durable mismatch on sync-body parent read.
            parent_wrong = dict(_gh_issue(FLOW_BODY), node_id="I_OTHER")
            ff = _flow_file(root)
            # Mutate saved status to done so status step is interesting; but
            # conflict fires first on sync-body durable mismatch.
            path = flow / "specs" / f"{SPEC_ID}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["status"] = "done"
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

            ex = fake_execute({
                "sync-body-parent-read": ok(parent_wrong),
            })
            out = F.sync(flow, SPEC_ID, op="push", event="makePr",
                         flow_file=ff, execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            # Structural: class + details.candidates, not prose-only.
            self.assertIn("candidates", out.details or {})
            self.assertEqual(out.details.get("normalized"), "durable")


# ---------------------------------------------------------------------------
# Pull: wire read inside the claimed sync-body transaction (PR #246 review)
# ---------------------------------------------------------------------------

class PullReadInsideClaim(unittest.TestCase):
    """PR #246 review: op_pull performed its tracker read BEFORE sync_body's
    per-spec claim and injected the pre-claim snapshot. Two pulls overlapping
    a remote edit could then commit a stale pair (the older read claims
    last), and a set-tracker-id repoint in the gap could commit the old
    issue's snapshot under the new locator. The read now runs INSIDE the
    claimed transaction, so the claim and the commit identity guard cover it
    too."""

    NEW_ID = "I_kwDORepointed9"
    NEW_DISPLAY = "#99"

    def _repoint(self, flow: Path) -> None:
        path = flow / "specs" / f"{SPEC_ID}.json"
        spec = json.loads(path.read_text(encoding="utf-8"))
        spec["tracker"].update({
            "id": self.NEW_ID, "identifier": self.NEW_DISPLAY,
            "url": "https://x/99",
            "mergeBaseFlow": None, "mergeBaseTracker": None,
            "baseHashFlow": None, "baseHashTracker": None,
            "lastSyncedAt": None,
        })
        path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

    def test_pull_read_runs_under_claim_racing_pull_conflicts(self) -> None:
        """The wire read fires only while the syncbody claim is pending, so
        an overlapping pull backs off with structured CONFLICT before ANY
        tracker I/O - it can never commit an older read as the newer base."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked(), spec_md=FLOW_BODY)
            rec_path = flow / "create-first" / f"syncbody-{SPEC_ID}.json"
            inner: dict = {}

            def racing_read(req):
                # The claim must be durable BEFORE the tracker read...
                claim = json.loads(rec_path.read_text(encoding="utf-8"))
                self.assertEqual(claim.get("status"), "pending")
                self.assertEqual(claim.get("specId"), SPEC_ID)
                self.assertEqual(claim.get("op"), "sync-body")
                # ...so a second pull racing in around a remote edit refuses
                # (the empty executor would AssertionError on any wire call)
                # instead of committing a stale snapshot last.
                inner["ex"] = fake_execute({})
                inner["out"] = F.sync(flow, SPEC_ID, op="pull",
                                      event="interview",
                                      execute=inner["ex"])
                return ok(_gh_issue("remote edit body\n"))

            ex = fake_execute({"wire-read": racing_read})
            out = F.sync(flow, SPEC_ID, op="pull", event="interview",
                         execute=ex)
            self.assertNotIsInstance(out, TrackerError, out)
            expected = SB.trackerBodyForMerge("remote edit body\n")
            saved = json.loads(
                (flow / "specs" / f"{SPEC_ID}.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["tracker"]["mergeBaseTracker"], expected)

            raced = inner["out"]
            self.assertIsInstance(raced, TrackerError)
            self.assertIs(raced.cls, ErrorClass.CONFLICT)
            self.assertEqual(raced.subtype, "syncbody_in_flight")
            self.assertTrue(raced.auto_retryable)
            self.assertEqual(inner["ex"].calls, [],
                             "loser backs off before any wire call")
            # Loser landed nothing -> receipt-less; winner wrote exactly one.
            self.assertEqual(len(_receipts(flow)), 1)
            self.assertEqual(_receipts(flow)[0]["status"], "pulled")
            self.assertFalse(rec_path.exists(), "claim released")

    def test_pull_repoint_during_read_refuses_stale_commit(self) -> None:
        """set-tracker-id repointing the spec while the pull's read is in
        flight: the transaction's identity guard now covers the read too, so
        the old issue's snapshot is never committed under the new locator."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked(), spec_md=FLOW_BODY)

            def repoint_then_read(req):
                self._repoint(flow)
                return ok(_gh_issue("OLD ISSUE BODY\n"))

            ex = fake_execute({"wire-read": repoint_then_read})
            out = F.sync(flow, SPEC_ID, op="pull", event="interview",
                         execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "identity_changed")
            details = out.details or {}
            self.assertEqual(details.get("transaction"),
                             {"durable": GH_NODE, "display": "#42"})
            self.assertEqual(details.get("current"),
                             {"durable": self.NEW_ID,
                              "display": self.NEW_DISPLAY})
            # Nothing from the old issue persisted under the new identity.
            saved = json.loads(
                (flow / "specs" / f"{SPEC_ID}.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["tracker"]["id"], self.NEW_ID)
            self.assertIsNone(saved["tracker"]["mergeBaseFlow"])
            self.assertIsNone(saved["tracker"]["mergeBaseTracker"])
            # The read landed, so the refusal carries receipt evidence.
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["status"], "errored")
            self.assertFalse(
                (flow / "create-first" / f"syncbody-{SPEC_ID}.json").exists(),
                "claim released after the refused run")

    def test_pull_repoint_before_claim_receipt_records_new_identity(self) -> None:
        """PR #246 review: op_pull captured `durable` BEFORE sync_body's
        claim while the transaction reloads the locator after claiming. A
        set-tracker-id repoint in that gap makes the read and paired base
        correctly target the NEW issue - so the aggregate receipt and the
        returned tracker_id must record that same transaction identity, not
        the stale pre-claim durable."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked(), spec_md=FLOW_BODY)

            orig = SB._claim_sync_body

            def claim_then_repoint(*args, **kwargs):
                out = orig(*args, **kwargs)
                # Relink lands after op_pull captured its pre-claim durable
                # but before the transaction reloads the locator.
                self._repoint(flow)
                return out

            def read_new_issue(req):
                issue = _gh_issue("NEW ISSUE BODY\n")
                issue.update({"node_id": self.NEW_ID, "number": 99})
                return ok(issue)

            ex = fake_execute({"wire-read": read_new_issue})
            with mock.patch.object(SB, "_claim_sync_body",
                                   side_effect=claim_then_repoint):
                out = F.sync(flow, SPEC_ID, op="pull", event="interview",
                             execute=ex)
            self.assertNotIsInstance(out, TrackerError, out)
            self.assertEqual(out["tracker_id"], self.NEW_ID)
            # The paired base committed under the new identity...
            saved = json.loads(
                (flow / "specs" / f"{SPEC_ID}.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["tracker"]["id"], self.NEW_ID)
            self.assertEqual(saved["tracker"]["mergeBaseTracker"],
                             SB.trackerBodyForMerge("NEW ISSUE BODY\n"))
            # ...and the ONE aggregate receipt records that same identity.
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["status"], "pulled")
            self.assertEqual(receipts[0]["tracker_id"], self.NEW_ID)


# ---------------------------------------------------------------------------
# Comment: identity revalidated after the marker claim (PR #246 review)
# ---------------------------------------------------------------------------

class CommentIdentityGuard(unittest.TestCase):
    """PR #246 review: the comment marker claim does not coordinate with the
    link writer, so a set-tracker-id repoint between op_comment's locator
    load and the post let the comment land on the OLD issue (and the receipt
    record the old id). The facade now revalidates the spec identity under
    the shared writer lock after taking the claim, refusing with structured
    CONFLICT (identity_changed) before any wire call."""

    NEW_ID = "I_kwDORepointed9"
    NEW_DISPLAY = "#99"

    def test_comment_repoint_after_claim_refuses_before_any_wire_call(self) -> None:
        from flowctl_tracker.facade import ops as OPS
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked())
            bf = _body_file(root, "evidence=abc1234\n**done** - shipped.\n")

            def repoint(_flow: Path) -> None:
                path = flow / "specs" / f"{SPEC_ID}.json"
                spec = json.loads(path.read_text(encoding="utf-8"))
                spec["tracker"].update({
                    "id": self.NEW_ID, "identifier": self.NEW_DISPLAY,
                    "url": "https://x/99"})
                path.write_text(json.dumps(spec, indent=2) + "\n",
                                encoding="utf-8")

            orig = OPS._claim_comment_marker

            def claim_then_repoint(*args, **kwargs):
                out = orig(*args, **kwargs)
                # Relink lands AFTER the claim is durable but before the
                # dedup scan / post would run.
                repoint(flow)
                return out

            # Empty executor: without the guard this test dies on an
            # unexpected wire-comment-list call against the OLD issue.
            ex = fake_execute({})
            with mock.patch.object(OPS, "_claim_comment_marker",
                                   side_effect=claim_then_repoint):
                out = F.sync(flow, SPEC_ID, op="comment", event="work.done",
                             body_file=bf, execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "identity_changed")
            details = out.details or {}
            self.assertEqual(details.get("transaction"),
                             {"durable": GH_NODE, "display": "#42"})
            self.assertEqual(details.get("current"),
                             {"durable": self.NEW_ID,
                              "display": self.NEW_DISPLAY})
            self.assertEqual(ex.calls, [],
                             "refused before any wire call - no comment-add")
            # The claim (keyed on the OLD issue id) is released by the
            # facade's finally: nothing remains for the stale key.
            self.assertEqual(
                list((flow / "create-first").glob("comment-*.json")), [])
            # Pre-flight refusal with nothing landed: receipt-less.
            self.assertEqual(_receipts(flow), [])

    def test_comment_repoint_during_scan_refuses_before_post(self) -> None:
        """PR #246: the dedup scan is network I/O run outside the lock, so a
        relink can still land while it is in flight. A second locked recheck
        immediately before the mutating comment-add catches it - the post
        never fires against the old issue."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked())
            bf = _body_file(root, "evidence=abc1234\n**done** - shipped.\n")

            def repoint_then_list(req):
                path = flow / "specs" / f"{SPEC_ID}.json"
                spec = json.loads(path.read_text(encoding="utf-8"))
                spec["tracker"].update({
                    "id": self.NEW_ID, "identifier": self.NEW_DISPLAY,
                    "url": "https://x/99"})
                path.write_text(json.dumps(spec, indent=2) + "\n",
                                encoding="utf-8")
                return ok([])

            # No wire-comment-add key: a post against the old issue would
            # die on an unexpected op.
            ex = fake_execute({"wire-comment-list": repoint_then_list})
            out = F.sync(flow, SPEC_ID, op="comment", event="work.done",
                         body_file=bf, execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "identity_changed")
            details = out.details or {}
            self.assertEqual(details.get("transaction"),
                             {"durable": GH_NODE, "display": "#42"})
            self.assertEqual(details.get("current"),
                             {"durable": self.NEW_ID,
                              "display": self.NEW_DISPLAY})
            self.assertFalse(any(c.op == "wire-comment-add" for c in ex.calls))
            self.assertEqual(
                list((flow / "create-first").glob("comment-*.json")), [],
                "claim released on the refusal path")


# ---------------------------------------------------------------------------
# Outer facade claim: one tracker identity across all push/reconcile steps
# ---------------------------------------------------------------------------

class FacadeOuterClaim(unittest.TestCase):
    """PR #246 review: the inner step claims (syncbody-<id>, status-<id>)
    each cover only their own step, so `sync set-tracker-id` could relink the
    spec BETWEEN op_push's body and status steps - the body lands on the old
    issue, the status step targets the new one, and the receipt reloads only
    the new id, presenting the split mutations as one push. The facades now
    hold an OUTER spec-identity claim (`facade-<spec-id>`, distinct from
    every inner key so nesting cannot self-refuse) across the whole
    sequence, and flowctl's relink scan honors it."""

    NEW_UUID = "I_kwDORelinked99"

    def _spec_tracker_id(self, flow: Path) -> str | None:
        spec = json.loads(
            (flow / "specs" / f"{SPEC_ID}.json").read_text(encoding="utf-8"))
        return spec["tracker"]["id"]

    def _relink_cli(self, root: Path) -> "subprocess.CompletedProcess":
        flowctl_py = ROOT / "scripts" / "flowctl.py"
        return subprocess.run(
            [sys.executable, str(flowctl_py), "sync", "set-tracker-id",
             SPEC_ID, self.NEW_UUID, "--json"],
            cwd=root, capture_output=True, text=True, check=False)

    def test_push_relink_between_body_and_status_refused_one_identity(self) -> None:
        """A real `flowctl sync set-tracker-id` fired in the gap between the
        sync-body step and the status step refuses while the facade claim is
        live; the whole push completes against ONE identity (the receipt and
        the on-disk link never split). After the push releases the claim,
        the same relink succeeds - the refusal is retryable."""
        from flowctl_tracker.facade import ops as OPS
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked(
                mergeBaseFlow=FLOW_BODY,
                mergeBaseTracker=FLOW_BODY.rstrip("\n"),
            ))
            ff = _flow_file(root)
            rec_path = flow / "create-first" / f"facade-{SPEC_ID}.json"
            seen: dict = {}

            orig_run_status = OPS.run_status

            def relink_then_status(*args, **kwargs):
                # BETWEEN steps: sync-body released its inner claim, status
                # has not taken its own yet. Only the facade claim is live.
                claim = json.loads(rec_path.read_text(encoding="utf-8"))
                self.assertEqual(claim.get("status"), "pending")
                self.assertEqual(claim.get("op"), "facade-push")
                self.assertFalse(
                    (flow / "create-first" / f"syncbody-{SPEC_ID}.json").exists())
                self.assertFalse(
                    (flow / "create-first" / f"status-{SPEC_ID}.json").exists())
                seen["relink"] = self._relink_cli(root)
                seen["id_in_gap"] = self._spec_tracker_id(flow)
                return orig_run_status(*args, **kwargs)

            ex = fake_execute(_noop_push_responses(FLOW_BODY))
            with mock.patch.object(OPS, "run_status",
                                   side_effect=relink_then_status):
                out = F.sync(flow, SPEC_ID, op="push", event="work.done",
                             flow_file=ff, execute=ex)

            self.assertNotIsInstance(out, TrackerError, out)
            proc = seen["relink"]
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("in flight", proc.stdout + proc.stderr)
            self.assertIn(f"facade-{SPEC_ID}.json", proc.stdout + proc.stderr)
            # The relink never landed inside the sequence: ONE identity.
            self.assertEqual(seen["id_in_gap"], GH_NODE)
            self.assertEqual(out["tracker_id"], GH_NODE)
            self.assertEqual(self._spec_tracker_id(flow), GH_NODE)
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["tracker_id"], GH_NODE)
            # Claim released on completion; the refused relink now succeeds.
            self.assertFalse(rec_path.exists(), "facade claim released")
            proc2 = self._relink_cli(root)
            self.assertEqual(proc2.returncode, 0, proc2.stdout + proc2.stderr)
            self.assertEqual(self._spec_tracker_id(flow), self.NEW_UUID)

    def test_comment_create_then_relink_refused_through_receipt(self) -> None:
        """The comment facade's outer claim starts before create and remains
        live through comment-add and its aggregate receipt. A relink racing
        the provider create cannot redirect the comment and receipt to a new
        issue while orphaning the issue just created."""
        from flowctl_tracker.facade import ops as OPS
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg())  # unlinked
            bf = _body_file(root, "evidence=abc1234\n**done** - shipped.\n")
            rec_path = flow / "create-first" / f"facade-{SPEC_ID}.json"
            seen: dict = {}
            posted_bodies = []

            def create_response(request):
                return ok({
                    "id": 1, "node_id": GH_NODE, "number": 42,
                    "html_url": "https://github.com/o/r/issues/42",
                })

            original_create = OPS.create_if_unlinked

            def relink_after_create(*args, **kwargs):
                created = original_create(*args, **kwargs)
                claim = json.loads(rec_path.read_text(encoding="utf-8"))
                self.assertEqual(claim.get("status"), "pending")
                self.assertEqual(claim.get("op"), "facade-comment")
                self.assertFalse(
                    (flow / "create-first" / f"spec-{SPEC_ID}.json").exists(),
                    "inner create claim released before the relink attempt")
                seen["relink"] = self._relink_cli(root)
                seen["id_during_create"] = self._spec_tracker_id(flow)
                return created

            def capture_add(request):
                posted_bodies.append(json.loads(request.body)["body"])
                return ok({"id": 99, "body": posted_bodies[-1],
                           "html_url": "https://x/c/99"})

            ex = fake_execute({
                "lifecycle-create": create_response,
                "wire-parent-read": ok(_gh_issue(FLOW_BODY)),
                "wire-comment-list": ok([]),
                "wire-comment-add": capture_add,
            })
            with mock.patch.object(OPS, "create_if_unlinked",
                                   side_effect=relink_after_create):
                out = F.sync(flow, SPEC_ID, op="comment", event="work.done",
                             body_file=bf, execute=ex)

            self.assertNotIsInstance(out, TrackerError, out)
            proc = seen["relink"]
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn(f"facade-{SPEC_ID}.json",
                          proc.stdout + proc.stderr)
            self.assertEqual(seen["id_during_create"], GH_NODE,
                             "relink cannot land after create")
            self.assertEqual(self._spec_tracker_id(flow), GH_NODE)
            self.assertEqual(out["tracker_id"], GH_NODE)
            self.assertEqual(len(posted_bodies), 1)
            self.assertIn(f"issue={GH_NODE}", posted_bodies[0])
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["tracker_id"], GH_NODE)
            self.assertFalse(rec_path.exists(), "facade claim released")

    def test_push_nested_inner_claims_coexist_no_self_deadlock(self) -> None:
        """The inner step claims use DIFFERENT keys, so a normal push runs
        with the facade claim AND the step claim pending simultaneously -
        nesting cannot self-refuse - and everything is released on exit."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked(
                mergeBaseFlow="PRIOR\n", mergeBaseTracker="PRIOR",
            ))
            ff = _flow_file(root, "NEW BODY\n")
            facade_rec = flow / "create-first" / f"facade-{SPEC_ID}.json"
            seen: dict = {}

            def assert_nested_syncbody(req):
                facade = json.loads(facade_rec.read_text(encoding="utf-8"))
                inner = json.loads(
                    (flow / "create-first" / f"syncbody-{SPEC_ID}.json")
                    .read_text(encoding="utf-8"))
                seen["syncbody_nested"] = (facade.get("status"),
                                           inner.get("status"))
                return ok(_gh_issue("old"))

            def assert_nested_status(req):
                facade = json.loads(facade_rec.read_text(encoding="utf-8"))
                inner = json.loads(
                    (flow / "create-first" / f"status-{SPEC_ID}.json")
                    .read_text(encoding="utf-8"))
                seen["status_nested"] = (facade.get("status"),
                                         inner.get("status"))
                return ok(_gh_issue("NEW BODY\n"))

            written = _gh_issue("NEW BODY\n")
            ex = fake_execute({
                "sync-body-parent-read": assert_nested_syncbody,
                "wire-parent-read": ok(_gh_issue("old")),
                "wire-update": ok(written),
                "wire-read": ok(written),
                "status-parent-read": assert_nested_status,
                "merge-evidence": ok([]),
            })
            out = F.sync(flow, SPEC_ID, op="push", event="work.done",
                         flow_file=ff, execute=ex)
            self.assertNotIsInstance(out, TrackerError, out)
            self.assertEqual(seen["syncbody_nested"], ("pending", "pending"))
            self.assertEqual(seen["status_nested"], ("pending", "pending"))
            leftover = sorted(
                p.name for p in (flow / "create-first").glob("*.json"))
            self.assertEqual(leftover, [], "all claims released")

    def test_concurrent_push_refused_facade_in_flight(self) -> None:
        """A second push racing in while the facade claim is live backs off
        with structured CONFLICT before ANY wire call; the winner completes
        and writes the single receipt."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked(
                mergeBaseFlow=FLOW_BODY,
                mergeBaseTracker=FLOW_BODY.rstrip("\n"),
            ))
            ff = _flow_file(root)
            inner: dict = {}

            def racing_push(req):
                inner["ex"] = fake_execute({})
                inner["out"] = F.sync(flow, SPEC_ID, op="push",
                                      event="work.done", flow_file=ff,
                                      execute=inner["ex"])
                return ok(_gh_issue(FLOW_BODY))

            responses = _noop_push_responses(FLOW_BODY)
            responses["sync-body-parent-read"] = racing_push
            ex = fake_execute(responses)
            out = F.sync(flow, SPEC_ID, op="push", event="work.done",
                         flow_file=ff, execute=ex)
            self.assertNotIsInstance(out, TrackerError, out)
            raced = inner["out"]
            self.assertIsInstance(raced, TrackerError)
            self.assertIs(raced.cls, ErrorClass.CONFLICT)
            self.assertEqual(raced.subtype, "facade_in_flight")
            self.assertTrue(raced.auto_retryable)
            self.assertEqual(inner["ex"].calls, [],
                             "loser backs off before any wire call")
            # Loser landed nothing -> receipt-less; winner wrote exactly one.
            self.assertEqual(len(_receipts(flow)), 1)

    def test_reconcile_holds_facade_claim_across_steps(self) -> None:
        """op_reconcile has the same multi-step gap (wire-read -> sync-body
        -> status) and holds the same outer claim across it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked(
                mergeBaseFlow=FLOW_BODY,
                mergeBaseTracker=FLOW_BODY.rstrip("\n"),
            ))
            ff = _flow_file(root)
            bf = _body_file(root, FLOW_BODY)
            rec_path = flow / "create-first" / f"facade-{SPEC_ID}.json"
            seen: dict = {}

            def assert_claimed_read(req):
                claim = json.loads(rec_path.read_text(encoding="utf-8"))
                seen["claim"] = (claim.get("status"), claim.get("op"))
                return ok(_gh_issue(FLOW_BODY))

            responses = _noop_push_responses(FLOW_BODY)
            responses["wire-read"] = assert_claimed_read
            ex = fake_execute(responses)
            out = F.sync(flow, SPEC_ID, op="reconcile", event="plan",
                         flow_file=ff, body_file=bf, execute=ex)
            self.assertNotIsInstance(out, TrackerError, out)
            self.assertEqual(seen["claim"], ("pending", "facade-reconcile"))
            self.assertFalse(rec_path.exists(), "facade claim released")
            self.assertEqual(len(_receipts(flow)), 1)


# ---------------------------------------------------------------------------
# Envelope / CLI shell
# ---------------------------------------------------------------------------

class EnvelopeShell(unittest.TestCase):
    def test_run_emits_success_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked(
                mergeBaseFlow=FLOW_BODY,
                mergeBaseTracker=FLOW_BODY.rstrip("\n"),
            ))
            ff = _flow_file(root)
            ex = fake_execute(_noop_push_responses(FLOW_BODY))
            payload, code = F.run(
                flow, spec_id=SPEC_ID, op="push", event="work.done",
                flow_file=ff, execute=ex)
            self.assertEqual(code, 0)
            data = json.loads(payload)
            self.assertTrue(data["success"])
            self.assertEqual(data["data"]["op"], "push")

    def test_all_four_ops_registered(self) -> None:
        from flowctl_tracker.facade.helpers import OPS
        self.assertEqual(OPS, frozenset({"push", "pull", "reconcile", "comment"}))


# ---------------------------------------------------------------------------
# R19 cross-adapter conformance matrix (4 adapters x 4 ops + fault rows)
# ---------------------------------------------------------------------------

class FacadeMatrix(unittest.TestCase):
    """Every adapter × every facade op; plus partial-failure + degradation."""

    def _run_cell(self, provider, cfg_fn, durable, display, mk_issue, op):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            tracker = _linked(id=durable, identifier=display, url="https://x",
                              mergeBaseFlow=FLOW_BODY,
                              mergeBaseTracker=FLOW_BODY.rstrip("\n"))
            _write_flow(flow, cfg_fn(), tracker=tracker, spec_md=FLOW_BODY)
            env = {}
            if provider == "linear":
                env["LINEAR_API_KEY"] = "lin_test"

            if op == "push":
                new_body = "## Goal\nShip it rewritten.\n"
                ff = _flow_file(root, new_body)
                old = mk_issue("old remote body")
                written = mk_issue(new_body)
                responses = {
                    **_status_noop_responses(provider, written),
                    "sync-body-parent-read": _parent_resp(provider, old),
                    "wire-parent-read": _parent_resp(provider, old),
                    "wire-update": _update_resp(provider, written),
                    "wire-read": _parent_resp(provider, written),
                    "status-parent-read": _parent_resp(provider, written),
                }
                ex = fake_execute(responses)
                with mock.patch.dict(os.environ, env, clear=False):
                    payload, code = F.run(
                        flow, spec_id=SPEC_ID, op="push", event="work.done",
                        flow_file=ff, execute=ex)
                data = json.loads(payload)
                self.assertTrue(data["success"], data)
                self.assertEqual(code, 0)
                self.assertEqual(data["data"]["op"], "push")
                self.assertFalse(
                    any(c.op == "lifecycle-create" for c in ex.calls),
                    f"{provider}: create must no-op on linked")
                self.assertTrue(
                    any(c.op == "wire-update" for c in ex.calls),
                    f"{provider}: push must write body")
                saved = json.loads(
                    (flow / "specs" / f"{SPEC_ID}.json").read_text(encoding="utf-8"))
                self.assertEqual(saved["tracker"]["mergeBaseFlow"], new_body)
                self.assertEqual(
                    saved["tracker"]["mergeBaseTracker"],
                    SB.trackerBodyForMerge(new_body))

            elif op == "pull":
                remote = "tracker-side body for pull\n"
                issue = mk_issue(remote)
                ex = fake_execute({
                    "wire-read": _parent_resp(provider, issue),
                    # Poisoned second read must never fire.
                    "sync-body-parent-read": _parent_resp(
                        provider, mk_issue("POISON")),
                })
                with mock.patch.dict(os.environ, env, clear=False):
                    payload, code = F.run(
                        flow, spec_id=SPEC_ID, op="pull", event="interview",
                        execute=ex)
                data = json.loads(payload)
                self.assertTrue(data["success"], data)
                self.assertEqual(code, 0)
                self.assertEqual(data["data"]["op"], "pull")
                self.assertFalse(
                    any(c.op == "wire-update" for c in ex.calls),
                    f"{provider}: pull must not write tracker")
                self.assertEqual(
                    [c.op for c in ex.calls
                     if c.op in ("wire-read", "sync-body-parent-read")],
                    ["wire-read"])
                saved = json.loads(
                    (flow / "specs" / f"{SPEC_ID}.json").read_text(encoding="utf-8"))
                self.assertEqual(
                    saved["tracker"]["mergeBaseTracker"],
                    SB.trackerBodyForMerge(remote))

            elif op == "reconcile":
                ff = _flow_file(root, FLOW_BODY)
                bf = _body_file(root, FLOW_BODY)
                # No prior base: seed both halves from matching tracker body.
                path = flow / "specs" / f"{SPEC_ID}.json"
                spec = json.loads(path.read_text(encoding="utf-8"))
                spec["tracker"]["mergeBaseFlow"] = None
                spec["tracker"]["mergeBaseTracker"] = None
                path.write_text(json.dumps(spec, indent=2) + "\n",
                                encoding="utf-8")
                issue = mk_issue(FLOW_BODY)
                ex = fake_execute(_status_noop_responses(provider, issue))
                with mock.patch.dict(os.environ, env, clear=False):
                    payload, code = F.run(
                        flow, spec_id=SPEC_ID, op="reconcile", event="plan",
                        flow_file=ff, body_file=bf, execute=ex)
                data = json.loads(payload)
                self.assertTrue(data["success"], data)
                self.assertEqual(code, 0)
                self.assertEqual(data["data"]["op"], "reconcile")
                saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
                self.assertEqual(saved["mergeBaseFlow"], FLOW_BODY)
                self.assertEqual(
                    saved["mergeBaseTracker"],
                    SB.trackerBodyForMerge(FLOW_BODY))
                self.assertIsNotNone(saved["mergeBaseFlow"])
                self.assertIsNotNone(saved["mergeBaseTracker"])

            elif op == "comment":
                evidence = "abc1234"
                bf = _body_file(root, f"evidence={evidence}\n**done** shipped.\n")
                marker = (f"<!-- flow-next:sync issue={durable} spec={SPEC_ID} "
                          f"evt=work.done evidence={evidence} -->")
                issue = mk_issue(FLOW_BODY)
                parent = _parent_resp(provider, issue)
                posted_bodies: list[str] = []

                def capture_add(req):
                    posted_bodies.append(_posted_body(provider, req))
                    return _comment_add_resp(provider, posted_bodies[-1])(req)

                ex1 = fake_execute({
                    "wire-parent-read": parent,
                    "wire-comment-list": _comment_list_empty(provider),
                    "wire-comment-add": capture_add,
                })
                with mock.patch.dict(os.environ, env, clear=False):
                    payload1, code1 = F.run(
                        flow, spec_id=SPEC_ID, op="comment", event="work.done",
                        body_file=bf, execute=ex1)
                data1 = json.loads(payload1)
                self.assertTrue(data1["success"], data1)
                self.assertEqual(code1, 0)
                self.assertEqual(data1["data"]["op"], "comment")
                self.assertTrue(data1["data"]["posted"])
                self.assertEqual(len(posted_bodies), 1)
                self.assertTrue(posted_bodies[0].startswith(marker),
                                posted_bodies[0])
                self.assertEqual(len(_receipts(flow)), 1)

                ex2 = fake_execute({
                    "wire-parent-read": parent,
                    "wire-comment-list": _comment_list_with(
                        provider, posted_bodies[0]),
                })
                with mock.patch.dict(os.environ, env, clear=False):
                    payload2, code2 = F.run(
                        flow, spec_id=SPEC_ID, op="comment", event="work.done",
                        body_file=bf, execute=ex2)
                data2 = json.loads(payload2)
                self.assertTrue(data2["success"], data2)
                self.assertEqual(code2, 0)
                self.assertFalse(data2["data"]["posted"])
                self.assertTrue(data2["data"]["deduped"])
                self.assertFalse(
                    any(c.op == "wire-comment-add" for c in ex2.calls))
                self.assertEqual(len(_receipts(flow)), 2)
                return  # comment writes two receipts; skip common assert below

            else:
                self.fail(f"unknown op {op}")

            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1, receipts)
            # Zero granular: every receipt is the facade aggregate type=sync.
            self.assertEqual(receipts[0]["type"], "sync")
            self.assertEqual(receipts[0].get("transport"), provider)

    def test_matrix_all_adapters_all_ops(self) -> None:
        for provider, cfg_fn, durable, display, mk_issue in ADAPTERS:
            for op in ("push", "pull", "reconcile", "comment"):
                with self.subTest(provider=provider, op=op):
                    self._run_cell(provider, cfg_fn, durable, display,
                                   mk_issue, op)

    def test_matrix_partial_failure_readback_one_adapter(self) -> None:
        """sync-body readback error on gitlab: success:false + completed_steps."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gl_cfg(), tracker=_linked(
                id=str(GL_ID), identifier="g/p#12", url="https://x",
                mergeBaseFlow="PRIOR\n", mergeBaseTracker="PRIOR",
            ))
            ff = _flow_file(root, "NEW BODY\n")
            parent = _gl_issue("old")
            ex = fake_execute({
                "sync-body-parent-read": ok(parent),
                "wire-parent-read": ok(parent),
                "wire-update": ok(_gl_issue("written")),
                "wire-read": TrackerError(ErrorClass.TRANSPORT, "readback boom",
                                          subtype="readback"),
            })
            payload, code = F.run(
                flow, spec_id=SPEC_ID, op="push", event="work.done",
                flow_file=ff, execute=ex)
            data = json.loads(payload)
            self.assertFalse(data["success"])
            self.assertNotEqual(code, 0)
            self.assertIn("completed_steps", data["data"])
            self.assertIn("wire-update", data["data"]["completed_steps"])
            self.assertEqual(data["class"], "transport")
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["status"], "errored")
            self.assertEqual(receipts[0]["transport"], "gitlab")

    def test_matrix_structured_degradation_assignee_replace(self) -> None:
        """Single-assignee replace reports structured degraded (not prose)."""
        parent = _ln_issue(FLOW_BODY)
        parent["assignee"] = {"id": "user-1", "name": "Ada"}
        ex = fake_execute({
            "wire-parent-read": gql_issue(parent),
            "wire-assign": ok({"data": {"issueUpdate": {
                "success": True,
                "issue": {**parent,
                          "assignee": {"id": "user-2", "name": "Bea"}}}}}),
        })
        with mock.patch.dict(os.environ, {"LINEAR_API_KEY": "lin_test"}):
            out = W.dispatch(
                "assign", ln_cfg(),
                locator={"durable": LN_UUID, "display": "WOR-17"},
                add=["user-2"], execute=ex)
        self.assertNotIsInstance(out, TrackerError, out)
        deg = out.get("degraded")
        self.assertIsInstance(deg, dict)
        self.assertEqual(deg["kind"], "assignee_replaced")
        self.assertEqual(deg["previous"], "user-1")
        self.assertEqual(deg["applied"], "user-2")


if __name__ == "__main__":
    unittest.main()


class FacadeDegradationPropagation(unittest.TestCase):
    def test_status_write_degradation_reaches_response_and_receipt(self) -> None:
        """The status verb nests label degradation under result['write'];
        the facade must surface it in BOTH the response and the aggregate
        receipt, never silently drop it."""
        from flowctl_tracker.facade import helpers as FH
        nested = {"kind": "status_labels_inconsistent",
                  "expected": ["status:done"], "present": []}
        got = FH.collect_degraded({"kind": "applied",
                                   "write": {"degraded": nested}})
        self.assertEqual(got, nested)
        # top-level still wins when present
        top = {"kind": "relates_to"}
        self.assertEqual(FH.collect_degraded({"degraded": top}), top)
        self.assertIsNone(FH.collect_degraded({"kind": "noop"}, None))


class SharedIssueSpecScopedDedup(unittest.TestCase):
    """Two specs intentionally sharing one issue (`sync set-tracker-id
    --force`) emitting the same event/evidence: the dedup matcher and the
    comment claim key must include the spec, or spec B's comment is silently
    dropped as a false dedup against spec A's marker."""

    SPEC_A = SPEC_ID
    SPEC_B = "fn-2-other"

    def _flow_two_specs(self, flow: Path) -> None:
        _write_flow(flow, gh_cfg(), spec_id=self.SPEC_A, tracker=_linked())
        # Second spec linked to the SAME issue (config already written).
        base = {
            "id": GH_NODE, "identifier": "#42", "url": "https://x/42",
            "lastSyncedAt": None, "depRelations": [], "linkState": "linked",
            "baseHashFlow": None, "baseHashTracker": None,
            "mergeBaseFlow": None, "mergeBaseTracker": None,
        }
        spec = {"id": self.SPEC_B, "title": "Other", "status": "open",
                "branch_name": self.SPEC_B, "tracker": base}
        (flow / "specs" / f"{self.SPEC_B}.json").write_text(
            json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        (flow / "specs" / f"{self.SPEC_B}.md").write_text(
            FLOW_BODY, encoding="utf-8")

    def test_second_spec_posts_despite_first_specs_marker(self) -> None:
        """Spec A's marker for the same issue/event/evidence must NOT dedup
        spec B's comment (no false noop, no silently omitted comment)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            self._flow_two_specs(flow)
            evidence = "abc1234"
            bf = _body_file(root, f"evidence={evidence}\n**done** - shipped.\n")
            marker_a = (f"<!-- flow-next:sync issue={GH_NODE} "
                        f"spec={self.SPEC_A} evt=work.done "
                        f"evidence={evidence} -->")
            posted_bodies = []

            def capture_add(req):
                posted_bodies.append(json.loads(req.body)["body"])
                return ok({"id": 100, "body": posted_bodies[-1],
                           "html_url": "https://x/c/100"})

            ex = fake_execute({
                "wire-parent-read": ok(_gh_issue(FLOW_BODY)),
                "wire-comment-list": ok([{
                    "id": 99, "body": f"{marker_a}\n\n**done** - shipped.",
                    "html_url": "https://x/c/99",
                }]),
                "wire-comment-add": capture_add,
            })
            out = F.sync(flow, self.SPEC_B, op="comment", event="work.done",
                         body_file=bf, execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertTrue(out["posted"], "spec B must post, not false-dedup")
            self.assertFalse(out["deduped"])
            self.assertEqual(len(posted_bodies), 1)
            self.assertIn(f"spec={self.SPEC_B}", posted_bodies[0])

    def test_same_spec_same_event_evidence_still_dedups_noop(self) -> None:
        """Identity guard intact: the SAME spec's marker still dedups."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_linked())
            evidence = "abc1234"
            bf = _body_file(root, f"evidence={evidence}\n**done** - shipped.\n")
            marker = (f"<!-- flow-next:sync issue={GH_NODE} spec={SPEC_ID} "
                      f"evt=work.done evidence={evidence} -->")
            ex = fake_execute({
                "wire-parent-read": ok(_gh_issue(FLOW_BODY)),
                "wire-comment-list": ok([{
                    "id": 99, "body": f"{marker}\n\n**done** - shipped.",
                    "html_url": "https://x/c/99",
                }]),
            })
            out = F.sync(flow, SPEC_ID, op="comment", event="work.done",
                         body_file=bf, execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertFalse(out["posted"])
            self.assertTrue(out["deduped"])
            self.assertFalse(any(c.op == "wire-comment-add" for c in ex.calls))

    def test_claim_keys_differ_per_spec_and_stay_hex_safe(self) -> None:
        """Two specs sharing issue/event/evidence get DIFFERENT claim paths
        (concurrent claims, no false back-off); filenames stay hex-safe."""
        from flowctl_tracker.facade.ops import _comment_claim_path
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            p_a = _comment_claim_path(
                flow, issue=GH_NODE, spec=self.SPEC_A, event="work.done",
                evidence="abc1234")
            p_b = _comment_claim_path(
                flow, issue=GH_NODE, spec=self.SPEC_B, event="work.done",
                evidence="abc1234")
            self.assertNotEqual(p_a, p_b)
            for p in (p_a, p_b):
                self.assertRegex(p.name, r"^comment-[0-9a-f]{16}\.json$")
                self.assertEqual(p.parent, flow / "create-first")
            # Same quadruple stays deterministic.
            self.assertEqual(p_a, _comment_claim_path(
                flow, issue=GH_NODE, spec=self.SPEC_A, event="work.done",
                evidence="abc1234"))
