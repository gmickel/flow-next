"""status verb: fn-66 merge-evidence gate + who-wins ladder (fn-140.3).

Fake transport = injected executor seam (same harness as test_tracker_lifecycle).
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import status as S  # noqa: E402
from flowctl_tracker.status.policy import (  # noqa: E402
    decide, flow_to_normalized, in_progress_wins_matches, is_deadlock,
    merge_evidence, terminal_wins_matches,
)
from flowctl_tracker.status.providers import tracker_norm_from_parent  # noqa: E402
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
GL_ID = "84817009"
LN_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
JR_ID = "10042"


def gh_cfg() -> dict:
    return {"tracker": {"type": "github",
                        "resolved": {"destination": {"owner": "o", "repo": "r"}}},
            "review": {"backend": "codex"}}


def gl_cfg() -> dict:
    return {"tracker": {"type": "gitlab",
                        "resolved": {"destination": {
                            "projectId": 1, "projectPath": "g/p"}}},
            "review": {"backend": "codex"}}


def ln_cfg(*, state_ids=None) -> dict:
    return {"tracker": {"type": "linear",
                        "resolved": {"destination": {
                            "teamId": "team-1", "teamKey": "WOR",
                            "stateIds": state_ids or {
                                "todo": "s-todo", "in_progress": "s-ip",
                                "in_review": "s-ir", "done": "s-done",
                            }}}},
            "review": {"backend": "codex"}}


def jr_cfg(*, status_ids=None) -> dict:
    return {"tracker": {"type": "jira",
                        "resolved": {"destination": {
                            "baseUrl": "https://ex.atlassian.net",
                            "projectKey": "SCRUM", "projectId": "10000",
                            "issueTypeId": "10001", "apiVersion": 2,
                            "statusIds": status_ids or {
                                "todo": "1", "in_progress": "2",
                                "in_review": "3", "done": "4",
                            }}}},
            "review": {"backend": "codex"}}


def _write_flow(flow: Path, config: dict, *, spec_id: str = "fn-1-demo",
                tracker: dict | None = None, spec_extra: dict | None = None,
                tasks: list | None = None) -> Path:
    (flow / "specs").mkdir(parents=True, exist_ok=True)
    (flow / "config.json").write_text(json.dumps(config), encoding="utf-8")
    spec = {
        "id": spec_id, "title": "Demo", "status": "open",
        "branch_name": "fn-1-demo",
        "completion_review_status": "unknown",
        "tracker": tracker if tracker is not None else {
            "id": GH_NODE, "identifier": "#42", "url": "https://x/42",
            "lastSyncedAt": None, "depRelations": [], "linkState": "linked",
        },
    }
    if spec_extra:
        spec.update(spec_extra)
    path = flow / "specs" / f"{spec_id}.json"
    path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    if tasks is not None:
        tdir = flow / "tasks"
        tdir.mkdir(parents=True, exist_ok=True)
        for i, t in enumerate(tasks, 1):
            tid = t.get("id") or f"{spec_id}.{i}"
            (tdir / f"{tid}.json").write_text(
                json.dumps({"id": tid, "status": t.get("status", "todo"),
                            "spec": spec_id}), encoding="utf-8")
    return path


def _receipts(flow: Path) -> list[dict]:
    runs = flow / "sync-runs"
    if not runs.is_dir():
        return []
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(runs.glob("sync-*.json"))]


def _gh_parent(*, state="open", labels=None, state_reason=None):
    body = {"node_id": GH_NODE, "number": 42, "state": state,
            "labels": [{"name": x} for x in (labels or [])],
            "html_url": "https://github.com/o/r/issues/42"}
    if state_reason is not None:
        body["state_reason"] = state_reason
    return body


# ---------------------------------------------------------------------------
# flow_to_normalized — 8-row table + merge gate
# ---------------------------------------------------------------------------

class FlowToNormalized(unittest.TestCase):
    def test_completion_review_ship_without_merged_is_not_terminal(self) -> None:
        spec = {"status": "done", "completion_review_status": "ship"}
        # rows 5/6: none / closed-unmerged → in_review, NEVER done
        for ev in ("none", "closed-unmerged", "ambiguous", "probe-error", "open"):
            with self.subTest(ev=ev):
                self.assertEqual(
                    flow_to_normalized(spec, ev, True), "in_review")
                self.assertNotEqual(
                    flow_to_normalized(spec, ev, True), "done")

    def test_merged_ungated_is_done(self) -> None:
        spec = {"status": "done", "completion_review_status": "unknown"}
        self.assertEqual(flow_to_normalized(spec, "merged", False), "done")

    def test_merged_ship_configured_is_done_slot(self) -> None:
        # verified collapses to done slot
        spec = {"status": "done", "completion_review_status": "ship"}
        self.assertEqual(flow_to_normalized(spec, "merged", True), "done")

    def test_merged_configured_not_ship_stays_in_review(self) -> None:
        spec = {"status": "done", "completion_review_status": "unknown"}
        self.assertEqual(flow_to_normalized(spec, "merged", True), "in_review")

    def test_open_pr_beats_local_in_progress(self) -> None:
        # row 4 before row 7 — all-tasks-done OPEN + open PR → in_review
        spec = {"status": "open"}
        tasks = [{"status": "done"}, {"status": "done"}]
        self.assertEqual(
            flow_to_normalized(spec, "open", False, tasks=tasks), "in_review")

    def test_row7_in_progress_and_row8_todo_backlog(self) -> None:
        spec = {"status": "open"}
        self.assertEqual(
            flow_to_normalized(spec, "none", False,
                               tasks=[{"status": "in_progress"}]),
            "in_progress")
        self.assertEqual(
            flow_to_normalized(spec, "none", False,
                               tasks=[{"status": "todo"}]),
            "todo")
        self.assertEqual(
            flow_to_normalized(spec, "none", False, tasks=[]), "backlog")


# ---------------------------------------------------------------------------
# decide — deadlock FIRST + reordering guard
# ---------------------------------------------------------------------------

class DecideLadder(unittest.TestCase):
    def test_deadlock_returns_conflict_never_silent(self) -> None:
        d = decide("done", None, "in_progress", "done", "none")
        self.assertEqual(d.kind, "conflict")
        self.assertEqual(d.reason, "status-deadlock")

    def test_reordering_guard_deadlock_also_matches_terminal_wins(self) -> None:
        """If deadlock ran AFTER terminal-wins, this pair would silently noop.

        Assert BOTH single-field rules match so a reorder would change the
        outcome from conflict → noop (the bug memory records).
        """
        flow, tracker = "in_progress", "done"
        self.assertTrue(is_deadlock(flow, tracker))
        self.assertTrue(terminal_wins_matches(flow, tracker),
                        "terminal-wins ALSO matches — order is load-bearing")
        # Mirror pair
        flow2, tracker2 = "done", "in_progress"
        self.assertTrue(is_deadlock(flow2, tracker2))
        # in-progress-wins would match the clean (non-deadlock) case:
        self.assertTrue(in_progress_wins_matches("in_progress", "todo"))
        d = decide("done", None, flow, tracker, "none")
        self.assertEqual(d.kind, "conflict")
        # Simulate wrong order: if terminal-wins ran first → would be noop
        if terminal_wins_matches(flow, tracker) and not is_deadlock(flow, tracker):
            self.fail("unreachable")
        # The reordering failure mode: terminal-wins alone yields noop
        wrong_order_outcome = "noop" if terminal_wins_matches(flow, tracker) else "?"
        self.assertEqual(wrong_order_outcome, "noop")
        self.assertNotEqual(d.kind, wrong_order_outcome)

    def test_to_done_without_merge_is_conflict(self) -> None:
        d = decide("done", None, "in_review", "in_progress", "none")
        self.assertEqual(d.kind, "conflict")
        self.assertEqual(d.reason, "merge-evidence-gate")

    def test_closed_unmerged_is_a_conflict_for_recovery(self) -> None:
        """R7: genuinely ambiguous evidence returns class conflict, never a
        successful defer envelope (codex round-1 finding 3)."""
        d = decide("done", None, "in_review", "in_progress", "closed-unmerged")
        self.assertEqual(d.kind, "conflict")
        self.assertEqual(d.reason, "closed-unmerged")

    def test_cancelled_surfaced_never_applied(self) -> None:
        d = decide("cancelled", "not_planned", "in_progress", "todo", "none")
        self.assertEqual(d.kind, "defer")
        self.assertEqual(d.reason, "cancelled-family")

    def test_garbage_reason_invalid_input(self) -> None:
        d = decide("done", "garbage", "done", "in_review", "merged")
        self.assertEqual(d.kind, "invalid_input")

    def test_duplicate_reason_allowed_for_done(self) -> None:
        d = decide("done", "duplicate", "done", "in_review", "merged")
        self.assertEqual(d.kind, "apply")
        self.assertEqual(d.target_slot, "done")
        self.assertEqual(d.close_reason, "duplicate")

    def test_flow_wins_in_progress(self) -> None:
        d = decide("in_progress", None, "in_progress", "todo", "none")
        self.assertEqual(d.kind, "apply")
        self.assertEqual(d.target_slot, "in_progress")

    def test_unmapped_residual_is_conflict(self) -> None:
        d = decide("backlog", None, "todo", "in_review", "none")
        self.assertEqual(d.kind, "conflict")


# ---------------------------------------------------------------------------
# merge_evidence
# ---------------------------------------------------------------------------

class MergeEvidence(unittest.TestCase):
    def test_classifies_buckets(self) -> None:
        cases = [
            ([{"state": "MERGED"}], "merged"),
            ([{"state": "OPEN"}], "open"),
            ([{"state": "CLOSED"}], "closed-unmerged"),
            ([], "none"),
            ([{"state": "OPEN"}, {"state": "CLOSED"}], "ambiguous"),
        ]
        for rows, want in cases:
            with self.subTest(want=want):
                ex = fake_execute({"merge-evidence": ok(rows)})
                got = merge_evidence(gh_cfg(), {"branch_name": "b"}, ex)
                self.assertEqual(got, want)

    def test_draft_only_is_ambiguous_not_clean_open(self) -> None:
        """status-sync.md names a draft-only probe result ambiguous - the
        classifier must use the isDraft field it requests, never report a
        draft-only branch as clean open evidence (which would advance the
        tracker to In Review)."""
        cases = [
            ([{"state": "OPEN", "isDraft": True}], "ambiguous"),
            # draft alongside closed: still no clean dominant signal
            ([{"state": "OPEN", "isDraft": True}, {"state": "CLOSED"}],
             "ambiguous"),
            # a real (non-draft) open PR still dominates a draft sibling
            ([{"state": "OPEN", "isDraft": True},
              {"state": "OPEN", "isDraft": False}], "open"),
            # merged always wins, drafts irrelevant
            ([{"state": "OPEN", "isDraft": True}, {"state": "MERGED"}],
             "merged"),
            # explicit isDraft: false keeps classifying as clean open
            ([{"state": "OPEN", "isDraft": False}], "open"),
        ]
        for rows, want in cases:
            with self.subTest(rows=rows, want=want):
                ex = fake_execute({"merge-evidence": ok(rows)})
                got = merge_evidence(gh_cfg(), {"branch_name": "b"}, ex)
                self.assertEqual(got, want)

    def test_draft_only_decision_surfaces_ambiguity(self) -> None:
        """Draft-only evidence routes through the ambiguous conflict path
        (NEEDS_HUMAN surface), never a clean in_review apply."""
        d = decide("done", None, "in_review", "in_progress", "ambiguous")
        self.assertEqual(d.kind, "conflict")
        self.assertEqual(d.reason, "ambiguous")

    def test_missing_branch_is_probe_error(self) -> None:
        ex = fake_execute({})
        self.assertEqual(merge_evidence(gh_cfg(), {}, ex), "probe-error")

    def test_executor_error_is_probe_error(self) -> None:
        ex = fake_execute({"merge-evidence": TrackerError(
            ErrorClass.TRANSPORT, "gh failed", subtype="spawn")})
        self.assertEqual(
            merge_evidence(gh_cfg(), {"branch_name": "b"}, ex), "probe-error")


# ---------------------------------------------------------------------------
# status verb integration
# ---------------------------------------------------------------------------

class StatusVerbGate(unittest.TestCase):
    def test_completion_review_ship_to_done_without_merged_not_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "done",
                            "completion_review_status": "ship"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": "2020-01-01T00:00:00Z",
                         "linkState": "linked"},
            )
            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="open", labels=["status:in_progress"])),
                "merge-evidence": ok([]),  # none — no merged PR
            })
            out = S.status(flow, "fn-1-demo", to="done", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["lastSyncedAt"], "2020-01-01T00:00:00Z")
            # No status-set mutation was issued
            self.assertFalse(any(c.op == "status-set" for c in ex.calls))

    def test_garbage_reason_invalid_input_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, gh_cfg())
            ex = fake_execute({})  # any network op would AssertionError
            out = S.status(flow, "fn-1-demo", to="done", reason="garbage",
                           execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
            self.assertEqual(len(ex.calls), 0)

    def test_github_reason_duplicate_lands_state_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "done",
                            "completion_review_status": "unknown"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": None, "linkState": "linked"},
            )
            # ungated completion review so merged → done
            cfg_path = flow / "config.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg["review"] = {"backend": "none"}
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

            bodies = []

            def capture_set(req):
                bodies.append(json.loads(req.body))
                return ok({"node_id": GH_NODE, "number": 42, "state": "closed",
                           "state_reason": "duplicate"})

            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="open", labels=["status:in_review"])),
                "merge-evidence": ok([{"state": "MERGED", "number": 1}]),
                "status-set": capture_set,
                "status-label-rm": empty_ok(),
                "status-label-add": ok([{"name": "status:done"}]),
                "status-label-readback": ok([{"name": "status:done"}]),
            })
            out = S.status(flow, "fn-1-demo", to="done", reason="duplicate",
                           execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["kind"], "applied")
            self.assertEqual(bodies[0]["state"], "closed")
            self.assertEqual(bodies[0]["state_reason"], "duplicate")
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertIsNotNone(saved["lastSyncedAt"])

    def test_last_synced_advanced_only_on_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": "OLD", "linkState": "linked"},
                tasks=[{"status": "in_progress"}],
            )
            # noop path: tracker already in_progress, flow in_progress
            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="open", labels=["status:in_progress"])),
                "merge-evidence": ok([]),
            })
            out = S.status(flow, "fn-1-demo", to="in_progress", execute=ex)
            self.assertEqual(out["kind"], "noop")
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["lastSyncedAt"], "OLD")
            self.assertEqual(_receipts(flow), [])

    def test_defer_writes_receipt_without_advancing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "done",
                            "completion_review_status": "ship"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": "OLD", "linkState": "linked"},
            )
            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="open", labels=["status:in_progress"])),
                "merge-evidence": ok([{"state": "CLOSED"}]),
            })
            out = S.status(flow, "fn-1-demo", to="done", execute=ex)
            # R7: ambiguous evidence is a CONFLICT error, not a defer success.
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "closed-unmerged")
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["lastSyncedAt"], "OLD")
            # A conflict is the skill's recovery surface - no defer receipt.
            self.assertEqual(_receipts(flow), [])

    def test_identifier_only_is_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, gh_cfg(), tracker={
                "id": None, "identifier": "#42", "linkState": "identifier_only",
            })
            ex = fake_execute({})
            out = S.status(flow, "fn-1-demo", to="in_progress", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.UNRESOLVED)
            self.assertIn("identifier_only", out.message)


class GitlabOpenedClosed(unittest.TestCase):
    def test_close_sends_state_event_close_and_opened_is_understood(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(
                flow, gl_cfg(),
                spec_extra={"status": "done"},
                tracker={"id": GL_ID, "identifier": "g/p#12", "url": "u",
                         "lastSyncedAt": None, "linkState": "linked"},
            )
            cfg = json.loads((flow / "config.json").read_text(encoding="utf-8"))
            cfg["review"] = {"backend": "none"}
            (flow / "config.json").write_text(json.dumps(cfg), encoding="utf-8")

            bodies = []

            def capture(req):
                bodies.append(json.loads(req.body))
                return ok({"id": int(GL_ID), "iid": 12, "state": "closed",
                           "labels": ["status:done"]})

            ex = fake_execute({
                "status-parent-read": ok({
                    "id": int(GL_ID), "iid": 12, "state": "opened",
                    "labels": ["status:in_review"],
                }),
                "merge-evidence": ok([{"state": "MERGED"}]),
                "status-set": capture,
            })
            out = S.status(flow, "fn-1-demo", to="done", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["kind"], "applied")
            self.assertEqual(bodies[0]["state_event"], "close")
            # parent was opened (not "open") — norm extracted without conflict
            self.assertEqual(out["tracker"], "in_review")


class JiraTransitions(unittest.TestCase):
    def test_no_legal_transition_defers_with_receipt_no_advance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, jr_cfg(),
                spec_extra={"status": "open"},
                tracker={"id": JR_ID, "identifier": "SCRUM-1", "url": "u",
                         "lastSyncedAt": "OLD", "linkState": "linked"},
                tasks=[{"status": "in_progress"}],
            )
            ex = fake_execute({
                "status-parent-read": ok({
                    "id": JR_ID, "key": "SCRUM-1",
                    "fields": {"status": {"id": "1", "name": "To Do",
                                          "statusCategory": {"key": "new"}}},
                }),
                "merge-evidence": ok([]),
                "status-current": ok({
                    "fields": {"status": {"id": "1", "name": "To Do"}},
                }),
                # Legal transitions do NOT include target in_progress (id 2)
                "status-transitions": ok({
                    "transitions": [
                        {"id": "11", "to": {"id": "4", "name": "Done"}},
                    ],
                }),
            })
            out = S.status(flow, "fn-1-demo", to="in_progress", execute=ex)
            self.assertEqual(out["kind"], "defer")
            self.assertEqual(out["reason"], "transition-unreachable")
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["lastSyncedAt"], "OLD")
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["status"], "deferred")
            # Never issued status-set (forced jump)
            self.assertFalse(any(c.op == "status-set" for c in ex.calls))
            # Did GET transitions (no cached transition id)
            self.assertTrue(any(c.op == "status-transitions" for c in ex.calls))

    def test_legal_transition_posts_matched_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(
                flow, jr_cfg(),
                tracker={"id": JR_ID, "identifier": "SCRUM-1", "url": "u",
                         "lastSyncedAt": None, "linkState": "linked"},
                tasks=[{"status": "in_progress"}],
            )
            bodies = []

            def capture(req):
                bodies.append(json.loads(req.body))
                return empty_ok()

            ex = fake_execute({
                "status-parent-read": ok({
                    "id": JR_ID, "key": "SCRUM-1",
                    "fields": {"status": {"id": "1", "name": "To Do",
                                          "statusCategory": {"key": "new"}}},
                }),
                "merge-evidence": ok([]),
                "status-current": ok({
                    "fields": {"status": {"id": "1"}},
                }),
                "status-transitions": ok({
                    "transitions": [
                        {"id": "21", "to": {"id": "2", "name": "In Progress"}},
                        {"id": "31", "to": {"id": "4", "name": "Done"}},
                    ],
                }),
                "status-set": capture,
            })
            out = S.status(flow, "fn-1-demo", to="in_progress", execute=ex)
            self.assertEqual(out["kind"], "applied")
            self.assertEqual(bodies[0]["transition"]["id"], "21")


class LinearStateIds(unittest.TestCase):
    def test_applies_cached_state_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(
                flow, ln_cfg(),
                tracker={"id": LN_UUID, "identifier": "WOR-1", "url": "u",
                         "lastSyncedAt": None, "linkState": "linked"},
                tasks=[{"status": "in_progress"}],
            )
            variables = []

            def capture(req):
                body = json.loads(req.body)
                variables.append(body.get("variables"))
                return ok({"data": {"issueUpdate": {
                    "success": True, "issue": {"id": LN_UUID}}}})

            ex = fake_execute({
                "status-parent-read": ok({"data": {
                    "issue": {"id": LN_UUID, "identifier": "WOR-1",
                              "title": "t", "description": "", "url": "u",
                              "updatedAt": "t", "labels": {"nodes": []},
                              "assignee": None},
                }}),
                "status-state-read": ok({"data": {
                    "issue": {"id": LN_UUID,
                              "state": {"id": "s-todo", "name": "Todo",
                                        "type": "unstarted"}},
                }}),
                "merge-evidence": ok([]),
                "status-set": capture,
            })
            out = S.status(flow, "fn-1-demo", to="in_progress", execute=ex)
            self.assertNotIsInstance(out, TrackerError, msg=repr(out))
            self.assertEqual(out["kind"], "applied")
            self.assertEqual(variables[0]["stateId"], "s-ip")


class ReorderingUnit(unittest.TestCase):
    def test_decide_deadlock_before_terminal_wins(self) -> None:
        """Parametrized guard: monkeypatching order would flip the outcome."""
        flow, tracker = "in_progress", "done"
        # Document the dual-match that makes order load-bearing.
        self.assertTrue(is_deadlock(flow, tracker))
        self.assertTrue(terminal_wins_matches(flow, tracker))

        real = decide("todo", None, flow, tracker, "none")
        self.assertEqual(real.kind, "conflict")

        # If someone moved deadlock AFTER terminal-wins, the earlier branch
        # would return noop. Simulate that wrong ladder:
        def wrong_order(requested_to, reason, flow_norm, tracker_norm, pr_evidence):
            if terminal_wins_matches(flow_norm, tracker_norm):
                return S.Decision("noop", target_slot=tracker_norm)
            if is_deadlock(flow_norm, tracker_norm):
                return S.Decision("conflict", reason="status-deadlock")
            return S.Decision("conflict", reason="unmapped")

        wrong = wrong_order("todo", None, flow, tracker, "none")
        self.assertEqual(wrong.kind, "noop")
        self.assertNotEqual(real.kind, wrong.kind)


if __name__ == "__main__":
    unittest.main()


class Round1HostFixes(unittest.TestCase):
    """Tracker-terminal local fold + partial label accounting."""

    def test_tracker_terminal_folds_into_local_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "open"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": None, "linkState": "linked"},
            )
            # PM closed the issue (completed); flow is NOT in_progress (no tasks
            # started) -> tracker wins, folded LOCALLY, no tracker mutation.
            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="closed", labels=[], state_reason="completed")),
                "merge-evidence": ok([]),
            })
            out = S.status(flow, "fn-1-demo", to="todo", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["kind"], "applied_local")
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "done", "local spec folded")
            self.assertIsNotNone(saved["tracker"]["lastSyncedAt"])
            mutations = [c for c in ex.calls if c.op == "status-set"]
            self.assertEqual(mutations, [], "no tracker write on a local fold")
            receipts = _receipts(flow)
            self.assertEqual(receipts[0]["status"], "pulled")

    def test_partial_label_failure_is_explicit_never_silent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "done", "completion_review_status": "unknown"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": None, "linkState": "linked"},
            )
            cfg_path = flow / "config.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg["review"] = {"backend": "none"}
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="open", labels=["status:in_review"])),
                "merge-evidence": ok([{"state": "MERGED"}]),
                "status-set": ok({"node_id": GH_NODE, "number": 42,
                                  "state": "closed"}),
                "status-label-rm": empty_ok(),
                "status-label-add": TrackerError(ErrorClass.TRANSPORT, "boom"),
                "status-label-readback": ok([{"name": "status:in_review"}]),
            })
            out = S.status(flow, "fn-1-demo", to="done", execute=ex)
            self.assertNotIsInstance(out, TrackerError,
                                     "the STATE change landed - not a bare failure")
            self.assertEqual(out["kind"], "applied")
            write = out["write"]
            self.assertEqual(write["completed_steps"], ["state"])
            self.assertEqual(write["degraded"]["kind"], "status_labels_inconsistent")
            self.assertIn({"op": "add", "label": "status:done", "error": "boom"},
                          write["degraded"]["failures"])

    def test_readback_failure_is_degraded_even_when_label_ops_succeed(self) -> None:
        """A failed label readback must surface as degraded evidence even when
        every preceding label op succeeded - the single-valued invariant is
        unverifiable, so the verb cannot claim clean success."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "done", "completion_review_status": "unknown"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": None, "linkState": "linked"},
            )
            cfg_path = flow / "config.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg["review"] = {"backend": "none"}
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="open", labels=["status:in_review"])),
                "merge-evidence": ok([{"state": "MERGED"}]),
                "status-set": ok({"node_id": GH_NODE, "number": 42,
                                  "state": "closed"}),
                "status-label-rm": empty_ok(),
                "status-label-add": ok([{"name": "status:done"}]),
                "status-label-readback": TrackerError(
                    ErrorClass.TRANSPORT, "readback boom"),
            })
            out = S.status(flow, "fn-1-demo", to="done", execute=ex)
            self.assertNotIsInstance(out, TrackerError,
                                     "state landed - never a bare failure")
            self.assertEqual(out["kind"], "applied")
            write = out["write"]
            self.assertEqual(write["degraded"]["kind"], "status_labels_unverified")
            self.assertIn({"op": "readback", "error": "readback boom"},
                          write["degraded"]["failures"])
            # The DURABLE receipt must carry the same degradation - the result
            # dict alone is ephemeral (PR #246 review).
            receipts = _receipts(flow)
            self.assertEqual(receipts[0]["status"], "updated")
            self.assertEqual(receipts[0]["degraded"]["kind"],
                             "status_labels_unverified")


