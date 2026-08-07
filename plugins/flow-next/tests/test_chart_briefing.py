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


class TestNonStringStoredFingerprint(unittest.TestCase):
    """A malformed stored fingerprint must not match - and must not crash.

    `load_chart_sidecar` validates the root object only, so `briefings[]`
    entries reach the match loop exactly as written. The accepted-fingerprint
    set membership test hashes its left operand, so an externally produced or
    hand-edited sidecar carrying a JSON array or object in
    `briefings[].fingerprint` raised TypeError there and escaped as a bare
    traceback, bypassing the versioned error envelope every other chart
    failure emits. Every stored fingerprint that is not a string is simply
    not a match, which is how the pre-set equality comparison behaved.
    """

    @staticmethod
    def _plant_array_fingerprint(flow: Path, chart_id: str) -> None:
        side_path = flow / "charts" / f"{chart_id}.json"
        side = json.loads(side_path.read_text(encoding="utf-8"))
        side["briefings"][0]["fingerprint"] = ["not", "a", "string"]
        side_path.write_text(
            json.dumps(side, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def _assert_no_traceback(self, r: subprocess.CompletedProcess) -> None:
        combined = r.stdout + r.stderr
        self.assertNotIn("Traceback", combined, combined)
        self.assertNotIn("TypeError", combined, combined)
        self.assertNotIn("unhashable", combined, combined)

    def test_done_chart_array_fingerprint_gives_error_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, _d1, _d2 = _ready_single_cluster(repo)

            r1 = _brief(repo, chart_id, prop)
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)
            self.assertEqual(json.loads(r1.stdout)["result"]["briefing_id"], "B1")

            self._plant_array_fingerprint(flow, chart_id)

            r2 = _brief(repo, chart_id, prop)
            self._assert_no_traceback(r2)
            self.assertNotEqual(r2.returncode, 0, r2.stdout)
            env = json.loads(r2.stdout)
            self.assertFalse(env["success"], env)
            self.assertEqual(env["schema_version"], 1, env)
            # No match, so the done-chart guard names the remedy - the ordinary
            # versioned envelope, not an interpreter crash.
            self.assertEqual(env["error"]["code"], "chart_not_open", env)
            self.assertIn("reopen", env["error"]["message"], env)

    def test_reopened_chart_array_fingerprint_mints_normally(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, _d1, _d2 = _ready_single_cluster(repo)

            r1 = _brief(repo, chart_id, prop)
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)
            self.assertEqual(json.loads(r1.stdout)["result"]["briefing_id"], "B1")

            self._plant_array_fingerprint(flow, chart_id)

            r_re = _run_flowctl(
                repo, "chart", "reopen", chart_id, "--reason", "resume", "--json"
            )
            self._assert_no_traceback(r_re)
            self.assertEqual(r_re.returncode, 0, r_re.stderr + r_re.stdout)

            # Open chart, no match -> the ordinary emission path mints B2.
            r2 = _brief(repo, chart_id, prop)
            self._assert_no_traceback(r2)
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            e2 = json.loads(r2.stdout)["result"]
            self.assertFalse(e2["noop"], e2)
            self.assertEqual(e2["briefing_id"], "B2", e2)


class TestSupersedesStaleDiscriminator(unittest.TestCase):
    """R9/R4/R3: the emission is self-describing - and only where it should be.

    PRESENCE of `supersedes_stale` is the discriminator, so its absence on every
    other path is what makes the byte-unchanged claim for existing envelopes
    checkable rather than merely intended.
    """

    def test_absent_from_first_emission_retry_and_error_envelopes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id, prop, d1, d2 = _ready_single_cluster(repo)

            r1 = _brief(repo, chart_id, prop)
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)
            e1 = json.loads(r1.stdout)["result"]
            self.assertEqual(e1["briefing_id"], "B1")
            self.assertFalse(e1["noop"])
            # First emission: nothing was superseded.
            self.assertNotIn("supersedes_stale", e1)

            r2 = _brief(repo, chart_id, prop)
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            e2 = json.loads(r2.stdout)["result"]
            self.assertTrue(e2["noop"])
            self.assertNotIn("supersedes_stale", e2)

            # Error envelope: a changed proposal against the done chart.
            prop2 = _proposal(
                repo,
                "prop-split.json",
                [
                    {"key": "a", "rationale": "Split storage", "decisions": [d1["id"]]},
                    {"key": "b", "rationale": "Split auth", "decisions": [d2["id"]]},
                ],
            )
            r3 = _brief(repo, chart_id, prop2)
            self.assertNotEqual(r3.returncode, 0, r3.stdout)
            self.assertEqual(json.loads(r3.stdout)["error"]["code"], "chart_not_open")
            self.assertNotIn("supersedes_stale", r3.stdout)

    def test_present_on_a_superseding_emission_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id, prop, _d1, _d2 = _ready_single_cluster(repo)

            self.assertEqual(_brief(repo, chart_id, prop).returncode, 0)
            r_re = _run_flowctl(
                repo, "chart", "reopen", chart_id, "--reason", "more work", "--json"
            )
            self.assertEqual(r_re.returncode, 0, r_re.stderr)

            r2 = _brief(repo, chart_id, prop)
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            e2 = json.loads(r2.stdout)["result"]
            self.assertFalse(e2["noop"])
            self.assertEqual(e2["briefing_id"], "B2")
            # Array of B-ID strings, in sidecar order.
            self.assertEqual(e2["supersedes_stale"], ["B1"])
            self.assertTrue(
                all(isinstance(x, str) for x in e2["supersedes_stale"]),
                e2["supersedes_stale"],
            )

            # R3: per-briefing `status` stays the capture-readiness source of
            # truth. It lives in the chart record `briefings[]` - the artifact
            # downstream consumers read - and `chart show --json` projects only
            # `briefing_count`, which this change leaves untouched. So pin the
            # statuses where they actually live, and pin the projection as
            # unchanged rather than pretending it carries them.
            side = _chart_json(flow, chart_id)
            self.assertEqual(
                [b["status"] for b in side["briefings"]], ["stale", "final"]
            )
            # The discriminator is invocation-scoped: it is never persisted onto
            # a briefing record, so it can never be mistaken for that status.
            self.assertNotIn("supersedes_stale", side["briefings"][1])

            r_show = _run_flowctl(repo, "chart", "show", chart_id, "--json")
            self.assertEqual(r_show.returncode, 0, r_show.stderr)
            show = json.loads(r_show.stdout)["result"]
            self.assertEqual(show["briefing_count"], 2)
            self.assertNotIn("supersedes_stale", r_show.stdout)

            # Cross-check the same capture-readiness facts from public command
            # output, so a corruption of either record or envelope fails here:
            # `reopen` reported staling B1, and the emission reported B2 final.
            self.assertEqual(
                json.loads(r_re.stdout)["result"]["staled_briefings"], ["B1"]
            )
            self.assertEqual(e2["status"], "final")
            self.assertEqual(e2["chart_status"], show["status"])

            # The retry that answers with B2 carries no discriminator either.
            r3 = _brief(repo, chart_id, prop)
            self.assertEqual(r3.returncode, 0, r3.stderr + r3.stdout)
            e3 = json.loads(r3.stdout)["result"]
            self.assertTrue(e3["noop"])
            self.assertEqual(e3["briefing_id"], "B2")
            self.assertNotIn("supersedes_stale", e3)

    def test_human_output_reports_the_superseding_emission(self) -> None:
        # The bug report's complaint was the terminal output: `status=<val>
        # (noop)` told the operator nothing about what actually happened.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            chart_id, prop, _d1, _d2 = _ready_single_cluster(repo)

            r1 = _run_flowctl(
                repo, "chart", "briefing", chart_id, "--proposal-file", str(prop)
            )
            self.assertEqual(r1.returncode, 0, r1.stderr + r1.stdout)
            # Ordinary output is unchanged - no discriminator anywhere.
            self.assertIn(f"{chart_id} briefing B1 status=final\n", r1.stdout)
            self.assertNotIn("supersedes", r1.stdout)

            r_re = _run_flowctl(
                repo, "chart", "reopen", chart_id, "--reason", "more work", "--json"
            )
            self.assertEqual(r_re.returncode, 0, r_re.stderr)

            r2 = _run_flowctl(
                repo, "chart", "briefing", chart_id, "--proposal-file", str(prop)
            )
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            self.assertIn(
                f"{chart_id} briefing B2 status=final (supersedes stale B1)\n",
                r2.stdout,
            )
            self.assertIn("chart status -> done via B2", r2.stdout)


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


