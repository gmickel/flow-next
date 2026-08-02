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


class TestResolveRetryAssets(unittest.TestCase):
    def test_retry_asset_subset_noop_and_new_asset_rejected(self) -> None:
        """A retry is identical only when its assets are a subset of the
        stored set; a NEW asset after resolve is divergent evidence and must
        be refused (attach-asset also refuses resolved decisions), never
        silently dropped by a successful no-op."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Proto retry", "prototype")
            for name in ("proto.md", "extra.md"):
                (repo / name).write_text("mock\n", encoding="utf-8")
            _git(repo, "add", "proto.md", "extra.md")
            _git(repo, "commit", "-q", "-m", "assets")
            asset_a = {
                "kind": "path",
                "reference": "proto.md",
                "display": "throwaway proto",
                "revision": "r1",
            }
            asset_b = {
                "kind": "path",
                "reference": "extra.md",
                "display": "late evidence",
                "revision": "r1",
            }
            af = _write_answer(repo, "ans.txt", "Ship the layout")
            r = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--assets",
                json.dumps([asset_a]),
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)

            # Matching-subset retry: same answer, same asset -> no-op.
            r2 = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--assets",
                json.dumps([asset_a]),
                "--json",
            )
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            self.assertTrue(json.loads(r2.stdout)["result"]["noop"])

            # Same answer + NEW asset: refused, nothing persisted.
            r3 = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--assets",
                json.dumps([asset_a, asset_b]),
                "--json",
            )
            self.assertNotEqual(r3.returncode, 0)
            err = json.loads(r3.stdout)["error"]
            self.assertEqual(err["class"], "invalid_state")
            self.assertEqual(err["code"], "decision_immutable")
            self.assertEqual(err["details"]["divergent_assets"], ["extra.md"])
            side = _decision_json(flow, chart_id, 1)
            self.assertEqual(len(side["assets"]), 1)
            self.assertEqual(side["assets"][0]["reference"], "proto.md")


class TestResolveRetrySharpen(unittest.TestCase):
    def test_retry_with_sharpen_rejected_clean_retry_noops(self) -> None:
        """A resolved retry is identical only when it carries NO sharpen
        content: resolve-time sharpening creates decisions and removes
        parked questions, so a successful no-op would silently drop them.
        The clean retry (no sharpen) stays an idempotent no-op."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main question", "research")
            park_body = repo / "park.txt"
            park_body.write_text(
                "How do tenants share indexes?", encoding="utf-8"
            )
            park = _run_flowctl(
                repo, "chart", "park-question", chart_id,
                "--body-file", str(park_body), "--json",
            )
            self.assertEqual(park.returncode, 0, park.stderr)
            pkey = json.loads(park.stdout)["result"]["key"]

            af = _write_answer(repo, "ans.txt", "Shared indexes")
            r = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(af), "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)

            # Clean identical retry: no-op.
            r2 = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(af), "--json",
            )
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            self.assertTrue(json.loads(r2.stdout)["result"]["noop"])

            # Same answer + sharpen content: refused, nothing created or
            # removed - the no-op branch must not swallow it.
            sharpen = {
                "decisions": [
                    {
                        "title": "Index sharing model",
                        "type": "research",
                        "question": "Share or isolate?",
                    }
                ],
                "remove_questions": [pkey],
            }
            sf = repo / "sharpen.json"
            sf.write_text(json.dumps(sharpen), encoding="utf-8")
            r3 = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(af),
                "--sharpen-file", str(sf), "--json",
            )
            self.assertNotEqual(r3.returncode, 0)
            err = json.loads(r3.stdout)["error"]
            self.assertEqual(err["class"], "invalid_state")
            self.assertEqual(err["code"], "decision_immutable")
            ignored = err["details"]["ignored_sharpen"]
            self.assertEqual(ignored["decisions"], ["Index sharing model"])
            self.assertEqual(ignored["remove_questions"], [pkey])
            # No decision allocated, parked question intact.
            self.assertFalse(
                (flow / "charts" / chart_id / "2.json").exists()
            )
            chart = _chart_json(flow, chart_id)
            self.assertEqual(
                [q["key"] for q in chart["parked_questions"]], [pkey],
            )


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

    def test_replacement_rebinds_premises_to_superseding_decision(self) -> None:
        """A replacement created for a resolved dependent must depend on the
        SUPERSEDING decision, not the superseded premise: otherwise a later
        supersession of the superseding decision misses the replacement in
        _depends_on_closure and its stale conclusion survives the second
        reversal."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Storage choice", "research")
            a1 = _write_answer(repo, "a1.txt", "Pick Postgres")
            r1 = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(a1), "--json",
            )
            self.assertEqual(r1.returncode, 0, r1.stderr)
            # D2 resolved, depends on D1.
            d2 = _add_decision(
                repo, chart_id, "Migration path", "research", depends_on="D1",
            )
            a2 = _write_answer(repo, "a2.txt", "Big-bang migration")
            r2 = _run_flowctl(
                repo, "chart", "resolve", d2["id"],
                "--answer-file", str(a2), "--json",
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)

            # First reversal: D3 supersedes D1 -> replacement for D2.
            d3 = _add_decision(repo, chart_id, "Revisit storage", "research")
            a3 = _write_answer(repo, "a3.txt", "Pick SQLite")
            r3 = _run_flowctl(
                repo, "chart", "resolve", d3["id"],
                "--answer-file", str(a3), "--supersedes", "D1", "--json",
            )
            self.assertEqual(r3.returncode, 0, r3.stderr + r3.stdout)
            res3 = json.loads(r3.stdout)["result"]
            self.assertEqual(len(res3["replacements"]), 1)
            rep_id = res3["replacements"][0]["id"]
            rep_n = int(rep_id.rsplit("D", 1)[1])
            rep_side = _decision_json(flow, chart_id, rep_n)
            # Premise rebound: superseded D1 -> superseding D3.
            self.assertEqual(rep_side["depends_on"], [d3["id"]])
            note = rep_side["transition_notes"][0]
            self.assertEqual(
                note.get("rebound_premises"), {d1["id"]: d3["id"]},
            )
            self.assertIn("premises rebound", note["text"])

            # Resolve the replacement so it becomes a resolved dependent
            # of D3.
            ar = _write_answer(repo, "ar.txt", "Streamed migration")
            rr = _run_flowctl(
                repo, "chart", "resolve", rep_id,
                "--answer-file", str(ar), "--json",
            )
            self.assertEqual(rr.returncode, 0, rr.stderr + rr.stdout)

            # Second reversal: D5 supersedes D3. The closure must now find
            # the replacement (its premise was rebound to D3) and mint its
            # own replacement instead of leaving the stale conclusion.
            d5 = _add_decision(repo, chart_id, "Re-revisit storage", "research")
            a5 = _write_answer(repo, "a5.txt", "Back to Postgres")
            r5 = _run_flowctl(
                repo, "chart", "resolve", d5["id"],
                "--answer-file", str(a5), "--supersedes", d3["id"], "--json",
            )
            self.assertEqual(r5.returncode, 0, r5.stderr + r5.stdout)
            res5 = json.loads(r5.stdout)["result"]
            self.assertIn(rep_id, res5["cascade_resolved"])
            self.assertEqual(len(res5["replacements"]), 1)
            rep2_id = res5["replacements"][0]["id"]
            rep_after = _decision_json(flow, chart_id, rep_n)
            self.assertEqual(rep_after["status"], "superseded")
            self.assertEqual(rep_after["superseded_by"], rep2_id)
            rep2_side = _decision_json(
                flow, chart_id, int(rep2_id.rsplit("D", 1)[1])
            )
            self.assertEqual(rep2_side["depends_on"], [d5["id"]])

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


class TestPremiseFirstCascade(unittest.TestCase):
    """fn-153.1: the supersession cascade must process dependents
    premise-first, so a replacement is wired to the replacement of a premise
    this same cascade superseded - never to the superseded premise itself."""

    def _wire(self, repo: Path, did: str, depends_on: str) -> None:
        r = _run_flowctl(
            repo, "chart", "wire-decision", did, "--depends-on", depends_on, "--json"
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)

    def _resolve(self, repo: Path, did: str, text: str, *extra: str) -> dict:
        answer = _write_answer(repo, f"ans-{did.replace('.', '-')}.txt", text)
        r = _run_flowctl(
            repo,
            "chart",
            "resolve",
            did,
            "--answer-file",
            str(answer),
            *extra,
            "--json",
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return json.loads(r.stdout)["result"]

    def _non_topological_chart(self, repo: Path) -> tuple[str, list[dict]]:
        """D2 depends on D3, D3 depends on D1 - local number order is NOT
        premise order. `_add_decision` allocates strictly in creation order
        and cannot build this shape; `wire-decision` can."""
        chart_id = _create_chart(repo)
        decisions = [
            _add_decision(repo, chart_id, "Storage choice", "research"),
            _add_decision(repo, chart_id, "Migration path", "research"),
            _add_decision(repo, chart_id, "Cache layer", "research"),
            _add_decision(repo, chart_id, "Revisit storage", "research"),
        ]
        self._wire(repo, decisions[1]["id"], "D3")
        self._wire(repo, decisions[2]["id"], "D1")
        self._resolve(repo, decisions[2]["id"], "Redis in front of Postgres")
        self._resolve(repo, decisions[1]["id"], "Big-bang migration weekend")
        return chart_id, decisions

    def test_replacement_wired_to_replacement_not_superseded_premise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, decisions = self._non_topological_chart(repo)
            d1, d2, d3, d4 = (d["id"] for d in decisions)

            res = self._resolve(
                repo, d4, "Pick SQLite for the embedded edge case", "--supersedes", "D1"
            )
            rep_d3 = f"{chart_id}.D5"
            rep_d2 = f"{chart_id}.D6"

            # Premise-first: D3 (whose premise D1 is superseded here) is
            # cascaded before its own dependent D2.
            self.assertEqual(res["cascade_resolved"], [d3, d2])
            self.assertEqual(res["cascade_open"], [])
            self.assertEqual(
                [(r["id"], r["replaces"]) for r in res["replacements"]],
                [(rep_d3, d3), (rep_d2, d2)],
            )
            self.assertEqual(res["affected"], [d4, d1, d3, rep_d3, d2, rep_d2])

            # D3's replacement rebinds the superseded premise D1 -> D4.
            rep_d3_side = _decision_json(flow, chart_id, 5)
            self.assertEqual(rep_d3_side["depends_on"], [d4])
            # The core fix: D2's replacement points at D3's REPLACEMENT, not
            # at the superseded D3.
            rep_d2_side = _decision_json(flow, chart_id, 6)
            self.assertEqual(rep_d2_side["depends_on"], [rep_d3])
            self.assertEqual(
                rep_d2_side["transition_notes"][0].get("rebound_premises"),
                {d3: rep_d3},
            )

            # The whole chain stays reachable: resolve both replacements, then
            # supersede D3's replacement and the cascade must still find D2's.
            self._resolve(repo, rep_d3, "Streamed migration")
            self._resolve(repo, rep_d2, "Cache after migration")
            d7 = _add_decision(repo, chart_id, "Re-revisit migration", "research")["id"]
            res7 = self._resolve(
                repo, d7, "Back to a big-bang weekend", "--supersedes", rep_d3
            )
            self.assertEqual(res7["cascade_resolved"], [rep_d2])
            self.assertEqual(len(res7["replacements"]), 1)
            rep2_d2 = res7["replacements"][0]["id"]
            self.assertEqual(rep2_d2, f"{chart_id}.D8")
            self.assertEqual(
                _decision_json(flow, chart_id, 8)["depends_on"], [d7]
            )
            self.assertEqual(
                _decision_json(flow, chart_id, 6)["superseded_by"], rep2_d2
            )

    def _tie_run(self, repo: Path) -> dict:
        """D2 and D3 both depend only on D1: a genuine tie at the Kahn
        frontier, broken by ascending local D-number."""
        _init_repo(repo)
        _init_flow(repo)
        chart_id = _create_chart(repo)
        d1 = _add_decision(repo, chart_id, "Storage choice", "research")["id"]
        d2 = _add_decision(
            repo, chart_id, "Migration path", "research", depends_on="D1"
        )["id"]
        d3 = _add_decision(
            repo, chart_id, "Cache layer", "research", depends_on="D1"
        )["id"]
        d4 = _add_decision(repo, chart_id, "Revisit storage", "research")["id"]
        self._resolve(repo, d1, "Pick Postgres")
        self._resolve(repo, d2, "Big-bang migration weekend")
        self._resolve(repo, d3, "Redis in front of Postgres")
        res = self._resolve(repo, d4, "Pick SQLite", "--supersedes", "D1")
        return {
            "chart_id": chart_id,
            "ids": [d1, d2, d3, d4],
            "affected": res["affected"],
            "cascade_open": res["cascade_open"],
            "cascade_resolved": res["cascade_resolved"],
            "replacements": [
                (r["id"], r["replaces"]) for r in res["replacements"]
            ],
        }

    def test_tie_order_is_deterministic_and_ascending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = self._tie_run(Path(tmp) / "repo-a")
            chart_id = first["chart_id"]
            d1, d2, d3, d4 = first["ids"]
            rep_d2 = f"{chart_id}.D5"
            rep_d3 = f"{chart_id}.D6"
            # Exact arrays, not membership: `affected` opens with the primary
            # decision and the named --supersedes target in caller order; the
            # closure-derived tail is what Kahn determines.
            self.assertEqual(first["affected"], [d4, d1, d2, rep_d2, d3, rep_d3])
            self.assertEqual(first["cascade_resolved"], [d2, d3])
            self.assertEqual(first["cascade_open"], [])
            self.assertEqual(
                first["replacements"], [(rep_d2, d2), (rep_d3, d3)]
            )

            # Same ordered inputs on an equivalent fixture reproduce them.
            second = self._tie_run(Path(tmp) / "repo-b")
            self.assertEqual(second, first)

    def test_keep_dependents_order_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, decisions = self._non_topological_chart(repo)
            d1, d2, d3, d4 = (d["id"] for d in decisions)

            res = self._resolve(
                repo,
                d4,
                "Pick SQLite for the embedded edge case",
                "--supersedes",
                "D1",
                "--keep-dependents",
            )
            # Full arrays pinned: the keep branch keeps emitting dependents in
            # local-number order even on a non-topological graph.
            self.assertTrue(res["keep_dependents"])
            self.assertEqual(res["affected"], [d4, d1, d2, d3])
            self.assertEqual(res["cascade_open"], [])
            self.assertEqual(res["cascade_resolved"], [])
            self.assertEqual(res["replacements"], [])
            for n in (2, 3):
                kinds = [
                    note.get("kind")
                    for note in _decision_json(flow, chart_id, n).get(
                        "transition_notes"
                    )
                    or []
                ]
                self.assertIn("keep_dependents", kinds)


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

    def test_refuse_unsafe_prose_in_sharpen_created_decision(self) -> None:
        """Sharpening CREATES decisions (R20/R48): a sharpen-file decision
        whose title/question embeds a secret shape refuses before anything -
        answer, removals, or the new decision - persists."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main question", "research")
            sharpen = {
                "decisions": [
                    {
                        "title": "Creds follow-up",
                        "type": "research",
                        # Obviously fake credential shape.
                        "question": "rotate password=hunter2-FAKE first?",
                    }
                ],
            }
            sf = repo / "sharpen.json"
            sf.write_text(json.dumps(sharpen), encoding="utf-8")
            af = _write_answer(repo, "ans.txt", "Safe answer text")
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
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)["error"]
            self.assertEqual(err["class"], "validation")
            self.assertEqual(err["code"], "unsafe_prose_content")
            # Nothing persisted: decision still open, no D2 allocated.
            self.assertEqual(_decision_json(flow, chart_id, 1)["status"], "open")
            self.assertFalse((flow / "charts" / chart_id / "2.json").exists())

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
