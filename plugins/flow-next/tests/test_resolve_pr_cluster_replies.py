"""Each thread of a resolved cluster gets its own reply and resolution.

The resolver returns one verdict per thread, the cluster's assessment riding on
each; Phase 8's reply/resolve fence runs for real against stubbed scripts.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / "skills" / "flow-next-resolve-pr" / "workflow.md"
SHELLS = [("bash",)] + ([("zsh", "-f")] if shutil.which("zsh") else [])


def _fence(marker: str) -> str:
    blocks = re.findall(r"```bash\n(.*?)```", WORKFLOW.read_text(encoding="utf-8"), re.S)
    found = [b for b in blocks if marker in b]
    assert len(found) == 1, f"{len(found)} fences contain {marker!r}"
    return found[0]


def _verdict(thread, verdict):
    return {"verdict": verdict, "feedback_id": thread, "feedback_type": "review_thread",
            "reply_text": f"> quoted {thread}\n\nFixed with a shared validator.", "files_changed": ["src/auth.ts"],
            "reason": "shared validator", "cluster_assessment": "validation was missing across the module"}


@unittest.skipIf(os.name == "nt" or not shutil.which("jq"), "POSIX shells and jq")
class ClusterReplyTests(unittest.TestCase):
    def _run(self, shell, verdicts):
        with tempfile.TemporaryDirectory() as tmp:
            scripts, calls = Path(tmp), Path(tmp) / "calls"
            # The reply script reads its body from stdin; the resolve script, like the real one, reads none.
            (scripts / "reply-to-pr-thread").write_text(f'cat >/dev/null; echo "reply-to-pr-thread $1" >> "{calls}"\n')
            (scripts / "resolve-pr-thread").write_text(f'echo "resolve-pr-thread $1" >> "{calls}"\n')
            env = dict(os.environ, SCRIPTS=str(scripts), PR_NUMBER="7", VERDICTS=json.dumps(verdicts))
            result = subprocess.run([*shell, "-c", _fence("reply-to-pr-thread")], env=env, text=True,
                                    capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return calls.read_text().splitlines() if calls.exists() else []

    def test_two_thread_cluster_gets_two_replies_and_two_resolutions(self):
        for shell in SHELLS:
            with self.subTest(shell=shell[0]):
                calls = self._run(shell, [_verdict("PRRT_a", "fixed"), _verdict("PRRT_b", "fixed")])
                self.assertEqual(sorted(calls), ["reply-to-pr-thread PRRT_a", "reply-to-pr-thread PRRT_b",
                                                 "resolve-pr-thread PRRT_a", "resolve-pr-thread PRRT_b"])

    def test_needs_human_thread_in_a_cluster_is_replied_not_resolved(self):
        for shell in SHELLS:
            with self.subTest(shell=shell[0]):
                calls = self._run(shell, [_verdict("PRRT_a", "fixed"), _verdict("PRRT_b", "needs-human")])
                self.assertEqual(sorted(calls), ["reply-to-pr-thread PRRT_a", "reply-to-pr-thread PRRT_b",
                                                 "resolve-pr-thread PRRT_a"])


if __name__ == "__main__":
    unittest.main()
