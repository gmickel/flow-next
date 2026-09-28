"""fn-274 R4: evidence written before the resolved-feature record was removed.

A task whose done evidence carries `resolved_feature` still completes and
loads; the key is ignored (warned as unrendered, never exported).

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_resolved_feature_legacy -q
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import flowctl  # noqa: E402

FLOWCTL_PY = SCRIPTS / "flowctl.py"
TASK_ID = "fn-1-sample.1"
RECORD = {"surface": "web", "sub_feature": "notes.list", "file": "notes-list.md",
          "last_proven": None, "stage": "flow"}


class LegacyResolvedFeatureTest(unittest.TestCase):
    def test_done_evidence_with_the_key_loads_and_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "FLOW_STATE_DIR": str(Path(tmp) / "state")}

            def run(*args: str) -> subprocess.CompletedProcess:
                result = subprocess.run([sys.executable, str(FLOWCTL_PY), *args],
                                        cwd=tmp, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result

            run("init")
            run("spec", "create", "--title", "Sample")
            run("task", "create", "--spec", "fn-1-sample", "--title", "T one")
            run("start", TASK_ID)
            done = run("done", TASK_ID, "--evidence",
                       json.dumps({"commits": ["abc"], "resolved_feature": RECORD}))
            self.assertIn("resolved_feature", done.stderr)
            evidence = json.loads(run("show", TASK_ID, "--json").stdout)["evidence"]
            self.assertEqual(evidence["commits"], ["abc"])
            self.assertNotIn("resolved_feature", flowctl._export_task_evidence_block(evidence))


if __name__ == "__main__":
    unittest.main()
