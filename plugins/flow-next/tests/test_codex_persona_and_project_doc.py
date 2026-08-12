"""fn-187 R1/R2 — the codex reviewer must not inherit ambient instructions.

Issue #331: ``flowctl codex plan-review`` returned no verdict 13 times in a row.
Two contamination channels reach the ``codex exec`` reviewer subprocess:

- the host repo's auto-loaded project doc (``AGENTS.md``), which in a flow-next
  repo tells agents to drive reviews through the flow-next skills — so the
  reviewer re-dispatched at itself instead of reviewing (R2 suppresses it at the
  argv level, on BOTH the fresh and the resume path);
- with the codex plugin installed, the plugin's own coordinator skill catalogs
  ("Coordinator (NOT the reviewer)", "never self-declares a verdict") — no CLI
  knob exists, so the persona override asserts precedence in-prompt (R1).

These mock the spawn (``run_codex_exec`` / ``subprocess.run``) and drive the real
handlers against a real temp git repo + ``.flow`` tree — the codex mirror of
``test_cursor_review_commands.CursorPersonaOverrideAndCap``.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402


EPIC_ID = "fn-187-codex-demo"
TASK_ID = f"{EPIC_ID}.1"

REVIEW_OUTPUT = (
    "Reviewed the diff.\n\n"
    "<verdict>NEEDS_WORK</verdict>\n"
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


@contextlib.contextmanager
def _flow_repo():
    """Real temp git repo + ``.flow`` tree with a base..HEAD diff. chdir'd."""
    prev_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        _git(repo, "init", "-q")
        _git(repo, "config", "user.email", "t@t.t")
        _git(repo, "config", "user.name", "t")
        (repo / "src").mkdir()
        (repo / "src" / "mod.py").write_text(
            "def a(x):\n    return x\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "base")
        base = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

        flow = repo / ".flow"
        (flow / "specs").mkdir(parents=True)
        (flow / "tasks").mkdir(parents=True)
        (flow / "specs" / f"{EPIC_ID}.md").write_text(
            "# Demo spec\n\n## Acceptance Criteria\n\n- **R1:** do a thing\n",
            encoding="utf-8",
        )
        (flow / "specs" / f"{EPIC_ID}.json").write_text(
            json.dumps({"id": EPIC_ID, "title": "Demo", "status": "in_progress"}),
            encoding="utf-8",
        )
        (flow / "tasks" / f"{TASK_ID}.md").write_text(
            "---\nsatisfies: [R1]\n---\n\n## Description\n\nImplement a().\n",
            encoding="utf-8",
        )
        (repo / "src" / "mod.py").write_text(
            "def a(x):\n    return x + 1\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "change")

        os.chdir(repo)
        try:
            yield repo, base
        finally:
            os.chdir(prev_cwd)


def _fake_codex_exec():
    """A ``run_codex_exec`` stand-in recording the prompt it was handed."""
    calls: list[dict] = []

    def _runner(prompt, session_id=None, *, sandbox=None, spec=None,
                repo_root=None, resolution_out=None, resume_only=False):
        calls.append({"prompt": prompt, "session_id": session_id, "spec": spec})
        if resolution_out is not None:
            resolution_out["model"] = "gpt-5.5"
            resolution_out["effort"] = "high"
        return REVIEW_OUTPUT, "codex-sid-1", 0, ""

    _runner.calls = calls  # type: ignore[attr-defined]
    return _runner


class CodexPersonaOverride(unittest.TestCase):
    """fn-187 R1: the persona override reaches the codex reviewer on all kinds.

    Mirrors the cursor pins in ``test_cursor_review_commands`` — codex's
    ``needs_persona_override: False`` was never a decision, it preserved
    pre-registry behavior, and it is what let the coordinator-role contamination
    (route B) through.
    """

    def _run(self, repo: Path, base: str, kind: str):
        runner = _fake_codex_exec()
        receipt = repo / "receipt.json"
        common = dict(
            base=base, receipt=str(receipt), json=False, spec=None,
            sandbox="read-only", force=False,
        )
        if kind == "impl":
            args = argparse.Namespace(task=TASK_ID, focus=None, **common)
            fn = flowctl.cmd_codex_impl_review
        elif kind == "plan":
            args = argparse.Namespace(epic=EPIC_ID, files="src/mod.py", **common)
            fn = flowctl.cmd_codex_plan_review
        else:
            args = argparse.Namespace(epic=EPIC_ID, **common)
            fn = flowctl.cmd_codex_completion_review
        with mock.patch.object(flowctl, "run_codex_exec", runner):
            with contextlib.redirect_stdout(io.StringIO()):
                fn(args)
        self.assertTrue(runner.calls, f"no codex dispatch captured for {kind}")
        return runner.calls[0]["prompt"]

    def test_registry_flag_is_on(self):
        self.assertTrue(
            flowctl.BACKEND_REGISTRY["codex"]["needs_persona_override"]
        )

    def test_impl_review_prompt_carries_persona_override(self):
        with _flow_repo() as (repo, base):
            sent = self._run(repo, base, "impl")
        self.assertIn("PERSONA OVERRIDE", sent)
        self.assertIn("superseded", sent)

    def test_plan_review_prompt_carries_persona_override(self):
        with _flow_repo() as (repo, base):
            sent = self._run(repo, base, "plan")
        self.assertIn("PERSONA OVERRIDE", sent)
        self.assertIn("superseded", sent)

    def test_completion_review_prompt_carries_persona_override(self):
        with _flow_repo() as (repo, base):
            sent = self._run(repo, base, "completion")
        self.assertIn("PERSONA OVERRIDE", sent)
        self.assertIn("superseded", sent)

    def test_persona_leads_the_prompt(self):
        """Precedence is positional: the override must arrive FIRST."""
        with _flow_repo() as (repo, base):
            sent = self._run(repo, base, "impl")
        self.assertTrue(sent.startswith("## PERSONA OVERRIDE"), sent[:80])


class CodexProjectDocSuppression(unittest.TestCase):
    """fn-187 R2: ``-c project_doc_max_bytes=0`` on BOTH codex argv paths.

    Fresh dispatch and ``exec resume`` build separate argv; the reporter measured
    the flag fixing route A on the fresh path, and a resumed reviewer re-reads the
    project doc on every turn — so a resume-only miss would re-open the failure on
    the second round of every re-review.
    """

    def _capture(self, **kwargs) -> list[list[str]]:
        seen: list[list[str]] = []

        def fake_run(cmd, **rk):
            seen.append(list(cmd))
            return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

        with mock.patch.object(flowctl, "require_codex",
                               return_value="/usr/local/bin/codex"), \
                mock.patch.object(flowctl.subprocess, "run", side_effect=fake_run):
            flowctl.run_codex_exec("p", repo_root=Path("."), **kwargs)
        return seen

    def test_fresh_dispatch_suppresses_the_project_doc(self):
        cmds = self._capture(sandbox="read-only")
        fresh = [c for c in cmds if len(c) > 1 and c[1] == "exec" and "resume" not in c]
        self.assertTrue(fresh, f"no fresh codex exec captured: {cmds}")
        for cmd in fresh:
            self.assertIn("project_doc_max_bytes=0", cmd)
            self.assertEqual(cmd[cmd.index("project_doc_max_bytes=0") - 1], "-c")

    def test_resume_dispatch_suppresses_the_project_doc(self):
        cmds = self._capture(sandbox="read-only", session_id="sid-1")
        resumed = [c for c in cmds if len(c) > 2 and c[1] == "exec" and c[2] == "resume"]
        self.assertTrue(resumed, f"no codex exec resume captured: {cmds}")
        for cmd in resumed:
            self.assertIn("project_doc_max_bytes=0", cmd)
            self.assertEqual(cmd[cmd.index("project_doc_max_bytes=0") - 1], "-c")


if __name__ == "__main__":
    unittest.main(verbosity=2)
