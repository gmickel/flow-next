"""Shared flowctl test support: the runner behaves like a script run of
flowctl.py (fn-256 R1), and the per-class memory repo template hands every
test an isolated copy (fn-256 R3)."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling test helpers
from flowctl_test_support import FLOWCTL_CMD, FLOWCTL_SCRIPT, MemoryRepoTemplate

HERE = Path(__file__).resolve().parent


def _run(argv):
    return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", timeout=60)


class RunnerParityTests(unittest.TestCase):
    def test_help_and_usage_error_match_a_script_run(self):
        for args in (["--help"], [], ["no-such-command"]):
            with self.subTest(args=args):
                script = _run([sys.executable, str(FLOWCTL_SCRIPT), *args])
                runner = _run([*FLOWCTL_CMD, *args])
                self.assertEqual(
                    (runner.returncode, runner.stdout, runner.stderr),
                    (script.returncode, script.stdout, script.stderr),
                )

    def test_missing_runner_fails_with_its_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy2(HERE / "flowctl_test_support.py", tmp)
            proc = subprocess.run(
                [sys.executable, "-c", "import flowctl_test_support"],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(str(Path(tmp).resolve() / "flowctl_runner.py"), proc.stderr)


class MemoryRepoTemplateTests(MemoryRepoTemplate, unittest.TestCase):
    def test_each_copy_is_isolated_from_other_tests(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first = self.init_repo(Path(a))
            (first / "mutated.md").write_text("x", encoding="utf-8")
            second = self.init_repo(Path(b))
            self.assertTrue((second / "README.md").is_file())
            self.assertFalse((second / "mutated.md").exists())
            self.assertFalse((self._template / ".flow" / "memory" / "mutated.md").exists())

    def test_copy_failure_names_the_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "not-a-dir"
            dest.write_text("", encoding="utf-8")
            with self.assertRaises(OSError) as ctx:
                self.init_repo(dest)
            # The exception text quotes the path (Windows doubles its backslashes).
            self.assertEqual(ctx.exception.filename, str(dest))


if __name__ == "__main__":
    unittest.main()
