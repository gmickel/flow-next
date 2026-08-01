"""Chart tracker projection + locate (fn-135.5 / R16,R42,R54,R55).

Covers local-only mode, typed locator/URL re-entry (incl. rejections with zero
mutation), lifecycle/rollup matrix, four-adapter capability degradation,
partial-success/reordered reconcile without duplicates, and event dedup.

Harness style follows test_tracker_conformance / test_tracker_facade.
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowctl_tracker.facade import chart_projection as CP  # noqa: E402
from flowctl_tracker.subjects import (  # noqa: E402
    charts_projection_enabled,
    projection_gate,
)
from flowctl_tracker.types import (  # noqa: E402
    ErrorClass,
    Response,
    TrackerError,
)

import flowctl  # noqa: E402


# ---------------------------------------------------------------------------
# Shared harness
# ---------------------------------------------------------------------------

def ok(body) -> Response:
    if isinstance(body, (bytes, bytearray)):
        return Response(200, {}, bytes(body), 0.01)
    return Response(
        200, {},
        json.dumps(body).encode() if body is not None else b"",
        0.01,
    )


def empty() -> Response:
    return Response(204, {}, b"", 0.01)


def fake_execute(responses: dict):
    calls = []
    sticky = {}  # last response per op for reusable reads

    def execute(request):
        calls.append(request)
        if request.op not in responses:
            if request.op == "lifecycle-create-meta":
                return ok({})
            if request.op in sticky:
                out = sticky[request.op]
                return out(request) if callable(out) else out
            raise AssertionError(
                f"unexpected op {request.op!r}; have {sorted(responses)}"
            )
        out = responses[request.op]
        if isinstance(out, list):
            if not out:
                if request.op in sticky:
                    out = sticky[request.op]
                    return out(request) if callable(out) else out
                raise AssertionError(f"no more responses for op {request.op!r}")
            out = out.pop(0)
            sticky[request.op] = out
        else:
            sticky[request.op] = out
        return out(request) if callable(out) else out

    execute.calls = calls
    return execute


def gh_cfg() -> dict:
    return {
        "tracker": {
            "enabled": True,
            "type": "github",
            "charts": "on",
            "perTracker": {"repo": "acme/demo", "owner": "acme"},
            "resolved": {
                "destination": {"owner": "acme", "repo": "demo"},
                "capabilities": {
                    "attachments": False,
                    "blockedBy": False,
                    "subIssues": True,
                    "deleteIssue": False,
                },
            },
        }
    }


def gl_cfg() -> dict:
    return {
        "tracker": {
            "enabled": True,
            "type": "gitlab",
            "charts": "on",
            "perTracker": {"project": "g/p", "host": "gitlab.com"},
            "resolved": {
                "destination": {
                    "projectId": "99",
                    "projectPath": "g/p",
                    "host": "gitlab.com",
                    "namespaceId": "1",
                },
                "capabilities": {
                    "attachments": True,
                    "blockedBy": True,
                    "subIssues": False,
                    "deleteIssue": True,
                },
            },
        }
    }


def ln_cfg() -> dict:
    return {
        "tracker": {
            "enabled": True,
            "type": "linear",
            "charts": "on",
            "perTracker": {"teamId": "team-1"},
            "resolved": {
                "destination": {
                    "teamId": "team-1",
                    "teamKey": "WOR",
                    "stateIds": {},
                    "labelIds": {},
                },
                "capabilities": {
                    "attachments": True,
                    "blockedBy": True,
                    "subIssues": False,
                    "deleteIssue": True,
                },
            },
        }
    }


def jr_cfg() -> dict:
    return {
        "tracker": {
            "enabled": True,
            "type": "jira",
            "charts": "on",
            "perTracker": {
                "baseUrl": "https://ex.atlassian.net",
                "projectKey": "SCRUM",
                "blocksLinkType": "Blocks",
            },
            "resolved": {
                "destination": {
                    "baseUrl": "https://ex.atlassian.net",
                    "projectKey": "SCRUM",
                    "projectId": "10000",
                    "issueTypeId": "10001",
                    "apiVersion": 2,
                    "style": "classic",
                    "statusIds": {
                        "todo": "1",
                        "in_progress": "2",
                        "in_review": "3",
                        "done": "4",
                    },
                },
                "capabilities": {
                    "attachments": True,
                    "blockedBy": True,
                    "subIssues": False,
                    "deleteIssue": True,
                },
            },
        }
    }


def _write_config(flow: Path, config: dict) -> None:
    flow.mkdir(parents=True, exist_ok=True)
    (flow / "config.json").write_text(json.dumps(config), encoding="utf-8")


def _seed_chart(
    flow: Path,
    chart_id: str = "fn-10",
    *,
    decisions: list[dict] | None = None,
    tracker: dict | None = None,
) -> dict:
    charts = flow / "charts"
    charts.mkdir(parents=True, exist_ok=True)
    (charts / chart_id).mkdir(parents=True, exist_ok=True)
    decs = decisions or [
        {
            "id": f"{chart_id}.D1",
            "title": "Pick storage",
            "type": "research",
            "attendance": "unattended",
            "status": "open",
            "blocked_by": [],
            "depends_on": [],
            "n": 1,
        }
    ]
    chart = {
        "id": chart_id,
        "title": "Tenancy chart",
        "outcome": "Multi-tenant ready",
        "status": "open",
        "created": "2026-01-01T00:00:00Z",
        "decisions": [
            {
                "id": d["id"],
                "title": d["title"],
                "type": d["type"],
                "attendance": d["attendance"],
                "status": d["status"],
                "blocked_by": d.get("blocked_by") or [],
                "depends_on": d.get("depends_on") or [],
                "record_path": f".flow/charts/{chart_id}/{d.get('n', 1)}.md",
            }
            for d in decs
        ],
        "parked_questions": [],
        "briefings": [],
        "tracker": tracker or {
            "id": None,
            "identifier": None,
            "url": None,
            "linkState": "unlinked",
            "depRelations": [],
            "projection": {"revision": None, "event_markers": [], "completed_steps": []},
        },
        "produced_specs": [],
        "claim_events": [],
    }
    (charts / f"{chart_id}.json").write_text(
        json.dumps(chart, indent=2) + "\n", encoding="utf-8"
    )
    (charts / f"{chart_id}.md").write_text(
        f"# {chart_id} Tenancy chart\n\n## Outcome\nMulti-tenant ready\n",
        encoding="utf-8",
    )
    for d in decs:
        n = d.get("n") or int(str(d["id"]).rsplit("D", 1)[-1])
        full = {
            **d,
            "chart": chart_id,
            "n": n,
            "question": d.get("question") or d["title"],
            "answer": d.get("answer"),
            "assets": d.get("assets") or [],
            "supersedes": d.get("supersedes") or [],
            "superseded_by": d.get("superseded_by"),
            "claimed_by": d.get("claimed_by"),
            "claimed_at": d.get("claimed_at"),
            "transition_notes": [],
            "created": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "record_path": f".flow/charts/{chart_id}/{n}.md",
            "tracker": d.get("tracker") or {
                "id": None,
                "identifier": None,
                "url": None,
                "linkState": "unlinked",
                "depRelations": [],
            },
        }
        (charts / chart_id / f"{n}.json").write_text(
            json.dumps(full, indent=2) + "\n", encoding="utf-8"
        )
        (charts / chart_id / f"{n}.md").write_text(
            f"## Question\n{full['question']}\n", encoding="utf-8"
        )
    return chart


# ---------------------------------------------------------------------------
# Config / gate
# ---------------------------------------------------------------------------

class ChartsConfigGateTests(unittest.TestCase):
    def test_default_charts_off(self) -> None:
        cfg = flowctl.get_default_tracker_config()
        self.assertEqual(cfg.get("charts"), "off")
        self.assertFalse(charts_projection_enabled({"tracker": cfg}))

    def test_literal_on_only(self) -> None:
        self.assertTrue(charts_projection_enabled({"tracker": {"charts": "on"}}))
        self.assertFalse(charts_projection_enabled({"tracker": {"charts": True}}))
        self.assertFalse(charts_projection_enabled({"tracker": {"charts": "push"}}))
        self.assertFalse(charts_projection_enabled({"tracker": {"charts": "off"}}))

    def test_gate_skips_when_off_or_inactive(self) -> None:
        g = projection_gate({"tracker": {"charts": "off", "type": "github"}})
        self.assertFalse(g["active"])
        self.assertEqual(g["skipped"], "tracker.charts_off")
        g2 = projection_gate({"tracker": {"charts": "on", "type": None}})
        self.assertFalse(g2["active"])
        self.assertEqual(g2["skipped"], "bridge_inactive")


# ---------------------------------------------------------------------------
# Local-only mode
# ---------------------------------------------------------------------------

class LocalOnlyProjectionTests(unittest.TestCase):
    def test_local_mutation_succeeds_with_projection_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, {"tracker": {"charts": "off", "type": None}})
            _seed_chart(flow)
            out = CP.project_chart(flow, "fn-10", event="chart.create")
            self.assertIsInstance(out, dict)
            self.assertFalse(out.get("projected"))
            self.assertEqual(out.get("skipped"), "tracker.charts_off")
            # Local chart untouched / still readable
            chart = json.loads(
                (flow / "charts" / "fn-10.json").read_text(encoding="utf-8")
            )
            self.assertEqual(chart["id"], "fn-10")
            self.assertIsNone((chart.get("tracker") or {}).get("id"))

    def test_inactive_bridge_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, {"tracker": {"charts": "on", "type": None}})
            _seed_chart(flow)
            out = CP.project_chart(flow, "fn-10", event="chart.resolve")
            self.assertFalse(out.get("projected"))
            self.assertEqual(out.get("skipped"), "bridge_inactive")


# ---------------------------------------------------------------------------
# Locate / URL re-entry
# ---------------------------------------------------------------------------

class LocateTests(unittest.TestCase):
    def test_canonical_chart_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(flow)
            out = CP.locate_selector(flow, "fn-10")
            self.assertIsInstance(out, dict)
            self.assertEqual(out["kind"], "chart")
            self.assertEqual(out["chart_id"], "fn-10")

    def test_open_decision_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(flow)
            out = CP.locate_selector(flow, "fn-10.D1")
            self.assertEqual(out["kind"], "decision")
            self.assertEqual(out["decision_id"], "fn-10.D1")
            self.assertEqual(out["status"], "open")
            self.assertIsNone(out.get("history"))

    def test_resolved_decision_is_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(
                flow,
                decisions=[{
                    "id": "fn-10.D1",
                    "title": "Done",
                    "type": "research",
                    "attendance": "unattended",
                    "status": "resolved",
                    "answer": {"gist": "use postgres"},
                    "n": 1,
                }],
            )
            out = CP.locate_selector(flow, "fn-10.D1")
            self.assertEqual(out["status"], "resolved")
            self.assertIsNotNone(out.get("history"))
            self.assertEqual(out["history"]["gist"], "use postgres")

    def test_stored_url_resolves_locally(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            url = "https://github.com/acme/demo/issues/42"
            _seed_chart(
                flow,
                tracker={
                    "id": "I_parent",
                    "identifier": "#42",
                    "url": url,
                    "linkState": "linked",
                    "depRelations": [],
                    "projection": {"event_markers": []},
                },
            )
            before = (flow / "charts" / "fn-10.json").read_text(encoding="utf-8")
            out = CP.locate_selector(flow, "HTTPS://GitHub.com/acme/demo/issues/42/")
            self.assertEqual(out["kind"], "chart")
            self.assertEqual(out["chart_id"], "fn-10")
            after = (flow / "charts" / "fn-10.json").read_text(encoding="utf-8")
            self.assertEqual(before, after, "locate must not mutate")

    def test_credential_url_rejected_zero_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(flow)
            before = (flow / "charts" / "fn-10.json").read_text(encoding="utf-8")
            out = CP.locate_selector(
                flow, "https://user:secret@github.com/acme/demo/issues/1"
            )
            self.assertIsInstance(out, TrackerError)
            self.assertEqual(out.cls, ErrorClass.INVALID_INPUT)
            self.assertEqual((out.details or {}).get("code"), "unresolved_locator")
            after = (flow / "charts" / "fn-10.json").read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_unknown_url_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(flow)
            out = CP.locate_selector(
                flow, "https://github.com/acme/demo/issues/99999"
            )
            self.assertIsInstance(out, TrackerError)
            self.assertEqual(out.cls, ErrorClass.UNRESOLVED)

    def test_wrong_host_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(
                flow,
                tracker={
                    "id": "I_x",
                    "identifier": "#1",
                    "url": "https://evil.example/issues/1",
                    "linkState": "linked",
                    "depRelations": [],
                    "projection": {"event_markers": []},
                },
            )
            # URL is in ledger but host is not allowed for github config
            out = CP.locate_selector(flow, "https://evil.example/issues/1")
            self.assertIsInstance(out, TrackerError)

    def test_stale_identifier_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(
                flow,
                tracker={
                    "id": None,
                    "identifier": "#7",
                    "url": None,
                    "linkState": "identifier_only",
                    "depRelations": [],
                    "projection": {"event_markers": []},
                },
            )
            out = CP.locate_selector(flow, "#7")
            self.assertIsInstance(out, TrackerError)
            self.assertEqual(out.cls, ErrorClass.STALE_ID)


# ---------------------------------------------------------------------------
# Bodies / depends_on never blocking
# ---------------------------------------------------------------------------

class BodyAndEdgeTests(unittest.TestCase):
    def test_decision_body_keeps_depends_on_local(self) -> None:
        body = CP.build_decision_body({
            "id": "fn-10.D2",
            "title": "Follow-on",
            "type": "eval",
            "attendance": "unattended",
            "status": "open",
            "blocked_by": ["fn-10.D1"],
            "depends_on": ["fn-10.D1"],
            "answer": None,
        })
        self.assertIn("Blocked by (local)", body)
        self.assertIn("Depends on (local provenance only", body)
        self.assertIn("flow-next:decision", body)

    def test_parent_rollup_counts(self) -> None:
        chart = {"id": "fn-10", "title": "T", "outcome": "O", "status": "open",
                 "parked_questions": [{"key": "k", "body": "q"}]}
        decisions = [
            {"id": "fn-10.D1", "title": "A", "status": "resolved",
             "answer": {"gist": "yes"}, "updated_at": "2026-02-01T00:00:00Z"},
            {"id": "fn-10.D2", "title": "B", "status": "open", "blocked_by": []},
            {"id": "fn-10.D3", "title": "C", "status": "open",
             "blocked_by": ["fn-10.D2"], "claimed_by": None},
        ]
        rollup = CP.build_parent_rollup(chart, decisions)
        self.assertIn("actionable=1", rollup)
        self.assertIn("blocked=1", rollup)
        self.assertIn("resolved=1", rollup)
        self.assertIn("parked=1", rollup)
        self.assertIn("Latest resolved", rollup)
        self.assertIn("fn-10.D1", rollup)


# ---------------------------------------------------------------------------
# Lifecycle projection with fake adapters
# ---------------------------------------------------------------------------

def _gh_issue(*, node_id: str, number: int, body: str = "b"):
    return {
        "node_id": node_id,
        "number": number,
        "html_url": f"https://github.com/acme/demo/issues/{number}",
        "body": body,
        "title": "t",
        "id": 9000 + number,
    }


def _gh_create_responses(*, parent_n=100, child_n=101):
    """Responses for parent + one child create on GitHub."""
    parent = _gh_issue(node_id=f"I_parent_{parent_n}", number=parent_n)
    child = _gh_issue(node_id=f"I_child_{child_n}", number=child_n)
    # wire-parent-read is used by update's identity check (many times).
    parent_reads = [ok(dict(parent)) for _ in range(8)]
    child_reads = [ok(dict(child)) for _ in range(8)]
    return {
        "lifecycle-create": [ok(dict(parent)), ok(dict(child))],
        "wire-parent-read": parent_reads + child_reads,
        "wire-read": [ok(dict(parent)), ok(dict(child))] * 4,
        "wire-update": [ok(dict(parent)), ok(dict(child))] * 4,
        "relate-child-read": ok(dict(child)),
        "relate-create": ok({"ok": True}),
    }


class LifecycleProjectionTests(unittest.TestCase):
    def _gh_issue(self, **kw):
        return _gh_issue(**kw)

    def _gh_create_responses(self, **kw):
        return _gh_create_responses(**kw)

    def test_create_wire_projects_parent_and_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(flow)
            ex = fake_execute(self._gh_create_responses())
            out = CP.project_chart(
                flow, "fn-10", event="chart.create",
                revision="rev1", evidence="ev1", execute=ex,
            )
            self.assertIsInstance(out, dict)
            self.assertTrue(out.get("projected"))
            self.assertIn("create-parent", out.get("completed_steps") or [])
            chart = json.loads(
                (flow / "charts" / "fn-10.json").read_text(encoding="utf-8")
            )
            self.assertEqual(chart["tracker"]["id"], "I_parent_100")
            child = json.loads(
                (flow / "charts" / "fn-10" / "1.json").read_text(encoding="utf-8")
            )
            self.assertEqual(child["tracker"]["id"], "I_child_101")
            # Aggregate receipt written
            runs = list((flow / "sync-runs").glob("sync-*.json"))
            self.assertTrue(runs)
            receipt = json.loads(runs[0].read_text(encoding="utf-8"))
            self.assertEqual(receipt["event"], "chart.create")

    def test_event_dedup_no_second_remote_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(flow)
            ex1 = fake_execute(self._gh_create_responses())
            out1 = CP.project_chart(
                flow, "fn-10", event="chart.create",
                revision="rev1", evidence="ev1", execute=ex1,
            )
            self.assertTrue(out1.get("projected"))
            creates1 = [
                c for c in ex1.calls if c.op == "lifecycle-create"
            ]
            self.assertEqual(len(creates1), 2)
            # Second call with same event+revision+evidence: deduped
            ex2 = fake_execute({})  # no responses - any call would fail
            out2 = CP.project_chart(
                flow, "fn-10", event="chart.create",
                revision="rev1", evidence="ev1", execute=ex2,
            )
            self.assertTrue(out2.get("deduped"))
            self.assertEqual(ex2.calls, [])

    def test_partial_success_persists_completed_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(flow)
            responses = self._gh_create_responses()
            # Parent create ok; child create fails
            responses["lifecycle-create"] = [
                ok({
                    "node_id": "I_parent_100",
                    "number": 100,
                    "html_url": "https://github.com/acme/demo/issues/100",
                    "body": "parent",
                    "id": 9100,
                }),
                TrackerError(ErrorClass.TRANSPORT, "child create failed",
                             subtype="timeout"),
            ]
            ex = fake_execute(responses)
            out = CP.project_chart(
                flow, "fn-10", event="chart.create",
                revision="rev-partial", evidence="evp", execute=ex,
            )
            self.assertIsInstance(out, TrackerError)
            # Parent identity persisted for reconcile
            chart = json.loads(
                (flow / "charts" / "fn-10.json").read_text(encoding="utf-8")
            )
            self.assertEqual(chart["tracker"]["id"], "I_parent_100")
            # Local chart status not rolled back
            self.assertEqual(chart["status"], "open")

    def test_claim_refresh_does_not_require_status_verb(self) -> None:
        """Claim/release may refresh body; never provider workflow status."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(
                flow,
                tracker={
                    "id": "I_parent_100",
                    "identifier": "#100",
                    "url": "https://github.com/acme/demo/issues/100",
                    "linkState": "linked",
                    "depRelations": [],
                    "projection": {"event_markers": []},
                },
                decisions=[{
                    "id": "fn-10.D1",
                    "title": "Pick storage",
                    "type": "research",
                    "attendance": "unattended",
                    "status": "open",
                    "claimed_by": "alice",
                    "claimed_at": "2026-01-02T00:00:00Z",
                    "n": 1,
                    "tracker": {
                        "id": "I_child_101",
                        "identifier": "#101",
                        "url": "https://github.com/acme/demo/issues/101",
                        "linkState": "linked",
                        "depRelations": [],
                    },
                }],
            )
            child = {
                "node_id": "I_child_101", "number": 101, "body": "c",
                "title": "t", "id": 9101,
            }
            parent = {
                "node_id": "I_parent_100", "number": 100, "body": "p",
                "title": "t", "id": 9100,
            }
            responses = {
                "wire-parent-read": [ok(dict(child)), ok(dict(parent))] * 4,
                "wire-read": [ok(dict(child)), ok(dict(parent))] * 4,
                "wire-update": [ok(dict(child)), ok(dict(parent))] * 4,
                # linked-branch hierarchy re-assertion (no marker yet)
                "relate-child-read": ok(dict(child)),
                "relate-create": ok({"ok": True}),
            }
            ex = fake_execute(responses)
            out = CP.project_chart(
                flow, "fn-10", event="chart.claim",
                revision="rev-claim", evidence="evc", execute=ex,
            )
            self.assertIsInstance(out, dict)
            self.assertTrue(out.get("projected"))
            ops = [c.op for c in ex.calls]
            self.assertNotIn("status-transition", ops)
            self.assertNotIn("status-apply", ops)


