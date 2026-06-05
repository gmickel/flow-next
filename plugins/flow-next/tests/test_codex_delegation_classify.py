"""Deterministic classification + scoped-rollback tests for Codex
implementation-delegation (fn-55.4, R5 + R6 + R8).

Two executable surfaces live in ``flowctl.py`` (and its byte-identical dogfood
copy ``.flow/bin/flowctl.py``):

  * ``flowctl codex classify-result --result <f> --exit <n> --json``
      → ``{class, status, action, scoped_paths, valid_schema}`` for the lifted
        5-row table + malformed/missing JSON.
  * ``flowctl codex rollback-plan --preexisting-untracked-file <pre>
        --post-untracked-file <post> --json``
      → ``{rollback_paths, rejected}`` — the cleanup set = ``post − pre`` over
        ``git ls-files --others --exclude-standard -z`` (NUL-delimited)
        snapshots, sanitized to repo-relative FILE paths (absolute / ``..`` /
        empty / ``.`` / bare-directory / ``.flow/**`` rejected).

The classifier + rollback computations are PURE (no git, no model), so a
mock-codex fixture (``tests/fixtures/mock-codex/mock-codex.py``) emits canned
``result-batch-*.json`` + exit codes for every row, driving the helpers
deterministically.

This file also locks the prose contract authored in this task:
  * the ``references/codex-delegation.md`` orchestration/safety stub is FILLED;
  * ``worker.md`` carries the HEAD-unchanged assertion + ``.flow/`` integrity +
    clean-baseline-excludes-.flow + scoped-rollback mechanics;
  * the two flowctl copies are byte-identical AND both carry the new helpers.
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
from typing import Any, Optional


HERE = Path(__file__).resolve()
TESTS_DIR = HERE.parent
PLUGIN_DIR = TESTS_DIR.parent
REPO_ROOT = PLUGIN_DIR.parent.parent
FLOWCTL_PY = PLUGIN_DIR / "scripts" / "flowctl.py"
DOGFOOD_FLOWCTL_PY = REPO_ROOT / ".flow" / "bin" / "flowctl.py"
FLOWCTL_BIN = REPO_ROOT / ".flow" / "bin" / "flowctl"
MOCK_CODEX = TESTS_DIR / "fixtures" / "mock-codex" / "mock-codex.py"
REFERENCE_MD = PLUGIN_DIR / "skills" / "flow-next-work" / "references" / "codex-delegation.md"
WORKER_MD = PLUGIN_DIR / "agents" / "worker.md"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_classify_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _run_mock_codex(*args: str, cwd: Optional[Path] = None) -> int:
    """Run the mock-codex fixture; return its exit code (the codex exit)."""
    proc = subprocess.run(
        [sys.executable, str(MOCK_CODEX), *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    return proc.returncode


# ── Pure classifier (in-process) ─────────────────────────────────────────────


class ClassifyResultPureTestCase(unittest.TestCase):
    """Exercise the pure ``classify_delegation_result`` over the 5 rows."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.flowctl = _load_flowctl()

    def _valid(self, status: str, files=None) -> dict:
        return {
            "status": status,
            "files_modified": files or [],
            "issues": [],
            "summary": "s",
            "verification_summary": "v",
        }

    def test_row_completed_exit0_is_success_commit(self) -> None:
        r = self.flowctl.classify_delegation_result(
            0, self._valid("completed", ["a.py"]), True
        )
        self.assertEqual(r["class"], "success")
        self.assertEqual(r["status"], "completed")
        self.assertEqual(r["action"], "commit")
        self.assertEqual(r["scoped_paths"], ["a.py"])
        self.assertTrue(r["valid_schema"])

    def test_row_partial_exit0_is_partial_finish_locally(self) -> None:
        r = self.flowctl.classify_delegation_result(0, self._valid("partial"), True)
        self.assertEqual(r["class"], "partial")
        self.assertEqual(r["action"], "finish_locally")

    def test_row_failed_exit0_is_task_failure_rollback(self) -> None:
        r = self.flowctl.classify_delegation_result(0, self._valid("failed"), True)
        self.assertEqual(r["class"], "task_failure")
        self.assertEqual(r["action"], "rollback")

    def test_row_malformed_exit0_is_task_failure_rollback(self) -> None:
        # result None / schema-invalid on exit 0 → task failure.
        r = self.flowctl.classify_delegation_result(0, None, False)
        self.assertEqual(r["class"], "task_failure")
        self.assertEqual(r["action"], "rollback")
        self.assertIsNone(r["status"])
        self.assertFalse(r["valid_schema"])

    def test_row_cli_failure_exit_nonzero_wins(self) -> None:
        # Even a perfectly-valid `completed` result is overridden by exit != 0.
        r = self.flowctl.classify_delegation_result(
            1, self._valid("completed"), True
        )
        self.assertEqual(r["class"], "cli_failure")
        self.assertEqual(r["action"], "rollback_and_disable")

    def test_cli_failure_with_missing_result(self) -> None:
        # exit != 0 AND no result → still cli_failure (CLI failure dominates).
        r = self.flowctl.classify_delegation_result(2, None, False)
        self.assertEqual(r["class"], "cli_failure")
        self.assertEqual(r["action"], "rollback_and_disable")
        self.assertEqual(r["scoped_paths"], [])

    def test_schema_validator_rejects_bad_status(self) -> None:
        bad = self._valid("done")  # not in enum
        self.assertFalse(self.flowctl._result_is_valid_schema(bad))

    def test_schema_validator_rejects_missing_key(self) -> None:
        bad = {"status": "completed", "files_modified": [], "issues": []}
        self.assertFalse(self.flowctl._result_is_valid_schema(bad))

    def test_schema_validator_accepts_full(self) -> None:
        self.assertTrue(self.flowctl._result_is_valid_schema(self._valid("completed")))


