"""Unit tests for `flowctl repo-map list / show / since-ref` (fn-50.2).

These readers parse clawpatch's `.clawpatch/features/*.json` index. They
BYPASS the `ensure_flow_exists()` guard — they gate on `.clawpatch/`
presence instead — so the prime DE7 detection works without special-casing
in a repo that has clawpatch state but no `.flow/`.

CI matrix: ubuntu-latest + macos-latest + windows-latest, bash + Python
3.11. Tests stay self-contained: every fixture is built in a temp dir;
production paths are exercised via `subprocess` against `flowctl.py`
(NOT via importing handlers — per
`bug/test-failures/test-production-path-not-parallel-construction-2026-05-21`
memory). No `clawpatch` invocation in tests; the checked-in fixtures at
`tests/fixtures/clawpatch-map/` are the source of truth.

Run:
    python -m unittest discover -s plugins/flow-next/tests \
        -p "test_repo_map.py" -v
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent
FLOWCTL_PY = PLUGIN_DIR / "scripts" / "flowctl.py"
FIXTURES_ROOT = HERE.parent / "fixtures" / "clawpatch-map"


def _run(
    *args: str, cwd: str | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    """Invoke `python flowctl.py <args>` from `cwd` (defaults to a temp dir)."""
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    return subprocess.run(
        [sys.executable, str(FLOWCTL_PY), *args],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=cwd,
        env=proc_env,
    )


def _copy_fixture_clawpatch(dest: Path) -> None:
    """Copy `tests/fixtures/clawpatch-map/.clawpatch/` into `dest/.clawpatch/`."""
    src = FIXTURES_ROOT / ".clawpatch"
    shutil.copytree(src, dest / ".clawpatch")


class RepoMapListAbsent(unittest.TestCase):
    """When `.clawpatch/` is missing, `list` returns count=0 cleanly."""

    def test_list_json_missing_clawpatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = _run("repo-map", "list", "--json", cwd=td)
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            payload = json.loads(res.stdout)
            self.assertTrue(payload["success"])
            self.assertEqual(payload["count"], 0)
            self.assertEqual(payload["features"], [])
            self.assertFalse(payload["clawpatch_present"])
            # No parse_skipped key when zero (R9: count reported only when > 0).
            self.assertNotIn("parse_skipped", payload)

    def test_list_count_plain_missing_clawpatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = _run("repo-map", "list", "--count", cwd=td)
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            self.assertEqual(res.stdout.strip(), "0")

    def test_list_plain_missing_clawpatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = _run("repo-map", "list", cwd=td)
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            self.assertIn(".clawpatch/", res.stdout)


class RepoMapListPresent(unittest.TestCase):
    """Fixture-driven parsing: 1 valid + 1 schema-mismatch + 1 malformed."""

    def setUp(self) -> None:
        self._td = tempfile.mkdtemp()
        _copy_fixture_clawpatch(Path(self._td))

    def tearDown(self) -> None:
        shutil.rmtree(self._td, ignore_errors=True)

    def test_list_json_counts_only_valid(self) -> None:
        res = _run("repo-map", "list", "--json", cwd=self._td)
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        payload = json.loads(res.stdout)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["parse_skipped"], 2)
        self.assertTrue(payload["clawpatch_present"])
        feat = payload["features"][0]
        self.assertEqual(feat["featureId"], "auth")
        self.assertEqual(feat["kind"], "module")
        self.assertEqual(
            feat["ownedFiles"], ["src/auth.ts", "src/auth.test.ts"]
        )
        self.assertEqual(feat["entrypoints"], ["src/auth.ts"])

    def test_list_stderr_diagnostics_for_skipped_files(self) -> None:
        res = _run("repo-map", "list", "--json", cwd=self._td)
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        # R9: each skip emits one stderr line. Both kinds (schemaVersion
        # mismatch + invalid JSON) must be visible.
        self.assertIn("schemaVersion=2", res.stderr)
        self.assertIn("expected=1", res.stderr)
        self.assertIn("invalid JSON", res.stderr)
        # Filenames in the diagnostic so the user can locate the offender.
        self.assertIn("invalid-schema.json", res.stderr)
        self.assertIn("malformed.json", res.stderr)

    def test_list_count_plain_reports_only_valid(self) -> None:
        res = _run("repo-map", "list", "--count", cwd=self._td)
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertEqual(res.stdout.strip(), "1")

    def test_list_plain_renders_table(self) -> None:
        res = _run("repo-map", "list", cwd=self._td)
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        # Header + the one valid row.
        self.assertIn("featureId", res.stdout)
        self.assertIn("auth", res.stdout)
        self.assertIn("Authentication module", res.stdout)
        # Skipped count surfaced in plain mode too.
        self.assertIn("2 file(s) skipped", res.stdout)


class RepoMapShow(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.mkdtemp()
        _copy_fixture_clawpatch(Path(self._td))

    def tearDown(self) -> None:
        shutil.rmtree(self._td, ignore_errors=True)

    def test_show_valid_feature_json(self) -> None:
        res = _run(
            "repo-map", "show", "--feature", "auth", "--json", cwd=self._td
        )
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        payload = json.loads(res.stdout)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["featureId"], "auth")
        self.assertEqual(payload["title"], "Authentication module")
        # `path` surfaces the on-disk source so callers can re-read raw JSON.
        self.assertTrue(payload["path"].endswith("valid.json"))

    def test_show_unknown_feature_returns_exit_3(self) -> None:
        res = _run(
            "repo-map", "show", "--feature", "no-such-id", "--json",
            cwd=self._td,
        )
        # Distinct exit code (3) so callers can differentiate "not found"
        # from generic error.
        self.assertEqual(res.returncode, 3, msg=res.stderr)
        payload = json.loads(res.stdout)
        self.assertFalse(payload["success"])
        self.assertIn("not found", payload["error"])

    def test_show_skipped_files_never_match(self) -> None:
        # The schemaVersion=2 entry carries featureId "future-feature" but
        # was skipped; show MUST NOT find it.
        res = _run(
            "repo-map", "show", "--feature", "future-feature", "--json",
            cwd=self._td,
        )
        self.assertEqual(res.returncode, 3, msg=res.stderr)

    def test_show_plain_renders_summary(self) -> None:
        res = _run(
            "repo-map", "show", "--feature", "auth", cwd=self._td
        )
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertIn("auth:", res.stdout)
        self.assertIn("Authentication module", res.stdout)
        self.assertIn("src/auth.ts", res.stdout)

    def test_show_missing_clawpatch_returns_exit_3(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = _run(
                "repo-map", "show", "--feature", "auth", "--json", cwd=td
            )
            self.assertEqual(res.returncode, 3, msg=res.stderr)
            payload = json.loads(res.stdout)
            self.assertFalse(payload["success"])
            self.assertIn(".clawpatch", payload["error"])


class RepoMapSinceRef(unittest.TestCase):
    """`since-ref` overlaps `git diff --name-only` against `ownedFiles[]`.

    Edge cases (non-git repo, unknown ref) must return JSON `success:false`
    with exit 0 so skill bash can branch on the JSON envelope without
    hitting noisy non-zero exits.
    """

    def _init_git_repo(self, td: Path) -> str:
        """Initialize a git repo + one base commit; return the base SHA."""
        env = {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t.t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t.t",
        }
        for cmd in (
            ["git", "init", "-q", "-b", "main"],
            ["git", "commit", "-q", "--allow-empty", "-m", "init"],
        ):
            r = subprocess.run(
                cmd, cwd=str(td), capture_output=True, text=True, env={**os.environ, **env}
            )
            self.assertEqual(r.returncode, 0, msg=r.stderr)
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(td), capture_output=True, text=True,
        )
        return sha.stdout.strip()

    def test_since_ref_non_git_repo_returns_success_false_exit_0(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            _copy_fixture_clawpatch(Path(td))
            # Force git to fail to find a repo even if /tmp happens to be
            # inside an outer repo: point GIT_CEILING_DIRECTORIES at td so
            # rev-parse refuses to ascend.
            env = {
                "GIT_CEILING_DIRECTORIES": td,
                "GIT_DIR": os.path.join(td, ".no-such-git-dir"),
            }
            res = _run(
                "repo-map", "since-ref", "origin/main", "--json",
                cwd=td, env=env,
            )
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            payload = json.loads(res.stdout)
            self.assertFalse(payload["success"])
            self.assertEqual(payload["error"], "not-a-git-repo")
            self.assertIn("not a git repository", res.stderr)

    def test_since_ref_unknown_ref_returns_success_false_exit_0(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _copy_fixture_clawpatch(tdp)
            self._init_git_repo(tdp)
            res = _run(
                "repo-map", "since-ref", "bogus-ref-xyz", "--json", cwd=td
            )
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            payload = json.loads(res.stdout)
            self.assertFalse(payload["success"])
            self.assertEqual(payload["error"], "unknown-ref")
            self.assertIn("unknown ref", res.stderr)

    def test_since_ref_overlaps_owned_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _copy_fixture_clawpatch(tdp)
            base_sha = self._init_git_repo(tdp)
            # Create a change to one of the valid feature's ownedFiles[].
            src_dir = tdp / "src"
            src_dir.mkdir(parents=True, exist_ok=True)
            (src_dir / "auth.ts").write_text(
                "// touched after base\nexport const x = 1;\n",
                encoding="utf-8",
            )
            env = {
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@t.t",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@t.t",
            }
            for cmd in (
                ["git", "add", "src/auth.ts"],
                ["git", "commit", "-q", "-m", "touch auth"],
            ):
                r = subprocess.run(
                    cmd, cwd=td, capture_output=True, text=True,
                    env={**os.environ, **env},
                )
                self.assertEqual(r.returncode, 0, msg=r.stderr)

            res = _run(
                "repo-map", "since-ref", base_sha, "--json", cwd=td
            )
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            payload = json.loads(res.stdout)
            self.assertTrue(payload["success"])
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["features"][0]["featureId"], "auth")
            self.assertIn("src/auth.ts", payload["changed_files"])

    def test_since_ref_no_overlap_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _copy_fixture_clawpatch(tdp)
            base_sha = self._init_git_repo(tdp)
            # Touch a file the valid fixture does NOT own.
            (tdp / "README.md").write_text("hello\n", encoding="utf-8")
            env = {
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@t.t",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@t.t",
            }
            for cmd in (
                ["git", "add", "README.md"],
                ["git", "commit", "-q", "-m", "readme"],
            ):
                r = subprocess.run(
                    cmd, cwd=td, capture_output=True, text=True,
                    env={**os.environ, **env},
                )
                self.assertEqual(r.returncode, 0, msg=r.stderr)

            res = _run(
                "repo-map", "since-ref", base_sha, "--json", cwd=td
            )
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            payload = json.loads(res.stdout)
            self.assertTrue(payload["success"])
            self.assertEqual(payload["count"], 0)
            self.assertEqual(payload["features"], [])

    def test_since_ref_absent_clawpatch_returns_count_zero(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            base_sha = self._init_git_repo(tdp)
            # No .clawpatch/ — should short-circuit cleanly.
            res = _run(
                "repo-map", "since-ref", base_sha, "--json", cwd=td
            )
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            payload = json.loads(res.stdout)
            self.assertTrue(payload["success"])
            self.assertEqual(payload["count"], 0)
            self.assertFalse(payload["clawpatch_present"])


class RepoMapArgparse(unittest.TestCase):
    """Surface-level argparse contract: required args + --json threading."""

    def test_show_missing_feature_arg_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = _run("repo-map", "show", cwd=td)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("--feature", res.stderr)

    def test_since_ref_missing_arg_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = _run("repo-map", "since-ref", cwd=td)
            self.assertNotEqual(res.returncode, 0)

    def test_repo_map_no_subcommand_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = _run("repo-map", cwd=td)
            self.assertNotEqual(res.returncode, 0)

    def test_all_three_subcommands_accept_json_flag(self) -> None:
        """R3: --json threaded through each subcommand (per fn-44 memory)."""
        with tempfile.TemporaryDirectory() as td:
            # list --json — already tested; smoke for argparse acceptance.
            res = _run("repo-map", "list", "--json", cwd=td)
            self.assertEqual(res.returncode, 0)
            self.assertIn('"success"', res.stdout)
            # show --json — needs --feature; missing feature is a usage error,
            # but --json being parsed at all is the contract.
            res = _run(
                "repo-map", "show", "--feature", "x", "--json", cwd=td
            )
            # 3 = not found / no clawpatch — but JSON output regardless.
            self.assertIn('"success"', res.stdout)
            # since-ref --json
            res = _run(
                "repo-map", "since-ref", "HEAD", "--json", cwd=td
            )
            self.assertIn('"success"', res.stdout)


if __name__ == "__main__":
    unittest.main()