# ---------------------------------------------------------------------------
# Four-adapter capability contracts
# ---------------------------------------------------------------------------

class FourAdapterCapabilityTests(unittest.TestCase):
    def test_hierarchy_and_blocking_degradation_matrix(self) -> None:
        cases = [
            ("github", gh_cfg(), True, False),
            ("gitlab", gl_cfg(), False, True),
            ("linear", ln_cfg(), False, True),
            ("jira", jr_cfg(), False, True),
        ]
        for name, cfg, expect_sub, expect_block in cases:
            with self.subTest(provider=name):
                caps = cfg["tracker"]["resolved"]["capabilities"]
                self.assertEqual(bool(caps.get("subIssues")), expect_sub)
                self.assertEqual(bool(caps.get("blockedBy")), expect_block)
                # Hierarchy projection reports degradation when no subIssues
                # without needing a remote call.
                if not expect_sub:
                    hier = CP._project_hierarchy(
                        cfg, fake_execute({}),
                        parent_loc={"durable": "P", "display": "#1"},
                        child_loc={"durable": "C", "display": "#2"},
                        caps=caps,
                    )
                    self.assertIsInstance(hier, dict)
                    self.assertFalse(hier.get("projected"))
                    self.assertEqual(
                        (hier.get("degraded") or {}).get("capability"),
                        "subIssues",
                    )
                    self.assertEqual(
                        (hier.get("degraded") or {}).get("form"),
                        "flat_linked",
                    )
                # Blocking: github never; others have capability true (probe
                # is remote - we only assert the capability flag contract
                # here and the github local-provenance degradation).
                if name == "github":
                    blk = CP._project_blocking(
                        cfg, fake_execute({}),
                        from_loc={"durable": "A", "display": "#3"},
                        to_loc={"durable": "B", "display": "#4"},
                        caps=caps,
                        dep_subject="fn-10.D1",
                    )
                    self.assertIsInstance(blk, dict)
                    self.assertFalse(blk.get("projected"))
                    self.assertEqual(
                        (blk.get("degraded") or {}).get("capability"),
                        "blockedBy",
                    )
                    self.assertEqual(
                        (blk.get("degraded") or {}).get("form"),
                        "local_provenance",
                    )

    def test_depends_on_never_calls_blocking_provider(self) -> None:
        """depends_on is local provenance - projection code never treats it as blocks."""
        # Inspect build_decision_body only projects depends_on as body text.
        body = CP.build_decision_body({
            "id": "fn-10.D2",
            "title": "X",
            "type": "research",
            "attendance": "unattended",
            "status": "open",
            "blocked_by": [],
            "depends_on": ["fn-10.D1"],
        })
        self.assertIn("local provenance only", body)
        self.assertNotIn("Blocked by (local): fn-10.D1", body)


