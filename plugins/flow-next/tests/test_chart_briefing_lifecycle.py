# Split from test_chart_briefing.py 2026-08-07 to halve the slowest unit-suite shard (runner shards per file). Reopen/lifecycle briefing tests.
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
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
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


def _ledger_snapshot(flow: Path, chart_id: str) -> dict:
    """Every decision-state input the briefing fingerprint hashes.

    Chart body, the compact entries chart_decision_revision covers, and the
    decision records _briefing_evidence_digest loads. Comparing two snapshots
    proves nothing was settled between two emissions - without that, a test
    that mints a new briefing after a reopen may only have moved the ledger.
    """
    charts = flow / "charts"
    side = json.loads((charts / f"{chart_id}.json").read_text(encoding="utf-8"))
    snap = {
        "chart.md": (charts / f"{chart_id}.md").read_text(encoding="utf-8"),
        "id": side.get("id"),
        "title": side.get("title"),
        "outcome": side.get("outcome"),
        "decisions": side.get("decisions"),
        "parked_questions": side.get("parked_questions"),
    }
    for p in sorted((charts / chart_id).glob("*")):
        if p.is_file():
            snap[f"record/{p.name}"] = p.read_text(encoding="utf-8")
    return snap


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


def _forced_draft_then_abandon_reopen(repo: Path) -> tuple[str, Path, dict, dict]:
    """Force-draft B1 on an unbriefable chart, then abandon -> reopen.

    Leaves a chart whose ONLY briefing is a staled forced draft, reached from
    the `abandoned` source state. `abandon` is legal only from `open` and never
    touches briefings, so this is the only way an abandoned-sourced reopen
    carries a briefing at all: abandon a chart with none and the later
    reopen-then-brief simply mints B1, exercising no stale handling whatsoever.

    Returns (chart_id, proposal covering the one resolved decision, resolved
    decision, still-open decision).
    """
    chart_id = _create_chart(repo)
    d1 = _add_decision(repo, chart_id, "Storage choice", "research")
    d2 = _add_decision(repo, chart_id, "Still open", "research")
    _resolve(repo, d1["id"], "Use Postgres for tenant metadata")
    prop = _proposal(
        repo,
        "prop-forced.json",
        [{"key": "1", "rationale": "partial handoff", "decisions": [d1["id"]]}],
    )

    r = _brief(repo, chart_id, prop, force=True)
    assert r.returncode == 0, r.stderr + r.stdout
    first = json.loads(r.stdout)["result"]
    # The premise: a DRAFT B1 on a chart that stays open (an unbriefable chart
    # cannot reach `done`, so `abandoned` is the only terminal state available).
    assert first["briefing_id"] == "B1", first
    assert first["status"] == "draft", first
    assert first["chart_status"] == "open", first

    r_ab = _run_flowctl(
        repo, "chart", "abandon", chart_id, "--reason", "paused discovery", "--json"
    )
    assert r_ab.returncode == 0, r_ab.stderr + r_ab.stdout
    r_re = _run_flowctl(
        repo, "chart", "reopen", chart_id, "--reason", "resume discovery", "--json"
    )
    assert r_re.returncode == 0, r_re.stderr + r_re.stdout
    reopened = json.loads(r_re.stdout)["result"]
    assert reopened["prior_status"] == "abandoned", reopened
    assert reopened["staled_briefings"] == ["B1"], reopened
    return chart_id, prop, d1, d2


