# Split from test_chart_graph_claims.py 2026-08-07 to shrink the per-file unit-suite shard. Claim/release/stale, supersede-claim guard, parked questions, unsafe prose, compact reads.
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

    def test_claim_blocked_decision_rejected_until_blocker_resolves(self) -> None:
        """A blocked decision is not claimable (it would vanish from the
        frontier as blocked-then-claimed and wedge the chart); the rejection
        names the open blockers, and the claim succeeds once they resolve."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Blocker")
            d2 = _add_decision(repo, chart_id, "Dependent", blocked_by=d1["id"])

            r = _run_flowctl(
                repo,
                "chart",
                "claim",
                d2["id"],
                "--json",
                env={"FLOW_ACTOR": "alice"},
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)["error"]
            self.assertEqual(err["class"], "invalid_state")
            self.assertEqual(err["code"], "decision_blocked")
            self.assertIn(d1["id"], err["message"])
            self.assertEqual(err["details"]["blocked_by"], [d1["id"]])
            # Nothing persisted: sidecar stays unclaimed.
            dside = json.loads(
                (flow / "charts" / chart_id / "2.json").read_text(encoding="utf-8")
            )
            self.assertIsNone(dside["claimed_by"])

            # Resolve the blocker; the claim now succeeds.
            af = repo / "ans.txt"
            af.write_text("Blocker settled", encoding="utf-8")
            r_res = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--json",
                env={"FLOW_ACTOR": "alice"},
            )
            self.assertEqual(r_res.returncode, 0, r_res.stderr)
            r2 = _run_flowctl(
                repo,
                "chart",
                "claim",
                d2["id"],
                "--json",
                env={"FLOW_ACTOR": "alice"},
            )
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            self.assertEqual(
                json.loads(r2.stdout)["result"]["claimed_by"], "alice"
            )

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


class TestSupersedeClaimGuard(unittest.TestCase):
    def test_supersede_of_claimed_open_target_conflicts(self) -> None:
        """resolve --supersedes on an OPEN target claimed by another actor is
        a claim_conflict (release-claim / --break-stale is the sanctioned
        route); the DEPENDENT cascade keeps its audited claim-clearing."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Replacement")
            d2 = _add_decision(repo, chart_id, "Old direction")
            d3 = _add_decision(
                repo, chart_id, "Derived work", depends_on=d2["id"]
            )
            for did, actor in ((d2["id"], "bob"), (d3["id"], "carol")):
                r = _run_flowctl(
                    repo, "chart", "claim", did, "--json",
                    env={"FLOW_ACTOR": actor},
                )
                self.assertEqual(r.returncode, 0, r.stderr)

            af = repo / "ans.txt"
            af.write_text("New direction supersedes old", encoding="utf-8")
            r = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--supersedes",
                d2["id"],
                "--json",
                env={"FLOW_ACTOR": "alice"},
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)["error"]
            self.assertEqual(err["class"], "conflict")
            self.assertEqual(err["code"], "claim_conflict")
            self.assertEqual(err["details"]["id"], d2["id"])
            self.assertEqual(err["details"]["claimed_by"], "bob")
            self.assertEqual(err["details"]["actor"], "alice")
            # Nothing applied: target open, claim intact; primary still open.
            d2_side = json.loads(
                (flow / "charts" / chart_id / "2.json").read_text(
                    encoding="utf-8")
            )
            self.assertEqual(d2_side["status"], "open")
            self.assertEqual(d2_side["claimed_by"], "bob")
            d1_side = json.loads(
                (flow / "charts" / chart_id / "1.json").read_text(
                    encoding="utf-8")
            )
            self.assertEqual(d1_side["status"], "open")

            # Unclaimed target proceeds; the dependent cascade still clears
            # carol's claim on D3 (audited exception, by design).
            rel = _run_flowctl(
                repo, "chart", "release-claim", d2["id"], "--json",
                env={"FLOW_ACTOR": "bob"},
            )
            self.assertEqual(rel.returncode, 0, rel.stderr)
            r2 = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--supersedes",
                d2["id"],
                "--json",
                env={"FLOW_ACTOR": "alice"},
            )
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            d2_side = json.loads(
                (flow / "charts" / chart_id / "2.json").read_text(
                    encoding="utf-8")
            )
            self.assertEqual(d2_side["status"], "superseded")
            d3_side = json.loads(
                (flow / "charts" / chart_id / "3.json").read_text(
                    encoding="utf-8")
            )
            self.assertEqual(d3_side["status"], "open")
            self.assertIsNone(d3_side["claimed_by"])

    def test_supersede_same_actor_claim_proceeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Replacement")
            d2 = _add_decision(repo, chart_id, "Old direction")
            r = _run_flowctl(
                repo, "chart", "claim", d2["id"], "--json",
                env={"FLOW_ACTOR": "alice"},
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            af = repo / "ans.txt"
            af.write_text("Alice replaces her own work", encoding="utf-8")
            r2 = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--supersedes",
                d2["id"],
                "--json",
                env={"FLOW_ACTOR": "alice"},
            )
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            d2_side = json.loads(
                (flow / "charts" / chart_id / "2.json").read_text(
                    encoding="utf-8")
            )
            self.assertEqual(d2_side["status"], "superseded")


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


