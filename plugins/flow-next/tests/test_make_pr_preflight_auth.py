"""make-pr preflight auth check must not assume github.com (#532)."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "make-pr-preflight.sh"


@unittest.skipIf(os.name == "nt" or not shutil.which("bash"), "POSIX stubs")
class PreflightAuthTests(unittest.TestCase):
    def run_auth_block(self, gh_body):
        with tempfile.TemporaryDirectory() as temp:
            bin_dir = Path(temp)
            gh = bin_dir / "gh"
            gh.write_text("#!/usr/bin/env bash\n" + gh_body + "\n")
            gh.chmod(0o755)
            block = SCRIPT.read_text(encoding="utf-8").split("# end:block", 1)[0]
            env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"], DRY_RUN="0")
            return subprocess.run(["bash", "-c", block], env=env, capture_output=True, text=True)

    def test_enterprise_only_login_passes(self):
        # Logged in to a GHE host only: a github.com-scoped check fails, a plain one passes.
        result = self.run_auth_block('[[ "$*" == *"--hostname github.com"* ]] && exit 1; exit 0')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_valid_github_com_with_expired_other_host_passes(self):
        # Valid github.com login plus an expired login elsewhere: the all-hosts check fails, github.com passes.
        result = self.run_auth_block('[[ "$*" == *"--hostname github.com"* ]] && exit 0; exit 1')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unauthenticated_stops_without_naming_github_com(self):
        result = self.run_auth_block("exit 1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("gh auth status", result.stderr)
        self.assertNotIn("github.com.", result.stderr)


if __name__ == "__main__":
    unittest.main()