class TestReopenEpochFingerprint(unittest.TestCase):
    """fn-154: a reopen is a new briefing epoch.

    Before the fix, `reopen` staled every briefing but moved nothing the
    fingerprint hashed, so re-briefing the same proposal over an untouched
    ledger echoed the stale briefing back with noop and left the operator on a
    briefable chart with no capture-ready briefing.
    """

    def test_reopen_then_identical_brief_mints_final(self) -> None:
        # R1: reopen -> brief with the SAME proposal and an untouched ledger
        # ends on a final briefing.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, _d1, _d2 = _ready_single_cluster(repo)

            r1 = _brief(repo, chart_id, prop)
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)
            e1 = json.loads(r1.stdout)["result"]
            self.assertEqual(e1["briefing_id"], "B1")
            self.assertEqual(e1["status"], "final")
            self.assertEqual(e1["chart_status"], "done")

            r_re = _run_flowctl(
                repo,
                "chart",
                "reopen",
                chart_id,
                "--reason",
                "more work needed",
                "--json",
            )
            self.assertEqual(r_re.returncode, 0, r_re.stderr)
            self.assertIn("B1", json.loads(r_re.stdout)["result"]["staled_briefings"])

            # Snapshot AFTER the reopen: settling anything from here would move
            # the fingerprint on its own and the test would pass without ever
            # exercising the defect.
            ledger_after_reopen = _ledger_snapshot(flow, chart_id)

            r2 = _brief(repo, chart_id, prop)
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            e2 = json.loads(r2.stdout)["result"]
            self.assertFalse(e2["noop"])
            self.assertEqual(e2["briefing_id"], "B2")
            self.assertEqual(e2["status"], "final")
            self.assertEqual(e2["chart_status"], "done")
            self.assertTrue(e2["transitioned_done"])
            self.assertNotEqual(e2["fingerprint"], e1["fingerprint"])

            self.assertEqual(_ledger_snapshot(flow, chart_id), ledger_after_reopen)

            side = _chart_json(flow, chart_id)
            self.assertEqual(len(side["briefings"]), 2)
            b1, b2 = side["briefings"]
            self.assertEqual(b1["status"], "stale")
            self.assertEqual(b2["status"], "final")
            # Identical decision state across both emissions: the new B-ID came
            # from the reopen epoch alone.
            self.assertEqual(b2["chart_revision"], b1["chart_revision"])
            self.assertEqual(side["status"], "done")

    def test_same_version_retry_still_noops(self) -> None:
        # R5b: ordinary idempotence regression. This is NOT proof that pre-fix
        # charts still match - see TestPreFixFingerprintCompatibility for that.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, _d1, _d2 = _ready_single_cluster(repo)

            r1 = _brief(repo, chart_id, prop)
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)
            e1 = json.loads(r1.stdout)["result"]

            r2 = _brief(repo, chart_id, prop)
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            e2 = json.loads(r2.stdout)["result"]
            self.assertTrue(e2["noop"])
            self.assertEqual(e2["briefing_id"], "B1")
            self.assertEqual(e2["fingerprint"], e1["fingerprint"])
            self.assertEqual(len(_chart_json(flow, chart_id)["briefings"]), 1)


class TestPreFixFingerprintCompatibility(unittest.TestCase):
    """R5a: charts written before the epoch change keep their B-IDs."""

    def test_prefix_fixture_still_matches_and_noops(self) -> None:
        fixture = FIXTURES / "chart_prefix_fingerprint"
        expected = json.loads((fixture / "expected.json").read_text(encoding="utf-8"))
        chart_id = expected["chart_id"]
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            # A chart whose stored fingerprint was minted by the pre-fix
            # algorithm, checked in as bytes. It carries no reopened_at, so the
            # epoch key must be absent from the hashed blob entirely.
            shutil.copytree(fixture / "charts", flow / "charts", dirs_exist_ok=True)
            side_path = flow / "charts" / f"{chart_id}.json"
            side_before = side_path.read_text(encoding="utf-8")

            r = _brief(repo, chart_id, fixture / "proposal.json")
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            res = json.loads(r.stdout)["result"]
            self.assertTrue(res["noop"])
            self.assertEqual(res["briefing_id"], expected["briefing_id"])
            self.assertEqual(res["fingerprint"], expected["fingerprint"])
            self.assertEqual(res["status"], expected["briefing_status"])
            self.assertEqual(res["chart_status"], expected["chart_status"])
            # An idempotent answer writes nothing.
            self.assertEqual(side_path.read_text(encoding="utf-8"), side_before)


