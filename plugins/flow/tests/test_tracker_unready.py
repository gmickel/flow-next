"""`tracker wire unready` (fn-324): move an issue out of tracker.readyState.

Fake transport over response shapes recorded live on 2026-11-15 against
GitHub (gmickel/test#1), a self-managed GitLab (flownext/flownext#1) and
Linear (FLOW-106); Jira shapes follow its existing status-writer path.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flow" / "scripts"))

from flowctl_tracker import wire as W  # noqa: E402
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
            out = out.pop(0)
        return out

    execute.calls = calls
    return execute


def loc(durable: str, display: str) -> dict:
    return {"durable": durable, "display": display}


GH_NODE = "I_kwDOBT30Qs8AAAABfaaOOA"
GH_READY = {"id": 4171, "node_id": GH_NODE, "number": 1, "title": "T", "body": "B",
            "html_url": "https://github.com/o/r/issues/1", "state": "open",
            "labels": [{"name": "Ready"}, {"name": "bug"}]}
GH_AFTER = dict(GH_READY, labels=[{"name": "bug"}])

GL_READY = {"id": 1, "iid": 1, "title": "T", "description": "B",
            "web_url": "http://localhost:8929/flownext/flownext/-/issues/1",
            "labels": ["ready"], "state": "opened"}
GL_AFTER = dict(GL_READY, labels=[])

LN_UUID = "6ec96698-49f6-4af1-ba84-533d6862f50c"
LN_TODO = {"id": LN_UUID, "identifier": "FLOW-106", "title": "T", "description": "B",
           "url": "https://linear.app/x/issue/FLOW-106",
           "state": {"id": "st-todo", "name": "Todo", "type": "unstarted"},
           "labels": {"nodes": []}, "assignee": None}
LN_BACKLOG = dict(LN_TODO, state={"id": "st-backlog", "name": "Backlog", "type": "backlog"})

JR_ID = "10042"
JR_READY = {"id": JR_ID, "key": "KAN-7",
            "fields": {"summary": "T", "description": "B", "labels": [],
                       "status": {"id": "10001", "name": "To Do",
                                  "statusCategory": {"key": "new"}}}}
JR_BACKLOG = {"id": JR_ID, "key": "KAN-7",
              "fields": {"summary": "T", "description": "B", "labels": [],
                         "status": {"id": "10000", "name": "Backlog",
                                    "statusCategory": {"key": "new"}}}}


def gh_cfg(ready="ready") -> dict:
    return {"tracker": {"type": "github", "readyState": ready,
                        "resolved": {"destination": {"owner": "o", "repo": "r"}}}}


def gl_cfg() -> dict:
    return {"tracker": {"type": "gitlab", "readyState": "ready",
                        "perTracker": {"project": "flownext/flownext"},
                        "resolved": {"destination": {
                            "projectId": 1, "projectPath": "flownext/flownext",
                            "host": "localhost:8929", "namespaceId": 1}}}}


def ln_cfg(backlog=True) -> dict:
    ids = {"todo": "st-todo", "in_progress": "st-prog", "done": "st-done"}
    if backlog:
        ids["backlog"] = "st-backlog"
    return {"tracker": {"type": "linear", "readyState": "Todo",
                        "perTracker": {"teamId": "team-1"},
                        "resolved": {"destination": {"teamId": "team-1", "teamKey": "FLOW",
                                                     "stateIds": ids}}}}


def jr_cfg(backlog=True) -> dict:
    ids = {"todo": "10001", "in_progress": "10002", "done": "10003"}
    if backlog:
        ids["backlog"] = "10000"
    return {"tracker": {"type": "jira", "readyState": "To Do",
                        "perTracker": {"baseUrl": "https://ex.atlassian.net",
                                       "projectKey": "KAN"},
                        "resolved": {"destination": {
                            "baseUrl": "https://ex.atlassian.net", "projectKey": "KAN",
                            "projectId": "10000", "issueTypeId": "10007",
                            "apiVersion": 2, "style": "next-gen", "statusIds": ids}}}}


def gql(issue) -> Response:
    return ok({"data": {"issue": issue}})


class Unready(unittest.TestCase):
    def test_github_drops_the_ready_label_case_insensitively(self) -> None:
        ex = fake_execute({"wire-read": ok(GH_READY), "wire-parent-read": ok(GH_READY),
                           "wire-label": ok([{"name": "bug"}]),
                           "wire-label-readback": ok(GH_AFTER)})
        out = W.dispatch("unready", gh_cfg(), locator=loc(GH_NODE, "#1"), execute=ex)
        self.assertEqual(out, {"issue": {"id": GH_NODE, "identifier": "#1"},
                               "from": "Ready", "to": None, "changed": True})
        delete = [c for c in ex.calls if c.op == "wire-label"][0]
        self.assertEqual(delete.method, "DELETE")
        self.assertTrue(delete.url_or_argv[-1].endswith("/issues/1/labels/Ready"))

    def test_gitlab_drops_the_ready_label(self) -> None:
        ex = fake_execute({"wire-read": ok(GL_READY), "wire-parent-read": ok(GL_READY),
                           "wire-label": ok(GL_AFTER)})
        out = W.dispatch("unready", gl_cfg(), locator=loc("1", "flownext/flownext#1"),
                         execute=ex)
        self.assertEqual(out["changed"], True)
        self.assertEqual(out["from"], "ready")
        body = json.loads([c for c in ex.calls if c.op == "wire-label"][0].body)
        self.assertEqual(body.get("remove_labels"), "ready")

    def test_linear_moves_to_the_backlog_state(self) -> None:
        ex = fake_execute({"wire-read": [gql(LN_TODO), gql(LN_BACKLOG)],
                           "status-set": ok({"data": {"issueUpdate": {
                               "success": True, "issue": {"id": LN_UUID}}}})})
        out = W.dispatch("unready", ln_cfg(), locator=loc(LN_UUID, "FLOW-106"), execute=ex)
        self.assertEqual(out, {"issue": {"id": LN_UUID, "identifier": "FLOW-106"},
                               "from": "Todo", "to": "Backlog", "changed": True})
        mutation = json.loads([c for c in ex.calls if c.op == "status-set"][0].body)
        self.assertEqual(mutation["variables"]["stateId"], "st-backlog")

    def test_jira_transitions_to_the_backlog_status(self) -> None:
        ex = fake_execute({
            "wire-read": [ok(JR_READY), ok(JR_BACKLOG)],
            "status-current": ok(JR_READY),
            "status-transitions": ok({"transitions": [
                {"id": "11", "to": {"id": "10002"}}, {"id": "21", "to": {"id": "10000"}}]}),
            "status-set": Response(204, {}, b"", 0.01)})
        out = W.dispatch("unready", jr_cfg(), locator=loc(JR_ID, "KAN-7"), execute=ex)
        self.assertEqual(out, {"issue": {"id": JR_ID, "identifier": "KAN-7"},
                               "from": "To Do", "to": "Backlog", "changed": True})
        posted = json.loads([c for c in ex.calls if c.op == "status-set"][0].body)
        self.assertEqual(posted, {"transition": {"id": "21"}})

    def test_an_issue_already_out_of_the_ready_state_is_not_written(self) -> None:
        cases = [
            ("github", gh_cfg(), loc(GH_NODE, "#1"), ok(GH_AFTER), None),
            ("gitlab", gl_cfg(), loc("1", "flownext/flownext#1"), ok(GL_AFTER), None),
            ("linear", ln_cfg(), loc(LN_UUID, "FLOW-106"), gql(LN_BACKLOG), "Backlog"),
            ("jira", jr_cfg(), loc(JR_ID, "KAN-7"), ok(JR_BACKLOG), "Backlog"),
        ]
        for provider, cfg, locator, read, name in cases:
            with self.subTest(provider=provider):
                ex = fake_execute({"wire-read": read})
                out = W.dispatch("unready", cfg, locator=locator, execute=ex)
                self.assertEqual(out["changed"], False)
                self.assertEqual((out["from"], out["to"]), (name, name))
                self.assertEqual([c.op for c in ex.calls], ["wire-read"])

    def test_ready_state_unset_makes_no_call(self) -> None:
        for cfg, locator in [(gh_cfg(), loc(GH_NODE, "#1")),
                             (gl_cfg(), loc("1", "flownext/flownext#1")),
                             (ln_cfg(), loc(LN_UUID, "FLOW-106")),
                             (jr_cfg(), loc(JR_ID, "KAN-7"))]:
            with self.subTest(provider=cfg["tracker"]["type"]):
                cfg["tracker"].pop("readyState")
                ex = fake_execute({})
                out = W.dispatch("unready", cfg, locator=locator, execute=ex)
                self.assertIsInstance(out, TrackerError)
                self.assertIs(out.cls, ErrorClass.UNRESOLVED)
                self.assertEqual(out.subtype, "ready_state")
                self.assertEqual(ex.calls, [])

    def test_no_backlog_slot_is_a_typed_error_with_no_mutation(self) -> None:
        ln = fake_execute({"wire-read": gql(LN_TODO)})
        out = W.dispatch("unready", ln_cfg(backlog=False),
                         locator=loc(LN_UUID, "FLOW-106"), execute=ln)
        self.assertEqual((out.cls, out.subtype), (ErrorClass.UNRESOLVED, "backlog_slot"))
        self.assertEqual([c.op for c in ln.calls], ["wire-read"])

        jr = fake_execute({"wire-read": ok(JR_READY)})
        out = W.dispatch("unready", jr_cfg(backlog=False),
                         locator=loc(JR_ID, "KAN-7"), execute=jr)
        self.assertEqual((out.cls, out.subtype), (ErrorClass.UNRESOLVED, "backlog_slot"))
        self.assertEqual([c.op for c in jr.calls], ["wire-read"])

    def test_jira_without_a_transition_to_backlog_is_a_typed_error(self) -> None:
        ex = fake_execute({"wire-read": ok(JR_READY), "status-current": ok(JR_READY),
                           "status-transitions": ok({"transitions": [
                               {"id": "11", "to": {"id": "10002"}}]})})
        out = W.dispatch("unready", jr_cfg(), locator=loc(JR_ID, "KAN-7"), execute=ex)
        self.assertEqual((out.cls, out.subtype),
                         (ErrorClass.UNRESOLVED, "transition_unreachable"))
        self.assertNotIn("status-set", [c.op for c in ex.calls])

    def test_a_move_that_did_not_take_is_an_error(self) -> None:
        ex = fake_execute({"wire-read": [gql(LN_TODO), gql(LN_TODO)],
                           "status-set": ok({"data": {"issueUpdate": {
                               "success": True, "issue": {"id": LN_UUID}}}})})
        out = W.dispatch("unready", ln_cfg(), locator=loc(LN_UUID, "FLOW-106"), execute=ex)
        self.assertEqual((out.cls, out.subtype), (ErrorClass.TRANSPORT, "readback"))

    def test_a_moved_issue_is_never_written(self) -> None:
        ex = fake_execute({"wire-read": gql(dict(LN_TODO, id="other-uuid"))})
        out = W.dispatch("unready", ln_cfg(), locator=loc(LN_UUID, "FLOW-106"), execute=ex)
        self.assertIs(out.cls, ErrorClass.CONFLICT)
        self.assertEqual([c.op for c in ex.calls], ["wire-read"])

    def test_cli_inactive_bridge_is_the_inactive_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp) / ".flow"
            flow.mkdir()
            (flow / "config.json").write_text("{}", encoding="utf-8")
            run = subprocess.run(
                [sys.executable, str(ROOT / "skills" / "flow" / "scripts" / "edge.py"), "tracker", "wire",
                 "unready", "--locator", json.dumps(loc(LN_UUID, "FLOW-106")), "--json"],
                cwd=tmp, capture_output=True, text=True)
        payload = json.loads(run.stdout)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["class"], "inactive")
        self.assertEqual(run.returncode, 3)


if __name__ == "__main__":
    unittest.main()
