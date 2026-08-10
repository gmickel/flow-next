"""fn-180.3 / #302: `validate` evidence-commit reachability findings.

Two layers:

- Black box over a real git fixture that holds all THREE states at once —
  a reachable commit, a commit orphaned by `reset --hard` (still in the
  object store), and foreign tokens (a hex SHA from another repo, a tracker
  UUID). Only the orphan is flagged; the foreign tokens survive untouched in
  the recorded evidence, which is the load-bearing half of the contract.
- Spawn-budget assertions (R4): a `git` shim on PATH logs every invocation,
  and the reachability plumbing must cost the SAME number of git spawns with
  2 recorded commits as with 40 — one `cat-file --batch-check`, one
  `rev-list`. Plus offline unit coverage of the graceful-degrade paths.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"

FOREIGN_SHA = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
TRACKER_UUID = "3f8b2c1e-77aa-4c0d-9d3e-0b1c2d3e4f50"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_evidence_reachability_under_test", FLOWCTL_PY
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


flowctl = _load_flowctl()


class _RepoFixture:
    """A throwaway git repo with a `.flow/` and a PATH-shimmed git logger."""

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.shim_dir = self.root / "_shim"
        self.git_log = self.root / "_gitcalls.log"
        self._git("init", "-q")
        self._git("config", "user.email", "test@example.com")
        self._git("config", "user.name", "Test")
        self.run("init", "--json", check=True)

    def destroy(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def _git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit(self, name: str) -> str:
        (self.root / name).write_text(name, encoding="utf-8")
        self._git("add", name)
        self._git("commit", "-q", "-m", name)
        return self._git("rev-parse", "HEAD")

    def run(
        self, *args: str, check: bool = False, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY), *args],
            cwd=self.root,
            check=check,
            capture_output=True,
            text=True,
            env=env,
        )

    def create_task_with_evidence(self, spec_id: str, title: str, commits: list[str]) -> str:
        created = json.loads(
            self.run(
                "task", "create", "--spec", spec_id, "--title", title, "--json",
                check=True,
            ).stdout
        )
        task_id = created["id"]
        self.run("start", task_id, "--json", check=True)
        summary = self.root / f"_summary_{task_id}.md"
        summary.write_text("done\n", encoding="utf-8")
        evidence = self.root / f"_evidence_{task_id}.json"
        evidence.write_text(
            json.dumps({"commits": commits, "tests": [], "prs": []}), encoding="utf-8"
        )
        self.run(
            "done", task_id,
            "--summary-file", str(summary),
            "--evidence-json", str(evidence),
            "--json",
            check=True,
        )
        return task_id

    # --- git spawn accounting -------------------------------------------------

    def shimmed_env(self) -> dict[str, str]:
        """PATH env whose `git` logs its argv, then execs the real git."""
        self.shim_dir.mkdir(exist_ok=True)
        real_git = shutil.which("git")
        assert real_git
        shim = self.shim_dir / "git"
        shim.write_text(
            "#!/bin/sh\n"
            f'printf "%s\\n" "$*" >> {self.git_log}\n'
            f'exec {real_git} "$@"\n',
            encoding="utf-8",
        )
        shim.chmod(0o755)
        env = dict(os.environ)
        env["PATH"] = f"{self.shim_dir}{os.pathsep}{env['PATH']}"
        return env

    def git_calls(self) -> list[str]:
        if not self.git_log.exists():
            return []
        return [
            line for line in self.git_log.read_text(encoding="utf-8").splitlines() if line
        ]

    def reset_git_log(self) -> None:
        if self.git_log.exists():
            self.git_log.unlink()


class EvidenceReachabilityBlackBoxTest(unittest.TestCase):
    """All three #302 states in one repo, through the real `validate` verb."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.fx = _RepoFixture()
        base = cls.fx.commit("base.txt")
        cls.orphan_sha = cls.fx.commit("orphan.txt")
        cls.fx._git("reset", "--hard", "-q", base)
        cls.reachable_sha = cls.fx.commit("kept.txt")

        cls.spec_id = json.loads(
            cls.fx.run("spec", "create", "--title", "Evidence states", "--json", check=True).stdout
        )["id"]
        cls.reachable_task = cls.fx.create_task_with_evidence(
            cls.spec_id, "Reachable evidence", [cls.reachable_sha]
        )
        cls.orphan_task = cls.fx.create_task_with_evidence(
            cls.spec_id, "Orphaned evidence", [cls.orphan_sha[:8]]
        )
        cls.foreign_task = cls.fx.create_task_with_evidence(
            cls.spec_id, "Foreign evidence", [FOREIGN_SHA, TRACKER_UUID]
        )
        result = cls.fx.run("validate", "--spec", cls.spec_id, "--json")
        cls.payload = json.loads(result.stdout)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fx.destroy()

    def _warnings_for(self, task_id: str) -> list[str]:
        return [w for w in self.payload["warnings"] if w.startswith(f"Task {task_id}:")]

    def test_orphaned_commit_is_reported(self) -> None:
        warnings = self._warnings_for(self.orphan_task)
        self.assertEqual(len(warnings), 1, self.payload["warnings"])
        self.assertIn(self.orphan_sha[:8], warnings[0])
        self.assertIn("not reachable", warnings[0])

    def test_reachable_commit_is_silent(self) -> None:
        self.assertEqual(self._warnings_for(self.reachable_task), [])

    def test_foreign_tokens_are_ignored_not_flagged(self) -> None:
        # The load-bearing state: a foreign SHA and a tracker UUID are
        # legitimate recorded evidence and must never produce a finding.
        self.assertEqual(self._warnings_for(self.foreign_task), [])

    def test_foreign_tokens_survive_untouched(self) -> None:
        shown = json.loads(
            self.fx.run("show", self.foreign_task, "--json", check=True).stdout
        )
        self.assertEqual(
            shown["evidence"]["commits"], [FOREIGN_SHA, TRACKER_UUID]
        )

    def test_orphan_finding_is_a_warning_not_an_error(self) -> None:
        # Read-only verdict: never fails validate, never rewrites a SHA.
        self.assertTrue(self.payload["valid"])
        self.assertEqual(self.payload["errors"], [])
        shown = json.loads(
            self.fx.run("show", self.orphan_task, "--json", check=True).stdout
        )
        self.assertEqual(shown["evidence"]["commits"], [self.orphan_sha[:8]])