class TestPreFixReopenedChartUpgrade(unittest.TestCase):
    """R4: upgrading must not orphan a briefing a pre-fix binary minted after a
    reopen. That chart carries a reopened_at but an epoch-free stored hash, so
    the epoch-aware fingerprint alone would miss it and refuse the retry on the
    now-done chart."""

    @staticmethod
    def _plant(repo: Path, flow: Path) -> dict:
        fixture = FIXTURES / "chart_prefix_reopened_fingerprint"
        shutil.copytree(fixture / "charts", flow / "charts", dirs_exist_ok=True)
        return json.loads((fixture / "expected.json").read_text(encoding="utf-8"))

    def test_live_prefix_briefing_still_noops_after_upgrade(self) -> None:
        fixture = FIXTURES / "chart_prefix_reopened_fingerprint"
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            expected = self._plant(repo, flow)
            chart_id = expected["chart_id"]
            # Precondition the fixture exists to test: reopened, and its live
            # briefing was minted after that reopen by the pre-fix binary.
            side = _chart_json(flow, chart_id)
            self.assertEqual(side.get("reopened_at"), expected["reopened_at"])
            self.assertEqual(side["status"], "done")

            r = _brief(repo, chart_id, fixture / "proposal-b2.json")
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            res = json.loads(r.stdout)["result"]
            self.assertTrue(res["noop"])
            self.assertEqual(res["briefing_id"], expected["current_briefing_id"])
            self.assertEqual(res["status"], expected["current_briefing_status"])
            self.assertEqual(res["fingerprint"], expected["current_fingerprint"])
            self.assertEqual(res["chart_status"], expected["chart_status"])

    def test_prefix_stale_briefing_is_still_refused(self) -> None:
        # R6 on the same real pre-fix data: B1's epoch-free hash matches the
        # proposal it was built from, but B1 is stale - the legacy fallback
        # must not resurrect it.
        fixture = FIXTURES / "chart_prefix_reopened_fingerprint"
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            expected = self._plant(repo, flow)
            chart_id = expected["chart_id"]

            r = _brief(repo, chart_id, fixture / "proposal-b1.json")
            self.assertNotEqual(r.returncode, 0, r.stdout)
            err = json.loads(r.stdout)["error"]
            self.assertEqual(err["code"], "chart_not_open")
            # The error names the remedy rather than echoing the stale briefing.
            self.assertIn("reopen", err["message"])
            self.assertNotIn(
                expected["stale_briefing_id"], json.dumps(err.get("details") or {})
            )


