"""fn-109: hot-path memoization of get_repo_root / get_state_dir.

Covers the spec's R3-R6 acceptance criteria:

- R3: ``cmd_list`` over 400+ tasks spawns <= 5 subprocesses (baseline 809 —
  2 uncached ``git rev-parse`` spawns PER TASK via get_repo_root /
  get_state_dir).
- R4: both caches are keyed by ``Path.cwd()`` — an ``os.chdir`` invalidates
  them naturally (the module-scope-load + per-test chdir pattern used by
  test_review_convergence_cap.py / test_anchor_bundle.py must keep working).
- R5: the ``FLOW_STATE_DIR`` override is honored under caching — set/unset
  within one process always resolves fresh.
- R6: only SUCCESS results are cached — a transient git failure is never
  sticky, and a later success both resolves correctly and is cached.

The flowctl module is loaded ONCE at module scope (same pattern as the two
chdir suites the caches must survive), then each test chdirs into a fresh
temp git repo so cache keys never collide across tests.
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest import mock


def _load_flowctl() -> Any:
    here = Path(__file__).resolve()
    flowctl_path = here.parent.parent / "scripts" / "flowctl.py"
    spec = importlib.util.spec_from_file_location(
        "flowctl_hot_path_under_test", flowctl_path
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


@contextmanager
def _counting_subprocess(module):
    """Wrap ``subprocess.run`` as seen by the flowctl module with a counting
    delegate (records argv, then calls the real run). Precedent:
    tests/test_backend_spec.py ``_stub_subprocess``."""
    real_run = module.subprocess.run
    calls = []

    def counting_run(cmd, **kwargs):
        calls.append(list(cmd))
        return real_run(cmd, **kwargs)

    module.subprocess.run = counting_run
    try:
        yield calls
    finally:
        module.subprocess.run = real_run


@contextmanager
def _failing_subprocess(module):
    """Make every ``subprocess.run`` in the flowctl module raise
    ``CalledProcessError`` (simulates a transient git failure)."""
    real_run = module.subprocess.run

    def failing_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(returncode=128, cmd=list(cmd))

    module.subprocess.run = failing_run
    try:
        yield
    finally:
        module.subprocess.run = real_run


def _git_state_dir(cwd: Path) -> Path:
    """The value production's success branch computes for ``cwd`` — the exact
    same git invocation, so expectations track real git output (relative
    ``.git`` at a standalone toplevel, absolute inside a linked worktree)."""
    out = subprocess.run(
        ["git", "rev-parse", "--git-common-dir", "--path-format=absolute"],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()
    return Path(out) / "flow-state"


class _TempGitRepoCase(unittest.TestCase):
    """Fresh temp git repo per test, chdir'd into (the chdir-suite pattern)."""

    def _make_git_repo(self) -> Path:
        root = Path(tempfile.mkdtemp()).resolve()
        self._roots.append(root)
        subprocess.run(
            ["git", "init", "-q"], cwd=root, check=True, capture_output=True
        )
        return root

    def setUp(self) -> None:
        self._roots = []
        self._prev_cwd = os.getcwd()
        self.root = self._make_git_repo()
        os.chdir(self.root)

    def tearDown(self) -> None:
        os.chdir(self._prev_cwd)
        for root in self._roots:
            shutil.rmtree(root, ignore_errors=True)


# ------------------------- R3: subprocess budget ---------------------------


class TestCmdListSubprocessBudget(_TempGitRepoCase):
    N_SPECS = 4
    TASKS_PER_SPEC = 101  # 404 tasks total (>= 400 per R3)

    def _seed_flow(self) -> None:
        flow = self.root / ".flow"
        (flow / "specs").mkdir(parents=True)
        (flow / "tasks").mkdir(parents=True)
        for s in range(1, self.N_SPECS + 1):
            spec_id = f"fn-{s}"
            (flow / "specs" / f"{spec_id}.json").write_text(
                json.dumps(
                    {"id": spec_id, "title": f"Spec {s}", "status": "open"}
                ),
                encoding="utf-8",
            )
            for t in range(1, self.TASKS_PER_SPEC + 1):
                task_id = f"{spec_id}.{t}"
                (flow / "tasks" / f"{task_id}.json").write_text(
                    json.dumps(
                        {
                            "id": task_id,
                            "spec": spec_id,
                            "title": f"Task {t}",
                            "status": "todo",
                        }
                    ),
                    encoding="utf-8",
                )

    def test_cmd_list_400_tasks_spawns_at_most_5_subprocesses(self) -> None:
        self._seed_flow()
        captured = []
        with _counting_subprocess(flowctl) as calls:
            with mock.patch.object(flowctl, "json_output", captured.append):
                flowctl.cmd_list(argparse.Namespace(json=True))
        # The fixture really is at 400+ scale and cmd_list really ran.
        self.assertEqual(len(captured), 1)
        self.assertEqual(
            captured[0]["task_count"], self.N_SPECS * self.TASKS_PER_SPEC
        )
        self.assertGreaterEqual(captured[0]["task_count"], 400)
        # Baseline was 809 spawns (2 per task); memoized budget is <= 5.
        self.assertLessEqual(
            len(calls),
            5,
            f"cmd_list spawned {len(calls)} subprocesses: {calls[:10]}...",
        )


