"""`scripts/sync-codex.sh --check` reports a stale mirror without writing (fn-256 R5)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
STALE_FILE = "plugins/flow-next/codex/skills/flow-next-work/SKILL.md"


@unittest.skipIf(sys.platform == "win32" or not shutil.which("bash"), "requires bash")
class SyncCodexCheckTests(unittest.TestCase):
    def test_stale_mirror_and_generator_error_fail_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            shutil.copytree(REPO / "scripts", repo / "scripts",
                            ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(REPO / "plugins/flow-next", repo / "plugins/flow-next",
                            ignore=shutil.ignore_patterns("tests", "__pycache__"))
            stale = repo / STALE_FILE
            stale_bytes = stale.read_bytes() + b"\nstale line\n"
            stale.write_bytes(stale_bytes)
            (repo / "scripts/gen_tracker_manifest.py").write_text(
                "import sys\nprint('manifest generator exploded')\nsys.exit(3)\n",
                encoding="utf-8",
            )
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith(("CODEX_MODEL_", "CODEX_REASONING_EFFORT"))}
            result = subprocess.run(
                ["bash", str(repo / "scripts/sync-codex.sh"), "--check"],
                env=env, capture_output=True, text=True, timeout=300,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 1, output)
            self.assertIn(str(stale), output)
            self.assertIn("manifest generator exploded", output)
            self.assertEqual(stale.read_bytes(), stale_bytes)


if __name__ == "__main__":
    unittest.main()