class TestStaleBriefingNeverEchoed(unittest.TestCase):
    """R6: a stale briefing is never an idempotent answer, match or not."""

    def test_planted_stale_match_mints_instead_of_echoing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, _d1, _d2 = _ready_single_cluster(repo)

            r1 = _brief(repo, chart_id, prop)
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)
            e1 = json.loads(r1.stdout)["result"]
            self.assertEqual(e1["briefing_id"], "B1")

            # Plant exactly what a pre-fix binary's reopen left behind: chart
            # open again, B1 staled, and NO reopened_at epoch - so the stored
            # fingerprint still matches under the current algorithm.
            side_path = flow / "charts" / f"{chart_id}.json"
            side = json.loads(side_path.read_text(encoding="utf-8"))
            side["status"] = "open"
            for key in ("done_at", "done_by", "done_via_briefing"):
                side.pop(key, None)
            side["briefings"][0]["status"] = "stale"
            side["briefings"][0]["staled_at"] = "2026-01-01T00:00:00Z"
            side["briefings"][0]["stale_reason"] = "chart reopened by a pre-fix binary"
            self.assertNotIn("reopened_at", side)
            side_path.write_text(
                json.dumps(side, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )

            r2 = _brief(repo, chart_id, prop)
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            e2 = json.loads(r2.stdout)["result"]
            self.assertFalse(e2["noop"])
            self.assertEqual(e2["briefing_id"], "B2")
            self.assertEqual(e2["status"], "final")
            self.assertEqual(e2["chart_status"], "done")
            # The fingerprint still matches B1's - the defensive guard, not the
            # epoch, is what refused the echo here.
            self.assertEqual(e2["fingerprint"], e1["fingerprint"])

            side_after = _chart_json(flow, chart_id)
            self.assertEqual(len(side_after["briefings"]), 2)
            self.assertEqual(side_after["briefings"][0]["status"], "stale")
            self.assertEqual(side_after["briefings"][1]["status"], "final")

            # And the fresh briefing is what a retry now answers with.
            r3 = _brief(repo, chart_id, prop)
            self.assertEqual(r3.returncode, 0, r3.stderr + r3.stdout)
            e3 = json.loads(r3.stdout)["result"]
            self.assertTrue(e3["noop"])
            self.assertEqual(e3["briefing_id"], "B2")
            self.assertEqual(e3["status"], "final")


class TestDraftRecomputedAfterReopen(unittest.TestCase):
    """R7: draft-vs-final is decided per invocation from the live chart.

    `reopen` flattens `draft` and `final` alike to `stale`, so a stored status
    can never tell the two apart afterwards - inheriting one would silently
    promote a forced draft to final, or demote a final to draft.
    """

    def test_staled_forced_draft_goes_final_only_when_briefable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, d1, d2 = _forced_draft_then_abandon_reopen(repo)

            # Snapshot AFTER the reopen: settling anything from here would move
            # the fingerprint on its own and the retry below would mint for the
            # ordinary reason instead of the epoch.
            ledger_after_reopen = _ledger_snapshot(flow, chart_id)

            r = _brief(repo, chart_id, prop, force=True)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            e = json.loads(r.stdout)["result"]
            self.assertFalse(e["noop"])
            self.assertEqual(e["briefing_id"], "B2")
            # Recomputed, not inherited: the chart is still unbriefable.
            self.assertEqual(e["status"], "draft")
            self.assertEqual(e["chart_status"], "open")
            self.assertFalse(e["transitioned_done"])
            self.assertEqual(e["supersedes_stale"], ["B1"])
            self.assertEqual(_ledger_snapshot(flow, chart_id), ledger_after_reopen)

            # ...unless the chart is genuinely briefable: resolve the last open
            # decision and an ordinary, unforced emission reaches final.
            _resolve(repo, d2["id"], "settled after the reopen")
            prop_all = _proposal(
                repo,
                "prop-all.json",
                [{"key": "1", "rationale": "whole map", "decisions": [d1["id"], d2["id"]]}],
            )
            r2 = _brief(repo, chart_id, prop_all)
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            e2 = json.loads(r2.stdout)["result"]
            self.assertEqual(e2["briefing_id"], "B3")
            self.assertEqual(e2["status"], "final")
            self.assertEqual(e2["chart_status"], "done")
            self.assertTrue(e2["transitioned_done"])
            # B2 is a live draft, not stale, so it is not listed.
            self.assertEqual(e2["supersedes_stale"], ["B1"])

            side = _chart_json(flow, chart_id)
            self.assertEqual(
                [b["status"] for b in side["briefings"]], ["stale", "draft", "final"]
            )

    def test_staled_final_does_not_make_a_forced_emission_final(self) -> None:
        # The other direction: a stale predecessor that WAS final must not lend
        # its status to an emission on a chart that is no longer briefable.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, _d1, _d2 = _ready_single_cluster(repo)

            r1 = _brief(repo, chart_id, prop)
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)
            self.assertEqual(json.loads(r1.stdout)["result"]["status"], "final")

            r_re = _run_flowctl(
                repo, "chart", "reopen", chart_id, "--reason", "one more question", "--json"
            )
            self.assertEqual(r_re.returncode, 0, r_re.stderr)
            self.assertEqual(_chart_json(flow, chart_id)["briefings"][0]["status"], "stale")

            # A new open decision makes the chart unbriefable again.
            _add_decision(repo, chart_id, "Newly opened", "research")

            r2 = _brief(repo, chart_id, prop, force=True)
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            e2 = json.loads(r2.stdout)["result"]
            self.assertEqual(e2["briefing_id"], "B2")
            self.assertEqual(e2["status"], "draft")
            self.assertEqual(e2["chart_status"], "open")
            self.assertFalse(e2["transitioned_done"])
            self.assertEqual(e2["supersedes_stale"], ["B1"])
            self.assertEqual(_chart_json(flow, chart_id)["status"], "open")


