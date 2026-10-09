"""Public-CLI coverage for resuming review after transport failures.

Every flowctl invocation is a fresh subprocess. Fake reviewer executables
exercise the actual backend process boundary without credentials or network
access; Codex replies use its JSONL event envelope and Copilot replies use its
plain-text result contract.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
DEFAULT_FLOWCTL_SOURCE = HERE.parents[1] / "scripts" / "flowctl.py"
FLOWCTL_SOURCE = Path(
    os.environ.get("FLOWCTL_TEST_SOURCE", str(DEFAULT_FLOWCTL_SOURCE))
).resolve()

_FAKE_REVIEWER = r'''import json
import os
import sys
from pathlib import Path


backend = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in {"codex", "copilot"} else Path(sys.argv[0]).name
args = sys.argv[2:] if len(sys.argv) > 1 and sys.argv[1] in {"codex", "copilot"} else sys.argv[1:]
if "--version" in args:
    print("codex 0.159.0" if backend == "codex" else "GitHub Copilot CLI 1.0.34")
    raise SystemExit(0)

if backend == "codex":
    sys.stdin.read()
model = None
if "--model" in args:
    model = args[args.index("--model") + 1]
response = os.environ.get(f"FLOW_FAKE_{backend.upper()}_RESPONSE", "missing_verdict")
exit_code = 0
if response == "ship":
    text = (
        "No blocking findings. The reviewed change is sound.\n\n"
        "```json\n"
        '{"findings":[],"classification_counts":{"introduced":0,"pre_existing":0},"unaddressed":[]}\n'
        "```\n"
        "<verdict>SHIP</verdict>\n"
    )
elif response == "needs_work":
    text = (
        "## Issue 1\n"
        "- **Severity**: Major\n"
        "- **Confidence**: 100\n"
        "- **Classification**: introduced\n"
        "- **Problem**: The reviewed change mishandles the empty value.\n"
        "- **Suggestion**: Handle the empty value explicitly.\n\n"
        "```json\n"
        '{"findings":[{"severity":"P1","confidence":100,"classification":"introduced","title":"Empty value"}],"classification_counts":{"introduced":1,"pre_existing":0},"unaddressed":[]}\n'
        "```\n"
        "<verdict>NEEDS_WORK</verdict>\n"
    )
elif response == "ship_resolved":
    ordinal = os.environ.get("FLOW_FAKE_RESOLUTION_ORDINAL", "")
    if not ordinal.isdigit():
        raise SystemExit("FLOW_FAKE_RESOLUTION_ORDINAL must be a positive integer")
    text = (
        f"Prior finding #{ordinal}: fixed\n\n"
        "No blocking findings. The reviewed change is sound.\n\n"
        "```json\n"
        '{"findings":[],"classification_counts":{"introduced":0,"pre_existing":0},"unaddressed":[]}\n'
        "```\n"
        "<verdict>SHIP</verdict>\n"
    )
elif response == "nonzero_exit":
    text = "The reviewer process failed before producing a verdict.\n"
    exit_code = 1
else:
    text = "Review process completed without a verdict tag.\n"

record_path = os.environ.get("FLOW_FAKE_REVIEW_CALLS")
if record_path:
    record = json.dumps({"backend": backend, "model": model, "response": response, "args": args}) + "\n"
    fd = os.open(record_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, record.encode("utf-8"))
    finally:
        os.close(fd)

if backend == "codex":
    print(json.dumps({"type": "thread.started", "thread_id": "test-thread"}))
    print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": text}}))
else:
    sys.stdout.write(text)
if exit_code:
    sys.stderr.write("temporary fake reviewer failure\n")
    raise SystemExit(exit_code)
'''

_EMPTY_SHIP = (
    "No blocking findings. The reviewed change is sound.\n\n"
    "```json\n"
    '{"findings":[],"classification_counts":{"introduced":0,"pre_existing":0},"unaddressed":[]}\n'
    "```\n"
    "<verdict>SHIP</verdict>\n"
)


@unittest.skipIf(
    os.name == "nt",
    "CreateProcess cannot execute the list-form PATH script shims used for fake reviewers",
)
class TestReviewTransportResumption(unittest.TestCase):
    def setUp(self) -> None:
        if not FLOWCTL_SOURCE.is_file():
            self.fail(f"flowctl source not found: {FLOWCTL_SOURCE}")
        self._tmp = tempfile.TemporaryDirectory(prefix="flowctl-transport-resumption-")
        self.addCleanup(self._tmp.cleanup)
        self.temp_root = Path(self._tmp.name).resolve()
        self.repo = self.temp_root / "repo"
        self.repo.mkdir()
        self.state_dir = self.temp_root / "flow-state"
        self.receipt = self.temp_root / "review-receipt.json"
        self.calls_path = self.temp_root / "reviewer-calls.jsonl"
        self.bin_dir = self.temp_root / "bin"
        self.bin_dir.mkdir()
        self.spec_id = "fn-520-demo"
        self.task_id = f"{self.spec_id}.1"
        self.other_task_id = f"{self.spec_id}.2"
        self._init_repo()
        self._install_fake_reviewers()
        self.base = self._git("rev-parse", "HEAD")
        (self.repo / "app.py").write_text("value = 2\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", "reviewed change")
        self.head = self._git("rev-parse", "HEAD")
        self.env = dict(os.environ)
        for key in (
            "FLOW_REVIEW_BACKEND",
            "FLOW_REVIEW_EXECUTION_URL",
            "FLOW_REVIEW_EXECUTION_TOKEN",
            "FLOW_RE_REVIEW_SESSION",
            "REVIEW_RECEIPT_PATH",
        ):
            self.env.pop(key, None)
        self.env.pop("MAX_REVIEW_TRANSPORT_FAILURES", None)
        self.env.pop("MAX_REVIEW_ITERATIONS", None)
        self.env.update(
            {
                "FLOW_STATE_DIR": str(self.state_dir),
                "FLOW_REVIEW_EXEC_TIMEOUT": "5",
                "FLOW_FAKE_REVIEW_CALLS": str(self.calls_path),
                "FLOW_FAKE_CODEX_RESPONSE": "missing_verdict",
                "FLOW_FAKE_COPILOT_RESPONSE": "missing_verdict",
                "PATH": str(self.bin_dir) + os.pathsep + os.environ.get("PATH", ""),
            }
        )

    def _init_repo(self) -> None:
        (self.repo / ".flow" / "specs").mkdir(parents=True)
        (self.repo / ".flow" / "tasks").mkdir(parents=True)
        spec = {
            "id": self.spec_id,
            "title": "Transport resumption",
            "status": "in_progress",
        }
        (self.repo / ".flow" / "specs" / f"{self.spec_id}.json").write_text(
            json.dumps(spec), encoding="utf-8"
        )
        (self.repo / ".flow" / "specs" / f"{self.spec_id}.md").write_text(
            "# Transport resumption\n\n## Acceptance Criteria\n\n- R1: review completes.\n",
            encoding="utf-8",
        )
        for task_id in (self.task_id, self.other_task_id):
            (self.repo / ".flow" / "tasks" / f"{task_id}.json").write_text(
                json.dumps({"id": task_id, "spec": self.spec_id, "title": "Review task"}),
                encoding="utf-8",
            )
            (self.repo / ".flow" / "tasks" / f"{task_id}.md").write_text(
                f"# {task_id}\n\nImplement R1.\n", encoding="utf-8"
            )
        (self.repo / "app.py").write_text("value = 1\n", encoding="utf-8")
        for argv in (
            ["git", "init", "-q", "-b", "main"],
            ["git", "config", "user.email", "test@example.com"],
            ["git", "config", "user.name", "Test"],
            ["git", "add", "-A"],
            ["git", "commit", "-qm", "base"],
        ):
            subprocess.run(argv, cwd=self.repo, check=True, capture_output=True, text=True)

    def _install_fake_reviewers(self) -> None:
        for name in ("codex", "copilot"):
            launcher = self.bin_dir / name
            launcher.write_text(f"#!{sys.executable}\n" + _FAKE_REVIEWER, encoding="utf-8")
            launcher.chmod(0o755)

    def _git(self, *argv: str, cwd: Path | None = None) -> str:
        result = subprocess.run(
            ["git", *argv], cwd=cwd or self.repo, check=True,
            capture_output=True, text=True, encoding="utf-8",
        )
        return result.stdout.strip()

    def _cli(self, *args: str) -> list[str]:
        if FLOWCTL_SOURCE.suffix.lower() == ".py":
            return [sys.executable, str(FLOWCTL_SOURCE), *args]
        return [str(FLOWCTL_SOURCE), *args]

    def _run(
        self,
        *args: str,
        cwd: Path | None = None,
        state_dir: Path | None = None,
        responses: dict[str, str] | None = None,
        fake_context: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(self.env)
        if state_dir is not None:
            env["FLOW_STATE_DIR"] = str(state_dir)
        for backend, response in (responses or {}).items():
            env[f"FLOW_FAKE_{backend.upper()}_RESPONSE"] = response
        env.update(fake_context or {})
        result = subprocess.run(
            self._cli(*args),
            cwd=cwd or self.repo,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
        )
        transcript_path = os.environ.get("FLOWCTL_TEST_TRANSCRIPT")
        if transcript_path:
            path = Path(transcript_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "cwd": str(cwd or self.repo),
                "argv": list(args),
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
            with path.open("a", encoding="utf-8") as transcript:
                transcript.write(json.dumps(record, ensure_ascii=False) + "\n")
        return result

    def _spec_data(self, repo: Path | None = None) -> dict:
        root = repo or self.repo
        return json.loads(
            (root / ".flow" / "specs" / f"{self.spec_id}.json").read_text(
                encoding="utf-8"
            )
        )

    def _attempts(self, repo: Path | None = None, task_id: str | None = None) -> list[dict]:
        rows = self._spec_data(repo).get("review_attempts") or []
        return [
            row for row in rows
            if isinstance(row, dict) and (task_id is None or row.get("task") == task_id)
        ]

    def _review_args(self, command: str, backend: str, task_id: str, model: str) -> list[str]:
        return [
            backend,
            command,
            task_id,
            "--base",
            self.base,
            "--receipt",
            str(self.receipt),
            "--spec",
            f"{backend}:{model}:high",
            "--json",
        ]

    def _assert_command(self, result: subprocess.CompletedProcess[str], code: int) -> None:
        self.assertEqual(
            result.returncode,
            code,
            f"flowctl exited {result.returncode}, expected {code}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_single_review_records_first_verdict_after_transport_failure(self) -> None:
        failed = self._run(
            *self._review_args("impl-review", "codex", self.task_id, "gpt-6.1-sol")
        )
        self._assert_command(failed, 2)
        self.assertEqual(len(self._attempts()), 1)
        failure = self._attempts()[0]
        self.assertEqual(failure.get("outcome"), "transport_failure")
        self.assertEqual(failure.get("failure_class"), "missing_verdict")
        self.assertFalse(failure.get("round_consumed"))

        recovered = self._run(
            *self._review_args("impl-review", "copilot", self.task_id, "gpt-6-astra"),
            responses={"copilot": "ship"},
        )
        self._assert_command(recovered, 0)
        self.assertEqual(json.loads(recovered.stdout).get("verdict"), "SHIP")
        attempts = self._attempts()
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[0].get("backend"), "codex")
        self.assertEqual(attempts[0].get("model"), "gpt-6.1-sol")
        self.assertEqual(attempts[1].get("outcome"), "verdict")
        self.assertEqual(attempts[1].get("backend"), "copilot")
        self.assertEqual(attempts[1].get("model"), "gpt-6-astra")
        self.assertTrue(attempts[1].get("round_consumed"))
        self.assertEqual(self._spec_data().get("review_pending_rounds", {}).get(f"impl:{self.task_id}", 0), 0)
        self.assertEqual(len([row for row in attempts if row.get("round_consumed")]), 1)

    def test_single_review_same_backend_recovers_after_transport_unhealthy(self) -> None:
        failures = []
        for response in ("missing_verdict", "nonzero_exit", "missing_verdict"):
            failures.append(
                self._run(
                    *self._review_args("impl-review", "codex", self.task_id, "gpt-6.1-sol"),
                    responses={"codex": response},
                )
            )
        self.assertEqual([result.returncode for result in failures], [2, 2, 5])
        self.assertIn("TRANSPORT_UNHEALTHY", failures[-1].stdout)

        recovered = self._run(
            *self._review_args("impl-review", "codex", self.task_id, "gpt-6.1-sol"),
            responses={"codex": "ship"},
        )
        self._assert_command(recovered, 0)
        self.assertEqual(json.loads(recovered.stdout).get("verdict"), "SHIP")
        attempts = self._attempts()
        self.assertEqual(len(attempts), 4)
        self.assertEqual(
            [row.get("failure_class") for row in attempts[:3]],
            ["missing_verdict", "nonzero_exit", "missing_verdict"],
        )
        self.assertTrue(all(not row.get("round_consumed") for row in attempts[:3]))
        self.assertEqual(attempts[-1].get("outcome"), "verdict")
        self.assertTrue(attempts[-1].get("round_consumed"))

    def test_cross_backend_no_verdict_preserves_open_findings_for_original_backend(self) -> None:
        first = self._run(
            *self._review_args("impl-review", "codex", self.task_id, "gpt-6.1-sol"),
            responses={"codex": "needs_work"},
        )
        self._assert_command(first, 0)
        original_receipt_bytes = self.receipt.read_bytes()
        original_receipt = json.loads(original_receipt_bytes)
        original_findings = original_receipt["findings"]
        original_finding = original_findings["items"][0]
        original_finding_id = original_finding["id"]
        self.assertEqual(original_receipt.get("verdict"), "NEEDS_WORK")

        (self.repo / "app.py").write_text("value = 3\n", encoding="utf-8")
        self._git("add", "app.py")
        self._git("commit", "-qm", "address review finding")

        copilot_failure = self._run(
            *self._review_args("impl-review", "copilot", self.task_id, "gpt-6-astra"),
            responses={"copilot": "nonzero_exit"},
        )
        snapshot = self.receipt.read_bytes() if self.receipt.exists() else None
        route = self._run(
            "review-route", self.task_id, "--receipt", str(self.receipt), "--json"
        )
        self._assert_command(copilot_failure, 2)
        self.assertEqual(snapshot, original_receipt_bytes)
        self._assert_command(route, 0)
        route_payload = json.loads(route.stdout)
        self.assertEqual(route_payload.get("action"), "fix-then-rereview", route.stdout)
        self.assertEqual(route_payload.get("reason"), "open_receipt", route.stdout)

        repaired_codex = self._run(
            *self._review_args("impl-review", "codex", self.task_id, "gpt-6.1-sol"),
            responses={"codex": "ship_resolved"},
            fake_context={
                "FLOW_FAKE_RESOLUTION_ORDINAL": str(original_finding["ordinal"]),
            },
        )
        self._assert_command(repaired_codex, 0)
        self.assertEqual(json.loads(repaired_codex.stdout).get("verdict"), "SHIP")

        shipped_receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        shipped_findings = shipped_receipt["findings"]
        self.assertEqual(shipped_receipt.get("verdict"), "SHIP")
        self.assertEqual(shipped_findings["round"], original_findings["round"] + 1)
        self.assertEqual(
            shipped_findings.get("supersedesReceiptId"),
            original_findings["sourceReceiptId"],
        )
        self.assertEqual(shipped_findings["items"][0]["id"], original_finding_id)
        self.assertEqual(shipped_findings["items"][0]["status"], "fixed")
        self.assertEqual(
            shipped_findings["items"][0]["firstSeenReceiptId"],
            original_finding["firstSeenReceiptId"],
        )

        attempts = self._attempts(task_id=self.task_id)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(attempts[0].get("backend"), "codex")
        self.assertEqual(attempts[0].get("verdict"), "NEEDS_WORK")
        self.assertTrue(attempts[0].get("round_consumed"))
        self.assertEqual(attempts[1].get("backend"), "copilot")
        self.assertEqual(attempts[1].get("failure_class"), "nonzero_exit")
        self.assertEqual(attempts[1].get("outcome"), "transport_failure")
        self.assertFalse(attempts[1].get("round_consumed"))
        self.assertEqual(attempts[2].get("backend"), "codex")
        self.assertEqual(attempts[2].get("verdict"), "SHIP")
        self.assertEqual(attempts[2].get("outcome"), "verdict")
        self.assertTrue(attempts[2].get("round_consumed"))
        self.assertEqual(sum(row.get("verdict") == "SHIP" for row in attempts), 1)
        self.assertEqual(sum(bool(row.get("round_consumed")) for row in attempts), 2)
        state = self._spec_data()
        self.assertEqual((state.get("impl_review_rounds") or {}).get(self.task_id, 0), 0)
        self.assertEqual(
            (state.get("review_pending_rounds") or {}).get(f"impl:{self.task_id}", 0),
            0,
        )
        self.assertFalse(state.get("review_reservations"))

    def test_six_refunds_route_to_fanout_and_finalize_once(self) -> None:
        failure_codes = []
        for _ in range(6):
            result = self._run(
                *self._review_args(
                    "impl-review-fanout", "codex", self.task_id, "gpt-6.1-sol"
                ),
                "--draw",
                "correctness",
            )
            failure_codes.append(result.returncode)
            self.assertIn(
                result.returncode,
                (2, 5),
                f"unexpected fan-out result\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
        self.assertEqual(failure_codes[2], 5, "the third no-verdict failure hits the default budget")
        self.assertEqual(len(self._attempts()), 6)
        self.assertTrue(all(row.get("outcome") == "transport_failure" for row in self._attempts()))
        self.assertTrue(all(row.get("failure_class") == "missing_verdict" for row in self._attempts()))
        self.assertTrue(all(not row.get("round_consumed") for row in self._attempts()))
        state = self._spec_data()
        self.assertEqual((state.get("impl_review_rounds") or {}).get(self.task_id, 0), 0)
        self.assertEqual((state.get("review_pending_rounds") or {}).get(f"impl:{self.task_id}", 0), 0)
        self.assertFalse(state.get("review_reservations"))

        route = self._run(
            "review-route", self.task_id, "--receipt", str(self.receipt), "--json"
        )
        self._assert_command(route, 0)
        route_payload = json.loads(route.stdout)
        self.assertEqual(route_payload.get("action"), "fanout", route.stdout)
        self.assertEqual(route_payload.get("reason"), "first_round", route.stdout)

        # Same task id and git common-dir, separate worktree/state: failures
        # recorded in the first checkout do not leak into a sibling checkout.
        sibling = self.temp_root / "sibling-worktree"
        self._git("worktree", "add", "-q", "--detach", str(sibling), self.head)
        sibling_state = self.temp_root / "sibling-flow-state"
        sibling_receipt = self.temp_root / "sibling-receipt.json"
        sibling_route = self._run(
            "review-route", self.task_id, "--receipt", str(sibling_receipt), "--json",
            cwd=sibling, state_dir=sibling_state,
        )
        self._assert_command(sibling_route, 0)
        self.assertEqual(json.loads(sibling_route.stdout).get("action"), "fanout")
        self.assertFalse(self._attempts(repo=sibling))
        other_task_route = self._run(
            "review-route", self.other_task_id, "--receipt", str(self.temp_root / "other-task.json"), "--json"
        )
        self._assert_command(other_task_route, 0)
        self.assertEqual(json.loads(other_task_route.stdout).get("action"), "fanout")

        dispatch = self._run(
            *self._review_args("impl-review-fanout", "copilot", self.task_id, "gpt-6-astra"),
            "--draw",
            "correctness",
            responses={"copilot": "ship"},
        )
        self._assert_command(dispatch, 0)
        dispatch_payload = json.loads(dispatch.stdout)
        self.assertEqual(dispatch_payload.get("failed_draws"), 0, dispatch.stdout)
        reservation_id = dispatch_payload["rid"]
        before_finalize = self._spec_data()
        self.assertEqual(
            (before_finalize.get("impl_review_rounds") or {}).get(self.task_id), 1
        )
        self.assertEqual(
            (before_finalize.get("review_pending_rounds") or {}).get(f"impl:{self.task_id}"), 1
        )
        self.assertEqual(len(self._attempts()), 6)

        merged = self.temp_root / "merged-review.md"
        merged.write_text(_EMPTY_SHIP, encoding="utf-8")
        finalized = self._run(
            "copilot",
            "impl-review-fanout-finalize",
            self.task_id,
            "--rid",
            reservation_id,
            "--merged-file",
            str(merged),
            "--receipt",
            str(self.receipt),
            "--json",
            responses={"copilot": "ship"},
        )
        self._assert_command(finalized, 0)
        self.assertEqual(json.loads(finalized.stdout).get("verdict"), "SHIP")
        attempts = self._attempts()
        self.assertEqual(len(attempts), 7)
        self.assertEqual(sum(bool(row.get("round_consumed")) for row in attempts), 1)
        final = attempts[-1]
        self.assertEqual(final.get("outcome"), "verdict")
        self.assertEqual(final.get("backend"), "copilot")
        self.assertEqual(final.get("model"), "gpt-6-astra")
        self.assertTrue(final.get("round_consumed"))
        after_finalize = self._spec_data()
        self.assertEqual((after_finalize.get("review_pending_rounds") or {}).get(f"impl:{self.task_id}", 0), 0)
        self.assertFalse(after_finalize.get("review_reservations"))
        self.assertEqual(json.loads(self.receipt.read_text(encoding="utf-8")).get("mode"), "copilot")

        duplicate = self._run(
            "copilot",
            "impl-review-fanout-finalize",
            self.task_id,
            "--rid",
            reservation_id,
            "--merged-file",
            str(merged),
            "--receipt",
            str(self.receipt),
            "--json",
        )
        self._assert_command(duplicate, 0)
        self.assertEqual(len(self._attempts()), 7, "finalize replay must not consume a second round")

    def test_open_needs_work_receipt_survives_transport_failures(self) -> None:
        first = self._run(
            *self._review_args("impl-review", "codex", self.task_id, "gpt-6.1-sol"),
            responses={"codex": "needs_work"},
        )
        self._assert_command(first, 0)
        original_receipt_bytes = self.receipt.read_bytes()
        original_receipt = json.loads(original_receipt_bytes)
        original_findings = original_receipt.get("findings")
        self.assertEqual(original_receipt.get("verdict"), "NEEDS_WORK")
        self.assertIsInstance(original_findings, dict)
        self.assertEqual(len(original_findings["items"]), 1)
        original_finding = original_findings["items"][0]
        self.assertEqual(original_finding.get("ordinal"), 1)
        original_finding_id = original_finding["id"]

        (self.repo / "app.py").write_text("value = 3\n", encoding="utf-8")
        self._git("add", "app.py")
        self._git("commit", "-qm", "address review finding")
        failures = []
        receipt_snapshots = []
        for response in ("missing_verdict", "nonzero_exit", "missing_verdict"):
            failures.append(
                self._run(
                    *self._review_args("impl-review", "codex", self.task_id, "gpt-6.1-sol"),
                    responses={"codex": response},
                )
            )
            receipt_snapshots.append(
                self.receipt.read_bytes() if self.receipt.exists() else None
            )
        route = self._run(
            "review-route", self.task_id, "--receipt", str(self.receipt), "--json"
        )
        self.assertEqual([result.returncode for result in failures], [2, 2, 5])
        self.assertEqual(
            receipt_snapshots,
            [original_receipt_bytes] * 3,
            "every no-verdict cleanup must leave the active NEEDS_WORK receipt byte-identical",
        )

        refunded = self._attempts(task_id=self.task_id)
        self.assertEqual(len(refunded), 4)
        self.assertEqual(refunded[0].get("verdict"), "NEEDS_WORK")
        self.assertTrue(refunded[0].get("round_consumed"))
        self.assertEqual(
            [row.get("failure_class") for row in refunded[1:]],
            ["missing_verdict", "nonzero_exit", "missing_verdict"],
        )
        self.assertIn("temporary fake reviewer failure", refunded[2].get("failure_message", ""))
        self.assertTrue(all(row.get("outcome") == "transport_failure" for row in refunded[1:]))
        self.assertTrue(all(not row.get("round_consumed") for row in refunded[1:]))
        state = self._spec_data()
        self.assertEqual((state.get("impl_review_rounds") or {}).get(self.task_id), 1)
        self.assertEqual(
            (state.get("review_pending_rounds") or {}).get(f"impl:{self.task_id}", 0),
            0,
        )
        self.assertFalse(state.get("review_reservations"))

        self._assert_command(route, 0)
        route_payload = json.loads(route.stdout)
        self.assertEqual(route_payload.get("action"), "fix-then-rereview", route.stdout)
        self.assertEqual(route_payload.get("reason"), "open_receipt", route.stdout)

        repaired = self._run(
            *self._review_args("impl-review", "codex", self.task_id, "gpt-6.1-sol"),
            responses={"codex": "ship_resolved"},
            fake_context={
                "FLOW_FAKE_RESOLUTION_ORDINAL": str(original_finding["ordinal"]),
            },
        )
        self._assert_command(repaired, 0)
        self.assertEqual(json.loads(repaired.stdout).get("verdict"), "SHIP")

        shipped_receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        shipped_findings = shipped_receipt["findings"]
        self.assertEqual(shipped_receipt.get("verdict"), "SHIP")
        self.assertEqual(shipped_findings["round"], original_findings["round"] + 1)
        self.assertEqual(
            shipped_findings.get("supersedesReceiptId"),
            original_findings["sourceReceiptId"],
        )
        self.assertEqual(shipped_findings["items"][0]["id"], original_finding_id)
        self.assertEqual(shipped_findings["items"][0]["status"], "fixed")
        self.assertEqual(
            shipped_findings["items"][0]["firstSeenReceiptId"],
            original_finding["firstSeenReceiptId"],
        )

        shipped_attempts = self._attempts(task_id=self.task_id)
        verdict_rows = [row for row in shipped_attempts if row.get("outcome") == "verdict"]
        self.assertEqual(len(verdict_rows), 2)
        self.assertTrue(all(row.get("round_consumed") for row in verdict_rows))
        digest_item = verdict_rows[-1]["findings_digest"]["items"][0]
        self.assertEqual(digest_item["findingId"], original_finding_id)
        self.assertEqual(digest_item["status"], "fixed")
        self.assertEqual(digest_item["chainRoot"], original_finding_id)

        history_dir = self.receipt.with_name(self.receipt.name + ".history")
        archived_receipts = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(history_dir.glob("*.json"))
        ]
        self.assertIn(original_receipt, archived_receipts)


if __name__ == "__main__":
    unittest.main()
