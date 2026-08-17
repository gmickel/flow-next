# Split from test_review_convergence_cap.py 2026-08-07 to halve the slowest unit-suite shard (runner shards per file). Finalization-journal/replay, in-process backend receipt publication, NEEDS_HUMAN ordering, dispatch fences, and review-scope tests.
"""Convergence-ratchet + verdict-aware deterministic-cap tests.

R4 (convergence ratchet): ``build_rereview_preamble`` injects the prior round's
findings and flips the re-review contract to shrink-only (verify prior fixed;
only NEW >=Major blocks; all-fixed + no new >=Major => MUST SHIP). Without prior
findings (round 1 / legacy receipt) it falls back to the original fresh-review
preamble (back-compatible).

R5 (deterministic cap): a flowctl-owned cumulative round counter on spec state,
enforced at ``MAX_REVIEW_ITERATIONS`` (default 8), surviving FRESH invocations,
reset only on SHIP / re-plan. At the cap the review refuses with an ESCALATE
marker (exit REVIEW_CAP_EXIT_CODE), never a retryable error.

fn-131: pre-dispatch reservations are finalized by outcome. Verdicts consume;
no-verdict transport failures refund and enter a separate bounded audit trail.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def _load_flowctl() -> Any:
    here = Path(__file__).resolve()
    flowctl_path = here.parent.parent / "scripts" / "flowctl.py"
    spec = importlib.util.spec_from_file_location(
        "flowctl_convergence_cap_under_test", flowctl_path
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()

REPO = Path(__file__).resolve().parents[3]
SKILLS = REPO / "plugins" / "flow-next" / "skills"


def _bash_fence_after(text: str, marker: str) -> str:
    marker_at = text.index(marker)
    fence_at = text.index("```bash\n", marker_at) + len("```bash\n")
    return text[fence_at:text.index("\n```", fence_at)]


def _bash_executable() -> str:
    """Return the POSIX shell CI uses, avoiding the Windows WSL launcher."""
    if os.name == "nt":
        git = shutil.which("git")
        if git:
            git_bash = Path(git).resolve().parent.parent / "bin" / "bash.exe"
            if git_bash.is_file():
                return str(git_bash)
    bash = shutil.which("bash")
    if bash:
        return bash
    raise RuntimeError("bash executable not found")


# ------------------------- R4: convergence ratchet -------------------------



def _ratchet_prior_container(*, status: str = "open") -> dict:
    """One minimal, strictly-valid v1 prior container (fn-168 R6 fixtures).

    Built to the production validator's contract so the tests exercise the real
    `_review_finding_prior_items` path rather than a parallel construction.
    """
    return {
        "schemaVersion": 1,
        "sourceReceiptId": "receipt-1",
        "reviewKind": "implementation",
        "backend": "codex",
        "round": 1,
        "headSha": "a" * 40,
        "items": [
            {
                "id": flowctl._review_finding_lineage_id("receipt-1", 1),
                "ordinal": 1,
                "severity": "P1",
                "confidence": 100,
                "classification": "introduced",
                "status": status,
                "title": "Prior thing",
                "body": "Body.",
                "rIds": [],
                "firstSeenReceiptId": "receipt-1",
                "lastSeenReceiptId": "receipt-1",
            }
        ],
    }


def _init_flow_repo(root: Path) -> Path:
    """Create a minimal .flow/ with one spec json for cap tests."""
    flow = root / ".flow"
    (flow / "specs").mkdir(parents=True)
    (flow / "tasks").mkdir(parents=True)
    spec_id = "fn-1-demo"
    spec_json = {
        "id": spec_id,
        "title": "Demo",
        "status": "in_progress",
    }
    (flow / "specs" / f"{spec_id}.json").write_text(json.dumps(spec_json))
    return flow


FLOWCTL_PY = REPO / "plugins" / "flow-next" / "scripts" / "flowctl.py"


class _JournalReplayBase(unittest.TestCase):
    """Shared fixture for fn-159.1 finalization-journal + replay tests."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _init_flow_repo(self.root)
        self.spec_id = "fn-1-demo"
        self._cwd = os.getcwd()
        os.chdir(self.root)
        self._old_env = os.environ.pop("MAX_REVIEW_ITERATIONS", None)

    def tearDown(self):
        os.chdir(self._cwd)
        if self._old_env is not None:
            os.environ["MAX_REVIEW_ITERATIONS"] = self._old_env
        self._tmp.cleanup()

    def _data(self) -> dict:
        return json.loads(
            (self.root / ".flow" / "specs" / f"{self.spec_id}.json").read_text()
        )

    def _reserve(self) -> str:
        artifact_sha256 = f"{len(self._data().get('review_attempts', [])):064x}"
        _, reservation_id = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", review_type="plan",
            artifact_sha256=artifact_sha256, return_reservation=True,
        )
        assert reservation_id is not None
        return reservation_id

    def _payload(self) -> dict:
        return {
            "type": "plan_review",
            "id": self.spec_id,
            "mode": "rp",
            "head": "a" * 40,
        }

    def _record_with_receipt(
        self,
        reservation_id: str,
        target: Path,
        *,
        verdict: str = "NEEDS_WORK",
    ) -> dict:
        return flowctl.record_review_attempt(
            self.spec_id,
            "plan",
            backend="rp",
            output=f"<verdict>{verdict}</verdict>",
            verdict=verdict,
            review_type="plan",
            reservation_id=reservation_id,
            receipt_target=str(target),
            receipt_payload=self._payload(),
        )

    def _record_findings_round(
        self, reservation_id: str, target: Path
    ) -> dict:
        """Record a round whose response carries a real findings container."""
        return flowctl.record_review_attempt(
            self.spec_id,
            "plan",
            backend="rp",
            output=(
                "## Issue\n"
                "- **Severity**: Major\n"
                "- **Confidence**: 100\n"
                "- **Classification**: introduced\n"
                "- **Location**: Task acceptance\n"
                f"- **Problem**: Acceptance {reservation_id} is not testable.\n"
                "- **Suggestion**: Add an executable assertion.\n"
                "<verdict>NEEDS_WORK</verdict>\n"
            ),
            verdict="NEEDS_WORK",
            review_type="plan",
            reservation_id=reservation_id,
            receipt_target=str(target),
            receipt_payload=self._payload(),
        )

    def _journal_path(self, reservation_id: str) -> Path:
        return self.root / ".flow" / "review-runs" / f"{reservation_id}.json"

    def _run_cli(self, *argv: str) -> "tuple[int, str, str]":
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with mock.patch.object(sys, "argv", ["flowctl", *argv]):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    flowctl.main()
                except SystemExit as e:
                    code = int(e.code or 0)
        return code, out.getvalue(), err.getvalue()

    def _fresh_process(self, *argv: str) -> "subprocess.CompletedProcess[str]":
        env = dict(os.environ)
        env.pop("MAX_REVIEW_ITERATIONS", None)
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY), *argv],
            cwd=self.root, env=env, capture_output=True, text=True,
        )


