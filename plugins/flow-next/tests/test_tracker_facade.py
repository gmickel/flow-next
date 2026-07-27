"""Lifecycle facade: tracker sync --op push|pull|reconcile|comment (fn-140.7).

Fake transport = injected executor seam (same harness as lifecycle/syncbody).
"""

from __future__ import annotations

import json
import os
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