def _seed_linked_pair(flow: Path, **decision_extra) -> None:
    """Seed a chart + one decision, both already linked to remote issues."""
    _seed_chart(
        flow,
        tracker={
            "id": "I_parent_100",
            "identifier": "#100",
            "url": "https://github.com/acme/demo/issues/100",
            "linkState": "linked",
            "depRelations": [],
            "projection": {"event_markers": []},
        },
        decisions=[{
            "id": "fn-10.D1",
            "title": "Pick storage",
            "type": "research",
            "attendance": "unattended",
            "status": "open",
            "n": 1,
            "tracker": {
                "id": "I_child_101",
                "identifier": "#101",
                "url": "https://github.com/acme/demo/issues/101",
                "linkState": "linked",
                "depRelations": [],
            },
            **decision_extra,
        }],
    )


def _linked_refresh_responses(*, with_hierarchy: bool = True) -> dict:
    child = _gh_issue(node_id="I_child_101", number=101)
    parent = _gh_issue(node_id="I_parent_100", number=100)
    responses = {
        "wire-parent-read": [ok(dict(child)), ok(dict(parent))] * 4,
        "wire-read": [ok(dict(child)), ok(dict(parent))] * 4,
        "wire-update": [ok(dict(child)), ok(dict(parent))] * 4,
    }
    if with_hierarchy:
        responses["relate-child-read"] = ok(dict(child))
        responses["relate-create"] = ok({"ok": True})
    return responses


