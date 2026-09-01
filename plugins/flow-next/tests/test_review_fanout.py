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
                fin_code, fin, fin_err = self._finalize(payload["rid"], merged)
                self.assertEqual(fin_code, exit_code, fin_err)
                self.assertEqual(fin.get("verdict"), expected)

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
        fin_code, fin, fin_err = self._finalize(rid, empty)
        self.assertEqual(fin_code, flowctl.REVIEW_CAP_EXIT_CODE, fin_err)
        self.assertEqual(fin.get("verdict"), "NEEDS_HUMAN")

        # Counter-case: absent/unparseable container keeps NEEDS_WORK (R9).
        code, payload, err = self._dispatch(self._verdict_exec(by_axis))
        self.assertEqual(code, 0, err)
        missing = self._write_merged(_unparseable_merged_review())
        fin_code, fin, fin_err = self._finalize(payload["rid"], missing)
        self.assertEqual(fin_code, 0, fin_err)
        self.assertEqual(fin.get("verdict"), "NEEDS_WORK")

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

    # 9 -----------------------------------------------------------------

    def test_path_collision(self) -> None:
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
        for backend in ("copilot", "cursor"):
            with self.subTest(backend=backend):
                code, out, err = self._run(
                    backend, "impl-review-fanout", "--base", "HEAD~1", "--json"
                )
                self.assertNotEqual(code, 0)
                self.assertTrue(out or err)

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
        code, payload, err = self._dispatch(
            self._ship_exec(calls), "--receipt", str(receipt)
        )
        self.assertNotEqual(code, 0)
        combined = (payload.get("error") or "") + err
        self.assertIn("first-round only", combined)
        self.assertFalse(calls)


if __name__ == "__main__":
    unittest.main()
