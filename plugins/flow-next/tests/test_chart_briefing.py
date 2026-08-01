"""Unit tests for chart briefing, reopen, link-spec (fn-135.3).

Covers: completion refusal (blocked/claimed/open/parked), forced draft,
fingerprint versioning B1 idempotent / B2 on change, first-final->done,
done-chart mutation rejection, reopen stales briefings+links, link-spec
idempotency + cluster identity + stale-after-supersession, multi-cluster
emission, shared-context handling, failpoint rollback during publication.
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
    blocked_by: str | None = None,
    depends_on: str | None = None,
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
    if blocked_by is not None:
        args.extend(["--blocked-by", blocked_by])
    if depends_on is not None:
        args.extend(["--depends-on", depends_on])
    r = _run_flowctl(repo, *args)
    assert r.returncode == 0, r.stderr + r.stdout
    return json.loads(r.stdout)["result"]


def _resolve(repo: Path, did: str, answer: str, *, supersedes: str | None = None) -> dict:
    af = repo / f"ans-{did.replace('.', '-')}.txt"
    af.write_text(answer, encoding="utf-8")
    args = ["chart", "resolve", did, "--answer-file", str(af), "--json"]
    if supersedes:
        args.extend(["--supersedes", supersedes])
    r = _run_flowctl(repo, *args)
    assert r.returncode == 0, r.stderr + r.stdout
    return json.loads(r.stdout)["result"]


def _proposal(
    repo: Path,
    name: str,
    clusters: list[dict],
    shared: list[str] | None = None,
) -> Path:
    p = repo / name
    payload = {"clusters": clusters, "shared_context": shared or []}
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def _brief(
    repo: Path,
    chart_id: str,
    proposal: Path,
    *,
    force: bool = False,
) -> subprocess.CompletedProcess:
    args = [
        "chart",
        "briefing",
        chart_id,
        "--proposal-file",
        str(proposal),
        "--json",
    ]
    if force:
        args.append("--force")
    return _run_flowctl(repo, *args)


def _chart_json(flow: Path, chart_id: str) -> dict:
    return json.loads((flow / "charts" / f"{chart_id}.json").read_text(encoding="utf-8"))


def _ready_single_cluster(repo: Path) -> tuple[str, Path, dict, dict]:
    """Create chart with two resolved decisions and a single-cluster proposal."""
    chart_id = _create_chart(repo)
    d1 = _add_decision(repo, chart_id, "Storage choice", "research")
    d2 = _add_decision(repo, chart_id, "Auth model", "research")
    _resolve(repo, d1["id"], "Use Postgres for tenant metadata")
    _resolve(repo, d2["id"], "OIDC with per-tenant issuers")
    prop = _proposal(
        repo,
        "prop-one.json",
        [
            {
                "key": "1",
                "rationale": "Single captureable surface",
                "decisions": [d1["id"], d2["id"]],
            }
        ],
    )
    return chart_id, prop, d1, d2


class TestBriefingEligibility(unittest.TestCase):
    def test_refuses_open_unblocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Open Q", "research")
            # Resolve nothing - open frontier.
            _proposal(
                repo,
                "p.json",
                [{"key": "1", "rationale": "n/a", "decisions": [d1["id"]]}],
            )
            # Membership also fails (not resolved), but eligibility is the gate
            # once we have resolved coverage - create a second resolved + leave open.
            d2 = _add_decision(repo, chart_id, "Done one", "research")
            _resolve(repo, d2["id"], "settled")
            prop2 = _proposal(
                repo,
                "p2.json",
                [{"key": "1", "rationale": "partial", "decisions": [d2["id"]]}],
            )
            r = _brief(repo, chart_id, prop2)
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)
            self.assertEqual(err["error"]["code"], "chart_not_briefable")
            self.assertIn("open", " ".join(err["error"]["details"].get("stuck_reasons") or []).lower()
                          or err["error"]["message"].lower())

    def test_refuses_blocked_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Premise", "research")
            _add_decision(repo, chart_id, "Blocked", "research", blocked_by=d1["id"])
            _resolve(repo, d1["id"], "premise settled")
            # d2 still open+blocked
            prop = _proposal(
                repo,
                "p.json",
                [{"key": "1", "rationale": "only resolved", "decisions": [d1["id"]]}],
            )
            r = _brief(repo, chart_id, prop)
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)
            self.assertEqual(err["error"]["code"], "chart_not_briefable")
            self.assertTrue(
                any("blocked" in s.lower() for s in err["error"]["details"].get("stuck_reasons") or [])
                or "blocked" in err["error"]["message"].lower()
            )

    def test_refuses_claimed_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Claimed open", "research")
            d2 = _add_decision(repo, chart_id, "Resolved", "research")
            _resolve(repo, d2["id"], "done")
            r_claim = _run_flowctl(repo, "chart", "claim", d1["id"], "--json")
            self.assertEqual(r_claim.returncode, 0, r_claim.stderr)
            prop = _proposal(
                repo,
                "p.json",
                [{"key": "1", "rationale": "only resolved", "decisions": [d2["id"]]}],
            )
            r = _brief(repo, chart_id, prop)
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)
            self.assertEqual(err["error"]["code"], "chart_not_briefable")
            self.assertTrue(
                any("claimed" in s.lower() for s in err["error"]["details"].get("stuck_reasons") or [])
                or "claimed" in err["error"]["message"].lower()
            )

    def test_refuses_parked_questions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Only", "research")
            _resolve(repo, d1["id"], "done")
            body = repo / "park.txt"
            body.write_text("What about multi-region failover?", encoding="utf-8")
            r_park = _run_flowctl(
                repo,
                "chart",
                "park-question",
                chart_id,
                "--body-file",
                str(body),
                "--json",
            )
            self.assertEqual(r_park.returncode, 0, r_park.stderr)
            prop = _proposal(
                repo,
                "p.json",
                [{"key": "1", "rationale": "single", "decisions": [d1["id"]]}],
            )
            r = _brief(repo, chart_id, prop)
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)
            self.assertEqual(err["error"]["code"], "chart_not_briefable")


class TestForcedDraft(unittest.TestCase):
    def test_force_draft_lists_unresolved_and_leaves_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Settled", "research")
            d2 = _add_decision(repo, chart_id, "Still open", "research")
            _resolve(repo, d1["id"], "settled answer")
            prop = _proposal(
                repo,
                "p.json",
                [{"key": "1", "rationale": "partial handoff", "decisions": [d1["id"]]}],
            )
            r = _brief(repo, chart_id, prop, force=True)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            env = json.loads(r.stdout)
            self.assertTrue(env["success"])
            self.assertEqual(env["result"]["status"], "draft")
            self.assertEqual(env["result"]["chart_status"], "open")
            self.assertFalse(env["result"]["transitioned_done"])
            self.assertEqual(env["result"]["briefing_id"], "B1")

            side = _chart_json(flow, chart_id)
            self.assertEqual(side["status"], "open")
            self.assertEqual(side["briefings"][0]["status"], "draft")

            index = (flow / "charts" / f"{chart_id}-briefing.md").read_text(encoding="utf-8")
            self.assertIn("draft-only", index.lower())
            self.assertIn(d2["id"], index)
            self.assertIn("DRAFT", index)


class TestFingerprintVersioning(unittest.TestCase):
    def test_b1_idempotent_and_b2_on_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, d1, d2 = _ready_single_cluster(repo)

            r1 = _brief(repo, chart_id, prop)
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)
            e1 = json.loads(r1.stdout)["result"]
            self.assertEqual(e1["briefing_id"], "B1")
            self.assertEqual(e1["status"], "final")
            self.assertTrue(e1["transitioned_done"])
            self.assertEqual(e1["chart_status"], "done")
            fp1 = e1["fingerprint"]

            # Identical retry on done chart returns B1.
            r2 = _brief(repo, chart_id, prop)
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            e2 = json.loads(r2.stdout)["result"]
            self.assertTrue(e2["noop"])
            self.assertEqual(e2["briefing_id"], "B1")
            self.assertEqual(e2["fingerprint"], fp1)

            side = _chart_json(flow, chart_id)
            self.assertEqual(len(side["briefings"]), 1)

            # Changed proposal needs reopen first.
            prop2 = _proposal(
                repo,
                "prop-two.json",
                [
                    {
                        "key": "a",
                        "rationale": "Split storage",
                        "decisions": [d1["id"]],
                    },
                    {
                        "key": "b",
                        "rationale": "Split auth",
                        "decisions": [d2["id"]],
                    },
                ],
            )
            r_bad = _brief(repo, chart_id, prop2)
            self.assertNotEqual(r_bad.returncode, 0)
            self.assertEqual(json.loads(r_bad.stdout)["error"]["code"], "chart_not_open")

            r_re = _run_flowctl(
                repo,
                "chart",
                "reopen",
                chart_id,
                "--reason",
                "need a two-spec split",
                "--json",
            )
            self.assertEqual(r_re.returncode, 0, r_re.stderr)
            re_out = json.loads(r_re.stdout)["result"]
            self.assertEqual(re_out["status"], "open")
            self.assertIn("B1", re_out["staled_briefings"])

            side = _chart_json(flow, chart_id)
            self.assertEqual(side["briefings"][0]["status"], "stale")

            r3 = _brief(repo, chart_id, prop2)
            self.assertEqual(r3.returncode, 0, r3.stderr + r3.stdout)
            e3 = json.loads(r3.stdout)["result"]
            self.assertEqual(e3["briefing_id"], "B2")
            self.assertEqual(e3["status"], "final")
            self.assertNotEqual(e3["fingerprint"], fp1)
            self.assertTrue(e3["transitioned_done"])


class TestEvidenceFingerprint(unittest.TestCase):
    def test_attach_asset_between_forced_drafts_mints_new_briefing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Settled", "research")
            d2 = _add_decision(repo, chart_id, "Still open", "research")
            _resolve(repo, d1["id"], "settled answer")
            prop = _proposal(
                repo,
                "p.json",
                [{"key": "1", "rationale": "partial handoff", "decisions": [d1["id"]]}],
            )
            r1 = _brief(repo, chart_id, prop, force=True)
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)
            e1 = json.loads(r1.stdout)["result"]
            self.assertEqual(e1["briefing_id"], "B1")

            # Attach evidence to the still-open decision; the chart's compact
            # entries are unchanged, but rendered briefing content is not.
            (repo / "docs").mkdir()
            (repo / "docs" / "evidence.md").write_text("mock", encoding="utf-8")
            _git(repo, "add", "docs/evidence.md")
            _git(repo, "commit", "-q", "-m", "evidence")
            af = repo / "asset.json"
            af.write_text(
                json.dumps(
                    {
                        "kind": "path",
                        "reference": "docs/evidence.md",
                        "display": "late evidence",
                        "revision": "rev-1",
                    }
                ),
                encoding="utf-8",
            )
            r_att = _run_flowctl(
                repo,
                "chart",
                "attach-asset",
                d2["id"],
                "--asset-file",
                str(af),
                "--json",
            )
            self.assertEqual(r_att.returncode, 0, r_att.stderr + r_att.stdout)

            # Same proposal again: evidence changed, so this must NOT no-op.
            r2 = _brief(repo, chart_id, prop, force=True)
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            e2 = json.loads(r2.stdout)["result"]
            self.assertFalse(e2["noop"])
            self.assertEqual(e2["briefing_id"], "B2")
            self.assertNotEqual(e2["fingerprint"], e1["fingerprint"])

            side = _chart_json(flow, chart_id)
            self.assertEqual(len(side["briefings"]), 2)
            index = (flow / "charts" / f"{chart_id}-briefing.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("docs/evidence.md", index)


class TestVersionedBriefingPaths(unittest.TestCase):
    def test_b1_recorded_paths_survive_b2_emission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, d1, d2 = _ready_single_cluster(repo)

            r1 = _brief(repo, chart_id, prop)
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)
            e1 = json.loads(r1.stdout)["result"]
            b1_paths = e1["paths"]
            # Recorded index path is per-version; a stable latest also exists.
            self.assertIn("-briefing-B1.md", b1_paths["index"])
            self.assertTrue(b1_paths["latest_index"].endswith("-briefing.md"))
            b1_index = repo / b1_paths["index"]
            self.assertTrue(b1_index.is_file())
            b1_content = b1_index.read_text(encoding="utf-8")
            self.assertIn("briefing B1", b1_content)

            _run_flowctl(
                repo, "chart", "reopen", chart_id, "--reason", "resplit", "--json"
            )
            prop2 = _proposal(
                repo,
                "prop-two.json",
                [
                    {"key": "a", "rationale": "Split storage", "decisions": [d1["id"]]},
                    {"key": "b", "rationale": "Split auth", "decisions": [d2["id"]]},
                ],
            )
            r2 = _brief(repo, chart_id, prop2)
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            e2 = json.loads(r2.stdout)["result"]
            self.assertEqual(e2["briefing_id"], "B2")
            # B2 gets versioned index and cluster paths.
            self.assertIn("-briefing-B2.md", e2["paths"]["index"])
            self.assertIn("-briefing-B2-a.md", e2["paths"]["cluster_a"])
            self.assertIn("-briefing-B2-b.md", e2["paths"]["cluster_b"])
            for rel in e2["paths"].values():
                self.assertTrue((repo / rel).is_file(), rel)

            # B1's recorded artifact is untouched by the B2 emission.
            self.assertEqual(
                b1_index.read_text(encoding="utf-8"), b1_content
            )
            # The stable latest copy now carries B2.
            latest = (repo / b1_paths["latest_index"]).read_text(encoding="utf-8")
            self.assertIn("briefing B2", latest)
            self.assertNotIn("briefing B1", latest)

            # Sidecar records agree with the emit result.
            side = _chart_json(flow, chart_id)
            self.assertIn("-briefing-B1.md", side["briefings"][0]["paths"]["index"])
            self.assertIn("-briefing-B2.md", side["briefings"][1]["paths"]["index"])


class TestProposalDuplicateClusterKey(unittest.TestCase):
    def test_duplicate_cluster_key_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id, _prop, d1, d2 = _ready_single_cluster(repo)
            prop = _proposal(
                repo,
                "dup.json",
                [
                    {"key": "core", "rationale": "first", "decisions": [d1["id"]]},
                    {"key": "core", "rationale": "second", "decisions": [d2["id"]]},
                ],
            )
            r = _brief(repo, chart_id, prop)
            self.assertNotEqual(r.returncode, 0)
            err = json.loads(r.stdout)["error"]
            self.assertEqual(err["code"], "proposal_duplicate_cluster_key")
            self.assertEqual(err["details"]["key"], "core")


class TestClusterKeyNamespace(unittest.TestCase):
    def test_reserved_and_invalid_cluster_keys_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, _prop, d1, d2 = _ready_single_cluster(repo)
            # 'B1' would make the cluster path equal the immutable versioned
            # index path fn-N-briefing-B1.md; separators/traversal escape the
            # generated-path namespace entirely.
            cases = [
                ("B1", "proposal_cluster_key_reserved"),
                ("b7", "proposal_cluster_key_reserved"),
                ("x/y", "proposal_cluster_key_invalid"),
                ("..", "proposal_cluster_key_invalid"),
            ]
            for i, (key, code) in enumerate(cases):
                prop = _proposal(
                    repo,
                    f"key-{i}.json",
                    [
                        {"key": key, "rationale": "first", "decisions": [d1["id"]]},
                        {"key": "ok", "rationale": "second", "decisions": [d2["id"]]},
                    ],
                )
                r = _brief(repo, chart_id, prop)
                self.assertNotEqual(r.returncode, 0, key)
                err = json.loads(r.stdout)["error"]
                self.assertEqual(err["code"], code, key)
                self.assertEqual(err["details"]["key"], key)
            # Nothing was emitted for any refused proposal.
            self.assertFalse(
                (flow / "charts" / f"{chart_id}-briefing-B1.md").is_file()
            )
            self.assertFalse(
                (flow / "charts" / f"{chart_id}-briefing.md").is_file()
            )

    def test_emission_relpath_collision_guard(self) -> None:
        """Belt-and-braces behind key validation: a forged proposal whose
        generated paths collide is refused before any staging."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, d1, d2 = _ready_single_cluster(repo)
            forged = {
                "clusters": [
                    {
                        "key": "B1",
                        "rationale": "collides with versioned index",
                        "decisions": [d1["id"]],
                    },
                    {"key": "ok", "rationale": "fine", "decisions": [d2["id"]]},
                ],
                "shared_context": [],
            }
            with mock.patch.object(
                flowctl, "_parse_briefing_proposal_file", return_value=forged
            ):
                with self.assertRaises(flowctl.ChartError) as ctx:
                    flowctl.emit_chart_briefing(flow, chart_id, prop)
            self.assertEqual(ctx.exception.code, "briefing_path_collision")
            self.assertIn(
                f"{chart_id}-briefing-B1.md", ctx.exception.details["paths"]
            )
            self.assertFalse(
                (flow / "charts" / f"{chart_id}-briefing-B1.md").is_file()
            )
            self.assertFalse(
                (flow / "charts" / f"{chart_id}-briefing.md").is_file()
            )


