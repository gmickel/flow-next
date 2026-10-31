"""Argument-parse fences word-split under zsh as well as bash.

Hosts often run skill fences in the person's shell. zsh does not word-split an
unquoted `$ARGUMENTS`, so a `for arg in $ARGUMENTS` loop sees one token and
drops every flag. Each fence runs for real with ARGUMENTS set as a variable.
"""
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "skills"
RESOLVE_PR = SKILLS / "flow-next-resolve-pr" / "workflow.md"
QA = SKILLS / "flow-next-qa" / "SKILL.md"
SHELLS = [("bash",)] + ([("zsh", "-f")] if shutil.which("zsh") else [])


def _fence(path: Path, marker: str) -> str:
    blocks = re.findall(r"```bash\n(.*?)```", path.read_text(encoding="utf-8"), re.S)
    found = [b for b in blocks if marker in b]
    assert len(found) == 1, f"{path.name}: {len(found)} fences contain {marker!r}"
    return found[0]


def _run(shell: tuple, script: str, names: list, arguments: str) -> dict:
    printer = "".join(f'printf "%s=%s\\n" {n} "${{{n}}}"\n' for n in names)
    env = {k: v for k, v in os.environ.items() if k != "FLOW_AUTONOMOUS"}
    result = subprocess.run([*shell, "-c", script + "\n" + printer], env=dict(env, ARGUMENTS=arguments),
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)


@unittest.skipIf(os.name == "nt", "POSIX shells")
@unittest.skipUnless(shutil.which("zsh"), "zsh")
class ArgLoopZshTests(unittest.TestCase):
    def test_resolve_pr_flags_split(self):
        script = _fence(RESOLVE_PR, "DRY_RUN=0") + _fence(RESOLVE_PR, "MODE=full")
        names = ["DRY_RUN", "NO_CLUSTER", "AUTONOMOUS", "TARGET", "MODE", "PR_NUMBER"]
        for shell in SHELLS:
            with self.subTest(shell=shell[0]):
                self.assertEqual(_run(shell, script, names, "--dry-run --no-cluster 42"),
                                 {"DRY_RUN": "1", "NO_CLUSTER": "1", "AUTONOMOUS": "0",
                                  "TARGET": "42", "MODE": "full", "PR_NUMBER": "42"})
                self.assertEqual(_run(shell, script, names, ""),
                                 {"DRY_RUN": "0", "NO_CLUSTER": "0", "AUTONOMOUS": "0",
                                  "TARGET": "", "MODE": "full", "PR_NUMBER": ""})

    def test_qa_flags_split(self):
        script = _fence(QA, "SPEC_ID=")
        names = ["SPEC_ID", "QA_TARGET_URL", "QA_BASE_REF", "NO_PROMPT"]
        for shell in SHELLS:
            with self.subTest(shell=shell[0]):
                self.assertEqual(_run(shell, script, names, "fn-1 --target=http://localhost:3000 --base main mode:autonomous"),
                                 {"SPEC_ID": "fn-1", "QA_TARGET_URL": "http://localhost:3000",
                                  "QA_BASE_REF": "main", "NO_PROMPT": "1"})
                self.assertEqual(_run(shell, script, names, ""),
                                 {"SPEC_ID": "", "QA_TARGET_URL": "", "QA_BASE_REF": "", "NO_PROMPT": "0"})


if __name__ == "__main__":
    unittest.main()