class EvidenceReachabilitySpawnBudgetTest(unittest.TestCase):
    """R4: constant git spawns regardless of how many commits are recorded."""

    def setUp(self) -> None:
        self.fx = _RepoFixture()
        self.addCleanup(self.fx.destroy)
        self.shas = [self.fx.commit(f"f{i}.txt") for i in range(40)]
        self.spec_id = json.loads(
            self.fx.run("spec", "create", "--title", "Spawn budget", "--json", check=True).stdout
        )["id"]

    def _git_calls_for(self, commits: list[str]) -> list[str]:
        self.fx.create_task_with_evidence(self.spec_id, "evidence", commits)
        self.fx.reset_git_log()
        env = self.fx.shimmed_env()
        self.fx.run("validate", "--spec", self.spec_id, "--json", env=env)
        return self.fx.git_calls()

    def test_spawn_count_is_flat_in_commit_count(self) -> None:
        few = self._git_calls_for(self.shas[:2])
        many = self._git_calls_for(self.shas)
        self.assertEqual(
            len(few), len(many), f"few={few!r} many={many!r}"
        )
        for calls in (few, many):
            self.assertEqual(
                len([c for c in calls if c.startswith("cat-file --batch-check")]), 1, calls
            )
            self.assertEqual(
                len([c for c in calls if c.startswith("rev-list HEAD")]), 1, calls
            )
        # No per-SHA probing crept in under another name.
        self.assertEqual([c for c in many if "merge-base" in c], [])
        self.assertFalse([c for c in many if c.startswith("cat-file -t")])

    def test_validate_all_shares_one_batch_across_specs(self) -> None:
        self.fx.create_task_with_evidence(self.spec_id, "evidence", self.shas[:5])
        other = json.loads(
            self.fx.run("spec", "create", "--title", "Second spec", "--json", check=True).stdout
        )["id"]
        self.fx.create_task_with_evidence(other, "more evidence", self.shas[5:10])
        self.fx.reset_git_log()
        self.fx.run("validate", "--all", "--json", env=self.fx.shimmed_env())
        calls = self.fx.git_calls()
        self.assertEqual(
            len([c for c in calls if c.startswith("cat-file --batch-check")]), 1, calls
        )
        self.assertEqual(
            len([c for c in calls if c.startswith("rev-list HEAD")]), 1, calls
        )


