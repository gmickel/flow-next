"""Capture and refine read glossary and strategy status from their preflight snapshot.

A healthy snapshot probe makes no flowctl call; a failed probe or a missing
snapshot falls back to the live call, so the gates still fail open. Each fence
runs for real against a stub flowctl that logs its calls.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "skills"
CAPTURE_GLOSSARY = SKILLS / "flow-next-capture" / "references" / "glossary-terms.md"
CAPTURE_STRATEGY = SKILLS / "flow-next-capture" / "references" / "strategy-alignment.md"
REFINE_GLOSSARY = SKILLS / "flow-next-refine" / "references" / "doc-aware-docs.md"
SHELLS = [("bash",)] + ([("zsh", "-f")] if shutil.which("zsh") else [])
GLOSSARY = {"groups": [], "file_count": 1, "total_terms": 3}
STRATEGY = {"exists": True, "sections_filled": 2}
STUB = """#!/bin/sh
echo "$1 $2" >> "$CALLS"
case "$1 $2" in
  "glossary list") echo '{"total_terms": 7}' ;;
  "strategy status") echo '{"sections_filled": 0}' ;;
  *) echo '{}' ;;
esac
"""


def _fence(path: Path, marker: str) -> str:
    blocks = re.findall(r"```bash\n(.*?)```", path.read_text(encoding="utf-8"), re.S)
    found = [b for b in blocks if marker in b]
    assert len(found) == 1, f"{path.name}: {len(found)} fences contain {marker!r}"
    return found[0]


@unittest.skipIf(os.name == "nt", "POSIX shells")
class SnapshotProbeReadTests(unittest.TestCase):
    def _run(self, shell, fence, snapshot, name, out):
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / "flowctl"
            stub.write_text(STUB)
            stub.chmod(0o755)
            calls = Path(tmp) / "calls"
            if snapshot is not None:
                Path(tmp, f"flow-{name}-sfx.json").write_text(json.dumps(snapshot))
            env = dict(os.environ, FLOWCTL=str(stub), CALLS=str(calls), TMPDIR=tmp)
            script = fence.replace("<suffix>", "sfx")
            if out:
                script += f'\nprintf "%s\\n" "${{{out}}}"\n'
            result = subprocess.run([*shell, "-c", script], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout.strip(), (calls.read_text().splitlines() if calls.exists() else [])

    def _snapshots(self, key, value):
        return {
            "ok": ({"probes": {key: {"status": "ok", "value": value}}}, []),
            "error": ({"probes": {key: {"status": "error", "value": None}}}, None),
            "missing": (None, None),
        }

    def test_capture_glossary_terms(self):
        fence = _fence(CAPTURE_GLOSSARY, "GLOSSARY_TERMS=")
        for shell in SHELLS:
            for case, (snap, calls) in self._snapshots("glossary", GLOSSARY).items():
                with self.subTest(shell=shell[0], case=case):
                    out, seen = self._run(shell, fence, snap, "capture-config", "GLOSSARY_TERMS")
                    self.assertEqual((out, seen), ("3", []) if calls == [] else ("7", ["glossary list"]))

    def test_capture_strategy_status(self):
        fence = _fence(CAPTURE_STRATEGY, "STRATEGY_STATUS_JSON=")
        for shell in SHELLS:
            for case, (snap, calls) in self._snapshots("strategy", STRATEGY).items():
                with self.subTest(shell=shell[0], case=case):
                    out, seen = self._run(shell, fence, snap, "capture-config", "STRATEGY_FILLED")
                    if calls == []:
                        self.assertEqual((out, seen), ("2", ["strategy read"]))
                    else:
                        self.assertEqual((out, seen), ("0", ["strategy status"]))

    def test_refine_glossary_list(self):
        fence = _fence(REFINE_GLOSSARY, "glossary probe")
        for shell in SHELLS:
            for case, (snap, calls) in self._snapshots("glossary", GLOSSARY).items():
                with self.subTest(shell=shell[0], case=case):
                    out, seen = self._run(shell, fence, snap, "refine-preflight", None)
                    if calls == []:
                        self.assertEqual((json.loads(out), seen), (GLOSSARY, []))
                    else:
                        self.assertEqual((json.loads(out), seen), ({"total_terms": 7}, ["glossary list"]))


if __name__ == "__main__":
    unittest.main()
