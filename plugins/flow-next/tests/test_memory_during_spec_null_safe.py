"""Tests for `_export_memory_during_epic` null-safe time-window fallback (fn-49.2).

When `spec.created_at` is null (specs created via `/flow-next:capture` in
the same session as `flowctl init`, or pre-timestamp-population specs),
the memory time-window filter walks a deterministic fallback chain so the
returned set still approximates the spec lifetime:

1. Spec `created_at` (primary, YYYY-MM-DD prefix).
2. Earliest non-empty `tasks[].created_at` (Option A).
3. First commit on the spec's branch via `git log <branch> --reverse
   --format=%cI --max-count=1` (Option B).
4. Empty threshold → return all entries (graceful-degradation fallback,
   preserves pre-fn-49.2 no-signal behavior).

Each step is deterministic; the chain stops at the first success.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402  (path-injected import)


def _write_memory_entry(
    memory_dir: Path,
    track: str,
    category: str,
    slug: str,
    date: str,
    title: str = "",
) -> Path:
    """Write a minimal memory entry at `<track>/<category>/<slug>-<date>.md`.

    `_memory_parse_entry_filename` reads slug + date from the FILENAME
    (stem matches `^<slug>-YYYY-MM-DD$`), so the on-disk filename carries
    the canonical date even though frontmatter also stores it.
    """
    entry_dir = memory_dir / track / category
    entry_dir.mkdir(parents=True, exist_ok=True)
    path = entry_dir / f"{slug}-{date}.md"
    title = title or slug.replace("-", " ")
    body = (
        f"---\n"
        f'title: "{title}"\n'
        f'date: "{date}"\n'
        f"track: {track}\n"
        f"category: {category}\n"
        f"module: synthetic\n"
        f"tags: []\n"
        f"---\n\n"
        f"## Problem\n\n"
        f"Synthetic body for {slug}.\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


class TestResolveMemoryThreshold(unittest.TestCase):
    """`_export_resolve_memory_threshold` walks the fallback chain deterministically."""

    def test_spec_created_wins(self) -> None:
        threshold, source = flowctl._export_resolve_memory_threshold(
            "2026-05-25T06:08:52.904959Z",
            task_created_ats=["2026-05-20T00:00:00Z"],
            branch_name="any",
        )
        self.assertEqual(threshold, "2026-05-25")
        self.assertEqual(source, "spec")

    def test_falls_back_to_earliest_task(self) -> None:
        threshold, source = flowctl._export_resolve_memory_threshold(
            None,
            task_created_ats=[
                "2026-05-26T10:00:00Z",
                "2026-05-25T07:04:49Z",
                "2026-05-27T03:00:00Z",
            ],
        )
        self.assertEqual(threshold, "2026-05-25")
        self.assertEqual(source, "earliest_task")

    def test_falls_back_to_branch_when_tasks_empty(self) -> None:
        """No spec.created + no usable task timestamps → branch first commit."""
        threshold, source = flowctl._export_resolve_memory_threshold(
            None,
            task_created_ats=[],
            branch_name="HEAD",  # use HEAD so the test is git-repo-aware
        )
        self.assertEqual(source, "branch_first_commit")
        # Threshold is a real YYYY-MM-DD prefix.
        self.assertRegex(threshold, r"^\d{4}-\d{2}-\d{2}$")

    def test_no_signals_returns_empty(self) -> None:
        threshold, source = flowctl._export_resolve_memory_threshold(
            None, task_created_ats=None, branch_name=None
        )
        self.assertEqual(threshold, "")
        self.assertEqual(source, "")

    def test_empty_strings_in_task_list_filtered(self) -> None:
        """Empty/None task created_at values must not crash min()."""
        threshold, source = flowctl._export_resolve_memory_threshold(
            None,
            task_created_ats=["", "", "2026-05-25T07:04:49Z", ""],
        )
        self.assertEqual(threshold, "2026-05-25")
        self.assertEqual(source, "earliest_task")

    def test_all_empty_task_list_falls_through_to_branch(self) -> None:
        threshold, source = flowctl._export_resolve_memory_threshold(
            None,
            task_created_ats=["", ""],
            branch_name="HEAD",
        )
        self.assertEqual(source, "branch_first_commit")

    def test_invalid_branch_falls_through(self) -> None:
        """git log on a nonexistent branch returns rc != 0 → fall through."""
        threshold, source = flowctl._export_resolve_memory_threshold(
            None,
            task_created_ats=None,
            branch_name="definitely-not-a-real-branch-fn-49-2",
        )
        # Should not raise; falls through to no-signal.
        self.assertEqual(threshold, "")
        self.assertEqual(source, "")

    def test_branch_first_commit_returns_root_not_tip(self) -> None:
        """Regression: multi-commit branch must return the ROOT commit's date,
        not the tip's.

        Caught by Codex bot review on PR #147 — `git log --reverse --format=%cI
        --max-count=1` is wrong because ``--max-count`` is a selection option
        applied BEFORE output ordering. Combined with ``--reverse`` it picks
        the most recent commit, then "reverses" a 1-element list (no-op),
        returning the branch TIP date instead of the root commit's date.

        Pre-fix this test would fail because the threshold returned would be
        2026-05-30 (tip) instead of 2026-05-25 (root). Pre-fix tests passed
        only because their fixtures had a SINGLE commit where root == tip.
        """
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            base_env = {
                **os.environ,
                "GIT_COMMITTER_NAME": "fn-49.2 regression",
                "GIT_COMMITTER_EMAIL": "regression@example.com",
                "GIT_AUTHOR_NAME": "fn-49.2 regression",
                "GIT_AUTHOR_EMAIL": "regression@example.com",
            }
            subprocess.run(
                ["git", "init", "-b", "fn-49-multi-commit-branch", "."],
                cwd=repo, env=base_env, check=True, capture_output=True,
            )
            # Commit 1: 2026-05-25 (the ROOT — what we want returned).
            env_root = {
                **base_env,
                "GIT_COMMITTER_DATE": "2026-05-25T12:00:00+00:00",
                "GIT_AUTHOR_DATE": "2026-05-25T12:00:00+00:00",
            }
            (repo / "a.txt").write_text("a", encoding="utf-8")
            subprocess.run(
                ["git", "add", "a.txt"],
                cwd=repo, env=env_root, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "root commit (2026-05-25)"],
                cwd=repo, env=env_root, check=True, capture_output=True,
            )
            # Commit 2: 2026-05-30 (the TIP — what the buggy form would return).
            env_tip = {
                **base_env,
                "GIT_COMMITTER_DATE": "2026-05-30T12:00:00+00:00",
                "GIT_AUTHOR_DATE": "2026-05-30T12:00:00+00:00",
            }
            (repo / "b.txt").write_text("b", encoding="utf-8")
            subprocess.run(
                ["git", "add", "b.txt"],
                cwd=repo, env=env_tip, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "tip commit (2026-05-30)"],
                cwd=repo, env=env_tip, check=True, capture_output=True,
            )

            cwd_before = os.getcwd()
            os.chdir(repo)
            try:
                threshold, source = flowctl._export_resolve_memory_threshold(
                    None,
                    task_created_ats=[],
                    branch_name="fn-49-multi-commit-branch",
                )
            finally:
                os.chdir(cwd_before)

        self.assertEqual(source, "branch_first_commit")
        # ROOT commit date — NOT the tip date. The buggy form would return
        # "2026-05-30" here, filtering out in-window memory entries dated
        # 2026-05-25 through 2026-05-29 — the exact regression class fn-49.2
        # was supposed to prevent.
        self.assertEqual(threshold, "2026-05-25")
        self.assertNotEqual(threshold, "2026-05-30")

    def test_branch_first_commit_excludes_base_history(self) -> None:
        """Regression: when ``base_ref`` is provided, the fallback uses
        ``git log {base_ref}..{branch_name}`` so only commits unique to the
        feature branch are walked.

        Caught by Codex bot P2 review on PR #147. Without ``base_ref``,
        ``git log <branch>`` walks ALL commits reachable from the branch
        tip — including inherited mainline history. ``--reverse`` then
        ``splitlines()[0]`` returns the REPOSITORY ROOT commit's date
        (way too old), defeating the purpose of "approximate the spec
        lifetime".

        Pre-fix this test would fail with threshold == 2026-01-01 (the
        repo root). Post-fix it returns 2026-05-25 (the feature branch's
        first commit).
        """
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            base_env = {
                **os.environ,
                "GIT_COMMITTER_NAME": "fn-49.2 base-history",
                "GIT_COMMITTER_EMAIL": "base-history@example.com",
                "GIT_AUTHOR_NAME": "fn-49.2 base-history",
                "GIT_AUTHOR_EMAIL": "base-history@example.com",
            }
            subprocess.run(
                ["git", "init", "-b", "trunk", "."],
                cwd=repo, env=base_env, check=True, capture_output=True,
            )
            # Trunk commit 1: 2026-01-01 (the REPO ROOT — what the buggy
            # form would return).
            env_t1 = {
                **base_env,
                "GIT_COMMITTER_DATE": "2026-01-01T12:00:00+00:00",
                "GIT_AUTHOR_DATE": "2026-01-01T12:00:00+00:00",
            }
            (repo / "trunk1.txt").write_text("t1", encoding="utf-8")
            subprocess.run(
                ["git", "add", "trunk1.txt"],
                cwd=repo, env=env_t1, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "trunk root (2026-01-01)"],
                cwd=repo, env=env_t1, check=True, capture_output=True,
            )
            # Trunk commit 2: 2026-04-01 (still on trunk).
            env_t2 = {
                **base_env,
                "GIT_COMMITTER_DATE": "2026-04-01T12:00:00+00:00",
                "GIT_AUTHOR_DATE": "2026-04-01T12:00:00+00:00",
            }
            (repo / "trunk2.txt").write_text("t2", encoding="utf-8")
            subprocess.run(
                ["git", "add", "trunk2.txt"],
                cwd=repo, env=env_t2, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "trunk advanced (2026-04-01)"],
                cwd=repo, env=env_t2, check=True, capture_output=True,
            )
            # Branch off trunk and add a feature commit: 2026-05-25
            # (the FORK POINT — what the correct form returns).
            subprocess.run(
                ["git", "checkout", "-b", "feature-fn-49"],
                cwd=repo, env=base_env, check=True, capture_output=True,
            )
            env_f1 = {
                **base_env,
                "GIT_COMMITTER_DATE": "2026-05-25T12:00:00+00:00",
                "GIT_AUTHOR_DATE": "2026-05-25T12:00:00+00:00",
            }
            (repo / "feature.txt").write_text("f", encoding="utf-8")
            subprocess.run(
                ["git", "add", "feature.txt"],
                cwd=repo, env=env_f1, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "feature commit (2026-05-25)"],
                cwd=repo, env=env_f1, check=True, capture_output=True,
            )

            cwd_before = os.getcwd()
            os.chdir(repo)
            try:
                # With base_ref — correct: feature commit date.
                t_with_base, source_with_base = flowctl._export_resolve_memory_threshold(
                    None,
                    task_created_ats=[],
                    branch_name="feature-fn-49",
                    base_ref="trunk",
                )
                # Without base_ref — buggy: repo root date.
                t_without_base, source_without_base = flowctl._export_resolve_memory_threshold(
                    None,
                    task_created_ats=[],
                    branch_name="feature-fn-49",
                )
            finally:
                os.chdir(cwd_before)

        self.assertEqual(source_with_base, "branch_first_commit")
        # WITH base_ref: returns the fork-point commit's date (2026-05-25).
        # This is the correct behavior — narrow window to commits unique to
        # the feature branch.
        self.assertEqual(t_with_base, "2026-05-25")
        # Sanity check: the pre-base-ref behavior is preserved when no
        # base_ref is supplied (best-effort for callers without a base).
        # In that case the returned date is the repo root (2026-01-01) —
        # demonstrably wrong for narrow-window purposes but documented as
        # the fallback when no base context is available.
        self.assertEqual(source_without_base, "branch_first_commit")
        self.assertEqual(t_without_base, "2026-01-01")
        # And of course the two diverge — that's the whole point.
        self.assertNotEqual(t_with_base, t_without_base)


class TestMemoryDuringEpicNullSafe(unittest.TestCase):
    """`_export_memory_during_epic` honors the fallback-resolved threshold."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.mem = self.tmp / "memory"
        # 3 decisions across a range: one before, one at, one after the window.
        _write_memory_entry(
            self.mem, "knowledge", "decisions", "decision-old", "2026-05-20"
        )
        _write_memory_entry(
            self.mem, "knowledge", "decisions", "decision-mid", "2026-05-25"
        )
        _write_memory_entry(
            self.mem, "knowledge", "decisions", "decision-new", "2026-05-26"
        )
        # 2 bugs.
        _write_memory_entry(
            self.mem, "bug", "build-errors", "bug-old", "2026-05-20"
        )
        _write_memory_entry(
            self.mem, "bug", "build-errors", "bug-new", "2026-05-26"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_spec_created_drives_window(self) -> None:
        r = flowctl._export_memory_during_epic(self.mem, "2026-05-25T00:00:00Z")
        decision_ids = sorted(d["id"] for d in r["decisions"])
        # Date >= 2026-05-25 → decision-mid + decision-new.
        self.assertEqual(len(decision_ids), 2)
        self.assertTrue(all("decision-old" not in i for i in decision_ids))

    def test_null_spec_falls_back_to_earliest_task(self) -> None:
        """R3 — spec.created null + tasks have created_at → earliest task wins."""
        r = flowctl._export_memory_during_epic(
            self.mem,
            None,
            task_created_ats=["2026-05-26T10:00:00Z", "2026-05-25T07:00:00Z"],
        )
        decision_ids = sorted(d["id"] for d in r["decisions"])
        # Threshold = 2026-05-25 → decision-mid + decision-new survive.
        self.assertEqual(len(decision_ids), 2)
        self.assertTrue(all("decision-old" not in i for i in decision_ids))
        # Bugs filtered same way.
        self.assertEqual(len(r["bugs"]), 1)  # only bug-new

    def test_null_spec_null_tasks_falls_back_to_branch_first_commit(self) -> None:
        """R3 — spec.created null + tasks all null → branch first-commit fires."""
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            # Build a synthetic git repo: branch's first commit is the
            # branch first-commit timestamp that drives the threshold.
            env = {
                **os.environ,
                # Pin committer date so the test is deterministic across
                # machines. `git log --format=%cI` reads committer date.
                "GIT_COMMITTER_DATE": "2026-05-25T12:00:00+00:00",
                "GIT_AUTHOR_DATE": "2026-05-25T12:00:00+00:00",
                "GIT_COMMITTER_NAME": "fn-49.2 test",
                "GIT_COMMITTER_EMAIL": "test@example.com",
                "GIT_AUTHOR_NAME": "fn-49.2 test",
                "GIT_AUTHOR_EMAIL": "test@example.com",
            }
            subprocess.run(
                ["git", "init", "-b", "fn-49-test-branch", "."],
                cwd=repo, env=env, check=True, capture_output=True,
            )
            (repo / "f.txt").write_text("x", encoding="utf-8")
            subprocess.run(
                ["git", "add", "f.txt"],
                cwd=repo, env=env, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=repo, env=env, check=True, capture_output=True,
            )

            # Run the resolution from within the synthetic repo so
            # `_export_run_git` (which uses cwd=None → process cwd)
            # resolves the branch name correctly.
            cwd_before = os.getcwd()
            os.chdir(repo)
            try:
                r = flowctl._export_memory_during_epic(
                    self.mem,
                    None,
                    task_created_ats=[],
                    branch_name="fn-49-test-branch",
                )
            finally:
                os.chdir(cwd_before)

        decision_ids = sorted(d["id"] for d in r["decisions"])
        # Branch first commit was 2026-05-25 → decision-mid + decision-new.
        self.assertEqual(len(decision_ids), 2)
        self.assertTrue(all("decision-old" not in i for i in decision_ids))

    def test_no_signals_returns_all_entries(self) -> None:
        """Graceful-degradation contract — no usable timestamp → return all."""
        r = flowctl._export_memory_during_epic(
            self.mem,
            None,
            task_created_ats=None,
            branch_name=None,
        )
        self.assertEqual(len(r["decisions"]), 3)
        self.assertEqual(len(r["bugs"]), 2)

    def test_missing_memory_dir_returns_empty_structure(self) -> None:
        """No memory dir → empty structure, never crash."""
        r = flowctl._export_memory_during_epic(
            self.tmp / "nonexistent-memory",
            None,
            task_created_ats=["2026-05-25T00:00:00Z"],
        )
        self.assertEqual(r, {"decisions": [], "bugs": [], "architecture_patterns": []})


if __name__ == "__main__":
    unittest.main()
