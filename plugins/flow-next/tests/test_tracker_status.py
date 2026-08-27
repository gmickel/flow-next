"""status verb: fn-66 merge-evidence gate + who-wins ladder (fn-140.3).

Fake transport = injected executor seam (same harness as test_tracker_lifecycle).
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

from flowctl_tracker import status as S  # noqa: E402
from flowctl_tracker.status import verb as V  # noqa: E402
from flowctl_tracker.status.policy import (  # noqa: E402
    COMPLETION_REVIEW_SATISFYING, COMPLETION_REVIEW_STATUSES,
    decide, flow_to_normalized, in_progress_wins_matches, is_deadlock,
    merge_evidence, terminal_wins_matches, validate_conflict_tiebreak,
)
from flowctl_tracker.status.providers import (  # noqa: E402
    apply_status, tracker_norm_from_parent,
)
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

    def test_completion_review_member_enumeration_pins_projection(self) -> None:
        # fn-205 R7: every known member is classified explicitly; adding a
        # member fails here until it is deliberately classified.
        self.assertEqual(
            set(COMPLETION_REVIEW_STATUSES),
            {"ship", "needs_work", "needs_human", "unknown", "not_required"},
        )
        self.assertEqual(
            COMPLETION_REVIEW_SATISFYING, frozenset({"ship", "not_required"})
        )
        for member in COMPLETION_REVIEW_STATUSES:
            expected = (
                "done" if member in COMPLETION_REVIEW_SATISFYING else "in_review"
            )
            spec = {"status": "done", "completion_review_status": member}
            with self.subTest(member=member):
                self.assertEqual(
                    flow_to_normalized(spec, "merged", True), expected)

    def test_not_required_never_terminal_without_merged(self) -> None:
        # fn-205 R2: policy-excused review does not weaken the merge gate.
        spec = {"status": "done", "completion_review_status": "not_required"}
        for ev in ("none", "closed-unmerged", "ambiguous", "probe-error", "open"):
            with self.subTest(ev=ev):
                self.assertEqual(flow_to_normalized(spec, ev, True), "in_review")

    def test_unrecognized_or_absent_review_value_satisfies_nothing(self) -> None:
        # fn-205 R7 fail-closed: garbage or absent reads as unknown.
        for review in ("garbage", None):
            spec = {"status": "done"}
            if review is not None:
                spec["completion_review_status"] = review
            with self.subTest(review=review):
                self.assertEqual(
                    flow_to_normalized(spec, "merged", True), "in_review")


# ---------------------------------------------------------------------------
# decide — deadlock FIRST + reordering guard
# ---------------------------------------------------------------------------

class DecideLadder(unittest.TestCase):
    def test_deadlock_returns_conflict_never_silent(self) -> None:
        d = decide("done", None, "in_progress", "done", "none")
        self.assertEqual(d.kind, "conflict")
        self.assertEqual(d.reason, "status-deadlock")

    def test_deadlock_tiebreak_matrix_covers_both_orientations(self) -> None:
        pairs = (
            ("in_progress", "done"),
            ("done", "in_progress"),
        )
        for flow, tracker in pairs:
            with self.subTest(policy="always-ask", flow=flow, tracker=tracker):
                d = decide(
                    flow, None, flow, tracker, "merged", "always-ask")
                self.assertEqual((d.kind, d.reason),
                                 ("conflict", "status-deadlock"))
            with self.subTest(policy="flow-wins", flow=flow, tracker=tracker):
                d = decide(
                    flow, None, flow, tracker, "merged", "flow-wins")
                self.assertEqual((d.kind, d.target_slot), ("apply", flow))

        terminal = decide(
            "in_progress", None, "in_progress", "done", "none",
            "tracker-wins")
        self.assertEqual(
            (terminal.kind, terminal.target_slot), ("apply_local", "done"))

        mirror = decide(
            "done", None, "done", "in_progress", "merged",
            "tracker-wins")
        self.assertEqual(mirror.kind, "conflict")
        self.assertEqual(mirror.reason, "status-deadlock-unrepresentable")
        self.assertTrue(mirror.details["unrepresentable"])

    def test_conflict_tiebreak_runtime_validation(self) -> None:
        self.assertEqual(validate_conflict_tiebreak({}), "always-ask")
        self.assertEqual(
            validate_conflict_tiebreak({"tracker": {}}), "always-ask")
        for value in ("always-ask", "flow-wins", "tracker-wins"):
            self.assertEqual(
                validate_conflict_tiebreak(
                    {"tracker": {"conflictTiebreak": value}}),
                value,
            )
        for value in (None, True, "FLOW-WINS", "typo", 1):
            with self.subTest(value=value):
                out = validate_conflict_tiebreak(
                    {"tracker": {"conflictTiebreak": value}})
                self.assertIsInstance(out, TrackerError)
                self.assertIs(out.cls, ErrorClass.INVALID_INPUT)

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

    def test_not_planned_reason_rejected_for_done(self) -> None:
        d = decide("done", "not_planned", "done", "in_review", "merged")
        self.assertEqual(d.kind, "invalid_input")

    def test_done_reasons_rejected_for_cancelled(self) -> None:
        for reason in ("completed", "duplicate"):
            with self.subTest(reason=reason):
                d = decide(
                    "cancelled", reason, "done", "in_review", "merged")
                self.assertEqual(d.kind, "invalid_input")

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
    def test_out_of_tree_issue_repo_never_redirects_pr_probe(self) -> None:
        cfg = gh_cfg()
        cfg["tracker"]["resolved"]["destination"] = {
            "owner": "other-owner",
            "repo": "out-of-tree-issues",
        }
        ex = fake_execute({"merge-evidence": ok([])})

        self.assertEqual(
            merge_evidence(cfg, {"branch_name": "feature-branch"}, ex),
            "none")
        argv = list(ex.calls[0].url_or_argv)
        self.assertNotIn("-R", argv)
        self.assertEqual(argv[:3], ["gh", "pr", "list"])

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
    def test_malformed_tiebreak_fails_before_claim_or_executor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            cfg = gh_cfg()
            cfg["tracker"]["conflictTiebreak"] = "flow-WINS"
            path = _write_flow(
                flow, cfg,
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": "OLD", "linkState": "linked"},
            )
            before = path.read_text(encoding="utf-8")
            ex = fake_execute({})
            out = S.status(
                flow, "fn-1-demo", to="in_progress", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
            self.assertEqual(out.subtype, "conflict_tiebreak")
            self.assertEqual(ex.calls, [])
            self.assertEqual(path.read_text(encoding="utf-8"), before)
            self.assertFalse(
                (flow / "create-first" / "status-fn-1-demo.json").exists())
            self.assertEqual(_receipts(flow), [])

    def test_tracker_wins_terminal_reuses_local_fold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            cfg = gh_cfg()
            cfg["tracker"]["conflictTiebreak"] = "tracker-wins"
            path = _write_flow(
                flow, cfg,
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": "OLD", "linkState": "linked"},
                tasks=[{"status": "in_progress"}],
            )
            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="closed", labels=["status:done"],
                    state_reason="completed")),
                "merge-evidence": ok([]),
            })
            out = S.status(
                flow, "fn-1-demo", to="in_progress", execute=ex)
            self.assertNotIsInstance(out, TrackerError, out)
            self.assertEqual(out["kind"], "applied_local")
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "done")
            self.assertNotEqual(saved["tracker"]["lastSyncedAt"], "OLD")
            self.assertFalse(any(c.op == "status-set" for c in ex.calls))
            self.assertEqual(_receipts(flow)[0]["status"], "pulled")

    def test_tracker_wins_active_mirror_is_unrepresentable_no_mutation(
            self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            cfg = gh_cfg()
            cfg["tracker"]["conflictTiebreak"] = "tracker-wins"
            cfg["review"] = {"backend": "none"}
            path = _write_flow(
                flow, cfg, spec_extra={"status": "done"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": "OLD", "linkState": "linked"},
            )
            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="open", labels=["status:in-progress"])),
                "merge-evidence": ok([{"state": "MERGED"}]),
            })
            out = S.status(flow, "fn-1-demo", to="done", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CONFLICT)
            self.assertEqual(
                out.subtype, "status-deadlock-unrepresentable")
            self.assertTrue(out.details["unrepresentable"])
            self.assertFalse(any(c.op == "status-set" for c in ex.calls))
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "done")
            self.assertEqual(saved["tracker"]["lastSyncedAt"], "OLD")
            self.assertEqual(_receipts(flow), [])

    def test_jira_tls_policy_does_not_bind_source_repo_pr_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            cfg = jr_cfg()
            cfg["tracker"]["perTracker"] = {"sslVerify": False}
            _write_flow(
                flow, cfg,
                spec_extra={"status": "done"},
                tracker={
                    "id": JR_ID, "identifier": "SCRUM-1", "url": "u",
                    "lastSyncedAt": None, "linkState": "linked",
                },
            )
            parent = {
                "id": JR_ID,
                "key": "SCRUM-1",
                "fields": {
                    "status": {"id": "4", "name": "Done"},
                    "labels": [],
                },
            }
            raw = fake_execute({
                "merge-evidence": ok([{"state": "MERGED", "number": 1}]),
            })
            tracker_bound = fake_execute({
                "status-parent-read": ok(parent),
            })

            with mock.patch(
                    "flowctl_tracker.resolve_verb.bound_executor",
                    return_value=tracker_bound):
                out = S.status(
                    flow, "fn-1-demo", to="done", execute=raw)

            self.assertNotIsInstance(out, TrackerError, out)
            self.assertEqual(out["kind"], "noop")
            self.assertEqual(
                [c.op for c in raw.calls], ["merge-evidence"],
                "gh probe uses the unbound source-repository executor")
            self.assertEqual(
                [c.op for c in tracker_bound.calls], ["status-parent-read"])

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

    def test_not_planned_done_invalid_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, gh_cfg())
            ex = fake_execute({})  # any network op would AssertionError
            out = S.status(
                flow, "fn-1-demo", to="done", reason="not_planned",
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
            out = S.status(
                flow, "fn-1-demo", to="in_progress",
                event="work.firstClaim", execute=ex)
            self.assertEqual(out["kind"], "noop")
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["lastSyncedAt"], "OLD")
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["status"], "noop")
            self.assertEqual(receipts[0]["event"], "work.firstClaim")

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


class CanonicalStatusLabelWrites(unittest.TestCase):
    def test_github_and_gitlab_write_hyphenated_active_labels(self) -> None:
        for provider, target in (
            ("github", "in_progress"),
            ("github", "in_review"),
            ("gitlab", "in_progress"),
            ("gitlab", "in_review"),
        ):
            with self.subTest(provider=provider, target=target):
                expected = f"status:{target.replace('_', '-')}"
                captured: list[dict] = []

                def capture(
                        req, captured=captured, provider=provider,
                        expected=expected):
                    captured.append(json.loads(req.body))
                    if provider == "github":
                        return ok([{"name": expected}])
                    return ok({
                        "id": int(GL_ID), "iid": 12, "state": "opened",
                        "labels": [expected],
                    })

                if provider == "github":
                    ex = fake_execute({
                        "status-set": ok({
                            "node_id": GH_NODE, "number": 42,
                            "state": "open",
                        }),
                        "status-label-rm": empty_ok(),
                        "status-label-add": capture,
                        "status-label-readback": ok([{"name": expected}]),
                    })
                    out = apply_status(
                        provider, gh_cfg(),
                        {"durable": GH_NODE, "display": "#42"},
                        _gh_parent(state="open", labels=["status:todo"]),
                        ex, target_slot=target)
                    self.assertEqual(captured[0]["labels"], [expected])
                else:
                    ex = fake_execute({"status-set": capture})
                    out = apply_status(
                        provider, gl_cfg(),
                        {"durable": GL_ID, "display": "g/p#12"},
                        {
                            "id": int(GL_ID), "iid": 12, "state": "opened",
                            "labels": ["status:todo"],
                        },
                        ex, target_slot=target)
                    self.assertEqual(captured[0]["add_labels"], expected)
                self.assertNotIsInstance(out, TrackerError, out)
                self.assertEqual(out["label"], expected)


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


class ProviderDeadlockParity(unittest.TestCase):
    def test_all_providers_reach_shared_always_ask_decision(self) -> None:
        fixtures = (
            (
                "github", gh_cfg(), GH_NODE, "#42",
                {
                    "status-parent-read": ok(_gh_parent(
                        state="closed", labels=["status:done"],
                        state_reason="completed")),
                },
            ),
            (
                "gitlab", gl_cfg(), GL_ID, "g/p#12",
                {
                    "status-parent-read": ok({
                        "id": int(GL_ID), "iid": 12, "state": "closed",
                        "labels": ["status:done"],
                    }),
                },
            ),
            (
                "linear", ln_cfg(), LN_UUID, "WOR-1",
                {
                    "status-parent-read": ok({"data": {
                        "issue": {
                            "id": LN_UUID, "identifier": "WOR-1",
                            "title": "t", "description": "", "url": "u",
                            "updatedAt": "t", "labels": {"nodes": []},
                            "assignee": None,
                        },
                    }}),
                    "status-state-read": ok({"data": {
                        "issue": {
                            "id": LN_UUID,
                            "state": {
                                "id": "s-done", "name": "Done",
                                "type": "completed",
                            },
                        },
                    }}),
                },
            ),
            (
                "jira", jr_cfg(), JR_ID, "SCRUM-1",
                {
                    "status-parent-read": ok({
                        "id": JR_ID, "key": "SCRUM-1",
                        "fields": {
                            "status": {"id": "4", "name": "Done"},
                            "labels": [],
                        },
                    }),
                },
            ),
        )
        for provider, config, durable, display, responses in fixtures:
            with self.subTest(provider=provider), tempfile.TemporaryDirectory() as tmp:
                flow = Path(tmp) / ".flow"
                _write_flow(
                    flow, config,
                    tracker={
                        "id": durable, "identifier": display, "url": "u",
                        "lastSyncedAt": "OLD", "linkState": "linked",
                    },
                    tasks=[{"status": "in_progress"}],
                )
                ex = fake_execute({
                    **responses,
                    "merge-evidence": ok([]),
                })
                out = S.status(
                    flow, "fn-1-demo", to="in_progress", execute=ex)
                self.assertIsInstance(out, TrackerError)
                self.assertIs(out.cls, ErrorClass.CONFLICT)
                self.assertEqual(out.subtype, "status-deadlock")
                self.assertFalse(any(c.op == "status-set" for c in ex.calls))
                self.assertEqual(_receipts(flow), [])


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

    def test_remove_failure_is_repaired_before_durable_success(self) -> None:
        """A failed remove plus successful add first proves two status labels.
        One bounded cleanup/readback repairs the namespace before success."""
        ex = fake_execute({
            "status-set": ok({"node_id": GH_NODE, "number": 42,
                              "state": "closed"}),
            "status-label-rm": [
                TrackerError(ErrorClass.TRANSPORT, "remove boom"),
                empty_ok(),
            ],
            "status-label-add": ok([{"name": "status:done"}]),
            "status-label-readback": [
                ok([{"name": "status:in_review"},
                    {"name": "status:done"}]),
                ok([{"name": "status:done"}]),
            ],
        })
        out = apply_status(
            "github", gh_cfg(),
            {"durable": GH_NODE, "display": "#42"},
            _gh_parent(state="open", labels=["status:in_review"]),
            ex, target_slot="done")
        self.assertNotIsInstance(out, TrackerError)
        self.assertEqual(out["completed_steps"], ["state", "labels"])
        self.assertIsNone(out["degraded"])
        self.assertEqual(
            [c.op for c in ex.calls],
            ["status-set", "status-label-rm", "status-label-add",
             "status-label-readback", "status-label-rm",
             "status-label-readback"])

    def test_unrepaired_remove_failure_does_not_advance_last_synced(self) -> None:
        """A second invocation safely repairs the partial namespace.

        The first bounded cleanup still leaves two labels, returns landed
        partial evidence, and persists no durable success. The retry proves
        the requested terminal state through native state + merge policy,
        replays the idempotent write, and converges without manual cleanup.
        """
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "done",
                            "completion_review_status": "unknown"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": "OLD", "linkState": "linked"},
            )
            cfg_path = flow / "config.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg["review"] = {"backend": "none"}
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            ambiguous = ok([{"name": "status:in_review"},
                            {"name": "status:done"}])
            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="open", labels=["status:in_review"])),
                "merge-evidence": ok([{"state": "MERGED"}]),
                "status-set": ok({"node_id": GH_NODE, "number": 42,
                                  "state": "closed"}),
                "status-label-rm": [
                    TrackerError(ErrorClass.TRANSPORT, "remove boom"),
                    TrackerError(ErrorClass.TRANSPORT, "repair boom"),
                ],
                "status-label-add": ok([{"name": "status:done"}]),
                "status-label-readback": [ambiguous, ambiguous],
            })
            out = S.status(flow, "fn-1-demo", to="done", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertEqual(out.subtype, "status_labels_partial")
            self.assertTrue(out.auto_retryable)
            self.assertEqual((out.details or {}).get("completed_steps"),
                             ["state", "label-add"])
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["lastSyncedAt"], "OLD")
            self.assertEqual(_receipts(flow), [])

            retry_ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="closed",
                    labels=["status:in_review", "status:done"],
                    state_reason="completed")),
                "merge-evidence": ok([{"state": "MERGED"}]),
                "status-label-rm": empty_ok(),
                "status-label-add": ok([{"name": "status:done"}]),
                "status-label-readback": ok([{"name": "status:done"}]),
            })
            retry = S.status(
                flow, "fn-1-demo", to="done", execute=retry_ex)
            self.assertNotIsInstance(retry, TrackerError, retry)
            self.assertEqual(retry["kind"], "applied")
            self.assertEqual(retry["applied"], "done")
            repaired = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertNotEqual(repaired["lastSyncedAt"], "OLD")
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["status"], "updated")
            self.assertEqual(
                [c.op for c in retry_ex.calls],
                ["status-parent-read", "merge-evidence", "status-label-rm",
                 "status-label-add", "status-label-readback"])

    def test_retry_label_repair_preserves_duplicate_close_reason(self) -> None:
        """A safe noop retry repairs labels only. It must not replay PATCH
        state and overwrite GitHub's authoritative duplicate close reason."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "done",
                            "completion_review_status": "unknown"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": "OLD", "linkState": "linked"},
            )
            cfg_path = flow / "config.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg["review"] = {"backend": "none"}
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="closed",
                    labels=["status:in_review", "status:done"],
                    state_reason="duplicate")),
                "merge-evidence": ok([{"state": "MERGED"}]),
                "status-label-rm": empty_ok(),
                "status-label-add": ok([{"name": "status:done"}]),
                "status-label-readback": ok([{"name": "status:done"}]),
            })
            out = S.status(flow, "fn-1-demo", to="done", execute=ex)
            self.assertNotIsInstance(out, TrackerError, out)
            self.assertEqual(out["kind"], "applied")
            self.assertEqual(out["write"]["repair"], "labels-only")
            self.assertFalse(any(c.op == "status-set" for c in ex.calls))
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertNotEqual(saved["lastSyncedAt"], "OLD")
            self.assertEqual(_receipts(flow)[0]["status"], "updated")

    def test_missing_target_partial_is_repaired_on_next_invocation(self) -> None:
        """Bounded cleanup can leave no target label. The next invocation
        detects the missing label despite successful native normalization and
        converges through the same policy-gated label-only repair."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "done",
                            "completion_review_status": "unknown"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": "OLD", "linkState": "linked"},
            )
            cfg_path = flow / "config.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg["review"] = {"backend": "none"}
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            first = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="open", labels=["status:in_review"])),
                "merge-evidence": ok([{"state": "MERGED"}]),
                "status-set": ok({"node_id": GH_NODE, "number": 42,
                                  "state": "closed"}),
                "status-label-rm": [
                    TrackerError(ErrorClass.TRANSPORT, "remove boom"),
                    empty_ok(),
                ],
                "status-label-add": ok([{"name": "status:done"}]),
                "status-label-readback": [
                    ok([{"name": "status:in_review"},
                        {"name": "status:done"}]),
                    ok([]),
                ],
            })
            partial = S.status(
                flow, "fn-1-demo", to="done", execute=first)
            self.assertIsInstance(partial, TrackerError)
            self.assertEqual(partial.subtype, "status_labels_partial")
            self.assertTrue(partial.auto_retryable)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8"))["tracker"][
                    "lastSyncedAt"],
                "OLD")
            self.assertEqual(_receipts(flow), [])

            second = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="closed", labels=[],
                    state_reason="completed")),
                "merge-evidence": ok([{"state": "MERGED"}]),
                "status-label-add": ok([{"name": "status:done"}]),
                "status-label-readback": ok([{"name": "status:done"}]),
            })
            repaired = S.status(
                flow, "fn-1-demo", to="done", execute=second)
            self.assertNotIsInstance(repaired, TrackerError, repaired)
            self.assertEqual(repaired["kind"], "applied")
            self.assertEqual(repaired["write"]["repair"], "labels-only")
            self.assertFalse(any(c.op == "status-set" for c in second.calls))
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertNotEqual(saved["lastSyncedAt"], "OLD")
            self.assertEqual(_receipts(flow)[0]["status"], "updated")

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

    def test_native_open_wins_over_stale_terminal_label(self) -> None:
        for provider, parent in (
            ("github", _gh_parent(state="open", labels=["status:done"])),
            ("github", _gh_parent(state="open", labels=["status:wontfix"])),
            ("gitlab", {"state": "opened", "labels": ["status:done"]}),
            ("gitlab", {"state": "opened", "labels": ["status:deferred"]}),
        ):
            with self.subTest(provider=provider, parent=parent):
                self.assertEqual(
                    tracker_norm_from_parent(provider, parent, {}),
                    "in_progress")

    def test_unrecognized_extra_status_labels_are_ignored(self) -> None:
        out = tracker_norm_from_parent(
            "github",
            _gh_parent(state="open",
                       labels=["status:custom-bucket", "status:in_review"]),
            {})
        self.assertEqual(out, "in_review")

    def test_ambiguous_labels_repaired_when_native_flow_request_agree(
            self) -> None:
        """Native state, derived flow, and requested target jointly prove a
        safe repair target, so ambiguity is repaired instead of silent noop."""
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
                "merge-evidence": ok([]),
                "status-set": ok({"node_id": GH_NODE, "number": 42,
                                  "state": "open"}),
                "status-label-rm": empty_ok(),
                "status-label-add": ok([{"name": "status:in-progress"}]),
                "status-label-readback": ok([
                    {"name": "status:in-progress"}]),
            })
            out = S.status(flow, "fn-1-demo", to="in_progress", execute=ex)
            self.assertNotIsInstance(out, TrackerError, out)
            self.assertEqual(out["kind"], "applied")
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertNotEqual(saved["lastSyncedAt"], "OLD")
            self.assertEqual(_receipts(flow)[0]["status"], "updated")

    def test_ambiguous_repair_refused_when_merge_gate_is_not_clean(self) -> None:
        """Native/request agreement alone is insufficient: failed merge
        evidence keeps the ordinary conflict surface and emits no mutation."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "done",
                            "completion_review_status": "unknown"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": "OLD", "linkState": "linked"},
            )
            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="closed",
                    labels=["status:in_review", "status:done"],
                    state_reason="completed")),
                "merge-evidence": TrackerError(
                    ErrorClass.TRANSPORT, "probe unavailable"),
            })
            out = S.status(flow, "fn-1-demo", to="done", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertEqual(out.subtype, "ambiguous-status-labels")
            self.assertFalse(any(c.op == "status-set" for c in ex.calls))
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["lastSyncedAt"], "OLD")
            self.assertEqual(_receipts(flow), [])

    def test_ambiguous_cancelled_state_is_never_auto_repaired(self) -> None:
        """The retry path preserves cancelled-family human confirmation."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "done"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": "OLD", "linkState": "linked"},
            )
            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="closed",
                    labels=["status:wontfix", "status:done"],
                    state_reason="not_planned")),
                "merge-evidence": ok([]),
            })
            out = S.status(
                flow, "fn-1-demo", to="cancelled",
                reason="not_planned", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertEqual(out.subtype, "ambiguous-status-labels")
            self.assertFalse(any(c.op == "status-set" for c in ex.calls))
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["lastSyncedAt"], "OLD")
            self.assertEqual(_receipts(flow), [])


class LoadTasksMergesRuntimeState(unittest.TestCase):
    """Live smoke 2026-07-28: since the fn-111 storage split the task
    DEFINITION (.flow/tasks/<id>.json) keeps its scaffold status while the
    live status (claimed/in_progress/done) lives in the runtime store at
    <state-dir>/tasks/<id>.state.json. _load_tasks must overlay it, or every
    started spec normalizes as todo and the tracker never advances."""

    def _flow_with_task(self, tmp: Path) -> Path:
        flow = tmp / ".flow"
        (flow / "tasks").mkdir(parents=True)
        (flow / "tasks" / "fn-1.1.json").write_text(
            json.dumps({"id": "fn-1.1", "status": "todo", "spec": "fn-1"}),
            encoding="utf-8")
        return flow

    def test_runtime_state_overlays_definition_status(self) -> None:
        import os
        from flowctl_tracker.status import verb as V
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            flow = self._flow_with_task(tmp_path)
            state = tmp_path / "state" / "tasks"
            state.mkdir(parents=True)
            (state / "fn-1.1.state.json").write_text(
                json.dumps({"status": "in_progress",
                            "assignee": "smoke", "claimed_at": "t"}),
                encoding="utf-8")
            old = os.environ.get("FLOW_STATE_DIR")
            os.environ["FLOW_STATE_DIR"] = str(tmp_path / "state")
            try:
                tasks = V._load_tasks(flow, "fn-1")
            finally:
                if old is None:
                    os.environ.pop("FLOW_STATE_DIR", None)
                else:
                    os.environ["FLOW_STATE_DIR"] = old
            self.assertEqual(tasks, [{"id": "fn-1.1", "status": "in_progress"}])

    def test_definition_status_still_read_without_runtime_state(self) -> None:
        import os
        from flowctl_tracker.status import verb as V
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            flow = self._flow_with_task(tmp_path)
            old = os.environ.get("FLOW_STATE_DIR")
            os.environ["FLOW_STATE_DIR"] = str(tmp_path / "state-missing")
            try:
                tasks = V._load_tasks(flow, "fn-1")
            finally:
                if old is None:
                    os.environ.pop("FLOW_STATE_DIR", None)
                else:
                    os.environ["FLOW_STATE_DIR"] = old
            self.assertEqual(tasks, [{"id": "fn-1.1", "status": "todo"}])


class StateDirAbsoluteFromSubdir(unittest.TestCase):
    """PR #246 wave-14 P1: --path-format modifies only options AFTER it, so
    a trailing --path-format=absolute returned a cwd-relative ".git". The
    resolved state dir must be absolute regardless of the caller's cwd."""

    def test_state_dir_is_absolute(self) -> None:
        import os
        import subprocess as sp
        from flowctl_tracker.status import verb as V
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / ".flow").mkdir(parents=True)
            sp.run(["git", "init", "-q", str(repo)], check=True)
            old = os.environ.pop("FLOW_STATE_DIR", None)
            try:
                out = V._state_dir(repo / ".flow")
            finally:
                if old is not None:
                    os.environ["FLOW_STATE_DIR"] = old
            self.assertTrue(out.is_absolute(), out)
            self.assertEqual(out, (repo / ".git" / "flow-state").resolve())