class Round4PersistIntegrity(unittest.TestCase):
    """PR #246 review: reload-under-lock persistence for the applied paths."""

    def test_applied_write_does_not_erase_concurrent_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "done",
                            "completion_review_status": "unknown"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": None, "linkState": "linked"},
            )
            cfg_path = flow / "config.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg["review"] = {"backend": "none"}
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

            def concurrent_set(req):
                # Another command updates the same spec while status() is
                # mid-flight (after its snapshot load, before its persist).
                data = json.loads(path.read_text(encoding="utf-8"))
                data["title"] = "CONCURRENT"
                path.write_text(json.dumps(data), encoding="utf-8")
                return ok({"node_id": GH_NODE, "number": 42, "state": "closed"})

            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="open", labels=["status:in_review"])),
                "merge-evidence": ok([{"state": "MERGED"}]),
                "status-set": concurrent_set,
                "status-label-rm": empty_ok(),
                "status-label-add": ok([{"name": "status:done"}]),
                "status-label-readback": ok([{"name": "status:done"}]),
            })
            out = S.status(flow, "fn-1-demo", to="done", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["kind"], "applied")
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["title"], "CONCURRENT",
                             "persist must reload, never replay the stale snapshot")
            self.assertIsNotNone(saved["tracker"]["lastSyncedAt"])

    def test_persist_failure_after_tracker_write_reports_the_write(self) -> None:
        """PR #246 review: when the provider mutation LANDED but the locked
        local persistence fails, the returned error must carry the completed
        provider write (completed_steps + write details, mirroring the
        syncbody post-write pattern) and lastSyncedAt must NOT advance."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "done",
                            "completion_review_status": "unknown"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": None, "linkState": "linked"},
            )
            cfg_path = flow / "config.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg["review"] = {"backend": "none"}
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

            def corrupt_after_readback(req):
                # Persistence reloads the spec under the lock; corrupting it
                # after the final provider call makes that reload fail while
                # the tracker mutation has already landed.
                path.write_text("{not json", encoding="utf-8")
                return ok([{"name": "status:done"}])

            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="open", labels=["status:in_review"])),
                "merge-evidence": ok([{"state": "MERGED"}]),
                "status-set": ok({"node_id": GH_NODE, "number": 42,
                                  "state": "closed"}),
                "status-label-rm": empty_ok(),
                "status-label-add": ok([{"name": "status:done"}]),
                "status-label-readback": corrupt_after_readback,
            })
            out = S.status(flow, "fn-1-demo", to="done", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIn("after tracker write", out.message)
            details = out.details or {}
            self.assertEqual(details["completed_steps"], ["status-write"])
            self.assertEqual(details["target"], "done")
            write = details["write"]
            self.assertIsInstance(write, dict,
                                  "landed provider write must be reported")
            self.assertEqual(write["applied"], "done")
            self.assertIn("state", write["completed_steps"])
            # lastSyncedAt must NOT advance - it advances only on applied.
            mutations = [c for c in ex.calls if c.op == "status-set"]
            self.assertEqual(len(mutations), 1, "the mutation DID land")
            self.assertNotIn("lastSyncedAt",
                             path.read_text(encoding="utf-8"),
                             "no persisted advance on a failed persist")

    def test_local_fold_does_not_erase_concurrent_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "open"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": None, "linkState": "linked"},
            )

            def concurrent_parent(req):
                data = json.loads(path.read_text(encoding="utf-8"))
                data["title"] = "CONCURRENT"
                path.write_text(json.dumps(data), encoding="utf-8")
                return ok(_gh_parent(state="closed", labels=[],
                                     state_reason="completed"))

            ex = fake_execute({
                "status-parent-read": concurrent_parent,
                "merge-evidence": ok([]),
            })
            out = S.status(flow, "fn-1-demo", to="todo", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["kind"], "applied_local")
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["title"], "CONCURRENT")
            self.assertEqual(saved["status"], "done", "fold still lands")
            self.assertIsNotNone(saved["tracker"]["lastSyncedAt"])


class BlockedTasksAreWorkUnderway(unittest.TestCase):
    """PR #246 review: status-sync.md says blocked tasks do not change the
    spec-level normalized status - "the issue stays `in-progress`" - so an
    all-blocked spec with no PR signal derives in_progress, never todo."""

    def test_all_blocked_no_pr_signal_is_in_progress_per_status_sync_md(self) -> None:
        spec = {"status": "open", "completion_review_status": "unknown"}
        out = flow_to_normalized(
            spec, "none", True,
            tasks=[{"status": "blocked"}, {"status": "blocked"}])
        self.assertEqual(out, "in_progress")

    def test_blocked_among_todo_is_still_in_progress(self) -> None:
        spec = {"status": "open", "completion_review_status": "unknown"}
        out = flow_to_normalized(
            spec, "none", True,
            tasks=[{"status": "todo"}, {"status": "blocked"}])
        self.assertEqual(out, "in_progress")


NEW_NODE = "I_kwDORepointed99"


class Round6IdentityGuard(unittest.TestCase):
    """PR #246 review: spec repointed to a different issue while the parent
    read / PR probe / provider write was in flight must not persist onto the
    NEW link (linkstate._complete pattern - refuse with structured CONFLICT,
    persist nothing)."""

    @staticmethod
    def _repoint(path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["tracker"] = {"id": NEW_NODE, "identifier": "#99",
                           "url": "https://x/99", "lastSyncedAt": None,
                           "linkState": "linked"}
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_applied_path_refuses_persist_after_repoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "done",
                            "completion_review_status": "unknown"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": None, "linkState": "linked"},
            )
            cfg_path = flow / "config.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg["review"] = {"backend": "none"}
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

            def repoint_then_ok(req):
                # Another command repoints the spec to a different issue
                # while the provider status write is in flight.
                self._repoint(path)
                return ok([{"name": "status:done"}])

            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="open", labels=["status:in_review"])),
                "merge-evidence": ok([{"state": "MERGED"}]),
                "status-set": ok({"node_id": GH_NODE, "number": 42,
                                  "state": "closed"}),
                "status-label-rm": empty_ok(),
                "status-label-add": ok([{"name": "status:done"}]),
                "status-label-readback": repoint_then_ok,
            })
            out = S.status(flow, "fn-1-demo", to="done", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertEqual(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "identity_drift")
            details = out.details or {}
            self.assertEqual(details["expected"]["id"], GH_NODE)
            self.assertEqual(details["found"]["id"], NEW_NODE)
            # The landed provider write is still reported (never silent).
            self.assertEqual(details["completed_steps"], ["status-write"])
            # lastSyncedAt on the NEW link untouched - persist refused.
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["tracker"]["id"], NEW_NODE)
            self.assertIsNone(saved["tracker"]["lastSyncedAt"])
            self.assertEqual(_receipts(flow), [],
                             "no receipt for a refused persist")

    def test_apply_local_refuses_done_fold_after_repoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "open"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": None, "linkState": "linked"},
            )

            def repoint_parent(req):
                # Repoint mid-flight; the OLD issue reads closed/terminal.
                self._repoint(path)
                return ok(_gh_parent(state="closed", labels=[],
                                     state_reason="completed"))

            ex = fake_execute({
                "status-parent-read": repoint_parent,
                "merge-evidence": ok([]),
            })
            out = S.status(flow, "fn-1-demo", to="todo", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertEqual(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "identity_drift")
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "open",
                             "done must NOT fold from the OLD issue's "
                             "terminal state onto the repointed spec")
            self.assertEqual(saved["tracker"]["id"], NEW_NODE)
            self.assertIsNone(saved["tracker"]["lastSyncedAt"])
            self.assertEqual(_receipts(flow), [])


class Round2Ordering(unittest.TestCase):
    def test_terminal_agreement_is_a_noop_never_a_refold(self) -> None:
        d = decide("done", None, "done", "done", "merged")
        self.assertEqual(d.kind, "noop")

    def test_ambiguous_evidence_beats_tracker_terminal_fold(self) -> None:
        for ev in ("ambiguous", "closed-unmerged", "probe-error"):
            with self.subTest(evidence=ev):
                d = decide("done", None, "in_review", "done", ev)
                self.assertEqual(d.kind, "conflict")
                self.assertEqual(d.reason, ev)

    def test_clean_disagreement_still_folds(self) -> None:
        d = decide("todo", None, "todo", "done", "none")
        self.assertEqual(d.kind, "apply_local")


class Round3Ordering(unittest.TestCase):
    def test_equality_does_not_mask_evidence_conflicts(self) -> None:
        """flow==tracker==in_review with non-clean evidence and --to done must
        still surface the conflict - equality evaluates AFTER evidence."""
        for ev in ("ambiguous", "closed-unmerged", "probe-error"):
            with self.subTest(evidence=ev):
                d = decide("done", None, "in_review", "in_review", ev)
                self.assertEqual(d.kind, "conflict")
                self.assertEqual(d.reason, ev)

    def test_clean_equality_still_noops(self) -> None:
        d = decide("in_review", None, "in_review", "in_review", "open")
        self.assertEqual(d.kind, "noop")


class AmbiguousStatusLabels(unittest.TestCase):
    """status:* is a single-valued namespace (github.md/gitlab.md "Idempotent
    status: labels"): multiple recognized status:* labels classify as a
    CONFLICT, never a silent provider-order first-match."""

    def test_two_recognized_labels_conflict_github_order_independent(self) -> None:
        for labels in (["status:in_progress", "status:in_review"],
                       ["status:in_review", "status:in_progress"],
                       ["status:done", "status:verified"]):  # same-slot pair
            with self.subTest(labels=labels):
                out = tracker_norm_from_parent(
                    "github", _gh_parent(state="open", labels=labels), {})
                self.assertIsInstance(out, TrackerError)
                self.assertIs(out.cls, ErrorClass.CONFLICT)
                self.assertEqual(out.subtype, "ambiguous-status-labels")
                self.assertEqual(sorted(out.details["labels"]), sorted(labels))

    def test_two_recognized_labels_conflict_gitlab(self) -> None:
        parent = {"state": "opened",
                  "labels": ["status:todo", "status:done"]}
        out = tracker_norm_from_parent("gitlab", parent, {})
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual(out.subtype, "ambiguous-status-labels")

    def test_gitlab_closed_with_conflicting_labels_is_conflict(self) -> None:
        # closed + {wontfix, done} is order-dependent (cancelled vs done)
        # under first-match; must surface instead.
        parent = {"state": "closed",
                  "labels": ["status:wontfix", "status:done"]}
        out = tracker_norm_from_parent("gitlab", parent, {})
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual(out.subtype, "ambiguous-status-labels")

    def test_single_recognized_label_still_classifies(self) -> None:
        out = tracker_norm_from_parent(
            "github", _gh_parent(state="open", labels=["status:in_review"]), {})
        self.assertEqual(out, "in_review")
        out = tracker_norm_from_parent(
            "gitlab", {"state": "opened", "labels": ["status:todo"]}, {})
        self.assertEqual(out, "todo")

    def test_unrecognized_extra_status_labels_are_ignored(self) -> None:
        out = tracker_norm_from_parent(
            "github",
            _gh_parent(state="open",
                       labels=["status:custom-bucket", "status:in_review"]),
            {})
        self.assertEqual(out, "in_review")

    def test_no_silent_noop_when_first_label_matches_derived(self) -> None:
        """Mirror of test_last_synced_advanced_only_on_applied with one extra
        recognized label AFTER the matching one: first-match used to make
        tracker_norm == flow_norm == requested → noop, permanently leaving
        the single-valued namespace inconsistent. Must surface instead."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": "OLD", "linkState": "linked"},
                tasks=[{"status": "in_progress"}],
            )
            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="open",
                    labels=["status:in_progress", "status:in_review"])),
            })
            out = S.status(flow, "fn-1-demo", to="in_progress", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(out.subtype, "ambiguous-status-labels")
            # No mutation, no lastSyncedAt advance, no receipt.
            self.assertFalse(any(c.op == "status-set" for c in ex.calls))
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["lastSyncedAt"], "OLD")
            self.assertEqual(_receipts(flow), [])
