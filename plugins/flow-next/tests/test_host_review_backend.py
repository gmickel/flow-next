"""Unit tests for the host review-backend sentinel (fn-123 R5 / task .3).

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_host_review_backend -q

``host`` is a NON-EXECUTABLE selection sentinel: review runs as a host-native
fresh-context subagent (skill-owned). flowctl only registers/parses it —
no model/effort on the string, no run_exec hook, never a subprocess path.
The model is named on the reviewer tier of the AGENTS.md model-routing block.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
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


def _bash_fence_containing(text: str, needle: str) -> str:
    """The first ```bash fence whose body contains `needle`."""
    for body in re.findall(r"```bash\n(.*?)```", text, re.S):
        if needle in body:
            return body
    raise AssertionError(f"no bash fence contains {needle!r}")


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

    def test_host_takes_no_model_axis(self) -> None:
        # The model is named on the AGENTS.md routing block, never on the
        # backend string - so host carries no model/effort axis at all.
        self.assertIsNone(BACKEND_REGISTRY["host"].get("default_model"))
        self.assertIsNone(BACKEND_REGISTRY["host"].get("default_effort"))


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
                "**For host backend:**",
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

    def test_completion_status_is_journaled_before_host_or_rp_terminal(self) -> None:
        root = _read("flow-next-spec-completion-review/SKILL.md")
        host = _read("flow-next-spec-completion-review/workflow-host.md")
        rp = _read("flow-next-spec-completion-review/workflow-rp.md")
        work = _read("flow-next-work/phases.md")
        command = "$FLOWCTL spec set-completion-review-status"
        self.assertNotIn(command, root)
        self.assertIn("$FLOWCTL review-rounds resume-terminal", root)
        self.assertIn("--status-target completion", host)
        self.assertIn("--status-target completion", rp)
        self.assertEqual(
            work.count(command),
            1,
            "work's only completion-status write is the 3g policy-skip CAS",
        )
        cas_write = command + " <spec-id> --status not_required --if-current unknown"
        self.assertIn(cas_write, work, "the 3g skip write must be the atomic CAS form")
        gate_index = work.index("### 3g. Completion Review Gate")
        self.assertGreater(
            work.index(command),
            gate_index,
            "work's single status write must live in the 3g gate",
        )
        for verdict in ("ship", "needs_work", "needs_human"):
            self.assertNotIn(
                f"{command} <spec-id> --status {verdict}",
                work,
                "work must never write a verdict completion status",
            )
        self.assertIn("NEEDS_HUMAN", root)
        self.assertIn("needs_human", host)
        self.assertIn("NEEDS_HUMAN", rp)
        self.assertIn("ESCALATE: reviewer requested human review", host)

    def test_host_needs_human_fences_attach_before_exit(self) -> None:
        for skill in (
            "flow-next-plan-review",
            "flow-next-impl-review",
            "flow-next-spec-completion-review",
        ):
            with self.subTest(skill=skill):
                host = _read(f"{skill}/workflow-host.md")
                record_at = host.index("review-rounds record")
                attach_at = host.index("--attach", record_at)
                terminal_at = host.index(
                    "ESCALATE: reviewer requested human review", attach_at
                )
                self.assertLess(record_at, attach_at)
                self.assertLess(attach_at, terminal_at)
                if skill != "flow-next-impl-review":
                    self.assertIn("--status-target", host[record_at:attach_at])

    def test_terminal_checkpoint_routes_command_actions(self) -> None:
        block = _bash_fence_after(
            _read("flow-next-spec-completion-review/SKILL.md"),
            "### Step 0.5: Resume terminal status persistence before dispatch",
        )
        with tempfile.TemporaryDirectory() as temp:
            stub = Path(temp) / "flowctl"
            stub.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$PAYLOAD"\n')
            stub.chmod(0o755)
            for action, status, code, marker in (
                ("continue", "unknown", 0, "CONTINUED"),
                ("retry", "unknown", 0, "<promise>RETRY</promise>"),
                ("ship", "ship", 0, "VERDICT=SHIP"),
                ("superseded", "ship", 0, "COMPLETION_REVIEW_STATUS=ship"),
                # ralph.sh greps this exact line for its NEEDS_HUMAN fast path.
                ("escalate", "needs_human", 4, "ESCALATE: reviewer requested human review"),
                ("escalate", "needs_work", 4, "ESCALATE: completion-review did not converge"),
                ("bad-action", "unknown", 1, "Unknown terminal review action"),
            ):
                with self.subTest(action=action):
                    run = subprocess.run(
                        [_bash_executable(), "-c", block + '\necho CONTINUED'],
                        env={**os.environ, "FLOWCTL": str(stub), "SPEC_ID": "fn-1",
                             "PAYLOAD": json.dumps({"action": action, "status": status, "exit": code})},
                        capture_output=True, text=True,
                    )
                    self.assertEqual(run.returncode, code, run.stderr)
                    self.assertIn(marker, run.stdout + run.stderr)

    def test_completion_backend_persists_recovery_and_receipt_before_status(
        self,
    ) -> None:
        source = (
            REPO / "plugins" / "flow-next" / "scripts" / "flowctl.py"
        ).read_text(encoding="utf-8")
        payload_builder = _section(
            source,
            "def _backend_review_receipt_payload(",
            "def _publish_review_receipt_from_journal(",
        )
        publisher = _section(
            source,
            "def _publish_review_receipt_from_journal(",
            "def _write_backend_review_receipt(",
        )
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
        self.assertIn('receipt_data["attempt_timestamp"]', payload_builder)
        self.assertIn(
            "_completion_review_receipt_recovery_path(review_id)", writer
        )
        # PR #290 bot P1: the journaled publish keeps the same pre-pointer
        # recovery copy the unjournaled direct writer wrote.
        self.assertIn("_completion_review_receipt_recovery_path(", publisher)
        self.assertNotIn("recovery_path.unlink", writer)
        host = _read("flow-next-spec-completion-review/workflow-host.md")
        rp = _read("flow-next-spec-completion-review/workflow-rp.md")
        recovery = "completion-review-receipt-recovery-${SPEC_ID}.json"
        # fn-257 R5: the host publishes through `attach`, whose record journal
        # is the recovery source; it never hand-writes a recovery copy.
        self.assertNotIn(recovery, host)
        # fn-159.7 review r1: the RP transport no longer hand-rolls a /tmp
        # recovery copy. `review-rounds record` journals the exact intended
        # payload under .flow/review-runs/ BEFORE the receipt advances, which
        # is the same guarantee with a durable, identity-bound artifact.
        self.assertNotIn('RECOVERY_TMP', rp)
        self.assertNotIn('--recovery "$RECEIPT_RECOVERY"', rp)
        self.assertLess(
            rp.index('--receipt-payload-file "$RECEIPT_INPUT"'),
            rp.index('review-findings attach'),
        )
        self.assertIn('--receipt-target "$REVIEW_RECEIPT_PATH"', rp)
        self.assertIn('--reservation-id "$RESERVATION_ID"', rp)
        self.assertNotIn(
            'cp "$RECEIPT_RECOVERY" "$REVIEW_RECEIPT_PATH"', rp
        )
        # fn-159.7: the host fence assembles receipt inputs BEFORE record
        # (record journals them); attach only publishes by reservation id.
        self.assertIn('--receipt-target "$RECEIPT_PATH"', host)
        self.assertIn('--receipt-payload-file "$RECEIPT_INPUT"', host)
        self.assertIn('--reservation-id "$RESERVATION_ID"', host)
        self.assertIn('--receipt "$RECEIPT_PATH"', host)
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
        # PR #290 bot r2: both the terminal status write and the recovery
        # cleanup are GATED on publication succeeding — a failed publish must
        # leave the wedge-free state the replay gate recovers from.
        self.assertIn("receipt_published = _write_backend_review_receipt(", completion)
        self.assertIn("if receipt_published:", completion)
        self.assertLess(
            completion.index("if receipt_published:"),
            completion.index("_self_write_review_status("),
        )
        # The impl handler writes no terminal review status at all, so there
        # is nothing to gate there.
        impl = _section(
            source,
            "def _backend_impl_review(",
            "def _current_review_rounds(",
        )
        self.assertNotIn("_self_write_review_status(", impl)

    def test_rp_recorder_failure_cannot_be_swallowed_by_verdict_echo(self) -> None:
        rp = _read("flow-next-spec-completion-review/workflow-rp.md")
        # fn-159.7 review r1: recording moved into the Phase 4 finalize fence
        # so the receipt inputs are assembled BEFORE record.
        block = _bash_fence_after(rp, "This is the single recorder fence")
        block = block.replace("<spec-id>", "fn-1").replace("<suffix>", "test")
        self.assertIn('RECORD_EXIT=$?', block)
        self.assertLess(block.index('RECORD_EXIT=$?'), block.index('echo "VERDICT='))

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            (temp / "flow-completion-review-snapshot-fn-1-test.env").write_text(
                "REVIEW_HEAD_SHA=deadbeef\nREVIEW_BASE_SHA=deadbeef\n",
                encoding="utf-8",
            )
            (temp / "flow-completion-review-dispatch-result-fn-1-test.env").write_text(
                "RP_EXIT=0\nVERDICT=SHIP\n", encoding="utf-8",
            )
            (temp / "flow-completion-review-reservation-fn-1-test.json").write_text(
                '{"reservation_id":"reservation-test"}', encoding="utf-8",
            )
            (temp / "flow-completion-review-response-fn-1-test.md").write_text(
                "<verdict>SHIP</verdict>\n", encoding="utf-8",
            )
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
            '$FLOWCTL review-rounds increment "$SPEC_ID" --kind plan',
            host,
        )
        # fn-159.7: the reserve carries the completion artifact hash inputs.
        self.assertIn(
            '--review-type completion --base "$REVIEW_BASE_SHA" --head "$REVIEW_HEAD_SHA" --json',
            host,
        )
        self.assertIn(
            '$FLOWCTL review-rounds record "$SPEC_ID" --kind plan',
            host,
        )
        self.assertIn("--review-type completion --backend host", host)
        # fn-159 R9: SHIP reset is system-owned inside `record`; the explicit
        # reset verb is a human-only recovery tool and must NOT appear as an
        # autonomous host-fence command.
        self.assertNotIn(
            '$FLOWCTL review-rounds reset "$SPEC_ID" --kind plan --json',
            host,
        )
        self.assertIn(
            "Never issue `review-rounds reset` autonomously", host
        )
        self.assertIn("(`REVIEW_ROUND == REVIEW_CAP`)", host)
        self.assertIn("<verdict>SHIP</verdict>", host)
        self.assertIn("<verdict>NEEDS_WORK</verdict>", host)


class TestHostStandaloneImplReview(unittest.TestCase):
    """fn-257 R2: a standalone host impl-review reserves nothing and attaches directly."""

    def test_host_reservation_refuses_empty_diff_over_nonempty_range(self) -> None:
        for rel, env_extra in (
            ("flow-next-impl-review/workflow-host.md", {"TASK_ID": "fn-1.1"}),
            ("flow-next-spec-completion-review/workflow-host.md", {"SPEC_ID": "fn-1"}),
        ):
            with self.subTest(workflow=rel), tempfile.TemporaryDirectory() as temp_dir:
                reserve = _bash_fence_containing(_read(rel), "review-rounds increment")
                temp = Path(temp_dir)
                git = ["git", "-C", str(temp), "-c", "user.email=t@t.t", "-c", "user.name=t"]
                subprocess.run([*git, "init", "-q"], check=True)
                subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "base"], check=True)
                base = subprocess.run([*git, "rev-parse", "HEAD"], check=True,
                                      capture_output=True, text=True).stdout.strip()
                subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "no-op"], check=True)
                log = temp / "flowctl.log"
                stub = temp / "flowctl-stub"
                stub.write_text(f'#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "{log.as_posix()}"\necho "{{}}"\n',
                                encoding="utf-8")
                stub.chmod(0o755)
                env = os.environ.copy()
                env.update({"FLOWCTL": stub.as_posix(), "BASE_COMMIT": base, "TMPDIR": temp.as_posix(), **env_extra})
                result = subprocess.run([_bash_executable(), "-c", reserve], cwd=temp, env=env,
                                        text=True, capture_output=True, check=False)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("empty diff over a non-empty range", result.stderr)
                calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
                self.assertFalse(any("increment" in call for call in calls), calls)

    def test_standalone_skips_reservation_and_attaches_directly(self) -> None:
        host = _read("flow-next-impl-review/workflow-host.md")
        reserve = _bash_fence_after(host, "### Convergence reservation and recovery fence")
        record = _bash_fence_after(host, "On a fan-out round this runs ONCE")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            git = ["git", "-C", str(temp), "-c", "user.email=t@t.t", "-c", "user.name=t"]
            subprocess.run([*git, "init", "-q"], check=True)
            subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "base"], check=True)
            head = subprocess.run(
                [*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
            ).stdout.strip()
            log = temp / "flowctl.log"
            stub = temp / "flowctl-stub"
            stub.write_text(
                f'#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "{log.as_posix()}"\necho "{{}}"\n',
                encoding="utf-8",
            )
            stub.chmod(0o755)
            env = os.environ.copy()
            env.update({
                "FLOWCTL": stub.as_posix(), "TASK_ID": "", "BASE_COMMIT": head,
                "TMPDIR": temp.as_posix(), "VERDICT": "SHIP",
                "RECEIPT_INPUT": "in.json", "RECEIPT_PATH": "receipt.json",
                "REVIEW_OUTPUT_FILE": "review.md",
                "REVIEW_BASE_SHA": head, "REVIEW_HEAD_SHA": head,
            })
            for block in (reserve, record):
                result = subprocess.run(
                    [_bash_executable(), "-c", block], cwd=temp, env=env,
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            calls = log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(calls), 1, calls)
            self.assertTrue(calls[0].startswith("review-findings attach --input in.json"))
            self.assertIn(f"--base {head} --head {head}", calls[0])

            # A failed attach is the run's failure, never a silent exit 0.
            stub.write_text("#!/usr/bin/env bash\nexit 7\n", encoding="utf-8")
            result = subprocess.run(
                [_bash_executable(), "-c", record], cwd=temp, env=env,
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