class TestFinalizationJournalReplay(_JournalReplayBase):
    """fn-159.1 rounds 5-8: durable write-ahead finalization + idempotent
    replay at every defined crash boundary, with zero dispatch until every
    in-scope journal is complete."""

    def test_record_journals_receipt_operation_before_consumption(self):
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        result = self._record_with_receipt(reservation_id, target)
        self.assertEqual(result["reservation_id"], reservation_id)
        journal = json.loads(self._journal_path(reservation_id).read_text())
        # The exact intended receipt operation is journaled…
        self.assertEqual(journal["receipt_target"], str(target))
        self.assertEqual(journal["receipt_payload"], self._payload())
        # …including the validated-findings parse OUTCOME (key present even
        # when the response carried no supportable findings container).
        self.assertIn("findings_container", journal)
        self.assertEqual(journal["finalized"]["receipt"], "pending")
        # record never publishes the receipt; attach/replay owns publication.
        self.assertFalse(target.exists())
        row = self._data()["review_attempts"][-1]
        self.assertEqual(row["finalized"]["receipt"], "pending")

    def test_crash_replay_preserves_provenance_fields(self):
        """fn-183 (#312), PR #324 bot finding: a crash between the journal
        write and the sidecar row write must not degrade the recovered row's
        provenance - the journal carries reviewed_head_sha / reviewed_base_sha
        / tool_calls and the replay forwards them, so the recovered row keeps
        the observed snapshot and measured count instead of falling back to
        replay-time HEAD and unknown."""
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        real_write = flowctl.atomic_write_json

        def crash_before_sidecar(path, data):
            if str(path).endswith(f"{self.spec_id}.json"):
                raise RuntimeError("crash before sidecar write")
            return real_write(path, data)

        with mock.patch.object(
            flowctl, "atomic_write_json", side_effect=crash_before_sidecar
        ):
            with self.assertRaises(RuntimeError):
                flowctl.record_review_attempt(
                    self.spec_id, "plan", backend="codex",
                    output="<verdict>NEEDS_WORK</verdict>", verdict="NEEDS_WORK",
                    review_type="plan", reservation_id=reservation_id,
                    receipt_target=str(target),
                    receipt_payload=self._payload(),
                    reviewed_head_sha="a" * 40,
                    reviewed_base_sha="c" * 40,
                    tool_calls=22,
                )
        # Crash boundary is real: journal persisted, row never landed.
        journal = json.loads(self._journal_path(reservation_id).read_text())
        self.assertEqual(journal["reviewed_head_sha"], "a" * 40)
        self.assertEqual(journal["reviewed_base_sha"], "c" * 40)
        self.assertEqual(journal["tool_calls"], 22)
        self.assertEqual(self._data().get("review_attempts", []), [])

        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(result.get("replayed"))
        row = self._data()["review_attempts"][-1]
        self.assertEqual(row["head_sha"], "a" * 40)
        self.assertIs(row["head_sha_observed"], True)
        self.assertEqual(row["base_sha"], "c" * 40)
        self.assertEqual(row["tool_calls"], 22)

    def test_crash_replay_preserves_the_resolved_model(self):
        """fn-193 (#338): the dispatch that resolved model/effort is gone by
        replay time and config cannot re-derive them (ladder downgrades, codex
        resume carries), so the journal carries them and the replay forwards
        them onto the recovered row."""
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        real_write = flowctl.atomic_write_json

        def crash_before_sidecar(path, data):
            if str(path).endswith(f"{self.spec_id}.json"):
                raise RuntimeError("crash before sidecar write")
            return real_write(path, data)

        with mock.patch.object(
            flowctl, "atomic_write_json", side_effect=crash_before_sidecar
        ):
            with self.assertRaises(RuntimeError):
                flowctl.record_review_attempt(
                    self.spec_id, "plan", backend="codex",
                    output="<verdict>NEEDS_WORK</verdict>", verdict="NEEDS_WORK",
                    review_type="plan", reservation_id=reservation_id,
                    receipt_target=str(target),
                    receipt_payload=self._payload(),
                    reviewed_head_sha="a" * 40,
                    reviewed_model="gpt-5.6-sol",
                    reviewed_effort="high",
                )
        journal = json.loads(self._journal_path(reservation_id).read_text())
        self.assertEqual(journal["reviewed_model"], "gpt-5.6-sol")
        self.assertEqual(journal["reviewed_effort"], "high")
        self.assertEqual(self._data().get("review_attempts", []), [])

        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(result.get("replayed"))
        row = self._data()["review_attempts"][-1]
        self.assertEqual(row["model"], "gpt-5.6-sol")
        self.assertEqual(row["effort"], "high")

    def test_gate_replays_receipt_typed_result_zero_dispatch(self):
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        self._record_with_receipt(reservation_id, target)
        rounds_before = self._data()["plan_review_rounds"]
        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertEqual(
            result,
            {
                "replayed": True,
                "replays": [
                    {"reservation_id": reservation_id, "verdict": "NEEDS_WORK"}
                ],
            },
        )
        # Byte-equivalent publication from the journal.
        published = json.loads(target.read_text())
        self.assertEqual(
            published,
            {**self._payload(), "review_reservation_id": reservation_id},
        )
        data = self._data()
        self.assertEqual(data["plan_review_rounds"], rounds_before)
        self.assertEqual(data.get("review_reservations", {}), {})
        self.assertEqual(
            data["review_attempts"][-1]["finalized"]["receipt"], "complete"
        )
        self.assertFalse(self._journal_path(reservation_id).exists())
        # With every journal complete, the NEXT call dispatches normally.
        follow_up = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertIsInstance(follow_up, tuple)

    def test_journal_retained_until_publisher_sidecar_write_is_durable(self):
        """PR #290 bot r6 crash boundary: process exit between the receipt
        publish and the publisher's sidecar write. The durable row still has a
        pending leg, so the journal MUST survive as its repair source."""
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        self._record_with_receipt(reservation_id, target)
        journal_path = self._journal_path(reservation_id)
        spec_path = (
            self.root / ".flow" / "specs" / f"{self.spec_id}.json"
        ).resolve()
        real_write = flowctl.atomic_write_json

        def crash_on_sidecar(path, data, *args, **kwargs):
            if Path(path).resolve() == spec_path:
                raise RuntimeError("process exit before the sidecar write")
            return real_write(path, data, *args, **kwargs)

        with mock.patch.object(flowctl, "atomic_write_json", crash_on_sidecar):
            with self.assertRaises(RuntimeError):
                flowctl._publish_review_receipt_from_journal(
                    reservation_id, str(target)
                )
        # Receipt durable, row still pending — and the journal is still there.
        self.assertTrue(target.exists())
        self.assertEqual(
            self._data()["review_attempts"][-1]["finalized"]["receipt"],
            "pending",
        )
        self.assertTrue(journal_path.exists())
        # The next invocation repairs from it: zero dispatch, row completed,
        # journal finally dropped.
        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(isinstance(result, dict) and result["replayed"])
        self.assertEqual(
            self._data()["review_attempts"][-1]["finalized"]["receipt"],
            "complete",
        )
        self.assertFalse(journal_path.exists())
        # …and the round after that dispatches normally again.
        self.assertIsInstance(
            flowctl.enforce_and_increment_review_cap(
                self.spec_id, "plan", return_reservation=True
            ),
            tuple,
        )

    def test_retained_completed_journal_replays_as_idempotent_noop(self):
        """Crash between the sidecar write and the journal unlink: the
        retained cleanup-pending journal re-applies as a pure no-op."""
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        self._record_with_receipt(reservation_id, target)
        journal_path = self._journal_path(reservation_id)
        journal = json.loads(journal_path.read_text())
        self.assertTrue(
            flowctl._publish_review_receipt_from_journal(
                reservation_id, str(target)
            )
        )
        self.assertFalse(journal_path.exists())
        # Resurrect the journal exactly as the cleanup-pending crash leaves it.
        journal["finalized"] = {
            leg: "complete" if state == "pending" else state
            for leg, state in journal["finalized"].items()
        }
        journal["cleanup"] = "pending"
        journal_path.write_text(json.dumps(journal))
        receipt_before = target.read_text()
        rows_before = self._data()["review_attempts"]
        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(isinstance(result, dict) and result["replayed"])
        self.assertEqual(target.read_text(), receipt_before)
        self.assertEqual(self._data()["review_attempts"], rows_before)
        self.assertFalse(journal_path.exists())

    def test_receipt_published_progress_unmarked_replay_is_noop(self):
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        self._record_with_receipt(reservation_id, target)
        # Crash boundary: receipt published, journal progress unmarked.
        payload = {**self._payload(), "review_reservation_id": reservation_id}
        target.write_text(json.dumps(payload, indent=2, sort_keys=True))
        before = target.read_text()
        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(isinstance(result, dict) and result["replayed"])
        self.assertEqual(json.loads(target.read_text()), json.loads(before))
        self.assertFalse(self._journal_path(reservation_id).exists())

    def test_digest_written_receipt_missing_replays_receipt(self):
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        self._record_with_receipt(reservation_id, target)
        journal_path = self._journal_path(reservation_id)
        journal = json.loads(journal_path.read_text())
        # Crash boundary: digest leg already complete, receipt still missing.
        journal["finalized"]["digest"] = "complete"
        journal_path.write_text(json.dumps(journal))
        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(isinstance(result, dict) and result["replayed"])
        self.assertEqual(
            json.loads(target.read_text()),
            {**self._payload(), "review_reservation_id": reservation_id},
        )
        self.assertFalse(journal_path.exists())

    def test_receipt_pointer_advanced_replay_is_superseded_noop(self):
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        self._record_with_receipt(reservation_id, target)
        # A LATER reservation already advanced the receipt pointer: replaying
        # the old bytes over it would regress the newer receipt. Supersession
        # must be PROVEN, so the newer id is backed by a finalized attempt row
        # in the same scope stamped after this journal was created.
        newer_id = "f" * 32
        spec_path = self.root / ".flow" / "specs" / f"{self.spec_id}.json"
        data = json.loads(spec_path.read_text())
        data["review_attempts"].append({
            "timestamp": "9999-01-01T00:00:00Z",
            "scope": "plan", "counter_kind": "plan", "task": None,
            "kind": "plan", "backend": "rp", "outcome": "verdict",
            "verdict": "NEEDS_WORK", "reservation_id": newer_id,
            "finalized": {
                "receipt": "complete", "digest": "not_applicable",
                "status": "not_applicable",
            },
        })
        spec_path.write_text(json.dumps(data))
        newer = {**self._payload(), "review_reservation_id": newer_id}
        target.write_text(json.dumps(newer))
        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(isinstance(result, dict) and result["replayed"])
        self.assertEqual(json.loads(target.read_text()), newer)
        self.assertFalse(self._journal_path(reservation_id).exists())

    def test_unproven_differing_receipt_id_is_published_over(self):
        """Round-1 review r1 P0: a differing reservation id on a REUSED
        receipt path is the PRIOR round, not a newer one. Without proof of
        supersession the delivered verdict must be published, never dropped."""
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        self._record_with_receipt(reservation_id, target)
        # No attempt row backs this id: unproven, therefore not superseding.
        target.write_text(
            json.dumps({**self._payload(), "review_reservation_id": "f" * 32})
        )
        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(isinstance(result, dict) and result["replayed"])
        self.assertEqual(
            json.loads(target.read_text()),
            {**self._payload(), "review_reservation_id": reservation_id},
        )
        self.assertFalse(self._journal_path(reservation_id).exists())

    def test_legacy_receipt_without_reservation_id_is_published_over(self):
        """Round-1 review r1 P0: a pre-fn-159 receipt carries no reservation
        id; publishing over it must succeed instead of failing closed and
        wedging every later gate call on REPLAY_REQUIRED."""
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        self._record_with_receipt(reservation_id, target)
        target.write_text(json.dumps({**self._payload(), "verdict": "SHIP"}))
        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(isinstance(result, dict) and result["replayed"])
        self.assertEqual(
            json.loads(target.read_text()),
            {**self._payload(), "review_reservation_id": reservation_id},
        )
        self.assertFalse(self._journal_path(reservation_id).exists())
        # The gate is not wedged: the next call dispatches normally.
        self.assertIsInstance(
            flowctl.enforce_and_increment_review_cap(
                self.spec_id, "plan", return_reservation=True
            ),
            tuple,
        )

    def test_two_rounds_against_one_receipt_path_land_second_payload(self):
        """Round-1 review r1 P0: receipt paths are stable per spec, so the
        second round's journaled payload must land over the first."""
        first = self._reserve()
        target = self.root / "receipt.json"
        self._record_with_receipt(first, target)
        code, _, err = self._run_cli(
            "review-findings", "attach", "--reservation-id", first,
            "--receipt", str(target), "--json",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(
            json.loads(target.read_text())["review_reservation_id"], first
        )
        second = self._reserve()
        self._record_with_receipt(second, target, verdict="SHIP")
        code, out, err = self._run_cli(
            "review-findings", "attach", "--reservation-id", second,
            "--receipt", str(target), "--json",
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(json.loads(out)["published_from_journal"])
        self.assertEqual(
            json.loads(target.read_text()),
            {**self._payload(), "review_reservation_id": second},
        )
        self.assertFalse(self._journal_path(second).exists())
        row = self._data()["review_attempts"][-1]
        self.assertEqual(row["reservation_id"], second)
        self.assertEqual(row["finalized"]["receipt"], "complete")

    def test_journal_publish_preserves_prior_receipt_generation(self):
        """Round-1 review r1 P2: the journal publish must preserve the prior
        findings generation exactly like the direct writer and legacy attach."""
        target = self.root / "receipt.json"
        first = self._reserve()
        self._record_findings_round(first, target)
        code, _, err = self._run_cli(
            "review-findings", "attach", "--reservation-id", first,
            "--receipt", str(target), "--json",
        )
        self.assertEqual(code, 0, err)
        first_findings = json.loads(target.read_text())["findings"]
        second = self._reserve()
        self._record_findings_round(second, target)
        code, _, err = self._run_cli(
            "review-findings", "attach", "--reservation-id", second,
            "--receipt", str(target), "--json",
        )
        self.assertEqual(code, 0, err)
        second_findings = json.loads(target.read_text())["findings"]
        self.assertNotEqual(
            second_findings["sourceReceiptId"],
            first_findings["sourceReceiptId"],
        )
        generations = flowctl.load_review_receipt_generations(target)
        self.assertIsNotNone(generations)
        self.assertEqual(len(generations), 2)
        self.assertIn(
            first_findings["sourceReceiptId"],
            {entry["findings"]["sourceReceiptId"] for entry in generations},
        )

    def test_completion_journal_publish_carries_bound_criteria(self):
        """Round-1 review r1 P2: record binds completion criteria into the
        journal, so a journal-published completion receipt keeps them."""
        (self.root / ".flow" / "criteria.md").write_text(
            "- **G1:** Every route change regenerates the contract.\n",
            encoding="utf-8",
        )
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        payload = {
            "type": "completion_review", "id": self.spec_id,
            "mode": "rp", "head": "a" * 40,
        }
        flowctl.record_review_attempt(
            self.spec_id, "plan", backend="rp",
            output=(
                "## Global criteria\n"
                "G1: met - contract regenerated\n"
                "<verdict>SHIP</verdict>\n"
            ),
            verdict="SHIP", review_type="completion",
            reservation_id=reservation_id,
            receipt_target=str(target), receipt_payload=payload,
        )
        journal = json.loads(self._journal_path(reservation_id).read_text())
        self.assertEqual(
            journal["criteria"],
            [{"id": "G1", "status": "met", "note": "contract regenerated"}],
        )
        code, _, err = self._run_cli(
            "review-findings", "attach", "--reservation-id", reservation_id,
            "--receipt", str(target), "--json",
        )
        self.assertEqual(code, 0, err)
        published = json.loads(target.read_text())
        self.assertEqual(
            published["criteria"],
            [{"id": "G1", "status": "met", "note": "contract regenerated"}],
        )
        self.assertTrue(flowctl.validate_review_receipt_criteria(published))

    def test_mixed_verdict_two_incomplete_journals_zero_dispatch(self):
        first, second = self._reserve(), self._reserve()
        self._record_with_receipt(first, self.root / "a.json", verdict="SHIP")
        self._record_with_receipt(
            second, self.root / "b.json", verdict="NEEDS_WORK"
        )
        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(isinstance(result, dict) and result["replayed"])
        self.assertEqual(
            {(r["reservation_id"], r["verdict"]) for r in result["replays"]},
            {(first, "SHIP"), (second, "NEEDS_WORK")},
        )
        data = self._data()
        # Zero dispatch: nothing reserved, counter untouched by the replay.
        self.assertEqual(data.get("review_reservations", {}), {})
        self.assertEqual(data["plan_review_rounds"], 2)
        self.assertNotIn("plan", data.get("review_pending_rounds", {}))

    def test_per_verdict_replay_ship_only(self):
        reservation_id = self._reserve()
        self._record_with_receipt(
            reservation_id, self.root / "receipt.json", verdict="SHIP"
        )
        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertEqual(
            result["replays"],
            [{"reservation_id": reservation_id, "verdict": "SHIP"}],
        )
        self.assertEqual(self._data().get("review_reservations", {}), {})

    def test_pending_leg_without_journal_refuses_dispatch(self):
        reservation_id = self._reserve()
        self._record_with_receipt(reservation_id, self.root / "receipt.json")
        self._journal_path(reservation_id).unlink()
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as exc:
                flowctl.enforce_and_increment_review_cap(
                    self.spec_id, "plan", return_reservation=True
                )
        self.assertEqual(exc.exception.code, 2)
        self.assertIn("REPLAY_REQUIRED", err.getvalue())

    def test_no_findings_digest_leg_completes_never_blocks(self):
        """Round 7: finalized.digest tracks the OPERATION — a completed parse
        with no supportable findings (legacy/malformed/absent) is complete."""
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        self._record_with_receipt(reservation_id, target)
        journal_path = self._journal_path(reservation_id)
        journal = json.loads(journal_path.read_text())
        self.assertIsNone(journal["findings_container"])  # no-findings parse
        journal["finalized"]["digest"] = "pending"
        journal_path.write_text(json.dumps(journal))
        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(isinstance(result, dict) and result["replayed"])
        self.assertFalse(journal_path.exists())

    def test_interrupted_digest_operation_stays_pending_and_blocks(self):
        reservation_id = self._reserve()
        self._record_with_receipt(reservation_id, self.root / "receipt.json")
        journal_path = self._journal_path(reservation_id)
        journal = json.loads(journal_path.read_text())
        journal["finalized"]["digest"] = "pending"
        del journal["findings_container"]  # operation never completed
        journal_path.write_text(json.dumps(journal))
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as exc:
                flowctl.enforce_and_increment_review_cap(
                    self.spec_id, "plan", return_reservation=True
                )
        self.assertEqual(exc.exception.code, 2)
        self.assertIn("REPLAY_REQUIRED", err.getvalue())

    def test_attach_reservation_id_publishes_journaled_payload(self):
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        self._record_with_receipt(reservation_id, target)
        code, out, _ = self._run_cli(
            "review-findings", "attach",
            "--reservation-id", reservation_id,
            "--receipt", str(target), "--json",
        )
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertTrue(payload["published_from_journal"])
        self.assertEqual(
            json.loads(target.read_text()),
            {**self._payload(), "review_reservation_id": reservation_id},
        )
        row = self._data()["review_attempts"][-1]
        self.assertEqual(row["finalized"]["receipt"], "complete")
        self.assertFalse(self._journal_path(reservation_id).exists())

    def test_attach_unknown_reservation_id_exit_two_zero_mutation(self):
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        self._record_with_receipt(reservation_id, target)
        before = self._data()
        code, _, err = self._run_cli(
            "review-findings", "attach",
            "--reservation-id", "0" * 32,
            "--receipt", str(target), "--json",
        )
        self.assertEqual(code, 2)
        self.assertEqual(self._data(), before)
        self.assertFalse(target.exists())

    def test_status_surface_reservation_id_requires_exactly_one_attempt(self):
        reservation_id = self._reserve()
        flowctl.record_review_attempt(
            self.spec_id, "plan", backend="rp",
            output="<verdict>SHIP</verdict>", verdict="SHIP",
            review_type="plan", reservation_id=reservation_id,
        )
        # Simulate an out-of-band status leg left pending on the row.
        spec_path = self.root / ".flow" / "specs" / f"{self.spec_id}.json"
        data = json.loads(spec_path.read_text())
        data["review_attempts"][-1]["finalized"]["status"] = "pending"
        spec_path.write_text(json.dumps(data))
        code, _, _ = self._run_cli(
            "spec", "set-plan-review-status", self.spec_id,
            "--status", "ship", "--reservation-id", reservation_id, "--json",
        )
        self.assertEqual(code, 0)
        data = self._data()
        self.assertEqual(data["plan_review_status"], "ship")
        self.assertEqual(
            data["review_attempts"][-1]["finalized"]["status"], "complete"
        )
        # Unknown reservation id: exit 2, zero mutation.
        before = self._data()
        code, _, _ = self._run_cli(
            "spec", "set-plan-review-status", self.spec_id,
            "--status", "needs_work", "--reservation-id", "0" * 32, "--json",
        )
        self.assertEqual(code, 2)
        self.assertEqual(self._data(), before)

    def test_fresh_process_crash_after_record_before_attach_input_exists(self):
        """Round 7 named test: record journaled the receipt operation and
        consumed the reservation, then the process died before the attach
        fence ever created its input file. A FRESH process replays the
        receipt byte-equivalently from the journal — zero dispatch — with
        the original /tmp response file already deleted."""
        reserve = self._fresh_process(
            "review-rounds", "increment", self.spec_id, "--kind", "plan",
            "--review-type", "plan", "--json",
        )
        self.assertEqual(reserve.returncode, 0, reserve.stderr)
        reservation_id = json.loads(reserve.stdout)["reservation_id"]
        response = self.root / "response.txt"
        response.write_text("<verdict>NEEDS_WORK</verdict>")
        payload_file = self.root / "payload.json"
        payload_file.write_text(json.dumps(self._payload()))
        target = self.root / "receipt.json"
        record = self._fresh_process(
            "review-rounds", "record", self.spec_id, "--kind", "plan",
            "--review-type", "plan", "--output-file", str(response),
            "--reservation-id", reservation_id,
            "--receipt-target", str(target),
            "--receipt-payload-file", str(payload_file), "--json",
        )
        self.assertEqual(record.returncode, 0, record.stderr)
        response.unlink()  # the reviewer response is gone forever
        self.assertFalse(target.exists())  # attach input never existed
        replay = self._fresh_process(
            "review-rounds", "increment", self.spec_id, "--kind", "plan",
            "--review-type", "plan", "--json",
        )
        self.assertEqual(replay.returncode, 0, replay.stderr)
        result = json.loads(replay.stdout)
        self.assertTrue(result["replayed"])
        self.assertEqual(
            result["replays"],
            [{"reservation_id": reservation_id, "verdict": "NEEDS_WORK"}],
        )
        # Byte-equivalent receipt replay after process restart.
        self.assertEqual(
            json.loads(target.read_text()),
            {**self._payload(), "review_reservation_id": reservation_id},
        )
        data = self._data()
        self.assertEqual(data.get("review_reservations", {}), {})
        self.assertEqual(data["plan_review_rounds"], 1)

    def test_ship_record_cli_is_system_owned_reset(self):
        """fn-159 R9: recording SHIP resets the counter AND advances the hash
        epoch inside record itself — no explicit reset verb needed."""
        code, out, _ = self._run_cli(
            "review-rounds", "increment", self.spec_id, "--kind", "plan",
            "--json",
        )
        self.assertEqual(code, 0)
        response = self.root / "response.txt"
        response.write_text("<verdict>SHIP</verdict>")
        code, _, _ = self._run_cli(
            "review-rounds", "record", self.spec_id, "--kind", "plan",
            "--review-type", "plan", "--output-file", str(response), "--json",
        )
        self.assertEqual(code, 0)
        data = self._data()
        self.assertEqual(data["plan_review_rounds"], 0)
        self.assertEqual(data["review_hash_epoch"]["plan"], 1)
        # fn-134.7 / R22: pending untouched by the reset half (record's own
        # consume already popped it; nothing else was cleared).
        self.assertNotIn("plan", data.get("review_pending_rounds", {}))


class TestArtifactHashDispatchGuard(unittest.TestCase):
    """fn-159.7: domain identities and the no-repeat dispatch terminal."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _init_flow_repo(self.root)
        self.spec_id = "fn-1-demo"
        self._cwd = os.getcwd()
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _data(self) -> dict:
        return json.loads(
            (self.root / ".flow" / "specs" / f"{self.spec_id}.json").read_text()
        )

    def _reserve_and_record(
        self,
        artifact_sha256: str,
        *,
        review_type: str = "plan",
        forced: bool = False,
    ) -> str:
        _, reservation_id = flowctl.enforce_and_increment_review_cap(
            self.spec_id,
            "plan",
            artifact_sha256=artifact_sha256,
            review_type=review_type,
            forced=forced,
            return_reservation=True,
        )
        self.assertIsNotNone(reservation_id)
        flowctl.record_review_attempt(
            self.spec_id,
            "plan",
            backend="host",
            output="<verdict>NEEDS_WORK</verdict>",
            verdict="NEEDS_WORK",
            review_type=review_type,
            reservation_id=reservation_id,
        )
        return reservation_id

    def test_plan_impl_and_completion_blobs_are_normalized_and_domain_separated(self):
        plan_lf = flowctl.build_plan_review_artifact_blob(
            "# Spec\n", "### fn-1.1\n\nTask\n"
        )
        plan_crlf = flowctl.build_plan_review_artifact_blob(
            "# Spec\r\n", "### fn-1.1\r\n\r\nTask\r\n"
        )
        completion = flowctl.build_completion_review_artifact_blob(
            "# Spec\n", "### fn-1.1\n\nTask\n", "diff", ""
        )
        impl = flowctl.build_impl_review_artifact_blob("diff")
        self.assertEqual(plan_lf, plan_crlf)
        self.assertNotEqual(
            flowctl._review_artifact_sha256(plan_lf),
            flowctl._review_artifact_sha256(completion),
        )
        self.assertNotEqual(
            flowctl._review_artifact_sha256(completion),
            flowctl._review_artifact_sha256(impl),
        )

    def test_four_same_artifact_dispatches_yield_one_record_and_three_refusals(self):
        artifact = flowctl._review_artifact_sha256(
            flowctl.build_plan_review_artifact_blob("spec", "tasks")
        )
        self._reserve_and_record(artifact)
        for _ in range(3):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as exc:
                    flowctl.enforce_and_increment_review_cap(
                        self.spec_id, "plan", artifact_sha256=artifact,
                        review_type="plan", return_reservation=True,
                    )
            self.assertEqual(exc.exception.code, 1)
            self.assertEqual(
                err.getvalue().strip(),
                "NOT_RETRYABLE: artifact unchanged since last verdict",
            )
        self.assertEqual(len(self._data()["review_attempts"]), 1)
        self.assertEqual(self._data()["plan_review_rounds"], 1)

    def test_baseline_ignores_the_other_review_type_on_the_shared_counter(self):
        """fn-159.7 review r1: plan and completion share the plan counter, so
        an interleaved completion row must not become the plan baseline."""
        plan_artifact = flowctl._review_artifact_sha256(
            flowctl.build_plan_review_artifact_blob("spec", "tasks")
        )
        completion_artifact = flowctl._review_artifact_sha256(
            flowctl.build_completion_review_artifact_blob(
                "spec", "tasks", "diff", ""
            )
        )
        self._reserve_and_record(plan_artifact, review_type="plan")
        self._reserve_and_record(completion_artifact, review_type="completion")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as exc:
                flowctl.enforce_and_increment_review_cap(
                    self.spec_id, "plan", artifact_sha256=plan_artifact,
                    review_type="plan", return_reservation=True,
                )
        self.assertEqual(exc.exception.code, 1)
        self.assertEqual(
            err.getvalue().strip(),
            "NOT_RETRYABLE: artifact unchanged since last verdict",
        )
        self.assertEqual(len(self._data()["review_attempts"]), 2)

    def test_reset_allows_clean_redispatch_without_force(self):
        artifact = flowctl._review_artifact_sha256(
            flowctl.build_plan_review_artifact_blob("spec", "tasks")
        )
        self._reserve_and_record(artifact)
        flowctl.reset_review_cap(self.spec_id, "plan")
        round_number, reservation_id = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", artifact_sha256=artifact,
            review_type="plan", return_reservation=True,
        )
        self.assertEqual(round_number, 1)
        self.assertIsNotNone(reservation_id)

    def test_force_consumes_and_stamps_forced_provenance(self):
        artifact = flowctl._review_artifact_sha256(
            flowctl.build_plan_review_artifact_blob("spec", "tasks")
        )
        self._reserve_and_record(artifact)
        self._reserve_and_record(artifact, forced=True)
        self.assertTrue(self._data()["review_attempts"][-1]["forced"])

    def test_absent_hash_and_hash_builder_failure_fail_open_with_warning(self):
        artifact = flowctl._review_artifact_sha256(
            flowctl.build_plan_review_artifact_blob("spec", "tasks")
        )
        self._reserve_and_record(artifact)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            round_number, _ = flowctl.enforce_and_increment_review_cap(
                self.spec_id, "plan", review_type="plan", return_reservation=True
            )
        self.assertEqual(round_number, 2)
        self.assertIn("guard is fail-open", err.getvalue())
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            failed_hash = flowctl._review_artifact_hash_or_warn(
                lambda _text: (_ for _ in ()).throw(ValueError("hash read failed")),
                "artifact",
            )
        self.assertIsNone(failed_hash)
        self.assertIn("guard is fail-open", err.getvalue())

    def test_completion_after_impl_only_fix_and_plan_completion_boundary_dispatch(self):
        plan = flowctl._review_artifact_sha256(
            flowctl.build_plan_review_artifact_blob("spec", "tasks")
        )
        completion_before = flowctl._review_artifact_sha256(
            flowctl.build_completion_review_artifact_blob(
                "spec", "tasks", "impl diff before", "criteria"
            )
        )
        completion_after = flowctl._review_artifact_sha256(
            flowctl.build_completion_review_artifact_blob(
                "spec", "tasks", "impl diff after", "criteria"
            )
        )
        self._reserve_and_record(plan, review_type="plan")
        # Plan and completion share a counter but can never collide.
        self._reserve_and_record(completion_before, review_type="completion")
        # Completion NEEDS_WORK followed by an implementation-only change gets
        # a fresh completion reservation without a human reset or --force.
        round_number, reservation_id = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", artifact_sha256=completion_after,
            review_type="completion", return_reservation=True,
        )
        self.assertEqual(round_number, 3)
        self.assertIsNotNone(reservation_id)

    def test_ce_setup_failure_refunds_only_its_reservation(self):
        self._assert_transport_refund_is_reservation_scoped("ce")

    def test_classic_setup_failure_refunds_only_its_reservation(self):
        self._assert_transport_refund_is_reservation_scoped("classic")

    def _assert_transport_refund_is_reservation_scoped(self, mode: str) -> None:
        _, first = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", review_type="plan", return_reservation=True
        )
        _, second = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", review_type="plan", return_reservation=True
        )
        flowctl.record_review_attempt(
            self.spec_id, "plan", backend="rp",
            output=f"{mode} setup failed", failure_class="nonzero_exit",
            review_type="plan", reservation_id=first,
        )
        data = self._data()
        self.assertIn(second, data["review_reservations"])
        self.assertEqual(data["plan_review_rounds"], 1)

    def test_mode_probe_only_checks_cli_availability(self):
        for executable, expected in (("/tmp/rp-cli", "classic"), ("/tmp/rp", "ce")):
            with self.subTest(executable=executable):
                out = io.StringIO()
                with mock.patch.object(flowctl, "require_rp_cli", return_value=executable), \
                     mock.patch.object(flowctl, "bind_context_window") as bind, \
                     contextlib.redirect_stdout(out):
                    flowctl.cmd_rp_mode_probe(mock.Mock(json=True))
                self.assertEqual(json.loads(out.getvalue())["mode"], expected)
                bind.assert_not_called()

    def test_host_finalize_uses_the_reserved_id(self):
        artifact = flowctl._review_artifact_sha256(
            flowctl.build_plan_review_artifact_blob("spec", "tasks")
        )
        _, reservation_id = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", artifact_sha256=artifact,
            review_type="plan", return_reservation=True,
        )
        verdict = flowctl._finish_backend_exec(
            backend="host",
            reg={"has_sandbox": False, "cli_label": "host", "no_verdict_label": "Host"},
            args=mock.Mock(json=False), receipt_path=None,
            output="<verdict>NEEDS_WORK</verdict>", stderr="", exit_code=0,
            spec_id=self.spec_id, review_kind="plan", review_type="plan",
            reservation_id=reservation_id,
        )
        self.assertEqual(verdict, "NEEDS_WORK")
        self.assertEqual(
            self._data()["review_attempts"][-1]["reservation_id"], reservation_id
        )


class TestNeedsHumanTerminal(_JournalReplayBase):
    """R3: every delivered NEEDS_HUMAN persists before exit 4."""

    def _record_and_attach(
        self,
        *,
        backend: str,
        counter_kind: str,
        review_type: str,
        receipt_type: str,
        status_target: str | None = None,
        task_id: str | None = None,
    ) -> tuple[dict, Path]:
        _, reservation_id = flowctl.enforce_and_increment_review_cap(
            self.spec_id,
            counter_kind,
            task_id=task_id,
            review_type=review_type,
            return_reservation=True,
        )
        assert reservation_id is not None
        receipt = self.root / f"{backend}-{review_type}.json"
        payload = {
            "type": receipt_type,
            "id": task_id or self.spec_id,
            "mode": backend,
            "verdict": "NEEDS_HUMAN",
        }
        flowctl.record_review_attempt(
            self.spec_id,
            counter_kind,
            backend=backend,
            output="<verdict>NEEDS_HUMAN</verdict>",
            verdict="NEEDS_HUMAN",
            task_id=task_id,
            review_type=review_type,
            reservation_id=reservation_id,
            receipt_target=str(receipt),
            receipt_payload=payload,
            status_target=status_target,
        )
        with contextlib.redirect_stdout(io.StringIO()):
            flowctl.cmd_review_findings_attach(
                mock.Mock(
                    reservation_id=reservation_id,
                    receipt=str(receipt),
                    json=True,
                )
            )
        return self._data(), receipt

    def _assert_human_exit_after_persistence(
        self, data: dict, receipt: Path, *, status_key: str | None
    ) -> None:
        row = data["review_attempts"][-1]
        self.assertTrue(row["round_consumed"])
        self.assertEqual(row["verdict"], "NEEDS_HUMAN")
        self.assertEqual(row["finalized"]["receipt"], "complete")
        self.assertEqual(json.loads(receipt.read_text())["verdict"], "NEEDS_HUMAN")
        if status_key:
            self.assertEqual(data[status_key], "needs_human")
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as ctx:
                flowctl._exit_needs_human_after_persistence(
                    "NEEDS_HUMAN", use_json=False
                )
        self.assertEqual(ctx.exception.code, flowctl.REVIEW_CAP_EXIT_CODE)
        self.assertIn("ESCALATE: reviewer requested human review", err.getvalue())

    def test_plan_needs_human_persists_before_exit(self):
        data, receipt = self._record_and_attach(
            backend="codex",
            counter_kind="plan",
            review_type="plan",
            receipt_type="plan_review",
            status_target="plan",
        )
        self._assert_human_exit_after_persistence(
            data, receipt, status_key="plan_review_status"
        )

    def test_impl_needs_human_persists_before_exit(self):
        data, receipt = self._record_and_attach(
            backend="copilot",
            counter_kind="impl",
            review_type="impl",
            receipt_type="impl_review",
            task_id=f"{self.spec_id}.1",
        )
        self._assert_human_exit_after_persistence(data, receipt, status_key=None)

    def test_completion_needs_human_persists_before_exit(self):
        data, receipt = self._record_and_attach(
            backend="cursor",
            counter_kind="plan",
            review_type="completion",
            receipt_type="completion_review",
            status_target="completion",
        )
        self._assert_human_exit_after_persistence(
            data, receipt, status_key="completion_review_status"
        )

    def test_status_cli_accepts_needs_human_for_plan_and_completion(self):
        for command, key in (
            ("set-plan-review-status", "plan_review_status"),
            ("set-completion-review-status", "completion_review_status"),
        ):
            with self.subTest(command=command):
                code, _, err = self._run_cli(
                    "spec", command, self.spec_id, "--status", "needs_human", "--json"
                )
                self.assertEqual(code, 0, err)
                self.assertEqual(self._data()[key], "needs_human")

    def test_standalone_needs_human_receipt_precedes_exit(self):
        receipt = self.root / "standalone.json"
        flowctl._write_backend_review_receipt(
            str(receipt),
            review_type="impl_review",
            review_id="branch",
            backend="codex",
            verdict="NEEDS_HUMAN",
            session_id=None,
            effective_model="test-model",
            effective_effort=None,
            resolved_spec=mock.Mock(),
            review_text="<verdict>NEEDS_HUMAN</verdict>",
            include_effort=False,
            findings_built=True,
        )
        self.assertEqual(json.loads(receipt.read_text())["verdict"], "NEEDS_HUMAN")
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                flowctl._exit_needs_human_after_persistence(
                    "NEEDS_HUMAN", use_json=False
                )
        self.assertEqual(ctx.exception.code, 4)

    def test_rp_nonzero_delivery_persists_before_exit(self):
        _, reservation_id = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", review_type="plan", return_reservation=True
        )
        assert reservation_id is not None
        response = self.root / "rp-response.md"
        response.write_text("<verdict>NEEDS_HUMAN</verdict>")
        receipt = self.root / "rp-receipt.json"
        payload = self.root / "rp-payload.json"
        payload.write_text(json.dumps({
            "type": "plan_review", "id": self.spec_id, "mode": "rp",
            "verdict": "NEEDS_HUMAN",
        }))
        code, _, err = self._run_cli(
            "review-rounds", "record", self.spec_id, "--kind", "plan",
            "--review-type", "plan", "--backend", "rp", "--output-file",
            str(response), "--reservation-id", reservation_id, "--receipt-target",
            str(receipt), "--receipt-payload-file", str(payload), "--status-target",
            "plan", "--exit-code", "7", "--json",
        )
        self.assertEqual(code, 0, err)
        code, _, err = self._run_cli(
            "review-findings", "attach", "--reservation-id", reservation_id,
            "--receipt", str(receipt), "--json",
        )
        self.assertEqual(code, 0, err)
        self._assert_human_exit_after_persistence(
            self._data(), receipt, status_key="plan_review_status"
        )

    def test_incomplete_finalization_replay_persists_before_exit_without_redispatch(self):
        _, reservation_id = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", review_type="plan", return_reservation=True
        )
        assert reservation_id is not None
        receipt = self.root / "replay-receipt.json"
        flowctl.record_review_attempt(
            self.spec_id,
            "plan",
            backend="rp",
            output="<verdict>NEEDS_HUMAN</verdict>",
            verdict="NEEDS_HUMAN",
            review_type="plan",
            reservation_id=reservation_id,
            receipt_target=str(receipt),
            receipt_payload={
                "type": "plan_review", "id": self.spec_id, "mode": "rp",
                "verdict": "NEEDS_HUMAN",
            },
            status_target="plan",
        )
        replay = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(isinstance(replay, dict) and replay["replayed"])
        self.assertEqual(flowctl.review_replay_terminal_verdict(replay["replays"]), "NEEDS_HUMAN")
        data = self._data()
        self.assertEqual(len(data["review_attempts"]), 1)
        self._assert_human_exit_after_persistence(
            data, receipt, status_key="plan_review_status"
        )

    def test_rp_workflow_fences_attach_before_needs_human_exit(self):
        for relative in (
            "flow-next-plan-review/workflow-rp.md",
            "flow-next-impl-review/workflow-rp.md",
            "flow-next-spec-completion-review/workflow-rp.md",
        ):
            with self.subTest(workflow=relative):
                text = (SKILLS / relative).read_text(encoding="utf-8")
                attach_at = text.index("review-findings attach")
                terminal_at = text.index(
                    "ESCALATE: reviewer requested human review", attach_at
                )
                self.assertLess(attach_at, terminal_at)


class TestNeedsHumanHandlerOrdering(unittest.TestCase):
    """fn-159.3 r1: run a NEEDS_HUMAN dispatch end-to-end through the
    in-process handlers. The ordering claim itself is the assertion - the
    attempt row, the receipt, and (for plan) the denormalized status must all
    be durable AT the moment the handler exits 4, and stdout must carry
    exactly one JSON object."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        _init_flow_repo(self.root)
        self.spec_id = "fn-1-demo"
        (self.root / ".flow" / "specs" / f"{self.spec_id}.md").write_text(
            "# Demo\n\n## Acceptance Criteria\n\n- R1: works\n", encoding="utf-8"
        )
        (self.root / ".flow" / "tasks" / f"{self.spec_id}.1.md").write_text(
            "# Task 1\n\nImplement R1.\n", encoding="utf-8"
        )
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        (self.root / "app.py").write_text("x = 1\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", "base")
        (self.root / "app.py").write_text("x = 2\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", "change")
        self._cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self._cwd)
        self._old_env = os.environ.pop("MAX_REVIEW_ITERATIONS", None)
        if self._old_env is not None:
            self.addCleanup(
                os.environ.__setitem__, "MAX_REVIEW_ITERATIONS", self._old_env
            )
        flowctl._wire_backend_review_hooks()

    def _git(self, *argv: str) -> None:
        subprocess.run(
            ["git", *argv], cwd=self.root, check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def _data(self) -> dict:
        return json.loads(
            (self.root / ".flow" / "specs" / f"{self.spec_id}.json").read_text()
        )

    def _run(self, handler, args) -> "tuple[dict, int]":
        def fake_exec(_prompt, **_kwargs):
            return "<verdict>NEEDS_HUMAN</verdict>", "sess-1", 0, ""

        out = io.StringIO()
        with mock.patch.dict(
            flowctl.BACKEND_REGISTRY["codex"], {"run_exec": fake_exec}
        ):
            with contextlib.redirect_stdout(out):
                with self.assertRaises(SystemExit) as ctx:
                    handler(args, "codex")
        return json.loads(out.getvalue()), ctx.exception.code

    def test_impl_needs_human_exits_four_with_state_durable(self):
        receipt = self.root / "impl-receipt.json"
        args = argparse.Namespace(
            task=f"{self.spec_id}.1", base="HEAD~1", focus=None, json=True,
            receipt=str(receipt), spec=None, model=None, effort=None,
            force=False, sandbox=None,
        )
        payload, code = self._run(flowctl._backend_impl_review, args)
        self.assertEqual(code, flowctl.REVIEW_CAP_EXIT_CODE)
        self.assertEqual(payload["verdict"], "NEEDS_HUMAN")
        self.assertTrue(payload["escalate"])
        self.assertFalse(payload["success"])
        self.assertEqual(
            payload["error"], flowctl.NEEDS_HUMAN_ESCALATION_MARKER
        )
        row = self._data()["review_attempts"][-1]
        self.assertEqual(row["verdict"], "NEEDS_HUMAN")
        self.assertTrue(row["round_consumed"])
        self.assertEqual(
            json.loads(receipt.read_text())["verdict"], "NEEDS_HUMAN"
        )

    def test_plan_needs_human_exits_four_with_status_durable(self):
        receipt = self.root / "plan-receipt.json"
        args = argparse.Namespace(
            epic=self.spec_id, base="HEAD~1", json=True, files="app.py",
            receipt=str(receipt), spec=None, model=None, effort=None,
            force=False, sandbox=None,
        )
        payload, code = self._run(flowctl._backend_plan_review, args)
        self.assertEqual(code, flowctl.REVIEW_CAP_EXIT_CODE)
        self.assertEqual(payload["verdict"], "NEEDS_HUMAN")
        self.assertTrue(payload["escalate"])
        self.assertFalse(payload["success"])
        data = self._data()
        row = data["review_attempts"][-1]
        self.assertEqual(row["verdict"], "NEEDS_HUMAN")
        self.assertTrue(row["round_consumed"])
        self.assertEqual(data["plan_review_status"], "needs_human")
        self.assertEqual(
            json.loads(receipt.read_text())["verdict"], "NEEDS_HUMAN"
        )
        self.assertEqual(payload["plan_review_status"], "needs_human")


class TestSupersededVerdictNeverSurfacesAsTerminal(TestNeedsHumanHandlerOrdering):
    """PR #290 bot r8: a concurrent SHIP lands WHILE a review is in flight.

    The late finalization correctly consumes nothing and writes no status, but
    the handler used to route its NEEDS_WORK/NEEDS_HUMAN out as a live terminal
    — exit 4 / fix-loop — while durable state said ship, so pilot and Ralph
    acted on a pre-SHIP artifact. The late verdict must surface as SUPERSEDED
    evidence instead.
    """

    def _run_with_concurrent_ship(
        self, handler, args, verdict: str, *, review_kind: str,
        ship_review_type: str, task_id=None,
    ) -> "tuple[dict, str]":
        """Run a handler while a SHIP of ``ship_review_type`` lands mid-dispatch."""

        def fake_exec(_prompt, **_kwargs):
            # The concurrent SHIP lands after this review reserved its round
            # and before it finalizes — the exact interleave.
            _, ship_id = flowctl.enforce_and_increment_review_cap(
                self.spec_id, review_kind, task_id=task_id,
                review_type=ship_review_type,
                return_reservation=True,
            )
            flowctl.record_review_attempt(
                self.spec_id, review_kind, backend="rp",
                output="<verdict>SHIP</verdict>", verdict="SHIP",
                task_id=task_id,
                review_type=ship_review_type,
                reservation_id=ship_id,
                status_target=(
                    ship_review_type
                    if ship_review_type in ("plan", "completion") else None
                ),
                reset_rounds_on_ship=True,
            )
            return f"<verdict>{verdict}</verdict>", "sess-1", 0, ""

        out = io.StringIO()
        with mock.patch.dict(
            flowctl.BACKEND_REGISTRY["codex"], {"run_exec": fake_exec}
        ):
            with contextlib.redirect_stdout(out):
                with contextlib.suppress(SystemExit):
                    handler(args, "codex")
        printed = out.getvalue()
        return json.loads(printed), printed

    def _run_superseded(
        self, handler, args, verdict: str, *, review_kind: str, task_id=None,
        ship_review_type: "str | None" = None,
    ) -> dict:
        """Run a handler whose reservation is superseded mid-dispatch."""
        payload, printed = self._run_with_concurrent_ship(
            handler, args, verdict, review_kind=review_kind, task_id=task_id,
            ship_review_type=ship_review_type or (
                "plan" if review_kind == "plan" else "impl"
            ),
        )
        self.assertTrue(payload["superseded"])
        self.assertTrue(payload["dispatched"])
        self.assertEqual(payload["verdict"], verdict)
        self.assertNotIn("escalate", payload)
        self.assertNotIn(flowctl.NEEDS_HUMAN_ESCALATION_MARKER, printed)
        self.assertNotIn("ESCALATE", printed)
        self.assertEqual(payload["note"], flowctl.SUPERSEDED_REVIEW_NOTICE)
        row = self._data()["review_attempts"][-1]
        self.assertEqual(row["verdict"], verdict)
        self.assertFalse(row["round_consumed"])  # evidence only
        self.assertEqual(payload["superseded_by"], row["superseded_by"])
        return payload

    def test_impl_late_needs_work_is_superseded_not_terminal(self):
        args = argparse.Namespace(
            task=f"{self.spec_id}.1", base="HEAD~1", focus=None, json=True,
            receipt=str(self.root / "impl-receipt.json"), spec=None,
            model=None, effort=None, force=False, sandbox=None,
        )
        payload = self._run_superseded(
            flowctl._backend_impl_review, args, "NEEDS_WORK",
            review_kind="impl", task_id=f"{self.spec_id}.1",
        )
        self.assertEqual(payload["effective_status"], "ship")

    def test_plan_late_needs_human_is_superseded_not_exit_four(self):
        args = argparse.Namespace(
            epic=self.spec_id, base="HEAD~1", json=True, files="app.py",
            receipt=str(self.root / "plan-receipt.json"), spec=None,
            model=None, effort=None, force=False, sandbox=None,
        )
        payload = self._run_superseded(
            flowctl._backend_plan_review, args, "NEEDS_HUMAN",
            review_kind="plan",
        )
        data = self._data()
        # The SHIP's durable terminal is what callers must act on.
        self.assertEqual(data["plan_review_status"], "ship")
        self.assertEqual(payload["effective_status"], "ship")
        self.assertNotIn("plan_review_status", payload)

    def _completion_args(self) -> argparse.Namespace:
        return argparse.Namespace(
            epic=self.spec_id, base="HEAD~1", json=True,
            receipt=str(self.root / "completion-receipt.json"), spec=None,
            model=None, effort=None, force=False, sandbox=None,
        )

    def test_completion_late_needs_work_never_regresses_durable_status(self):
        payload = self._run_superseded(
            flowctl._backend_completion_review, self._completion_args(),
            "NEEDS_WORK", review_kind="plan", ship_review_type="completion",
        )
        data = self._data()
        self.assertEqual(data["completion_review_status"], "ship")
        self.assertEqual(payload["effective_status"], "ship")
        self.assertNotIn("completion_review_status", payload)

    def test_plan_ship_does_not_supersede_a_concurrent_completion_review(self):
        """PR #290 bot r9: plan and completion share the spec counter but are
        different artifacts with different terminal slots. Superseding on the
        counter alone made a real completion NEEDS_WORK surface as
        non-actionable superseded evidence with an effective status of `ship`,
        masking the defect. Only same-typed reservations are superseded."""
        payload, _ = self._run_with_concurrent_ship(
            flowctl._backend_completion_review, self._completion_args(),
            "NEEDS_WORK", review_kind="plan", ship_review_type="plan",
        )
        self.assertNotIn("superseded", payload)
        self.assertNotIn("effective_status", payload)
        self.assertEqual(payload["verdict"], "NEEDS_WORK")
        data = self._data()
        # The plan SHIP owns the plan slot; the completion verdict owns its own.
        self.assertEqual(data["plan_review_status"], "ship")
        self.assertEqual(data["completion_review_status"], "needs_work")
        self.assertEqual(payload["completion_review_status"], "needs_work")
        row = data["review_attempts"][-1]
        self.assertEqual(row["kind"], "completion")
        self.assertTrue(row["round_consumed"])
        self.assertIsNone(row["superseded_by"])

    def test_record_cli_reports_superseded_without_a_terminal_exit(self):
        _, reservation_id = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", review_type="plan", return_reservation=True,
        )
        _, ship_id = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", review_type="plan", return_reservation=True,
        )
        flowctl.record_review_attempt(
            self.spec_id, "plan", backend="rp", output="<verdict>SHIP</verdict>",
            verdict="SHIP", review_type="plan", reservation_id=ship_id,
            status_target="plan", reset_rounds_on_ship=True,
        )
        response = self.root / "late-response.txt"
        response.write_text("<verdict>NEEDS_WORK</verdict>", encoding="utf-8")
        args = argparse.Namespace(
            id=self.spec_id, kind="plan", review_type="plan", backend="rp",
            output_file=str(response), task=None, json=True, force=False,
            reservation_id=reservation_id, exit_code=0, failure_class=None,
            receipt_target=None, receipt_payload_file=None, status_target="plan",
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            flowctl.cmd_review_rounds_record(args)
        payload = json.loads(out.getvalue())
        self.assertTrue(payload["superseded"])
        self.assertEqual(payload["superseded_by"], ship_id)
        self.assertEqual(payload["effective_status"], "ship")
        self.assertEqual(payload["note"], flowctl.SUPERSEDED_REVIEW_NOTICE)
        self.assertEqual(self._data()["plan_review_status"], "ship")

    def test_non_superseded_terminal_contract_is_unchanged(self):
        # The drivers' existing contract must not move for ordinary verdicts.
        args = argparse.Namespace(
            epic=self.spec_id, base="HEAD~1", json=True, files="app.py",
            receipt=str(self.root / "plan-receipt.json"), spec=None,
            model=None, effort=None, force=False, sandbox=None,
        )
        payload, code = self._run(flowctl._backend_plan_review, args)
        self.assertEqual(code, flowctl.REVIEW_CAP_EXIT_CODE)
        self.assertTrue(payload["escalate"])
        self.assertNotIn("superseded", payload)


class TestOverlappingReviewProcesses(_JournalReplayBase):
    """fn-159.1: truly concurrent state transitions under the sidecar lock,
    plus attach-vs-finalize lock-order scaffolding."""

    def test_two_concurrent_increments_yield_distinct_reservations(self):
        env = dict(os.environ)
        env.pop("MAX_REVIEW_ITERATIONS", None)
        argv = [
            sys.executable, str(FLOWCTL_PY), "review-rounds", "increment",
            self.spec_id, "--kind", "plan", "--json",
        ]
        procs = [
            subprocess.Popen(
                argv, cwd=self.root, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            for _ in range(2)
        ]
        outputs = [p.communicate() for p in procs]
        for p, (_out, err) in zip(procs, outputs, strict=True):
            self.assertEqual(p.returncode, 0, err)
        ids = {json.loads(out)["reservation_id"] for out, _ in outputs}
        rounds = {json.loads(out)["round"] for out, _ in outputs}
        self.assertEqual(len(ids), 2)
        self.assertEqual(rounds, {1, 2})  # no lost update under the lock
        data = self._data()
        self.assertEqual(data["plan_review_rounds"], 2)
        self.assertEqual(data["review_pending_rounds"]["plan"], 2)
        self.assertEqual(set(data["review_reservations"]), ids)

    def test_record_racing_reset_stays_consistent(self):
        reserve = self._fresh_process(
            "review-rounds", "increment", self.spec_id, "--kind", "plan",
            "--json",
        )
        self.assertEqual(reserve.returncode, 0, reserve.stderr)
        reservation_id = json.loads(reserve.stdout)["reservation_id"]
        response = self.root / "response.txt"
        response.write_text("<verdict>NEEDS_WORK</verdict>")
        env = dict(os.environ)
        env.pop("MAX_REVIEW_ITERATIONS", None)
        record = subprocess.Popen(
            [
                sys.executable, str(FLOWCTL_PY), "review-rounds", "record",
                self.spec_id, "--kind", "plan", "--review-type", "plan",
                "--output-file", str(response),
                "--reservation-id", reservation_id, "--json",
            ],
            cwd=self.root, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        reset = subprocess.Popen(
            [
                sys.executable, str(FLOWCTL_PY), "spec",
                "reset-review-rounds", self.spec_id, "--json",
            ],
            cwd=self.root, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        record_out = record.communicate()
        reset_out = reset.communicate()
        self.assertEqual(reset.returncode, 0, reset_out[1])
        # The lock serializes the race into one of two legal histories:
        # record-then-reset (row exists) or reset-then-record (the re-plan
        # abandoned the reservation, so record refuses with zero mutation).
        self.assertIn(record.returncode, (0, 2), record_out[1])
        data = self._data()
        rows = [
            row for row in data.get("review_attempts", [])
            if row.get("reservation_id") == reservation_id
        ]
        if record.returncode == 0:
            self.assertEqual(len(rows), 1)
        else:
            self.assertEqual(rows, [])
        # Either way: no stranded reservation, no torn sidecar, epoch
        # advanced by the reset, pending fully drained, counter sane.
        self.assertEqual(data.get("review_reservations", {}), {})
        self.assertGreaterEqual(data["review_hash_epoch"]["plan"], 1)
        self.assertIn(data["plan_review_rounds"], (0, 1))
        self.assertNotIn("plan", data.get("review_pending_rounds", {}))
        self.assertFalse(
            (self.root / ".flow" / "review-runs" / f"{reservation_id}.json").exists()
        )

    @unittest.skipIf(os.name == "nt", "flock holder script is POSIX-only")
    def test_finalize_waits_for_held_receipt_lock_no_deadlock(self):
        """Lock-order scaffolding: a finalize that touches a receipt takes
        the RECEIPT lock BEFORE the SIDECAR lock, so it queues behind an
        attach-style holder of the receipt lock instead of deadlocking."""
        import time

        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        lock_path = flowctl._review_receipt_lock_path(target)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        holder = subprocess.Popen(
            [
                sys.executable, "-c",
                (
                    "import fcntl,sys,time\n"
                    f"fd = open({str(lock_path)!r}, 'a+')\n"
                    "fcntl.flock(fd, fcntl.LOCK_EX)\n"
                    "print('held', flush=True)\n"
                    "time.sleep(1.2)\n"
                ),
            ],
            stdout=subprocess.PIPE, text=True,
        )
        try:
            self.assertEqual(holder.stdout.readline().strip(), "held")
            started = time.monotonic()
            self._record_with_receipt(reservation_id, target)
            elapsed = time.monotonic() - started
        finally:
            holder.wait()
        # The finalize queued behind the holder (receipt lock honored) and
        # then completed — no deadlock, no bypass.
        self.assertGreater(elapsed, 0.8)
        row = self._data()["review_attempts"][-1]
        self.assertEqual(row["reservation_id"], reservation_id)


class TestRpRecorderFailureFences(unittest.TestCase):
    """A recorder failure cannot be hidden by later verdict/control commands."""

    def _stub(self, temp: Path) -> Path:
        path = temp / "flowctl-stub"
        path.write_text(
            "#!/usr/bin/env bash\n"
            "if [[ \"$1 $2\" == \"rp chat-send\" ]]; then\n"
            "  printf '%s\\n' '<verdict>SHIP</verdict>'\n"
            "elif [[ \"$1\" == \"review-artifact\" ]]; then\n"
            "  printf '%s\\n' '{\"artifact_sha256\":\"a\"}'\n"
            "elif [[ \"$1 $2 $3\" == \"review-rounds increment fn-1\" ]]; then\n"
            "  printf '%s\\n' '{\"reservation_id\":\"reservation-test\",\"round\":1,\"cap\":8}'\n"
            "elif [[ \"$1 $2\" == \"review-rounds record\" ]]; then\n"
            "  printf '%s\\n' 'recorder failed'\n"
            "  exit 5\n"
            "else\n"
            "  exit 9\n"
            "fi\n",
            encoding="utf-8",
        )
        path.chmod(0o755)
        return path

    def _run_fence(
        self, relative: str, marker: str, *, task_id: str = ""
    ) -> subprocess.CompletedProcess[str]:
        text = (SKILLS / relative).read_text(encoding="utf-8")
        block = _bash_fence_after(text, marker)
        block = (
            block.replace("<spec-id>", "fn-1")
            .replace("<task-id-or-branch-slug>", "fn-1-1")
            .replace("<suffix>", "test")
        )
        self.assertIn("RECORD_EXIT=$?", block)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            (temp / "flow-plan-review-setup-fn-1-test.env").write_text(
                "RP_MODE=classic W=1 T=classic-tab\n",
                encoding="utf-8",
            )
            (temp / "flow-impl-review-setup-fn-1-1-test.env").write_text(
                "RP_MODE=classic W=1 T=classic-tab\n",
                encoding="utf-8",
            )
            # fn-159.7 review r1: the fences bind their snapshot anchors before
            # hashing and read the dispatch result from disk, so the fixture
            # must supply both (an empty base..head range is legal here).
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=REPO, capture_output=True, text=True, check=True,
            ).stdout.strip()
            (temp / "flow-plan-review-snapshot-fn-1-test.env").write_text(
                f"REVIEW_HEAD_SHA={head}\n", encoding="utf-8",
            )
            (temp / "flow-impl-review-snapshot-fn-1-1-test.env").write_text(
                f"REVIEW_HEAD_SHA={head}\nREVIEW_BASE_SHA={head}\n",
                encoding="utf-8",
            )
            (temp / "flow-impl-review-dispatch-result-fn-1-1-test.env").write_text(
                "RP_EXIT=0\nVERDICT=SHIP\n", encoding="utf-8",
            )
            (temp / "flow-impl-review-reservation-fn-1-1-test.json").write_text(
                '{"reservation_id":"reservation-test"}', encoding="utf-8",
            )
            (temp / "flow-impl-review-response-fn-1-1-test.md").write_text(
                "<verdict>SHIP</verdict>\n", encoding="utf-8",
            )
            env = os.environ.copy()
            env.update(
                {
                    "FLOWCTL": self._stub(temp).as_posix(),
                    "SPEC_ID": "fn-1",
                    "TASK_ID": task_id,
                    "BRANCH": "test-branch",
                    "TMPDIR": temp.as_posix(),
                }
            )
            return subprocess.run(
                [_bash_executable(), "-c", block],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_plan_rp_recorder_failure_stops_the_dispatch_fence(self):
        result = self._run_fence(
            "flow-next-plan-review/workflow-rp.md",
            "Otherwise run one blocking",
        )
        self.assertEqual(
            result.returncode, 5, result.stdout + result.stderr
        )
        self.assertIn("recorder failed", result.stdout)

    def test_impl_rp_recorder_failure_precedes_verdict_echo(self):
        result = self._run_fence(
            "flow-next-impl-review/workflow-rp.md",
            "This is the single recorder fence",
            task_id="fn-1.1",
        )
        self.assertEqual(
            result.returncode, 5, result.stdout + result.stderr
        )
        self.assertIn("recorder failed", result.stdout)
        self.assertNotIn("VERDICT=", result.stdout)

    def test_impl_standalone_review_keeps_no_recorder_path(self):
        result = self._run_fence(
            "flow-next-impl-review/workflow-rp.md",
            "This is the single recorder fence",
        )
        self.assertEqual(
            result.returncode, 0, result.stdout + result.stderr
        )
        self.assertIn("VERDICT=SHIP", result.stdout)


class TestExecutableFenceChain(unittest.TestCase):
    """fn-159.7 review r1: run the real fence chain, not just its prose.

    The prose fences hash a diff produced from snapshot anchors. Unbound
    anchors used to hash an empty blob and falsely refuse round 2, and no test
    executed the chain end to end. This one does: build → increment → record →
    refuse on unchanged → pass after a real edit.
    """

    SPEC_ID = "fn-1-demo"
    TASK_ID = "fn-1-demo.1"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        flow = self.root / ".flow"
        (flow / "specs").mkdir(parents=True)
        (flow / "tasks").mkdir(parents=True)
        (flow / "specs" / f"{self.SPEC_ID}.json").write_text(
            json.dumps({
                "id": self.SPEC_ID, "title": "Demo", "status": "in_progress",
                "tasks": [{"id": self.TASK_ID, "title": "T", "status": "in_progress"}],
            })
        )
        (flow / "specs" / f"{self.SPEC_ID}.md").write_text("# Demo\n")
        (flow / "tasks" / f"{self.TASK_ID}.md").write_text("# T\n")
        self.source = self.root / "app.py"
        self.source.write_text("value = 1\n")
        env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"}
        for argv in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "t@example.com"],
            ["git", "config", "user.name", "T"],
            ["git", "add", "-A"],
            ["git", "commit", "-qm", "base"],
        ):
            subprocess.run(argv, cwd=self.root, check=True, env=env)
        self.base_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.git_env = env

    def tearDown(self):
        self._tmp.cleanup()

    def _flowctl(self, *argv: str) -> "subprocess.CompletedProcess[str]":
        env = dict(os.environ)
        env.pop("MAX_REVIEW_ITERATIONS", None)
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY), *argv],
            cwd=self.root, env=env, capture_output=True, text=True,
        )

    def _build_artifact(self) -> Path:
        """Exactly what the fences do: snapshot → diff → review-artifact."""
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        diff_file = self.root / "dispatch.diff"
        diff = subprocess.run(
            ["git", "diff", f"{self.base_sha}..{head}"], cwd=self.root,
            capture_output=True, text=True, check=True,
        ).stdout
        diff_file.write_text(diff)
        blob = self.root / "artifact.blob"
        built = self._flowctl(
            "review-artifact", "impl", self.SPEC_ID,
            "--diff-file", str(diff_file), "--output", str(blob), "--json",
        )
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        return blob

    def _increment(self, blob: Path) -> "subprocess.CompletedProcess[str]":
        return self._flowctl(
            "review-rounds", "increment", self.SPEC_ID, "--kind", "impl",
            "--task", self.TASK_ID, "--review-type", "impl",
            "--artifact-file", str(blob), "--json",
        )

    def _commit(self, text: str) -> None:
        self.source.write_text(text)
        subprocess.run(
            ["git", "commit", "-qam", "edit"], cwd=self.root, check=True,
            env=self.git_env,
        )

    def test_chain_refuses_unchanged_artifact_and_passes_after_an_edit(self):
        self._commit("value = 2\n")
        blob = self._build_artifact()
        first = self._increment(blob)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        reservation_id = json.loads(first.stdout)["reservation_id"]

        response = self.root / "response.md"
        response.write_text("<verdict>NEEDS_WORK</verdict>\n")
        recorded = self._flowctl(
            "review-rounds", "record", self.SPEC_ID, "--kind", "impl",
            "--task", self.TASK_ID, "--review-type", "impl", "--backend", "rp",
            "--output-file", str(response),
            "--reservation-id", reservation_id, "--json",
        )
        self.assertEqual(recorded.returncode, 0, recorded.stdout + recorded.stderr)

        repeat = self._increment(self._build_artifact())
        self.assertEqual(repeat.returncode, 1, repeat.stdout + repeat.stderr)
        self.assertIn(
            "NOT_RETRYABLE: artifact unchanged since last verdict",
            repeat.stdout + repeat.stderr,
        )

        self._commit("value = 3\n")
        after_fix = self._increment(self._build_artifact())
        self.assertEqual(
            after_fix.returncode, 0, after_fix.stdout + after_fix.stderr
        )
        self.assertIn("reservation_id", json.loads(after_fix.stdout))

    def test_chain_hashes_the_diff_not_an_empty_blob(self):
        """An unbound-anchor fence would hash the same empty diff every round;
        two genuinely different trees must produce different artifacts."""
        self._commit("value = 2\n")
        first = self._build_artifact().read_bytes()
        self._commit("value = 3\n")
        second = self._build_artifact().read_bytes()
        self.assertNotEqual(first, second)
        self.assertIn(b"value = 3", second)


