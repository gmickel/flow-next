"""resolve-pr refuses a pull request or comment URL from another repository.

Every later call acts on the current checkout's repository, so the target
parse stops before any fetch. The argument, parse and fetch fences run for
real under bash and zsh, with gh and the fetch script stubbed.
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
GH = 'gh() { echo "gh $*" >> "$CALLS"; echo "$CURRENT_REPO_STUB"; }\n'


def _fence(marker: str) -> str:
    blocks = re.findall(r"```bash\n(.*?)```", WORKFLOW.read_text(encoding="utf-8"), re.S)
    found = [b for b in blocks if marker in b]
    assert len(found) == 1, f"{len(found)} fences contain {marker!r}"
    return found[0]


@unittest.skipIf(os.name == "nt", "POSIX shells")
class RepoGuardTests(unittest.TestCase):
    def _run(self, shell, target, current):
        with tempfile.TemporaryDirectory() as tmp:
            scripts = Path(tmp)
            calls = scripts / "calls"
            (scripts / "get-pr-comments").write_text(f'echo "fetch $*" >> "{calls}"\necho {{}}\n')
            script = GH + _fence("DRY_RUN=0") + _fence("MODE=full") + _fence("FEEDBACK_JSON=$(")
            env = dict(os.environ, ARGUMENTS=target, CALLS=str(calls), CURRENT_REPO_STUB=current,
                       SCRIPTS=str(scripts))
            env.pop("FLOW_AUTONOMOUS", None)
            result = subprocess.run([*shell, "-c", script], env=env, text=True, capture_output=True)
            return result, (calls.read_text().splitlines() if calls.exists() else [])

    def test_foreign_repository_url_refused_before_fetch(self):
        for shell in SHELLS:
            for target in ("https://github.com/acme/widgets/pull/12",
                           "https://github.com/acme/widgets/pull/12#discussion_r34",
                           "https://github.com/acme/widgets/pull/12#issuecomment-56"):
                with self.subTest(shell=shell[0], target=target):
                    result, calls = self._run(shell, target, "gmickel/flow-next")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("acme/widgets", result.stderr)
                    self.assertIn("gmickel/flow-next", result.stderr)
                    self.assertEqual(calls, ["gh repo view --json nameWithOwner --jq .nameWithOwner"])

    def test_same_repository_url_proceeds(self):
        for shell in SHELLS:
            with self.subTest(shell=shell[0]):
                result, calls = self._run(shell, "https://github.com/Acme/Widgets/pull/12", "acme/widgets")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls[-1], "fetch 12")

    def test_pr_number_needs_no_repository_lookup(self):
        for shell in SHELLS:
            with self.subTest(shell=shell[0]):
                result, calls = self._run(shell, "12", "acme/widgets")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls, ["fetch 12"])


if __name__ == "__main__":
    unittest.main()
