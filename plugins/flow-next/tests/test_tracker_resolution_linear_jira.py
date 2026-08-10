"""Linear + Jira resolution, the normalized vocabulary, `--select`, and the
`flowctl tracker resolve` verb (fn-139.6).

Fake transport = the injected executor seam; response shapes mirror the live
smoke measurements (Linear started->2 states, Jira 3 status categories).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import resolve_verb as RV  # noqa: E402
from flowctl_tracker import states as ST  # noqa: E402
from flowctl_tracker.providers import jira as JR  # noqa: E402
from flowctl_tracker.providers import linear as LN  # noqa: E402
from flowctl_tracker.types import ErrorClass, Response, TrackerError  # noqa: E402


def ok(body) -> Response:
    return Response(200, {}, json.dumps(body).encode(), 0.01)


def fake_execute(responses: dict):
    calls = []

    def execute(request):
        calls.append(request)
        out = responses[request.op]
        if isinstance(out, list):  # sequence: one per call of this op
            out = out.pop(0)
        return out(request) if callable(out) else out

    execute.calls = calls
    return execute


def linear_cfg() -> dict:
    return {"tracker": {"type": "linear",
                        "perTracker": {"teamId": "team-uuid-1"}}}


def jira_cfg(**per_extra) -> dict:
    per = {"baseUrl": "https://guilty.atlassian.net", "projectKey": "SCRUM"}
    per.update(per_extra)
    return {"tracker": {"type": "jira", "perTracker": per}}


def linear_states(states):
    return ok({"data": {"team": {"states": {
        "nodes": states, "pageInfo": {"hasNextPage": False, "endCursor": None}}}}})


#: Two `started` states - the measured ambiguous workspace shape.
FIVE_STATES = [
    {"id": "s-backlog", "name": "Backlog", "type": "backlog"},
    {"id": "s-todo", "name": "Todo", "type": "unstarted"},
    {"id": "s-prog", "name": "In Progress", "type": "started"},
    {"id": "s-review", "name": "In Review", "type": "started"},
    {"id": "s-done", "name": "Done", "type": "completed"},
    {"id": "s-cancel", "name": "Canceled", "type": "canceled"},
]

#: One state per type - resolves without any human tiebreak.
SIMPLE_STATES = [
    {"id": "s-backlog", "name": "Backlog", "type": "backlog"},
    {"id": "s-todo", "name": "Todo", "type": "unstarted"},
    {"id": "s-prog", "name": "In Progress", "type": "started"},
    {"id": "s-done", "name": "Done", "type": "completed"},
    {"id": "s-cancel", "name": "Canceled", "type": "canceled"},
]

JIRA_STATUSES = ok([{"id": "10001", "name": "Task", "statuses": [
    {"id": "1", "name": "To Do", "statusCategory": {"key": "new"}},
    {"id": "2", "name": "In Progress", "statusCategory": {"key": "indeterminate"}},
    {"id": "3", "name": "Done", "statusCategory": {"key": "done"}},
]}])


class Vocabulary(unittest.TestCase):
    def test_required_and_optional_slots(self) -> None:
        self.assertEqual(ST.REQUIRED_SLOTS, ("todo", "in_progress", "done"))
        self.assertEqual(ST.OPTIONAL_SLOTS, ("backlog", "in_review", "cancelled"))


class LinearStates(unittest.TestCase):
    def test_single_state_per_type_resolves_without_tiebreak(self) -> None:
        ex = fake_execute({"resolve-states": linear_states(SIMPLE_STATES)})
        out = LN.resolve_state_ids(linear_cfg(), ex)
        self.assertIsNone(out.conflict)
        self.assertEqual(out.mapping, {
            "backlog": "s-backlog", "todo": "s-todo", "in_progress": "s-prog",
            "done": "s-done", "cancelled": "s-cancel"})
        self.assertNotIn("in_review", out.mapping,
                         "the single started state is in_progress - reusing it "
                         "for in_review would be a silent alias")
        self.assertTrue(out.complete)

    def test_names_do_not_bypass_the_type_ambiguity_contract(self) -> None:
        """The mapping algorithm is TYPE-only: two started states are ambiguous
        even when named exactly In Progress / In Review - the tiebreak is a
        human decision, not a string match."""
        ex = fake_execute({"resolve-states": linear_states(FIVE_STATES)})
        out = LN.resolve_state_ids(linear_cfg(), ex)
        self.assertIsNotNone(out.conflict)
        self.assertEqual(out.conflict["normalized"], "in_progress")
        self.assertEqual({c["id"] for c in out.conflict["candidates"]},
                         {"s-prog", "s-review"})

    def test_two_generic_started_states_are_ambiguous(self) -> None:
        states = [
            {"id": "s-todo", "name": "Todo", "type": "unstarted"},
            {"id": "s-a", "name": "Doing", "type": "started"},
            {"id": "s-b", "name": "Verifying", "type": "started"},
            {"id": "s-done", "name": "Done", "type": "completed"},
        ]
        ex = fake_execute({"resolve-states": linear_states(states)})
        out = LN.resolve_state_ids(linear_cfg(), ex)
        self.assertIsNotNone(out.conflict)
        self.assertEqual(out.conflict["normalized"], "in_progress")
        self.assertEqual({c["id"] for c in out.conflict["candidates"]}, {"s-a", "s-b"})

    def test_selecting_in_progress_does_not_infer_in_review(self) -> None:
        states = [
            {"id": "s-todo", "name": "Todo", "type": "unstarted"},
            {"id": "s-a", "name": "Doing", "type": "started"},
            {"id": "s-b", "name": "Verifying", "type": "started"},
            {"id": "s-done", "name": "Done", "type": "completed"},
        ]
        cfg = linear_cfg()
        cfg["tracker"]["resolved"] = {"destination": {"stateIds": {"in_progress": "s-a"}}}
        ex = fake_execute({"resolve-states": linear_states(states)})
        out = LN.resolve_state_ids(cfg, ex)
        self.assertIsNone(out.conflict, "required slots all resolvable now")
        self.assertEqual(out.mapping["in_progress"], "s-a", "human tiebreak kept")
        self.assertNotIn("in_review", out.mapping,
                         "selecting in_progress must NOT infer in_review - it "
                         "stays unfilled until its own --select")

    def test_dead_prior_selection_is_dropped_with_warning(self) -> None:
        cfg = linear_cfg()
        cfg["tracker"]["resolved"] = {"destination": {"stateIds": {"todo": "gone-id"}}}
        ex = fake_execute({"resolve-states": linear_states(FIVE_STATES)})
        out = LN.resolve_state_ids(cfg, ex)
        self.assertEqual(out.mapping["todo"], "s-todo")
        self.assertTrue(any("gone-id" in w for w in out.warnings))

    def test_pagination_is_fully_drained(self) -> None:
        page1 = ok({"data": {"team": {"states": {
            "nodes": SIMPLE_STATES[:3],
            "pageInfo": {"hasNextPage": True, "endCursor": "c1"}}}}})
        page2 = ok({"data": {"team": {"states": {
            "nodes": SIMPLE_STATES[3:],
            "pageInfo": {"hasNextPage": False, "endCursor": None}}}}})
        ex = fake_execute({"resolve-states": [page1, page2]})
        out = LN.resolve_state_ids(linear_cfg(), ex)
        self.assertTrue(out.complete, "second page carried Done - must be drained")
        self.assertEqual(len(ex.calls), 2)
        body2 = json.loads(ex.calls[1].body)
        self.assertEqual(body2["variables"]["after"], "c1")


class LinearDestination(unittest.TestCase):
    def test_labels_are_lowercased_and_drained(self) -> None:
        team = ok({"data": {"team": {"id": "team-uuid-1", "key": "FLOW"}}})
        lbl1 = ok({"data": {"team": {"labels": {
            "nodes": [{"id": "l1", "name": "Bug"}],
            "pageInfo": {"hasNextPage": True, "endCursor": "c1"}}}}})
        lbl2 = ok({"data": {"team": {"labels": {
            "nodes": [{"id": "l2", "name": "Feature"}],
            "pageInfo": {"hasNextPage": False, "endCursor": None}}}}})
        ex = fake_execute({"resolve-destination": team, "resolve-labels": [lbl1, lbl2]})
        out = LN.resolve_destination(linear_cfg(), ex)
        self.assertEqual(out, {"teamId": "team-uuid-1", "teamKey": "FLOW",
                               "labelIds": {"bug": "l1", "feature": "l2"}})

    def test_missing_team_id_is_unresolved(self) -> None:
        out = LN.resolve_destination({"tracker": {"perTracker": {}}}, fake_execute({}))
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.UNRESOLVED)

    def test_capabilities_are_static(self) -> None:
        self.assertEqual(LN.resolve_capabilities({}, None), {
            "attachments": True, "blockedBy": True,
            "subIssues": False, "deleteIssue": True})


class JiraDestination(unittest.TestCase):
    def setUp(self) -> None:
        # Isolate from a developer/CI machine that legitimately exports
        # JIRA_BASE_URL - production honors the override; fixtures must not.
        import os
        from unittest import mock
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("JIRA_BASE_URL", None)

    PROJECT = {"id": 10000, "key": "SCRUM", "style": "next-gen", "simplified": True,
               "issueTypes": [
                   {"id": "10001", "name": "Task", "subtask": False},
                   {"id": "10002", "name": "Subtask", "subtask": True},
                   {"id": "10003", "name": "Epic", "subtask": False},
               ]}

    def test_resolves_every_architecture_table_field(self) -> None:
        ex = fake_execute({"resolve-destination": ok(self.PROJECT)})
        out = JR.resolve_destination(jira_cfg(), ex)
        self.assertEqual(out, {"baseUrl": "https://guilty.atlassian.net",
                               "projectKey": "SCRUM", "projectId": "10000",
                               "issueTypeId": "10001", "apiVersion": 2,
                               "style": "next-gen"})

    def test_classic_style_detected(self) -> None:
        project = dict(self.PROJECT)
        project.pop("style"); project["simplified"] = False
        ex = fake_execute({"resolve-destination": ok(project)})
        out = JR.resolve_destination(jira_cfg(), ex)
        self.assertEqual(out["style"], "classic")

    def test_issue_type_precedence_configured_wins(self) -> None:
        ex = fake_execute({"resolve-destination": ok(self.PROJECT)})
        out = JR.resolve_destination(jira_cfg(issueType="Epic"), ex)
        self.assertEqual(out["issueTypeId"], "10003")

    def test_unresolvable_configured_issue_type_errors_not_falls_back(self) -> None:
        ex = fake_execute({"resolve-destination": ok(self.PROJECT)})
        out = JR.resolve_destination(jira_cfg(issueType="Story"), ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.INVALID_INPUT)

    def test_no_task_type_falls_back_to_first_non_subtask(self) -> None:
        project = dict(self.PROJECT)
        project["issueTypes"] = [
            {"id": "10002", "name": "Subtask", "subtask": True},
            {"id": "10005", "name": "Story", "subtask": False},
        ]
        ex = fake_execute({"resolve-destination": ok(project)})
        out = JR.resolve_destination(jira_cfg(), ex)
        self.assertEqual(out["issueTypeId"], "10005")

    def test_env_base_url_overrides_persisted(self) -> None:
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {"JIRA_BASE_URL": "https://dc.example.com/"}):
            self.assertEqual(JR.base_url(jira_cfg()), "https://dc.example.com")

    def test_capabilities_are_static(self) -> None:
        self.assertEqual(JR.resolve_capabilities({}, None), {
            "attachments": True, "blockedBy": True,
            "subIssues": False, "deleteIssue": True})


class JiraStatuses(unittest.TestCase):
    def setUp(self) -> None:
        import os
        from unittest import mock
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("JIRA_BASE_URL", None)

    def _cfg(self, status_map=None) -> dict:
        cfg = jira_cfg(**({"statusMap": status_map} if status_map is not None else {}))
        cfg["tracker"]["resolved"] = {"destination": {"issueTypeId": "10001"}}
        return cfg

    def test_three_status_next_gen_resolves_all_required(self) -> None:
        ex = fake_execute({"resolve-statuses": JIRA_STATUSES})
        out = JR.resolve_status_ids(self._cfg(), ex)
        self.assertTrue(out.complete)
        self.assertEqual(out.mapping, {"todo": "1", "in_progress": "2", "done": "3"})

    def test_only_status_ids_ever_reach_the_mapping(self) -> None:
        """No transition id is written to the cache - ids come from the project
        statuses endpoint, which has no transitions at all."""
        ex = fake_execute({"resolve-statuses": JIRA_STATUSES})
        out = JR.resolve_status_ids(self._cfg(), ex)
        self.assertEqual(set(out.mapping.values()), {"1", "2", "3"})
        for req in ex.calls:
            self.assertNotIn("transitions", str(req.url_or_argv))

    def test_shared_category_is_ambiguous_and_takes_select(self) -> None:
        statuses = ok([{"id": "10001", "statuses": [
            {"id": "1", "name": "Open", "statusCategory": {"key": "new"}},
            {"id": "2", "name": "Working", "statusCategory": {"key": "indeterminate"}},
            {"id": "5", "name": "Verifying", "statusCategory": {"key": "indeterminate"}},
            {"id": "3", "name": "Finished", "statusCategory": {"key": "done"}},
        ]}])
        ex = fake_execute({"resolve-statuses": statuses})
        out = JR.resolve_status_ids(self._cfg(), ex)
        self.assertIsNotNone(out.conflict)
        self.assertEqual(out.conflict["normalized"], "in_progress")

    def test_status_map_migrates_resolvable_entries(self) -> None:
        ex = fake_execute({"resolve-statuses": JIRA_STATUSES})
        out = JR.resolve_status_ids(self._cfg(
            {"todo": {"id": "1"}, "done": {"name": "Done"}}), ex)
        self.assertEqual(out.mapping["todo"], "1")
        self.assertEqual(out.mapping["done"], "3")

    def test_dead_status_map_entries_dropped_with_warning(self) -> None:
        ex = fake_execute({"resolve-statuses": JIRA_STATUSES})
        out = JR.resolve_status_ids(self._cfg(
            {"in_review": {"id": "99"}, "cancelled": {"name": "Ghost"}}), ex)
        self.assertNotIn("in_review", out.mapping)
        self.assertNotIn("cancelled", out.mapping)
        self.assertEqual(len([w for w in out.warnings if "dropped" in w]), 2)

    def test_malformed_status_map_does_not_crash(self) -> None:
        ex = fake_execute({"resolve-statuses": JIRA_STATUSES})
        for bad in ("not-a-dict", 7, ["x"], {"todo": "bare-string"}):
            with self.subTest(statusMap=bad):
                out = JR.resolve_status_ids(self._cfg(bad), ex)
                self.assertIsInstance(out, ST.Assignment)
                self.assertTrue(out.warnings)

    def test_missing_required_category_names_the_slot(self) -> None:
        statuses = ok([{"id": "10001", "statuses": [
            {"id": "1", "name": "To Do", "statusCategory": {"key": "new"}},
            {"id": "3", "name": "Done", "statusCategory": {"key": "done"}},
        ]}])
        ex = fake_execute({"resolve-statuses": statuses})
        out = JR.resolve_status_ids(self._cfg(), ex)
        self.assertIn("in_progress", out.missing_required)


class ResolveVerb(unittest.TestCase):
    def setUp(self) -> None:
        import os
        from unittest import mock
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("JIRA_BASE_URL", None)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.flow = Path(self.tmp.name)

    def _write(self, cfg: dict) -> None:
        (self.flow / "config.json").write_text(json.dumps(cfg), encoding="utf-8")

    def _linear_responses(self) -> dict:
        return {
            "resolve-destination": ok({"data": {"team": {"id": "team-uuid-1",
                                                         "key": "FLOW"}}}),
            "resolve-labels": ok({"data": {"team": {"labels": {
                "nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}),
            "resolve-states": linear_states(SIMPLE_STATES),
        }

    def test_inactive_repo_reports_inactive(self) -> None:
        self._write({})
        payload, code = RV.run(self.flow, execute=fake_execute({}))
        self.assertEqual(json.loads(payload)["class"], "inactive")
        self.assertEqual(code, 3)

    def test_backfill_resolves_all_scopes_and_stamps_resolved_at(self) -> None:
        self._write(linear_cfg())
        payload, code = RV.run(self.flow, execute=fake_execute(self._linear_responses()))
        self.assertEqual(code, 0, payload)
        data = json.loads(payload)["data"]["resolved"]
        self.assertEqual(data["destination"]["teamKey"], "FLOW")
        self.assertEqual(data["destination"]["stateIds"]["in_progress"], "s-prog")
        self.assertTrue(data["capabilities"]["blockedBy"])
        self.assertIsNotNone(data["resolvedAt"])
        self.assertEqual(set(data["scopeResolvedAt"]),
                         {"destination", "destination.stateIds", "capabilities"})

    def test_backfill_skips_fresh_scopes_without_refresh(self) -> None:
        self._write(linear_cfg())
        RV.run(self.flow, execute=fake_execute(self._linear_responses()))
        ex2 = fake_execute(self._linear_responses())
        payload, code = RV.run(self.flow, execute=ex2)
        self.assertEqual(code, 0)
        self.assertEqual(len(ex2.calls), 0, "everything fresh - zero network")

    def test_refresh_re_resolves(self) -> None:
        self._write(linear_cfg())
        RV.run(self.flow, execute=fake_execute(self._linear_responses()))
        ex2 = fake_execute(self._linear_responses())
        payload, code = RV.run(self.flow, refresh=True, execute=ex2)
        self.assertEqual(code, 0)
        self.assertGreater(len(ex2.calls), 0)

    def test_scope_resolves_only_that_path(self) -> None:
        self._write(linear_cfg())
        ex = fake_execute(self._linear_responses())
        payload, code = RV.run(self.flow, scope="destination.stateIds", execute=ex)
        self.assertEqual(code, 0, payload)
        cfg = json.loads((self.flow / "config.json").read_text(encoding="utf-8"))
        sra = cfg["tracker"]["resolved"]["scopeResolvedAt"]
        self.assertEqual(set(sra), {"destination.stateIds"})
        self.assertIsNone(cfg["tracker"]["resolved"]["resolvedAt"],
                          "partial resolution never stamps resolvedAt")

    def test_inapplicable_scope_is_invalid_input(self) -> None:
        self._write(linear_cfg())
        payload, code = RV.run(self.flow, scope="destination.statusIds",
                               execute=fake_execute({}))
        self.assertEqual(code, 2)

    def test_ambiguous_slot_is_a_typed_conflict(self) -> None:
        states = [
            {"id": "s-todo", "name": "Todo", "type": "unstarted"},
            {"id": "s-a", "name": "Doing", "type": "started"},
            {"id": "s-b", "name": "Verifying", "type": "started"},
            {"id": "s-done", "name": "Done", "type": "completed"},
        ]
        responses = self._linear_responses()
        responses["resolve-states"] = linear_states(states)
        self._write(linear_cfg())
        payload, code = RV.run(self.flow, execute=fake_execute(responses))
        self.assertEqual(code, 10, payload)
        out = json.loads(payload)
        self.assertEqual(out["class"], "conflict")
        self.assertEqual(out["details"]["normalized"], "in_progress")
        self.assertEqual(len(out["details"]["candidates"]), 2)

    #: Two started states (the #308 shape): in_progress needs a human tiebreak,
    #: every other slot is unambiguous.
    TWO_STARTED = [
        {"id": "s-todo", "name": "Todo", "type": "unstarted"},
        {"id": "s-a", "name": "Doing", "type": "started"},
        {"id": "s-b", "name": "Verifying", "type": "started"},
        {"id": "s-done", "name": "Done", "type": "completed"},
    ]

    def test_select_persists_the_union_of_selection_and_assignment(self) -> None:
        """#308: the tiebreak resolves ONE slot; the remaining slots still get
        the normal assignment, and the union is what is persisted."""
        self._write(linear_cfg())
        ex = fake_execute({"resolve-states": linear_states(self.TWO_STARTED)})
        payload, code = RV.run(self.flow, select="in_progress=s-a", execute=ex)
        self.assertEqual(code, 0, payload)
        out = json.loads(payload)["data"]
        self.assertEqual(out["selected"], {"in_progress": "s-a"})
        self.assertFalse(out["alias"])
        cfg = json.loads((self.flow / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["tracker"]["resolved"]["destination"]["stateIds"],
                         {"todo": "s-todo", "in_progress": "s-a",
                          "done": "s-done"})
        self.assertNotIn("in_review",
                         cfg["tracker"]["resolved"]["destination"]["stateIds"],
                         "the secondary started slot NEVER auto-fills - that "
                         "design stays (#308)")

    def test_issue_308_repro_ends_with_a_complete_map_at_step_three(self) -> None:
        """The five-step repro, verbatim: resolve -> conflict, select -> the map
        is COMPLETE, and the follow-up plain resolve has nothing left to repair.
        """
        self._write(linear_cfg())
        responses = dict(self._linear_responses(),
                         **{"resolve-states": linear_states(self.TWO_STARTED)})

        # 1. scoped resolve: in_progress is ambiguous.
        payload, code = RV.run(self.flow, scope="destination.stateIds",
                               execute=fake_execute(responses))
        self.assertEqual(code, 10, payload)
        self.assertEqual(json.loads(payload)["details"]["normalized"],
                         "in_progress")

        # 2. the human tiebreak.
        payload, code = RV.run(self.flow, select="in_progress=s-a",
                               execute=fake_execute(responses))
        self.assertEqual(code, 0, payload)

        # 3. read the map back: every REQUIRED slot present, stamped fresh.
        cfg = json.loads((self.flow / "config.json").read_text(encoding="utf-8"))
        state_ids = cfg["tracker"]["resolved"]["destination"]["stateIds"]
        for slot in ST.REQUIRED_SLOTS:
            self.assertIn(slot, state_ids, state_ids)
        self.assertIn("destination.stateIds",
                      cfg["tracker"]["resolved"]["scopeResolvedAt"])

        # 4. a plain resolve skips the fresh scope - and now that is correct.
        payload, code = RV.run(self.flow, execute=fake_execute(responses))
        self.assertEqual(code, 0, payload)
        self.assertEqual(
            json.loads(payload)["data"]["resolved"]["destination"]["stateIds"],
            state_ids)

        # 5. --refresh has nothing left to add.
        RV.run(self.flow, scope="destination.stateIds", refresh=True,
               execute=fake_execute(responses))
        cfg = json.loads((self.flow / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["tracker"]["resolved"]["destination"]["stateIds"],
                         state_ids)

    def test_required_incomplete_select_is_a_conflict_with_no_fresh_stamp(self) -> None:
        """A workflow with no unstarted/completed state cannot satisfy
        REQUIRED_SLOTS: the selection is kept (progress), the scope is NOT
        stamped, and the caller gets the CONFLICT the full path already had."""
        states = [
            {"id": "s-a", "name": "Doing", "type": "started"},
            {"id": "s-b", "name": "Verifying", "type": "started"},
        ]
        self._write(linear_cfg())
        ex = fake_execute({"resolve-states": linear_states(states)})
        payload, code = RV.run(self.flow, select="in_progress=s-a", execute=ex)
        self.assertEqual(code, 10, payload)
        out = json.loads(payload)
        self.assertEqual(out["class"], "conflict")
        self.assertEqual(out["details"]["normalized"], "todo")
        cfg = json.loads((self.flow / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["tracker"]["resolved"]["destination"]["stateIds"],
                         {"in_progress": "s-a"},
                         "the human tiebreak is kept - otherwise no sequence of "
                         "selects can ever complete the map")
        self.assertNotIn("destination.stateIds",
                         cfg["tracker"]["resolved"]["scopeResolvedAt"],
                         "an incomplete map must never read fresh, or a later "
                         "plain resolve skips the scope (#308)")
        self.assertIsNone(cfg["tracker"]["resolved"]["resolvedAt"])

    def test_a_stale_fresh_stamp_is_dropped_when_the_map_stays_incomplete(self) -> None:
        """Configs already damaged by the #308 bug self-repair: writing an
        incomplete map REMOVES the prior stamp rather than leaving it fresh."""
        cfg = linear_cfg()
        cfg["tracker"]["resolved"] = {
            "destination": {"stateIds": {"in_progress": "s-a"}},
            "scopeResolvedAt": {"destination.stateIds": "2020-01-01T00:00:00Z"},
            "resolvedAt": None,
        }
        self._write(cfg)
        ex = fake_execute({"resolve-states": linear_states([
            {"id": "s-a", "name": "Doing", "type": "started"},
            {"id": "s-b", "name": "Verifying", "type": "started"},
        ])})
        payload, code = RV.run(self.flow, select="in_progress=s-b", execute=ex)
        self.assertEqual(code, 10, payload)
        written = json.loads((self.flow / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(written["tracker"]["resolved"]["destination"]["stateIds"],
                         {"in_progress": "s-b"})
        self.assertNotIn("destination.stateIds",
                         written["tracker"]["resolved"]["scopeResolvedAt"])

    def test_select_leaves_another_ambiguous_required_slot_as_conflict(self) -> None:
        """Jira: filling one slot must not paper over a second ambiguity."""
        cfg = jira_cfg()
        cfg["tracker"]["resolved"] = {"destination": {"issueTypeId": "10001"}}
        self._write(cfg)
        ex = fake_execute({"resolve-statuses": ok([{
            "id": "10001", "name": "Task", "statuses": [
                {"id": "1", "name": "Triage", "statusCategory": {"key": "new"}},
                {"id": "2", "name": "Selected", "statusCategory": {"key": "new"}},
                {"id": "3", "name": "Doing",
                 "statusCategory": {"key": "indeterminate"}},
                {"id": "4", "name": "Shipped", "statusCategory": {"key": "done"}},
            ]}])})
        payload, code = RV.run(self.flow, select="in_progress=3", execute=ex)
        self.assertEqual(code, 10, payload)
        out = json.loads(payload)
        self.assertEqual(out["details"]["normalized"], "todo")
        written = json.loads((self.flow / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(
            written["tracker"]["resolved"]["destination"]["statusIds"],
            {"in_progress": "3", "done": "4"},
            "the unambiguous slots still fill; only the ambiguous one waits")

    def test_reselect_overwrites(self) -> None:
        states = [
            {"id": "s-a", "name": "Doing", "type": "started"},
            {"id": "s-b", "name": "Verifying", "type": "started"},
        ]
        self._write(linear_cfg())
        RV.run(self.flow, select="in_progress=s-a",
               execute=fake_execute({"resolve-states": linear_states(states)}))
        RV.run(self.flow, select="in_progress=s-b",
               execute=fake_execute({"resolve-states": linear_states(states)}))
        cfg = json.loads((self.flow / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["tracker"]["resolved"]["destination"]["stateIds"],
                         {"in_progress": "s-b"})

    def test_select_validates_against_live_candidates(self) -> None:
        self._write(linear_cfg())
        ex = fake_execute({"resolve-states": linear_states(FIVE_STATES)})
        payload, code = RV.run(self.flow, select="in_progress=not-a-live-id", execute=ex)
        self.assertEqual(code, 2)
        self.assertIn("not a live", json.loads(payload)["error"])

    def test_select_outside_natural_pool_is_a_recorded_alias(self) -> None:
        self._write(linear_cfg())
        ex = fake_execute({"resolve-states": linear_states(SIMPLE_STATES)})
        payload, code = RV.run(self.flow, select="in_review=s-done", execute=ex)
        self.assertEqual(code, 0, payload)
        out = json.loads(payload)["data"]
        self.assertTrue(out["alias"])
        self.assertTrue(out["warnings"], "recorded, not silent")
        self.assertEqual(out["stateIds"]["in_review"], "s-done")
        self.assertEqual(out["stateIds"]["in_progress"], "s-prog",
                         "the alias select still runs the normal assignment "
                         "over the remaining slots (#308)")

    def test_jira_backfill_end_to_end(self) -> None:
        self._write(jira_cfg())
        ex = fake_execute({
            "resolve-destination": ok(JiraDestination.PROJECT),
            "resolve-statuses": JIRA_STATUSES,
        })
        payload, code = RV.run(self.flow, execute=ex)
        self.assertEqual(code, 0, payload)
        data = json.loads(payload)["data"]["resolved"]
        self.assertEqual(data["destination"]["apiVersion"], 2)
        self.assertEqual(data["destination"]["statusIds"],
                         {"todo": "1", "in_progress": "2", "done": "3"})
        self.assertIsNotNone(data["resolvedAt"])

    def test_select_on_a_non_slot_provider_is_invalid(self) -> None:
        self._write({"tracker": {"type": "github", "perTracker": {}}})
        payload, code = RV.run(self.flow, select="todo=x", execute=fake_execute({}))
        self.assertEqual(code, 2)


class CliSurface(unittest.TestCase):
    def test_tracker_resolve_registered(self) -> None:
        out = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "flowctl.py"),
             "tracker", "resolve", "--help"],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        for flag in ("--scope", "--refresh", "--select"):
            self.assertIn(flag, out.stdout)


if __name__ == "__main__":
    unittest.main()


class LegacyStatusMapVocabulary(unittest.TestCase):
    """Existing statusMap keys use the OLD normalized vocabulary (status-sync.md:
    planned / in-progress / in-review / verified / wontfix ...). Copying them
    verbatim silently ignored every real mapping."""

    def setUp(self) -> None:
        import os
        from unittest import mock
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("JIRA_BASE_URL", None)

    def _cfg(self, status_map) -> dict:
        cfg = jira_cfg(statusMap=status_map)
        cfg["tracker"]["resolved"] = {"destination": {"issueTypeId": "10001"}}
        return cfg

    def test_legacy_keys_migrate_to_the_new_slots(self) -> None:
        ex = fake_execute({"resolve-statuses": JIRA_STATUSES})
        out = JR.resolve_status_ids(self._cfg({
            "planned": {"id": "1"}, "in-progress": {"id": "2"},
            "done": {"id": "3"}}), ex)
        self.assertEqual(out.mapping, {"todo": "1", "in_progress": "2", "done": "3"})

    def test_verified_fills_done_only_when_done_is_absent(self) -> None:
        ex = fake_execute({"resolve-statuses": JIRA_STATUSES})
        out = JR.resolve_status_ids(self._cfg({"verified": {"id": "3"}}), ex)
        self.assertEqual(out.mapping["done"], "3")
        ex2 = fake_execute({"resolve-statuses": JIRA_STATUSES})
        out2 = JR.resolve_status_ids(self._cfg(
            {"done": {"id": "3"}, "verified": {"id": "3"}}), ex2)
        self.assertTrue(any("verified" in w for w in out2.warnings))

    def test_unknown_legacy_key_warns_never_silent(self) -> None:
        ex = fake_execute({"resolve-statuses": JIRA_STATUSES})
        out = JR.resolve_status_ids(self._cfg({"deferred": {"id": "1"}}), ex)
        self.assertTrue(any("deferred" in w for w in out.warnings))


class JiraIssueTypeIsNeverFirstEntry(unittest.TestCase):
    def test_status_scope_without_resolved_issue_type_is_unresolved(self) -> None:
        cfg = jira_cfg()  # no resolved destination at all
        ex = fake_execute({"resolve-statuses": ok([
            {"id": "10005", "name": "Story", "statuses": [
                {"id": "9", "name": "Story Doing",
                 "statusCategory": {"key": "indeterminate"}}]},
        ])})
        out = JR.resolve_status_ids(cfg, ex)
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.UNRESOLVED)
        self.assertIn("issueTypeId", out.message)


class MalformedConfigShapes(unittest.TestCase):
    def test_non_object_containers_return_the_envelope_not_a_traceback(self) -> None:
        for cfg in ({"tracker": "bad"},
                    {"tracker": ["x"]},
                    {"tracker": {"type": "jira", "perTracker": "bad"}}):
            with self.subTest(cfg=cfg):
                with tempfile.TemporaryDirectory() as td:
                    flow = Path(td)
                    (flow / "config.json").write_text(json.dumps(cfg),
                                                      encoding="utf-8")
                    payload, code = RV.run(flow, execute=fake_execute({}))
                    out = json.loads(payload)
                    self.assertFalse(out["success"])
                    self.assertIn(out["class"], ("invalid_input", "inactive"))


class PaginationProgressGuard(unittest.TestCase):
    def test_repeated_cursor_fails_rather_than_looping(self) -> None:
        looping = ok({"data": {"team": {"states": {
            "nodes": [{"id": "s1", "name": "X", "type": "unstarted"}],
            "pageInfo": {"hasNextPage": True, "endCursor": "same"}}}}})
        ex = fake_execute({"resolve-states": looping})  # same response forever
        out = LN.resolve_state_ids(linear_cfg(), ex)
        self.assertIsInstance(out, TrackerError)
        self.assertEqual(out.subtype, "malformed_body")
        self.assertLess(len(ex.calls), 5, "must abort on the first repeat")


class SelectIsFingerprintProtected(unittest.TestCase):
    def test_mid_select_team_repoint_cannot_write_team_a_ids_into_team_b(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            flow = Path(td)
            (flow / "config.json").write_text(json.dumps(linear_cfg()),
                                              encoding="utf-8")
            calls = {"n": 0}

            def execute(request):
                calls["n"] += 1
                if calls["n"] == 1:
                    # A `config set` repoints the team while the select's
                    # validation fetch is in flight.
                    repointed = {"tracker": {"type": "linear",
                                             "perTracker": {"teamId": "team-B"}}}
                    (flow / "config.json").write_text(json.dumps(repointed),
                                                      encoding="utf-8")
                return linear_states([
                    {"id": "s-todo", "name": "Todo", "type": "unstarted"},
                    {"id": "s-a", "name": "Doing", "type": "started"},
                    {"id": "s-b", "name": "Verifying", "type": "started"},
                    {"id": "s-done", "name": "Done", "type": "completed"},
                ])

            payload, code = RV.run(flow, select="in_progress=s-a", execute=execute)
            self.assertEqual(code, 0, payload)
            self.assertEqual(calls["n"], 2,
                             "fingerprint mismatch forces ONE re-validation "
                             "against the repointed team")