class TestAssetRevisionInBriefing(unittest.TestCase):
    def test_asset_revision_rendered_in_index_and_cluster(self) -> None:
        """A mutable reference (path/branch/url) with a stored revision must
        carry that revision into the immutable briefing artifacts, or the
        briefing cannot identify which evidence version backed the decision
        after the referenced content changes."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            chart_id = _create_chart(repo)
            d1 = _add_decision(repo, chart_id, "Storage choice", "research")
            d2 = _add_decision(repo, chart_id, "Auth model", "research")
            _resolve(repo, d2["id"], "OIDC with per-tenant issuers")
            (repo / "docs").mkdir()
            (repo / "docs" / "evidence.md").write_text("mock", encoding="utf-8")
            _git(repo, "add", "docs/evidence.md")
            _git(repo, "commit", "-q", "-m", "evidence")
            af = repo / f"ans-{d1['id'].replace('.', '-')}.txt"
            af.write_text("Use Postgres", encoding="utf-8")
            r = _run_flowctl(
                repo,
                "chart",
                "resolve",
                d1["id"],
                "--answer-file",
                str(af),
                "--assets",
                json.dumps([
                    {
                        "kind": "path",
                        "reference": "docs/evidence.md",
                        "display": "evidence doc",
                        "revision": "rev-abc123",
                    }
                ]),
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            prop = _proposal(
                repo,
                "rev.json",
                [
                    {"key": "core", "rationale": "storage surface", "decisions": [d1["id"]]},
                    {"key": "auth", "rationale": "auth surface", "decisions": [d2["id"]]},
                ],
            )
            rb = _brief(repo, chart_id, prop)
            self.assertEqual(rb.returncode, 0, rb.stderr + rb.stdout)
            index_txt = (
                flow / "charts" / f"{chart_id}-briefing.md"
            ).read_text(encoding="utf-8")
            cluster_txt = (
                flow / "charts" / f"{chart_id}-briefing-core.md"
            ).read_text(encoding="utf-8")
            for txt in (index_txt, cluster_txt):
                self.assertIn("docs/evidence.md", txt)
                self.assertIn("@ rev-abc123", txt)


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


class TestBriefingCarriesChartNotes(unittest.TestCase):
    """R52: grounding facts must survive the handoff - capture reads the
    briefing artifacts, not the original chart body."""

    def test_notes_section_appears_in_briefing_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            note = "- Shared schema today [ref: src/db/schema.sql rev:9f2c1ab]"
            map_path = repo / "map.json"
            map_path.write_text(
                json.dumps(
                    {
                        "decisions": [{"title": "Choose key", "type": "research"}],
                        "notes": note,
                    }
                ),
                encoding="utf-8",
            )
            r = _run_flowctl(
                repo, "chart", "create", "--title", "Tenants", "--outcome",
                "Ready", "--initial-map-file", str(map_path), "--json",
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            chart_id = json.loads(r.stdout)["result"]["id"]
            answer = repo / "a.md"
            answer.write_text("Use a tenant column.", encoding="utf-8")
            r2 = _run_flowctl(
                repo, "chart", "resolve", f"{chart_id}.D1",
                "--answer-file", str(answer), "--json",
            )
            self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
            proposal = repo / "p.json"
            proposal.write_text(
                json.dumps(
                    {
                        "clusters": [
                            {
                                "key": "1",
                                "rationale": "one spec",
                                "decisions": [f"{chart_id}.D1"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            r3 = _run_flowctl(
                repo, "chart", "briefing", chart_id,
                "--proposal-file", str(proposal), "--json",
            )
            self.assertEqual(r3.returncode, 0, r3.stdout + r3.stderr)
            index = (flow / "charts" / f"{chart_id}-briefing.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("## Notes", index)
            self.assertIn(note, index)


if __name__ == "__main__":
    unittest.main()