def _rewrite_decision_claim(flow: Path, claimed_by, claimed_at) -> None:
    dpath = flow / "charts" / "fn-10" / "1.json"
    data = json.loads(dpath.read_text(encoding="utf-8"))
    data["claimed_by"] = claimed_by
    data["claimed_at"] = claimed_at
    dpath.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _rewrite_decision_assets(flow: Path, assets: list[dict]) -> None:
    dpath = flow / "charts" / "fn-10" / "1.json"
    data = json.loads(dpath.read_text(encoding="utf-8"))
    data["assets"] = assets
    dpath.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Subject writes serialize with chart WAL transactions
# ---------------------------------------------------------------------------

class ProjectionChartLockTests(unittest.TestCase):
    def test_projection_link_write_waits_for_chart_resource_lock(self) -> None:
        """A projection sidecar write cannot interleave with a chart command's
        read-modify-write: while the chart resource lock is held, the tracker
        link write blocks; after the (stale) publish and release, the
        projection reloads and lands its link on top - nothing is lost."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(flow)
            chart_json = flow / "charts" / "fn-10.json"
            results: dict = {}

            def run_projection() -> None:
                ex = fake_execute(_gh_create_responses())
                results["out"] = CP.project_chart(
                    flow, "fn-10", event="chart.create",
                    revision="rev-lock", evidence="evl", execute=ex,
                )

            lock_path = flowctl.charts_resource_lock_path(flow)
            with flowctl.cross_process_lock(lock_path):
                t = threading.Thread(target=run_projection)
                t.start()
                time.sleep(0.4)
                # Deterministic: the link write REQUIRES the lock we hold, so
                # the sidecar cannot carry a tracker id yet.
                mid = json.loads(chart_json.read_text(encoding="utf-8"))
                self.assertIsNone((mid.get("tracker") or {}).get("id"))
                # Simulate the overlapped chart command publishing its staged
                # (pre-projection) JSON while still holding the lock.
                mid["title"] = "Tenancy chart (mutated)"
                chart_json.write_text(
                    json.dumps(mid, indent=2) + "\n", encoding="utf-8"
                )
            t.join(timeout=30)
            self.assertFalse(t.is_alive())
            out = results["out"]
            self.assertIsInstance(out, dict)
            self.assertTrue(out.get("projected"))
            after = json.loads(chart_json.read_text(encoding="utf-8"))
            # Both survive: the concurrent mutation AND the projection link.
            self.assertEqual(after["title"], "Tenancy chart (mutated)")
            self.assertEqual(after["tracker"]["id"], "I_parent_100")


# ---------------------------------------------------------------------------
# Remote read failure aborts the update step
# ---------------------------------------------------------------------------

class ReadFailureAbortsUpdateTests(unittest.TestCase):
    def test_child_read_error_aborts_without_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_linked_pair(flow)
            responses = _linked_refresh_responses()
            responses["wire-read"] = [
                TrackerError(ErrorClass.TRANSPORT, "read timed out",
                             subtype="timeout"),
            ]
            responses["wire-parent-read"] = [
                TrackerError(ErrorClass.TRANSPORT, "read timed out",
                             subtype="timeout"),
            ]
            ex = fake_execute(responses)
            out = CP.project_chart(
                flow, "fn-10", event="chart.claim",
                revision="rev-rf", evidence="evrf", execute=ex,
            )
            self.assertIsInstance(out, TrackerError)
            # Never update on top of an unread body.
            self.assertNotIn("wire-update", [c.op for c in ex.calls])
            # Retry with healthy reads converges.
            ex2 = fake_execute(_linked_refresh_responses())
            out2 = CP.project_chart(
                flow, "fn-10", event="chart.claim",
                revision="rev-rf", evidence="evrf", execute=ex2,
            )
            self.assertIsInstance(out2, dict)
            self.assertTrue(out2.get("projected"))
            self.assertIn("wire-update", [c.op for c in ex2.calls])


# ---------------------------------------------------------------------------
# Hierarchy retry for already-linked children
# ---------------------------------------------------------------------------

class HierarchyRetryTests(unittest.TestCase):
    def test_create_ok_hierarchy_fail_retry_converges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(flow)
            responses = _gh_create_responses()
            responses["relate-create"] = [
                TrackerError(ErrorClass.TRANSPORT, "hierarchy write failed",
                             subtype="timeout"),
            ]
            ex1 = fake_execute(responses)
            out1 = CP.project_chart(
                flow, "fn-10", event="chart.create",
                revision="rev-h", evidence="evh", execute=ex1,
            )
            self.assertIsInstance(out1, TrackerError)
            # Child is linked locally despite the hierarchy failure.
            child = json.loads(
                (flow / "charts" / "fn-10" / "1.json").read_text(encoding="utf-8")
            )
            self.assertEqual(child["tracker"]["id"], "I_child_101")
            # Retry (same event+revision; no marker was recorded) must
            # re-attempt hierarchy through the linked-child branch.
            ex2 = fake_execute(_linked_refresh_responses())
            out2 = CP.project_chart(
                flow, "fn-10", event="chart.create",
                revision="rev-h", evidence="evh", execute=ex2,
            )
            self.assertIsInstance(out2, dict)
            self.assertTrue(out2.get("projected"))
            self.assertIn(
                "hierarchy:fn-10.D1", out2.get("completed_steps") or [],
            )
            self.assertIn("relate-create", [c.op for c in ex2.calls])
            # Completion marker persisted on the decision ledger.
            child = json.loads(
                (flow / "charts" / "fn-10" / "1.json").read_text(encoding="utf-8")
            )
            keys = [
                e.get("key")
                for e in child["tracker"].get("depRelations") or []
            ]
            self.assertTrue(any(str(k).startswith("hier:") for k in keys))
            # Third projection (new revision): marker respected, no re-set.
            ex3 = fake_execute(_linked_refresh_responses(with_hierarchy=False))
            out3 = CP.project_chart(
                flow, "fn-10", event="chart.wire",
                revision="rev-h2", evidence="evh2", execute=ex3,
            )
            self.assertIsInstance(out3, dict)
            self.assertTrue(out3.get("projected"))
            self.assertNotIn("relate-create", [c.op for c in ex3.calls])


# ---------------------------------------------------------------------------
# Claim state is part of the projection marker revision
# ---------------------------------------------------------------------------

class ClaimRevisionTests(unittest.TestCase):
    def test_claim_release_claim_refreshes_each_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_linked_pair(
                flow,
                claimed_by="alice",
                claimed_at="2026-01-02T00:00:00Z",
            )
            chart_rev = "chart-rev-static"  # chart_decision_revision omits claims
            ex1 = fake_execute(_linked_refresh_responses())
            out1 = CP.project_chart(
                flow, "fn-10", event="chart.claim",
                revision=chart_rev, execute=ex1,
            )
            self.assertTrue(out1.get("projected"))
            self.assertFalse(out1.get("deduped"))
            # Release locally, project, then claim again (same chart revision).
            _rewrite_decision_claim(flow, None, None)
            ex2 = fake_execute(_linked_refresh_responses(with_hierarchy=False))
            out2 = CP.project_chart(
                flow, "fn-10", event="chart.release",
                revision=chart_rev, execute=ex2,
            )
            self.assertTrue(out2.get("projected"))
            _rewrite_decision_claim(flow, "alice", "2026-01-03T00:00:00Z")
            ex3 = fake_execute(_linked_refresh_responses(with_hierarchy=False))
            out3 = CP.project_chart(
                flow, "fn-10", event="chart.claim",
                revision=chart_rev, execute=ex3,
            )
            # The second claim must NOT dedupe against the first claim marker.
            self.assertIsInstance(out3, dict)
            self.assertFalse(out3.get("deduped"))
            self.assertTrue(out3.get("projected"))
            self.assertIn("wire-update", [c.op for c in ex3.calls])
            # Distinct marker revisions for the two claim events.
            chart = json.loads(
                (flow / "charts" / "fn-10.json").read_text(encoding="utf-8")
            )
            markers = chart["tracker"]["projection"]["event_markers"]
            claim_revs = {
                m["revision"] for m in markers if m["event"] == "chart.claim"
            }
            self.assertEqual(len(claim_revs), 2)


class AssetRevisionTests(unittest.TestCase):
    def test_attach_asset_reprojects_with_same_chart_revision(self) -> None:
        """Assets are sidecar-only (chart_decision_revision omits them);
        back-to-back attaches must not dedupe into a no-op, while an
        identical retry with unchanged assets still dedupes."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_linked_pair(flow)
            chart_rev = "chart-rev-static"
            ex1 = fake_execute(_linked_refresh_responses())
            out1 = CP.project_chart(
                flow, "fn-10", event="chart.attachAsset",
                revision=chart_rev, execute=ex1,
            )
            self.assertIsInstance(out1, dict)
            self.assertTrue(out1.get("projected"))
            self.assertFalse(out1.get("deduped"))
            # Attach evidence locally, then project again with the SAME
            # chart revision - the asset digest must force a refresh.
            _rewrite_decision_assets(flow, [{
                "kind": "prototype",
                "reference": "proto/tenancy.html",
                "summary": "clickable spike",
            }])
            ex2 = fake_execute(_linked_refresh_responses(with_hierarchy=False))
            out2 = CP.project_chart(
                flow, "fn-10", event="chart.attachAsset",
                revision=chart_rev, execute=ex2,
            )
            self.assertIsInstance(out2, dict)
            self.assertFalse(out2.get("deduped"))
            self.assertTrue(out2.get("projected"))
            self.assertIn("wire-update", [c.op for c in ex2.calls])
            # Unchanged assets: identical retry dedupes, zero remote calls.
            ex3 = fake_execute({})
            out3 = CP.project_chart(
                flow, "fn-10", event="chart.attachAsset",
                revision=chart_rev, execute=ex3,
            )
            self.assertTrue(out3.get("deduped"))
            self.assertEqual(ex3.calls, [])