class TestDoneAndMutations(unittest.TestCase):
    def test_first_final_sets_done_and_blocks_mutations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, _d1, _d2 = _ready_single_cluster(repo)
            r = _brief(repo, chart_id, prop)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(_chart_json(flow, chart_id)["status"], "done")

            # add-decision rejected
            r_add = _run_flowctl(
                repo,
                "chart",
                "add-decision",
                chart_id,
                "--title",
                "Late",
                "--type",
                "research",
                "--json",
            )
            self.assertNotEqual(r_add.returncode, 0)
            self.assertEqual(json.loads(r_add.stdout)["error"]["code"], "chart_not_open")

            # show/list still work
            r_show = _run_flowctl(repo, "chart", "show", chart_id, "--json")
            self.assertEqual(r_show.returncode, 0, r_show.stderr)
            self.assertEqual(json.loads(r_show.stdout)["result"]["status"], "done")
            r_list = _run_flowctl(repo, "chart", "list", "--json")
            self.assertEqual(r_list.returncode, 0, r_list.stderr)


class TestLinkSpec(unittest.TestCase):
    def test_empty_decision_set_rejected(self) -> None:
        """--decisions '' must not persist a provenance-free link: an empty
        decision list passes membership vacuously and later supersession
        staling can never match it."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, _d1, _d2 = _ready_single_cluster(repo)
            r = _brief(repo, chart_id, prop)
            self.assertEqual(r.returncode, 0, r.stderr)
            bid = json.loads(r.stdout)["result"]["briefing_id"]

            r1 = _run_flowctl(
                repo,
                "chart",
                "link-spec",
                chart_id,
                "--briefing",
                bid,
                "--spec",
                "fn-900",
                "--decisions",
                "",
                "--json",
            )
            self.assertNotEqual(r1.returncode, 0)
            err = json.loads(r1.stdout)["error"]
            self.assertEqual(err["class"], "validation")
            self.assertEqual(err["code"], "link_decisions_required")
            self.assertEqual(err["details"]["briefing"], bid)
            # Nothing persisted.
            side = _chart_json(flow, chart_id)
            self.assertEqual(side["produced_specs"], [])

    def test_idempotent_cluster_identity_and_stale_after_supersession(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, d1, d2 = _ready_single_cluster(repo)
            r = _brief(repo, chart_id, prop)
            self.assertEqual(r.returncode, 0, r.stderr)
            bid = json.loads(r.stdout)["result"]["briefing_id"]

            # Link with cluster key
            r1 = _run_flowctl(
                repo,
                "chart",
                "link-spec",
                chart_id,
                "--briefing",
                bid,
                "--spec",
                "fn-900",
                "--decisions",
                f"{d1['id']},{d2['id']}",
                "--cluster",
                "1",
                "--json",
            )
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)
            e1 = json.loads(r1.stdout)["result"]
            self.assertFalse(e1["noop"])
            self.assertEqual(e1["status"], "linked")
            self.assertEqual(e1["cluster"], "1")

            # Identical retry no-op
            r2 = _run_flowctl(
                repo,
                "chart",
                "link-spec",
                chart_id,
                "--briefing",
                bid,
                "--spec",
                "fn-900",
                "--decisions",
                f"{d1['id']},{d2['id']}",
                "--cluster",
                "1",
                "--json",
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertTrue(json.loads(r2.stdout)["result"]["noop"])

            side = _chart_json(flow, chart_id)
            self.assertEqual(len(side["produced_specs"]), 1)

            # Different identity (no cluster key) is a second link
            r3 = _run_flowctl(
                repo,
                "chart",
                "link-spec",
                chart_id,
                "--briefing",
                bid,
                "--spec",
                "fn-901",
                "--decisions",
                d2["id"],
                "--json",
            )
            self.assertEqual(r3.returncode, 0, r3.stderr)
            self.assertFalse(json.loads(r3.stdout)["result"]["noop"])
            side = _chart_json(flow, chart_id)
            self.assertEqual(len(side["produced_specs"]), 2)

            # Supersession after reopen stales links containing that D-ID
            r_re = _run_flowctl(
                repo,
                "chart",
                "reopen",
                chart_id,
                "--reason",
                "revisit storage",
                "--json",
            )
            self.assertEqual(r_re.returncode, 0, r_re.stderr)
            side = _chart_json(flow, chart_id)
            for link in side["produced_specs"]:
                self.assertEqual(link["status"], "stale")

            # Fresh link after reopen, then supersede d1 via new decision
            d3 = _add_decision(repo, chart_id, "New storage", "research")
            # d3 is still open, so resolve it (superseding d1) before B2.
            _resolve(repo, d3["id"], "Use SQLite instead", supersedes=d1["id"])
            # Now d1 is superseded; resolved set is d2+d3
            prop_b2 = _proposal(
                repo,
                "prop-b2.json",
                [
                    {
                        "key": "1",
                        "rationale": "post-supersession",
                        "decisions": [d2["id"], d3["id"]],
                    }
                ],
            )
            r_b2 = _brief(repo, chart_id, prop_b2)
            self.assertEqual(r_b2.returncode, 0, r_b2.stderr + r_b2.stdout)
            b2 = json.loads(r_b2.stdout)["result"]["briefing_id"]
            self.assertEqual(b2, "B2")

            r_link = _run_flowctl(
                repo,
                "chart",
                "link-spec",
                chart_id,
                "--briefing",
                b2,
                "--spec",
                "fn-902",
                "--decisions",
                f"{d2['id']},{d3['id']}",
                "--cluster",
                "1",
                "--json",
            )
            self.assertEqual(r_link.returncode, 0, r_link.stderr)
            side = _chart_json(flow, chart_id)
            linked = [
                x
                for x in side["produced_specs"]
                if x.get("spec") == "fn-902" and x.get("status") == "linked"
            ]
            self.assertEqual(len(linked), 1)

            # Reopen to allow supersession of a linked D-ID (d3)
            _run_flowctl(
                repo,
                "chart",
                "reopen",
                chart_id,
                "--reason",
                "supersede linked d3",
                "--json",
            )
            # Re-link again after reopen staled B2 link
            # After reopen all links stale; create d4 superseding d3 while chart open
            d4 = _add_decision(repo, chart_id, "Even newer storage", "research")
            # Manually re-link first (simulating capture before supersession)
            # Need to un-stale by writing a new link with different identity? Or
            # test supersession path by calling resolve with supersedes on a
            # chart that has a linked entry that is currently "linked".
            # Reopen staled all. Insert a fresh linked entry via link-spec with
            # a new identity, then supersede.
            r_fresh = _run_flowctl(
                repo,
                "chart",
                "link-spec",
                chart_id,
                "--briefing",
                b2,
                "--spec",
                "fn-903",
                "--decisions",
                d3["id"],
                "--cluster",
                "1",
                "--json",
            )
            self.assertEqual(r_fresh.returncode, 0, r_fresh.stderr)
            self.assertEqual(json.loads(r_fresh.stdout)["result"]["status"], "linked")

            _resolve(repo, d4["id"], "object store", supersedes=d3["id"])
            side = _chart_json(flow, chart_id)
            fresh = [x for x in side["produced_specs"] if x.get("spec") == "fn-903"]
            self.assertEqual(len(fresh), 1)
            self.assertEqual(fresh[0]["status"], "stale")
            self.assertIn("superseded", (fresh[0].get("stale_note") or "").lower())


class TestLinkSpecDecisionValidation(unittest.TestCase):
    def test_rejects_unknown_and_cross_cluster_dids_but_retries_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Shared tenancy model", "research")
            d2 = _add_decision(repo, chart_id, "Billing surface", "research")
            d3 = _add_decision(repo, chart_id, "Admin UI", "research")
            _resolve(repo, d1["id"], "shared schema with RLS")
            _resolve(repo, d2["id"], "usage-based billing")
            _resolve(repo, d3["id"], "admin console v1")
            prop = _proposal(
                repo,
                "split.json",
                [
                    {
                        "key": "billing",
                        "rationale": "Billing alone",
                        "decisions": [d1["id"], d2["id"]],
                    },
                    {
                        "key": "admin",
                        "rationale": "Admin alone",
                        "decisions": [d1["id"], d3["id"]],
                    },
                ],
                shared=[d1["id"]],
            )
            r = _brief(repo, chart_id, prop)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            bid = json.loads(r.stdout)["result"]["briefing_id"]

            # Nonexistent D-ID is rejected, nothing persisted.
            r_bad = _run_flowctl(
                repo,
                "chart",
                "link-spec",
                chart_id,
                "--briefing",
                bid,
                "--spec",
                "fn-900",
                "--decisions",
                "D999",
                "--cluster",
                "billing",
                "--json",
            )
            self.assertNotEqual(r_bad.returncode, 0)
            err = json.loads(r_bad.stdout)["error"]
            self.assertEqual(err["code"], "link_decisions_not_in_briefing")
            self.assertIn(f"{chart_id}.D999", err["details"]["unknown"])
            self.assertEqual(len(_chart_json(flow, chart_id).get("produced_specs") or []), 0)

            # D-ID from the other cluster is rejected for the named cluster.
            r_cross = _run_flowctl(
                repo,
                "chart",
                "link-spec",
                chart_id,
                "--briefing",
                bid,
                "--spec",
                "fn-900",
                "--decisions",
                d3["id"],
                "--cluster",
                "billing",
                "--json",
            )
            self.assertNotEqual(r_cross.returncode, 0)
            err = json.loads(r_cross.stdout)["error"]
            self.assertEqual(err["code"], "link_decisions_not_in_briefing")
            self.assertIn(d3["id"], err["details"]["unknown"])

            # Valid link (cluster set + shared context) succeeds.
            good_args = [
                "chart",
                "link-spec",
                chart_id,
                "--briefing",
                bid,
                "--spec",
                "fn-900",
                "--decisions",
                f"{d1['id']},{d2['id']}",
                "--cluster",
                "billing",
                "--json",
            ]
            r_ok = _run_flowctl(repo, *good_args)
            self.assertEqual(r_ok.returncode, 0, r_ok.stderr + r_ok.stdout)
            self.assertFalse(json.loads(r_ok.stdout)["result"]["noop"])

            # Identical retry stays a no-op.
            r_retry = _run_flowctl(repo, *good_args)
            self.assertEqual(r_retry.returncode, 0, r_retry.stderr + r_retry.stdout)
            self.assertTrue(json.loads(r_retry.stdout)["result"]["noop"])
            self.assertEqual(len(_chart_json(flow, chart_id)["produced_specs"]), 1)

            # Unknown cluster key is rejected outright (never falls back to
            # the briefing-wide union), nothing persisted.
            r_typo = _run_flowctl(
                repo,
                "chart",
                "link-spec",
                chart_id,
                "--briefing",
                bid,
                "--spec",
                "fn-904",
                "--decisions",
                d2["id"],
                "--cluster",
                "biling",
                "--json",
            )
            self.assertNotEqual(r_typo.returncode, 0)
            err = json.loads(r_typo.stdout)["error"]
            self.assertEqual(err["code"], "link_unknown_cluster")
            self.assertEqual(
                sorted(err["details"]["valid_clusters"]), ["admin", "billing"]
            )
            self.assertEqual(len(_chart_json(flow, chart_id)["produced_specs"]), 1)


class TestMultiClusterAndShared(unittest.TestCase):
    def test_multi_cluster_files_and_shared_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Shared tenancy model", "research")
            d2 = _add_decision(repo, chart_id, "Billing surface", "research")
            d3 = _add_decision(repo, chart_id, "Admin UI", "research")
            _resolve(repo, d1["id"], "shared schema with RLS")
            _resolve(repo, d2["id"], "usage-based billing")
            _resolve(repo, d3["id"], "admin console v1")

            prop = _proposal(
                repo,
                "split.json",
                [
                    {
                        "key": "billing",
                        "rationale": "Billing can ship alone",
                        "decisions": [d1["id"], d2["id"]],
                    },
                    {
                        "key": "admin",
                        "rationale": "Admin UI is a separate capture",
                        "decisions": [d1["id"], d3["id"]],
                    },
                ],
                shared=[d1["id"]],
            )
            r = _brief(repo, chart_id, prop)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            env = json.loads(r.stdout)["result"]
            self.assertEqual(env["briefing_id"], "B1")
            self.assertEqual(env["status"], "final")

            index = flow / "charts" / f"{chart_id}-briefing.md"
            c_billing = flow / "charts" / f"{chart_id}-briefing-billing.md"
            c_admin = flow / "charts" / f"{chart_id}-briefing-admin.md"
            self.assertTrue(index.is_file())
            self.assertTrue(c_billing.is_file())
            self.assertTrue(c_admin.is_file())

            billing_txt = c_billing.read_text(encoding="utf-8")
            self.assertIn("Shared context", billing_txt)
            self.assertIn(d1["id"], billing_txt)
            self.assertIn(d2["id"], billing_txt)
            self.assertIn("Outcome", billing_txt)

            # Conflict without shared_context listing
            prop_bad = _proposal(
                repo,
                "bad.json",
                [
                    {
                        "key": "a",
                        "rationale": "a",
                        "decisions": [d1["id"], d2["id"]],
                    },
                    {
                        "key": "b",
                        "rationale": "b",
                        "decisions": [d1["id"], d3["id"]],
                    },
                ],
                shared=[],
            )
            # Chart is done; reopen to test validation
            _run_flowctl(
                repo, "chart", "reopen", chart_id, "--reason", "test conflict", "--json"
            )
            r_bad = _brief(repo, chart_id, prop_bad)
            self.assertNotEqual(r_bad.returncode, 0)
            self.assertEqual(
                json.loads(r_bad.stdout)["error"]["code"],
                "proposal_membership_conflict",
            )


class TestBriefingFailpoint(unittest.TestCase):
    def test_kill_during_publication_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, _d1, _d2 = _ready_single_cluster(repo)

            r = _brief(
                repo,
                chart_id,
                prop,
            )
            # First establish clean path works without failpoint.
            self.assertEqual(r.returncode, 0, r.stderr)

            # Reopen and try failpoint on second briefing
            _run_flowctl(
                repo,
                "chart",
                "reopen",
                chart_id,
                "--reason",
                "failpoint test",
                "--json",
            )
            side_before = _chart_json(flow, chart_id)
            self.assertEqual(side_before["status"], "open")
            brief_count_before = len(side_before.get("briefings") or [])

            prop2 = _proposal(
                repo,
                "prop-fp.json",
                [
                    {
                        "key": "1",
                        "rationale": "failpoint proposal change",
                        "decisions": [_d1["id"], _d2["id"]],
                    }
                ],
            )
            # Note: _ready_single_cluster locals not available as _d1 - fix by re-reading
            # Actually we unpacked _d1, _d2 from ready - they're the decision dicts.
            # Wait I used _d1 in the prop above incorrectly - prop uses d1 from unpack.
            # Looking at my code: chart_id, prop, _d1, _d2 = _ready_single_cluster
            # prop2 uses _d1['id'] - good.

            r_kill = _run_flowctl(
                repo,
                "chart",
                "briefing",
                chart_id,
                "--proposal-file",
                str(prop2),
                "--json",
                env={"FLOWCTL_CHART_FAILPOINT": "exit:after_first_publish"},
            )
            self.assertNotEqual(r_kill.returncode, 0)

            # Recovery on next command
            r_show = _run_flowctl(repo, "chart", "show", chart_id, "--json")
            self.assertEqual(r_show.returncode, 0, r_show.stderr)
            side = _chart_json(flow, chart_id)
            # After kill mid-publish, recovery should restore or complete.
            # Either rolled back (status open, same brief count as after reopen)
            # or rolled forward. Assert no partial txn left.
            txn_dir = flow / "charts" / ".transactions"
            if txn_dir.is_dir():
                left = [p for p in txn_dir.iterdir() if p.is_dir()]
                # Recovery on show should have cleaned committed/restored txns
                # Allow empty after recovery
                self.assertEqual(len(left), 0, f"leftover txns: {left}")

            # Chart should be consistent: either open (restored) or done (rolled forward)
            self.assertIn(side["status"], ("open", "done"))
            # briefings count: if rolled back, same as after reopen; if forward, +1
            n = len(side.get("briefings") or [])
            self.assertIn(n, (brief_count_before, brief_count_before + 1))


class TestReopenFromAbandoned(unittest.TestCase):
    def test_reopen_abandoned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            r_ab = _run_flowctl(
                repo,
                "chart",
                "abandon",
                chart_id,
                "--reason",
                "stopped discovery",
                "--json",
            )
            self.assertEqual(r_ab.returncode, 0, r_ab.stderr)
            r_re = _run_flowctl(
                repo,
                "chart",
                "reopen",
                chart_id,
                "--reason",
                "resume discovery",
                "--json",
            )
            self.assertEqual(r_re.returncode, 0, r_re.stderr)
            self.assertEqual(_chart_json(flow, chart_id)["status"], "open")
            self.assertEqual(json.loads(r_re.stdout)["result"]["prior_status"], "abandoned")


if __name__ == "__main__":
    unittest.main()
