"""Unit tests for chart graph, frontier, parked questions, and claims (fn-135.9).

Covers: add-decision + record files, graph validation, frontier (blocked_by vs
depends_on), claim/release/break-stale, park/remove-question, completion
predicates, initial-map maxDecisions + force-size audit, config defaults,
exact v1 envelopes, and compact navigation reads (no answer/assets load).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
FLOWCTL_PY = ROOT / "scripts" / "flowctl.py"

spec = importlib.util.spec_from_file_location("flowctl", ROOT / "scripts" / "flowctl.py")
flowctl = importlib.util.module_from_spec(spec)
sys.modules["flowctl"] = flowctl
spec.loader.exec_module(flowctl)


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "chart-test@example.com")
    _git(repo, "config", "user.name", "chart-test")
    _git(repo, "config", "commit.gpgsign", "false")


def _init_flow(repo: Path) -> Path:
    r = subprocess.run(
        [sys.executable, str(FLOWCTL_PY), "init"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(f"flowctl init failed: {r.stderr}\n{r.stdout}")
    return repo / ".flow"


def _run_flowctl(
    cwd: Path, *args: str, env: dict | None = None
) -> subprocess.CompletedProcess:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    full_env.setdefault("FLOWCTL_CHART_FAILPOINT", "")
    if env is None or "FLOWCTL_CHART_FAILPOINT" not in env:
        full_env.pop("FLOWCTL_CHART_FAILPOINT", None)
    return subprocess.run(
        [sys.executable, str(FLOWCTL_PY), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        env=full_env,
    )


def _create_chart(repo: Path, title: str = "Tenant isolation", outcome: str = "Ready") -> str:
    r = _run_flowctl(
        repo,
        "chart",
        "create",
        "--title",
        title,
        "--outcome",
        outcome,
        "--json",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    return json.loads(r.stdout)["result"]["id"]


def _add_decision(
    repo: Path,
    chart_id: str,
    title: str,
    dtype: str = "research",
    *,
    attendance: str | None = None,
    blocked_by: str | None = None,
    depends_on: str | None = None,
    body_file: Path | None = None,
    env: dict | None = None,
) -> dict:
    args = [
        "chart",
        "add-decision",
        chart_id,
        "--title",
        title,
        "--type",
        dtype,
        "--json",
    ]
    if attendance is not None:
        args.extend(["--attendance", attendance])
    if blocked_by is not None:
        args.extend(["--blocked-by", blocked_by])
    if depends_on is not None:
        args.extend(["--depends-on", depends_on])
    if body_file is not None:
        args.extend(["--body-file", str(body_file)])
    r = _run_flowctl(repo, *args, env=env)
    assert r.returncode == 0, r.stderr + r.stdout
    env_out = json.loads(r.stdout)
    assert env_out["success"] is True
    assert env_out["command"] == "chart.add-decision"
    return env_out["result"]


def _backdate_claim(flow: Path, chart_id: str, did: str, hours: float = 25.0) -> str:
    """Mutate claimed_at on chart + decision sidecars for stale-break tests."""
    old = (
        datetime.now(timezone.utc) - timedelta(hours=hours)
    ).isoformat().replace("+00:00", "Z")
    chart_path = flow / "charts" / f"{chart_id}.json"
    chart = json.loads(chart_path.read_text(encoding="utf-8"))
    for d in chart.get("decisions") or []:
        if d.get("id") == did:
            d["claimed_at"] = old
    chart_path.write_text(json.dumps(chart, indent=2) + "\n", encoding="utf-8")
    n = int(did.rsplit("D", 1)[1])
    dpath = flow / "charts" / chart_id / f"{n}.json"
    dside = json.loads(dpath.read_text(encoding="utf-8"))
    dside["claimed_at"] = old
    dpath.write_text(json.dumps(dside, indent=2) + "\n", encoding="utf-8")
    return old


class TestAddDecisionAndRecords(unittest.TestCase):
    def test_add_decision_returns_id_title_attendance_and_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)

            r = _run_flowctl(
                repo,
                "chart",
                "add-decision",
                chart_id,
                "--title",
                "Choose tenant key",
                "--type",
                "research",
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            env = json.loads(r.stdout)
            self.assertEqual(
                env,
                {
                    "success": True,
                    "schema_version": 1,
                    "command": "chart.add-decision",
                    "result": env["result"],
                },
            )
            result = env["result"]
            self.assertEqual(result["id"], f"{chart_id}.D1")
            self.assertEqual(result["title"], "Choose tenant key")
            self.assertEqual(result["type"], "research")
            self.assertEqual(result["attendance"], "unattended")
            self.assertEqual(result["status"], "open")
            self.assertEqual(result["record_path"], f".flow/charts/{chart_id}/1.md")
            self.assertEqual(result["chart"], chart_id)
            self.assertEqual(result["blocked_by"], [])
            self.assertEqual(result["depends_on"], [])

            md = flow / "charts" / chart_id / "1.md"
            js = flow / "charts" / chart_id / "1.json"
            self.assertTrue(md.is_file())
            self.assertTrue(js.is_file())
            body = md.read_text(encoding="utf-8")
            self.assertIn("## Question", body)
            self.assertIn("Choose tenant key", body)
            side = json.loads(js.read_text(encoding="utf-8"))
            self.assertEqual(side["id"], f"{chart_id}.D1")
            self.assertEqual(side["title"], "Choose tenant key")
            self.assertEqual(side["attendance"], "unattended")
            self.assertIsNone(side["answer"])
            self.assertEqual(side["assets"], [])
            self.assertIsNone(side["claimed_by"])

            chart_side = json.loads(
                (flow / "charts" / f"{chart_id}.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(chart_side["decisions"]), 1)
            self.assertEqual(chart_side["decisions"][0]["id"], f"{chart_id}.D1")
            # Compact chart entry: no answer/assets.
            self.assertNotIn("answer", chart_side["decisions"][0])
            self.assertNotIn("assets", chart_side["decisions"][0])

    def test_derived_attendance_for_five_types_and_task_requires_explicit(self) -> None:
        expected = {
            "research": "unattended",
            "probe": "unattended",
            "eval": "unattended",
            "prototype": "attended",
            "interview": "attended",
        }
        for dtype, att in expected.items():
            self.assertEqual(flowctl.derive_decision_attendance(dtype), att)

        with self.assertRaises(flowctl.ChartError) as ctx:
            flowctl.derive_decision_attendance("task")
        self.assertEqual(ctx.exception.code, "attendance_required")

        self.assertEqual(
            flowctl.derive_decision_attendance("task", "attended"), "attended"
        )
        self.assertEqual(
            flowctl.derive_decision_attendance("task", "unattended"), "unattended"
        )

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)

            bad = _run_flowctl(
                repo,
                "chart",
                "add-decision",
                chart_id,
                "--title",
                "Human approval",
                "--type",
                "task",
                "--json",
            )
            self.assertNotEqual(bad.returncode, 0)
            err = json.loads(bad.stdout)
            self.assertEqual(err["error"]["class"], "validation")
            self.assertEqual(err["error"]["code"], "attendance_required")

            human = _add_decision(
                repo,
                chart_id,
                "Human approval",
                "task",
                attendance="attended",
            )
            self.assertEqual(human["attendance"], "attended")
            export = _add_decision(
                repo,
                chart_id,
                "Scripted export",
                "task",
                attendance="unattended",
            )
            self.assertEqual(export["attendance"], "unattended")

    def test_sequential_d_ids_and_body_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            q = repo / "q.md"
            q.write_text("What key scheme?\n", encoding="utf-8")
            d1 = _add_decision(
                repo, chart_id, "Key scheme", "research", body_file=q
            )
            d2 = _add_decision(repo, chart_id, "Store choice", "prototype")
            self.assertEqual(d1["id"], f"{chart_id}.D1")
            self.assertEqual(d2["id"], f"{chart_id}.D2")
            body = (flow / "charts" / chart_id / "1.md").read_text(encoding="utf-8")
            self.assertIn("What key scheme?", body)
            side = json.loads(
                (flow / "charts" / chart_id / "1.json").read_text(encoding="utf-8")
            )
            self.assertEqual(side["question"].strip(), "What key scheme?")

    def test_human_decision_line_pairs_title_id_link(self) -> None:
        line = flowctl.human_decision_line(
            {
                "id": "fn-3.D2",
                "title": "Pick store",
                "record_path": ".flow/charts/fn-3/2.md",
            }
        )
        self.assertEqual(line, "fn-3.D2  Pick store  .flow/charts/fn-3/2.md")


class TestGraphValidation(unittest.TestCase):
    def test_rejects_missing_self_duplicate_and_cycle_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "A")
            d2 = _add_decision(repo, chart_id, "B")
            d3 = _add_decision(repo, chart_id, "C")

            # Self-edge
            r = _run_flowctl(
                repo,
                "chart",
                "wire-decision",
                d1["id"],
                "--blocked-by",
                d1["id"],
                "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)
            self.assertEqual(err["success"], False)
            self.assertEqual(err["schema_version"], 1)
            self.assertEqual(err["command"], "chart.wire-decision")
            self.assertEqual(err["error"]["class"], "invalid_graph")
            self.assertEqual(err["error"]["code"], "self_edge")

            # Missing target
            r = _run_flowctl(
                repo,
                "chart",
                "wire-decision",
                d1["id"],
                "--blocked-by",
                f"{chart_id}.D99",
                "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)
            self.assertEqual(err["error"]["class"], "invalid_graph")
            self.assertEqual(err["error"]["code"], "missing_edge_target")

            # Duplicate edge
            r = _run_flowctl(
                repo,
                "chart",
                "wire-decision",
                d2["id"],
                "--blocked-by",
                f"{d1['id']},{d1['id']}",
                "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)
            self.assertEqual(err["error"]["class"], "invalid_graph")
            self.assertEqual(err["error"]["code"], "duplicate_edge")

            # Cycle: D2 -> D3 -> D2
            ok = _run_flowctl(
                repo,
                "chart",
                "wire-decision",
                d2["id"],
                "--blocked-by",
                d3["id"],
                "--json",
            )
            self.assertEqual(ok.returncode, 0, ok.stderr)
            r = _run_flowctl(
                repo,
                "chart",
                "wire-decision",
                d3["id"],
                "--blocked-by",
                d2["id"],
                "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)
            self.assertEqual(err["error"]["class"], "invalid_graph")
            self.assertEqual(err["error"]["code"], "cycle")

            # Valid wire persists both edge sets atomically
            r = _run_flowctl(
                repo,
                "chart",
                "wire-decision",
                d2["id"],
                "--blocked-by",
                d1["id"],
                "--depends-on",
                d3["id"],
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            env = json.loads(r.stdout)
            self.assertEqual(env["command"], "chart.wire-decision")
            self.assertEqual(env["result"]["blocked_by"], [d1["id"]])
            self.assertEqual(env["result"]["depends_on"], [d3["id"]])

    def test_validate_chart_graph_in_process(self) -> None:
        decisions = [
            {
                "id": "fn-1.D1",
                "blocked_by": [],
                "depends_on": [],
            },
            {
                "id": "fn-1.D2",
                "blocked_by": ["fn-1.D1"],
                "depends_on": ["fn-1.D1"],
            },
        ]
        flowctl.validate_chart_graph(decisions)  # no raise

        bad = [
            {"id": "fn-1.D1", "blocked_by": ["fn-1.D1"], "depends_on": []},
        ]
        with self.assertRaises(flowctl.ChartError) as ctx:
            flowctl.validate_chart_graph(bad)
        self.assertEqual(ctx.exception.error_class, "invalid_graph")
        self.assertEqual(ctx.exception.code, "self_edge")


class TestFrontierBlockedVsDepends(unittest.TestCase):
    def test_blocked_by_controls_readiness_depends_on_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Premise")
            d2 = _add_decision(repo, chart_id, "Ready-via-depends")
            d3 = _add_decision(repo, chart_id, "Blocked")

            # depends_on only: D2 still on frontier
            r = _run_flowctl(
                repo,
                "chart",
                "wire-decision",
                d2["id"],
                "--depends-on",
                d1["id"],
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr)

            # blocked_by: D3 off frontier
            r = _run_flowctl(
                repo,
                "chart",
                "wire-decision",
                d3["id"],
                "--blocked-by",
                d1["id"],
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr)

            fr = _run_flowctl(repo, "chart", "frontier", chart_id, "--json")
            self.assertEqual(fr.returncode, 0, fr.stderr)
            env = json.loads(fr.stdout)
            self.assertEqual(env["success"], True)
            self.assertEqual(env["schema_version"], 1)
            self.assertEqual(env["command"], "chart.frontier")
            ids = [d["id"] for d in env["result"]["frontier"]]
            self.assertIn(d1["id"], ids)
            self.assertIn(d2["id"], ids)  # depends_on is not readiness
            self.assertNotIn(d3["id"], ids)  # blocked_by is readiness
            self.assertEqual(env["result"]["count"], len(ids))
            self.assertFalse(env["result"]["briefable"])
            # Compact frontier entries
            for d in env["result"]["frontier"]:
                self.assertIn("title", d)
                self.assertIn("record_path", d)
                self.assertNotIn("answer", d)
                self.assertNotIn("assets", d)
                self.assertNotIn("question", d)

    def test_claimed_decision_excluded_from_frontier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "A")
            d2 = _add_decision(repo, chart_id, "B")
            claim = _run_flowctl(
                repo,
                "chart",
                "claim",
                d1["id"],
                "--json",
                env={"FLOW_ACTOR": "alice"},
            )
            self.assertEqual(claim.returncode, 0, claim.stderr)
            fr = _run_flowctl(repo, "chart", "frontier", chart_id, "--json")
            self.assertEqual(fr.returncode, 0, fr.stderr)
            ids = [d["id"] for d in json.loads(fr.stdout)["result"]["frontier"]]
            self.assertEqual(ids, [d2["id"]])

    def test_frontier_dependency_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "First")
            d2 = _add_decision(repo, chart_id, "Second")
            d3 = _add_decision(repo, chart_id, "Third")
            # All unblocked: allocation order (local number)
            fr = _run_flowctl(repo, "chart", "frontier", chart_id, "--json")
            ids = [d["id"] for d in json.loads(fr.stdout)["result"]["frontier"]]
            self.assertEqual(ids, [d1["id"], d2["id"], d3["id"]])


class TestClaimReleaseBreakStale(unittest.TestCase):
    def test_claim_conflict_and_status_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Work item")

            r = _run_flowctl(
                repo,
                "chart",
                "claim",
                d1["id"],
                "--json",
                env={"FLOW_ACTOR": "alice"},
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            env = json.loads(r.stdout)
            self.assertEqual(env["command"], "chart.claim")
            result = env["result"]
            self.assertEqual(result["id"], d1["id"])
            self.assertEqual(result["claimed_by"], "alice")
            self.assertEqual(result["status"], "open")  # claim never changes status
            self.assertIsNotNone(result["claimed_at"])
            self.assertFalse(result["noop"])

            dside = json.loads(
                (flow / "charts" / chart_id / "1.json").read_text(encoding="utf-8")
            )
            self.assertEqual(dside["status"], "open")
            self.assertEqual(dside["claimed_by"], "alice")

            # Second actor: conflict (distinguishable class/code)
            r2 = _run_flowctl(
                repo,
                "chart",
                "claim",
                d1["id"],
                "--json",
                env={"FLOW_ACTOR": "bob"},
            )
            self.assertNotEqual(r2.returncode, 0)
            err = json.loads(r2.stdout)
            self.assertEqual(err["success"], False)
            self.assertEqual(err["command"], "chart.claim")
            self.assertEqual(err["error"]["class"], "conflict")
            self.assertEqual(err["error"]["code"], "claim_conflict")
            self.assertEqual(err["error"]["details"]["claimed_by"], "alice")
            self.assertEqual(err["error"]["details"]["actor"], "bob")

            # Same owner re-claim is noop
            r3 = _run_flowctl(
                repo,
                "chart",
                "claim",
                d1["id"],
                "--json",
                env={"FLOW_ACTOR": "alice"},
            )
            self.assertEqual(r3.returncode, 0, r3.stderr)
            self.assertTrue(json.loads(r3.stdout)["result"]["noop"])

    def test_owner_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Work item")
            _run_flowctl(
                repo,
                "chart",
                "claim",
                d1["id"],
                "--json",
                env={"FLOW_ACTOR": "alice"},
            )

            # Non-owner without break-stale -> conflict
            bad = _run_flowctl(
                repo,
                "chart",
                "release-claim",
                d1["id"],
                "--json",
                env={"FLOW_ACTOR": "bob"},
            )
            self.assertNotEqual(bad.returncode, 0)
            err = json.loads(bad.stdout)
            self.assertEqual(err["error"]["class"], "conflict")
            self.assertEqual(err["error"]["code"], "claim_conflict")

            ok = _run_flowctl(
                repo,
                "chart",
                "release-claim",
                d1["id"],
                "--json",
                env={"FLOW_ACTOR": "alice"},
            )
            self.assertEqual(ok.returncode, 0, ok.stderr)
            env = json.loads(ok.stdout)
            self.assertEqual(env["command"], "chart.release-claim")
            self.assertTrue(env["result"]["released"])
            self.assertEqual(env["result"]["prior_owner"], "alice")
            self.assertEqual(env["result"]["status"], "open")

            dside = json.loads(
                (flow / "charts" / chart_id / "1.json").read_text(encoding="utf-8")
            )
            self.assertIsNone(dside["claimed_by"])
            self.assertIsNone(dside["claimed_at"])
            self.assertEqual(dside["status"], "open")

    def test_break_stale_age_gated_and_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Work item")
            _run_flowctl(
                repo,
                "chart",
                "claim",
                d1["id"],
                "--json",
                env={"FLOW_ACTOR": "alice"},
            )

            # Fresh claim: break-stale fails with stale_claim class
            young = _run_flowctl(
                repo,
                "chart",
                "release-claim",
                d1["id"],
                "--break-stale",
                "--reason",
                "take over",
                "--json",
                env={"FLOW_ACTOR": "bob"},
            )
            self.assertNotEqual(young.returncode, 0)
            err = json.loads(young.stdout)
            self.assertEqual(err["error"]["class"], "stale_claim")
            self.assertEqual(err["error"]["code"], "claim_not_stale")

            # Missing reason
            _backdate_claim(flow, chart_id, d1["id"], hours=25.0)
            no_reason = _run_flowctl(
                repo,
                "chart",
                "release-claim",
                d1["id"],
                "--break-stale",
                "--json",
                env={"FLOW_ACTOR": "bob"},
            )
            self.assertNotEqual(no_reason.returncode, 0)
            err = json.loads(no_reason.stdout)
            self.assertEqual(err["error"]["class"], "validation")
            self.assertEqual(err["error"]["code"], "break_stale_reason_required")

            ok = _run_flowctl(
                repo,
                "chart",
                "release-claim",
                d1["id"],
                "--break-stale",
                "--reason",
                "owner offline",
                "--json",
                env={"FLOW_ACTOR": "bob"},
            )
            self.assertEqual(ok.returncode, 0, ok.stderr)
            env = json.loads(ok.stdout)
            self.assertEqual(env["command"], "chart.release-claim")
            audit = env["result"]["audit"]
            self.assertIsNotNone(audit)
            self.assertEqual(audit["actor"], "bob")
            self.assertEqual(audit["prior_owner"], "alice")
            self.assertEqual(audit["reason"], "owner offline")
            self.assertEqual(audit["kind"], "break_stale")
            self.assertEqual(audit["decision"], d1["id"])
            self.assertGreaterEqual(audit["age_hours"], 24.0)
            self.assertIn("timestamp", audit)

            # Persisted on chart claim_events
            chart = json.loads(
                (flow / "charts" / f"{chart_id}.json").read_text(encoding="utf-8")
            )
            events = chart.get("claim_events") or []
            self.assertTrue(any(e.get("kind") == "break_stale" for e in events))
            dside = json.loads(
                (flow / "charts" / chart_id / "1.json").read_text(encoding="utf-8")
            )
            self.assertIsNone(dside["claimed_by"])
            notes = dside.get("transition_notes") or []
            self.assertTrue(any(n.get("kind") == "break_stale" for n in notes))


class TestParkQuestion(unittest.TestCase):
    def test_park_idempotent_remove_and_body_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            qf = repo / "park.txt"
            qf.write_text("  What about   multi   space?  \n", encoding="utf-8")

            r = _run_flowctl(
                repo,
                "chart",
                "park-question",
                chart_id,
                "--body-file",
                str(qf),
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            env = json.loads(r.stdout)
            self.assertEqual(env["command"], "chart.park-question")
            result = env["result"]
            self.assertEqual(result["chart_id"], chart_id)
            self.assertEqual(result["body"], "What about multi space?")
            self.assertFalse(result["noop"])
            key = result["key"]
            self.assertEqual(len(key), 16)
            self.assertEqual(key, flowctl.parked_question_key("What about multi space?"))

            # Open Questions section updated
            md = (flow / "charts" / f"{chart_id}.md").read_text(encoding="utf-8")
            self.assertIn("What about multi space?", md)

            # Identical retry is noop
            r2 = _run_flowctl(
                repo,
                "chart",
                "park-question",
                chart_id,
                "--body-file",
                str(qf),
                "--json",
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertTrue(json.loads(r2.stdout)["result"]["noop"])
            self.assertEqual(json.loads(r2.stdout)["result"]["key"], key)

            chart = json.loads(
                (flow / "charts" / f"{chart_id}.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(chart["parked_questions"]), 1)

            rm = _run_flowctl(
                repo,
                "chart",
                "remove-question",
                chart_id,
                "--question",
                key,
                "--json",
            )
            self.assertEqual(rm.returncode, 0, rm.stderr)
            env = json.loads(rm.stdout)
            self.assertEqual(env["command"], "chart.remove-question")
            self.assertTrue(env["result"]["removed"])
            self.assertEqual(env["result"]["key"], key)

            chart = json.loads(
                (flow / "charts" / f"{chart_id}.json").read_text(encoding="utf-8")
            )
            self.assertEqual(chart["parked_questions"], [])
            md = (flow / "charts" / f"{chart_id}.md").read_text(encoding="utf-8")
            self.assertNotIn("What about multi space?", md)

            # Missing key
            missing = _run_flowctl(
                repo,
                "chart",
                "remove-question",
                chart_id,
                "--question",
                key,
                "--json",
            )
            self.assertNotEqual(missing.returncode, 0)
            err = json.loads(missing.stdout)
            self.assertEqual(err["error"]["class"], "not_found")
            self.assertEqual(err["error"]["code"], "parked_question_not_found")


class TestCompletionPredicates(unittest.TestCase):
    def test_empty_chart_briefable(self) -> None:
        pred = flowctl.chart_completion_predicate(
            {"decisions": [], "parked_questions": []}
        )
        self.assertTrue(pred["briefable"])
        self.assertEqual(pred["stuck_reasons"], [])
        self.assertEqual(pred["open_count"], 0)

    def test_open_unblocked_not_briefable(self) -> None:
        pred = flowctl.chart_completion_predicate(
            {
                "decisions": [
                    {
                        "id": "fn-1.D1",
                        "status": "open",
                        "blocked_by": [],
                        "claimed_by": None,
                    }
                ],
                "parked_questions": [],
            }
        )
        self.assertFalse(pred["briefable"])
        self.assertEqual(pred["frontier_ids"], ["fn-1.D1"])

    def test_blocked_only_and_claimed_only_are_stuck_not_complete(self) -> None:
        # Blocked-only: open decisions all blocked by another open decision
        blocked_only = {
            "decisions": [
                {
                    "id": "fn-1.D1",
                    "status": "open",
                    "blocked_by": [],
                    "claimed_by": "alice",  # claimed so not on frontier
                },
                {
                    "id": "fn-1.D2",
                    "status": "open",
                    "blocked_by": ["fn-1.D1"],
                    "claimed_by": None,
                },
            ],
            "parked_questions": [],
        }
        pred = flowctl.chart_completion_predicate(blocked_only)
        self.assertFalse(pred["briefable"])
        self.assertIn("fn-1.D2", pred["blocked_open_ids"])
        self.assertIn("fn-1.D1", pred["claimed_open_ids"])
        self.assertEqual(pred["frontier_ids"], [])

        # Claimed-only: single open claimed decision
        claimed_only = {
            "decisions": [
                {
                    "id": "fn-1.D1",
                    "status": "open",
                    "blocked_by": [],
                    "claimed_by": "alice",
                }
            ],
            "parked_questions": [],
        }
        pred = flowctl.chart_completion_predicate(claimed_only)
        self.assertFalse(pred["briefable"])
        self.assertEqual(pred["claimed_open_ids"], ["fn-1.D1"])
        self.assertEqual(pred["frontier_ids"], [])

    def test_resolved_no_parked_is_briefable(self) -> None:
        pred = flowctl.chart_completion_predicate(
            {
                "decisions": [
                    {
                        "id": "fn-1.D1",
                        "status": "resolved",
                        "blocked_by": [],
                        "claimed_by": None,
                    }
                ],
                "parked_questions": [],
            }
        )
        self.assertTrue(pred["briefable"])

    def test_parked_questions_block_completion(self) -> None:
        pred = flowctl.chart_completion_predicate(
            {
                "decisions": [],
                "parked_questions": [{"key": "abc", "body": "Still open?"}],
            }
        )
        self.assertFalse(pred["briefable"])
        self.assertEqual(pred["parked_count"], 1)

    def test_frontier_command_reports_stuck_when_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Only")
            _run_flowctl(
                repo,
                "chart",
                "claim",
                d1["id"],
                "--json",
                env={"FLOW_ACTOR": "alice"},
            )
            fr = _run_flowctl(repo, "chart", "frontier", chart_id, "--json")
            self.assertEqual(fr.returncode, 0, fr.stderr)
            result = json.loads(fr.stdout)["result"]
            self.assertEqual(result["count"], 0)
            self.assertFalse(result["briefable"])
            self.assertTrue(result["stuck_reasons"])


class TestInitialMapMaxDecisions(unittest.TestCase):
    def test_over_ceiling_fails_without_reservation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            decisions = [{"title": f"D{i}", "type": "research"} for i in range(13)]
            map_path = repo / "map.json"
            map_path.write_text(
                json.dumps({"decisions": decisions}), encoding="utf-8"
            )

            r = _run_flowctl(
                repo,
                "chart",
                "create",
                "--title",
                "Too big",
                "--outcome",
                "Out",
                "--initial-map-file",
                str(map_path),
                "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)
            self.assertEqual(err["error"]["class"], "validation")
            self.assertEqual(err["error"]["code"], "max_decisions_exceeded")
            self.assertEqual(err["error"]["details"]["count"], 13)
            self.assertEqual(err["error"]["details"]["ceiling"], 12)
            # No chart id reserved
            charts = list((flow / "charts").glob("fn-*.json"))
            self.assertEqual(charts, [])

    def test_force_size_requires_reason_and_persists_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            decisions = [{"title": f"D{i}", "type": "research"} for i in range(13)]
            map_path = repo / "map.json"
            map_path.write_text(
                json.dumps({"decisions": decisions}), encoding="utf-8"
            )

            no_reason = _run_flowctl(
                repo,
                "chart",
                "create",
                "--title",
                "Too big",
                "--outcome",
                "Out",
                "--initial-map-file",
                str(map_path),
                "--force-size",
                "--json",
                env={"FLOW_ACTOR": "alice"},
            )
            self.assertNotEqual(no_reason.returncode, 0)
            err = json.loads(no_reason.stdout)
            self.assertEqual(err["error"]["code"], "force_size_reason_required")
            self.assertEqual(list((flow / "charts").glob("fn-*.json")), [])

            ok = _run_flowctl(
                repo,
                "chart",
                "create",
                "--title",
                "Forced",
                "--outcome",
                "Out",
                "--initial-map-file",
                str(map_path),
                "--force-size",
                "--reason",
                "explicit consent after read-back",
                "--json",
                env={"FLOW_ACTOR": "alice"},
            )
            self.assertEqual(ok.returncode, 0, ok.stderr)
            env = json.loads(ok.stdout)
            self.assertEqual(env["command"], "chart.create")
            result = env["result"]
            self.assertEqual(result["decision_count"], 13)
            self.assertEqual(result["id"], "fn-1")
            audit = result["force_size_audit"]
            self.assertEqual(audit["actor"], "alice")
            self.assertEqual(audit["ceiling"], 12)
            self.assertEqual(audit["count"], 13)
            self.assertEqual(audit["reason"], "explicit consent after read-back")
            self.assertIn("timestamp", audit)

            side = json.loads(
                (flow / "charts" / "fn-1.json").read_text(encoding="utf-8")
            )
            self.assertEqual(side["force_size_audit"], audit)
            self.assertEqual(len(side["decisions"]), 13)
            # Decision records created
            self.assertTrue((flow / "charts" / "fn-1" / "1.md").is_file())
            self.assertTrue((flow / "charts" / "fn-1" / "13.json").is_file())

    def test_initial_map_wires_edges_attendance_and_parked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            map_data = {
                "decisions": [
                    {"title": "Research keys", "type": "research"},
                    {
                        "title": "Approve model",
                        "type": "task",
                        "attendance": "attended",
                        "blocked_by": ["D1"],
                        "depends_on": ["1"],
                    },
                    {
                        "title": "Prototype store",
                        "type": "prototype",
                        "blocked_by": ["D2"],
                    },
                ],
                "parked_questions": ["Should we split the chart?"],
            }
            map_path = repo / "map.json"
            map_path.write_text(json.dumps(map_data), encoding="utf-8")
            r = _run_flowctl(
                repo,
                "chart",
                "create",
                "--title",
                "Mapped",
                "--outcome",
                "Capture-ready",
                "--initial-map-file",
                str(map_path),
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            result = json.loads(r.stdout)["result"]
            self.assertEqual(result["decision_count"], 3)
            self.assertEqual(result["parked_count"], 1)
            self.assertEqual(result["unattended_count"], 1)  # research
            self.assertEqual(result["attended_count"], 2)  # task + prototype
            self.assertIn("estimated_sessions", result)
            self.assertIn("cost_line", result)

            side = json.loads(
                (flow / "charts" / f"{result['id']}.json").read_text(encoding="utf-8")
            )
            by_id = {d["id"]: d for d in side["decisions"]}
            cid = result["id"]
            self.assertEqual(by_id[f"{cid}.D1"]["attendance"], "unattended")
            self.assertEqual(by_id[f"{cid}.D2"]["attendance"], "attended")
            self.assertEqual(by_id[f"{cid}.D2"]["blocked_by"], [f"{cid}.D1"])
            self.assertEqual(by_id[f"{cid}.D2"]["depends_on"], [f"{cid}.D1"])
            self.assertEqual(by_id[f"{cid}.D3"]["blocked_by"], [f"{cid}.D2"])
            self.assertEqual(len(side["parked_questions"]), 1)
            self.assertEqual(
                side["parked_questions"][0]["body"], "Should we split the chart?"
            )

            fr = _run_flowctl(repo, "chart", "frontier", cid, "--json")
            ids = [d["id"] for d in json.loads(fr.stdout)["result"]["frontier"]]
            self.assertEqual(ids, [f"{cid}.D1"])  # only unblocked


class TestConfigDefaults(unittest.TestCase):
    def test_constants_and_fresh_init_config_get(self) -> None:
        self.assertEqual(flowctl.CHART_DEFAULT_MAX_DECISIONS, 12)
        self.assertEqual(flowctl.CHART_DEFAULT_CLAIM_STALE_AFTER_HOURS, 24)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)

            r = _run_flowctl(repo, "config", "get", "chart.maxDecisions")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("12", r.stdout)

            r = _run_flowctl(repo, "config", "get", "chart.claimStaleAfter")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("24", r.stdout)

            # In-process readers after chdir into repo
            old_cwd = os.getcwd()
            try:
                os.chdir(repo)
                # Clear any cached config
                if hasattr(flowctl, "_config_cache"):
                    flowctl._config_cache = None  # type: ignore[attr-defined]
                self.assertEqual(flowctl.get_chart_max_decisions(), 12)
                self.assertEqual(flowctl.get_chart_claim_stale_after_hours(), 24.0)
            finally:
                os.chdir(old_cwd)

    def test_config_override_affects_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            cfg_path = flow / "config.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg.setdefault("chart", {})["maxDecisions"] = 2
            cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

            map_path = repo / "map.json"
            map_path.write_text(
                json.dumps(
                    {
                        "decisions": [
                            {"title": "A", "type": "research"},
                            {"title": "B", "type": "research"},
                            {"title": "C", "type": "research"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            r = _run_flowctl(
                repo,
                "chart",
                "create",
                "--title",
                "Over 2",
                "--outcome",
                "O",
                "--initial-map-file",
                str(map_path),
                "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)
            self.assertEqual(err["error"]["code"], "max_decisions_exceeded")
            self.assertEqual(err["error"]["details"]["ceiling"], 2)


class TestV1Envelopes(unittest.TestCase):
    def test_success_and_error_envelope_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "A")

            for cmd_args, command in [
                (["chart", "frontier", chart_id, "--json"], "chart.frontier"),
                (["chart", "claim", d1["id"], "--json"], "chart.claim"),
                (["chart", "show", chart_id, "--json"], "chart.show"),
                (["chart", "list", "--json"], "chart.list"),
            ]:
                env_vars = {"FLOW_ACTOR": "alice"} if "claim" in cmd_args else None
                r = _run_flowctl(repo, *cmd_args, env=env_vars)
                self.assertEqual(r.returncode, 0, f"{command}: {r.stderr}")
                env = json.loads(r.stdout)
                self.assertEqual(
                    set(env.keys()),
                    {"success", "schema_version", "command", "result"},
                )
                self.assertTrue(env["success"])
                self.assertEqual(env["schema_version"], 1)
                self.assertEqual(env["command"], command)

            # Error envelope
            r = _run_flowctl(repo, "chart", "show", "fn-999", "--json")
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)
            self.assertEqual(
                set(err.keys()),
                {"success", "schema_version", "command", "error"},
            )
            self.assertFalse(err["success"])
            self.assertEqual(err["schema_version"], 1)
            self.assertEqual(
                set(err["error"].keys()),
                {"class", "code", "message", "details"},
            )


class TestCompactReads(unittest.TestCase):
    def test_show_list_frontier_omit_answer_and_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Secret answer holder")

            # Inject answer/assets into full decision sidecar
            dpath = flow / "charts" / chart_id / "1.json"
            dside = json.loads(dpath.read_text(encoding="utf-8"))
            dside["answer"] = "CLASSIFIED_ANSWER_BODY"
            dside["assets"] = [{"path": "secret.bin", "note": "do not load"}]
            dside["question"] = "Should stay only on full record"
            dpath.write_text(json.dumps(dside, indent=2) + "\n", encoding="utf-8")

            show = _run_flowctl(repo, "chart", "show", chart_id, "--json")
            self.assertEqual(show.returncode, 0, show.stderr)
            show_env = json.loads(show.stdout)
            blob = json.dumps(show_env)
            self.assertNotIn("CLASSIFIED_ANSWER_BODY", blob)
            self.assertNotIn("secret.bin", blob)
            for d in show_env["result"]["decisions"]:
                self.assertNotIn("answer", d)
                self.assertNotIn("assets", d)
                self.assertNotIn("question", d)
                self.assertIn("title", d)
                self.assertIn("id", d)
                self.assertIn("record_path", d)

            lst = _run_flowctl(repo, "chart", "list", "--json")
            self.assertEqual(lst.returncode, 0, lst.stderr)
            list_env = json.loads(lst.stdout)
            self.assertNotIn("CLASSIFIED_ANSWER_BODY", json.dumps(list_env))
            for c in list_env["result"]["charts"]:
                self.assertNotIn("frontier", c)
                self.assertNotIn("claims", c)
                self.assertIn("cost_line", c)
                self.assertIn("decision_count", c)

            fr = _run_flowctl(repo, "chart", "frontier", chart_id, "--json")
            self.assertEqual(fr.returncode, 0, fr.stderr)
            fr_env = json.loads(fr.stdout)
            self.assertNotIn("CLASSIFIED_ANSWER_BODY", json.dumps(fr_env))
            self.assertEqual(
                [d["id"] for d in fr_env["result"]["frontier"]], [d1["id"]]
            )

    def test_frontier_and_show_do_not_open_decision_sidecars(self) -> None:
        """Instrument load_decision_sidecar: navigation must not call it."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            _add_decision(repo, chart_id, "A")
            _add_decision(repo, chart_id, "B")

            calls: list[tuple] = []

            real_load = flowctl.load_decision_sidecar

            def tracking_load(*args, **kwargs):
                calls.append((args, kwargs))
                return real_load(*args, **kwargs)

            old_cwd = os.getcwd()
            try:
                os.chdir(repo)
                with mock.patch.object(
                    flowctl, "load_decision_sidecar", side_effect=tracking_load
                ):
                    data = flowctl.load_chart_sidecar(flow, chart_id)
                    frontier = flowctl.compute_frontier(data)
                    meta = flowctl.compact_chart_metadata(data)
                    self.assertEqual(len(frontier), 2)
                    self.assertEqual(meta["decision_count"], 2)
            finally:
                os.chdir(old_cwd)

            self.assertEqual(
                calls,
                [],
                f"navigation loaded full decision sidecars: {calls}",
            )


class TestCostEstimate(unittest.TestCase):
    def test_cost_reads_attendance_field(self) -> None:
        cost = flowctl.chart_cost_estimate(
            [
                {"attendance": "unattended"},
                {"attendance": "unattended"},
                {"attendance": "attended"},
            ]
        )
        self.assertEqual(cost["unattended_count"], 2)
        self.assertEqual(cost["attended_count"], 1)
        self.assertEqual(cost["estimated_sessions"], 2)  # 1 attended + 1 batch
        self.assertIn("sessions", cost["cost_line"])


if __name__ == "__main__":
    unittest.main()
