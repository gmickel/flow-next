"""Hermetic green-receipt and honor-probe tests for `flowctl gate` (fn-102).

Every assertion drives the production CLI via subprocess against a temporary
real git repository. No network, no package installation, no shared state.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


FLOWCTL_PY = Path(__file__).resolve().parent.parent / "scripts" / "flowctl.py"
COMMAND = "python3 -m unittest discover -s plugins/flow-next/tests -p 'test_gate_*.py' -q"
GATE_ID = "full-gate"


class GateReceiptHarness(unittest.TestCase):
    """Temporary git repo with helpers that invoke the public CLI wire.

    Carries NO test_* methods - concrete test classes inherit it so unittest
    discovery never runs a shared case twice (PR #213 P3).
    """

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        self._git("init", "-q")
        self._git("config", "user.email", "gate@example.com")
        self._git("config", "user.name", "Gate Test")
        self._commit("src/app.py", "print('seed')\n", "seed")

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @staticmethod
    def _pinned_env() -> dict:
        env = dict(os.environ)
        env["GIT_AUTHOR_DATE"] = "2026-01-01T00:00:00Z"
        env["GIT_COMMITTER_DATE"] = "2026-01-01T00:00:00Z"
        return env

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=self.tmpdir,
            capture_output=True,
            text=True,
            check=True,
            env=self._pinned_env(),
        )
        return result.stdout.strip()

    def _commit(self, rel: str, content: str, message: str) -> str:
        path = self.tmpdir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", message)
        return self._git("rev-parse", "HEAD")

    def _flowctl(
        self, *args: str, cwd: Optional[Path] = None
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY), "gate"] + list(args),
            cwd=cwd or self.tmpdir,
            capture_output=True,
            text=True,
        )

    def _receipt(self, gate_id: str = GATE_ID, command: str = COMMAND) -> None:
        result = self._flowctl("receipt", "--gate", gate_id, "--command", command)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def _check(self, gate_id: str = GATE_ID, command: str = COMMAND) -> subprocess.CompletedProcess:
        return self._flowctl("check", "--gate", gate_id, "--command", command)

    def _receipt_path(self, gate_id: str = GATE_ID) -> Path:
        return self.tmpdir / ".flow" / "tmp" / "green-receipts" / f"{self._git('rev-parse', 'HEAD')[:8]}-{gate_id}.json"

    def _rewrite_receipt(self, **updates: object) -> None:
        path = self._receipt_path()
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt.update(updates)
        path.write_text(json.dumps(receipt), encoding="utf-8")

    def _receipt_dir(self) -> Path:
        path = self.tmpdir / ".flow" / "tmp" / "green-receipts"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _write_receipt(
        self,
        head_sha: str,
        *,
        command: str = COMMAND,
        timestamp: Optional[str] = None,
        filename_sha8: Optional[str] = None,
    ) -> Path:
        sha8 = filename_sha8 if filename_sha8 is not None else head_sha[:8]
        path = self._receipt_dir() / f"{sha8}-{GATE_ID}.json"
        path.write_text(
            json.dumps({
                "schema": 1,
                "head_sha": head_sha,
                "gate_id": GATE_ID,
                "command_sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
                "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
            }),
            encoding="utf-8",
        )
        return path


class GateReceiptTestCase(GateReceiptHarness):
    """Base receipt/check contract cases."""

    def test_receipt_round_trip_body_and_path(self) -> None:
        self._receipt()
        path = self._receipt_path()
        self.assertTrue(path.is_file())
        receipt = json.loads(path.read_text(encoding="utf-8"))
        head = self._git("rev-parse", "HEAD")
        self.assertEqual(
            set(receipt),
            {"schema", "head_sha", "gate_id", "command_sha256", "timestamp"},
        )
        self.assertEqual(receipt["schema"], 1)
        self.assertEqual(receipt["head_sha"], head)
        self.assertEqual(receipt["gate_id"], GATE_ID)
        self.assertEqual(
            receipt["command_sha256"],
            hashlib.sha256(COMMAND.encode("utf-8")).hexdigest(),
        )

    def test_check_honors_fresh_matching_clean_receipt(self) -> None:
        self._receipt()
        result = self._check()
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("HONORED:", result.stdout)

    def test_check_rejects_dirty_tracked_code(self) -> None:
        self._receipt()
        (self.tmpdir / "src" / "app.py").write_text("print('dirty')\n", encoding="utf-8")
        self.assertEqual(self._check().returncode, 1)

    def test_check_rejects_dirty_flow_bin(self) -> None:
        self._receipt()
        path = self.tmpdir / ".flow" / "bin" / "flowctl.py"
        path.parent.mkdir(parents=True)
        path.write_text("dirty\n", encoding="utf-8")
        self.assertEqual(self._check().returncode, 1)

    def test_check_rejects_dirty_flow_config(self) -> None:
        self._receipt()
        path = self.tmpdir / ".flow" / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
        self.assertEqual(self._check().returncode, 1)

    def test_check_ignores_flow_state_outside_bin_and_config(self) -> None:
        self._receipt()
        path = self.tmpdir / ".flow" / "tasks" / "x.md"
        path.parent.mkdir(parents=True)
        path.write_text("state\n", encoding="utf-8")
        self.assertEqual(self._check().returncode, 0)

    def test_check_rejects_moved_head(self) -> None:
        self._receipt()
        self._commit("docs/next.md", "next\n", "next")
        self.assertEqual(self._check().returncode, 1)

    def test_check_rejects_different_command(self) -> None:
        self._receipt()
        self.assertEqual(self._check(command="different command").returncode, 1)

    def test_check_rejects_stale_receipt(self) -> None:
        self._receipt()
        self._rewrite_receipt(
            timestamp=(datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        )
        self.assertEqual(self._check().returncode, 1)

    def test_check_rejects_future_receipt(self) -> None:
        self._receipt()
        self._rewrite_receipt(
            timestamp=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        )
        self.assertEqual(self._check().returncode, 1)

    def test_check_rejects_bad_schema(self) -> None:
        self._receipt()
        self._rewrite_receipt(schema=2)
        self.assertEqual(self._check().returncode, 1)

    def test_check_rejects_malformed_receipt_without_traceback(self) -> None:
        self._receipt()
        self._receipt_path().write_bytes(b"not json")
        result = self._check()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_check_rejects_missing_receipts_directory(self) -> None:
        self._receipt()
        shutil.rmtree(self.tmpdir / ".flow" / "tmp" / "green-receipts")
        self.assertEqual(self._check().returncode, 1)

    def test_non_git_repo_check_is_run_and_receipt_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            non_repo = Path(raw)
            check = self._flowctl("check", "--gate", GATE_ID, "--command", COMMAND, cwd=non_repo)
            receipt = self._flowctl("receipt", "--gate", GATE_ID, "--command", COMMAND, cwd=non_repo)
        self.assertEqual(check.returncode, 1)
        self.assertEqual(receipt.returncode, 2)

    def test_check_rejects_leading_space_flow_lookalike_dirt(self) -> None:
        # A path in a directory literally named " .flow" (leading space) is
        # NOT the ignorable .flow/ state dir. Normalization must preserve the
        # whitespace so the dirt fails the probe (review round 1 fail-open).
        self._receipt()
        path = self.tmpdir / " .flow" / "tasks" / "x.md"
        path.parent.mkdir(parents=True)
        path.write_text("dirt\n", encoding="utf-8")
        result = self._check()
        self.assertEqual(result.returncode, 1, result.stderr or result.stdout)

    def test_check_rejects_extreme_offset_timestamp_without_traceback(self) -> None:
        # Parseable-but-overflowing value: year 1 with a +23:59 offset raises
        # OverflowError in astimezone(); must fail closed, never crash.
        self._receipt()
        self._rewrite_receipt(timestamp="0001-01-01T00:00:00+23:59")
        result = self._check()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    @unittest.skipUnless(os.name == "posix", "PATH shim requires a POSIX shell")
    def test_check_git_status_failure_is_error_exit_2(self) -> None:
        # A failing `git status` inside a resolvable repo is a real tooling
        # error (exit 2+), not the ordinary run-the-full-gate exit 1.
        self._receipt()
        real_git = shutil.which("git")
        assert real_git is not None
        shim_dir = self.tmpdir / "shim-bin"
        shim_dir.mkdir()
        shim = shim_dir / "git"
        shim.write_text(
            "#!/bin/sh\n"
            'for a in "$@"; do case "$a" in status) exit 128;; esac; done\n'
            f'exec "{real_git}" "$@"\n',
            encoding="utf-8",
        )
        shim.chmod(0o755)
        env = dict(os.environ)
        env["PATH"] = f"{shim_dir}{os.pathsep}{env.get('PATH', '')}"
        result = subprocess.run(
            [sys.executable, str(FLOWCTL_PY), "gate", "check", "--gate", GATE_ID, "--command", COMMAND],
            cwd=self.tmpdir,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)

    def test_gate_id_validation_at_both_boundaries(self) -> None:
        invalid_ids = ["../x", "a/b", "..\\x", ".", "..", "", "a" * 65, "-x", ".x"]
        for gate_id in invalid_ids:
            for command in ("receipt", "check"):
                with self.subTest(gate_id=gate_id, command=command):
                    result = self._flowctl(
                        command, "--gate", gate_id, "--command", COMMAND
                    )
                    self.assertEqual(result.returncode, 2, result.stderr or result.stdout)


class GateReceiptAncestorWalkTestCase(GateReceiptHarness):
    """fn-116 ancestor-walk and receipt-retention contract matrix."""

    def test_ancestor_receipt_honors_after_flow_only_commit(self) -> None:
        self._receipt()
        receipt_head = self._git("rev-parse", "HEAD")
        self._commit(".flow/tasks/state.md", "state\n", "flow state")
        result = self._check()
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn(receipt_head[:8], result.stdout)

    def test_walk_rejects_non_ignored_commit_path(self) -> None:
        self._receipt()
        self._commit("docs/next.md", "next\n", "docs change")
        self.assertEqual(self._check().returncode, 1)

    def test_walk_rejects_diverged_sibling_receipt(self) -> None:
        starting_branch = self._git("branch", "--show-current")
        self._git("checkout", "-qb", "receipt-branch")
        receipt_head = self._commit(".flow/tasks/receipt.md", "receipt\n", "receipt branch")
        self._write_receipt(receipt_head)
        self._git("checkout", "-q", starting_branch)
        self._commit(".flow/tasks/current.md", "current\n", "current branch")
        self.assertEqual(self._check().returncode, 1)

    def test_walk_skips_filename_body_sha_mismatch(self) -> None:
        receipt_head = self._git("rev-parse", "HEAD")
        forged_prefix = "0" * 8 if receipt_head[:8] != "0" * 8 else "1" * 8
        self._write_receipt(receipt_head, filename_sha8=forged_prefix)
        self._commit(".flow/tasks/state.md", "state\n", "flow state")
        self.assertEqual(self._check().returncode, 1)

    def test_corrupt_candidate_does_not_abort_later_valid_candidate(self) -> None:
        self._receipt()
        receipt_head = self._git("rev-parse", "HEAD")
        self._commit(".flow/tasks/state.md", "state\n", "flow state")
        (self._receipt_dir() / f"corrupt-{GATE_ID}.json").write_text("not json", encoding="utf-8")
        result = self._check()
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn(receipt_head[:8], result.stdout)

    def test_walk_skips_symlinked_candidate(self) -> None:
        self._receipt()
        path = self._receipt_path()
        outside = Path(tempfile.mkdtemp()).resolve()
        try:
            target = outside / "receipt.json"
            target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            path.unlink()
            path.symlink_to(target)
            self._commit(".flow/tasks/state.md", "state\n", "flow state")
            self.assertEqual(self._check().returncode, 1)
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_walk_evaluates_only_eight_newest_candidates(self) -> None:
        oldest_head = ""
        base_timestamp = datetime.now(timezone.utc)
        for index in range(9):
            commit = self._commit(
                f".flow/tasks/state-{index}.md", f"{index}\n", f"flow state {index}"
            )
            if index == 0:
                oldest_head = commit
            self._write_receipt(
                commit,
                command=COMMAND if index == 0 else "mismatched command",
                timestamp=(base_timestamp + timedelta(seconds=index)).isoformat(),
            )
        self._commit(".flow/tasks/final.md", "final\n", "final flow state")
        result = self._check()
        self.assertEqual(result.returncode, 1, result.stderr or result.stdout)
        self.assertNotIn(oldest_head[:8], result.stdout)

    def test_walk_tries_next_candidate_after_command_fingerprint_mismatch(self) -> None:
        older_head = self._git("rev-parse", "HEAD")
        self._write_receipt(older_head)
        newer_head = self._commit(".flow/tasks/newer.md", "newer\n", "newer state")
        self._write_receipt(newer_head, command="mismatched command")
        self._commit(".flow/tasks/final.md", "final\n", "final state")
        result = self._check()
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn(older_head[:8], result.stdout)

    def test_walk_tied_timestamps_use_filename_order(self) -> None:
        first_head = self._git("rev-parse", "HEAD")
        self._write_receipt(first_head)
        second_head = self._commit(".flow/tasks/second.md", "second\n", "second state")
        tied_timestamp = datetime.now(timezone.utc).isoformat()
        self._write_receipt(first_head, timestamp=tied_timestamp)
        self._write_receipt(second_head, timestamp=tied_timestamp)
        self._commit(".flow/tasks/final.md", "final\n", "final state")
        result = self._check()
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn(min(first_head[:8], second_head[:8]), result.stdout)

    def test_receipt_prunes_old_receipts_but_keeps_fresh_ones(self) -> None:
        old_head = self._git("rev-parse", "HEAD")
        old_path = self._write_receipt(
            old_head,
            timestamp=(datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(),
        )
        fresh_head = self._commit(".flow/tasks/state.md", "state\n", "flow state")
        fresh_path = self._write_receipt(fresh_head, filename_sha8="ffffffff")
        self._receipt()
        self.assertFalse(old_path.exists())
        self.assertTrue(fresh_path.exists())

    def test_walk_skips_symbolic_head_sha(self) -> None:
        self._write_receipt("HEAD", filename_sha8="HEAD")
        self._commit(".flow/tasks/state.md", "state\n", "flow state")
        self.assertEqual(self._check().returncode, 1)

    def test_walk_skips_abbreviated_head_sha(self) -> None:
        self._write_receipt(self._git("rev-parse", "HEAD")[:8])
        self._commit(".flow/tasks/state.md", "state\n", "flow state")
        self.assertEqual(self._check().returncode, 1)

    def test_walk_skips_non_commit_object_sha(self) -> None:
        tree_sha = self._git("rev-parse", "HEAD^{tree}")
        self._write_receipt(tree_sha)
        self._commit(".flow/tasks/state.md", "state\n", "flow state")
        self.assertEqual(self._check().returncode, 1)


class GateReceiptCompletionRegressionsTestCase(GateReceiptHarness):
    """fn-102 completion-review regressions: full-sha compare, backslash, git errors."""

    def test_check_fails_closed_on_full_head_sha_mismatch_same_path(self) -> None:
        # Rewrite head_sha IN PLACE (path/sha8 unchanged) so the probe reaches
        # the full-SHA comparison rather than missing on the filename lookup.
        self._receipt()
        real_head = self._git("rev-parse", "HEAD")
        forged = real_head[:8] + ("0" * (len(real_head) - 8))
        self.assertNotEqual(forged, real_head)
        self._rewrite_receipt(head_sha=forged)
        result = self._check()
        self.assertEqual(result.returncode, 1, result.stderr or result.stdout)

    def test_check_counts_literal_backslash_path_as_dirty(self) -> None:
        # ".flow\tasks\x.md" on POSIX is a root-level FILE whose name contains
        # backslashes; normalization must not alias it into the .flow/ ignore set.
        self._receipt()
        (self.tmpdir / ".flow\\tasks\\x.md").write_text("dirt", encoding="utf-8")
        result = self._check()
        self.assertEqual(result.returncode, 1, result.stderr or result.stdout)

    def test_repo_probe_distinguishes_git_errors_from_not_a_repo(self) -> None:
        # Our branch logic, probed in-process: rev-parse failures whose stderr
        # is NOT "not a git repository" (dubious ownership, corruption,
        # permissions) must surface the "git error:" sentinel that the CLI
        # maps to exit 2+, never the quiet exit-1 "not a git repo" fallback.
        # (git itself reports broken gitdir pointers and unreadable .git dirs
        # as "not a git repository", so those legitimately stay exit 1 - the
        # taxonomy is git's; this pins OUR mapping of everything else.)
        import importlib.util
        from unittest import mock

        spec = importlib.util.spec_from_file_location(
            "flowctl_gate_repo_probe", str(FLOWCTL_PY)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd, 128, stdout="",
                stderr="fatal: detected dubious ownership in repository at '/x'",
            )

        with mock.patch.object(mod.subprocess, "run", side_effect=fake_run):
            root, head, err = mod._gate_repo_and_head()
        self.assertIsNone(root)
        self.assertTrue(err and err.startswith("git error:"), err)

        def fake_run_outside(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd, 128, stdout="",
                stderr="fatal: not a git repository (or any of the parent directories): .git",
            )

        # The genuinely-outside case must be probed from a cwd with NO .git
        # anywhere on the upward walk (the metadata-presence check is cwd-based).
        outside = Path(tempfile.mkdtemp()).resolve()
        try:
            os.chdir(outside)
            with mock.patch.object(mod.subprocess, "run", side_effect=fake_run_outside):
                root, head, err = mod._gate_repo_and_head()
        finally:
            os.chdir(self.tmpdir)
            shutil.rmtree(outside, ignore_errors=True)
        self.assertEqual(err, "not a git repo")

    def test_check_broken_git_metadata_exits_2(self) -> None:
        # A .git FILE with an invalid gitdir target: git reports "not a git
        # repository", but metadata EXISTS - our walk detects it and maps to
        # a real error (exit 2+), never the quiet run-full-gates fallback.
        self._receipt()
        git_dir = self.tmpdir / ".git"
        backup = self.tmpdir / ".git-backup"
        git_dir.rename(backup)
        (self.tmpdir / ".git").write_text("gitdir: /nonexistent/broken\n", encoding="utf-8")
        try:
            result = self._check()
            self.assertGreaterEqual(result.returncode, 2, result.stderr or result.stdout)
        finally:
            (self.tmpdir / ".git").unlink()
            backup.rename(git_dir)

    def test_check_dangling_git_symlink_exits_2(self) -> None:
        # .git as a DANGLING symlink: present-but-broken metadata. exists()
        # would follow the link and report absent; lexists must catch it.
        self._receipt()
        git_dir = self.tmpdir / ".git"
        backup = self.tmpdir / ".git-backup"
        git_dir.rename(backup)
        (self.tmpdir / ".git").symlink_to("/nonexistent/broken-target")
        try:
            result = self._check()
            self.assertGreaterEqual(result.returncode, 2, result.stderr or result.stdout)
        finally:
            (self.tmpdir / ".git").unlink()
            backup.rename(git_dir)

    def test_receipt_refuses_symlinked_receipts_dir(self) -> None:
        # A symlinked .flow/tmp would redirect the receipt write outside the
        # workspace - the containment guard must refuse (exit 2), never write.
        outside = Path(tempfile.mkdtemp()).resolve()
        try:
            flow_tmp = self.tmpdir / ".flow" / "tmp"
            flow_tmp.parent.mkdir(parents=True, exist_ok=True)
            if flow_tmp.exists():
                shutil.rmtree(flow_tmp)
            flow_tmp.symlink_to(outside, target_is_directory=True)
            result = self._flowctl("receipt", "--gate", GATE_ID, "--command", COMMAND)
            self.assertGreaterEqual(result.returncode, 2, result.stderr or result.stdout)
            self.assertFalse(list(outside.rglob("*.json")), "receipt escaped the workspace")
            self.assertFalse((outside / "green-receipts").exists(),
                             "mkdir side-effect escaped the workspace before the guard")
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_receipt_refuses_dirty_tree(self) -> None:
        # Gates on a dirty tree exercised HEAD+dirt, not HEAD - the receipt
        # must be refused (exit 1, nothing written). Ignore-set dirt (.flow
        # scratch) does not block.
        (self.tmpdir / "src" / "app.py").write_text("print('dirty')\n", encoding="utf-8")
        result = self._flowctl("receipt", "--gate", GATE_ID, "--command", COMMAND)
        self.assertEqual(result.returncode, 1, result.stderr or result.stdout)
        self.assertFalse(self._receipt_path().exists())
        self._git("checkout", "--", "src/app.py")
        scratch = self.tmpdir / ".flow" / "tmp" / "scratch.txt"
        scratch.parent.mkdir(parents=True, exist_ok=True)
        scratch.write_text("ok", encoding="utf-8")
        self._receipt()
        self.assertTrue(self._receipt_path().exists())

    def test_check_refuses_symlinked_receipts_dir(self) -> None:
        # Read-side symmetry: a symlinked .flow/tmp pointing at a shared dir
        # holding a VALID receipt must not be honored (exit 1).
        self._receipt()
        outside = Path(tempfile.mkdtemp()).resolve()
        try:
            flow_tmp = self.tmpdir / ".flow" / "tmp"
            shutil.move(str(flow_tmp), str(outside / "tmp"))
            flow_tmp.symlink_to(outside / "tmp", target_is_directory=True)
            result = self._check()
            self.assertEqual(result.returncode, 1, result.stderr or result.stdout)
        finally:
            if flow_tmp.is_symlink():
                flow_tmp.unlink()
                shutil.move(str(outside / "tmp"), str(flow_tmp))
            shutil.rmtree(outside, ignore_errors=True)

    def test_check_refuses_symlinked_receipt_file(self) -> None:
        self._receipt()
        path = self._receipt_path()
        real = path.with_suffix(".real.json")
        path.rename(real)
        path.symlink_to(real)
        result = self._check()
        self.assertEqual(result.returncode, 1, result.stderr or result.stdout)

    def test_check_outside_repo_exits_1(self) -> None:
        outside = Path(tempfile.mkdtemp()).resolve()
        try:
            result = self._flowctl("check", "--gate", GATE_ID, "--command", COMMAND, cwd=outside)
            self.assertEqual(result.returncode, 1, result.stderr or result.stdout)
        finally:
            shutil.rmtree(outside, ignore_errors=True)
