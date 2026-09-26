"""Exercise the shipped map wrapper with a local clawpatch stub."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "map.sh"


@unittest.skipIf(os.name == "nt" or not shutil.which("bash"), "POSIX executable stubs")
class BundledMapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        stub = self.bin / "clawpatch"
        stub.write_text('''#!/usr/bin/env bash
case "$1" in
--version) echo "clawpatch ${TEST_VERSION:-0.4.0}" ;;
init) mkdir -p .clawpatch; echo init >> calls ;;
map) printf '%s\\n' "$@" >> calls; mkdir -p .clawpatch/features; echo live-output; exit "${TEST_EXIT:-0}" ;;
esac
''')
        stub.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"], FLOWCTL="/nonexistent")
        for key in ("FLOW_RALPH", "REVIEW_RECEIPT_PATH"):
            self.env.pop(key, None)

    def run_map(self, arguments="", **env):
        return subprocess.run(["bash", str(SCRIPT), arguments], cwd=self.root,
                              env=dict(self.env, **env), capture_output=True, text=True)

    def test_default_init_and_rerun_preserve_user_ignore(self):
        result = self.run_map("-- --paths *.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "calls").read_text().splitlines(),
                         ["init", "map", "--source", "heuristic", "--paths", "*.py"])
        ignore = self.root / ".clawpatch/.gitignore"
        self.assertIn("!.gitignore", ignore.read_text())
        ignore.write_text("custom\n")
        result = self.run_map("--source=agent")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(ignore.read_text(), "custom\n")
        self.assertEqual((self.root / "calls").read_text().count("init"), 1)
        self.assertFalse((self.root / ".gitignore").exists())

    def test_version_degrades_and_map_failure_propagates(self):
        result = self.run_map(TEST_VERSION="0.5.0", TEST_EXIT="7")
        self.assertEqual(result.returncode, 7)
        self.assertIn("outside supported range", result.stderr)
        self.assertIn("live-output", result.stdout)

    def test_block_never_touches_review_receipt(self):
        receipt = self.root / "receipt.json"
        receipt.write_text("owned by reviewer")
        result = self.run_map(REVIEW_RECEIPT_PATH=str(receipt))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(receipt.read_text(), "owned by reviewer")
        self.assertFalse((self.root / "calls").exists())

    def test_missing_install_reports_instruction_without_writes(self):
        # Keep shell utilities, exclude our executable stub and user tool paths.
        if shutil.which("clawpatch", path="/usr/bin:/bin"):
            self.skipTest("system clawpatch installed")
        result = self.run_map(PATH="/usr/bin:/bin")
        self.assertEqual(result.returncode, 1)
        self.assertIn("pnpm add -g clawpatch", result.stderr)
        self.assertFalse((self.root / ".clawpatch").exists())

    def test_invalid_source_stops_before_init(self):
        result = self.run_map("--source --")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.root / "calls").exists())