PLAN_REVIEW_FINDING = (
    "## Issue\n"
    "- **Severity**: Major\n"
    "- **Confidence**: 100\n"
    "- **Classification**: introduced\n"
    "- **Location**: Task acceptance\n"
    "- **Problem**: The acceptance is not testable.\n"
    "- **Suggestion**: Add an executable assertion.\n"
    "<verdict>NEEDS_WORK</verdict>\n"
)

COMPLETION_REVIEW_FINDING = (
    "## Issue\n"
    "- **Severity**: Major\n"
    "- **Confidence**: 100\n"
    "- **Classification**: introduced\n"
    "- **Location**: app.py\n"
    "- **Problem**: R1 is not implemented.\n"
    "- **Suggestion**: Implement it.\n"
    "\n"
    "## Global criteria\n"
    "\n"
    "G1: met\n"
    "G2: n/a - no UI\n"
    "\n"
    "<verdict>NEEDS_WORK</verdict>\n"
)


class _InProcessBackendReviewBase(unittest.TestCase):
    """A real git repo + spec sidecar for end-to-end in-process dispatch."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        _init_flow_repo(self.root)
        self.spec_id = "fn-1-demo"
        (self.root / ".flow" / "specs" / f"{self.spec_id}.md").write_text(
            "# Demo\n\n## Acceptance Criteria\n\n- R1: works\n", encoding="utf-8"
        )
        (self.root / ".flow" / "tasks" / f"{self.spec_id}.1.md").write_text(
            "# Task 1\n\nImplement R1.\n", encoding="utf-8"
        )
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        (self.root / "app.py").write_text("x = 1\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", "base")
        (self.root / "app.py").write_text("x = 2\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", "change")
        self._cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self._cwd)
        self._old_env = os.environ.pop("MAX_REVIEW_ITERATIONS", None)
        if self._old_env is not None:
            self.addCleanup(
                os.environ.__setitem__, "MAX_REVIEW_ITERATIONS", self._old_env
            )
        flowctl._wire_backend_review_hooks()

    def _git(self, *argv: str) -> None:
        subprocess.run(
            ["git", *argv], cwd=self.root, check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def _data(self) -> dict:
        return json.loads(
            (self.root / ".flow" / "specs" / f"{self.spec_id}.json").read_text()
        )

    def _plan_args(self, receipt: "Path | None") -> argparse.Namespace:
        return argparse.Namespace(
            epic=self.spec_id, base="HEAD~1", json=True, files="app.py",
            receipt=str(receipt) if receipt else None,
            spec=None, model=None, effort=None, force=False, sandbox=None,
        )

    def _dispatch_plan(
        self, receipt: "Path | None", *, backend: str = "codex",
        review_text: str = PLAN_REVIEW_FINDING,
    ) -> "tuple[dict, str]":
        def fake_exec(_prompt, **_kwargs):
            return review_text, "sess-1", 0, ""

        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(
            flowctl.BACKEND_REGISTRY[backend], {"run_exec": fake_exec}
        ):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                with contextlib.suppress(SystemExit):
                    flowctl._backend_plan_review(self._plan_args(receipt), backend)
        return json.loads(out.getvalue()), err.getvalue()

    def _dispatch_completion(
        self, receipt: "Path | None", *, backend: str = "codex",
        review_text: str = COMPLETION_REVIEW_FINDING,
    ) -> "tuple[dict, str]":
        """Dispatch a completion review whose transport output is a real codex
        JSONL envelope — the criteria/findings parsers can only read the
        EXTRACTED message, which is exactly what a replay no longer has."""
        envelope = json.dumps({
            "type": "item.completed",
            "item": {"type": "agent_message", "text": review_text},
        }) + "\n"

        def fake_exec(_prompt, **_kwargs):
            return envelope, "sess-c1", 0, ""

        args = argparse.Namespace(
            epic=self.spec_id, base="HEAD~1", json=True,
            receipt=str(receipt) if receipt else None,
            spec=None, model=None, effort=None, force=False, sandbox=None,
        )
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(
            flowctl.BACKEND_REGISTRY[backend], {"run_exec": fake_exec}
        ):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                with contextlib.suppress(SystemExit):
                    flowctl._backend_completion_review(args, backend)
        return json.loads(out.getvalue()), err.getvalue()

    def _fresh_process(self, *argv: str) -> "subprocess.CompletedProcess[str]":
        env = dict(os.environ)
        env.pop("MAX_REVIEW_ITERATIONS", None)
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY), *argv],
            cwd=self.root, env=env, capture_output=True, text=True,
        )


class TestInProcessReceiptJournaledPreConsumption(_InProcessBackendReviewBase):
    """PR #290 bot P1: a direct-backend receipt must be journaled BEFORE the
    round is consumed, and published FROM that journal. Otherwise a crash in
    the record→publish gap burns a verdict (with a SHIP counter reset) leaving
    no receipt evidence and nothing for the replay gate to recover."""

    def test_crash_between_record_and_publish_replays_receipt_from_journal(self):
        receipt = self.root / "plan-receipt.json"
        # The induced crash: record journals + consumes, the process dies
        # before publication ever runs.
        with mock.patch.object(
            flowctl, "_publish_review_receipt_from_journal", return_value=False
        ):
            payload, _ = self._dispatch_plan(receipt)
        self.assertEqual(payload["verdict"], "NEEDS_WORK")
        self.assertFalse(receipt.exists())

        data = self._data()
        row = data["review_attempts"][-1]
        reservation_id = row["reservation_id"]
        self.assertTrue(row["round_consumed"])
        # Verdict consumed, receipt evidence still owed — and recoverable.
        self.assertEqual(row["finalized"]["receipt"], "pending")
        journal = json.loads(
            (self.root / ".flow" / "review-runs" / f"{reservation_id}.json")
            .read_text()
        )
        self.assertEqual(journal["receipt_target"], str(receipt))
        self.assertEqual(journal["receipt_payload"]["verdict"], "NEEDS_WORK")
        self.assertIn("findings_container", journal)

        # A FRESH process replays it at the pre-increment gate: zero dispatch.
        replay = self._fresh_process(
            "review-rounds", "increment", self.spec_id, "--kind", "plan",
            "--review-type", "plan", "--json",
        )
        self.assertEqual(replay.returncode, 0, replay.stderr)
        result = json.loads(replay.stdout)
        self.assertTrue(result["replayed"])
        self.assertEqual(
            result["replays"],
            [{"reservation_id": reservation_id, "verdict": "NEEDS_WORK"}],
        )
        published = json.loads(receipt.read_text())
        self.assertEqual(published["verdict"], "NEEDS_WORK")
        self.assertEqual(published["review_reservation_id"], reservation_id)
        self.assertEqual(
            published["review"], journal["receipt_payload"]["review"]
        )
        after = self._data()
        self.assertEqual(after["review_attempts"][-1]["reservation_id"], reservation_id)
        self.assertEqual(after.get("review_pending_rounds", {}), {})
        self.assertEqual(after.get("review_reservations", {}), {})

    def test_normal_run_publishes_from_journal_and_clears_it(self):
        receipt = self.root / "plan-receipt.json"
        payload, _ = self._dispatch_plan(receipt)
        self.assertEqual(payload["verdict"], "NEEDS_WORK")
        row = self._data()["review_attempts"][-1]
        self.assertEqual(row["finalized"]["receipt"], "complete")
        published = json.loads(receipt.read_text())
        self.assertEqual(
            published["review_reservation_id"], row["reservation_id"]
        )
        self.assertFalse(
            (self.root / ".flow" / "review-runs"
             / f"{row['reservation_id']}.json").exists()
        )

    def test_completion_crash_replay_publishes_journaled_criteria_and_container(self):
        """The crashed process bound the criteria and built the findings
        container from the EXTRACTED reviewer message. The journal keeps the
        raw transport envelope, so the replay must pass the journaled evidence
        through — re-deriving from `response` yields nothing and would publish
        a criteria-less receipt with a re-derived (empty) container."""
        (self.root / ".flow" / "criteria.md").write_text(
            "- **G1:** Criterion one.\n- **G2:** Criterion two.\n",
            encoding="utf-8",
        )
        receipt = self.root / "completion-receipt.json"
        # The induced crash is INSIDE record: the journal is written, the
        # reservation is not yet consumed. That is the boundary the
        # pre-increment gate resumes by re-calling record.
        spec_json = self.root / ".flow" / "specs" / f"{self.spec_id}.json"
        real_write = flowctl.atomic_write_json
        armed = []

        def crash_after_journal(path, data, *a, **kw):
            if armed and Path(path) == spec_json:
                raise RuntimeError("induced crash before reservation consumption")
            real_write(path, data, *a, **kw)
            if Path(path).parent.name == "review-runs":
                armed.append(True)

        with mock.patch.object(flowctl, "atomic_write_json", crash_after_journal):
            with self.assertRaises(RuntimeError):
                self._dispatch_completion(receipt)
        self.assertFalse(receipt.exists())

        journals = list((self.root / ".flow" / "review-runs").glob("*.json"))
        self.assertEqual(len(journals), 1)
        journal_path = journals[0]
        journal = json.loads(journal_path.read_text())
        reservation_id = journal["reservation_id"]
        # Reservation still open, no attempt row: the replay branch owns it.
        self.assertIn(reservation_id, self._data().get("review_reservations", {}))
        self.assertEqual(self._data().get("review_attempts", []), [])
        # Pre-condition: the journal holds the envelope, not the message.
        self.assertIn('"item.completed"', journal["response"])
        self.assertIsNone(flowctl.parse_review_criteria(journal["response"]))
        self.assertEqual(
            journal["criteria"],
            [{"id": "G1", "status": "met"}, {"id": "G2", "status": "n/a", "note": "no UI"}],
        )
        journaled_container = journal["findings_container"]
        self.assertIsNotNone(journaled_container)
        self.assertTrue(journaled_container["items"])

        replay = self._fresh_process(
            "review-rounds", "increment", self.spec_id, "--kind", "plan",
            "--review-type", "completion", "--json",
        )
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertTrue(json.loads(replay.stdout)["replayed"])

        published = json.loads(receipt.read_text())
        self.assertEqual(published["criteria"], journal["criteria"])
        self.assertEqual(published["findings"], journaled_container)
        self.assertEqual(published["review_reservation_id"], reservation_id)

    def test_receiptless_run_keeps_receipt_leg_not_applicable(self):
        payload, _ = self._dispatch_plan(None)
        self.assertEqual(payload["verdict"], "NEEDS_WORK")
        row = self._data()["review_attempts"][-1]
        self.assertEqual(row["finalized"]["receipt"], "not_applicable")
        self.assertTrue(row["round_consumed"])
        self.assertEqual(self._data().get("review_pending_rounds", {}), {})


class TestTerminalStatusGatedOnReceiptPublication(_InProcessBackendReviewBase):
    """PR #290 bot r2: the completion handler used to write the terminal
    completion status and delete the recovery payload even when journaled
    receipt publication failed. The next invocation then saw a terminal status
    with no receipt and no payload and exited RETRY in Step 0.5 — BEFORE the
    pre-increment gate that would have replayed the journal. Permanent wedge."""

    def _recovery_path(self) -> Path:
        return (
            self.root / ".flow" / "tmp"
            / f"completion-review-receipt-recovery-{self.spec_id}.json"
        )

    def test_failed_publication_defers_status_and_recovery_cleanup(self):
        receipt = self.root / "completion-receipt.json"
        # Publication fails after the recovery copy lands (the malformed /
        # unwritable-receipt class of failure): the journal's `receipt` leg
        # stays pending.
        with mock.patch.object(
            flowctl, "_complete_review_journal", return_value=False
        ):
            payload, err = self._dispatch_completion(receipt)
        self.assertEqual(payload["verdict"], "NEEDS_WORK")
        self.assertFalse(receipt.exists())

        # Terminal status NOT written; recovery payload intact; leg pending.
        self.assertNotIn("completion_review_status", payload)
        self.assertEqual(
            self._data().get("completion_review_status", "unknown"), "unknown"
        )
        self.assertTrue(self._recovery_path().exists())
        self.assertEqual(
            json.loads(self._recovery_path().read_text())["verdict"], "NEEDS_WORK"
        )
        row = self._data()["review_attempts"][-1]
        reservation_id = row["reservation_id"]
        self.assertEqual(row["finalized"]["receipt"], "pending")
        self.assertIn("replay", err)

        # A FRESH process replays the journal at the pre-increment gate.
        replay = self._fresh_process(
            "review-rounds", "increment", self.spec_id, "--kind", "plan",
            "--review-type", "completion", "--json",
        )
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertTrue(json.loads(replay.stdout)["replayed"])
        published = json.loads(receipt.read_text())
        self.assertEqual(published["verdict"], "NEEDS_WORK")
        self.assertEqual(published["review_reservation_id"], reservation_id)
        self.assertEqual(
            self._data()["review_attempts"][-1]["finalized"]["receipt"], "complete"
        )

        # ...and only THEN does the terminal status land, on real evidence.
        status = self._fresh_process(
            "spec", "set-completion-review-status", self.spec_id,
            "--status", "needs_work", "--json",
        )
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(self._data()["completion_review_status"], "needs_work")

    def test_successful_publication_writes_status_and_clears_recovery(self):
        receipt = self.root / "completion-receipt.json"
        payload, _ = self._dispatch_completion(receipt)
        self.assertEqual(payload["verdict"], "NEEDS_WORK")
        self.assertEqual(payload["completion_review_status"], "needs_work")
        self.assertEqual(self._data()["completion_review_status"], "needs_work")
        self.assertTrue(receipt.exists())
        self.assertFalse(self._recovery_path().exists())

    def _replay_completion(self) -> "subprocess.CompletedProcess[str]":
        return self._fresh_process(
            "review-rounds", "increment", self.spec_id, "--kind", "plan",
            "--review-type", "completion", "--json",
        )

    def _deferred_publication_failure(self) -> "tuple[Path, str]":
        """Dispatch a completion review whose receipt publication fails."""
        receipt = self.root / "completion-receipt.json"
        with mock.patch.object(
            flowctl, "_complete_review_journal", return_value=False
        ):
            payload, _ = self._dispatch_completion(receipt)
        self.assertEqual(payload["verdict"], "NEEDS_WORK")
        self.assertNotIn("completion_review_status", payload)
        row = self._data()["review_attempts"][-1]
        # Both legs owed: the status is journaled PENDING with its target, not
        # folded into the record write and not silently `not_applicable`.
        self.assertEqual(row["finalized"]["receipt"], "pending")
        self.assertEqual(row["finalized"]["status"], "pending")
        journal = json.loads(
            (self.root / ".flow" / "review-runs"
             / f"{row['reservation_id']}.json").read_text()
        )
        self.assertEqual(journal["status_target"], "completion")
        self.assertTrue(self._recovery_path().exists())
        return receipt, row["reservation_id"]

    def test_replay_lands_the_deferred_status_and_cleans_recovery(self):
        """PR #290 bot r3: the replay that publishes the receipt must also
        finish the deferred status leg. Before the fix the finalization
        journaled that leg `not_applicable`, so the gate replayed the verdict,
        deleted the journal, and NOBODY ever wrote completion_review_status or
        removed the recovery payload — the invocation after that hit the
        unchanged-artifact refusal with the spec still non-terminal."""
        receipt, reservation_id = self._deferred_publication_failure()

        replay = self._replay_completion()
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertTrue(json.loads(replay.stdout)["replayed"])

        self.assertEqual(json.loads(receipt.read_text())["verdict"], "NEEDS_WORK")
        data = self._data()
        self.assertEqual(data["completion_review_status"], "needs_work")
        self.assertTrue(data.get("completion_reviewed_at"))
        self.assertFalse(self._recovery_path().exists())
        row = next(
            r for r in data["review_attempts"]
            if r["reservation_id"] == reservation_id
        )
        self.assertEqual(row["finalized"]["receipt"], "complete")
        self.assertEqual(row["finalized"]["status"], "complete")
        self.assertFalse(
            (self.root / ".flow" / "review-runs"
             / f"{reservation_id}.json").exists()
        )

    def test_second_replay_is_a_no_op(self):
        """Replaying an already-statused journal changes nothing."""
        self._deferred_publication_failure()
        self.assertEqual(self._replay_completion().returncode, 0)
        after_first = self._data()

        second = self._replay_completion()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertFalse(json.loads(second.stdout).get("replayed", False))
        after_second = self._data()
        self.assertEqual(
            after_second["completion_review_status"],
            after_first["completion_review_status"],
        )
        self.assertEqual(
            after_second["completion_reviewed_at"],
            after_first["completion_reviewed_at"],
        )
        self.assertFalse(self._recovery_path().exists())

    def test_plan_handler_defers_status_to_publication(self):
        """PR #290 bot r9: the plan handler folded `plan_review_status` (and,
        on SHIP, the counter reset) into finalization while IGNORING the bool
        `_write_backend_review_receipt` returns. That fold was atomic with the
        JOURNAL write, never with publication SUCCESS — a SHIP whose receipt
        failed to publish left a terminal status with no receipt evidence. The
        plan status is now a journaled PENDING leg, exactly like completion."""
        receipt = self.root / "plan-receipt.json"
        with mock.patch.object(
            flowctl, "_complete_review_journal", return_value=False
        ):
            payload, err = self._dispatch_plan(receipt)
        self.assertEqual(payload["verdict"], "NEEDS_WORK")
        self.assertFalse(receipt.exists())
        # No terminal status anywhere until a receipt backs it.
        self.assertNotIn("plan_review_status", payload)
        self.assertEqual(
            self._data().get("plan_review_status", "unknown"), "unknown"
        )
        self.assertIn("replay", err)
        row = self._data()["review_attempts"][-1]
        reservation_id = row["reservation_id"]
        self.assertEqual(row["finalized"]["receipt"], "pending")
        self.assertEqual(row["finalized"]["status"], "pending")
        journal = json.loads(
            (self.root / ".flow" / "review-runs"
             / f"{reservation_id}.json").read_text()
        )
        self.assertEqual(journal["status_target"], "plan")

        # The replay publishes the receipt AND lands the deferred status.
        replay = self._fresh_process(
            "review-rounds", "increment", self.spec_id, "--kind", "plan",
            "--review-type", "plan", "--json",
        )
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertTrue(json.loads(replay.stdout)["replayed"])
        self.assertEqual(json.loads(receipt.read_text())["verdict"], "NEEDS_WORK")
        data = self._data()
        self.assertEqual(data["plan_review_status"], "needs_work")
        self.assertTrue(data.get("plan_reviewed_at"))
        landed = next(
            r for r in data["review_attempts"]
            if r["reservation_id"] == reservation_id
        )
        self.assertEqual(landed["finalized"]["receipt"], "complete")
        self.assertEqual(landed["finalized"]["status"], "complete")
        self.assertFalse(
            (self.root / ".flow" / "review-runs"
             / f"{reservation_id}.json").exists()
        )

    def test_plan_successful_publication_writes_status(self):
        receipt = self.root / "plan-receipt.json"
        payload, _ = self._dispatch_plan(receipt)
        self.assertEqual(payload["plan_review_status"], "needs_work")
        self.assertEqual(self._data()["plan_review_status"], "needs_work")
        self.assertTrue(receipt.exists())

    def test_plan_receiptless_run_still_folds_status(self):
        """No receipt target means nothing to gate on: the fold is correct."""
        payload, _ = self._dispatch_plan(None)
        self.assertEqual(payload["plan_review_status"], "needs_work")
        self.assertEqual(self._data()["plan_review_status"], "needs_work")
        row = self._data()["review_attempts"][-1]
        # Folded into the same atomic sidecar write as the row itself.
        self.assertEqual(row["finalized"]["status"], "complete")


class TestStatusTargetDefersToPublication(_JournalReplayBase):
    """PR #290 bot r4: the RP fences pass `--status-target` to `review-rounds
    record` and publish the receipt afterwards, in a SEPARATE `review-findings
    attach` process. Folding terminal status into the record write therefore
    published it BEFORE the receipt existed: a failed attach left terminal
    status with no valid receipt, which the workflow's Step 0.5 reads as
    'retry' — forever. The status leg must be journaled pending and land with
    the receipt, exactly like the in-process completion handler."""

    def _record_cli(self, reservation_id: str, receipt: Path, **kw) -> dict:
        response = self.root / f"response-{reservation_id}.md"
        response.write_text("<verdict>NEEDS_WORK</verdict>")
        payload_file = self.root / f"payload-{reservation_id}.json"
        payload_file.write_text(
            json.dumps({**self._payload(), "verdict": "NEEDS_WORK"})
        )
        argv = [
            "review-rounds", "record", self.spec_id, "--kind", "plan",
            "--review-type", "plan", "--backend", "rp",
            "--output-file", str(response),
            "--reservation-id", reservation_id,
            "--status-target", "plan", "--exit-code", "0", "--json",
        ]
        if kw.get("with_receipt", True):
            argv += [
                "--receipt-target", str(receipt),
                "--receipt-payload-file", str(payload_file),
            ]
        code, out, err = self._run_cli(*argv)
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def test_status_is_journaled_pending_not_folded(self):
        reservation_id = self._reserve()
        receipt = self.root / "rp-receipt.json"
        result = self._record_cli(reservation_id, receipt)

        self.assertIsNone(result["status_written"])
        self.assertEqual(result["status_deferred"], "plan")
        # Step-0.5-safe: no terminal status until a receipt backs it.
        self.assertEqual(self._data()["plan_review_status"], "unknown")
        self.assertIsNone(self._data()["plan_reviewed_at"])
        journal = json.loads(self._journal_path(reservation_id).read_text())
        self.assertEqual(journal["status_target"], "plan")
        self.assertEqual(journal["finalized"]["status"], "pending")
        self.assertEqual(journal["finalized"]["receipt"], "pending")
        row = self._data()["review_attempts"][-1]
        self.assertEqual(row["finalized"]["status"], "pending")

    def test_attach_publishes_receipt_and_lands_status(self):
        reservation_id = self._reserve()
        receipt = self.root / "rp-receipt.json"
        self._record_cli(reservation_id, receipt)

        code, _, err = self._run_cli(
            "review-findings", "attach", "--reservation-id", reservation_id,
            "--receipt", str(receipt), "--json",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(receipt.read_text())["verdict"], "NEEDS_WORK")
        data = self._data()
        self.assertEqual(data["plan_review_status"], "needs_work")
        self.assertTrue(data["plan_reviewed_at"])
        row = data["review_attempts"][-1]
        self.assertEqual(row["finalized"]["status"], "complete")
        self.assertEqual(row["finalized"]["receipt"], "complete")
        self.assertFalse(self._journal_path(reservation_id).exists())

    def test_failed_attach_leaves_no_terminal_status_and_replay_lands_it(self):
        reservation_id = self._reserve()
        receipt = self.root / "rp-receipt.json"
        self._record_cli(reservation_id, receipt)

        with mock.patch.object(
            flowctl, "_complete_review_journal", return_value=False
        ):
            code, _, _ = self._run_cli(
                "review-findings", "attach", "--reservation-id", reservation_id,
                "--receipt", str(receipt), "--json",
            )
        self.assertEqual(code, 2)
        self.assertFalse(receipt.exists())
        # The fence retries; the gate must NOT see a terminal status with no
        # receipt behind it (the permanent-repeat state).
        self.assertEqual(self._data()["plan_review_status"], "unknown")

        replay = self._fresh_process(
            "review-rounds", "increment", self.spec_id, "--kind", "plan",
            "--review-type", "plan", "--json",
        )
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertTrue(json.loads(replay.stdout)["replayed"])
        self.assertEqual(json.loads(receipt.read_text())["verdict"], "NEEDS_WORK")
        self.assertEqual(self._data()["plan_review_status"], "needs_work")
        self.assertFalse(self._journal_path(reservation_id).exists())

    def test_status_target_without_a_receipt_still_folds(self):
        """Legacy pure-status callers publish nothing, so there is nothing to
        gate on: the fold stays, in the one atomic sidecar write."""
        reservation_id = self._reserve()
        result = self._record_cli(
            reservation_id, self.root / "unused.json", with_receipt=False
        )
        self.assertEqual(result["status_written"], "needs_work")
        self.assertNotIn("status_deferred", result)
        self.assertEqual(self._data()["plan_review_status"], "needs_work")


class TestJournalScanLockGapIsClosed(_InProcessBackendReviewBase):
    """PR #290 bot r3: `_journal_receipt_targets` scans WITHOUT locks so the
    receipt-before-sidecar order can be honored. A finalizer that journals a
    receipt-bearing run in the gap between that scan and the lock acquisition
    used to be published by the replay loop on a lock this pass never held —
    racing a concurrent attach holding the receipt lock while waiting for the
    sidecar lock."""

    def _pending_journal(self) -> "tuple[Path, Path]":
        receipt = self.root / "plan-receipt.json"
        with mock.patch.object(
            flowctl, "_publish_review_receipt_from_journal", return_value=False
        ):
            self._dispatch_plan(receipt)
        reservation_id = self._data()["review_attempts"][-1]["reservation_id"]
        journal_path = (
            self.root / ".flow" / "review-runs" / f"{reservation_id}.json"
        )
        self.assertTrue(journal_path.exists())
        self.assertFalse(receipt.exists())
        return receipt, journal_path

    def _gate(self) -> Any:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(
            io.StringIO()
        ):
            return flowctl.enforce_and_increment_review_cap(
                self.spec_id, "plan", review_type="plan", use_json=True
            )

    def test_journal_never_seen_by_a_scan_is_not_published_unlocked(self):
        receipt, journal_path = self._pending_journal()
        # Every scan misses it (the worst case of the scan/lock gap): its
        # receipt lock is never acquired, so the replay loop must skip it.
        with mock.patch.object(
            flowctl, "_journal_receipt_targets", return_value=[]
        ):
            with self.assertRaises(SystemExit) as ctx:
                self._gate()
        self.assertEqual(ctx.exception.code, 2)
        self.assertFalse(receipt.exists())
        self.assertTrue(journal_path.exists())

        # The next pass sees it, locks it, and publishes it.
        result = self._gate()
        self.assertTrue(result["replayed"])
        self.assertEqual(json.loads(receipt.read_text())["verdict"], "NEEDS_WORK")
        self.assertFalse(journal_path.exists())

    def test_journal_landing_after_the_prelock_scan_is_relocked_then_published(self):
        receipt, journal_path = self._pending_journal()
        real_targets = flowctl._journal_receipt_targets
        real_lock = flowctl.cross_process_lock
        scans: list[int] = []
        locked: list[str] = []

        def hide_from_first_scan(flow_dir, counter_scope):
            scans.append(1)
            if len(scans) == 1:
                # The journal "lands" right after this pre-lock scan.
                return []
            return real_targets(flow_dir, counter_scope)

        def tracking_lock(path, *args, **kwargs):
            locked.append(str(path))
            return real_lock(path, *args, **kwargs)

        with mock.patch.object(
            flowctl, "_journal_receipt_targets", hide_from_first_scan
        ), mock.patch.object(flowctl, "cross_process_lock", tracking_lock):
            result = self._gate()

        # Rescan under the locks found it, so the pass reacquired (receipt
        # before sidecar) instead of publishing on an unheld lock.
        self.assertTrue(result["replayed"])
        self.assertEqual(json.loads(receipt.read_text())["verdict"], "NEEDS_WORK")
        self.assertFalse(journal_path.exists())
        self.assertIn(
            str(flowctl._review_receipt_lock_path(receipt)), locked
        )


class TestUnusableFindingsHistoryDegrades(_InProcessBackendReviewBase):
    """PR #290 bot P1: `_build_backend_review_findings` runs AFTER the paid
    dispatch and BEFORE finalization. A ReviewReceiptHistoryError escaping
    there strands the reservation — round reserved, verdict delivered,
    nothing consumed or refunded."""

    def _archive_foreign_backend_receipt(self, receipt: Path) -> None:
        """Mirror `_clear_stale_review_receipt` on a failed codex attempt."""
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        container = flowctl.build_review_receipt_findings(
            PLAN_REVIEW_FINDING,
            review_type="plan_review",
            review_id=self.spec_id,
            backend="codex",
            head_sha=head,
            anchor_side="head",
        )
        self.assertIsNotNone(container)
        flowctl.atomic_write_json(receipt, {
            "type": "plan_review", "id": self.spec_id, "mode": "codex",
            "verdict": "NEEDS_WORK", "session_id": "s0", "model": "m",
            "spec": "codex", "timestamp": flowctl.now_iso(),
            "review": PLAN_REVIEW_FINDING, "findings": container,
        })
        flowctl._clear_stale_review_receipt(str(receipt))
        self.assertFalse(receipt.exists())
        self.assertTrue(flowctl._review_receipt_history_dir(receipt).exists())

    def test_history_error_raises_without_the_guard(self):
        receipt = self.root / "plan-receipt.json"
        self._archive_foreign_backend_receipt(receipt)
        with self.assertRaises(flowctl.ReviewReceiptHistoryError):
            flowctl.build_review_receipt_findings(
                PLAN_REVIEW_FINDING,
                review_type="plan_review",
                review_id=self.spec_id,
                backend="cursor",
                head_sha="c" * 40,
                prior_receipt_path=receipt,
                anchor_side="head",
            )

    def test_mixed_backend_retry_finalizes_with_lineage_less_container(self):
        receipt = self.root / "plan-receipt.json"
        self._archive_foreign_backend_receipt(receipt)
        payload, stderr = self._dispatch_plan(receipt, backend="cursor")
        self.assertEqual(payload["verdict"], "NEEDS_WORK")
        self.assertIn("review findings history unusable", stderr)

        data = self._data()
        row = data["review_attempts"][-1]
        self.assertEqual(row["backend"], "cursor")
        self.assertTrue(row["round_consumed"])
        self.assertEqual(row["outcome"], "verdict")
        # No strand: the reservation is consumed, nothing left pending.
        self.assertEqual(data.get("review_pending_rounds", {}), {})
        self.assertEqual(data.get("review_reservations", {}), {})
        self.assertEqual(data["plan_review_rounds"], 1)
        published = json.loads(receipt.read_text())
        self.assertEqual(published["mode"], "cursor")
        # Lineage-less: a fresh chain, never a bogus supersession of the
        # foreign-backend generation.
        findings = published.get("findings")
        if findings is not None:
            self.assertEqual(findings["round"], 1)
            self.assertIsNone(findings.get("supersedesReceiptId"))


class TestSupersededJournalNeverRegressesStatus(_JournalReplayBase):
    """PR #290 bot r5 P1: when the receipt on disk is PROVEN newer, the older
    journal's receipt leg is left alone — but its STATUS leg used to run
    anyway, stamping the older verdict onto the single
    ``plan_review_status`` / ``completion_review_status`` slot. The receipt
    then said SHIP while the sidecar said needs_work, decided by nothing but
    journal scan order."""

    def _record_cli(self, reservation_id: str, receipt: Path) -> dict:
        response = self.root / f"response-{reservation_id}.md"
        response.write_text("<verdict>NEEDS_WORK</verdict>")
        payload_file = self.root / f"payload-{reservation_id}.json"
        payload_file.write_text(
            json.dumps({**self._payload(), "verdict": "NEEDS_WORK"})
        )
        code, out, err = self._run_cli(
            "review-rounds", "record", self.spec_id, "--kind", "plan",
            "--review-type", "plan", "--backend", "rp",
            "--output-file", str(response),
            "--reservation-id", reservation_id,
            "--status-target", "plan", "--exit-code", "0", "--json",
            "--receipt-target", str(receipt),
            "--receipt-payload-file", str(payload_file),
        )
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def _publish_newer_round(self, receipt: Path) -> str:
        """A later round finalizes and publishes a SHIP receipt + status."""
        newer_id = "f" * 32
        spec_path = self.root / ".flow" / "specs" / f"{self.spec_id}.json"
        data = json.loads(spec_path.read_text())
        data["review_attempts"].append({
            "timestamp": "9999-01-01T00:00:00Z",
            "scope": "plan", "counter_kind": "plan", "task": None,
            "kind": "plan", "backend": "rp", "outcome": "verdict",
            "verdict": "SHIP", "reservation_id": newer_id,
            "finalized": {
                "receipt": "complete", "digest": "not_applicable",
                "status": "complete",
            },
        })
        data["plan_review_status"] = "ship"
        data["plan_reviewed_at"] = "9999-01-01T00:00:00Z"
        spec_path.write_text(json.dumps(data))
        receipt.write_text(json.dumps({
            **self._payload(), "verdict": "SHIP",
            "review_reservation_id": newer_id,
        }))
        return newer_id

    def test_older_journal_replay_leaves_newer_status_alone(self):
        reservation_id = self._reserve()
        receipt = self.root / "rp-receipt.json"
        self._record_cli(reservation_id, receipt)
        # Deferred, as bot r4 requires: nothing terminal yet.
        self.assertEqual(self._data()["plan_review_status"], "unknown")

        newer = self._publish_newer_round(receipt)
        before = json.loads(receipt.read_text())

        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(isinstance(result, dict) and result["replayed"])

        # Receipt untouched AND the status it states is untouched.
        self.assertEqual(json.loads(receipt.read_text()), before)
        data = self._data()
        self.assertEqual(data["plan_review_status"], "ship")
        self.assertEqual(data["plan_reviewed_at"], "9999-01-01T00:00:00Z")
        # The older journal is finished, not stuck: both legs terminal.
        row = next(
            r for r in data["review_attempts"]
            if r.get("reservation_id") == reservation_id
        )
        self.assertEqual(row["finalized"]["receipt"], "complete")
        self.assertEqual(row["finalized"]["status"], "superseded")
        self.assertFalse(self._journal_path(reservation_id).exists())
        # …and the gate is not wedged behind it.
        self.assertIsInstance(
            flowctl.enforce_and_increment_review_cap(
                self.spec_id, "plan", return_reservation=True
            ),
            tuple,
        )
        self.assertEqual(
            json.loads(receipt.read_text())["review_reservation_id"], newer
        )

    def test_receipt_leg_already_complete_still_supersedes_status(self):
        """The receipt leg can have been completed by an earlier partial
        replay, with a newer round publishing over the stable receipt path
        before this journal's status leg ever ran."""
        reservation_id = self._reserve()
        receipt = self.root / "rp-receipt.json"
        self._record_cli(reservation_id, receipt)
        journal_path = self._journal_path(reservation_id)
        journal = json.loads(journal_path.read_text())
        journal["finalized"]["receipt"] = "complete"
        journal["finalized"]["digest"] = "complete"
        journal_path.write_text(json.dumps(journal))

        self._publish_newer_round(receipt)
        before = json.loads(receipt.read_text())

        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(isinstance(result, dict) and result["replayed"])
        self.assertEqual(json.loads(receipt.read_text()), before)
        self.assertEqual(self._data()["plan_review_status"], "ship")
        self.assertFalse(journal_path.exists())

    def test_unsuperseded_journal_still_lands_its_status(self):
        """The floor stays: with no proven-newer receipt, the delivered
        verdict's status must still be written."""
        reservation_id = self._reserve()
        receipt = self.root / "rp-receipt.json"
        self._record_cli(reservation_id, receipt)
        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(isinstance(result, dict) and result["replayed"])
        data = self._data()
        self.assertEqual(data["plan_review_status"], "needs_work")
        self.assertEqual(
            json.loads(receipt.read_text())["review_reservation_id"],
            reservation_id,
        )


class TestSupersededJournalFinalizesAndCleansUp(_JournalReplayBase):
    """PR #290 bot r7 P1: the d65d60be concurrent-SHIP interleave, carried
    through to journal finalization. A reservation superseded by a concurrent
    SHIP finalizes with ``round_consumed: false`` BY DESIGN, and the digest
    backfill's row matcher demanded a consumed round — so the superseded
    journal's digest leg could never complete, the journal was retained
    forever, and every later dispatch replayed instead of reserving."""

    def test_superseded_journal_completes_and_gate_reopens(self):
        ship_id, late_id = self._reserve(), self._reserve()
        receipt = self.root / "rp-receipt.json"

        # The winner finalizes SHIP: counter -> 0, epoch advances, the
        # outstanding reservation is superseded beneath it.
        flowctl.record_review_attempt(
            self.spec_id, "plan", backend="rp",
            output="<verdict>SHIP</verdict>", verdict="SHIP",
            review_type="plan", reservation_id=ship_id,
            status_target="plan", reset_rounds_on_ship=True,
            receipt_target=str(receipt),
            receipt_payload={**self._payload(), "verdict": "SHIP"},
        )
        published = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(isinstance(published, dict) and published["replayed"])
        ship_receipt = json.loads(receipt.read_text())
        self.assertEqual(ship_receipt["review_reservation_id"], ship_id)
        self.assertEqual(self._data()["plan_review_status"], "ship")
        self.assertEqual(
            self._data()["review_reservations"][late_id]["superseded_by"],
            ship_id,
        )

        # The loser finalizes afterwards, carrying findings: receipt + digest
        # legs journal as pending, no round charged.
        self._record_findings_round(late_id, receipt)
        journal_path = self._journal_path(late_id)
        self.assertTrue(journal_path.exists())
        row = next(
            r for r in self._data()["review_attempts"]
            if r.get("reservation_id") == late_id
        )
        self.assertFalse(row["round_consumed"])
        self.assertEqual(row["superseded_by"], ship_id)

        replay = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", return_reservation=True
        )
        self.assertTrue(isinstance(replay, dict) and replay["replayed"])

        # Both legs terminal, digest backfilled onto the superseded row, and
        # the journal is gone — not retained forever.
        data = self._data()
        row = next(
            r for r in data["review_attempts"]
            if r.get("reservation_id") == late_id
        )
        self.assertEqual(row["finalized"]["receipt"], "complete")
        self.assertEqual(row["finalized"]["digest"], "complete")
        self.assertIsInstance(row.get("findings_digest"), dict)
        self.assertFalse(journal_path.exists())

        # The shipped receipt and status are untouched: publication declined
        # to overwrite the newer receipt.
        self.assertEqual(json.loads(receipt.read_text()), ship_receipt)
        self.assertEqual(data["plan_review_status"], "ship")

        # And the gate is open again — the next dispatch reserves.
        self.assertIsInstance(
            flowctl.enforce_and_increment_review_cap(
                self.spec_id, "plan", return_reservation=True
            ),
            tuple,
        )


class TestSingleLockedCompletionStatusWrite(_InProcessBackendReviewBase):
    """PR #290 bot r5 P1: publication-from-journal completes the deferred
    status leg inside the receipt+sidecar lock, and the completion handler
    then ran ``_self_write_review_status`` as a SECOND, unlocked
    read-modify-write of the same spec JSON. Anything a concurrent
    reserve/finalize landed between that read and its write was overwritten by
    the stale snapshot."""

    def _spec_path(self) -> Path:
        return self.root / ".flow" / "specs" / f"{self.spec_id}.json"

    def test_concurrent_sidecar_mutation_survives_publication(self):
        receipt = self.root / "completion-receipt.json"
        spec_path = self._spec_path()
        published = {"done": False}
        real_publish = flowctl._publish_review_receipt_from_journal
        real_load = flowctl.load_json_or_exit

        def publish(reservation_id, receipt_path, *, result_out=None):
            ok = real_publish(reservation_id, receipt_path, result_out=result_out)
            published["done"] = True
            return ok

        def racing_load(path, what, use_json=True):
            data = real_load(path, what, use_json=use_json)
            if published["done"] and Path(path) == spec_path:
                # Another process finalizes/reserves immediately after this
                # read — ONCE, so a later reader cannot restore it. Any
                # unlocked read-modify-write over this snapshot loses it.
                published["done"] = False
                concurrent = json.loads(spec_path.read_text())
                concurrent["review_pending_rounds"] = {"plan": 1}
                concurrent["concurrent_marker"] = "kept"
                spec_path.write_text(json.dumps(concurrent))
            return data

        with mock.patch.object(
            flowctl, "_publish_review_receipt_from_journal", publish
        ), mock.patch.object(flowctl, "load_json_or_exit", racing_load):
            payload, err = self._dispatch_completion(receipt)

        self.assertEqual(payload["verdict"], "NEEDS_WORK")
        self.assertTrue(receipt.exists())
        data = self._data()
        # The concurrent mutation is intact — no stale snapshot wrote over it.
        self.assertEqual(data.get("concurrent_marker"), "kept")
        self.assertEqual(data.get("review_pending_rounds"), {"plan": 1})
        # …and the status the LOCKED transaction wrote is what's reported.
        self.assertEqual(data["completion_review_status"], "needs_work")
        self.assertEqual(payload["completion_review_status"], "needs_work")

    def test_journaled_path_does_not_self_write_status(self):
        receipt = self.root / "completion-receipt.json"
        with mock.patch.object(
            flowctl, "_self_write_review_status", side_effect=AssertionError(
                "journaled publication owns the status write"
            )
        ):
            payload, _ = self._dispatch_completion(receipt)
        self.assertEqual(payload["completion_review_status"], "needs_work")
        self.assertEqual(self._data()["completion_review_status"], "needs_work")
        row = self._data()["review_attempts"][-1]
        self.assertEqual(row["finalized"]["status"], "complete")

    def test_unjournaled_path_still_self_writes_status(self):
        """No receipt target (no `--receipt`) means no journal owns the
        status: the direct writer must still land it."""
        payload, _ = self._dispatch_completion(None)
        self.assertEqual(payload["completion_review_status"], "needs_work")
        self.assertEqual(self._data()["completion_review_status"], "needs_work")


class TestReviewScopeIsResolvable(unittest.TestCase):
    """fn-169 R3 — every path in `<changed_files>` must resolve to a real file.

    The whole no-embed model rests on this block being the complete, exact scope:
    the reviewer decides what to fetch from it, so a path it cannot resolve is
    evidence it will never read. Two git features abbreviate and both were caught
    the same way — by running the real command over real history rather than a
    synthetic fixture.
    """

    @classmethod
    def setUpClass(cls):
        cls.repo = Path(__file__).resolve().parents[3]

    def _rename_range(self) -> tuple[str, str]:
        """Find a commit in this repo's own history that renamed a file."""
        out = subprocess.run(
            ["git", "log", "--diff-filter=R", "--format=%H", "-1"],
            cwd=self.repo, capture_output=True, text=True, check=True,
        ).stdout.strip()
        if not out:
            self.skipTest("no rename commit in history")
        return f"{out}~1", out

    def test_renames_are_not_abbreviated_to_brace_notation(self):
        """Plain --numstat writes `{old => new}`, naming neither real path."""
        base, head = self._rename_range()
        with mock.patch.object(flowctl, "get_repo_root", return_value=self.repo):
            scope = flowctl._gather_review_scope(base, head)
        self.assertTrue(scope, "no scope gathered for a known rename commit")
        self.assertNotIn("=>", scope, "rename abbreviated — neither path resolves")
        self.assertNotIn("{", scope)

    def test_every_scope_path_exists_at_the_reviewed_head(self):
        """The paths are resolvable, not merely unabbreviated.

        Added paths must exist at head; deleted ones must not. Both are checked
        against git rather than the working tree, so the assertion is about the
        reviewed snapshot the reviewer is told to read.
        """
        base, head = self._rename_range()
        with mock.patch.object(flowctl, "get_repo_root", return_value=self.repo):
            scope = flowctl._gather_review_scope(base, head)
        tracked = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", head],
            cwd=self.repo, capture_output=True, text=True, check=True,
        ).stdout.split("\n")
        at_head = set(tracked)
        checked = 0
        for line in scope.split("\n"):
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            added, _deleted, path = parts
            if added == "0":
                continue  # a pure deletion is correctly absent at head
            self.assertIn(
                path, at_head,
                f"scope names {path!r}, which does not exist at the reviewed "
                "head — the reviewer would be told to read a path it cannot open",
            )
            checked += 1
        self.assertGreater(checked, 0, "no added/modified paths to verify")

    def test_a_wide_diff_lists_every_path_in_full(self):
        """The >50-file case the acceptance criterion names, on real history."""
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        base = None
        for depth in ("~20", "~40", "~80"):
            candidate = f"{head}{depth}"
            names = subprocess.run(
                ["git", "diff", "--name-only", "--no-renames",
                 f"{candidate}..{head}"],
                cwd=self.repo, capture_output=True, text=True,
            )
            if names.returncode == 0 and len(
                [n for n in names.stdout.split("\n") if n]
            ) > 50:
                base = candidate
                break
        if base is None:
            self.skipTest("no >50-file range available in shallow history")
        with mock.patch.object(flowctl, "get_repo_root", return_value=self.repo):
            scope = flowctl._gather_review_scope(base, head)
        expected = {
            n for n in subprocess.run(
                ["git", "diff", "--name-only", "--no-renames", f"{base}..{head}"],
                cwd=self.repo, capture_output=True, text=True, check=True,
            ).stdout.split("\n") if n
        }
        got = {
            line.split("\t")[2] for line in scope.split("\n")
            if len(line.split("\t")) == 3
        }
        self.assertEqual(
            got, expected,
            "scope is not the exact changed-path set on a >50-file diff",
        )
        self.assertNotIn("...", scope, "a path was elided")


class TestEvidenceFailureIsLoud(unittest.TestCase):
    """fn-169 R3 — a failed evidence read must never become an empty review.

    Before fn-169 both git reads returned "" on failure and the prompt embedded a
    diff body alongside, so a swallowed failure degraded the review. Nothing is
    embedded now: the scope map IS the reviewer's evidence and the full diff IS
    the artifact identity, so returning "" would dispatch a paid round with no
    evidence AND leave the artifact-unchanged guard reading "nothing changed" for
    every subsequent round. The distinction under test is failure vs. genuine
    emptiness — collapsing them is the defect.
    """

    def _fake_git(self, *, returncode: int, stdout: str = "", stderr: str = ""):
        def run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd, returncode, stdout=stdout, stderr=stderr
            )
        return run

    def test_failed_scope_read_raises_instead_of_returning_empty(self):
        with mock.patch.object(flowctl, "get_repo_root", return_value=Path(".")), \
                mock.patch.object(
                    flowctl.subprocess, "run",
                    side_effect=self._fake_git(
                        returncode=128,
                        stderr="fatal: bad revision 'deadbee..HEAD'",
                    )):
            with self.assertRaises(flowctl.ReviewEvidenceError) as ctx:
                flowctl._gather_review_scope("deadbee", "HEAD")
        # The operator needs git's own reason, not a generic failure.
        self.assertIn("bad revision", str(ctx.exception))

    def test_failed_identity_read_raises(self):
        with mock.patch.object(flowctl, "get_repo_root", return_value=Path(".")), \
                mock.patch.object(
                    flowctl.subprocess, "run",
                    side_effect=self._fake_git(returncode=1, stderr="boom")):
            with self.assertRaises(flowctl.ReviewEvidenceError):
                flowctl._gather_review_identity_diff("aaa", "bbb")

    def test_oserror_is_also_loud(self):
        with mock.patch.object(flowctl, "get_repo_root", return_value=Path(".")), \
                mock.patch.object(
                    flowctl.subprocess, "run",
                    side_effect=OSError("git not found")):
            with self.assertRaises(flowctl.ReviewEvidenceError):
                flowctl._gather_review_scope("aaa", "bbb")

    def test_a_genuinely_empty_range_is_not_an_error(self):
        """Success with no output stays the caller's judgement, not a failure.

        The two reads take different paths — the scope map is a captured run, the
        artifact identity is streamed under a ceiling — so both are exercised
        through the mechanism each actually uses.
        """
        with mock.patch.object(flowctl, "get_repo_root", return_value=Path(".")), \
                mock.patch.object(
                    flowctl.subprocess, "run",
                    side_effect=self._fake_git(returncode=0, stdout="")):
            self.assertEqual(flowctl._gather_review_scope("aaa", "aaa"), "")
        with mock.patch.object(flowctl, "get_repo_root", return_value=Path(".")), \
                mock.patch.object(
                    flowctl.subprocess, "Popen",
                    side_effect=TestIdentityDiffIsBoundedNeverTruncated()
                    ._fake_popen(b"")):
            self.assertEqual(
                flowctl._gather_review_identity_diff("aaa", "aaa"), ""
            )

    def test_handlers_abort_before_reserving_a_round(self):
        """The abort must precede the reservation, or a round is burned.

        Asserted structurally: in each diff-bearing handler the guarded gather
        appears before the cap enforcement it protects. A reordering that put the
        reservation first would spend a round to discover the evidence is missing.
        """
        source = (Path(__file__).resolve().parents[1]
                  / "scripts" / "flowctl.py").read_text(encoding="utf-8")
        for handler in ("_backend_impl_review", "_backend_completion_review"):
            with self.subTest(handler=handler):
                start = source.index(f"def {handler}(")
                nxt = source.find("\ndef ", start + 1)
                body = source[start:nxt if nxt != -1 else len(source)]
                guard = body.index("except ReviewEvidenceError")
                reserve = body.index("enforce_and_increment_review_cap")
                self.assertLess(
                    guard, reserve,
                    f"{handler} reserves a review round before verifying it can "
                    "read the evidence that review depends on",
                )


class TestIdentityDiffIsBoundedNeverTruncated(unittest.TestCase):
    """fn-169 (impl-review r3) — the identity read has a ceiling, not a budget.

    The pre-fn-169 read was capped at 50 KB because it was EMBEDDED; the identity
    read replaced it and is uncapped in intent, which made it an unbounded read
    whose result is then copied twice by hashing. So it is bounded — and the bound
    RAISES rather than trimming. A truncated identity is strictly worse than none:
    two diffs sharing a prefix would hash identically, and the unchanged-artifact
    guard reads that as "nothing changed", which is the false-SHIP hole this spec
    closed.
    """

    def _fake_popen(self, payload: bytes, *, returncode: int = 0, stderr: bytes = b""):
        class FakePipe:
            def __init__(self, data: bytes):
                self._data = data
                self.pos = 0

            def read(self, n=-1):
                if n is None or n < 0:
                    out, self.pos = self._data[self.pos:], len(self._data)
                    return out
                out = self._data[self.pos:self.pos + n]
                self.pos += len(out)
                return out

            def close(self):
                pass

        class FakeProc:
            """Mirrors the real call shape: stdout is a pipe, stderr is a FILE.

            fn-169 (impl-review r7) moved stderr to a temp file so there is no
            second pipe to deadlock on, so the fake writes the stderr bytes into
            whatever file object the caller passed as ``stderr``.
            """

            def __init__(self, stderr_file):
                self.stdout = FakePipe(payload)
                self.killed = False
                if stderr_file is not None and stderr:
                    stderr_file.write(stderr)

            def kill(self):
                self.killed = True

            def wait(self, timeout=None):
                return -9 if self.killed else returncode

        return lambda *a, **k: FakeProc(k.get("stderr"))

    def test_a_diff_over_the_ceiling_raises_and_names_the_bound(self):
        limit = flowctl.REVIEW_IDENTITY_DIFF_MAX_BYTES
        with mock.patch.object(flowctl, "get_repo_root", return_value=Path(".")), \
                mock.patch.object(
                    flowctl.subprocess, "Popen",
                    side_effect=self._fake_popen(b"x" * (limit + 1))):
            with self.assertRaises(flowctl.ReviewEvidenceError) as ctx:
                flowctl._gather_review_identity_diff("aaa", "bbb")
        message = str(ctx.exception)
        self.assertIn(str(limit), message)
        # The message must explain WHY it refuses rather than trimming.
        self.assertIn("never truncated", message)

    def test_a_large_but_in_bounds_diff_is_returned_whole(self):
        payload = b"d" * 3_000_000
        with mock.patch.object(flowctl, "get_repo_root", return_value=Path(".")), \
                mock.patch.object(
                    flowctl.subprocess, "Popen",
                    side_effect=self._fake_popen(payload)):
            out = flowctl._gather_review_identity_diff("aaa", "bbb")
        self.assertEqual(len(out), len(payload), "an in-bounds diff was shortened")

    def test_nonzero_exit_still_raises_with_gits_reason(self):
        with mock.patch.object(flowctl, "get_repo_root", return_value=Path(".")), \
                mock.patch.object(
                    flowctl.subprocess, "Popen",
                    side_effect=self._fake_popen(
                        b"", returncode=128, stderr=b"fatal: bad object")):
            with self.assertRaises(flowctl.ReviewEvidenceError) as ctx:
                flowctl._gather_review_identity_diff("aaa", "bbb")
        self.assertIn("bad object", str(ctx.exception))

    def test_standalone_reviews_never_read_the_identity_diff(self):
        """No reservation means no consumer; the read would be pure cost.

        Asserted structurally in the handler, because the wasted read is the whole
        point: a standalone branch review has no spec-scoped counter to guard.
        """
        source = (Path(__file__).resolve().parents[1]
                  / "scripts" / "flowctl.py").read_text(encoding="utf-8")
        start = source.index("def _backend_impl_review(")
        body = source[start:source.index("\ndef ", start + 1)]
        self.assertIn('"" if standalone', body)
        self.assertIn("None if standalone", body)


class TestScopePathsSurviveUnusualFilenames(unittest.TestCase):
    """fn-169 R3 (impl-review r5) — the third abbreviation git applies.

    `--stat` elides with an ellipsis, plain `--numstat` collapses renames into
    `{old => new}`, and without `-z` git C-quotes any path outside plain ASCII.
    All three break the same contract: the block claims to be the complete,
    resolvable scope, and a reviewer that cannot open a path cannot review it.
    Exercised over a real git repository, because every one of these was found by
    running the real command rather than by reasoning about it.
    """

    @contextlib.contextmanager
    def _repo_with(self, filename: str):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            run = lambda *a: subprocess.run(  # noqa: E731
                a, cwd=repo, check=True, capture_output=True
            )
            run("git", "init", "-q", ".")
            run("git", "config", "user.email", "t@example.com")
            run("git", "config", "user.name", "t")
            target = repo / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("a\n", encoding="utf-8")
            run("git", "add", "-A")
            run("git", "commit", "-qm", "one")
            target.write_text("a\nb\n", encoding="utf-8")
            run("git", "add", "-A")
            run("git", "commit", "-qm", "two")
            yield repo

    def _scope(self, repo: Path) -> str:
        with mock.patch.object(flowctl, "get_repo_root", return_value=repo):
            return flowctl._gather_review_scope("HEAD~1", "HEAD")

    def test_non_ascii_path_appears_literally(self):
        name = "src/wéird ñame.py"
        with self._repo_with(name) as repo:
            scope = self._scope(repo)
        self.assertIn(name, scope, "path was not emitted literally")
        # git's C-quoting escape for é is \303\251; its presence means -z is gone.
        self.assertNotIn("\\303", scope)
        self.assertFalse(scope.startswith('"'))

    def test_every_scope_path_opens(self):
        """The property, not the encoding: the reviewer can open what it is told."""
        name = "src/ünïcode dir/файл.py"
        with self._repo_with(name) as repo:
            scope = self._scope(repo)
            for line in scope.split("\n"):
                parts = line.split("\t")
                if len(parts) != 3:
                    continue
                self.assertTrue(
                    (repo / parts[2]).exists(),
                    f"scope names {parts[2]!r}, which does not open",
                )

    def test_quotes_in_a_filename_are_not_re_escaped(self):
        # NTFS forbids `"` in a filename outright (Errno 22), so this case is
        # unrepresentable on Windows rather than merely awkward. Probe the real
        # filesystem instead of keying off sys.platform: the constraint belongs to
        # the filesystem, and a POSIX checkout mounted on a Windows runner would
        # fail the same way.
        name = 'src/has"quote.py'
        try:
            with tempfile.TemporaryDirectory() as probe:
                target = Path(probe) / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("x", encoding="utf-8")
        except OSError:
            self.skipTest(f"filesystem rejects {name!r}; nothing to assert here")
        with self._repo_with(name) as repo:
            scope = self._scope(repo)
        self.assertIn(name, scope)
        self.assertNotIn('\\"', scope)

    def test_a_newline_bearing_path_is_flagged_not_silently_split(self):
        """Unrepresentable in a line-oriented block, so it says so.

        A path containing a newline cannot appear literally without reading as two
        entries. Rendering it quoted WITH an explanation is the only honest option;
        emitting it raw would silently corrupt the list.
        """
        raw = "1\t0\tsrc/ok.py\x001\t0\tsrc/we\nird.py\x00"
        rendered = flowctl._render_numstat_z(raw)
        lines = rendered.split("\n")
        self.assertIn("1\t0\tsrc/ok.py", lines)
        self.assertIn("quoted", rendered)
        self.assertIn("newline or tab", rendered)
        # Exactly two records in, exactly two lines out.
        self.assertEqual(len(lines), 2, rendered)

    def test_unexpected_records_are_kept_not_dropped(self):
        """A shorter scope map is the defect; never silently discard a record."""
        rendered = flowctl._render_numstat_z("1\t0\tsrc/a.py\x00weird-record\x00")
        self.assertIn("weird-record", rendered)


