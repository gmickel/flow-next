"""resolve-pr pushes a detached checkout to the PR's head repository and branch.

Land runs resolve-pr in a detached worktree, so the push names its target. The
fence runs for real: a stub gh answers one PR read, and git rewrites the GitHub
URL to a local bare repository that receives the push.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / "skills" / "flow-next-resolve-pr" / "workflow.md"
SHELLS = [("bash",)] + ([("zsh", "-f")] if shutil.which("zsh") else [])
GH_STUB = """#!/bin/sh
echo "$*" >> "$CALLS"
while [ $# -gt 0 ]; do [ "$1" = -q ] && q="$2"; shift; done
echo '{"headRepository":{"name":"repo"},"headRepositoryOwner":{"login":"fork-owner"},"headRefName":"feature"}' | jq -r "$q"
"""


def _push_block() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(r"^if git symbolic-ref -q HEAD.*?^fi$", text, re.S | re.M)
    assert match, "detached push block not found"
    return match.group(0)


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@unittest.skipIf(os.name == "nt", "POSIX shells")
@unittest.skipUnless(shutil.which("jq"), "jq")
class DetachedPushTests(unittest.TestCase):
    def test_detached_push_targets_head_repository_and_branch(self):
        for shell in SHELLS:
            with self.subTest(shell=shell[0]), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                remote = tmp / "remotes" / "fork-owner" / "repo.git"
                remote.mkdir(parents=True)
                _git(remote, "init", "-q", "--bare")
                work = tmp / "work"
                work.mkdir()
                _git(work, "init", "-q")
                for message in ("pr head", "fix"):
                    _git(work, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", message)
                    if message == "pr head":
                        _git(work, "push", "-q", str(remote), "HEAD:refs/heads/feature")
                _git(work, "checkout", "-q", "--detach")
                bin_dir = tmp / "bin"
                bin_dir.mkdir()
                (bin_dir / "gh").write_text(GH_STUB)
                (bin_dir / "gh").chmod(0o755)
                calls = tmp / "calls"
                env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}", CALLS=str(calls),
                           PR_NUMBER="7", GIT_CONFIG_COUNT="1",
                           GIT_CONFIG_KEY_0=f"url.{tmp / 'remotes'}/.insteadOf",
                           GIT_CONFIG_VALUE_0="https://github.com/")
                result = subprocess.run([*shell, "-c", _push_block()], cwd=work, env=env,
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=work, text=True,
                                      capture_output=True, check=True).stdout.strip()
                pushed = subprocess.run(["git", "rev-parse", "refs/heads/feature"], cwd=remote, text=True,
                                        capture_output=True, check=True).stdout.strip()
                self.assertEqual(pushed, head)
                self.assertEqual(len(calls.read_text().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