class AliasedStateIdReads(unittest.TestCase):
    """PR #246 wave-14 P2: non-injective slot->id maps (sanctioned aliasing
    via --select) must read deterministically. The reverse map picks the
    EARLIEST aliased slot in the canonical progression order, never dict
    key order, so JSON serialization order cannot flip the normalized slot
    and drive a different merge-gate decision."""

    def _linear_dest(self, state_ids: dict) -> dict:
        return {"stateIds": state_ids}

    def test_linear_alias_reads_earliest_slot_both_orders(self) -> None:
        parent = {"state": {"id": "s-shared", "name": "In Progress",
                            "type": "started"}}
        order_a = {"todo": "s-todo", "in_progress": "s-shared",
                   "in_review": "s-shared", "done": "s-done"}
        order_b = {"done": "s-done", "in_review": "s-shared",
                   "in_progress": "s-shared", "todo": "s-todo"}
        for ids in (order_a, order_b):
            out = tracker_norm_from_parent(
                "linear", parent, self._linear_dest(ids))
            self.assertEqual(out, "in_progress", msg=repr(ids))

    def test_linear_single_id_map_unchanged(self) -> None:
        parent = {"state": {"id": "s-rev", "name": "In Review",
                            "type": "started"}}
        ids = {"todo": "s-todo", "in_progress": "s-ip",
               "in_review": "s-rev", "done": "s-done"}
        out = tracker_norm_from_parent("linear", parent,
                                       self._linear_dest(ids))
        self.assertEqual(out, "in_review")

    def test_linear_done_cancelled_alias_reads_done(self) -> None:
        # done precedes cancelled in the canonical progression order.
        parent = {"state": {"id": "s-term", "name": "Closed",
                            "type": "completed"}}
        for ids in (
            {"done": "s-term", "cancelled": "s-term"},
            {"cancelled": "s-term", "done": "s-term"},
        ):
            out = tracker_norm_from_parent(
                "linear", parent, self._linear_dest(ids))
            self.assertEqual(out, "done", msg=repr(ids))

    def test_jira_alias_reads_earliest_slot_both_orders(self) -> None:
        parent = {"fields": {"status": {
            "id": "71", "name": "Working",
            "statusCategory": {"key": "indeterminate"},
        }}}
        order_a = {"todo": "11", "in_progress": "71",
                   "in_review": "71", "done": "31"}
        order_b = {"done": "31", "in_review": "71",
                   "in_progress": "71", "todo": "11"}
        for ids in (order_a, order_b):
            out = tracker_norm_from_parent("jira", parent,
                                           {"statusIds": ids})
            self.assertEqual(out, "in_progress", msg=repr(ids))

    def test_jira_single_id_map_unchanged(self) -> None:
        parent = {"fields": {"status": {
            "id": "41", "name": "In Review",
            "statusCategory": {"key": "indeterminate"},
        }}}
        ids = {"todo": "11", "in_progress": "21", "in_review": "41",
               "done": "31"}
        out = tracker_norm_from_parent("jira", parent, {"statusIds": ids})
        self.assertEqual(out, "in_review")

    def test_write_direction_alias_still_sanctioned(self) -> None:
        # validate_select keeps permitting an id outside the slot's natural
        # pool (the alias feature); the read-side fix must not touch it.
        from flowctl_tracker.states import validate_select
        live = {"s-ip": {"id": "s-ip", "name": "In Progress"}}
        pools = {"in_review": []}
        self.assertIsNone(validate_select("in_review", "s-ip", pools, live))