class TestEveryCanonicalTaskMustBeVisible(unittest.TestCase):
    """fn-169 R3 (impl-review r5) — a task with no readable spec aborts the review.

    The handlers used to enumerate task specs by globbing `*.md`. A task whose
    markdown was missing was therefore absent from the prompt AND from the artifact
    hash, so a completion review could return SHIP without ever seeing it. That was
    survivable while the specs were embedded — the prompt was merely shorter — but
    the prompt now carries PATHS, so an unresolvable path is an invisible gap in
    the evidence rather than a visible omission.
    """

    @contextlib.contextmanager
    def _flow_repo(self, *, task_ids: list[str], write_markdown_for: list[str]):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            flow = repo / ".flow"
            (flow / "specs").mkdir(parents=True)
            (flow / "tasks").mkdir(parents=True)
            spec_id = "fn-9-demo"
            (flow / "specs" / f"{spec_id}.md").write_text(
                "# Demo\n\n## Acceptance Criteria\n- **R1:** thing\n", encoding="utf-8"
            )
            for task_id in task_ids:
                (flow / "tasks" / f"{task_id}.json").write_text(
                    json.dumps({"id": task_id, "title": "t", "status": "done"}),
                    encoding="utf-8",
                )
                if task_id in write_markdown_for:
                    (flow / "tasks" / f"{task_id}.md").write_text(
                        f"# {task_id}\n", encoding="utf-8"
                    )
            yield repo, flow, spec_id

    def _load(self, flow: Path, spec_id: str):
        with mock.patch.object(flowctl, "get_flow_dir", return_value=flow):
            return flowctl._load_epic_and_task_specs(
                spec_id, use_json=False, missing_label="Epic spec not found"
            )

    def test_all_markdown_present_enumerates_every_task(self):
        ids = ["fn-9-demo.1", "fn-9-demo.2"]
        with self._flow_repo(task_ids=ids, write_markdown_for=ids) as (_r, flow, sid):
            *_rest, task_ids = self._load(flow, sid)
        self.assertEqual(task_ids, ids)

    def test_a_task_without_markdown_aborts_and_names_it(self):
        ids = ["fn-9-demo.1", "fn-9-demo.2"]
        with self._flow_repo(
            task_ids=ids, write_markdown_for=["fn-9-demo.1"]
        ) as (_r, flow, sid):
            err = io.StringIO()
            with contextlib.redirect_stderr(err), \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    self._load(flow, sid)
        self.assertNotEqual(ctx.exception.code, 0)
        message = err.getvalue()
        self.assertIn("fn-9-demo.2.md", message)
        # It must say WHY silence would be worse than failing.
        self.assertIn("silently omit", message)

    def test_the_abort_precedes_any_reservation(self):
        """Structural: the spec load runs before the cap is touched.

        A review that discovers a missing task after reserving a round has already
        spent it, and the round accounting is the thing that bounds cost.
        """
        source = (Path(__file__).resolve().parents[1]
                  / "scripts" / "flowctl.py").read_text(encoding="utf-8")
        for handler in ("_backend_plan_review", "_backend_completion_review"):
            with self.subTest(handler=handler):
                start = source.index(f"def {handler}(")
                body = source[start:source.index("\ndef ", start + 1)]
                self.assertLess(
                    body.index("_load_epic_and_task_specs"),
                    body.index("enforce_and_increment_review_cap"),
                    f"{handler} reserves a round before verifying every task spec "
                    "can be read",
                )




