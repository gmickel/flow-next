"""Behavioral tests for the two-phase impl-review fan-out (fn-215 Stage C).

Mirrors the in-process CLI harness in test_review_convergence_cap.py
(``_init_flow_repo`` + ``sys.argv`` / ``flowctl.main()``) and the
``mock.patch.dict(BACKEND_REGISTRY[backend], {run_exec: ...})`` stub after
``_wire_backend_review_hooks()``.
"""

from __future__ import annotations

import contextlib
import importlib.util
import inspect
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Any, Callable
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def _load_flowctl() -> Any:
    here = Path(__file__).resolve()
    flowctl_path = here.parent.parent / "scripts" / "flowctl.py"
    spec = importlib.util.spec_from_file_location(
        "flowctl_review_fanout_under_test", flowctl_path
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


def _init_flow_repo(root: Path) -> Path:
    """Create a minimal .flow/ with one spec json (same shape as cap tests)."""
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


def _axis_of(prompt: str) -> str:
    hits = [
        axis
        for axis, line in flowctl.REVIEW_FANOUT_AXIS_LINES.items()
        if line in prompt
    ]
    if len(hits) != 1:
        raise AssertionError(f"expected exactly one axis line, got {hits}")
    return hits[0]


def _merged_review(*problems: str, verdict: str = "NEEDS_WORK") -> str:
    """Minimal merged review: labeled findings + fenced JSON tally (fn-215 R9).

    ``build_review_receipt_findings`` parses the labeled blocks; the fenced
    object is the tally grammar the prompt asks for. ``findings`` on that
    object is coordinator-shaped and ignored by the v1 item allowlist.
    """
    parts: list[str] = []
    for index, problem in enumerate(problems, 1):
        parts.append(
            f"## Issue {index}\n"
            f"- **Severity**: Major\n"
            f"- **Confidence**: 100\n"
            f"- **Classification**: introduced\n"
            f"- **Problem**: {problem}\n"
            f"- **Suggestion**: Fix issue {index}.\n"
        )
    tally = {
        "findings": [
            {
                "severity": "P1",
                "confidence": 100,
                "classification": "introduced",
                "title": problem,
            }
            for problem in problems
        ],
        "classification_counts": {
            "introduced": len(problems),
            "pre_existing": 0,
        },
        "unaddressed": [],
    }
    parts.append("```json\n" + json.dumps(tally, separators=(",", ":")) + "\n```\n")
    parts.append(f"<verdict>{verdict}</verdict>\n")
    return "\n".join(parts)


def _empty_merged_review() -> str:
    """Explicitly-empty findings list (wedge input): same JSON block, zero items."""
    return (
        "No blocking findings. The implementation matches the task.\n\n"
        "```json\n"
        '{"findings":[],"classification_counts":{"introduced":0,"pre_existing":0},'
        '"unaddressed":[]}\n'
        "```\n"
        "<verdict>SHIP</verdict>\n"
    )


def _unparseable_merged_review() -> str:
    """No parseable findings block — parsers distinguish invalid from absent."""
    return (
        "Coordinator notes only; nothing structured to attach.\n"
        "<verdict>NEEDS_WORK</verdict>\n"
    )


class TestReviewFanout(unittest.TestCase):
    """fn-215 Stage C: one focused test per numbered behavior."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        _init_flow_repo(self.root)
        self.spec_id = "fn-1-demo"
        self.task_id = f"{self.spec_id}.1"
        (self.root / ".flow" / "specs" / f"{self.spec_id}.md").write_text(
            "# Demo\n\n## Acceptance Criteria\n\n- R1: works\n", encoding="utf-8"
        )
        (self.root / ".flow" / "tasks" / f"{self.task_id}.md").write_text(
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
        flowctl._MAX_REVIEW_ITERATIONS_CONFIG_MEMO.clear()
        flowctl._wire_backend_review_hooks()

    def _git(self, *argv: str) -> None:
        subprocess.run(
            ["git", *argv],
            cwd=self.root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _spec_data(self) -> dict:
        return json.loads(
            (self.root / ".flow" / "specs" / f"{self.spec_id}.json").read_text()
        )

    def _pending(self) -> int:
        pending = self._spec_data().get("review_pending_rounds") or {}
        return int(pending.get(f"impl:{self.task_id}", 0) or 0)

    def _rounds(self) -> int:
        rounds = self._spec_data().get("impl_review_rounds") or {}
        return int(rounds.get(self.task_id, 0) or 0)

    def _attempts(self) -> list:
        rows = self._spec_data().get("review_attempts") or []
        return [row for row in rows if isinstance(row, dict)]

    def _run(
        self,
        *argv: str,
        fake: Callable | None = None,
        backend: str = "codex",
        extra_patches: tuple = (),
    ) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        code = 0
        patches = []
        if fake is not None:
            patches.append(
                mock.patch.dict(
                    flowctl.BACKEND_REGISTRY[backend], {"run_exec": fake}
                )
            )
        patches.extend(extra_patches)
        with contextlib.ExitStack() as stack:
            for patcher in patches:
                stack.enter_context(patcher)
            with mock.patch.object(sys, "argv", ["flowctl", *argv]):
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    try:
                        flowctl.main()
                    except SystemExit as exc:
                        code = int(exc.code or 0)
        return code, out.getvalue(), err.getvalue()

    def _payload(self, out: str) -> dict:
        data = json.loads(out)
        self.assertIsInstance(data, dict)
        return data

    def _ship_exec(self, calls: list) -> Callable:
        def fake(
            prompt,
            *,
            session_id,
            repo_root,
            spec,
            resolution_out,
            args,
            resume_only=False,
        ):
            axis = _axis_of(prompt)
            resolution_out["model"] = f"{axis}-model"
            calls.append({"prompt": prompt, "session_id": session_id, "axis": axis})
            return "<verdict>SHIP</verdict>", f"sess-{axis}", 0, ""

        return fake

    def _verdict_exec(self, by_axis: dict[str, str], calls: list | None = None) -> Callable:
        def fake(
            prompt,
            *,
            session_id,
            repo_root,
            spec,
            resolution_out,
            args,
            resume_only=False,
        ):
            axis = _axis_of(prompt)
            if calls is not None:
                calls.append({"prompt": prompt, "axis": axis})
            resolution_out["model"] = f"{axis}-model"
            verdict = by_axis[axis]
            return f"<verdict>{verdict}</verdict>", f"sess-{axis}", 0, ""

        return fake

    def _write_merged(self, text: str) -> Path:
        path = self.root / "merged.md"
        path.write_text(text, encoding="utf-8")
        return path

    def _dispatch(self, fake, *extra: str) -> tuple[int, dict, str]:
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            self.task_id,
            "--base",
            "HEAD~1",
            "--force",
            "--json",
            *extra,
            fake=fake,
        )
        payload = self._payload(out) if out.strip() else {}
        return code, payload, err

    def _finalize(self, rid: str, merged: Path, *extra: str) -> tuple[int, dict, str]:
        code, out, err = self._run(
            "codex",
            "impl-review-fanout-finalize",
            self.task_id,
            "--base",
            "HEAD~1",
            "--rid",
            rid,
            "--merged-file",
            str(merged),
            "--json",
            *extra,
        )
        payload = self._payload(out) if out.strip() else {}
        return code, payload, err

    # 1 -----------------------------------------------------------------

    def test_one_reservation_both_phases(self) -> None:
        calls: list = []
        receipt = self.root / "receipt.json"
        code, payload, err = self._dispatch(
            self._ship_exec(calls), "--receipt", str(receipt)
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(len(calls), 3)
        self.assertEqual(self._rounds(), 1)
        self.assertEqual(self._pending(), 1)
        self.assertFalse(self._attempts())
        self.assertFalse(receipt.exists())
        rid = payload["rid"]
        self.assertEqual(payload["reservation_id"], rid)

        code, fin, err = self._finalize(
            rid, self._write_merged(_empty_merged_review()),
            "--receipt", str(receipt),
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(fin.get("verdict"), "SHIP")
        self.assertEqual(self._pending(), 0)
        consumed = [row for row in self._attempts() if row.get("round_consumed")]
        self.assertEqual(len(consumed), 1)
        self.assertTrue(receipt.is_file())
        self.assertEqual(len(calls), 3)

    # 2 -----------------------------------------------------------------

    def test_side_effect_free_draw_runner(self) -> None:
        receipt = self.root / "receipt.json"
        calls: list = []

        def fake(
            prompt,
            *,
            session_id,
            repo_root,
            spec,
            resolution_out,
            args,
            resume_only=False,
        ):
            axis = _axis_of(prompt)
            calls.append(axis)
            if axis == "contracts":
                raise RuntimeError("draw boom")
            resolution_out["model"] = f"{axis}-model"
            return "<verdict>SHIP</verdict>", f"sess-{axis}", 0, ""

        code, payload, err = self._dispatch(fake, "--receipt", str(receipt))
        self.assertEqual(code, 0, err)
        self.assertEqual(sorted(calls), ["contracts", "correctness", "integration"])
        self.assertFalse(receipt.exists())
        self.assertEqual(self._pending(), 1)
        self.assertFalse(self._attempts())
        self.assertEqual(payload.get("failed_draws"), 1)

    # 2b ----------------------------------------------------------------

    def test_draw_system_exit_is_contained(self) -> None:
        """host review r1 P1: error_exit inside a run_exec hook raises
        SystemExit (a BaseException). The draw runner must contain it as a
        failed draw — reservation intact, no attempt row, meta.json written —
        instead of letting it strand the rid with a charged, unrefundable
        round."""

        def fake(
            prompt,
            *,
            session_id,
            repo_root,
            spec,
            resolution_out,
            args,
            resume_only=False,
        ):
            axis = _axis_of(prompt)
            if axis == "integration":
                flowctl.error_exit("hook exploded", use_json=False)
            resolution_out["model"] = f"{axis}-model"
            return "<verdict>SHIP</verdict>", f"sess-{axis}", 0, ""

        code, payload, err = self._dispatch(fake)
        self.assertEqual(code, 0, err)
        self.assertEqual(payload.get("failed_draws"), 1)
        self.assertEqual(self._pending(), 1)
        self.assertFalse(self._attempts())
        meta = json.loads(
            (self.root / ".flow" / "review-fanout" / payload["rid"] / "meta.json")
            .read_text(encoding="utf-8")
        )
        failed = [row for row in meta["draws"] if row.get("failed")]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["axis"], "integration")
        self.assertEqual(failed[0]["failure_class"], "dispatch_exception")
        captured = Path(failed[0]["output_path"]).read_text(encoding="utf-8")
        self.assertIn("SystemExit", captured)

    # 2c ----------------------------------------------------------------

    def test_abandoned_dispatch_refunds_on_next_increment(self) -> None:
        """host review r1 P2: a dispatched-but-never-finalized fan-out must
        not stay a charged round forever. The dispatch writes a refund-intent
        journal; the next increment on the counter replays it as a transport
        failure (round refunded, fresh reservation granted), and the
        abandoned rid's finalize then refuses actionably."""
        calls: list = []
        code, first, err = self._dispatch(self._ship_exec(calls))
        self.assertEqual(code, 0, err)
        self.assertEqual(self._pending(), 1)
        self.assertEqual(self._rounds(), 1)
        journal = (
            self.root / ".flow" / "review-runs" / f"{first['rid']}.json"
        )
        self.assertTrue(journal.is_file(), "dispatch must journal its intent")
        # PR #392 r4 (P1): while the journal is FRESH the fan-out may still be
        # live (coordinator merging) — a concurrent dispatch must be refused,
        # not replay the live reservation as abandoned.
        code, blocked, err = self._dispatch(self._ship_exec(calls))
        self.assertEqual(code, 2, err)
        combined = json.dumps(blocked) + err
        self.assertIn("in flight", combined)
        self.assertEqual(self._pending(), 1)
        self.assertTrue(journal.is_file(), "live journal must survive refusal")
        # Coordinator dies here: no finalize ever lands for first["rid"].
        # Age the journal past the lease so the next increment treats it as
        # the crash it now provably is.
        data = json.loads(journal.read_text(encoding="utf-8"))
        data["timestamp"] = "2020-01-01T00:00:00Z"
        journal.write_text(json.dumps(data), encoding="utf-8")
        # PR #392 sol review: the sidecar's progress.log is the heartbeat —
        # age it too, or the live-lease correctly refuses.
        progress = (
            self.root / ".flow" / "review-fanout" / first["rid"] / "progress.log"
        )
        os.utime(progress, (0, 0))
        code, second, err = self._dispatch(self._ship_exec(calls))
        self.assertEqual(code, 0, err)
        self.assertNotEqual(second["rid"], first["rid"])
        self.assertEqual(self._pending(), 1)
        self.assertEqual(self._rounds(), 1)
        refunds = [
            row for row in self._attempts()
            if row.get("outcome") == "transport_failure"
        ]
        self.assertEqual(len(refunds), 1)
        self.assertEqual(refunds[0].get("failure_class"), "fanout_abandoned")
        self.assertEqual(refunds[0].get("reservation_id"), first["rid"])
        self.assertFalse(journal.exists(), "replayed journal must be cleaned")
        fin_code, fin, fin_err = self._finalize(
            first["rid"], self._write_merged(_empty_merged_review())
        )
        self.assertNotEqual(fin_code, 0)
        # The refund replay left an attempt row for the abandoned reservation,
        # so its late finalize hits the mismatched-duplicate guard.
        self.assertIn(
            "already finalized", (fin.get("error") or "") + fin_err
        )
        # The live dispatch still finalizes normally.
        fin_code, fin, fin_err = self._finalize(
            second["rid"], self._write_merged(_empty_merged_review())
        )
        self.assertEqual(fin_code, 0, fin_err)
        self.assertEqual(fin.get("verdict"), "SHIP")
        self.assertEqual(self._pending(), 0)

    # 3 -----------------------------------------------------------------

    def test_worst_wins(self) -> None:
        cases = [
            (
                {
                    "correctness": "SHIP",
                    "contracts": "NEEDS_WORK",
                    "integration": "SHIP",
                },
                "NEEDS_WORK",
                0,
            ),
            (
                {
                    "correctness": "SHIP",
                    "contracts": "NEEDS_WORK",
                    "integration": "NEEDS_HUMAN",
                },
                "NEEDS_HUMAN",
                flowctl.REVIEW_CAP_EXIT_CODE,
            ),
        ]
        merged = self._write_merged(
            _merged_review("The change mishandles the empty path.")
        )
        for by_axis, expected, exit_code in cases:
            with self.subTest(expected=expected):
                code, payload, err = self._dispatch(self._verdict_exec(by_axis))
                self.assertEqual(code, 0, err)
                fin_code, fin, fin_err = self._finalize(
                    payload["rid"], merged, "--needs-work-survivors", "1",
                )
                self.assertEqual(fin_code, exit_code, fin_err)
                self.assertEqual(fin.get("verdict"), expected)

        # PR #392 sol review: an all-SHIP synthesis stays SHIP even when the
        # coordinator's merged tag says NEEDS_WORK (R9 pure worst-wins; the
        # optional phases run after finalize and own their own transitions)...
        all_ship = {
            "correctness": "SHIP",
            "contracts": "SHIP",
            "integration": "SHIP",
        }
        code, payload, err = self._dispatch(self._verdict_exec(all_ship))
        self.assertEqual(code, 0, err)
        worse = self._write_merged(
            _merged_review("Deep pass found a P0.", verdict="NEEDS_WORK")
        )
        # PR #392 sol review (R9): the merged tag NEVER moves the recorded
        # verdict — pure worst-wins over the draws; the contradiction is
        # stamped instead.
        fin_code, fin, fin_err = self._finalize(payload["rid"], worse)
        self.assertEqual(fin_code, 0, fin_err)
        self.assertEqual(fin.get("verdict"), "SHIP")

        # ...while a milder merged tag never downgrades the synthesis:
        # worst-wins holds across the union, and the receipt stamps the
        # discrepancy so the stored contradiction (recorded NEEDS_WORK, body
        # tag SHIP) is visible rather than reverse-engineered (r2).
        one_bad = dict(all_ship, contracts="NEEDS_WORK")
        receipt = self.root / "milder-receipt.json"
        code, payload, err = self._dispatch(
            self._verdict_exec(one_bad), "--receipt", str(receipt)
        )
        self.assertEqual(code, 0, err)
        milder = self._write_merged(
            _merged_review("Residual finding.", verdict="SHIP")
        )
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], milder, "--receipt", str(receipt),
            "--needs-work-survivors", "1",
        )
        self.assertEqual(fin_code, 0, fin_err)
        self.assertEqual(fin.get("verdict"), "NEEDS_WORK")
        stored = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(stored["verdict"], "NEEDS_WORK")
        mismatch = stored.get("merged_tag_mismatch")
        self.assertIsInstance(mismatch, str)
        self.assertIn("SHIP", mismatch)
        self.assertIn("NEEDS_WORK", mismatch)

    # 4 -----------------------------------------------------------------

    def test_wedge_escalation(self) -> None:
        by_axis = {
            "correctness": "NEEDS_WORK",
            "contracts": "SHIP",
            "integration": "SHIP",
        }
        code, payload, err = self._dispatch(self._verdict_exec(by_axis))
        self.assertEqual(code, 0, err)
        rid = payload["rid"]

        empty = self._write_merged(_empty_merged_review())
        fin_code, fin, fin_err = self._finalize(
            rid, empty, "--needs-work-survivors", "0",
        )
        self.assertEqual(fin_code, flowctl.REVIEW_CAP_EXIT_CODE, fin_err)
        self.assertEqual(fin.get("verdict"), "NEEDS_HUMAN")

        # PR #392 sol review (R3/R14): an unparseable merge on a NEEDS_WORK
        # round is refused — the ratchet needs a valid v1 container.
        code, payload, err = self._dispatch(self._verdict_exec(by_axis))
        self.assertEqual(code, 0, err)
        missing = self._write_merged(_unparseable_merged_review())
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], missing, "--needs-work-survivors", "2",
        )
        self.assertEqual(fin_code, 2, fin_err)
        self.assertIn("did not parse", json.dumps(fin) + fin_err)

    # 4b ----------------------------------------------------------------

    def test_wedge_escalation_per_needs_work_draw(self) -> None:
        """Completion review R9: the wedge is per-NEEDS_WORK-draw.

        SHIP-draw remainder items keep the merged container non-empty while
        every NEEDS_WORK-draw finding was filtered — the coordinator-counted
        ``--needs-work-survivors 0`` escalates anyway; omitting the flag
        keeps the container-count default (compatibility), and an explicit
        nonzero count is authoritative over the container.
        """
        by_axis = {
            "correctness": "NEEDS_WORK",
            "contracts": "SHIP",
            "integration": "SHIP",
        }
        remainder = self._write_merged(
            _merged_review("SHIP-draw remainder item kept as deferred lineage.")
        )

        code, payload, err = self._dispatch(self._verdict_exec(by_axis))
        self.assertEqual(code, 0, err)
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], remainder, "--needs-work-survivors", "0",
        )
        self.assertEqual(fin_code, flowctl.REVIEW_CAP_EXIT_CODE, fin_err)
        self.assertEqual(fin.get("verdict"), "NEEDS_HUMAN")

        # No flag on a NEEDS_WORK round: refused — the container count cannot
        # distinguish NEEDS_WORK-draw survivors from SHIP-draw remainder
        # (PR #392 r7).
        code, payload, err = self._dispatch(self._verdict_exec(by_axis))
        self.assertEqual(code, 0, err)
        fin_code, fin, fin_err = self._finalize(payload["rid"], remainder)
        self.assertEqual(fin_code, 2, fin_err)
        self.assertIn("required", json.dumps(fin) + fin_err)

        # PR #392 sol review: survivors are a SUBSET of the merged items — a
        # count above the container is refused. Same rid: the refused
        # finalize consumed nothing, so the coordinator retries.
        empty = self._write_merged(_empty_merged_review())
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], empty, "--needs-work-survivors", "2",
        )
        self.assertEqual(fin_code, 2, fin_err)
        self.assertIn("exceeds", json.dumps(fin) + fin_err)
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], remainder, "--needs-work-survivors", "1",
        )
        self.assertEqual(fin_code, 0, fin_err)
        self.assertEqual(fin.get("verdict"), "NEEDS_WORK")

    def test_negative_survivors_rejected(self) -> None:
        """A negative --needs-work-survivors is malformed input, not a count:
        it must be refused (exit 2) rather than silently holding NEEDS_WORK
        past the wedge the flag exists to enforce."""
        by_axis = {
            "correctness": "NEEDS_WORK",
            "contracts": "SHIP",
            "integration": "SHIP",
        }
        code, payload, err = self._dispatch(self._verdict_exec(by_axis))
        self.assertEqual(code, 0, err)
        merged = self._write_merged(_merged_review("One finding."))
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], merged, "--needs-work-survivors", "-1",
        )
        self.assertEqual(fin_code, 2, fin_err)
        combined = json.dumps(fin) + fin_err
        self.assertIn("non-negative", combined)

    # 4c ----------------------------------------------------------------

    def test_copilot_secondary_draw_succeeds_with_minted_session(self) -> None:
        """Completion review R5: a cross-family copilot secondary draw gets a
        client-minted UUID session id (copilot composes a session-marker path
        from it — None crashed the draw thread pre-fix) and succeeds."""
        copilot_sessions: list = []

        def copilot_fake(
            prompt,
            *,
            session_id,
            repo_root,
            spec,
            resolution_out,
            args,
            resume_only=False,
        ):
            self.assertEqual(_axis_of(prompt), "contracts")
            copilot_sessions.append(session_id)
            resolution_out["model"] = "copilot-model"
            return "<verdict>SHIP</verdict>", session_id, 0, ""

        codex_calls: list = []
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            self.task_id,
            "--base",
            "HEAD~1",
            "--force",
            "--json",
            "--draw",
            "correctness",
            "--draw",
            "contracts=copilot:gpt-5.2",
            fake=self._ship_exec(codex_calls),
            extra_patches=(
                mock.patch.dict(
                    flowctl.BACKEND_REGISTRY["copilot"],
                    {"run_exec": copilot_fake},
                ),
            ),
        )
        self.assertEqual(code, 0, err)
        payload = self._payload(out)
        self.assertEqual(payload.get("failed_draws"), 0)
        self.assertEqual(len(copilot_sessions), 1)
        # Minted per draw: a real UUID, never None.
        uuid.UUID(copilot_sessions[0])
        # The codex primary draw keeps its no-mint contract (session None).
        self.assertEqual(len(codex_calls), 1)
        self.assertIsNone(codex_calls[0]["session_id"])
        meta = json.loads(
            (self.root / ".flow" / "review-fanout" / payload["rid"] / "meta.json")
            .read_text(encoding="utf-8")
        )
        contracts = [
            row for row in meta["draws"] if row.get("axis") == "contracts"
        ]
        self.assertEqual(len(contracts), 1)
        self.assertEqual(contracts[0]["backend"], "copilot")
        self.assertFalse(contracts[0]["failed"])
        self.assertEqual(contracts[0]["session_id"], copilot_sessions[0])

    # 5 -----------------------------------------------------------------

    def test_partial_fail_open(self) -> None:
        def fake(
            prompt,
            *,
            session_id,
            repo_root,
            spec,
            resolution_out,
            args,
            resume_only=False,
        ):
            axis = _axis_of(prompt)
            if axis == "contracts":
                return "", None, 2, "codex exec timed out (1800s)"
            resolution_out["model"] = f"{axis}-model"
            return "<verdict>SHIP</verdict>", f"sess-{axis}", 0, ""

        receipt = self.root / "receipt.json"
        code, payload, err = self._dispatch(fake, "--receipt", str(receipt))
        self.assertEqual(code, 0, err)
        self.assertEqual(payload.get("failed_draws"), 1)
        meta = json.loads(
            (self.root / ".flow" / "review-fanout" / payload["rid"] / "meta.json")
            .read_text(encoding="utf-8")
        )
        failed = [row for row in meta["draws"] if row.get("failed")]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["axis"], "contracts")
        self.assertEqual(failed[0]["failure_class"], "timeout")
        progress = (
            self.root / ".flow" / "review-fanout" / payload["rid"]
            / "progress.log"
        ).read_text(encoding="utf-8")
        lines = [line for line in progress.splitlines() if line.strip()]
        self.assertEqual(len(lines), 3, progress)
        for axis in flowctl.REVIEW_FANOUT_AXES:
            self.assertTrue(
                any(line.startswith(f"draw {axis}: ") for line in lines),
                progress,
            )
        self.assertTrue(
            any("FAILED (timeout)" in line for line in lines), progress
        )

        fin_code, fin, fin_err = self._finalize(
            payload["rid"],
            self._write_merged(_empty_merged_review()),
            "--receipt",
            str(receipt),
        )
        self.assertEqual(fin_code, 0, fin_err)
        receipt_draws = json.loads(receipt.read_text(encoding="utf-8"))["draws"]
        timed_out = [row for row in receipt_draws if row["axis"] == "contracts"]
        self.assertEqual(len(timed_out), 1)
        self.assertTrue(timed_out[0]["failed"])

    # 6 -----------------------------------------------------------------

    def test_all_fail_single_refund(self) -> None:
        def fake(
            prompt,
            *,
            session_id,
            repo_root,
            spec,
            resolution_out,
            args,
            resume_only=False,
        ):
            return "", None, 0, ""

        pre_rounds = self._rounds()
        code, payload, err = self._dispatch(fake)
        self.assertNotEqual(code, 0)
        self.assertIn("refunded", (payload.get("error") or "") + err)
        self.assertEqual(self._pending(), 0)
        self.assertEqual(self._rounds(), pre_rounds)
        attempts = self._attempts()
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].get("outcome"), "transport_failure")
        metas = list((self.root / ".flow" / "review-fanout").glob("*/meta.json"))
        self.assertEqual(len(metas), 1)

    # 7 -----------------------------------------------------------------

    def test_draws_receipt_schema(self) -> None:
        calls: list = []
        receipt = self.root / "receipt.json"
        code, payload, err = self._dispatch(
            self._ship_exec(calls), "--receipt", str(receipt)
        )
        self.assertEqual(code, 0, err)
        fin_code, fin, fin_err = self._finalize(
            payload["rid"],
            self._write_merged(
                _merged_review("The change mishandles the empty path.")
            ),
            "--receipt",
            str(receipt),
            "--needs-work-survivors",
            "1",
        )
        self.assertEqual(fin_code, 0, fin_err)
        data = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(data["session_id"], "sess-correctness")
        self.assertEqual(data["model"], "correctness-model")
        self.assertIsInstance(data["draws"], list)
        self.assertEqual(len(data["draws"]), 3)
        for row in data["draws"]:
            self.assertEqual(
                set(row),
                {"axis", "model", "session_id", "verdict", "failed"},
            )
        findings = data.get("findings") or {}
        items = findings.get("items") or []
        self.assertTrue(items, "expected parseable merged findings")
        for item in items:
            self.assertNotIn("axis", item)

    # 8 -----------------------------------------------------------------

    def test_round_2_prompt_contains_every_merged_ordinal(self) -> None:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        base = subprocess.run(
            ["git", "rev-parse", "HEAD~1"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        titles = (
            "Alpha unique fanout title one.",
            "Beta unique fanout title two.",
            "Gamma unique fanout title three.",
        )
        merged_text = _merged_review(*titles)
        container = flowctl.build_review_receipt_findings(
            merged_text,
            review_type="impl_review",
            review_id=self.task_id,
            backend="codex",
            head_sha=head,
            base_sha=base,
        )
        self.assertIsNotNone(container)
        items = container["items"]
        self.assertGreaterEqual(len(items), 3)
        receipt = self.root / "receipt.json"
        receipt.write_text(
            json.dumps(
                {
                    "type": "impl_review",
                    "id": self.task_id,
                    "mode": "codex",
                    "verdict": "NEEDS_WORK",
                    "session_id": "sess-primary",
                    "model": "correctness-model",
                    "review": merged_text,
                    "findings": container,
                    "draws": [
                        {
                            "axis": "correctness",
                            "model": "correctness-model",
                            "session_id": "sess-primary",
                            "verdict": "NEEDS_WORK",
                            "failed": False,
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        captured: list[dict] = []

        def fake(
            prompt,
            *,
            session_id,
            repo_root,
            spec,
            resolution_out,
            args,
            resume_only=False,
        ):
            captured.append(
                {
                    "prompt": prompt,
                    "session_id": session_id,
                    "resume_only": resume_only,
                }
            )
            return "<verdict>SHIP</verdict>", session_id or "minted", 0, ""

        code, out, err = self._run(
            "codex",
            "impl-review",
            self.task_id,
            "--base",
            "HEAD~1",
            "--receipt",
            str(receipt),
            "--json",
            fake=fake,
        )
        self.assertEqual(code, 0, err + out)
        self.assertEqual(len(captured), 1, "lean-resume disable is still one dispatch")
        prompt = captured[0]["prompt"]
        self.assertEqual(captured[0]["session_id"], "sess-primary")
        self.assertIn("<prior_findings>", prompt)
        for item in items:
            ordinal = item["ordinal"]
            # Payload render is "{ordinal}. {severity} | … | {title}"; the
            # "Prior finding #N" lines are the reply-grammar examples (1..3).
            self.assertIn(f"Prior finding #{ordinal}", prompt)
            self.assertIn(f"{ordinal}. ", prompt)
            self.assertIn(item["title"], prompt)

    def test_round_state_blocks_receiptless_second_fanout(self) -> None:
        """PR #392 r5 (P1): omitting --receipt must not disable the
        first-round guard — task mode consults the persisted round counter
        (non-zero = a delivered verdict this cycle), --force bypasses as the
        human-authorized re-review it is."""
        by_axis = {
            "correctness": "NEEDS_WORK",
            "contracts": "SHIP",
            "integration": "SHIP",
        }
        code, payload, err = self._dispatch(self._verdict_exec(by_axis))
        self.assertEqual(code, 0, err)
        merged = self._write_merged(_merged_review("One finding."))
        fin_code, _fin, fin_err = self._finalize(
            payload["rid"], merged, "--needs-work-survivors", "1",
        )
        self.assertEqual(fin_code, 0, fin_err)
        self.assertEqual(self._rounds(), 1)
        # No --force, no --receipt: the counter alone must refuse round 2.
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            self.task_id,
            "--base",
            "HEAD~1",
            "--json",
            fake=self._verdict_exec(by_axis),
        )
        self.assertEqual(code, 2, err)
        self.assertIn("first-round only", out + err)

    def test_finalize_refuses_moved_head(self) -> None:
        """PR #392 r5 (P1): a commit landing between dispatch and finalize
        means no draw saw the new head — finalize must refuse rather than
        record a verdict for unreviewed code."""
        code, payload, err = self._dispatch(self._ship_exec([]))
        self.assertEqual(code, 0, err)
        (self.root / "late.txt").write_text("late\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "late.txt"], cwd=self.root, check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-q", "-m", "late commit"], cwd=self.root,
            check=True, capture_output=True,
        )
        merged = self._write_merged(_merged_review("One finding."))
        fin_code, fin, fin_err = self._finalize(payload["rid"], merged)
        self.assertEqual(fin_code, 2, fin_err)
        combined = json.dumps(fin) + fin_err
        # A relative --base spelling moves with the new commit, so either
        # snapshot check may fire first — both are valid stale-round refusals
        # (PR #392 r25 added the merge-base recheck).
        self.assertTrue(
            "no longer matches" in combined or "merge base" in combined,
            combined,
        )
        # PR #392 r19: the provably-stale reservation refunds immediately —
        # no journal-lease wait before the advertised re-dispatch.
        self.assertEqual(self._pending(), 0)
        refunds = [
            row for row in self._attempts()
            if row.get("failure_class") in ("head_moved", "base_moved")
        ]
        self.assertEqual(len(refunds), 1)
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            self.task_id,
            "--base",
            "HEAD~1",
            "--json",
            fake=self._ship_exec([]),
        )
        self.assertEqual(code, 0, err + out[:300])

    def test_finalize_head_recheck_at_record(self) -> None:
        """PR #392 r6 (P1): the head assertion runs again immediately before
        the record mutation — a head that moves AFTER the early meta check
        passed must still refuse."""
        code, payload, err = self._dispatch(self._ship_exec([]))
        self.assertEqual(code, 0, err)
        real = flowctl._resolve_review_sha
        calls = {"n": 0}

        def moving_head(ref):
            value = real(ref)
            if ref == "HEAD":
                calls["n"] += 1
                if calls["n"] > 1:
                    return "f" * 40  # head moves after the early check
            return value

        merged = self._write_merged(_merged_review("One finding."))
        with unittest.mock.patch.object(
            flowctl, "_resolve_review_sha", side_effect=moving_head,
        ):
            fin_code, fin, fin_err = self._finalize(
                payload["rid"], merged, "--needs-work-survivors", "1",
            )
        self.assertGreaterEqual(calls["n"], 2, "record path must recheck")
        self.assertEqual(fin_code, 2, fin_err)
        self.assertIn("no longer matches", json.dumps(fin) + fin_err)

    def test_failed_primary_falls_back_to_surviving_session(self) -> None:
        """PR #392 r16 (P2): a partial fan-out that lost its primary draw
        stamps the receipt from the first surviving codex session instead of
        session_id: null, so round 2 and the optional phases stay runnable;
        draws[] still records the failed primary honestly."""
        def fake(
            prompt, *, session_id, repo_root, spec, resolution_out, args,
            resume_only=False,
        ):
            axis = _axis_of(prompt)
            resolution_out["model"] = f"{axis}-model"
            if axis == "correctness":
                return "no verdict here", None, 1, "boom"
            return "<verdict>SHIP</verdict>", f"sess-{axis}", 0, ""

        receipt = self.root / "pf-receipt.json"
        code, payload, err = self._dispatch(fake, "--receipt", str(receipt))
        self.assertEqual(code, 0, err)
        self.assertEqual(payload["failed_draws"], 1)
        merged = self._write_merged(_empty_merged_review())
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], merged, "--receipt", str(receipt),
        )
        self.assertEqual(fin_code, 0, fin_err)
        data = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertIn(data["session_id"], ("sess-contracts", "sess-integration"))
        by_axis = {row["axis"]: row for row in data["draws"]}
        self.assertTrue(by_axis["correctness"]["failed"])
        self.assertIsNone(by_axis["correctness"]["session_id"])

    def test_traversal_rid_rejected(self) -> None:
        """PR #392 r14 (P2): a dot-segment --rid must not escape the sidecar
        parent — only the 32-hex mint format is accepted."""
        merged = self._write_merged(_merged_review("x"))
        for bad in ("..", "../evil", "AB" * 16, "a" * 31):
            fin_code, fin, fin_err = self._finalize(bad, merged)
            self.assertEqual(fin_code, 2, f"{bad!r}: {fin_err}")
            self.assertIn("invalid --rid", json.dumps(fin) + fin_err)

    def test_task_finalize_replay_is_noop(self) -> None:
        """PR #392 r37 (P1): a task-scoped finalize retried after the round
        was recorded must not rebuild the receipt — optional-phase evidence
        and a phase-overturned verdict survive the replay."""
        receipt = self.root / "replay-receipt.json"
        code, payload, err = self._dispatch(
            self._ship_exec([]), "--receipt", str(receipt)
        )
        self.assertEqual(code, 0, err)
        merged = self._write_merged(_empty_merged_review())
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], merged, "--receipt", str(receipt),
        )
        self.assertEqual(fin_code, 0, fin_err)
        self.assertEqual(fin.get("verdict"), "SHIP")
        # A deep pass enriched and overturned the published receipt.
        data = json.loads(receipt.read_text(encoding="utf-8"))
        data["deep_passes"] = ["adversarial"]
        data["verdict_before_deep"] = "SHIP"
        data["verdict"] = "NEEDS_WORK"
        receipt.write_text(json.dumps(data), encoding="utf-8")
        # Coordinator retries the same finalize (crash recovery).
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], merged, "--receipt", str(receipt),
        )
        self.assertEqual(fin_code, 0, fin_err)
        after = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(after.get("deep_passes"), ["adversarial"])
        self.assertEqual(after.get("verdict"), "NEEDS_WORK")
        # PR #392 r38: the replay EMITS the preserved verdict too — a stale
        # phase-one SHIP here would make the coordinator skip required fixes.
        self.assertEqual(fin.get("verdict"), "NEEDS_WORK")

    def test_standalone_replay_emits_preserved_verdict(self) -> None:
        """PR #392 r40 (P1): a standalone finalize retried for the same rid
        is a no-op that EMITS the preserved (phase-changed) verdict."""
        receipt = self.root / "sa-receipt.json"
        code, out, err = self._run(
            "codex", "impl-review-fanout", "--base", "HEAD~1",
            "--receipt", str(receipt), "--json", fake=self._ship_exec([]),
        )
        self.assertEqual(code, 0, err)
        rid = self._payload(out)["rid"]
        merged = self._write_merged(_empty_merged_review())
        code, out, err = self._run(
            "codex", "impl-review-fanout-finalize", "--base", "HEAD~1",
            "--rid", rid, "--merged-file", str(merged),
            "--receipt", str(receipt), "--json",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(self._payload(out)["verdict"], "SHIP")
        data = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(data.get("rid"), rid)
        data["deep_passes"] = ["adversarial"]
        data["verdict_before_deep"] = "SHIP"
        data["verdict"] = "NEEDS_WORK"
        receipt.write_text(json.dumps(data), encoding="utf-8")
        code, out, err = self._run(
            "codex", "impl-review-fanout-finalize", "--base", "HEAD~1",
            "--rid", rid, "--merged-file", str(merged),
            "--receipt", str(receipt), "--json",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(self._payload(out)["verdict"], "NEEDS_WORK")
        after = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(after.get("deep_passes"), ["adversarial"])

    def test_task_replay_with_lost_receipt_uses_ledger(self) -> None:
        """PR #392 r40 (P1): a task replay whose receipt vanished derives the
        effective verdict from the durable ledger, never the stale SHIP."""
        receipt = self.root / "lost-receipt.json"
        code, payload, err = self._dispatch(
            self._ship_exec([]), "--receipt", str(receipt)
        )
        self.assertEqual(code, 0, err)
        merged = self._write_merged(_empty_merged_review())
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], merged, "--receipt", str(receipt),
        )
        self.assertEqual(fin_code, 0, fin_err)
        # A deep pass durably reopened the cycle, then the receipt was lost.
        spec = self._spec_data()
        spec.setdefault("review_attempts", []).append({
            "counter_kind": "impl", "kind": "impl", "review_type": "impl",
            "task": self.task_id, "backend": "codex", "verdict": "NEEDS_WORK",
            "outcome": "verdict", "round_consumed": False,
            "deep_pass_overturn": True, "reservation_id": None,
        })
        (self.root / ".flow" / "specs" / f"{self.spec_id}.json").write_text(
            json.dumps(spec), encoding="utf-8"
        )
        receipt.unlink()
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], merged, "--receipt", str(receipt),
        )
        self.assertEqual(fin_code, 0, fin_err)
        self.assertEqual(fin.get("verdict"), "NEEDS_WORK")

    def test_task_mode_defaults_receipt_path(self) -> None:
        """PR #392 sol review (R11/R12): task mode always has a receipt — a
        dispatch + finalize without --receipt publishes to the route default."""
        code, payload, err = self._dispatch(self._ship_exec([]))
        self.assertEqual(code, 0, err)
        merged = self._write_merged(_empty_merged_review())
        fin_code, fin, fin_err = self._finalize(payload["rid"], merged)
        self.assertEqual(fin_code, 0, fin_err)
        route = flowctl.compute_review_route(
            self.root / ".flow", self.root, self.task_id,
        )
        self.assertTrue(Path(route["receipt_path"]).is_file(), route["receipt_path"])
        data = json.loads(Path(route["receipt_path"]).read_text(encoding="utf-8"))
        self.assertEqual(data["id"], self.task_id)
        self.assertEqual(data["verdict"], "SHIP")
        Path(route["receipt_path"]).unlink()

    def test_task_mode_refuses_focus(self) -> None:
        code, out, err = self._run(
            "codex", "impl-review-fanout", self.task_id, "--base", "HEAD~1",
            "--focus", "x", "--json", fake=self._ship_exec([]),
        )
        self.assertEqual(code, 2, err)
        self.assertIn("standalone", out + err)

    def test_hold_for_phases_fences_dispatch(self) -> None:
        """PR #392 sol review (R15): finalize --hold-for-phases holds scope
        ownership through the optional phases — a new exclusive dispatch is
        refused until --release-phases."""
        receipt = self.root / "hold-receipt.json"
        code, payload, err = self._dispatch(self._ship_exec([]), "--receipt", str(receipt))
        self.assertEqual(code, 0, err)
        merged = self._write_merged(_empty_merged_review())
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], merged, "--receipt", str(receipt), "--hold-for-phases",
        )
        self.assertEqual(fin_code, 0, fin_err)
        lease = self._spec_data().get("review_phase_leases", {}).get(f"impl:{self.task_id}")
        self.assertIsInstance(lease, dict)
        self.assertEqual(lease.get("rid"), payload["rid"])
        # Fresh artifact so the unchanged-artifact fence is not what refuses.
        (self.root / "app.py").write_text("x = 3\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", "more")
        code, out, err = self._run(
            "codex", "impl-review-fanout", self.task_id, "--base", "HEAD~1",
            "--json", fake=self._ship_exec([]),
        )
        self.assertEqual(code, 2, err)
        self.assertIn("optional review phases are still in flight", out + err)
        code, out, err = self._run(
            "review-route", self.task_id, "--release-phases",
            "--rid", payload["rid"], "--json",
        )
        self.assertEqual(code, 0, err)
        code, out, err = self._run(
            "codex", "impl-review-fanout", self.task_id, "--base", "HEAD~1",
            "--json", fake=self._ship_exec([]),
        )
        self.assertEqual(code, 0, err + out[:200])

    def test_hold_for_phases_is_acquired_before_the_record(self) -> None:
        """codex r42: the lease exists BEFORE the record consumes the
        reservation — a record failure leaves no post-consumption gap."""
        receipt = self.root / "hold2-receipt.json"
        code, payload, err = self._dispatch(self._ship_exec([]), "--receipt", str(receipt))
        self.assertEqual(code, 0, err)
        merged = self._write_merged(_empty_merged_review())
        seen = {}
        real = flowctl.record_review_attempt

        def spy(*a, **k):
            seen["lease_at_record"] = (
                self._spec_data().get("review_phase_leases", {})
                .get(f"impl:{self.task_id}")
            )
            return real(*a, **k)

        with unittest.mock.patch.object(flowctl, "record_review_attempt", side_effect=spy):
            fin_code, fin, fin_err = self._finalize(
                payload["rid"], merged, "--receipt", str(receipt), "--hold-for-phases", "2",
            )
        self.assertEqual(fin_code, 0, fin_err)
        self.assertIsInstance(seen.get("lease_at_record"), dict)
        self.assertEqual(seen["lease_at_record"]["rid"], payload["rid"])
        self.assertEqual(
            seen["lease_at_record"]["ttl_seconds"],
            2 * flowctl.get_review_exec_timeout() + 900,
        )

    def test_exclusive_fence_is_two_way(self) -> None:
        """PR #392 sol review: a plain increment refuses a standing EXCLUSIVE
        reservation (the fan-out / host round), not only the reverse."""
        code, out, err = self._run(
            "review-rounds", "increment", self.spec_id,
            "--kind", "impl", "--task", self.task_id,
            "--review-type", "impl", "--exclusive", "--json",
        )
        self.assertEqual(code, 0, err)
        code, out, err = self._run(
            "review-rounds", "increment", self.spec_id,
            "--kind", "impl", "--task", self.task_id,
            "--review-type", "impl", "--json",
        )
        self.assertEqual(code, 2, err)
        self.assertIn("already reserved", out + err)

    def test_reset_review_rounds_task_scoped(self) -> None:
        """PR #392 sol review: the scoped repair the fences prescribe."""
        code, payload, err = self._dispatch(self._ship_exec([]))
        self.assertEqual(code, 0, err)
        self.assertEqual(self._pending(), 1)
        code, out, err = self._run(
            "spec", "reset-review-rounds", self.spec_id, "--task", "fn-1.1", "--json",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(self._pending(), 0)
        self.assertEqual(self._rounds(), 0)
        journal = self.root / ".flow" / "review-runs" / f"{payload['rid']}.json"
        self.assertFalse(journal.exists())
        self.assertNotIn(payload["rid"], self._spec_data().get("review_reservations", {}))

    def test_long_first_sentence_still_builds_container(self) -> None:
        """PR #392 sol dogfood: a reviewer problem whose first sentence exceeds
        the title limit caps the derived title instead of discarding the
        container (which would now refuse the NEEDS_WORK finalize)."""
        by_axis = {"correctness": "NEEDS_WORK", "contracts": "SHIP", "integration": "SHIP"}
        code, payload, err = self._dispatch(self._verdict_exec(by_axis))
        self.assertEqual(code, 0, err)
        long_problem = "This first sentence is deliberately far longer than the two hundred and forty character title limit so that the derived title would be rejected " * 3
        merged = self._write_merged(_merged_review(long_problem))
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], merged, "--needs-work-survivors", "1",
        )
        self.assertEqual(fin_code, 0, fin_err)
        self.assertEqual(fin.get("verdict"), "NEEDS_WORK")

    def test_every_finalize_requires_a_container(self) -> None:
        """Sol round 2: a malformed merge is refused for ANY verdict (an
        all-clear round says 'No findings.' and parses as a valid empty
        container)."""
        code, payload, err = self._dispatch(self._ship_exec([]))
        self.assertEqual(code, 0, err)
        malformed = self._write_merged("Looks fine to me.\n<verdict>SHIP</verdict>\n")
        fin_code, fin, fin_err = self._finalize(payload["rid"], malformed)
        self.assertEqual(fin_code, 2, fin_err)
        self.assertIn("did not parse", json.dumps(fin) + fin_err)
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], self._write_merged(_empty_merged_review()),
        )
        self.assertEqual(fin_code, 0, fin_err)
        self.assertEqual(fin.get("verdict"), "SHIP")

    def test_aborted_finalize_releases_its_lease(self) -> None:
        """Codex r45: a finalize that acquired the lease and then aborted
        (moved head) releases it — the immediate re-dispatch is not fenced."""
        receipt = self.root / "abort-receipt.json"
        code, payload, err = self._dispatch(self._ship_exec([]), "--receipt", str(receipt))
        self.assertEqual(code, 0, err)
        (self.root / "late.txt").write_text("late\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", "late")
        merged = self._write_merged(_empty_merged_review())
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], merged, "--receipt", str(receipt), "--hold-for-phases",
        )
        self.assertEqual(fin_code, 2, fin_err)
        leases = self._spec_data().get("review_phase_leases", {})
        self.assertNotIn(f"impl:{self.task_id}", leases)

    def test_replay_with_hold_keeps_the_lease(self) -> None:
        """Codex r46: a crashed coordinator re-running its finalize with
        --hold-for-phases keeps the lease for the phases it is about to run."""
        receipt = self.root / "replay-hold.json"
        code, payload, err = self._dispatch(self._ship_exec([]), "--receipt", str(receipt))
        self.assertEqual(code, 0, err)
        merged = self._write_merged(_empty_merged_review())
        for _ in range(2):
            fin_code, fin, fin_err = self._finalize(
                payload["rid"], merged, "--receipt", str(receipt), "--hold-for-phases",
            )
            self.assertEqual(fin_code, 0, fin_err)
            lease = self._spec_data().get("review_phase_leases", {}).get(f"impl:{self.task_id}")
            self.assertIsInstance(lease, dict)
            self.assertEqual(lease.get("rid"), payload["rid"])

    def test_failed_standalone_dispatch_releases_claim(self) -> None:
        """Sol round 5 (R10): all-draws-failed on a standalone dispatch must
        not strand the route's claim — the next route fans out again."""
        receipt = self.root / "claim-receipt.json"
        code, out, err = self._run(
            "review-route", "--receipt", str(receipt), "--rotate-stale", "--json",
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(self._payload(out).get("claimed"))

        def all_fail(prompt, *, session_id, repo_root, spec, resolution_out, args, resume_only=False):
            return "no verdict", None, 1, "boom"

        code, out, err = self._run(
            "codex", "impl-review-fanout", "--base", "HEAD~1",
            "--receipt", str(receipt), "--json", fake=all_fail,
        )
        self.assertEqual(code, 2, err)
        self.assertFalse(receipt.exists(), "claim placeholder must be released")
        code, out, err = self._run(
            "review-route", "--receipt", str(receipt), "--rotate-stale", "--json",
        )
        self.assertEqual(self._payload(out)["action"], "fanout")

    def test_claim_release_is_ownership_bound(self) -> None:
        """Sol round 6: cleanup unlinks only the claim the dispatch started
        under — a replacement claim (or receipt) at the same path survives."""
        receipt = self.root / "claim3-receipt.json"
        code, out, err = self._run(
            "review-route", "--receipt", str(receipt), "--rotate-stale", "--json",
        )
        self.assertEqual(code, 0, err)
        token = self._payload(out)["claim_token"]
        self.assertTrue(token)

        def all_fail_after_replace(prompt, *, session_id, repo_root, spec, resolution_out, args, resume_only=False):
            data = json.loads(receipt.read_text(encoding="utf-8"))
            data["claim"]["token"] = "someone-else"
            receipt.write_text(json.dumps(data), encoding="utf-8")
            return "no verdict", None, 1, "boom"

        code, out, err = self._run(
            "codex", "impl-review-fanout", "--base", "HEAD~1",
            "--receipt", str(receipt), "--json", fake=all_fail_after_replace,
        )
        self.assertEqual(code, 2, err)
        self.assertTrue(receipt.exists(), "a replacement claim must survive")
        self.assertEqual(
            json.loads(receipt.read_text(encoding="utf-8"))["claim"]["token"], "someone-else",
        )

    def test_needs_human_finalize_holds_no_lease(self) -> None:
        """Codex r49: NEEDS_HUMAN is terminal — no optional phase follows, so
        --hold-for-phases must not leave a lease fencing the scope."""
        by_axis = {
            "correctness": "SHIP",
            "contracts": "NEEDS_WORK",
            "integration": "NEEDS_HUMAN",
        }
        code, payload, err = self._dispatch(self._verdict_exec(by_axis))
        self.assertEqual(code, 0, err)
        merged = self._write_merged(
            _merged_review("The change mishandles the empty path.")
        )
        fin_code, fin, fin_err = self._finalize(
            payload["rid"], merged, "--needs-work-survivors", "1",
            "--hold-for-phases", "2",
        )
        self.assertEqual(fin_code, flowctl.REVIEW_CAP_EXIT_CODE, fin_err)
        leases = self._spec_data().get("review_phase_leases", {})
        self.assertNotIn(f"impl:{self.task_id}", leases)

    def test_standalone_finalize_is_fenced_on_claim_ownership(self) -> None:
        """Codex r49: a standalone finalize whose claim was rotated and
        re-claimed by another coordinator refuses to publish over it."""
        receipt = self.root / "claim4-receipt.json"
        code, out, err = self._run(
            "review-route", "--receipt", str(receipt), "--rotate-stale", "--json",
        )
        self.assertEqual(code, 0, err)
        code, out, err = self._run(
            "codex", "impl-review-fanout", "--base", "HEAD~1",
            "--receipt", str(receipt), "--json", fake=self._ship_exec([]),
        )
        self.assertEqual(code, 0, err)
        rid = self._payload(out)["rid"]
        data = json.loads(receipt.read_text(encoding="utf-8"))
        data["claim"]["token"] = "someone-else"
        receipt.write_text(json.dumps(data), encoding="utf-8")
        merged = self._write_merged(_empty_merged_review())
        code, out, err = self._run(
            "codex", "impl-review-fanout-finalize", "--base", "HEAD~1",
            "--rid", rid, "--merged-file", str(merged), "--receipt", str(receipt), "--json",
        )
        self.assertEqual(code, 2, err)
        self.assertIn("no longer owned", err + out)
        self.assertEqual(
            json.loads(receipt.read_text(encoding="utf-8"))["claim"]["token"], "someone-else",
        )

    def test_stale_standalone_finalize_releases_claim(self) -> None:
        """A moved-head refusal kills the standalone round — its claim goes."""
        receipt = self.root / "claim2-receipt.json"
        code, out, err = self._run(
            "review-route", "--receipt", str(receipt), "--rotate-stale", "--json",
        )
        self.assertEqual(code, 0, err)
        code, out, err = self._run(
            "codex", "impl-review-fanout", "--base", "HEAD~1",
            "--receipt", str(receipt), "--json", fake=self._ship_exec([]),
        )
        self.assertEqual(code, 0, err)
        rid = self._payload(out)["rid"]
        (self.root / "late.txt").write_text("late\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", "late")
        merged = self._write_merged(_empty_merged_review())
        code, out, err = self._run(
            "codex", "impl-review-fanout-finalize", "--base", "HEAD~1",
            "--rid", rid, "--merged-file", str(merged), "--receipt", str(receipt), "--json",
        )
        self.assertEqual(code, 2, err)
        self.assertFalse(receipt.exists())

    def test_exclusive_increment_refuses_standing_reservation(self) -> None:
        """PR #392 r22: --exclusive makes the single-dispatch fence atomic —
        inside the reservation lock, a standing same-scope reservation
        refuses; the default keeps the multi-pending model."""
        code, out, err = self._run(
            "review-rounds", "increment", self.spec_id,
            "--kind", "impl", "--task", self.task_id,
            "--review-type", "impl", "--json",
        )
        self.assertEqual(code, 0, err)
        code, out, err = self._run(
            "review-rounds", "increment", self.spec_id,
            "--kind", "impl", "--task", self.task_id,
            "--review-type", "impl", "--exclusive", "--json",
        )
        self.assertEqual(code, 2, err)
        self.assertIn("already reserved", out + err)
        # Default (non-exclusive) still permits the multi-pending model.
        code, out, err = self._run(
            "review-rounds", "increment", self.spec_id,
            "--kind", "impl", "--task", self.task_id,
            "--review-type", "impl", "--json",
        )
        self.assertEqual(code, 0, err)

    def test_unjournaled_reservation_blocks_dispatch(self) -> None:
        """PR #392 r21 (P2): a reservation with no journal (owner died between
        the cap commit and the intent write) must block a new dispatch with
        explicit repair guidance, never stack a second reservation."""
        code, payload, err = self._dispatch(self._ship_exec([]))
        self.assertEqual(code, 0, err)
        journal = (
            self.root / ".flow" / "review-runs" / f"{payload['rid']}.json"
        )
        self.assertTrue(journal.is_file())
        journal.unlink()  # the crashed-before-journal state
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            self.task_id,
            "--base",
            "HEAD~1",
            "--json",
            fake=self._ship_exec([]),
        )
        self.assertEqual(code, 2, err)
        self.assertIn("has no journal", out + err)
        self.assertIn("reset-review-rounds", out + err)

    def test_closed_receipt_permits_fresh_fanout(self) -> None:
        """PR #392 r13 (P2): a CLOSED receipt (SHIP) at --receipt is a
        completed earlier scope — flowctl's guard itself must admit the
        fresh fan-out without manual receipt surgery; an OPEN receipt still
        refuses."""
        receipt = self.root / "closed-receipt.json"
        base = {
            "type": "impl_review",
            "id": self.task_id,
            "mode": "codex",
            "model": "gpt-5.2",
            "session_id": "sess-old",
            "review": "Prior round text.",
            "timestamp": "2026-01-01T00:00:00Z",
        }
        receipt.write_text(
            json.dumps(dict(base, verdict="SHIP")), encoding="utf-8",
        )
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            self.task_id,
            "--base",
            "HEAD~1",
            "--receipt",
            str(receipt),
            "--json",
            fake=self._ship_exec([]),
        )
        self.assertEqual(code, 0, err + out[:300])

        receipt.write_text(
            json.dumps(dict(base, verdict="NEEDS_WORK")), encoding="utf-8",
        )
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            self.task_id,
            "--base",
            "HEAD~1",
            "--receipt",
            str(receipt),
            "--json",
            fake=self._ship_exec([]),
        )
        self.assertEqual(code, 2, err)
        self.assertIn("first-round only", out + err)

    def test_major_rethink_permits_fresh_fanout(self) -> None:
        """PR #392 r9 (P1): MAJOR_RETHINK is a completed terminal, not an
        active fix loop — after rework (new artifact) a fresh unforced
        fan-out must be admitted; only open verdicts refuse."""
        by_axis = {
            "correctness": "MAJOR_RETHINK",
            "contracts": "SHIP",
            "integration": "SHIP",
        }
        code, payload, err = self._dispatch(self._verdict_exec(by_axis))
        self.assertEqual(code, 0, err)
        merged = self._write_merged(
            _merged_review("Design conflict.", verdict="MAJOR_RETHINK")
        )
        fin_code, fin, fin_err = self._finalize(payload["rid"], merged)
        self.assertEqual(fin.get("verdict"), "MAJOR_RETHINK", fin_err)
        # Rework lands as a new commit (changed artifact).
        (self.root / "app.py").write_text("x = 3\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", "rework")
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            self.task_id,
            "--base",
            "HEAD~1",
            "--json",
            fake=self._ship_exec([]),
        )
        self.assertEqual(code, 0, err + out[:300])

    def test_meta_publish_failure_refunds(self) -> None:
        """PR #392 r9 (P2): an aggregate meta.json publication failure drives
        the all-failed single-refund path instead of escaping with the
        reservation charged behind the journal lease."""
        real = flowctl._review_fanout_publish

        def flaky(path, text):
            if Path(path).name == "meta.json":
                raise OSError("disk full")
            return real(path, text)

        with unittest.mock.patch.object(
            flowctl, "_review_fanout_publish", side_effect=flaky,
        ):
            code, payload, err = self._dispatch(self._ship_exec([]))
        self.assertEqual(code, 2, err)
        self.assertEqual(self._pending(), 0, "reservation must be refunded")
        refunds = [
            row for row in self._attempts()
            if row.get("outcome") == "transport_failure"
        ]
        self.assertEqual(len(refunds), 1)
        self.assertEqual(
            refunds[0].get("failure_class"), "sidecar_publish_failed",
        )

    def test_symlinked_sidecar_parent_refused(self) -> None:
        """PR #392 r8 (P2): a symlinked .flow/review-fanout would land raw
        reviewer output outside the repository — refuse, never follow."""
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: outside.rmdir() if not any(outside.iterdir()) else None)
        (self.root / ".flow" / "review-fanout").symlink_to(outside)
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            "--base",
            "HEAD~1",
            "--json",
            fake=self._ship_exec([]),
        )
        self.assertEqual(code, 2, err)
        self.assertIn("symlink", out + err)
        self.assertFalse(any(outside.iterdir()), "nothing may cross the link")

    def test_publish_failure_contained_as_failed_draw(self) -> None:
        """PR #392 r8 (P2): a sidecar publication failure is a failed draw,
        not an aggregate-killing exception — siblings still finalize."""
        real = flowctl._review_fanout_publish

        def flaky(path, text):
            if Path(path).name.startswith("contracts"):
                raise OSError("disk full")
            return real(path, text)

        with unittest.mock.patch.object(
            flowctl, "_review_fanout_publish", side_effect=flaky,
        ):
            code, payload, err = self._dispatch(self._ship_exec([]))
        self.assertEqual(code, 0, err)
        self.assertEqual(payload["failed_draws"], 1)
        by_axis = {row["axis"]: row for row in payload["draws"]}
        self.assertTrue(by_axis["contracts"]["failed"])
        self.assertEqual(
            by_axis["contracts"]["failure_class"], "sidecar_publish_failed",
        )
        self.assertEqual(by_axis["correctness"]["verdict"], "SHIP")
        sidecar = self.root / ".flow" / "review-fanout" / payload["rid"]
        self.assertTrue((sidecar / "meta.json").is_file())

    def test_standalone_sidecar_reconciles_gitignore(self) -> None:
        """PR #392 r4 (P2): standalone fan-outs reserve no round and so never
        pass the review-lock gitignore reconcile — sidecar creation itself
        must restore the managed review-fanout/ pattern in old repos."""
        gi = self.root / ".flow" / ".gitignore"
        if gi.is_file():
            stripped = "\n".join(
                line for line in gi.read_text(encoding="utf-8").splitlines()
                if "review-fanout" not in line
            ) + "\n"
            gi.write_text(stripped, encoding="utf-8")
        # (the fixture repo has no .flow/.gitignore at all — the oldest shape)
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            "--base",
            "HEAD~1",
            "--json",
            fake=self._ship_exec([]),
        )
        self.assertEqual(code, 0, err)
        self.assertIn("review-fanout/", gi.read_text(encoding="utf-8"))

    def test_standalone_focus_round_trip(self) -> None:
        """PR #392 r3: --focus persists through the sidecar meta into the
        finalized receipt, and a resumed dispatch adopts it from there."""
        calls: list = []
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            "--base",
            "HEAD~1",
            "--focus",
            "auth, error paths",
            "--json",
            fake=self._ship_exec(calls),
        )
        self.assertEqual(code, 0, err)
        payload = self._payload(out)
        rid = payload["rid"]
        meta = json.loads(
            (self.root / ".flow" / "review-fanout" / rid / "meta.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(meta["focus"], "auth, error paths")
        for call in calls:
            self.assertIn("auth, error paths", call["prompt"])

        receipt = self.root / "focus-receipt.json"
        merged = self._write_merged(_merged_review("One finding."))
        code, out, err = self._run(
            "codex",
            "impl-review-fanout-finalize",
            "--base",
            "HEAD~1",
            "--rid",
            rid,
            "--merged-file",
            str(merged),
            "--receipt",
            str(receipt),
            "--needs-work-survivors",
            "1",
            "--json",
        )
        self.assertEqual(code, 0, err)
        data = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(data.get("focus"), "auth, error paths")
        self.assertEqual(
            flowctl._receipt_focus(str(receipt)), "auth, error paths",
        )

    # 9 -----------------------------------------------------------------

    def test_path_collision(self) -> None:
        """Sequential (not concurrent) exercise of the collision surfaces:
        distinct rids for a task and a standalone dispatch on the same repo,
        then a forced standalone rid collision. True concurrency is covered
        by exclusive mkdir + O_EXCL publication at the OS layer; this test
        pins the visible refusal semantics (host review r1: honest scope)."""
        calls: list = []
        code, task_payload, err = self._dispatch(self._ship_exec(calls))
        self.assertEqual(code, 0, err)
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            "--base",
            "HEAD~1",
            "--json",
            fake=self._ship_exec(calls),
        )
        self.assertEqual(code, 0, err)
        standalone = self._payload(out)
        self.assertNotEqual(task_payload["rid"], standalone["rid"])
        fanout = self.root / ".flow" / "review-fanout"
        self.assertTrue((fanout / task_payload["rid"]).is_dir())
        self.assertTrue((fanout / standalone["rid"]).is_dir())

        collision_rid = "ab" * 16
        collide_dir = fanout / collision_rid
        collide_dir.mkdir(parents=True)
        marker = collide_dir / "keep-me"
        marker.write_text("untouched\n", encoding="utf-8")
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            "--base",
            "HEAD~1",
            "--json",
            fake=self._ship_exec(calls),
            extra_patches=(
                mock.patch.object(flowctl.secrets, "token_hex", return_value=collision_rid),
            ),
        )
        self.assertNotEqual(code, 0)
        combined = out + err
        self.assertIn("already exists", combined)
        self.assertEqual(marker.read_text(encoding="utf-8"), "untouched\n")
        self.assertFalse((collide_dir / "meta.json").exists())

    def test_task_collision_refunds_round(self) -> None:
        """host review r1: a task-scoped sidecar collision happens AFTER the
        round is reserved (the directory is named by the reservation id), so
        the dispatch must refund that round in-process instead of burning it."""
        collision_rid = "cd" * 16
        fanout = self.root / ".flow" / "review-fanout"
        collide_dir = fanout / collision_rid
        collide_dir.mkdir(parents=True)
        calls: list = []
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            self.task_id,
            "--base",
            "HEAD~1",
            "--force",
            "--json",
            fake=self._ship_exec(calls),
            extra_patches=(
                mock.patch.object(
                    flowctl.uuid,
                    "uuid4",
                    return_value=mock.Mock(hex=collision_rid),
                ),
            ),
        )
        self.assertEqual(code, 2)
        self.assertIn("already exists", out + err)
        self.assertFalse(calls, "no draw may run after a collision")
        self.assertEqual(self._pending(), 0)
        self.assertEqual(self._rounds(), 0)
        attempts = self._attempts()
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].get("outcome"), "transport_failure")
        self.assertEqual(attempts[0].get("failure_class"), "sidecar_collision")
        # The dispatch-phase refund-intent journal was superseded and cleaned
        # by the in-process refund.
        self.assertFalse(
            list((self.root / ".flow" / "review-runs").glob("*.json"))
        )

    # 10 ----------------------------------------------------------------

    def test_axis_prompt(self) -> None:
        captured: dict[str, str] = {}

        def fake(
            prompt,
            *,
            session_id,
            repo_root,
            spec,
            resolution_out,
            args,
            resume_only=False,
        ):
            axis = _axis_of(prompt)
            captured[axis] = prompt
            resolution_out["model"] = f"{axis}-model"
            return "<verdict>SHIP</verdict>", f"sess-{axis}", 0, ""

        code, payload, err = self._dispatch(fake)
        self.assertEqual(code, 0, err)
        self.assertEqual(set(captured), set(flowctl.REVIEW_FANOUT_AXES))
        for axis, prompt in captured.items():
            own = flowctl.REVIEW_FANOUT_AXIS_LINES[axis]
            self.assertIn(own, prompt)
            for other, line in flowctl.REVIEW_FANOUT_AXIS_LINES.items():
                if other != axis:
                    self.assertNotIn(line, prompt)
        default = flowctl.build_review_prompt("impl", spec_path="x")
        self.assertNotIn("Axis focus", default)

    # 11 ----------------------------------------------------------------

    def test_negative_gate(self) -> None:
        # The R15 gate IS the argument parser: the fanout subcommands are
        # registered under `codex` only, so copilot/cursor invocations die as
        # an argparse invalid-choice error before any handler runs (the old
        # in-handler registry re-check was unreachable and has been removed —
        # host review r1).
        for backend in ("copilot", "cursor"):
            with self.subTest(backend=backend):
                code, out, err = self._run(
                    backend, "impl-review-fanout", "--base", "HEAD~1", "--json"
                )
                self.assertEqual(code, 2)
                self.assertIn("invalid choice", err)
                self.assertIn("impl-review-fanout", err)

        flowctl._wire_backend_review_hooks()
        self.assertTrue(flowctl.BACKEND_REGISTRY["codex"].get("fanout_draws"))
        for name, reg in flowctl.BACKEND_REGISTRY.items():
            if name == "codex":
                continue
            self.assertFalse(
                bool(reg.get("fanout_draws")),
                f"{name} must not enable fanout_draws",
            )

        calls: list = []

        def fake(
            prompt,
            *,
            session_id,
            repo_root,
            spec,
            resolution_out,
            args,
            resume_only=False,
        ):
            calls.append(1)
            return "<verdict>SHIP</verdict>", session_id or "copilot-sess", 0, ""

        code, out, err = self._run(
            "copilot",
            "impl-review",
            self.task_id,
            "--base",
            "HEAD~1",
            "--json",
            fake=fake,
            backend="copilot",
        )
        self.assertEqual(code, 0, err + out)
        self.assertEqual(len(calls), 1)

        source = inspect.getsource(flowctl._dispatch_backend_review)
        self.assertNotIn("fanout", source)

    def test_non_codex_primary_rejected(self) -> None:
        """host review r1: the primary draw drives the merged receipt's
        top-level backend/session/model and the round-2 codex resume, so a
        cross-backend spec is allowed on secondary draws only."""
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            self.task_id,
            "--base",
            "HEAD~1",
            "--json",
            "--draw",
            "correctness=cursor",
            "--draw",
            "contracts",
        )
        self.assertEqual(code, 2)
        combined = out + err
        self.assertIn("primary draw", combined)
        self.assertEqual(self._pending(), 0)
        self.assertEqual(self._rounds(), 0)

    # 12 ----------------------------------------------------------------

    def test_first_round_only_guard(self) -> None:
        receipt = self.root / "prior.json"
        receipt.write_text(
            json.dumps(
                {
                    "type": "impl_review",
                    "id": self.task_id,
                    "mode": "codex",
                    "verdict": "NEEDS_WORK",
                    "session_id": "",
                    "review": "prior findings from the last round",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        calls: list = []
        # Unforced: the open receipt refuses the fan-out.
        code, out, err = self._run(
            "codex",
            "impl-review-fanout",
            self.task_id,
            "--base",
            "HEAD~1",
            "--receipt",
            str(receipt),
            "--json",
            fake=self._ship_exec(calls),
        )
        self.assertNotEqual(code, 0)
        payload = self._payload(out) if out.strip() else {}
        combined = (payload.get("error") or "") + err
        self.assertIn("first-round only", combined)
        self.assertFalse(calls)
        # --force is the documented human lane: it bypasses BOTH guard legs
        # (PR #392 r30) and the fresh fan-out proceeds.
        code, payload, err = self._dispatch(
            self._ship_exec(calls), "--receipt", str(receipt)
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(calls)


if __name__ == "__main__":
    unittest.main()
