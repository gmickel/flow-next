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
from flowctl_tracker.types import ErrorClass, Response, TrackerError  # noqa: E402


def ok(body) -> Response:
    return Response(200, {}, json.dumps(body).encode() if body is not None else b"", 0.01)


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
LN_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
FLOW_BODY = "## Goal\nShip it.\n"
SPEC_ID = "fn-1-demo"


def gh_cfg() -> dict:
    return {"tracker": {"type": "github",
                        "resolved": {"destination": {"owner": "o", "repo": "r"}}}}


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


def _gh_issue(body: str, *, labels=None) -> dict:
    return {"id": 999001, "node_id": GH_NODE, "number": 42, "title": "Demo",
            "body": body, "html_url": "https://github.com/o/r/issues/42",
            "labels": labels if labels is not None else [{"name": "status:backlog"}],
            "state": "open"}


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
                "wire-parent-read": ok(parent),
                "wire-read": ok(parent),
                "sync-body-parent-read": ok(parent),
            })
            out = F.sync(flow, SPEC_ID, op="pull", event="interview",
                         execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["op"], "pull")
            self.assertFalse(any(c.op == "wire-update" for c in ex.calls))
            self.assertEqual(len(_receipts(flow)), 1)
            self.assertEqual(_receipts(flow)[0]["status"], "pulled")

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


if __name__ == "__main__":
    unittest.main()