# ------------------------- R4: chdir invalidation --------------------------


class TestChdirInvalidatesCaches(_TempGitRepoCase):
    def test_repo_root_follows_chdir(self) -> None:
        root_a = self.root
        root_b = self._make_git_repo()
        self.assertEqual(flowctl.get_repo_root(), root_a)
        os.chdir(root_b)
        self.assertEqual(flowctl.get_repo_root(), root_b)
        # And back: the first repo's entry is still keyed to its own cwd.
        os.chdir(root_a)
        self.assertEqual(flowctl.get_repo_root(), root_a)

    def test_state_dir_follows_chdir(self) -> None:
        # A linked worktree yields an ABSOLUTE common-dir (a standalone
        # toplevel yields relative '.git', identical text in every repo — a
        # stale cache entry would be undetectable). Worktree first, then a
        # standalone repo: a first-call-wins cache would leak the absolute
        # worktree value into the second repo.
        main = self.root
        subprocess.run(
            ["git", "-C", str(main), "config", "user.email", "t@example.com"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(main), "config", "user.name", "t"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(main), "commit", "-q", "--allow-empty", "-m", "seed"],
            check=True, capture_output=True,
        )
        wt = main / "wt"
        subprocess.run(
            ["git", "-C", str(main), "worktree", "add", "-q", str(wt)],
            check=True, capture_output=True,
        )
        os.chdir(wt)
        v_wt = flowctl.get_state_dir()
        self.assertEqual(v_wt, _git_state_dir(wt))
        self.assertEqual(v_wt, main / ".git" / "flow-state")  # absolute
        root_b = self._make_git_repo()
        os.chdir(root_b)
        v_b = flowctl.get_state_dir()
        self.assertNotEqual(v_b, v_wt)  # the worktree entry did not leak
        self.assertEqual(v_b, _git_state_dir(root_b))
        self.assertEqual(
            Path(os.path.abspath(v_b)), root_b / ".git" / "flow-state"
        )

    def test_repeat_call_same_cwd_spawns_no_subprocess(self) -> None:
        flowctl.get_repo_root()  # prime both caches for this cwd
        flowctl.get_state_dir()
        with _counting_subprocess(flowctl) as calls:
            flowctl.get_repo_root()
            flowctl.get_state_dir()
        self.assertEqual(calls, [])


# ------------------------- R5: FLOW_STATE_DIR override ---------------------


class TestFlowStateDirOverrideUnderCaching(_TempGitRepoCase):
    def test_set_unset_within_one_process(self) -> None:
        override = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, override, ignore_errors=True)
        git_derived = _git_state_dir(self.root)

        with mock.patch.dict(os.environ, clear=False):
            os.environ.pop("FLOW_STATE_DIR", None)
            # Unset: git-derived path (primes the cache for this cwd).
            self.assertEqual(flowctl.get_state_dir(), git_derived)
            # Set: override wins immediately, cache notwithstanding.
            os.environ["FLOW_STATE_DIR"] = str(override)
            self.assertEqual(flowctl.get_state_dir(), override)
            # Unset again: back to the git-derived path.
            del os.environ["FLOW_STATE_DIR"]
            self.assertEqual(flowctl.get_state_dir(), git_derived)
            # Set to a different dir: the new value wins (no stale override).
            override2 = Path(tempfile.mkdtemp()).resolve()
            self.addCleanup(shutil.rmtree, override2, ignore_errors=True)
            os.environ["FLOW_STATE_DIR"] = str(override2)
            self.assertEqual(flowctl.get_state_dir(), override2)


# ------------------------- R6: failure is never sticky ---------------------


class TestTransientFailureNotCached(_TempGitRepoCase):
    def test_repo_root_failure_then_success(self) -> None:
        with _failing_subprocess(flowctl):
            # Failure path: falls back to cwd...
            self.assertEqual(flowctl.get_repo_root(), self.root)
            # ...and does NOT poison the cache for this cwd.
            self.assertNotIn(Path.cwd(), flowctl._REPO_ROOT_CACHE)
        # Later success resolves via git (not a stale fallback)...
        with _counting_subprocess(flowctl) as calls:
            self.assertEqual(flowctl.get_repo_root(), self.root)
        self.assertEqual(len(calls), 1)
        # ...and THAT success is cached (no further spawns).
        with _counting_subprocess(flowctl) as calls:
            flowctl.get_repo_root()
        self.assertEqual(calls, [])

    def test_state_dir_failure_then_success(self) -> None:
        with mock.patch.dict(os.environ, clear=False):
            os.environ.pop("FLOW_STATE_DIR", None)
            with _failing_subprocess(flowctl):
                # Both git lookups fail: non-git fallback (cwd/.flow/state).
                self.assertEqual(
                    flowctl.get_state_dir(), self.root / ".flow" / "state"
                )
            self.assertNotIn((Path.cwd(), None), flowctl._STATE_DIR_CACHE)
            # Later success resolves the real common-dir path and caches it.
            self.assertEqual(flowctl.get_state_dir(), _git_state_dir(self.root))
            with _counting_subprocess(flowctl) as calls:
                flowctl.get_state_dir()
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
