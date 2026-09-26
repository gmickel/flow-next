"""Execute the complete shipped create/update block, including prose-era skips."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "make-pr-create.sh"


@unittest.skipIf(os.name == "nt" or not shutil.which("bash") or not shutil.which("jq"), "POSIX stubs and jq")
class BundledMakePrTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name, body in {
            "git": '''case "$1" in
branch) echo feature ;;
rev-parse) echo abc ;;
push) echo push >> "$CALLS" ;;
esac''',
            "gh": '''printf '%s\\n' "$*" >> "$CALLS"
case "$1 $2" in
"pr create") echo https://example.com/project/pull/9 ;;
"pr edit") : ;;
"pr view") if [[ "$*" == *"--json url"* ]]; then echo https://example.com/project/pull/8; else echo 8; fi ;;
"api repos/"*) : ;;
esac''',
            "flowctl": 'echo \'{"active": false}\'',
            "sleep": ":",
        }.items():
            path = self.bin / name
            path.write_text("#!/usr/bin/env bash\n" + body + "\n")
            path.chmod(0o755)
        self.body = self.root / "body.md"
        self.body.write_text("Grounded body\n")
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        CALLS=str(self.root / "calls"), FLOWCTL=str(self.bin / "flowctl"),
                        RALPH="0", AUTONOMOUS="0", OPEN_ITEMS_COUNT="0", DRAFT_FORCE="auto",
                        BODY_FILE=str(self.body), BASE_REF="origin/main", PR_TITLE="Title",
                        REPO_ROOT=str(self.root), PHASE0_CONTEXT="{}", SPEC_ID="fn-1")

    def run_script(self, **env):
        return subprocess.run(["bash", "-c", 'set -e; source "$SCRIPT"; printf "RESULT=%s\\n" "$PR_URL"'],
                              cwd=self.root, env=dict(self.env, SCRIPT=str(SCRIPT), **env),
                              text=True, capture_output=True)

    def test_create_retains_url_and_body(self):
        result = self.run_script(UPDATE_MODE="0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RESULT=https://example.com/project/pull/9", result.stdout)
        self.assertIn("pr create --title Title --body-file", (self.root / "calls").read_text())
        self.assertEqual(self.body.read_text(), "Grounded body\n")

    def test_update_never_runs_create(self):
        result = self.run_script(UPDATE_MODE="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = (self.root / "calls").read_text()
        self.assertIn("pr edit 8 --body-file", calls)
        self.assertNotIn("pr create", calls)
        self.assertIn("RESULT=https://example.com/project/pull/8", result.stdout)

    def test_changed_closed_head_never_pushes(self):
        result = self.run_script(PHASE0_CONTEXT=json.dumps({"spec_closed": True, "head": "old", "branch": "feature"}))
        self.assertEqual(result.returncode, 1)
        self.assertIn("head changed", result.stderr)
        self.assertFalse((self.root / "calls").exists())