# ---------------------------------------------------------------------------
# Locator frontier excludes blocked decisions
# ---------------------------------------------------------------------------

class LocateFrontierTests(unittest.TestCase):
    def test_blocked_decisions_excluded_from_history_frontier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(
                flow,
                decisions=[
                    {
                        "id": "fn-10.D1", "title": "Done", "type": "research",
                        "attendance": "unattended", "status": "resolved",
                        "answer": {"gist": "use postgres"}, "n": 1,
                    },
                    {
                        "id": "fn-10.D2", "title": "Next", "type": "research",
                        "attendance": "unattended", "status": "open", "n": 2,
                    },
                    {
                        "id": "fn-10.D3", "title": "Waiting", "type": "research",
                        "attendance": "unattended", "status": "open",
                        "blocked_by": ["fn-10.D2"], "n": 3,
                    },
                ],
            )
            out = CP.locate_selector(flow, "fn-10.D1")
            self.assertIsInstance(out, dict)
            self.assertEqual(out["status"], "resolved")
            frontier_ids = [f["id"] for f in out.get("frontier") or []]
            self.assertEqual(frontier_ids, ["fn-10.D2"])
            self.assertNotIn("fn-10.D3", frontier_ids)


# ---------------------------------------------------------------------------
# Created-but-unlinked identity recovery (link-write failure, then retry)
# ---------------------------------------------------------------------------