# ── classify-result via the mock-codex fixture + live CLI ────────────────────


class ClassifyResultViaMockCodexTestCase(unittest.TestCase):
    """Drive classify-result with the mock-codex fixture's canned outputs,
    invoked through the LIVE ``.flow/bin/flowctl`` (proves the dogfood copy
    resolves the new subcommand)."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _mock_then_classify(self, row: str) -> dict:
        out = self.tmp / "result-batch-1.json"
        exit_code = _run_mock_codex("--row", row, "--out", str(out), cwd=self.tmp)
        proc = subprocess.run(
            [
                str(FLOWCTL_BIN),
                "codex",
                "classify-result",
                "--result",
                str(out),
                "--exit",
                str(exit_code),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_live_completed(self) -> None:
        r = self._mock_then_classify("completed")
        self.assertEqual(r["class"], "success")
        self.assertEqual(r["action"], "commit")

    def test_live_partial(self) -> None:
        r = self._mock_then_classify("partial")
        self.assertEqual(r["class"], "partial")
        self.assertEqual(r["action"], "finish_locally")

    def test_live_failed(self) -> None:
        r = self._mock_then_classify("failed")
        self.assertEqual(r["class"], "task_failure")
        self.assertEqual(r["action"], "rollback")

    def test_live_malformed(self) -> None:
        r = self._mock_then_classify("malformed")
        self.assertEqual(r["class"], "task_failure")
        self.assertFalse(r["valid_schema"])

    def test_live_missing(self) -> None:
        r = self._mock_then_classify("missing")
        self.assertEqual(r["class"], "task_failure")
        self.assertFalse(r["valid_schema"])

    def test_live_cli_failure(self) -> None:
        r = self._mock_then_classify("cli_failure")
        self.assertEqual(r["class"], "cli_failure")
        self.assertEqual(r["action"], "rollback_and_disable")


# ── rollback-plan (pure + path sanitization) ─────────────────────────────────


class RollbackPlanTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.flowctl = _load_flowctl()

    def test_cleanup_set_is_post_minus_pre(self) -> None:
        pre = {"pre.txt"}
        post = {"pre.txt", "new.py"}
        plan = self.flowctl.rollback_plan(pre, post)
        # pre-existing untracked file is NOT in the cleanup set.
        self.assertEqual(plan["rollback_paths"], ["new.py"])
        self.assertEqual(plan["rejected"], [])

    def test_nested_directory_file_is_kept(self) -> None:
        # A file inside a newly-created nested dir is listed individually by the
        # -z snapshot and must be cleaned (git clean -fd removes the empty dir).
        plan = self.flowctl.rollback_plan(set(), {"a/b/c/deep.py"})
        self.assertIn("a/b/c/deep.py", plan["rollback_paths"])

    def test_whitespace_and_odd_char_paths_kept(self) -> None:
        post = {"has space.txt", "weird\tname.py", "a..b.txt"}
        plan = self.flowctl.rollback_plan(set(), post)
        for p in post:
            self.assertIn(p, plan["rollback_paths"], p)
        self.assertEqual(plan["rejected"], [])

    def test_rejects_absolute_path(self) -> None:
        plan = self.flowctl.rollback_plan(set(), {"/etc/passwd"})
        self.assertEqual(plan["rollback_paths"], [])
        self.assertEqual(len(plan["rejected"]), 1)
        self.assertIn("absolute path", plan["rejected"][0])

    def test_rejects_dotdot_traversal(self) -> None:
        plan = self.flowctl.rollback_plan(set(), {"../escape.txt", "a/../b.txt"})
        self.assertEqual(plan["rollback_paths"], [])
        self.assertEqual(len(plan["rejected"]), 2)
        self.assertTrue(all(".. traversal" in r for r in plan["rejected"]))

    def test_rejects_bare_directory(self) -> None:
        plan = self.flowctl.rollback_plan(set(), {"emptydir/"})
        self.assertEqual(plan["rollback_paths"], [])
        self.assertIn("bare directory", plan["rejected"][0])

    def test_rejects_dot_and_empty(self) -> None:
        plan = self.flowctl.rollback_plan(set(), {".", "  "})
        self.assertEqual(plan["rollback_paths"], [])
        self.assertEqual(len(plan["rejected"]), 2)

    def test_rejects_flow_paths(self) -> None:
        # .flow/ is host-owned (plan-sync, specs, tasks) — NEVER cleaned.
        post = {".flow/tasks/x.md", ".flow/config.json", ".flow", "src/ok.py"}
        plan = self.flowctl.rollback_plan(set(), post)
        self.assertEqual(plan["rollback_paths"], ["src/ok.py"])
        self.assertEqual(len(plan["rejected"]), 3)
        self.assertTrue(all("host-owned" in r for r in plan["rejected"]))

    def test_dotfile_not_under_flow_is_kept(self) -> None:
        # A dotfile that is NOT .flow must not be wrongly rejected.
        plan = self.flowctl.rollback_plan(set(), {".flowery.txt", ".flowrc"})
        self.assertEqual(sorted(plan["rollback_paths"]), [".flowery.txt", ".flowrc"])

    def test_sanitize_filename_with_dotdot_substring_kept(self) -> None:
        # "a..b.txt" contains ".." as a substring but is NOT a traversal segment.
        self.assertEqual(self.flowctl.sanitize_rollback_path("a..b.txt"), "a..b.txt")
        self.assertIsNone(self.flowctl.sanitize_rollback_path("../x"))


# ── rollback-plan via NUL-delimited snapshots through the live CLI ───────────


class RollbackPlanLiveCliTestCase(unittest.TestCase):
    """End-to-end: build pre/post NUL-delimited snapshots (matching
    ``git ls-files --others --exclude-standard -z`` shape) and run the live
    ``.flow/bin/flowctl codex rollback-plan``."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _snapshot(self, name: str, paths: list) -> Path:
        p = self.tmp / name
        # -z is NUL-delimited WITH a trailing NUL after each entry.
        data = b"".join(x.encode("utf-8") + b"\x00" for x in paths)
        p.write_bytes(data)
        return p

    def _run(self, pre_paths: list, post_paths: list) -> dict:
        pre = self._snapshot("pre.txt", pre_paths)
        post = self._snapshot("post.txt", post_paths)
        proc = subprocess.run(
            [
                str(FLOWCTL_BIN),
                "codex",
                "rollback-plan",
                "--repo-root",
                str(self.tmp),
                "--preexisting-untracked-file",
                str(pre),
                "--post-untracked-file",
                str(post),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_cli_failure_cleanup_works_without_result_json(self) -> None:
        # The cleanup set is derived from snapshots, NOT files_modified, so it
        # still cleans new untracked files even when the result JSON is absent
        # (CLI-failure / malformed). pre is empty here.
        plan = self._run([], ["codex-made.py", "dir/also.py"])
        self.assertEqual(
            sorted(plan["rollback_paths"]), ["codex-made.py", "dir/also.py"]
        )

    def test_empty_pre_snapshot_treated_as_empty(self) -> None:
        plan = self._run([], ["only.py"])
        self.assertEqual(plan["rollback_paths"], ["only.py"])

    def test_full_mix_via_cli(self) -> None:
        plan = self._run(
            ["pre.py"],
            [
                "pre.py",
                "new.py",
                "nest/deep.py",
                "has space.txt",
                "/abs.txt",
                "../esc.txt",
                ".flow/tasks/t.md",
                "bare/",
            ],
        )
        self.assertEqual(
            sorted(plan["rollback_paths"]),
            ["has space.txt", "nest/deep.py", "new.py"],
        )
        self.assertEqual(len(plan["rejected"]), 4)


# ── Mock-codex creates real untracked files → snapshot diff cleans them ──────


class RollbackScopeViaMockCodexTestCase(unittest.TestCase):
    """The mock-codex fixture writes real untracked files; a pre/post snapshot
    diff (computed by ``rollback_plan``) yields ONLY the codex-created files —
    never a pre-existing untracked file, never a ``.flow/`` path."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.flowctl = _load_flowctl()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _ls_untracked(self) -> set:
        """Mimic ``git ls-files --others --exclude-standard -z`` over the temp
        dir WITHOUT requiring a git repo: just walk the tree (the test cares
        about the set-diff semantics, not git itself)."""
        out = set()
        for p in self.tmp.rglob("*"):
            if p.is_file():
                out.add(p.relative_to(self.tmp).as_posix())
        return out

    def test_only_codex_created_files_in_cleanup(self) -> None:
        # Pre-existing untracked file (NOT created by codex).
        (self.tmp / "preexisting.txt").write_text("user file\n", encoding="utf-8")
        # Host-owned .flow file that must never be cleaned.
        (self.tmp / ".flow" / "tasks").mkdir(parents=True)
        (self.tmp / ".flow" / "tasks" / "x.md").write_text("host\n", encoding="utf-8")
        pre = self._ls_untracked()

        # Codex writes code (incl. a nested dir).
        _run_mock_codex(
            "--row",
            "completed",
            "--out",
            str(self.tmp / "result.json"),
            "--create-file",
            "src/new.py",
            "--create-file",
            "src/sub/deep.py",
            cwd=self.tmp,
        )
        post = self._ls_untracked()
        plan = self.flowctl.rollback_plan(pre, post)

        rb = set(plan["rollback_paths"])
        # codex-created files are present (the result.json itself is also new,
        # but it lives in the scratch tree; here we assert the code files made
        # it in and the protected paths did NOT).
        self.assertIn("src/new.py", rb)
        self.assertIn("src/sub/deep.py", rb)
        # pre-existing untracked file is NOT cleaned.
        self.assertNotIn("preexisting.txt", rb)
        # .flow/ path is NEVER cleaned, even though it is "new" relative to an
        # earlier state (here it predates pre, but assert the exclusion anyway).
        self.assertFalse(any(p.startswith(".flow/") for p in rb))


# ── Dual-copy invariant ──────────────────────────────────────────────────────


class DualCopyInvariantTestCase(unittest.TestCase):
    """The repo dogfoods a BYTE-IDENTICAL ``.flow/bin/flowctl.py`` kept in
    lockstep with the canonical ``scripts/flowctl.py``. The new helpers MUST
    land in BOTH or the live ``.flow/bin/flowctl`` runs stale code."""

    def test_two_copies_are_byte_identical(self) -> None:
        self.assertEqual(
            FLOWCTL_PY.read_bytes(),
            DOGFOOD_FLOWCTL_PY.read_bytes(),
            "scripts/flowctl.py and .flow/bin/flowctl.py must be byte-identical",
        )

    def test_both_copies_carry_new_helpers(self) -> None:
        for path in (FLOWCTL_PY, DOGFOOD_FLOWCTL_PY):
            text = path.read_text(encoding="utf-8")
            self.assertIn("def cmd_codex_classify_result", text, str(path))
            self.assertIn("def cmd_codex_rollback_plan", text, str(path))
            self.assertIn("def classify_delegation_result", text, str(path))
            self.assertIn("def rollback_plan", text, str(path))

    def test_live_bin_resolves_classify_subcommand(self) -> None:
        # `.flow/bin/flowctl codex classify-result --help` must resolve (the
        # live wrapper runs the dogfood copy — proves it is not stale).
        proc = subprocess.run(
            [str(FLOWCTL_BIN), "codex", "classify-result", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--result", proc.stdout)
        self.assertIn("--exit", proc.stdout)

    def test_live_bin_resolves_rollback_plan_subcommand(self) -> None:
        proc = subprocess.run(
            [str(FLOWCTL_BIN), "codex", "rollback-plan", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--preexisting-untracked-file", proc.stdout)
        self.assertIn("--post-untracked-file", proc.stdout)


# ── Prose contract: reference stub filled + worker.md safety mechanics ───────


class DelegationProseContractTestCase(unittest.TestCase):
    """Lock the markdown this task authors: the orchestration/safety stub in the
    reference is FILLED, and worker.md carries the safety assertions."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ref = REFERENCE_MD.read_text(encoding="utf-8")
        cls.worker = WORKER_MD.read_text(encoding="utf-8")

    def test_reference_orchestration_stub_is_filled(self) -> None:
        # The fn-55.4 stub placeholder must be GONE, the section present.
        self.assertNotIn("_(stub — authored by fn-55.4)_", self.ref)
        self.assertIn(
            "## Orchestration split / batching / result classification / safety",
            self.ref,
        )

    def test_reference_documents_classify_and_rollback_helpers(self) -> None:
        self.assertIn("flowctl codex classify-result", self.ref)
        self.assertIn("flowctl codex rollback-plan", self.ref)

    def test_reference_documents_prompt_template_8_sections(self) -> None:
        for tag in (
            "<task>",
            "<files>",
            "<patterns>",
            "<approach>",
            "<constraints>",
            "<testing>",
            "<verify>",
            "<output_contract>",
        ):
            self.assertIn(tag, self.ref, tag)

    def test_reference_constraints_forbid_git_and_nonscratch_flow(self) -> None:
        # <constraints> must forbid git/PRs and non-scratch .flow writes.
        self.assertIn(".flow/tmp/codex-", self.ref)
        low = self.ref.lower()
        self.assertIn("forbid", low)
        self.assertIn("git commit", low)

    def test_reference_batching_is_per_task_max_5(self) -> None:
        self.assertIn("≤5", self.ref)
        # cross-task batching is explicitly out of scope.
        self.assertIn("cross-task", self.ref.lower())

    def test_reference_trust_cross_check_documented(self) -> None:
        self.assertIn("git status --porcelain", self.ref)
        self.assertIn("files_modified", self.ref)

    def test_reference_clean_baseline_excludes_flow(self) -> None:
        low = self.ref.lower()
        self.assertIn("clean-baseline", low)
        self.assertIn("plan-sync", low)

    def test_worker_has_head_unchanged_assertion(self) -> None:
        self.assertIn("BASE_COMMIT", self.worker)
        self.assertIn("git rev-parse HEAD", self.worker)
        self.assertIn("git reset --soft", self.worker)

    def test_worker_has_flow_integrity_and_scoped_rollback(self) -> None:
        self.assertIn("rollback-plan", self.worker)
        self.assertIn("classify-result", self.worker)
        low = self.worker.lower()
        self.assertIn("git clean", low)
        # never a bare git clean.
        self.assertIn("never", low)


@unittest.skipUnless(shutil.which("bash"), "bash required for predicate")
class CleanBaselineExcludesFlowTestCase(unittest.TestCase):
    """Execute the shipped clean-baseline predicate from the reference against
    realistic ``git status --porcelain`` output.

    This is the executable side of the multi-task plan-sync acceptance criterion:
    a run with ``planSync.enabled=true`` leaves uncommitted ``.flow/tasks/`` edits
    (and possibly untracked ``.flow/tmp/`` scratch), which MUST NOT count as
    "dirty" and disable delegation after task 1 — only NON-``.flow/`` working-tree
    changes are dirty.
    """

    # The exact predicate shipped in references/codex-delegation.md.
    PREDICATE = r"grep -v '^.. \.flow/'"

    def _dirty(self, porcelain: str) -> str:
        """Return the 'dirty' (non-.flow) lines the preflight would see."""
        proc = subprocess.run(
            ["bash", "-c", f"printf '%s' \"$1\" | {self.PREDICATE} || true", "_", porcelain],
            capture_output=True,
            text=True,
        )
        return proc.stdout

    def test_predicate_is_the_one_shipped_in_reference(self) -> None:
        # Guard against the test drifting from the reference.
        ref = REFERENCE_MD.read_text(encoding="utf-8")
        self.assertIn(self.PREDICATE, ref)

    def test_plan_sync_flow_edits_are_not_dirty(self) -> None:
        # Modified .flow/tasks + .flow/specs (plan-sync) → NOT dirty.
        out = self._dirty(" M .flow/tasks/fn-55.4.md\n M .flow/specs/fn-55.md\n")
        self.assertEqual(out.strip(), "")

    def test_untracked_flow_scratch_is_not_dirty(self) -> None:
        # ?? .flow/tmp/codex-* scratch → NOT dirty.
        out = self._dirty("?? .flow/tmp/codex-fn-55.4/scratch.json\n")
        self.assertEqual(out.strip(), "")

    def test_real_code_change_is_dirty(self) -> None:
        # A non-.flow change IS dirty (delegation must not run on a dirty tree).
        out = self._dirty(" M .flow/tasks/fn-55.4.md\n M src/app.py\n")
        self.assertIn("src/app.py", out)

    def test_untracked_code_file_is_dirty(self) -> None:
        out = self._dirty("?? new_module.py\n")
        self.assertIn("new_module.py", out)


if __name__ == "__main__":
    unittest.main()