class TestRefundedJournalNeverWedges(_JournalReplayBase):
    """fn-199.4: a refunded (no-verdict) record must never leave a journal
    that cannot complete. Pre-fix, transport-failure journals carried pending
    receipt/digest legs, but receipt publication and the digest backfill are
    verdict-only by design, so the journal wedged every later increment on
    REPLAY_REQUIRED - unrecoverable even via spec reset-review-rounds."""

    def _record_transport_failure(self, reservation_id: str, target: Path) -> dict:
        return flowctl.record_review_attempt(
            self.spec_id,
            "plan",
            backend="host",
            output="reviewer prose that never emits the verdict tag",
            verdict=None,
            review_type="plan",
            reservation_id=reservation_id,
            receipt_target=str(target),
            receipt_payload=self._payload(),
        )

    def test_transport_failure_record_completes_its_own_journal(self):
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        self._record_transport_failure(reservation_id, target)

        # The refund is fully recorded on the attempt row; nothing publishable
        # remains, so the journal is completed and cleaned by record itself.
        self.assertFalse(self._journal_path(reservation_id).exists())
        row = self._data()["review_attempts"][-1]
        self.assertEqual(row["outcome"], "transport_failure")
        self.assertIsNone(row["verdict"])
        self.assertFalse(row["round_consumed"])
        for leg in ("receipt", "digest"):
            self.assertEqual(row["finalized"][leg], "not_applicable")
        # No receipt is published for a refunded round - a receipt asserts a
        # delivered verdict, and none was parsed.
        self.assertFalse(target.exists())

        # The scope is not wedged: the next dispatch reserves cleanly.
        next_reservation = self._reserve()
        self.assertTrue(next_reservation)

    def test_prefix_wedged_refund_journal_self_heals_on_increment(self):
        """A journal written by the pre-fix code (pending legs, no verdict)
        self-heals on the next increment instead of REPLAY_REQUIRED forever."""
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        with mock.patch.object(flowctl, "_cleanup_review_journal"):
            self._record_transport_failure(reservation_id, target)

        journal_path = self._journal_path(reservation_id)
        self.assertTrue(journal_path.exists())
        journal = json.loads(journal_path.read_text())
        # Reconstruct the exact pre-fix wedge: pending receipt/digest legs on a
        # refunded journal, no cleanup marker, and the sidecar row matching.
        journal["finalized"] = {
            "receipt": "pending", "digest": "pending",
            "status": "not_applicable",
        }
        journal.pop("cleanup", None)
        journal_path.write_text(json.dumps(journal))
        spec_path = self.root / ".flow" / "specs" / f"{self.spec_id}.json"
        spec_data = json.loads(spec_path.read_text())
        for row in spec_data["review_attempts"]:
            if row.get("reservation_id") == reservation_id:
                row["finalized"] = {
                    "receipt": "pending", "digest": "pending",
                    "status": "not_applicable",
                }
        spec_path.write_text(json.dumps(spec_data))

        # Pre-fix this raised SystemExit(2) REPLAY_REQUIRED forever. The heal
        # is invisible: the no-verdict journal's pending legs retire, it is
        # completed and cleaned, no phantom replay is reported (a refund has
        # no verdict to replay), and THIS SAME call grants a reservation.
        _, reservation = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", review_type="plan",
            artifact_sha256="b" * 64, return_reservation=True,
        )
        self.assertFalse(journal_path.exists())
        self.assertTrue(reservation)
        row = json.loads(spec_path.read_text())["review_attempts"][0]
        for leg in ("receipt", "digest"):
            self.assertEqual(row["finalized"][leg], "not_applicable")

    def test_crash_resume_of_refund_journal_reports_no_phantom_replay(self):
        """PR #358 bot: crash AFTER the refund journal write but BEFORE the
        reservation is consumed. The crash-resume branch (journal present +
        reservation pending + no attempt row) must apply the same no-verdict
        rule as the completion path: record the refund, but never append it to
        the replay sink - pre-fix the resume returned a phantom
        ``verdict: None`` replay and suppressed the reservation."""
        reservation_id = self._reserve()
        target = self.root / "receipt.json"
        spec_path = self.root / ".flow" / "specs" / f"{self.spec_id}.json"
        # Snapshot the sidecar at the crash boundary: reservation reserved,
        # nothing consumed, no attempt row.
        crash_state = spec_path.read_text()
        with mock.patch.object(flowctl, "_cleanup_review_journal"):
            self._record_transport_failure(reservation_id, target)
        journal_path = self._journal_path(reservation_id)
        self.assertTrue(journal_path.exists())
        # Strip the completion marker so the journal reads exactly as the
        # write-ahead copy did at crash time, and roll the sidecar back to the
        # pre-consumption snapshot.
        journal = json.loads(journal_path.read_text())
        journal.pop("cleanup", None)
        journal_path.write_text(json.dumps(journal))
        spec_path.write_text(crash_state)

        result = flowctl.enforce_and_increment_review_cap(
            self.spec_id, "plan", review_type="plan",
            artifact_sha256="c" * 64, return_reservation=True,
        )
        # No phantom replay: a resumed refund is invisible, and this same
        # call resolves the crash AND grants the next reservation.
        self.assertIsInstance(result, tuple)
        _, reservation = result
        self.assertTrue(reservation)
        self.assertFalse(journal_path.exists())
        data = self._data()
        row = data["review_attempts"][0]
        self.assertEqual(row["reservation_id"], reservation_id)
        self.assertEqual(row["outcome"], "transport_failure")
        self.assertIsNone(row["verdict"])
        self.assertNotIn(reservation_id, data.get("review_reservations", {}))
