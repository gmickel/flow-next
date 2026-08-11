"""Per-spec Linear Project sidecar: tracker.projectId / projectMilestoneId.

fn-182.3 (#315 option 1). The pins that matter: present fields ride the
existing projection (issueCreate input, issueUpdate reconcile), absent fields
leave today's payload byte-identical, and reconcile NEVER sends a null - an
absent field is unmanaged, not "no Project" (R4).
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker import classify  # noqa: E402
from flowctl_tracker import lifecycle as L  # noqa: E402
from flowctl_tracker import syncbody as SB  # noqa: E402
from flowctl_tracker.lifecycle.helpers import spec_project_fields  # noqa: E402
from flowctl_tracker.types import ErrorClass, Response, TrackerError  # noqa: E402

LN_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
GH_NODE = "I_kwDOTestNode1"
PROJECT = "11111111-2222-3333-4444-555555555555"
MILESTONE = "66666666-7777-8888-9999-aaaaaaaaaaaa"


def ok(body) -> Response:
    return Response(200, {}, json.dumps(body).encode(), 0.01)


def linear_error(message: str):
    """What the REAL executor hands back for a rejected mutation: the response
    run through the shared classifier, not a raw body the fake pre-digested."""
    resp = Response(400, {}, json.dumps(
        {"errors": [{"message": message}]}).encode(), 0.01)
    err = classify.classify("linear", resp)
    assert isinstance(err, TrackerError)
    return err


def fake_execute(responses: dict):
    calls = []

    def execute(request):
        calls.append(request)
        if request.op not in responses:
            raise AssertionError(
                f"unexpected op {request.op!r}; have {sorted(responses)}")
        out = responses[request.op]
        if isinstance(out, list):
            out = out.pop(0)
        return out(request) if callable(out) else out

    execute.calls = calls
    return execute


def ln_cfg() -> dict:
    return {"tracker": {"type": "linear",
                        "resolved": {"destination": {
                            "teamId": "team-1", "teamKey": "WOR"}}}}


def gh_cfg() -> dict:
    return {"tracker": {"type": "github",
                        "resolved": {"destination": {"owner": "o", "repo": "r"}}}}


def _ln_issue(body: str, *, project=None, milestone=None) -> dict:
    issue = {
        "id": LN_UUID, "identifier": "WOR-17", "title": "Demo",
        "description": body, "url": "https://linear.app/x/issue/WOR-17",
        "state": {"id": "s", "name": "Backlog", "type": "backlog"},
        "labels": {"nodes": []}, "assignee": None,
    }
    if project is not None:
        issue["project"] = {"id": project}
    if milestone is not None:
        issue["projectMilestone"] = {"id": milestone}
    return issue


def _write_flow(flow: Path, config: dict, *, tracker: dict) -> Path:
    (flow / "specs").mkdir(parents=True, exist_ok=True)
    (flow / "config.json").write_text(json.dumps(config), encoding="utf-8")
    spec = {"id": "fn-1-demo", "title": "Demo", "status": "open",
            "tracker": tracker}
    path = flow / "specs" / "fn-1-demo.json"
    path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    return path


def _unlinked(**extra) -> dict:
    base = {"id": None, "identifier": None, "url": None,
            "lastSyncedAt": None, "depRelations": []}
    base.update(extra)
    return base


def _linked(**extra) -> dict:
    base = {"id": LN_UUID, "identifier": "WOR-17", "url": "https://x/17",
            "lastSyncedAt": None, "depRelations": [], "linkState": "linked",
            "baseHashFlow": None, "baseHashTracker": None,
            "mergeBaseFlow": None, "mergeBaseTracker": None}
    base.update(extra)
    return base


def _create_input(ex) -> dict:
    call = next(c for c in ex.calls if c.op == "lifecycle-create")
    return json.loads(call.body.decode())["variables"]["input"]


def _readback(body: str) -> Response:
    return ok({"data": {"issue": _ln_issue(body)}})


# ---------------------------------------------------------------------------
# Sidecar reader
# ---------------------------------------------------------------------------

class SidecarFields(unittest.TestCase):
    def test_absent_is_unmanaged(self) -> None:
        self.assertEqual(spec_project_fields(_linked()), {})
        self.assertEqual(
            spec_project_fields(_linked(projectId=None,
                                        projectMilestoneId=None)), {})

    def test_present_fields_are_trimmed_input_keys(self) -> None:
        self.assertEqual(
            spec_project_fields(_linked(projectId=f" {PROJECT} ",
                                        projectMilestoneId=MILESTONE)),
            {"projectId": PROJECT, "projectMilestoneId": MILESTONE})

    def test_unusable_value_errors_rather_than_dropping(self) -> None:
        for bad in ("", "   ", 17, {"id": PROJECT}):
            out = spec_project_fields(_linked(projectId=bad))
            self.assertIsInstance(out, TrackerError, bad)
            self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
            self.assertEqual(out.subtype, "project")


# ---------------------------------------------------------------------------
# create: issueCreate input
# ---------------------------------------------------------------------------

class CreateCarriesProject(unittest.TestCase):
    def test_absent_fields_keep_todays_payload_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg(), tracker=_unlinked())
            ex = fake_execute({
                "lifecycle-create": ok({"data": {"issueCreate": {
                    "success": True, "issue": _ln_issue("B")}}}),
                "sync-body-parent-read": _readback("B"),
            })
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertEqual(out["id"], LN_UUID)
            self.assertEqual(
                _create_input(ex),
                {"teamId": "team-1", "title": "T", "description": "B"})

    def test_both_fields_ride_the_create_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg(),
                        tracker=_unlinked(projectId=PROJECT,
                                          projectMilestoneId=MILESTONE))
            ex = fake_execute({
                "lifecycle-create": ok({"data": {"issueCreate": {
                    "success": True, "issue": _ln_issue("B")}}}),
                "sync-body-parent-read": _readback("B"),
            })
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertEqual(out["id"], LN_UUID)
            self.assertEqual(
                _create_input(ex),
                {"teamId": "team-1", "title": "T", "description": "B",
                 "projectId": PROJECT, "projectMilestoneId": MILESTONE})

    def test_project_only_never_sends_a_null_milestone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg(), tracker=_unlinked(projectId=PROJECT))
            ex = fake_execute({
                "lifecycle-create": ok({"data": {"issueCreate": {
                    "success": True, "issue": _ln_issue("B")}}}),
                "sync-body-parent-read": _readback("B"),
            })
            L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            inp = _create_input(ex)
            self.assertEqual(inp["projectId"], PROJECT)
            self.assertNotIn("projectMilestoneId", inp)

    def test_invalid_project_id_surfaces_the_provider_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg(), tracker=_unlinked(projectId="nope"))
            ex = fake_execute({
                "lifecycle-create": linear_error(
                    "Entity not found: Project - nope"),
            })
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.NOT_FOUND)
            self.assertEqual(out.subtype, "graphql")
            saved = json.loads(
                (flow / "specs" / "fn-1-demo.json").read_text())["tracker"]
            self.assertIsNone(saved["id"])

    def test_malformed_sidecar_refuses_before_any_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, ln_cfg(), tracker=_unlinked(projectId=""))
            ex = fake_execute({})
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.INVALID_INPUT)
            self.assertEqual(ex.calls, [])

    def test_non_linear_tracker_refuses_instead_of_dropping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            _write_flow(flow, gh_cfg(), tracker=_unlinked(projectId=PROJECT))
            ex = fake_execute({})
            out = L.create(flow, "fn-1-demo", title="T", body="B", execute=ex)
            self.assertIsInstance(out, TrackerError)
            self.assertIs(out.cls, ErrorClass.CAPABILITY)
            self.assertEqual(out.subtype, "project")
            self.assertEqual(ex.calls, [])


# ---------------------------------------------------------------------------
# sync-body push: issueUpdate reconcile
# ---------------------------------------------------------------------------

class ReconcileOnPush(unittest.TestCase):
    def _push(self, tracker: dict, responses: dict, *, body_in="new body\n"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        flow = Path(tmp.name)
        _write_flow(flow, ln_cfg(), tracker=tracker)
        ex = fake_execute(responses)
        out = SB.sync_body(flow, "fn-1-demo", flow_file_body=body_in,
                           direction="push", execute=ex)
        return out, ex

    def test_absent_fields_issue_no_project_mutation(self) -> None:
        out, ex = self._push(
            _linked(),
            {"sync-body-parent-read": _readback("old body\n"),
             "wire-parent-read": _readback("old body\n"),
             "wire-update": ok({"data": {"issueUpdate": {
                 "success": True, "issue": _ln_issue("new body\n")}}}),
             "wire-read": _readback("new body\n")})
        self.assertEqual(out["kind"], "pushed")
        self.assertEqual([c.op for c in ex.calls if c.op == "wire-project-set"], [])

    def test_present_fields_reconcile_via_issue_update(self) -> None:
        captured = {}

        def _project(request):
            captured["input"] = json.loads(
                request.body.decode())["variables"]["input"]
            captured["query"] = json.loads(request.body.decode())["query"]
            return ok({"data": {"issueUpdate": {
                "success": True,
                "issue": _ln_issue("old body\n", project=PROJECT,
                                   milestone=MILESTONE)}}})

        out, ex = self._push(
            _linked(projectId=PROJECT, projectMilestoneId=MILESTONE),
            {"sync-body-parent-read": _readback("old body\n"),
             "wire-parent-read": _readback("old body\n"),
             "wire-project-set": _project,
             "wire-update": ok({"data": {"issueUpdate": {
                 "success": True, "issue": _ln_issue("new body\n")}}}),
             "wire-read": _readback("new body\n")})
        self.assertEqual(out["kind"], "pushed")
        self.assertIn("issueUpdate", captured["query"])
        self.assertEqual(captured["input"],
                         {"projectId": PROJECT,
                          "projectMilestoneId": MILESTONE})

    def test_absent_milestone_is_never_sent_as_null(self) -> None:
        captured = {}

        def _project(request):
            captured["input"] = json.loads(
                request.body.decode())["variables"]["input"]
            return ok({"data": {"issueUpdate": {
                "success": True,
                "issue": _ln_issue("old body\n", project=PROJECT)}}})

        self._push(
            _linked(projectId=PROJECT),
            {"sync-body-parent-read": _readback("old body\n"),
             "wire-parent-read": _readback("old body\n"),
             "wire-project-set": _project,
             "wire-update": ok({"data": {"issueUpdate": {
                 "success": True, "issue": _ln_issue("new body\n")}}}),
             "wire-read": _readback("new body\n")})
        self.assertEqual(captured["input"], {"projectId": PROJECT})
        self.assertNotIn("projectMilestoneId", captured["input"])

    def test_converged_body_still_reconciles_the_project(self) -> None:
        # No body write at all (no-op push): the Project must still land, or a
        # projectId added after the body converged would never be applied.
        out, ex = self._push(
            _linked(projectId=PROJECT),
            {"sync-body-parent-read": _readback("same\n"),
             "wire-parent-read": _readback("same\n"),
             "wire-project-set": ok({"data": {"issueUpdate": {
                 "success": True,
                 "issue": _ln_issue("same\n", project=PROJECT)}}})},
            body_in="same\n")
        self.assertEqual(out["kind"], "seeded")
        self.assertEqual([c.op for c in ex.calls if c.op == "wire-update"], [])
        self.assertEqual(
            len([c for c in ex.calls if c.op == "wire-project-set"]), 1)

    def test_invalid_project_id_on_reconcile_surfaces_and_stops_the_push(self) -> None:
        out, ex = self._push(
            _linked(projectId="nope"),
            {"sync-body-parent-read": _readback("old body\n"),
             "wire-parent-read": _readback("old body\n"),
             "wire-project-set": linear_error(
                 "Entity not found: Project - nope")})
        self.assertIsInstance(out, TrackerError)
        self.assertIs(out.cls, ErrorClass.NOT_FOUND)
        self.assertEqual(out.subtype, "graphql")
        self.assertEqual([c.op for c in ex.calls if c.op == "wire-update"], [])


if __name__ == "__main__":
    unittest.main()
