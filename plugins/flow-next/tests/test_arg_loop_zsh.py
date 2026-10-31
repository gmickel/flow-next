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
FLOW = SKILLS / "flow-next-flow" / "SKILL.md"
AUTO = SKILLS / "flow-next-flow" / "auto.md"
FEATURES = SKILLS / "flow-next-features" / "SKILL.md"
CAPTURE = SKILLS / "flow-next-capture" / "SKILL.md"
SHELLS = [("bash",)] + ([("zsh", "-f")] if shutil.which("zsh") else [])


def _fence(path: Path, marker: str) -> str:
    blocks = re.findall(r"```bash\n(.*?)```", path.read_text(encoding="utf-8"), re.S)
    found = [b for b in blocks if marker in b]
    assert len(found) == 1, f"{path.name}: {len(found)} fences contain {marker!r}"
    return found[0]


def _run(shell: tuple, script: str, names: list, arguments: str, cwd=None) -> dict:
    printer = "".join(f'printf "%s=%s\\n" {n} "${{{n}}}"\n' for n in names)
    env = {k: v for k, v in os.environ.items() if k != "FLOW_AUTONOMOUS"}
    result = subprocess.run([*shell, "-c", script + "\n" + printer], env=dict(env, ARGUMENTS=arguments),
                            text=True, capture_output=True, cwd=cwd)
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

    def test_resolve_pr_url_capture(self):
        script = _fence(RESOLVE_PR, "DRY_RUN=0") + _fence(RESOLVE_PR, "MODE=full")
        names = ["MODE", "TARGETED_TYPE", "OWNER", "REPO", "PR_NUMBER", "COMMENT_REST_ID"]
        for shell in SHELLS:
            with self.subTest(shell=shell[0]):
                self.assertEqual(_run(shell, script, names, "https://github.com/acme/widgets/pull/12#discussion_r34"),
                                 {"MODE": "targeted", "TARGETED_TYPE": "review_thread", "OWNER": "acme",
                                  "REPO": "widgets", "PR_NUMBER": "12", "COMMENT_REST_ID": "34"})
                self.assertEqual(_run(shell, script, names, "https://github.com/acme/widgets/pull/12"),
                                 {"MODE": "full", "TARGETED_TYPE": "", "OWNER": "acme",
                                  "REPO": "widgets", "PR_NUMBER": "12", "COMMENT_REST_ID": ""})

    def test_flow_destination_flags_split(self):
        script = _fence(FLOW, "FLOW_DESTINATION_ERROR=0")
        for shell in SHELLS:
            with self.subTest(shell=shell[0]):
                self.assertEqual(_run(shell, script, ["AUTO", "FLOW_UNTIL"], "fn-1 --auto --until=merge"),
                                 {"AUTO": "1", "FLOW_UNTIL": "merge"})

    def test_auto_flags_split(self):
        script = _fence(AUTO, "PILOT_GOAL_MODE=0")
        names = ["PILOT_SPEC", "AUTO_TICK", "PILOT_REVIEW", "PILOT_GOAL_MODE"]
        for shell in SHELLS:
            with self.subTest(shell=shell[0]):
                self.assertEqual(_run(shell, script, names, "fn-1 --tick --review=codex"),
                                 {"PILOT_SPEC": "fn-1", "AUTO_TICK": "1", "PILOT_REVIEW": "codex",
                                  "PILOT_GOAL_MODE": "0"})

    def test_features_init_flag_split(self):
        import tempfile
        script = _fence(FEATURES, 'RAW_ARGS="${ARGUMENTS:-}"')
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".flow" / "features").mkdir(parents=True)
            for shell in SHELLS:
                with self.subTest(shell=shell[0]):
                    self.assertEqual(_run(shell, script, ["MODE"], "fn-1 --init", cwd=tmp), {"MODE": "seed"})
                    self.assertEqual(_run(shell, script, ["MODE"], "", cwd=tmp), {"MODE": "maintain"})

    def test_capture_tokens_split(self):
        script = _fence(CAPTURE, 'REWRITE_TARGET=""')
        names = ["REWRITE_TARGET", "NO_PLAN_OPT", "FROM_FLOW", "MODE"]
        for shell in SHELLS:
            with self.subTest(shell=shell[0]):
                self.assertEqual(_run(shell, script, names, "--rewrite fn-9 --no-plan from:flow"),
                                 {"REWRITE_TARGET": "fn-9", "NO_PLAN_OPT": "1", "FROM_FLOW": "1",
                                  "MODE": "interactive"})


if __name__ == "__main__":
    unittest.main()
