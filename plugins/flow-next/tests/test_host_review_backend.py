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
            spec = flowctl.parse_backend_spec_lenient("none:not-a-model", warn=True)
        self.assertIsNotNone(spec, "legacy lenience for non-host backends must not change")
        self.assertEqual(spec.backend, "none")


class TestHostReviewWorkflowRouting(unittest.TestCase):
    """Host mechanics stay behind the selected reference and own no status."""

    def test_host_workflow_is_reachable_from_the_skill_entry(self) -> None:
        for skill, chain in (
            ("flow-next-impl-review", ("SKILL.md", "other-paths.md")),
            ("flow-next-spec-completion-review", ("SKILL.md",)),
        ):
            with self.subTest(skill=skill):
                for parent, child in zip(chain, chain[1:] + ("workflow-host.md",), strict=True):
                    self.assertIn(f"]({child})", _read(f"{skill}/{parent}"))

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
                ("retry", "unknown", 0, "RETRY: no verdict"),
                ("ship", "ship", 0, "VERDICT=SHIP"),
                ("superseded", "ship", 0, "COMPLETION_REVIEW_STATUS=ship"),
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

    def test_recorder_failure_stops_the_host_finalize_fence(self) -> None:
        """A failed `review-rounds record` exits before any verdict handling."""
        for rel, env_extra in (
            ("flow-next-plan-review/workflow-host.md", {"SPEC_ID": "fn-1"}),
            ("flow-next-impl-review/workflow-host.md", {"TASK_ID": "fn-1.1"}),
            ("flow-next-spec-completion-review/workflow-host.md", {"SPEC_ID": "fn-1"}),
        ):
            with self.subTest(workflow=rel), tempfile.TemporaryDirectory() as temp_dir:
                block = _bash_fence_containing(_read(rel), "RECORD_EXIT=$?").replace(
                    "<count printed by Step 0>", "0"
                )
                self.assertLess(
                    block.index("RECORD_EXIT=$?"),
                    block.rindex('"$VERDICT" == "NEEDS_HUMAN"'),
                )
                temp = Path(temp_dir)
                flowctl_stub = temp / "flowctl-stub"
                flowctl_stub.write_text(
                    "#!/usr/bin/env bash\n"
                    "if [[ \"$1 $2\" == \"review-rounds record\" ]]; then\n"
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
                        # A swallowed failure would reach the escalation (exit 4).
                        "VERDICT": "NEEDS_HUMAN",
                        "TMPDIR": temp.as_posix(),
                        **env_extra,
                    }
                )
                result = subprocess.run(
                    [_bash_executable(), "-c", block + "\necho AFTER_RECORD"],
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(
                    result.returncode, 5, result.stdout + result.stderr
                )
                self.assertIn("recorder failed", result.stdout)
                self.assertNotIn("ESCALATE", result.stderr)
                self.assertNotIn("AFTER_RECORD", result.stdout)


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
