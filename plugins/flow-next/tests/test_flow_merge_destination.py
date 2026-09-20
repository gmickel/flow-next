"""Execute Flow destination fences; R9 retired land discovery/tail/handoff fences.

Flow dispatch remains covered here until R10 changes its landing stage.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


PLUGIN = Path(__file__).resolve().parent.parent


def fence(path: str, marker: str) -> str:
    text = (PLUGIN / "skills" / path).read_text(encoding="utf-8")
    return next(block for block in re.findall(r"```bash\n(.*?)```", text, re.S) if marker in block)


@unittest.skipIf(sys.platform == "win32" or not shutil.which("bash") or not shutil.which("jq"),
                 "skill fences require POSIX bash and jq")
class MergeDestinationTest(unittest.TestCase):
    def run_fence(self, code, *, env=None, before="", after="", cwd=None):
        return subprocess.run(["bash", "-c", before + "\n" + code + "\n" + after],
                              env={**os.environ, **(env or {})}, text=True, capture_output=True, cwd=cwd)

    def test_destination_is_exact_and_invalid_input_never_authorizes(self):
        code = fence("flow-next-flow/SKILL.md", 'FLOW_UNTIL=""')
        for args, expected in (("fn-1", ""), ("--auto fn-1", ""),
                               ("fn-1 --until=merge", "merge"),
                               ("--auto fn-1 --until=merge", "merge"),
                               ("fn-1 --until=merger", None), ("fn-1 --until", None),
                               ("fn-1 --until=", None),
                               ("--until=merge --until=no fn-1", None)):
            with self.subTest(args=args):
                result = self.run_fence(code, env={"ARGUMENTS": args},
                                        after='printf "destination=%s" "$FLOW_UNTIL"')
                if expected is None:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("NEEDS_HUMAN", result.stdout)
                    self.assertNotIn("destination=", result.stdout)
                else:
                    self.assertEqual((result.returncode, result.stdout), (0, f"destination={expected}"))
        stale = self.run_fence(code, env={"ARGUMENTS": "--auto fn-1", "LAND_AUTHORIZED": "1",
            "LAND_SCOPE_SPEC": "fn-1", "LAND_SCOPE_PR": "https://x/1"},
            after='printf "%s|%s|%s" "$LAND_AUTHORIZED" "$LAND_SCOPE_SPEC" "$LAND_SCOPE_PR"')
        self.assertEqual(stale.stdout, "0||")


    def test_backlog_land_dispatch_requires_current_scoped_authority(self):
        code = fence("flow-next-flow/auto.md", "assert_allowed_dispatch()")
        for authorized, spec, pr, allowed in (("0", "fn-1", "https://x/1", False),
                                             ("1", "", "https://x/1", False),
                                             ("1", "fn-1", "", False),
                                             ("1", "fn-1", "https://x/1", True)):
            with self.subTest(authorized=authorized, spec=spec, pr=pr):
                result = self.run_fence(code, env={"PILOT_AUTONOMY": "backlog",
                    "LAND_AUTHORIZED": authorized, "LAND_SCOPE_SPEC": spec, "LAND_SCOPE_PR": pr},
                    after='assert_allowed_dispatch /flow-next:land\nprintf dispatched')
                self.assertEqual(result.returncode == 0, allowed, result.stdout)
                self.assertEqual("dispatched" in result.stdout, allowed)


    def test_landing_outcomes_preserve_waits_blockers_and_incomplete_tail(self):
        code = fence("flow-next-flow/references/tail.md", "PILOT_LAND_VERDICT=")
        cases = (("AWAITING_REVIEW", "0", "0", "0", "DEFERRED_TO_LAND", "1"),
                 ("AWAITING_REVIEW", "0", "0", "1", "DEFERRED_TO_LAND", "0"),
                 ("RESOLVING", "1", "0", "0", "ADVANCED", "1"),
                 ("FIXING_CI", "0", "0", "0", "DEFERRED_TO_LAND", "1"),
                 ("MERGED", "0", "1", "0", "ADVANCED", "0"),
                 ("MERGED", "0", "0", "0", "NEEDS_HUMAN", "0"),
                 ("RELEASED", "0", "0", "0", "NEEDS_HUMAN", "0"),
                 ("BLOCKED", "1", "1", "0", "BLOCKED", "0"),
                 ("NEEDS_HUMAN", "1", "1", "0", "NEEDS_HUMAN", "0"),
                 ("NO_WORK", "0", "0", "0", "NEEDS_HUMAN", "0"))
        for verdict, progress, complete, tick, expected, again in cases:
            with self.subTest(verdict=verdict, complete=complete, tick=tick):
                result = self.run_fence(code, env={"LAND_RESULT": verdict, "LAND_PROGRESS": progress,
                    "LAND_COMPLETE": complete, "AUTO_TICK": tick, "LAND_OBSERVED": "1", "LAND_AUTHORIZED": "1"},
                    after='printf "%s|%s" "$PILOT_LAND_VERDICT" "$LAND_CONTINUE"')
                self.assertEqual((result.returncode, result.stdout), (0, f"{expected}|{again}"))
        for missing in ("LAND_OBSERVED", "LAND_AUTHORIZED"):
            result = self.run_fence(code, env={"LAND_RESULT": "MERGED", "LAND_COMPLETE": "1",
                "LAND_OBSERVED": "1", "LAND_AUTHORIZED": "1", missing: "0"},
                after='printf "%s|%s" "$PILOT_LAND_VERDICT" "$LAND_CONTINUE"')
            self.assertEqual(result.stdout, "NEEDS_HUMAN|0")


if __name__ == "__main__":
    unittest.main()