class IdentityRecoveryTests(unittest.TestCase):
    def test_link_write_failure_recovers_without_duplicate_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(flow)
            parent = _gh_issue(node_id="I_parent_100", number=100)
            real_write = CP.locked_subject_write

            def chart_writes_fail(flow_dir, kind, subject_id, mutate, **kw):
                if kind == "chart":
                    return TrackerError(
                        ErrorClass.CONFLICT,
                        "timed out acquiring chart resource lock",
                        subtype="lock_timeout",
                    )
                return real_write(flow_dir, kind, subject_id, mutate, **kw)

            ex1 = fake_execute({"lifecycle-create": [ok(dict(parent))]})
            with mock.patch.object(
                CP, "locked_subject_write", chart_writes_fail,
            ):
                out1 = CP.project_chart(
                    flow, "fn-10", event="chart.create",
                    revision="rev-rec", evidence="evrec", execute=ex1,
                )
            self.assertIsInstance(out1, TrackerError)
            # Created identity rides the error details (receipt evidence).
            self.assertEqual((out1.details or {}).get("id"), "I_parent_100")
            pending = flow / "create-first" / "chart-chart-fn-10.json"
            self.assertTrue(pending.is_file())
            # Retry: adopts the recorded identity - the ONLY remote create
            # is the child's (a second parent create would exhaust the
            # single-response list and fail loudly).
            child = _gh_issue(node_id="I_child_101", number=101)
            responses = _gh_create_responses()
            responses["lifecycle-create"] = [ok(dict(child))]
            ex2 = fake_execute(responses)
            out2 = CP.project_chart(
                flow, "fn-10", event="chart.create",
                revision="rev-rec", evidence="evrec", execute=ex2,
            )
            self.assertIsInstance(out2, dict)
            self.assertTrue(out2.get("projected"))
            creates = [c for c in ex2.calls if c.op == "lifecycle-create"]
            self.assertEqual(len(creates), 1)
            chart = json.loads(
                (flow / "charts" / "fn-10.json").read_text(encoding="utf-8")
            )
            self.assertEqual(chart["tracker"]["id"], "I_parent_100")
            self.assertEqual(out2["steps"]["create_parent"]["kind"], "adopted")
            self.assertIn("adopt-parent", out2.get("completed_steps") or [])
            self.assertFalse(pending.is_file())

    def test_transient_link_write_failure_retries_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, gh_cfg())
            _seed_chart(flow)
            real_write = CP.locked_subject_write
            failures = {"left": 1}

            def first_write_fails(flow_dir, kind, subject_id, mutate, **kw):
                if failures["left"] > 0:
                    failures["left"] -= 1
                    return TrackerError(
                        ErrorClass.CONFLICT,
                        "timed out acquiring chart resource lock",
                        subtype="lock_timeout",
                    )
                return real_write(flow_dir, kind, subject_id, mutate, **kw)

            ex = fake_execute(_gh_create_responses())
            with mock.patch.object(
                CP, "locked_subject_write", first_write_fails,
            ):
                out = CP.project_chart(
                    flow, "fn-10", event="chart.create",
                    revision="rev-tr", evidence="evtr", execute=ex,
                )
            self.assertIsInstance(out, dict)
            self.assertTrue(out.get("projected"))
            self.assertEqual(out["steps"]["create_parent"]["kind"], "created")
            self.assertFalse(
                (flow / "create-first" / "chart-chart-fn-10.json").is_file()
            )


