"""Unit tests for ``flowctl usage`` (cmd_usage) end-to-end via subprocess.

Exercises the real CLI entrypoint (``python3 <flowctl.py> usage``) with a
controlled cwd per case:

1. Bundled hit — real plugin tree; empty cwd with no ``.flow`` → plugin
   ``templates/usage.md``.
2. ``.flow`` fallback — isolated copy of ``flowctl.py`` (no sibling
   ``templates/``); cwd is a temp repo with ``.flow/usage.md``.
3. Neither — same isolated copy; cwd has ``.flow/`` but no ``usage.md`` →
   exit 1 and the canonical error message.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOWCTL_PY = ROOT / "scripts" / "flowctl.py"
BUNDLED_USAGE = ROOT / "templates" / "usage.md"

USAGE_GUIDE_HEADER = "# Flow-Next Usage Guide"
NO_GUIDE_MSG = "No usage guide found"
LOCAL_SENTINEL = "LOCAL COPY SENTINEL"


def _run_usage(flowctl_py: Path, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(flowctl_py), "usage"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
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
        self.assertTrue(
            result.stdout.startswith(USAGE_GUIDE_HEADER),
            f"stdout should start with bundled guide header, got: {result.stdout[:80]!r}",
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


if __name__ == "__main__":
    unittest.main()