class StatusClaimSerialization(unittest.TestCase):
    """PR #246 review: relinks must be excluded across the status verb's
    WHOLE window (initial reads -> provider mutation -> locked persistence),
    not merely detected afterwards by _persist_applied_state. The verb now
    takes a per-spec create-first claim (status-<spec-id>.json, syncbody's
    pattern) before any spec read or tracker I/O; `sync set-tracker-id`
    honors it, and a concurrent status invocation for the same spec backs
    off with CONFLICT/status_in_flight instead of double-mutating."""

    def test_concurrent_status_loser_conflicts_one_provider_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(
                flow, gh_cfg(),
                spec_extra={"status": "done",
                            "completion_review_status": "unknown"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": None, "linkState": "linked"},
            )
            # Ungated completion review so merged -> done -> apply.
            cfg_path = flow / "config.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg["review"] = {"backend": "none"}
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

            rec_path = flow / "create-first" / "status-fn-1-demo.json"
            inner: dict = {}

            def racing_parent_read(req):
                # The claim must be durable BEFORE the parent read...
                claim = json.loads(rec_path.read_text(encoding="utf-8"))
                self.assertEqual(claim.get("status"), "pending")
                self.assertEqual(claim.get("op"), "status")
                self.assertEqual(claim.get("specId"), "fn-1-demo")
                # ...so a second invocation racing in mid-transaction refuses
                # with structured CONFLICT before ANY tracker I/O (the empty
                # executor would AssertionError on any wire call) instead of
                # issuing a second provider mutation.
                inner["out"] = S.status(flow, "fn-1-demo", to="done",
                                        execute=fake_execute({}))
                return ok(_gh_parent(state="open",
                                     labels=["status:in_review"]))

            ex = fake_execute({
                "status-parent-read": racing_parent_read,
                "merge-evidence": ok([{"state": "MERGED", "number": 1}]),
                "status-set": ok({"node_id": GH_NODE, "number": 42,
                                  "state": "closed",
                                  "state_reason": "completed"}),
                "status-label-rm": empty_ok(),
                "status-label-add": ok([{"name": "status:done"}]),
                "status-label-readback": ok([{"name": "status:done"}]),
            })
            out = S.status(flow, "fn-1-demo", to="done", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["kind"], "applied")

            raced = inner["out"]
            self.assertIsInstance(raced, TrackerError)
            self.assertIs(raced.cls, ErrorClass.CONFLICT)
            self.assertEqual(raced.subtype, "status_in_flight")
            self.assertTrue(raced.auto_retryable)
            self.assertEqual((raced.details or {}).get("specId"), "fn-1-demo")
            # Exactly ONE provider mutation landed across both invocations.
            self.assertEqual(
                sum(1 for c in ex.calls if c.op == "status-set"), 1)
            self.assertFalse(rec_path.exists(),
                             "claim released after the transaction finished")

    def test_stale_dead_pid_claim_is_reclaimed(self) -> None:
        import os
        import socket
        import time
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(
                flow, gh_cfg(),
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": "OLD", "linkState": "linked"},
                tasks=[{"status": "in_progress"}],
            )
            rec_path = flow / "create-first" / "status-fn-1-demo.json"
            rec_path.parent.mkdir(parents=True)
            # pid 0 is never alive; claimedAt is past the stale window.
            rec_path.write_text(json.dumps({
                "specId": "fn-1-demo", "status": "pending", "op": "status",
                "to": "in_progress", "pid": 0,
                "host": socket.gethostname(),
                "claimedAt": time.time() - 999,
                "transport": "github"}), encoding="utf-8")
            self.assertNotEqual(os.getpid(), 0)
            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="open", labels=["status:in_progress"])),
                "merge-evidence": ok([]),
            })
            out = S.status(flow, "fn-1-demo", to="in_progress", execute=ex)
            self.assertNotIsInstance(out, TrackerError,
                                     "a crashed run's leftover claim must "
                                     "not wedge the spec")
            self.assertEqual(out["kind"], "noop")
            self.assertFalse(rec_path.exists(),
                             "reclaimed claim released after the run")


