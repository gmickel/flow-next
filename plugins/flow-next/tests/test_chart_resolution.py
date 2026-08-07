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
import re
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


class TestNotesAppend(unittest.TestCase):
    """fn-170.1: resolve --sharpen-file notes_append + unknown-key rejection."""

    def _sharpen_file(self, repo: Path, name: str, payload: dict) -> Path:
        p = repo / name
        p.write_text(json.dumps(payload), encoding="utf-8")
        return p

    def test_no_notes_section_creates_it(self) -> None:
        """A chart body predating the Notes feature (heading missing
        entirely) must not crash; _replace_chart_section appends it."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main question", "research")

            # Strip the ## Notes section entirely to simulate a pre-feature
            # chart body.
            md_path = flow / "charts" / f"{chart_id}.md"
            body = md_path.read_text(encoding="utf-8")
            body = re.sub(
                r"^##\s+Notes\s*\n.*?(?=^##\s+)",
                "",
                body,
                count=1,
                flags=re.MULTILINE | re.DOTALL,
            )
            self.assertNotIn("## Notes", body)
            md_path.write_text(body, encoding="utf-8")

            sf = self._sharpen_file(
                repo, "s.json",
                {"notes_append": "the auth module DOES have tests"},
            )
            af = _write_answer(repo, "ans.txt", "Answer text")
            r = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(af), "--sharpen-file", str(sf), "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            result = json.loads(r.stdout)["result"]
            self.assertEqual(len(result["notes_appended"]), 1)
            self.assertIn(
                "the auth module DOES have tests", result["notes_appended"][0]
            )
            body_after = _chart_md(flow, chart_id)
            self.assertIn("## Notes", body_after)
            self.assertIn("- [corrected ", body_after)
            self.assertIn("the auth module DOES have tests", body_after)

    def test_mixed_bulleting_normalized(self) -> None:
        """Lines already carrying `- ` keep their marker; bare lines get
        one; each bullet gets its own date stamp."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main question", "research")
            sf = self._sharpen_file(
                repo, "s.json",
                {
                    "notes_append": (
                        "- already bulleted fact\n"
                        "bare fact without a marker\n"
                    )
                },
            )
            af = _write_answer(repo, "ans.txt", "Answer text")
            r = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(af), "--sharpen-file", str(sf), "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            result = json.loads(r.stdout)["result"]
            self.assertEqual(len(result["notes_appended"]), 2)
            for bullet in result["notes_appended"]:
                self.assertRegex(bullet, r"^- \[corrected \d{4}-\d{2}-\d{2}\] ")
            self.assertIn("already bulleted fact", result["notes_appended"][0])
            self.assertIn(
                "bare fact without a marker", result["notes_appended"][1]
            )
            body = _chart_md(flow, chart_id)
            self.assertIn("already bulleted fact", body)
            self.assertIn("bare fact without a marker", body)

    def test_leading_hyphen_prose_preserved(self) -> None:
        """A leading hyphen without a following space (`--legacy`, `-5 ms`)
        is prose, not a bullet marker - the hyphen must survive intact.
        Only `- ` (and a bare `-`, the empty markdown bullet) is stripped."""
        bullets = flowctl._format_notes_append_bullets(
            "--legacy\n-5 ms\n- real bullet\n-\nplain prose\n",
            "2026-08-08",
        )
        self.assertEqual(
            bullets,
            [
                "- [corrected 2026-08-08] --legacy",
                "- [corrected 2026-08-08] -5 ms",
                "- [corrected 2026-08-08] real bullet",
                "- [corrected 2026-08-08] ",
                "- [corrected 2026-08-08] plain prose",
            ],
        )

    def test_backslash_content_not_corrupted(self) -> None:
        """_replace_chart_section substitutes via a lambda (literal text);
        a correction containing regex backreference shapes must survive
        byte-for-byte."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main question", "research")
            sf = self._sharpen_file(
                repo, "s.json",
                {"notes_append": r"matches \d+ occurrences, not \1 or \g<0>"},
            )
            af = _write_answer(repo, "ans.txt", "Answer text")
            r = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(af), "--sharpen-file", str(sf), "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            body = _chart_md(flow, chart_id)
            self.assertIn(r"matches \d+ occurrences, not \1 or \g<0>", body)

    def test_two_sequential_appends_both_survive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Question one", "research")
            d2 = _add_decision(repo, chart_id, "Question two", "research")

            sf1 = self._sharpen_file(
                repo, "s1.json", {"notes_append": "first correction"}
            )
            af1 = _write_answer(repo, "ans1.txt", "Answer one")
            r1 = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(af1), "--sharpen-file", str(sf1), "--json",
            )
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)

            sf2 = self._sharpen_file(
                repo, "s2.json", {"notes_append": "second correction"}
            )
            af2 = _write_answer(repo, "ans2.txt", "Answer two")
            r2 = _run_flowctl(
                repo, "chart", "resolve", d2["id"],
                "--answer-file", str(af2), "--sharpen-file", str(sf2), "--json",
            )
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)

            body = _chart_md(flow, chart_id)
            self.assertIn("first correction", body)
            self.assertIn("second correction", body)

    def test_existing_notes_bytes_preserved_verbatim(self) -> None:
        """R1: an append never rewrites pre-existing Notes bytes. The
        original section body (including internal blank lines and odd
        spacing) survives as an exact byte prefix, and the blank
        separator line before the next heading stays intact - the old
        strip()-and-rerender path normalized both."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main question", "research")

            md_path = flow / "charts" / f"{chart_id}.md"
            body = md_path.read_text(encoding="utf-8")
            seeded = (
                "- pre-existing  note   with  odd  spacing\n"
                "\n"
                "- second note\n"
                "\n"
            )
            pattern = re.compile(
                r"(^##\s+Notes\s*\n)(.*?)(?=^##\s+|\Z)",
                re.MULTILINE | re.DOTALL,
            )
            self.assertIsNotNone(pattern.search(body))
            body = pattern.sub(lambda m: m.group(1) + seeded, body, count=1)
            md_path.write_text(body, encoding="utf-8")

            sf = self._sharpen_file(
                repo, "s.json", {"notes_append": "fresh correction"}
            )
            af = _write_answer(repo, "ans.txt", "Answer text")
            r = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(af), "--sharpen-file", str(sf), "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)

            body_after = _chart_md(flow, chart_id)
            m = pattern.search(body_after)
            self.assertIsNotNone(m)
            new_raw = m.group(2)
            core = seeded.rstrip("\n")
            # Pre-existing bytes verbatim as a prefix...
            self.assertTrue(
                new_raw.startswith(core + "\n"),
                f"pre-existing Notes bytes rewritten: {new_raw!r}",
            )
            # ...new bullet spliced after them, and the trailing blank
            # separator before the next heading preserved.
            self.assertRegex(
                new_raw,
                re.escape(core)
                + r"\n- \[corrected \d{4}-\d{2}-\d{2}\] fresh correction\n\n\Z",
            )

    def test_unknown_key_rejected_before_prose_refusal(self) -> None:
        """A payload with BOTH an unknown key and unsafe-looking notes
        prose must fail sharpen_file_unknown_key, never
        unsafe_prose_content - the structural check runs first (R3)."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main question", "research")
            sf = self._sharpen_file(
                repo, "s.json",
                {
                    "notes": "token is sk-FAKESECRETVALUE0000000000",
                    "notes_append": "token is sk-FAKESECRETVALUE0000000000",
                },
            )
            af = _write_answer(repo, "ans.txt", "Answer text")
            r = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(af), "--sharpen-file", str(sf), "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)["error"]
            self.assertEqual(err["code"], "sharpen_file_unknown_key")
            self.assertIn("notes", err["details"]["unknown_keys"])
            self.assertEqual(
                _decision_json(flow, chart_id, 1)["status"], "open"
            )

    def test_unknown_key_alone_lists_offending_and_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main question", "research")
            sf = self._sharpen_file(repo, "s.json", {"typo_key": "oops"})
            af = _write_answer(repo, "ans.txt", "Answer text")
            r = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(af), "--sharpen-file", str(sf), "--json",
            )
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)["error"]
            self.assertEqual(err["code"], "sharpen_file_unknown_key")
            self.assertEqual(err["details"]["unknown_keys"], ["typo_key"])
            for key in (
                "decisions", "remove_questions", "remove_parked",
                "parked_removals", "notes_append",
            ):
                self.assertIn(key, err["details"]["accepted_keys"])

    def test_alias_keys_still_accepted(self) -> None:
        """remove_parked / parked_removals aliases remain accepted (R3)."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main question", "research")
            park_body = repo / "park.txt"
            park_body.write_text("A parked fact", encoding="utf-8")
            park = _run_flowctl(
                repo, "chart", "park-question", chart_id,
                "--body-file", str(park_body), "--json",
            )
            pkey = json.loads(park.stdout)["result"]["key"]
            sf = self._sharpen_file(
                repo, "s.json", {"remove_parked": [pkey]}
            )
            af = _write_answer(repo, "ans.txt", "Answer text")
            r = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(af), "--sharpen-file", str(sf), "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)

    def test_empty_whitespace_and_nonstring_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main question", "research")
            af = _write_answer(repo, "ans.txt", "Answer text")
            for bad in ("", "   \n  ", 5, ["not", "a", "string"]):
                sf = self._sharpen_file(
                    repo, "s.json", {"notes_append": bad}
                )
                r = _run_flowctl(
                    repo, "chart", "resolve", d1["id"],
                    "--answer-file", str(af),
                    "--sharpen-file", str(sf), "--json",
                )
                self.assertNotEqual(r.returncode, 0, bad)
                err = json.loads(r.stdout)["error"]
                self.assertEqual(err["code"], "sharpen_file_invalid_notes_append")
            self.assertEqual(
                _decision_json(flow, chart_id, 1)["status"], "open"
            )

    def test_explicit_null_rejected_not_conflated_with_absent(self) -> None:
        """An explicitly present null must fail the key's type contract,
        never be treated as an omitted key (codex review, PR #299)."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main question", "research")
            af = _write_answer(repo, "ans.txt", "Answer text")
            cases = [
                ({"notes_append": None}, "sharpen_file_invalid_notes_append"),
                ({"decisions": None}, "sharpen_file_invalid_decisions"),
                ({"remove_questions": None}, "sharpen_file_invalid_removals"),
                ({"remove_parked": None}, "sharpen_file_invalid_removals"),
                ({"parked_removals": None}, "sharpen_file_invalid_removals"),
            ]
            for payload, code in cases:
                sf = self._sharpen_file(repo, "s.json", payload)
                r = _run_flowctl(
                    repo, "chart", "resolve", d1["id"],
                    "--answer-file", str(af),
                    "--sharpen-file", str(sf), "--json",
                )
                self.assertNotEqual(r.returncode, 0, payload)
                err = json.loads(r.stdout)["error"]
                self.assertEqual(err["code"], code, payload)
            self.assertEqual(
                _decision_json(flow, chart_id, 1)["status"], "open"
            )

    def test_notes_appended_always_list_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main question", "research")
            af = _write_answer(repo, "ans.txt", "Answer text")
            r = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(af), "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            result = json.loads(r.stdout)["result"]
            self.assertEqual(result["notes_appended"], [])

    def test_identical_retry_with_notes_append_ignored_no_double_append(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main question", "research")
            af = _write_answer(repo, "ans.txt", "Answer text")
            r1 = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(af), "--json",
            )
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)

            sf = self._sharpen_file(
                repo, "s.json", {"notes_append": "a late correction"}
            )
            r2 = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(af),
                "--sharpen-file", str(sf), "--json",
            )
            self.assertNotEqual(r2.returncode, 0)
            err = json.loads(r2.stdout)["error"]
            self.assertEqual(err["class"], "invalid_state")
            self.assertEqual(err["code"], "decision_immutable")
            self.assertEqual(
                err["details"]["ignored_sharpen"]["notes_append"],
                ["a late correction"],
            )
            body = _chart_md(flow, chart_id)
            self.assertNotIn("a late correction", body)

    def test_post_reopen_resolve_appends_fresh(self) -> None:
        """A chart-level reopen does not retroactively unresolve any
        decision; a fresh decision created and resolved after reopen is a
        normal (non-retry) resolve and appends its correction."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Main question", "research")
            af = _write_answer(repo, "ans.txt", "Answer text")
            r1 = _run_flowctl(
                repo, "chart", "resolve", d1["id"],
                "--answer-file", str(af), "--json",
            )
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)

            prop = repo / "prop.json"
            prop.write_text(
                json.dumps(
                    {
                        "clusters": [
                            {
                                "key": "1",
                                "rationale": "sole surface",
                                "decisions": [d1["id"]],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            brief = _run_flowctl(
                repo, "chart", "briefing", chart_id,
                "--proposal-file", str(prop), "--json",
            )
            self.assertEqual(brief.returncode, 0, brief.stderr + brief.stdout)
            self.assertEqual(_chart_json(flow, chart_id)["status"], "done")

            reopen = _run_flowctl(
                repo, "chart", "reopen", chart_id,
                "--reason", "premise disproved during downstream work",
                "--json",
            )
            self.assertEqual(reopen.returncode, 0, reopen.stderr + reopen.stdout)
            self.assertEqual(_chart_json(flow, chart_id)["status"], "open")

            d2 = _add_decision(repo, chart_id, "Follow-up question", "research")
            sf = self._sharpen_file(
                repo, "s.json", {"notes_append": "premise 1 disproved"}
            )
            af2 = _write_answer(repo, "ans2.txt", "Follow-up answer")
            r2 = _run_flowctl(
                repo, "chart", "resolve", d2["id"],
                "--answer-file", str(af2),
                "--sharpen-file", str(sf), "--json",
            )
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            result = json.loads(r2.stdout)["result"]
            self.assertEqual(len(result["notes_appended"]), 1)
            body = _chart_md(flow, chart_id)
            self.assertIn("premise 1 disproved", body)


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
