"""Land merge fence is bash-and-zsh safe without `eval` (fn-242, #406).

The merge step used to build `MERGE_CMD="${FLOW_PR_MERGE_CMD:-gh pr merge}"`
and invoke `$MERGE_CMD ...` unquoted, relying on bash word-splitting. Under
zsh (macOS default login shell) the whole string is one command name and the
merge fails with exit 127. The fence is executed verbatim from workflow.md by
agents under either shell, so this test runs the REAL fence lines under both.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -p "test_land_merge_cmd_shell.py" -v
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "skills" / "flow-next-land" / "workflow.md"
MIRROR = ROOT / "codex" / "skills" / "flow-next-land" / "workflow.md"

_FENCE_RE = re.compile(
    r"^(  MERGE_CMD.*?\n  MERGE_ERR=.*?\n)", re.MULTILINE | re.DOTALL,
)


def _merge_fence(path: Path) -> str:
    m = _FENCE_RE.search(path.read_text(encoding="utf-8"))
    assert m, f"merge fence not found in {path}"
    return m.group(1)


class MergeFenceShellSafety(unittest.TestCase):
    def setUp(self) -> None:
        self.fence = _merge_fence(WORKFLOW)
        self.tmp = Path(tempfile.mkdtemp(prefix="fn242-merge-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        # Fake `gh` on PATH: proxies argv on stderr (the only stream the fence
        # captures) and exits 0, like a real merge.
        gh = self.tmp / "gh"
        gh.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\" >&2\n", encoding="utf-8")
        gh.chmod(0o755)
        # Wrapper reached via a multi-word FLOW_PR_MERGE_CMD.
        self.wrapper = self.tmp / "wrap.py"
        self.wrapper.write_text(
            "import sys\nsys.stderr.write('\\n'.join(sys.argv[1:]) + '\\n')\n",
            encoding="utf-8",
        )

    # No rc files and a PATH that holds only the shim dir plus the system
    # dirs: a login-shell rc (e.g. mise activation) would otherwise put the
    # REAL `gh` ahead of the shim and the test would perform a real merge.
    SHELLS = {
        "bash": ["bash", "--noprofile", "--norc", "-c"],
        "zsh": ["zsh", "-f", "-c"],
    }

    def _run(self, shell: str, env_override: dict[str, str]) -> list[str]:
        script = (
            # A standalone PR whose children read returned zero: the case today's flags model.
            # Unset would mean UNREAD and keep the branch (cursor review on #432).
            'PR_NUMBER=42\nHEAD_OID=abc123\nCHILD_COUNT=0\n'
            + self.fence
            + 'printf "%s\\n" "$MERGE_ERR"\necho "MERGE_RC=$MERGE_RC"\n'
        )
        env = {"PATH": f"{self.tmp}{os.pathsep}/usr/bin{os.pathsep}/bin", "HOME": str(self.tmp)}
        env.update(env_override)
        out = subprocess.run(
            self.SHELLS[shell] + [script], env=env, capture_output=True,
            text=True, timeout=30,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout.splitlines()

    def test_fence_never_evals(self) -> None:
        self.assertNotIn("eval", self.fence)

    def test_codex_mirror_carries_the_same_fence(self) -> None:
        self.assertEqual(_merge_fence(MIRROR), self.fence)

    @unittest.skipIf(sys.platform == "win32", "Native Windows bash is a WSL/git-bash stub; POSIX PATH and shim perms do not apply")
    def test_default_and_override_split_under_bash_and_zsh(self) -> None:
        tail = ["42", "--squash", "--delete-branch", "--match-head-commit", "abc123",
                "MERGE_RC=0"]
        cases = {
            # default `gh pr merge`: the shim `gh` sees `pr merge` first
            "default": ({}, ["pr", "merge"] + tail),
            # multi-word override reaches the wrapper with the fixed contract
            "override": ({"FLOW_PR_MERGE_CMD": f"{sys.executable} {self.wrapper}"}, tail),
        }
        for shell in self.SHELLS:
            if shutil.which(shell) is None:
                continue
            for label, (env, expected) in cases.items():
                with self.subTest(shell=shell, cmd=label):
                    self.assertEqual(self._run(shell, env), expected)


if __name__ == "__main__":
    unittest.main()
