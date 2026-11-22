"""Unit tests for ``flowctl usage`` (cmd_usage) end-to-end via subprocess.

Exercises the real CLI entrypoint (``python3 <flowctl.py> usage``) with a
controlled cwd per case:

1. Bundled hit — real plugin tree; empty cwd with no ``.flow`` → plugin
   ``templates/usage.md``.
2. ``.flow`` fallback — isolated copy of ``flowctl.py`` (no sibling
   ``templates/``); cwd is a temp repo with ``.flow/usage.md``.
3. Neither — same isolated copy; cwd has ``.flow/`` but no ``usage.md`` →
   exit 1 and the canonical error message.
4. ``--orchestration`` — the bridge and model-steering recipes, served the
   same way from ``templates/usage-orchestration.md`` by flowctl.py (the
   launchers send only bare ``usage`` to the bootstrap fast path); plain
   ``usage`` keeps a pointer heading to them on both paths.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOWCTL_PY = ROOT / "scripts" / "flowctl.py"
BOOTSTRAP_PY = ROOT / "scripts" / "flowctl_bootstrap.py"
BUNDLED_USAGE = ROOT / "templates" / "usage.md"
BUNDLED_ORCHESTRATION = ROOT / "templates" / "usage-orchestration.md"

NO_GUIDE_MSG = "No usage guide found"
LOCAL_SENTINEL = "LOCAL COPY SENTINEL"


def _run_usage(flowctl_py: Path, cwd: Path, *extra: str) -> subprocess.CompletedProcess:
    # UTF-8 both ways: usage.md carries non-ASCII, and a Windows console
    # encoding would otherwise mangle it in transit.
    return subprocess.run(
        [sys.executable, str(flowctl_py), "usage", *extra],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


class TestCmdUsage(unittest.TestCase):
    """Real-subprocess coverage of cmd_usage resolution order."""

    def test_bundled_hit_from_plugin_tree(self) -> None:
        # cwd has no .flow; flowctl.py still lives under the real plugin, so
        # Path(__file__).parent.parent / templates / usage.md resolves.
        self.assertTrue(FLOWCTL_PY.is_file(), f"missing {FLOWCTL_PY}")
        self.assertTrue(BUNDLED_USAGE.is_file(), f"missing {BUNDLED_USAGE}")

        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assertFalse((cwd / ".flow").exists())
            result = _run_usage(FLOWCTL_PY, cwd)

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            result.stdout, BUNDLED_USAGE.read_text(encoding="utf-8")
        )

    def test_flow_fallback_when_bundled_missing(self) -> None:
        # Copy only flowctl.py so ../templates/usage.md does not exist next to it.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fake_py = tmp / "fake" / "bin" / "flowctl.py"
            fake_py.parent.mkdir(parents=True)
            shutil.copy2(FLOWCTL_PY, fake_py)

            repo = tmp / "repo"
            flow_dir = repo / ".flow"
            flow_dir.mkdir(parents=True)
            (flow_dir / "usage.md").write_text(LOCAL_SENTINEL + "\n", encoding="utf-8")

            # Sanity: isolated tree has no templates/usage.md next to the copy.
            self.assertFalse(
                (fake_py.parent.parent / "templates" / "usage.md").is_file()
            )

            result = _run_usage(fake_py, repo)

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(LOCAL_SENTINEL, result.stdout)

    def test_neither_exits_one_with_error(self) -> None:
        # Same isolated copy; cwd has .flow so get_flow_dir resolves inside the
        # temp tree (not an enclosing real repo), but usage.md is absent.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fake_py = tmp / "fake" / "bin" / "flowctl.py"
            fake_py.parent.mkdir(parents=True)
            shutil.copy2(FLOWCTL_PY, fake_py)

            empty2 = tmp / "empty2"
            (empty2 / ".flow").mkdir(parents=True)
            # Deliberately no usage.md under .flow/

            result = _run_usage(fake_py, empty2)

        self.assertEqual(result.returncode, 1)
        self.assertIn(NO_GUIDE_MSG, result.stderr)



class TestCmdUsageOrchestration(unittest.TestCase):
    """`flowctl usage --orchestration` and the pointer left in plain usage."""

    def test_plain_usage_points_old_snippet_readers_at_orchestration(self) -> None:
        # Instruction blocks written before the split say: run `flowctl usage`
        # and follow "Orchestration & model steering". That heading must still
        # resolve in plain usage and name the command that prints the recipes.
        with tempfile.TemporaryDirectory() as tmp:
            for entry in (FLOWCTL_PY, BOOTSTRAP_PY):
                result = _run_usage(entry, Path(tmp))
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                self.assertIn("## Orchestration & model steering", result.stdout)
                self.assertIn("flowctl usage --orchestration", result.stdout)
                self.assertNotIn("codex exec", result.stdout)

    def test_orchestration_prints_bundled_recipes(self) -> None:
        expected = BUNDLED_ORCHESTRATION.read_text(encoding="utf-8")
        self.assertIn("## Orchestration & model steering", expected)
        self.assertIn("codex exec", expected)
        with tempfile.TemporaryDirectory() as tmp:
            result = _run_usage(FLOWCTL_PY, Path(tmp), "--orchestration")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout, expected)

    def test_help_documents_the_flag(self) -> None:
        result = subprocess.run(
            [sys.executable, str(FLOWCTL_PY), "usage", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("--orchestration", result.stdout)

    def test_missing_orchestration_template_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bindir = tmp / "fake" / "bin"
            bindir.mkdir(parents=True)
            shutil.copy2(FLOWCTL_PY, bindir / "flowctl.py")
            repo = tmp / "repo"
            (repo / ".flow").mkdir(parents=True)
            result = _run_usage(bindir / "flowctl.py", repo, "--orchestration")
        self.assertEqual(result.returncode, 1, msg=result.stdout)
        self.assertIn(NO_GUIDE_MSG, result.stderr)
        self.assertIn("usage-orchestration.md", result.stderr)


if __name__ == "__main__":
    unittest.main()
