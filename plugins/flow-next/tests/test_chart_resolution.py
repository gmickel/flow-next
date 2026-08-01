"""Unit tests for chart resolve, assets, supersession, scope, abandon (fn-135.2).

Covers: attach-asset idempotency, prototype gate, resolve ledger gist,
immutable answers, supersession cascade (open + resolved dependents),
--keep-dependents, resolve-with-sharpening + crash recovery, out-of-scope
boundaries, abandon terminal, unsafe-evidence refusal.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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
    r = _run_flowctl(repo, *args)
    assert r.returncode == 0, r.stderr + r.stdout
    env_out = json.loads(r.stdout)
    assert env_out["success"] is True
    return env_out["result"]


def _write_answer(repo: Path, name: str, text: str) -> Path:
    p = repo / name
    p.write_text(text, encoding="utf-8")
    return p


def _write_asset_file(repo: Path, name: str, asset: dict) -> Path:
    p = repo / name
    p.write_text(json.dumps(asset), encoding="utf-8")
    return p


def _decision_json(flow: Path, chart_id: str, n: int) -> dict:
    return json.loads(
        (flow / "charts" / chart_id / f"{n}.json").read_text(encoding="utf-8")
    )


def _chart_md(flow: Path, chart_id: str) -> str:
    return (flow / "charts" / f"{chart_id}.md").read_text(encoding="utf-8")


def _chart_json(flow: Path, chart_id: str) -> dict:
    return json.loads(
        (flow / "charts" / f"{chart_id}.json").read_text(encoding="utf-8")
    )


class TestAttachAsset(unittest.TestCase):
    def test_attach_path_idempotent_and_keeps_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Proto UI", "prototype")
            evidence = repo / "docs"
            evidence.mkdir()
            artefact = evidence / "wireframe.md"
            artefact.write_text("# wireframe\nmock layout\n", encoding="utf-8")
            _git(repo, "add", "docs/wireframe.md")
            _git(repo, "commit", "-q", "-m", "evidence")

            asset = {
                "kind": "path",
                "reference": "docs/wireframe.md",
                "display": "throwaway wireframe mock",
                "revision": "rev-1",
            }
            af = _write_asset_file(repo, "asset1.json", asset)
            r = _run_flowctl(
                repo,
                "chart",
                "attach-asset",
                d1["id"],
                "--asset-file",
                str(af),
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            env = json.loads(r.stdout)
            self.assertEqual(env["command"], "chart.attach-asset")
            self.assertTrue(env["success"])
            self.assertFalse(env["result"]["noop"])
            self.assertEqual(env["result"]["status"], "open")
            self.assertEqual(env["result"]["asset"]["reference"], "docs/wireframe.md")

            # Identical retry is no-op; still open; no duplicate asset.
            r2 = _run_flowctl(
                repo,
                "chart",
                "attach-asset",
                d1["id"],
                "--asset-file",
                str(af),
                "--json",
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)
            env2 = json.loads(r2.stdout)
            self.assertTrue(env2["result"]["noop"])
            side = _decision_json(flow, chart_id, 1)
            self.assertEqual(side["status"], "open")
            self.assertIsNone(side.get("answer"))
            self.assertEqual(len(side["assets"]), 1)

            # Conflicting reuse (same identity, different display) errors.
            asset_conflict = dict(asset)
            asset_conflict["display"] = "different summary"
            af2 = _write_asset_file(repo, "asset2.json", asset_conflict)
            r3 = _run_flowctl(
                repo,
                "chart",
                "attach-asset",
                d1["id"],
                "--asset-file",
                str(af2),
                "--json",
            )
            self.assertNotEqual(r3.returncode, 0)
            err = json.loads(r3.stdout)
            self.assertEqual(err["error"]["class"], "conflict")
            self.assertEqual(err["error"]["code"], "asset_conflict")

    def test_attach_rejects_missing_and_credential_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Research path", "research")

            af = _write_asset_file(
                repo,
                "missing.json",
                {
                    "kind": "path",
                    "reference": "no/such/file.md",
                    "display": "missing",
                },
            )
            r = _run_flowctl(
                repo,
                "chart",
                "attach-asset",
                d1["id"],
                "--asset-file",
                str(af),
                "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(json.loads(r.stdout)["error"]["code"], "asset_path_missing")

            af2 = _write_asset_file(
                repo,
                "cred.json",
                {
                    "kind": "url",
                    "reference": "https://user:pass@example.com/evidence",
                    "display": "bad url",
                },
            )
            r2 = _run_flowctl(
                repo,
                "chart",
                "attach-asset",
                d1["id"],
                "--asset-file",
                str(af2),
                "--json",
            )
            self.assertNotEqual(r2.returncode, 0)
            self.assertEqual(
                json.loads(r2.stdout)["error"]["code"], "asset_url_credentials"
            )


class TestResolveBasic(unittest.TestCase):
    def test_resolve_writes_answer_and_one_ledger_gist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Choose tenant key", "research")
            answer = (
                "Use org_id as the tenant key for all tables.\n"
                "Details that must NOT appear in the map body."
            )
            af = _write_answer(repo, "ans.txt", answer)
            r = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            env = json.loads(r.stdout)
            self.assertEqual(
                env,
                {
                    "success": True,
                    "schema_version": 1,
                    "command": "chart.resolve",
                    "result": env["result"],
                },
            )
            self.assertEqual(env["result"]["status"], "resolved")
            self.assertFalse(env["result"]["noop"])
            self.assertIn("org_id", env["result"]["answer_gist"])
            self.assertNotIn("must NOT appear", env["result"]["answer_gist"])

            side = _decision_json(flow, chart_id, 1)
            self.assertEqual(side["status"], "resolved")
            self.assertEqual(side["answer"], answer)
            self.assertIsNone(side["claimed_by"])

            body = _chart_md(flow, chart_id)
            # Exactly one ledger line for D1; full answer never restated.
            self.assertEqual(body.count("**D1:**"), 1)
            self.assertIn("org_id as the tenant key", body)
            self.assertNotIn("must NOT appear", body)
            self.assertIn(f".flow/charts/{chart_id}/1.md", body)

            # Identical retry is idempotent.
            r2 = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--json",
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertTrue(json.loads(r2.stdout)["result"]["noop"])

            # Conflicting retry is invalid_state.
            af2 = _write_answer(repo, "ans2.txt", "Different answer entirely")
            r3 = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af2),
                "--json",
            )
            self.assertNotEqual(r3.returncode, 0)
            err = json.loads(r3.stdout)
            self.assertEqual(err["error"]["class"], "invalid_state")
            self.assertEqual(err["error"]["code"], "decision_immutable")

    def test_prototype_requires_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Proto UI", "prototype")
            af = _write_answer(repo, "ans.txt", "Looks good, ship the layout")
            r = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)
            self.assertEqual(err["error"]["code"], "prototype_asset_required")
            self.assertEqual(_decision_json(flow, chart_id, 1)["status"], "open")

            # Attach then resolve succeeds; attach alone never closed it.
            evidence = repo / "proto.md"
            evidence.write_text("mock\n", encoding="utf-8")
            _git(repo, "add", "proto.md")
            _git(repo, "commit", "-q", "-m", "proto")
            asset_f = _write_asset_file(
                repo,
                "a.json",
                {
                    "kind": "path",
                    "reference": "proto.md",
                    "display": "throwaway proto",
                    "revision": "r1",
                },
            )
            att = _run_flowctl(
                repo,
                "chart",
                "attach-asset",
                d1["id"],
                "--asset-file",
                str(asset_f),
                "--json",
            )
            self.assertEqual(att.returncode, 0, att.stderr)
            self.assertEqual(json.loads(att.stdout)["result"]["status"], "open")

            r2 = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--json",
            )
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            side = _decision_json(flow, chart_id, 1)
            self.assertEqual(side["status"], "resolved")
            self.assertEqual(len(side["assets"]), 1)


class TestSupersession(unittest.TestCase):
    def test_supersedes_strikes_ledger_and_cascades(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Storage choice", "research")
            # D2 open, depends on D1 (premise)
            d2 = _add_decision(
                repo,
                chart_id,
                "Cache layer",
                "research",
                depends_on="D1",
            )
            # Resolve D1 first
            a1 = _write_answer(repo, "a1.txt", "Pick Postgres for primary store")
            r = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(a1),
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr)

            # D3 resolved and depends on D1
            d3 = _add_decision(
                repo,
                chart_id,
                "Migration path",
                "research",
                depends_on="D1",
            )
            a3 = _write_answer(repo, "a3.txt", "Big-bang migration weekend")
            r3 = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d3["id"],
                "--answer-file",
                str(a3),
                "--json",
            )
            self.assertEqual(r3.returncode, 0, r3.stderr)

            # Claim open D2 so cascade claim-clear is observable
            claim = _run_flowctl(repo, "chart", "claim", d2["id"], "--json")
            self.assertEqual(claim.returncode, 0, claim.stderr)

            # D4 supersedes D1
            d4 = _add_decision(repo, chart_id, "Revisit storage", "research")
            a4 = _write_answer(
                repo, "a4.txt", "Pick SQLite for the embedded edge case"
            )
            r4 = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d4["id"],
                "--answer-file",
                str(a4),
                "--supersedes",
                "D1",
                "--json",
            )
            self.assertEqual(r4.returncode, 0, r4.stderr + r4.stdout)
            result = json.loads(r4.stdout)["result"]
            self.assertIn(d1["id"], result["affected"])
            self.assertIn(d2["id"], result["affected"])
            self.assertIn(d3["id"], result["affected"])
            self.assertEqual(result["cascade_open"], [d2["id"]])
            self.assertEqual(result["cascade_resolved"], [d3["id"]])
            self.assertEqual(len(result["replacements"]), 1)
            rep_id = result["replacements"][0]["id"]
            self.assertIn(rep_id, result["affected"])

            d1_side = _decision_json(flow, chart_id, 1)
            self.assertEqual(d1_side["status"], "superseded")
            self.assertEqual(d1_side["superseded_by"], d4["id"])

            d2_side = _decision_json(flow, chart_id, 2)
            self.assertEqual(d2_side["status"], "open")
            self.assertIsNone(d2_side["claimed_by"])
            kinds = [n.get("kind") for n in d2_side.get("transition_notes") or []]
            self.assertIn("premise_invalidated", kinds)

            d3_side = _decision_json(flow, chart_id, 3)
            self.assertEqual(d3_side["status"], "superseded")
            self.assertEqual(d3_side["superseded_by"], rep_id)
            # Original answer immutable
            self.assertEqual(d3_side["answer"], "Big-bang migration weekend")

            rep_n = int(rep_id.rsplit("D", 1)[1])
            rep_side = _decision_json(flow, chart_id, rep_n)
            self.assertEqual(rep_side["status"], "open")
            self.assertEqual(rep_side["supersedes"], [d3["id"]])
            self.assertIn("re-evaluate", rep_side["transition_notes"][0]["text"])

            body = _chart_md(flow, chart_id)
            self.assertIn("~~**D1:**~~", body)
            self.assertIn("superseded by **D4**", body)
            self.assertIn("~~**D3:**~~", body)
            # D1 line never removed
            self.assertIn("Postgres", body)

    def test_keep_dependents_suppresses_cascade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Premise", "research")
            d2 = _add_decision(
                repo, chart_id, "Dependent", "research", depends_on="D1"
            )
            a1 = _write_answer(repo, "a1.txt", "First premise answer")
            self.assertEqual(
                _run_flowctl(
                    repo,
                    "chart",
                    "resolve",
                    d1["id"],
                    "--answer-file",
                    str(a1),
                    "--json",
                ).returncode,
                0,
            )
            claim = _run_flowctl(repo, "chart", "claim", d2["id"], "--json")
            self.assertEqual(claim.returncode, 0)

            d3 = _add_decision(repo, chart_id, "Override", "research")
            a3 = _write_answer(repo, "a3.txt", "New premise answer")
            r = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d3["id"],
                "--answer-file",
                str(a3),
                "--supersedes",
                "D1",
                "--keep-dependents",
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            result = json.loads(r.stdout)["result"]
            self.assertTrue(result["keep_dependents"])
            self.assertEqual(result["cascade_open"], [])
            self.assertEqual(result["replacements"], [])
            self.assertIn(d2["id"], result["affected"])

            d2_side = _decision_json(flow, chart_id, 2)
            self.assertEqual(d2_side["status"], "open")
            # Claim preserved when cascade suppressed
            self.assertIsNotNone(d2_side["claimed_by"])
            kinds = [n.get("kind") for n in d2_side.get("transition_notes") or []]
            self.assertIn("keep_dependents", kinds)
            d3_side = _decision_json(flow, chart_id, 3)
            kinds3 = [n.get("kind") for n in d3_side.get("transition_notes") or []]
            self.assertIn("keep_dependents", kinds3)


class TestSharpenAndCrash(unittest.TestCase):
    def test_resolve_with_sharpen_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main question", "research")
            # Park a question, then sharpen removes it and adds new decisions.
            park_body = repo / "park.txt"
            park_body.write_text("How do tenants share indexes?", encoding="utf-8")
            park = _run_flowctl(
                repo,
                "chart",
                "park-question",
                chart_id,
                "--body-file",
                str(park_body),
                "--json",
            )
            self.assertEqual(park.returncode, 0, park.stderr)
            pkey = json.loads(park.stdout)["result"]["key"]

            sharpen = {
                "decisions": [
                    {
                        "title": "Index sharing model",
                        "type": "research",
                        "question": "Do tenants share indexes or isolate?",
                        "depends_on": ["D1"],
                    }
                ],
                "remove_questions": [pkey],
            }
            sf = repo / "sharpen.json"
            sf.write_text(json.dumps(sharpen), encoding="utf-8")
            af = _write_answer(repo, "ans.txt", "Shared indexes with row filters")
            r = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--sharpen-file",
                str(sf),
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            result = json.loads(r.stdout)["result"]
            self.assertEqual(len(result["sharpened"]), 1)
            self.assertEqual(result["removed_questions"][0]["key"], pkey)
            new_id = result["sharpened"][0]["id"]
            self.assertTrue((flow / "charts" / chart_id / "2.json").is_file())
            chart = _chart_json(flow, chart_id)
            self.assertEqual(chart["parked_questions"], [])
            body = _chart_md(flow, chart_id)
            self.assertNotIn("How do tenants share indexes?", body)
            side_new = _decision_json(flow, chart_id, 2)
            self.assertEqual(side_new["id"], new_id)
            self.assertEqual(side_new["depends_on"], [d1["id"]])

    def test_sharpen_kill_after_stage_restores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main", "research")
            park_body = repo / "park.txt"
            park_body.write_text("Parked unknown X", encoding="utf-8")
            park = _run_flowctl(
                repo,
                "chart",
                "park-question",
                chart_id,
                "--body-file",
                str(park_body),
                "--json",
            )
            pkey = json.loads(park.stdout)["result"]["key"]
            sharpen = {
                "decisions": [
                    {"title": "New from sharpen", "type": "probe", "question": "Q?"}
                ],
                "remove_questions": [pkey],
            }
            sf = repo / "sharpen.json"
            sf.write_text(json.dumps(sharpen), encoding="utf-8")
            af = _write_answer(repo, "ans.txt", "Answer text")

            r = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--sharpen-file",
                str(sf),
                "--json",
                env={"FLOWCTL_CHART_FAILPOINT": "exit:after_stage"},
            )
            self.assertEqual(r.returncode, 99)

            # Recovery via show - no partial sharpening.
            show = _run_flowctl(repo, "chart", "show", chart_id, "--json")
            self.assertEqual(show.returncode, 0, show.stderr)
            side = _decision_json(flow, chart_id, 1)
            self.assertEqual(side["status"], "open")
            self.assertIsNone(side.get("answer"))
            self.assertFalse((flow / "charts" / chart_id / "2.json").exists())
            chart = _chart_json(flow, chart_id)
            self.assertEqual(len(chart["parked_questions"]), 1)
            body = _chart_md(flow, chart_id)
            self.assertIn("Parked unknown X", body)
            self.assertNotIn("**D1:**", body.split("## Decisions")[1].split("##")[0])


class TestOutOfScopeAndAbandon(unittest.TestCase):
    def test_out_of_scope_boundary_no_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Mobile client", "interview")
            r = _run_flowctl(
                repo,
                "chart",
                "out-of-scope",
                d1["id"],
                "--reason",
                "Outside the Outcome for this chart",
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            env = json.loads(r.stdout)
            self.assertEqual(env["command"], "chart.out-of-scope")
            self.assertEqual(env["result"]["status"], "out-of-scope")

            side = _decision_json(flow, chart_id, 1)
            self.assertEqual(side["status"], "out-of-scope")
            body = _chart_md(flow, chart_id)
            decisions_sec = body.split("## Decisions")[1].split("##")[0]
            self.assertNotIn("**D1:**", decisions_sec)
            self.assertIn("## Boundaries", body)
            self.assertIn("Outside the Outcome", body)

            # Idempotent identical reason
            r2 = _run_flowctl(
                repo,
                "chart",
                "out-of-scope",
                d1["id"],
                "--reason",
                "Outside the Outcome for this chart",
                "--json",
            )
            self.assertEqual(r2.returncode, 0)
            self.assertTrue(json.loads(r2.stdout)["result"]["noop"])

    def test_abandon_rejects_further_mutations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Anything", "research")
            r = _run_flowctl(
                repo,
                "chart",
                "abandon",
                chart_id,
                "--reason",
                "Priority shifted to other work",
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            env = json.loads(r.stdout)
            self.assertEqual(env["result"]["status"], "abandoned")
            chart = _chart_json(flow, chart_id)
            self.assertEqual(chart["status"], "abandoned")
            self.assertEqual(chart["abandon_reason"], "Priority shifted to other work")
            # Decision records preserved
            self.assertTrue((flow / "charts" / chart_id / "1.json").is_file())
            self.assertEqual(_decision_json(flow, chart_id, 1)["status"], "open")

            af = _write_answer(repo, "ans.txt", "Should fail")
            r2 = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--json",
            )
            self.assertNotEqual(r2.returncode, 0)
            err = json.loads(r2.stdout)
            self.assertEqual(err["error"]["class"], "invalid_state")
            self.assertEqual(err["error"]["code"], "chart_not_open")


class TestUnsafeEvidence(unittest.TestCase):
    def test_refuse_secret_shaped_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Creds decision", "research")
            # Obviously fake secret shape - never a real credential.
            af = _write_answer(
                repo,
                "bad.txt",
                "token is sk-FAKESECRETVALUE0000000000 do not ship",
            )
            r = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)
            self.assertEqual(err["error"]["code"], "unsafe_answer_content")
            self.assertEqual(_decision_json(flow, chart_id, 1)["status"], "open")
            # Safe summary is accepted.
            safe = _write_answer(
                repo,
                "safe.txt",
                "Use the vault reference for the service credential; "
                "see attached evidence path.",
            )
            # Attach approved evidence path (content not scanned as answer).
            evidence = repo / "notes.md"
            evidence.write_text("redacted notes only\n", encoding="utf-8")
            _git(repo, "add", "notes.md")
            _git(repo, "commit", "-q", "-m", "notes")
            assets = json.dumps(
                [
                    {
                        "kind": "path",
                        "reference": "notes.md",
                        "display": "redacted evidence notes",
                    }
                ]
            )
            r2 = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(safe),
                "--assets",
                assets,
                "--json",
            )
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            side = _decision_json(flow, chart_id, 1)
            self.assertEqual(side["status"], "resolved")
            self.assertNotIn("sk-FAKE", side["answer"])

    def test_refuse_destructive_command_shape_in_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Cleanup", "task", attendance="unattended")
            # Describe the shape without being subtle - pattern must match.
            # Use a prose-adjacent form that still contains the matched token.
            af = _write_answer(
                repo,
                "bad.txt",
                "Operator should run: git reset --hard before retry",
            )
            r = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(
                json.loads(r.stdout)["error"]["code"], "unsafe_answer_content"
            )


class TestUnitHelpers(unittest.TestCase):
    def test_answer_gist_truncates(self) -> None:
        long = "x" * 200
        g = flowctl.answer_gist(long)
        self.assertLessEqual(len(g), flowctl.CHART_LEDGER_GIST_MAX)
        self.assertTrue(g.endswith("..."))

    def test_scan_unsafe_fake_shapes(self) -> None:
        hits = flowctl.scan_unsafe_evidence("key=sk-FAKESECRETVALUE0000000000")
        self.assertTrue(any(h["kind"] == "secret" for h in hits))
        hits2 = flowctl.scan_unsafe_evidence("please avoid git reset --hard here")
        self.assertTrue(any(h["kind"] == "destructive_command" for h in hits2))
        self.assertEqual(flowctl.scan_unsafe_evidence("normal answer text"), [])


if __name__ == "__main__":
    unittest.main()