# ---------------------------------------------------------------------------
# Blocking edges project in a second pass over the fully-linked child set
# ---------------------------------------------------------------------------

def _ln_issue(iid: str, ident: str) -> dict:
    return {
        "id": iid, "identifier": ident,
        "url": f"https://linear.app/acme/issue/{ident}",
        "title": "t", "description": "b",
        "state": {"id": "st", "name": "Todo", "type": "unstarted"},
        "labels": {"nodes": []},
    }


def _ln_create(issue: dict):
    return ok({"data": {"issueCreate": {"success": True, "issue": dict(issue)}}})


def _ln_read(issue: dict):
    return ok({"data": {"issue": dict(issue)}})


def _ln_update(issue: dict):
    return ok({"data": {"issueUpdate": {"success": True, "issue": dict(issue)}}})


def _ln_no_edges(iid: str):
    empty_conn = {"nodes": [], "pageInfo": {"hasNextPage": False}}
    return ok({"data": {"issue": {
        "id": iid, "relations": dict(empty_conn),
        "inverseRelations": dict(empty_conn),
    }}})


class TwoPassBlockingTests(unittest.TestCase):
    def test_initial_map_projects_edge_blocked_by_later_decision(self) -> None:
        """D1 blocked_by D2 on the INITIAL projection: the edge must land
        even though D2 has no locator while D1 is being created."""
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, ln_cfg())
            _seed_chart(
                flow,
                decisions=[
                    {
                        "id": "fn-10.D1", "title": "Blocked first",
                        "type": "research", "attendance": "unattended",
                        "status": "open", "blocked_by": ["fn-10.D2"], "n": 1,
                    },
                    {
                        "id": "fn-10.D2", "title": "Later blocker",
                        "type": "research", "attendance": "unattended",
                        "status": "open", "n": 2,
                    },
                ],
            )
            parent = _ln_issue("lin-parent", "WOR-1")
            d1 = _ln_issue("lin-d1", "WOR-2")
            d2 = _ln_issue("lin-d2", "WOR-3")
            responses = {
                "lifecycle-create": [
                    _ln_create(parent), _ln_create(d1), _ln_create(d2),
                ],
                # edge probe: no existing relation on D1
                "relate-list": [_ln_no_edges("lin-d1")],
                "relate-create": ok({"data": {"issueRelationCreate": {
                    "success": True, "issueRelation": {"id": "rel-1"},
                }}}),
                "wire-read": [_ln_read(parent)],
                "wire-parent-read": [_ln_read(parent)],
                "wire-update": [_ln_update(parent)],
            }
            ex = fake_execute(responses)
            out = CP.project_chart(
                flow, "fn-10", event="chart.create",
                revision="rev-2p", evidence="ev2p", execute=ex,
            )
            self.assertIsInstance(out, dict)
            self.assertTrue(out.get("projected"))
            self.assertIn(
                "blocks:fn-10.D1->fn-10.D2", out.get("completed_steps") or [],
            )
            rel_creates = [c for c in ex.calls if c.op == "relate-create"]
            self.assertEqual(len(rel_creates), 1)
            # Edge landed on the SAME initial projection - ledger recorded.
            d1_json = json.loads(
                (flow / "charts" / "fn-10" / "1.json").read_text(encoding="utf-8")
            )
            entries = d1_json["tracker"].get("depRelations") or []
            self.assertTrue(any(
                e.get("from_tracker_id") == "lin-d1"
                and e.get("to_tracker_id") == "lin-d2"
                and e.get("type") == "blocks"
                for e in entries
            ))


# ---------------------------------------------------------------------------
# Stale flow-owned native blocking relations are removed on rewire
# ---------------------------------------------------------------------------

