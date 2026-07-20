"""Unit tests for `flowctl repo-map list` (fn-50.2; show/since-ref removed in fn-111).

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
        # kind is a member of upstream `featureKinds` (Zod enum); "service"
        # is one of the canonical values (see clawpatch src/types.ts).
        self.assertEqual(feat["kind"], "service")
        # Confidence is clawpatch's "high" | "medium" | "low" Zod enum
        # (NOT a numeric score) — locked here so future drift surfaces fast.
        self.assertEqual(feat["confidence"], "high")
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


class RepoMapArgparse(unittest.TestCase):
    """Surface-level argparse contract: list + --json threading."""

    def test_repo_map_no_subcommand_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = _run("repo-map", cwd=td)
            self.assertNotEqual(res.returncode, 0)

    def test_list_accepts_json_flag(self) -> None:
        """R3: --json threaded through list (per fn-44 memory)."""
        with tempfile.TemporaryDirectory() as td:
            res = _run("repo-map", "list", "--json", cwd=td)
            self.assertEqual(res.returncode, 0)
            self.assertIn('"success"', res.stdout)


if __name__ == "__main__":
    unittest.main()