class TestReopenSourceStateAgnostic(unittest.TestCase):
    """R8: the fix does not care which terminal state the reopen came from, and
    it repeats - a second reopen mints again rather than re-matching."""

    def test_abandoned_source_mints_a_draft_b2_not_a_final(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            # open chart with an UNRESOLVED decision -> `briefing --force` mints
            # draft B1, chart stays open -> abandon -> reopen (asserted inside).
            chart_id, prop, _d1, _d2 = _forced_draft_then_abandon_reopen(repo)
            side = _chart_json(flow, chart_id)
            self.assertEqual(side["status"], "open")
            self.assertEqual(side["briefings"][0]["status"], "stale")
            ledger_after_reopen = _ledger_snapshot(flow, chart_id)

            # `briefing --force` with the IDENTICAL proposal.
            r = _brief(repo, chart_id, prop, force=True)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            e = json.loads(r.stdout)["result"]
            self.assertFalse(e["noop"])
            self.assertEqual(e["briefing_id"], "B2")
            self.assertEqual(e["status"], "draft")
            self.assertEqual(e["chart_status"], "open")
            self.assertEqual(e["supersedes_stale"], ["B1"])
            # Same ledger on both sides of the emission: the new B-ID came from
            # the reopen epoch, not from something settled in between.
            self.assertEqual(_ledger_snapshot(flow, chart_id), ledger_after_reopen)

            side = _chart_json(flow, chart_id)
            self.assertEqual([b["status"] for b in side["briefings"]], ["stale", "draft"])
            self.assertEqual(side["status"], "open")

    def test_second_reopen_mints_b3_rather_than_rematching_b2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, _d1, _d2 = _ready_single_cluster(repo)

            r1 = _brief(repo, chart_id, prop)
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)
            e1 = json.loads(r1.stdout)["result"]
            self.assertEqual(e1["briefing_id"], "B1")

            r_re1 = _run_flowctl(
                repo, "chart", "reopen", chart_id, "--reason", "first pass", "--json"
            )
            self.assertEqual(r_re1.returncode, 0, r_re1.stderr)
            r2 = _brief(repo, chart_id, prop)
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            e2 = json.loads(r2.stdout)["result"]
            self.assertEqual(e2["briefing_id"], "B2")
            self.assertEqual(e2["status"], "final")
            self.assertEqual(e2["chart_status"], "done")

            # Second round trip, identical proposal throughout.
            r_re2 = _run_flowctl(
                repo, "chart", "reopen", chart_id, "--reason", "second pass", "--json"
            )
            self.assertEqual(r_re2.returncode, 0, r_re2.stderr)
            # B1 was already stale; only B2 transitions here.
            self.assertEqual(
                json.loads(r_re2.stdout)["result"]["staled_briefings"], ["B2"]
            )
            ledger_after_second_reopen = _ledger_snapshot(flow, chart_id)

            r3 = _brief(repo, chart_id, prop)
            self.assertEqual(r3.returncode, 0, r3.stderr + r3.stdout)
            e3 = json.loads(r3.stdout)["result"]
            self.assertFalse(e3["noop"])
            self.assertEqual(e3["briefing_id"], "B3")
            self.assertEqual(e3["status"], "final")
            self.assertEqual(e3["chart_status"], "done")
            self.assertTrue(e3["transitioned_done"])
            self.assertEqual(e3["supersedes_stale"], ["B1", "B2"])
            self.assertNotIn(e3["fingerprint"], (e1["fingerprint"], e2["fingerprint"]))
            self.assertEqual(
                _ledger_snapshot(flow, chart_id), ledger_after_second_reopen
            )

            side = _chart_json(flow, chart_id)
            self.assertEqual(
                [b["status"] for b in side["briefings"]], ["stale", "stale", "final"]
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