class TestUnsafeProse(unittest.TestCase):
    """R20/R48: EVERY prose entry point into git-tracked chart records
    refuses obvious secret / destructive-command shapes before allocation or
    persistence - not only the resolution answer path. Fixtures are obviously
    fake shapes; destructive commands are described, never executed."""

    def test_force_size_reason_refuses_unsafe_prose(self) -> None:
        """The --force-size audit reason is git-tracked chart prose too: an
        over-ceiling override carrying a secret shape refuses before the audit
        record (and the chart) is written."""
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
                "Big effort",
                "--outcome",
                "Out",
                "--initial-map-file",
                str(map_path),
                "--force-size",
                "--reason",
                "lead approved; password=hunter2-FAKE",
                "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)["error"]
            self.assertEqual(err["class"], "validation")
            self.assertEqual(err["code"], "unsafe_prose_content")
            self.assertIn("force-size", err["details"]["field"])
            self.assertEqual(list((flow / "charts").glob("fn-*.json")), [])

    def test_initial_map_notes_seed_chart_notes_section(self) -> None:
        """R52: grounding facts land under `## Notes` through the initial-map
        `notes` string, with citations preserved and no fabricated ledger
        line; unsafe notes prose refuses like every other entry point."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            note_line = "- Shared schema today [ref: src/db/schema.sql rev:9f2c1ab]"
            map_path = repo / "map.json"
            map_path.write_text(
                json.dumps(
                    {
                        "decisions": [{"title": "Choose key", "type": "research"}],
                        "notes": note_line,
                    }
                ),
                encoding="utf-8",
            )
            r = _run_flowctl(
                repo,
                "chart",
                "create",
                "--title",
                "Tenant isolation",
                "--outcome",
                "Ready",
                "--initial-map-file",
                str(map_path),
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            chart_id = json.loads(r.stdout)["result"]["id"]
            body = (flow / "charts" / f"{chart_id}.md").read_text(encoding="utf-8")
            notes_section = body.split("## Notes", 1)[1].split("## Decisions", 1)[0]
            self.assertIn(note_line, notes_section)
            # Background never becomes ledger history.
            ledger = body.split("## Decisions", 1)[1].split("## Open Questions", 1)[0]
            self.assertNotIn(note_line, ledger)

            unsafe_map = repo / "unsafe.json"
            unsafe_map.write_text(
                json.dumps(
                    {
                        "decisions": [{"title": "Choose key", "type": "research"}],
                        "notes": "- token sk-FAKESECRETVALUE0000000000",
                    }
                ),
                encoding="utf-8",
            )
            r2 = _run_flowctl(
                repo,
                "chart",
                "create",
                "--title",
                "Second",
                "--outcome",
                "Ready",
                "--initial-map-file",
                str(unsafe_map),
                "--json",
            )
            self.assertNotEqual(r2.returncode, 0)
            err2 = json.loads(r2.stdout)["error"]
            self.assertEqual(err2["code"], "unsafe_prose_content")
            self.assertIn("Notes", err2["details"]["field"])

    def test_chart_create_refuses_unsafe_title_and_outcome(self) -> None:
        """--title/--outcome land in git-tracked chart md/json (and the
        tracker parent rollup); both refuse unsafe shapes before any
        allocation, same error shape as decision prose."""
        cases = [
            (
                ["--title", "use password=hunter2-FAKE for db",
                 "--outcome", "Out"],
                "Chart title",
                "secret",
            ),
            (
                ["--title", "Fine title",
                 "--outcome", "weekly cleanup runs git reset --hard"],
                "Chart outcome",
                "destructive_command",
            ),
        ]
        for extra_args, field, kind in cases:
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory() as tmp:
                    repo = Path(tmp) / "repo"
                    _init_repo(repo)
                    flow = _init_flow(repo)
                    r = _run_flowctl(
                        repo, "chart", "create", *extra_args, "--json",
                    )
                    self.assertNotEqual(r.returncode, 0)
                    err = json.loads(r.stdout)["error"]
                    self.assertEqual(err["class"], "validation")
                    self.assertEqual(err["code"], "unsafe_prose_content")
                    self.assertEqual(err["details"]["field"], field)
                    self.assertIn(kind, err["details"]["kinds"])
                    # Refused BEFORE any allocation or persistence.
                    self.assertEqual(
                        list((flow / "charts").glob("fn-*")), [],
                    )

    def test_initial_map_refuses_unsafe_prose_before_allocation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            map_path = repo / "map.json"
            map_path.write_text(
                json.dumps({
                    "decisions": [
                        {"title": "Fine decision", "type": "research"},
                        {
                            "title": "Creds",
                            "type": "research",
                            # Obviously fake credential shape.
                            "question": "use password=hunter2-FAKE for db",
                        },
                    ],
                }),
                encoding="utf-8",
            )
            r = _run_flowctl(
                repo,
                "chart",
                "create",
                "--title",
                "Bad map",
                "--outcome",
                "Out",
                "--initial-map-file",
                str(map_path),
                "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)["error"]
            self.assertEqual(err["class"], "validation")
            self.assertEqual(err["code"], "unsafe_prose_content")
            self.assertIn("secret", err["details"]["kinds"])
            # Refused BEFORE any allocation or persistence.
            self.assertEqual(list((flow / "charts").glob("fn-*.json")), [])

    def test_initial_map_refuses_unsafe_parked_question(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            map_path = repo / "map.json"
            map_path.write_text(
                json.dumps({
                    "decisions": [
                        {"title": "Fine decision", "type": "research"},
                    ],
                    "parked_questions": [
                        # Destructive command described in prose per guard
                        # rules; the literal shape must still refuse.
                        "should cleanup use git reset --hard here?",
                    ],
                }),
                encoding="utf-8",
            )
            r = _run_flowctl(
                repo,
                "chart",
                "create",
                "--title",
                "Bad parked",
                "--outcome",
                "Out",
                "--initial-map-file",
                str(map_path),
                "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)["error"]
            self.assertEqual(err["code"], "unsafe_prose_content")
            self.assertIn("destructive_command", err["details"]["kinds"])
            self.assertEqual(list((flow / "charts").glob("fn-*.json")), [])

    def test_add_decision_refuses_unsafe_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            _add_decision(repo, chart_id, "First")
            body = repo / "body.md"
            body.write_text(
                "token is sk-FAKESECRETVALUE0000000000\n", encoding="utf-8"
            )
            r = _run_flowctl(
                repo,
                "chart",
                "add-decision",
                chart_id,
                "--title",
                "Creds",
                "--type",
                "research",
                "--body-file",
                str(body),
                "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)["error"]
            self.assertEqual(err["class"], "validation")
            self.assertEqual(err["code"], "unsafe_prose_content")
            # No D-ID allocated, no record persisted.
            self.assertFalse((flow / "charts" / chart_id / "2.json").exists())
            side = json.loads(
                (flow / "charts" / f"{chart_id}.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(len(side["decisions"]), 1)

    def test_park_question_refuses_unsafe_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            _add_decision(repo, chart_id, "First")
            qf = repo / "park.txt"
            qf.write_text(
                "is api_key=FAKE-NOT-REAL-1234 still valid?\n",
                encoding="utf-8",
            )
            r = _run_flowctl(
                repo,
                "chart",
                "park-question",
                chart_id,
                "--body-file",
                str(qf),
                "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)["error"]
            self.assertEqual(err["code"], "unsafe_prose_content")
            side = json.loads(
                (flow / "charts" / f"{chart_id}.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(side.get("parked_questions") or [], [])


if __name__ == "__main__":
    unittest.main()