class AliasedStateIdWriteNoop(unittest.TestCase):
    """Aliased in_progress/in_review + open PR: the read side resolves the
    shared id to in_progress (earliest slot), the gate requests in_review,
    and the target state id equals the one already on the issue. Writing it
    would report "applied" and advance lastSyncedAt on EVERY sync - the
    repeat loop. The writer must detect the identical native id and no-op."""

    ALIASED = {"todo": "s-todo", "in_progress": "s-shared",
               "in_review": "s-shared", "done": "s-done"}

    def _flow(self, tmp: str) -> Path:
        flow = Path(tmp) / ".flow"
        _write_flow(
            flow, ln_cfg(state_ids=dict(self.ALIASED)),
            tracker={"id": LN_UUID, "identifier": "WOR-1", "url": "u",
                     "lastSyncedAt": "OLD", "linkState": "linked"},
            tasks=[{"status": "in_progress"}],
        )
        return flow

    def _responses(self, current_state: dict) -> dict:
        return {
            "status-parent-read": ok({"data": {
                "issue": {"id": LN_UUID, "identifier": "WOR-1",
                          "title": "t", "description": "", "url": "u",
                          "updatedAt": "t", "labels": {"nodes": []},
                          "assignee": None},
            }}),
            "status-state-read": ok({"data": {
                "issue": {"id": LN_UUID, "state": current_state},
            }}),
            "merge-evidence": ok([{"state": "OPEN"}]),
        }

    def test_identical_native_id_noops_and_never_advances(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = self._flow(tmp)
            path = flow / "specs" / "fn-1-demo.json"
            state = {"id": "s-shared", "name": "In Progress",
                     "type": "started"}
            # Two consecutive syncs: the repeat loop the finding describes
            # would mutate + advance lastSyncedAt on each. Both must no-op.
            for attempt in (1, 2):
                ex = fake_execute(self._responses(state))
                out = S.status(flow, "fn-1-demo", to="in_review", execute=ex)
                self.assertNotIsInstance(out, TrackerError, msg=repr(out))
                self.assertEqual(out["kind"], "noop",
                                 msg=f"sync {attempt}: {out!r}")
                self.assertEqual(out["lastSyncedAt"], "OLD")
                self.assertFalse(
                    any(c.op == "status-set" for c in ex.calls),
                    msg=f"sync {attempt} issued a provider mutation")
                saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
                self.assertEqual(saved["lastSyncedAt"], "OLD",
                                 msg=f"sync {attempt} advanced lastSyncedAt")

    def test_different_native_id_still_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = self._flow(tmp)
            path = flow / "specs" / "fn-1-demo.json"
            variables = []

            def capture(req):
                variables.append(json.loads(req.body).get("variables"))
                return ok({"data": {"issueUpdate": {
                    "success": True, "issue": {"id": LN_UUID}}}})

            responses = self._responses(
                {"id": "s-todo", "name": "Todo", "type": "unstarted"})
            responses["status-set"] = capture
            ex = fake_execute(responses)
            out = S.status(flow, "fn-1-demo", to="in_review", execute=ex)
            self.assertNotIsInstance(out, TrackerError, msg=repr(out))
            self.assertEqual(out["kind"], "applied")
            self.assertEqual(variables[0]["stateId"], "s-shared")
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertNotEqual(saved["lastSyncedAt"], "OLD")

    def test_jira_parity_identical_status_id_noops(self) -> None:
        """Pin the Jira already-current check this fix mirrors: aliased
        statusIds + issue already on the shared id -> noop, no transition
        lookup, no POST, no lastSyncedAt advance."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            path = _write_flow(
                flow, jr_cfg(status_ids={"todo": "1", "in_progress": "2",
                                         "in_review": "2", "done": "4"}),
                tracker={"id": JR_ID, "identifier": "SCRUM-1", "url": "u",
                         "lastSyncedAt": "OLD", "linkState": "linked"},
                tasks=[{"status": "in_progress"}],
            )
            ex = fake_execute({
                "status-parent-read": ok({
                    "id": JR_ID, "key": "SCRUM-1",
                    "fields": {"status": {
                        "id": "2", "name": "In Progress",
                        "statusCategory": {"key": "indeterminate"}}},
                }),
                "merge-evidence": ok([{"state": "OPEN"}]),
                "status-current": ok({
                    "fields": {"status": {"id": "2"}},
                }),
            })
            out = S.status(
                flow, "fn-1-demo", to="in_review",
                event="makePr", execute=ex)
            self.assertNotIsInstance(out, TrackerError, msg=repr(out))
            self.assertEqual(out["kind"], "noop")
            self.assertFalse(any(c.op in {"status-set", "status-transitions"}
                                 for c in ex.calls))
            saved = json.loads(path.read_text(encoding="utf-8"))["tracker"]
            self.assertEqual(saved["lastSyncedAt"], "OLD")
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["status"], "noop")
            self.assertEqual(receipts[0]["event"], "makePr")


class EffectiveReviewBackendPrecedence(unittest.TestCase):
    """PR #246 wave 17 P1: the projection helper honors resolve_review_spec's
    precedence (spec default_review > FLOW_REVIEW_BACKEND > config)."""

    def setUp(self) -> None:
        self._env = os.environ.pop("FLOW_REVIEW_BACKEND", None)

    def tearDown(self) -> None:
        if self._env is not None:
            os.environ["FLOW_REVIEW_BACKEND"] = self._env
        else:
            os.environ.pop("FLOW_REVIEW_BACKEND", None)

    def test_spec_default_review_overrides_disabled_config(self) -> None:
        cfg = {"review": {"backend": "none"}}
        self.assertTrue(V._completion_review_configured(
            cfg, {"default_review": "codex"}))

    def test_spec_default_review_none_overrides_configured_backend(self) -> None:
        cfg = {"review": {"backend": "codex"}}
        self.assertFalse(V._completion_review_configured(
            cfg, {"default_review": "none"}))

    def test_env_overrides_config_when_spec_silent(self) -> None:
        cfg = {"review": {"backend": "none"}}
        os.environ["FLOW_REVIEW_BACKEND"] = "codex:gpt-5.6-sol:high"
        self.assertTrue(V._completion_review_configured(cfg, {}))

    def test_config_fallback_unchanged(self) -> None:
        self.assertTrue(V._completion_review_configured(
            {"review": {"backend": "codex"}}, {}))
        self.assertFalse(V._completion_review_configured(
            {"review": {"backend": "off"}}, {}))
        self.assertFalse(V._completion_review_configured({}, {}))


class TerminalFoldConverges(unittest.TestCase):
    """PR #246 wave 17 P2: a repeated tracker-terminal fold is a noop - no
    rewrite, no lastSyncedAt advance."""

    def test_second_fold_is_noop_and_synced_not_advanced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            cfg = gh_cfg()
            cfg["review"] = {"backend": "codex"}  # completion gated
            path = _write_flow(
                flow, cfg,
                spec_extra={"status": "done",
                            "completion_review_status": "unknown"},
                tracker={"id": GH_NODE, "identifier": "#42", "url": "u",
                         "lastSyncedAt": "PRIOR-FOLD",
                         "linkState": "linked"},
            )
            # Tracker terminal (closed completed), flow derives in_review
            # (done + no ship + gated) -> decide says apply_local; the raw
            # status is ALREADY done, so the verb must converge to noop.
            ex = fake_execute({
                "status-parent-read": ok(_gh_parent(
                    state="closed", labels=["status:done"],
                    state_reason="completed")),
                "merge-evidence": ok([{"state": "MERGED", "number": 1}]),
            })
            out = S.status(
                flow, "fn-1-demo", to="done",
                event="work.done", execute=ex)
            self.assertNotIsInstance(out, TrackerError)
            self.assertEqual(out["kind"], "noop")
            self.assertEqual(out["reason"], "already_folded")
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "done")
            self.assertEqual(saved["tracker"]["lastSyncedAt"], "PRIOR-FOLD")
            receipts = _receipts(flow)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["status"], "noop")
            self.assertEqual(receipts[0]["event"], "work.done")
