"""Unit tests for the host review-backend sentinel (fn-123 R5 / task .3).

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_host_review_backend -q

``host`` is a NON-EXECUTABLE selection sentinel: review runs as a host-native
fresh-context subagent (skill-owned). flowctl only registers/parses it —
no model/effort on the string, no run_exec hook, never a subprocess path.
Pins live in the AGENTS.md model-routing section.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

import sys

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def _load_flowctl() -> Any:
    here = Path(__file__).resolve()
    flowctl_path = here.parent.parent / "scripts" / "flowctl.py"
    if not flowctl_path.is_file():
        raise RuntimeError(f"flowctl.py not found at {flowctl_path}")
    spec = importlib.util.spec_from_file_location("flowctl_host_test", flowctl_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()
BackendSpec = flowctl.BackendSpec
BACKEND_REGISTRY = flowctl.BACKEND_REGISTRY
MODEL_ROLE_BACKENDS = flowctl.MODEL_ROLE_BACKENDS

REPO = Path(__file__).resolve().parents[3]
SKILLS = REPO / "plugins" / "flow-next" / "skills"


def _read(relative: str) -> str:
    return (SKILLS / relative).read_text(encoding="utf-8")


def _section(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


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


class TestHostBackendRegistry(unittest.TestCase):
    """host is registered but non-executable (no model axis, not role-mappable)."""

    def test_host_in_backend_registry(self) -> None:
        self.assertIn("host", BACKEND_REGISTRY)

    def test_host_models_is_none(self) -> None:
        self.assertIsNone(BACKEND_REGISTRY["host"]["models"])
        self.assertIsNone(BACKEND_REGISTRY["host"]["efforts"])

    def test_host_not_in_model_role_backends(self) -> None:
        # Pins live in AGENTS.md model-routing — not models.roles.<role>.host.
        self.assertNotIn("host", MODEL_ROLE_BACKENDS)


class TestHostBackendSpecParse(unittest.TestCase):
    """Bare host parses; host:<model> forms raise with AGENTS.md routing hint."""

    def test_bare_host_parses_ok(self) -> None:
        s = BackendSpec.parse("host")
        self.assertEqual(s.backend, "host")
        self.assertIsNone(s.model)
        self.assertIsNone(s.effort)
        self.assertIsNone(BACKEND_REGISTRY[s.backend]["models"])

    def test_host_model_form_raises_agents_md_hint(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            BackendSpec.parse("host:opus")
        msg = str(ctx.exception)
        self.assertIn("AGENTS.md", msg)
        self.assertIn("model-routing", msg)

    def test_host_model_effort_form_raises_agents_md_hint(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            BackendSpec.parse("host:opus:high")
        msg = str(ctx.exception)
        self.assertIn("AGENTS.md", msg)
        self.assertIn("model-routing", msg)


if __name__ == "__main__":
    unittest.main()


class TestHostLenientResolution(unittest.TestCase):
    """fn-123 review hardening (sol P1): the LENIENT read-time parser must not
    silently degrade ``host:<model>`` to bare ``host`` — the stored pin the
    user thought they set would be silently ignored. Invalid host specs are
    treated as unset (None) with a loud stderr error."""

    def test_lenient_host_model_returns_none(self) -> None:
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            spec = flowctl.parse_backend_spec_lenient("host:opus", warn=False)
        self.assertIsNone(spec, "host:<model> must not degrade to bare host")
        self.assertIn("invalid", buf.getvalue().lower())

    def test_lenient_host_model_effort_returns_none(self) -> None:
        import io, contextlib
        with contextlib.redirect_stderr(io.StringIO()):
            spec = flowctl.parse_backend_spec_lenient("host:opus:high", warn=True)
        self.assertIsNone(spec)

    def test_lenient_bare_host_still_parses(self) -> None:
        spec = flowctl.parse_backend_spec_lenient("host", warn=False)
        self.assertIsNotNone(spec)
        self.assertEqual(spec.backend, "host")
        resolved = spec.resolve()
        self.assertIsNone(resolved.model)
        self.assertIsNone(resolved.effort)

    def test_lenient_other_backends_still_degrade(self) -> None:
        import io, contextlib
        with contextlib.redirect_stderr(io.StringIO()):
            spec = flowctl.parse_backend_spec_lenient("rp:not-a-model", warn=True)
        self.assertIsNotNone(spec, "legacy lenience for non-host backends must not change")
        self.assertEqual(spec.backend, "rp")


class TestHostReviewWorkflowRouting(unittest.TestCase):
    """Host mechanics stay behind the selected reference and own no status."""

    REVIEW_SKILLS = (
        "flow-next-impl-review",
        "flow-next-spec-completion-review",
    )
    NON_HOST_BACKENDS = ("codex", "copilot", "cursor", "rp")
    HOST_ONLY_MECHANICS = (
        "NEEDS_HUMAN: host review needs a cross-family model pin",
        "`disallowedTools: Edit, Write, Task`",
        '"mode": "host"',
        '"session_id": null',
    )

    def test_root_host_surface_is_only_router_and_safety_invariant(self) -> None:
        for skill in self.REVIEW_SKILLS:
            root = _read(f"{skill}/SKILL.md")
            host = _section(
                root,
                "**For host backend (fn-123 R5 / fn-126):**",
                "**For all backends:**",
            )
            self.assertIn("[workflow-host.md](workflow-host.md)", host)
            self.assertIn("fresh, tool-enforced read-only reviewer", host)
            self.assertIn("different\nmodel family", host)
            self.assertIn("fail closed", host)
            for mechanic in self.HOST_ONLY_MECHANICS:
                self.assertNotIn(mechanic, host, f"{skill}: host mechanics leaked into root")

    def test_non_host_reached_paths_keep_host_mechanics_cold(self) -> None:
        for skill in self.REVIEW_SKILLS:
            root = _read(f"{skill}/SKILL.md")
            common = _read(f"{skill}/workflow-common.md")
            for backend in self.NON_HOST_BACKENDS:
                reached = root + common + _read(f"{skill}/workflow-{backend}.md")
                for mechanic in self.HOST_ONLY_MECHANICS:
                    self.assertNotIn(
                        mechanic,
                        reached,
                        f"{skill}/{backend}: loaded host-only mechanic {mechanic!r}",
                    )

    def test_selected_host_workflows_are_self_contained(self) -> None:
        for skill in self.REVIEW_SKILLS:
            host = _read(f"{skill}/workflow-host.md")
            for mechanic in self.HOST_ONLY_MECHANICS:
                self.assertIn(mechanic, host, f"{skill}: missing {mechanic!r}")
            host_lower = host.lower()
            for required in (
                "prior findings",
                "tests/lints",
                "commit the fixes before re-review",
                "<promise>RETRY</promise>",
            ):
                self.assertIn(
                    required.lower(),
                    host_lower,
                    f"{skill}: incomplete host workflow",
                )
            self.assertIn("deterministic round cap", host_lower)
            self.assertNotIn("Return the verdict", host)

    def test_completion_status_has_one_shared_owner(self) -> None:
        root = _read("flow-next-spec-completion-review/SKILL.md")
        host = _read("flow-next-spec-completion-review/workflow-host.md")
        rp = _read("flow-next-spec-completion-review/workflow-rp.md")
        work = _read("flow-next-work/phases.md")
        pilot = _read("flow-next-pilot/workflow.md")
        command = "$FLOWCTL spec set-completion-review-status"
        self.assertEqual(root.count(command), 1, "shared owner must issue one status write")
        self.assertNotIn(command, host, "selected host workflow must never write status")
        self.assertNotIn(command, rp, "selected rp workflow must never write status")
        self.assertNotIn(command, work, "work caller must never repeat the status write")
        self.assertIn("This shared step is the sole writer for host and rp", root)
        self.assertIn("never write completion status", root)
        self.assertIn("This host workflow never writes terminal completion status", host)
        self.assertIn("stop without writing completion status", host)
        self.assertIn("Work never writes that status again", work)
        self.assertIn(
            "the spec-completion-review skill writes terminal "
            "`completion_review_status` through its backend-aware shared owner",
            pilot,
        )
        self.assertNotIn("or write status here", host)

    def test_capped_completion_status_precedes_exit(self) -> None:
        root = _read("flow-next-spec-completion-review/SKILL.md")
        write_at = root.index("$FLOWCTL spec set-completion-review-status")
        terminal_at = root.index(
            'echo "ESCALATE: completion-review did not converge',
            write_at,
        )
        exit_at = root.index("exit 4", terminal_at)
        self.assertLess(write_at, terminal_at)
        self.assertLess(terminal_at, exit_at)
        self.assertIn(
            "An exit-4 cap refusal before this run has delivered a completion "
            "verdict is\nnon-terminal for completion status",
            root,
        )

    def test_shared_status_owner_rehydrates_durable_terminal_state(self) -> None:
        root = _read("flow-next-spec-completion-review/SKILL.md")
        block = _bash_fence_after(
            root, "### Step 0.5: Resume terminal status persistence before dispatch"
        )
        self.assertIn(
            '$FLOWCTL review-rounds attempts "$SPEC_ID"', block
        )
        self.assertIn("--review-type completion --json", block)
        self.assertLess(
            block.index("$FLOWCTL review-rounds attempts"),
            block.index("$FLOWCTL spec set-completion-review-status"),
        )

        cases = (
            (
                "ship-after-counter-reset",
                {
                    "attempts": [{"outcome": "verdict", "verdict": "SHIP"}],
                    "review_rounds": 0,
                    "review_rounds_cap": 4,
                },
                0,
                "ship",
                0,
                False,
            ),
            (
                "capped-needs-work",
                {
                    "attempts": [
                        {"outcome": "verdict", "verdict": "NEEDS_WORK"}
                    ],
                    "review_rounds": 4,
                    "review_rounds_cap": 4,
                },
                4,
                "needs_work",
                0,
                False,
            ),
            (
                "refunded-transport-failure",
                {
                    "attempts": [
                        {
                            "outcome": "transport_failure",
                            "verdict": None,
                        }
                    ],
                    "review_rounds": 3,
                    "review_rounds_cap": 4,
                },
                0,
                None,
                0,
                False,
            ),
            (
                "non-capped-needs-work",
                {
                    "attempts": [
                        {"outcome": "verdict", "verdict": "NEEDS_WORK"}
                    ],
                    "review_rounds": 3,
                    "review_rounds_cap": 4,
                },
                0,
                None,
                0,
                False,
            ),
            (
                "terminal-status-write-failure",
                {
                    "attempts": [{"outcome": "verdict", "verdict": "SHIP"}],
                    "review_rounds": 0,
                    "review_rounds_cap": 4,
                },
                0,
                "ship",
                2,
                True,
            ),
            (
                "newer-manual-reset-wins",
                {
                    "attempts": [{"outcome": "verdict", "verdict": "SHIP"}],
                    "review_rounds": 0,
                    "review_rounds_cap": 4,
                },
                0,
                None,
                0,
                False,
            ),
            (
                "already-persisted-ship-does-not-dispatch",
                {
                    "attempts": [{"outcome": "verdict", "verdict": "SHIP"}],
                    "review_rounds": 0,
                    "review_rounds_cap": 4,
                },
                0,
                None,
                0,
                False,
            ),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            flowctl_stub = temp / "flowctl-stub"
            flowctl_stub.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1 $2\" == \"review-rounds attempts\" ]]; then\n"
                "  printf '%s\\n' \"$ATTEMPTS_PAYLOAD\"\n"
                "elif [[ \"$1\" == \"show\" ]]; then\n"
                "  printf '%s\\n' \"$SPEC_STATE_PAYLOAD\"\n"
                "elif [[ \"$1 $2\" == "
                "\"spec set-completion-review-status\" ]]; then\n"
                "  printf '%s\\n' \"$*\" >> \"$STATUS_LOG\"\n"
                "  if [[ \"${STATUS_EXIT:-0}\" -ne 0 ]]; then\n"
                "    printf '%s\\n' 'status write failed'\n"
                "    exit \"$STATUS_EXIT\"\n"
                "  fi\n"
                "else\n"
                "  exit 9\n"
                "fi\n",
                encoding="utf-8",
            )
            flowctl_stub.chmod(0o755)

            for (
                name,
                payload,
                expected_exit,
                expected_status,
                status_exit,
                expects_retry,
            ) in cases:
                with self.subTest(name=name):
                    payload["attempts"][-1]["timestamp"] = (
                        "2026-07-29T10:00:00.000002Z"
                    )
                    spec_state = {
                        "completion_review_status": "unknown",
                        "completion_reviewed_at": "2026-07-29T09:00:00Z",
                    }
                    if name == "newer-manual-reset-wins":
                        spec_state["completion_reviewed_at"] = (
                            "2026-07-29T11:00:00Z"
                        )
                    elif name == "already-persisted-ship-does-not-dispatch":
                        spec_state["completion_review_status"] = "ship"
                        spec_state["completion_reviewed_at"] = (
                            "2026-07-29T10:00:00.000003Z"
                        )
                    status_log = temp / f"{name}.log"
                    env = os.environ.copy()
                    env.update(
                        {
                            "FLOWCTL": str(flowctl_stub),
                            "SPEC_ID": "fn-1",
                            "ATTEMPTS_PAYLOAD": json.dumps(payload),
                            "SPEC_STATE_PAYLOAD": json.dumps(spec_state),
                            "STATUS_LOG": str(status_log),
                            "STATUS_EXIT": str(status_exit),
                        }
                    )
                    result = subprocess.run(
                        [_bash_executable(), "-c", block],
                        env=env,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(
                        result.returncode,
                        expected_exit,
                        result.stdout + result.stderr,
                    )
                    writes = (
                        status_log.read_text(encoding="utf-8").splitlines()
                        if status_log.exists()
                        else []
                    )
                    if expected_status is None:
                        self.assertEqual(writes, [])
                    else:
                        self.assertEqual(len(writes), 1)
                        self.assertIn(
                            f"--status {expected_status} --json", writes[0]
                        )
                    self.assertEqual(
                        "<promise>RETRY</promise>" in result.stdout,
                        expects_retry,
                    )

    def test_terminal_checkpoint_restores_receipt_before_early_exit(self) -> None:
        root = _read("flow-next-spec-completion-review/SKILL.md")
        block = _bash_fence_after(
            root, "### Step 0.5: Resume terminal status persistence before dispatch"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            flowctl_stub = temp / "flowctl-stub"
            flowctl_stub.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1 $2\" == \"review-rounds attempts\" ]]; then\n"
                "  printf '%s\\n' \"$ATTEMPTS_PAYLOAD\"\n"
                "elif [[ \"$1\" == \"show\" ]]; then\n"
                "  printf '%s\\n' \"$SPEC_STATE_PAYLOAD\"\n"
                "else\n"
                "  exit 9\n"
                "fi\n",
                encoding="utf-8",
            )
            flowctl_stub.chmod(0o755)
            recovery = (
                temp
                / ".flow"
                / "tmp"
                / "completion-review-receipt-recovery-fn-1.json"
            )
            recovery.parent.mkdir(parents=True)
            payload = {
                "type": "completion_review",
                "id": "fn-1",
                "mode": "codex",
                "verdict": "SHIP",
                "review": "durable review",
                "attempt_timestamp": "2026-07-29T10:00:00Z",
            }
            recovery.write_text(json.dumps(payload), encoding="utf-8")
            receipt = temp / "receipts" / "completion.json"
            env = os.environ.copy()
            env.update(
                {
                    "FLOWCTL": flowctl_stub.as_posix(),
                    "SPEC_ID": "fn-1",
                    "BACKEND": "codex",
                    "REPO_ROOT": temp.as_posix(),
                    "REVIEW_RECEIPT_PATH": receipt.as_posix(),
                    "ATTEMPTS_PAYLOAD": json.dumps(
                        {
                            "attempts": [
                                {
                                    "outcome": "verdict",
                                    "verdict": "SHIP",
                                    "backend": "codex",
                                    "timestamp": "2026-07-29T10:00:00Z",
                                }
                            ],
                            "review_rounds": 0,
                            "review_rounds_cap": 4,
                        }
                    ),
                    "SPEC_STATE_PAYLOAD": json.dumps(
                        {
                            "completion_review_status": "ship",
                            "completion_reviewed_at": "2026-07-29T10:00:01Z",
                        }
                    ),
                }
            )
            result = subprocess.run(
                [_bash_executable(), "-c", block],
                cwd=temp,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERDICT=SHIP", result.stdout)
            self.assertNotIn("<promise>RETRY</promise>", result.stdout)
            self.assertEqual(json.loads(receipt.read_text(encoding="utf-8")), payload)
            self.assertFalse(recovery.exists())

            receipt.unlink()
            missing = subprocess.run(
                [_bash_executable(), "-c", block],
                cwd=temp,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(missing.returncode, 0)
            self.assertIn("<promise>RETRY</promise>", missing.stdout)
            self.assertNotIn("VERDICT=SHIP", missing.stdout)

            switch_env = env.copy()
            switch_env.pop("REVIEW_RECEIPT_PATH")
            switch_env["BACKEND"] = "codex"
            switch_env["ATTEMPTS_PAYLOAD"] = json.dumps(
                {
                    "attempts": [
                        {
                            "outcome": "verdict",
                            "verdict": "SHIP",
                            "backend": "rp",
                            "timestamp": "2026-07-29T10:00:00Z",
                        }
                    ],
                    "review_rounds": 0,
                    "review_rounds_cap": 4,
                }
            )
            rp_without_receipt = subprocess.run(
                [_bash_executable(), "-c", block],
                cwd=temp,
                env=switch_env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertIn("VERDICT=SHIP", rp_without_receipt.stdout)
            self.assertNotIn("<promise>RETRY</promise>", rp_without_receipt.stdout)

            switch_env["BACKEND"] = "rp"
            switch_env["ATTEMPTS_PAYLOAD"] = json.dumps(
                {
                    "attempts": [
                        {
                            "outcome": "verdict",
                            "verdict": "SHIP",
                            "backend": "host",
                            "timestamp": "2026-07-29T10:00:00Z",
                        }
                    ],
                    "review_rounds": 0,
                    "review_rounds_cap": 4,
                }
            )
            host_requires_receipt = subprocess.run(
                [_bash_executable(), "-c", block],
                cwd=temp,
                env=switch_env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertIn("<promise>RETRY</promise>", host_requires_receipt.stdout)
            self.assertNotIn("VERDICT=SHIP", host_requires_receipt.stdout)

            recovery.write_text(json.dumps(payload), encoding="utf-8")
            blocked_parent = temp / "blocked-parent"
            blocked_parent.write_text("not a directory", encoding="utf-8")
            copy_failure_env = env.copy()
            copy_failure_env["REVIEW_RECEIPT_PATH"] = (
                blocked_parent / "receipt.json"
            ).as_posix()
            copy_failure = subprocess.run(
                [_bash_executable(), "-c", block],
                cwd=temp,
                env=copy_failure_env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertIn("<promise>RETRY</promise>", copy_failure.stdout)
            self.assertNotIn("VERDICT=SHIP", copy_failure.stdout)
            self.assertTrue(recovery.exists())

            stale_payload = dict(payload)
            stale_payload["mode"] = "rp"
            stale_payload["attempt_timestamp"] = "2026-07-29T08:00:00Z"
            recovery.write_text(json.dumps(stale_payload), encoding="utf-8")
            stale_env = switch_env.copy()
            stale_env["BACKEND"] = "rp"
            stale_env["ATTEMPTS_PAYLOAD"] = json.dumps(
                {
                    "attempts": [
                        {
                            "outcome": "verdict",
                            "verdict": "SHIP",
                            "backend": "rp",
                            "timestamp": "2026-07-29T10:00:00Z",
                        }
                    ],
                    "review_rounds": 0,
                    "review_rounds_cap": 4,
                }
            )
            stale_result = subprocess.run(
                [_bash_executable(), "-c", block],
                cwd=temp,
                env=stale_env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertIn("VERDICT=SHIP", stale_result.stdout)
            self.assertNotIn("<promise>RETRY</promise>", stale_result.stdout)
            self.assertFalse(recovery.exists())

    def test_completion_backend_persists_recovery_and_receipt_before_status(
        self,
    ) -> None:
        source = (
            REPO / "plugins" / "flow-next" / "scripts" / "flowctl.py"
        ).read_text(encoding="utf-8")
        writer = _section(
            source,
            "def _write_backend_review_receipt(",
            "def _self_write_review_status(",
        )
        completion = _section(
            source,
            "def _backend_completion_review(",
            "def cmd_codex_impl_review(",
        )
        self.assertIn("completion-review-receipt-recovery-", source)
        self.assertIn('receipt_data["attempt_timestamp"]', writer)
        self.assertIn(
            "_completion_review_receipt_recovery_path(review_id)", writer
        )
        self.assertNotIn("recovery_path.unlink", writer)
        host = _read("flow-next-spec-completion-review/workflow-host.md")
        rp = _read("flow-next-spec-completion-review/workflow-rp.md")
        recovery = "completion-review-receipt-recovery-${SPEC_ID}.json"
        self.assertIn(recovery, host)
        self.assertIn(recovery, rp)
        self.assertLess(rp.index('cat > "$RECOVERY_TMP"'), rp.index(
            '--receipt "$REVIEW_RECEIPT_PATH"'
        ))
        self.assertIn('mktemp "${RECEIPT_RECOVERY}.tmp.XXXXXX"', rp)
        self.assertIn('if ! cat > "$RECOVERY_TMP"', rp)
        self.assertIn('mv -f "$RECOVERY_TMP" "$RECEIPT_RECOVERY"', rp)
        self.assertIn('--recovery "$RECEIPT_RECOVERY"', rp)
        self.assertNotIn(
            'cp "$RECEIPT_RECOVERY" "$REVIEW_RECEIPT_PATH"', rp
        )
        self.assertIn('--receipt "$RECEIPT_PATH"', host)
        self.assertIn('--recovery "$RECEIPT_RECOVERY"', host)
        self.assertLess(
            completion.index("_write_backend_review_receipt("),
            completion.index("_self_write_review_status("),
        )
        self.assertLess(
            completion.index("_self_write_review_status("),
            completion.index(
                "_completion_review_receipt_recovery_path(epic_id).unlink"
            ),
        )

    def test_rp_recorder_failure_cannot_be_swallowed_by_verdict_echo(self) -> None:
        rp = _read("flow-next-spec-completion-review/workflow-rp.md")
        block = _bash_fence_after(
            rp, "Redirect the review response to the literal response file"
        )
        block = block.replace("<spec-id>", "fn-1").replace("<suffix>", "test")
        self.assertIn('RECORD_EXIT=$?', block)
        self.assertLess(block.index('RECORD_EXIT=$?'), block.index('echo "VERDICT='))

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            flowctl_stub = temp / "flowctl-stub"
            flowctl_stub.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1 $2\" == \"rp chat-send\" ]]; then\n"
                "  printf '%s\\n' '<verdict>SHIP</verdict>'\n"
                "elif [[ \"$1 $2\" == \"review-rounds record\" ]]; then\n"
                "  printf '%s\\n' 'recorder failed'\n"
                "  exit 5\n"
                "else\n"
                "  exit 9\n"
                "fi\n",
                encoding="utf-8",
            )
            flowctl_stub.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "FLOWCTL": flowctl_stub.as_posix(),
                    "SPEC_ID": "fn-1",
                    "TMPDIR": temp.as_posix(),
                }
            )
            result = subprocess.run(
                [_bash_executable(), "-c", block],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                result.returncode, 5, result.stdout + result.stderr
            )
            self.assertIn("recorder failed", result.stdout)
            self.assertNotIn("VERDICT=", result.stdout)

    def test_host_completion_uses_shared_cap_attempt_lifecycle(self) -> None:
        host = _read("flow-next-spec-completion-review/workflow-host.md")
        self.assertIn(
            '$FLOWCTL review-rounds increment "$SPEC_ID" --kind plan --json',
            host,
        )
        self.assertIn(
            '$FLOWCTL review-rounds record "$SPEC_ID" --kind plan',
            host,
        )
        self.assertIn("--review-type completion --backend host", host)
        self.assertIn(
            '$FLOWCTL review-rounds reset "$SPEC_ID" --kind plan --json',
            host,
        )
        self.assertIn("(`REVIEW_ROUND == REVIEW_CAP`)", host)
        self.assertIn("<verdict>SHIP</verdict>", host)
        self.assertIn("<verdict>NEEDS_WORK</verdict>", host)