class EvidenceReachabilityUnitTest(unittest.TestCase):
    """Offline: token extraction and the graceful-degrade paths (R4 errors)."""

    def test_tokens_extracted_from_evidence_block(self) -> None:
        self.assertEqual(
            flowctl.evidence_commit_tokens({"evidence": {"commits": ["a1b2c3d", ""]}}),
            ["a1b2c3d"],
        )
        self.assertEqual(
            flowctl.evidence_commit_tokens({"evidence": {"commits": "a1b2c3d"}}),
            ["a1b2c3d"],
        )
        self.assertEqual(flowctl.evidence_commit_tokens({}), [])
        self.assertEqual(flowctl.evidence_commit_tokens({"evidence": "nope"}), [])

    def test_non_hex_tokens_never_reach_git(self) -> None:
        checker = flowctl.EvidenceReachability(Path("/nonexistent"))
        spawned: list[Any] = []
        checker._batch_check = lambda tokens: spawned.append(tokens) or {}  # type: ignore[assignment]
        checker.prime([TRACKER_UUID, "HEAD~1", "refs/heads/main", ""])
        self.assertEqual(spawned, [])
        self.assertEqual(
            checker.state(TRACKER_UUID), flowctl.EVIDENCE_STATE_IGNORED
        )

    def test_batch_check_unavailable_degrades_to_ignored(self) -> None:
        checker = flowctl.EvidenceReachability(Path("/nonexistent"))

        def boom(tokens: list[str]) -> dict[str, str]:
            raise AssertionError("must not be reached")

        checker._batch_check = lambda tokens: {}  # type: ignore[assignment]
        checker._reachable_oids = boom  # type: ignore[assignment]
        checker.prime([FOREIGN_SHA])
        self.assertEqual(checker.state(FOREIGN_SHA), flowctl.EVIDENCE_STATE_IGNORED)

    def test_membership_pass_failure_yields_no_verdict(self) -> None:
        checker = flowctl.EvidenceReachability(Path("/nonexistent"))
        checker._batch_check = lambda tokens: {t: t for t in tokens}  # type: ignore[assignment]
        checker._reachable_oids = lambda wanted: None  # type: ignore[assignment]
        checker.prime([FOREIGN_SHA])
        # None = git had no answer; never a false "everything is orphaned".
        self.assertEqual(checker.state(FOREIGN_SHA), flowctl.EVIDENCE_STATE_IGNORED)

    def test_batch_check_line_count_mismatch_refuses_to_guess(self) -> None:
        checker = flowctl.EvidenceReachability(Path("/nonexistent"))

        class _Proc:
            returncode = 0
            stdout = b"deadbeef commit 12\n"

        original = flowctl.subprocess.run
        flowctl.subprocess.run = lambda *a, **k: _Proc()  # type: ignore[assignment]
        try:
            self.assertEqual(
                checker._batch_check(["deadbeef", "cafebabe"]), {}
            )
        finally:
            flowctl.subprocess.run = original  # type: ignore[assignment]


if __name__ == "__main__":
    unittest.main()