def _seed_linear_linked_rewired(flow: Path) -> str:
    """Chart + D1 + D2 all linked; D1's ledger still owns a blocks edge to D2
    that blocked_by no longer lists (wire-decision cleared it)."""
    stale_key = CP.dep_relation_key("lin-d1", "lin-d2")
    _seed_chart(
        flow,
        tracker={
            "id": "lin-parent", "identifier": "WOR-1",
            "url": "https://linear.app/acme/issue/WOR-1",
            "linkState": "linked", "depRelations": [],
            "projection": {"event_markers": []},
        },
        decisions=[
            {
                "id": "fn-10.D1", "title": "Rewired", "type": "research",
                "attendance": "unattended", "status": "open",
                "blocked_by": [], "n": 1,
                "tracker": {
                    "id": "lin-d1", "identifier": "WOR-2",
                    "url": "https://linear.app/acme/issue/WOR-2",
                    "linkState": "linked",
                    "depRelations": [{
                        "key": stale_key,
                        "dep_spec": "fn-10.D2",
                        "from_tracker_id": "lin-d1",
                        "to_tracker_id": "lin-d2",
                        "type": "blocks",
                        "source": "flow",
                        "updatedAt": "2026-01-01T00:00:00Z",
                    }],
                },
            },
            {
                "id": "fn-10.D2", "title": "Old blocker", "type": "research",
                "attendance": "unattended", "status": "open", "n": 2,
                "tracker": {
                    "id": "lin-d2", "identifier": "WOR-3",
                    "url": "https://linear.app/acme/issue/WOR-3",
                    "linkState": "linked", "depRelations": [],
                },
            },
        ],
    )
    return stale_key


def _ln_linked_refresh_responses() -> dict:
    parent = _ln_issue("lin-parent", "WOR-1")
    d1 = _ln_issue("lin-d1", "WOR-2")
    d2 = _ln_issue("lin-d2", "WOR-3")
    return {
        "wire-read": [_ln_read(d1), _ln_read(d2), _ln_read(parent)],
        "wire-parent-read": [_ln_read(d1), _ln_read(d2), _ln_read(parent)],
        "wire-update": [_ln_update(d1), _ln_update(d2), _ln_update(parent)],
    }


class StaleRelationRemovalTests(unittest.TestCase):
    def test_rewire_removes_stale_native_relation_and_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow = Path(tmp)
            _write_config(flow, ln_cfg())
            _seed_linear_linked_rewired(flow)
            responses = _ln_linked_refresh_responses()
            responses["relate-list"] = [ok({"data": {"issue": {
                "id": "lin-d1",
                "inverseRelations": {
                    "nodes": [{
                        "id": "rel-9", "type": "blocks",
                        "issue": {"id": "lin-d2"},
                    }],
                    "pageInfo": {"hasNextPage": False},
                },
            }}})]
            responses["relate-delete"] = ok({"data": {
                "issueRelationDelete": {"success": True},
            }})
            ex = fake_execute(responses)
            out = CP.project_chart(
                flow, "fn-10", event="chart.wire",
                revision="rev-rm", evidence="evrm", execute=ex,
            )
            self.assertIsInstance(out, dict)
            self.assertTrue(out.get("projected"))
            self.assertIn("relate-delete", [c.op for c in ex.calls])
            self.assertIn(
                "unblock:fn-10.D1-x>fn-10.D2",
                out.get("completed_steps") or [],
            )
            d1_json = json.loads(
                (flow / "charts" / "fn-10" / "1.json").read_text(encoding="utf-8")
            )
            self.assertEqual(d1_json["tracker"].get("depRelations") or [], [])
            # Converged: the next projection performs no relation work at all.
            ex2 = fake_execute(_ln_linked_refresh_responses())
            out2 = CP.project_chart(
                flow, "fn-10", event="chart.wire",
                revision="rev-rm2", evidence="evrm2", execute=ex2,
            )
            self.assertTrue(out2.get("projected"))
            ops2 = [c.op for c in ex2.calls]
            self.assertNotIn("relate-list", ops2)
            self.assertNotIn("relate-delete", ops2)

    def test_removal_capability_gates(self) -> None:
        # GitHub never projected native blocking - nothing remote to remove.
        gh = gh_cfg()
        out = CP._remove_blocking(
            gh, fake_execute({}),
            from_loc={"durable": "A", "display": "#3"}, to_id="B",
            caps=gh["tracker"]["resolved"]["capabilities"],
        )
        self.assertEqual(out, {"removed": False, "already_absent": True})
        # A provider without blockedBy reports explicit degradation and the
        # caller keeps the ledger entry.
        gl = gl_cfg()
        gl["tracker"]["resolved"]["capabilities"]["blockedBy"] = False
        ex = fake_execute({})
        out = CP._remove_blocking(
            gl, ex,
            from_loc={"durable": "A", "display": "g/p#3"}, to_id="B",
            caps=gl["tracker"]["resolved"]["capabilities"],
        )
        self.assertFalse(out.get("removed"))
        self.assertEqual(
            (out.get("degraded") or {}).get("capability"), "blockedBy",
        )
        self.assertEqual(
            (out.get("degraded") or {}).get("form"), "stale_native_relation",
        )
        self.assertEqual(ex.calls, [])


# ---------------------------------------------------------------------------
# Caller inventory presence
# ---------------------------------------------------------------------------

class ChartCallerInventoryTests(unittest.TestCase):
    def test_chart_in_oracle_and_skill_gate(self) -> None:
        oracle_path = (
            Path(__file__).parent
            / "fixtures"
            / "tracker_callers"
            / "oracle-410756ef8f27d14c3cfbcbffe66356c67fd255ad.json"
        )
        oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
        ids = {c["id"] for c in oracle["callers"]}
        self.assertIn("chart", ids)
        chart = next(c for c in oracle["callers"] if c["id"] == "chart")
        self.assertEqual(chart["config_key"], "tracker.charts")
        self.assertEqual(chart["resolved_facade_op"], "push")
        skill = (
            ROOT / "skills" / "flow-next-chart" / "workflow.md"
        ).read_text(encoding="utf-8")
        self.assertIn("tracker.charts", skill)
        self.assertIn("sync active --json", skill)
        self.assertIn("tracker sync", skill)
        self.assertIn("--event chart", skill)


if __name__ == "__main__":
    unittest.main()
