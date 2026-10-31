"""impl-review's deep-pass and validator fences dispatch the resolved CLI backend.

One generic arm serves codex, copilot, cursor and claude; host and an unknown
backend make no flowctl call. Each fence runs for real against a stub flowctl.
"""
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

OPTIONAL = Path(__file__).resolve().parents[1] / "skills" / "flow-next-impl-review" / "optional-phases.md"
STUB = """#!/bin/sh
if [ "$1" = review-route ]; then echo '{"task_id":"fn-1-x.1","receipt_path":"/r/receipt.json"}'; exit 0; fi
echo "$*" >> "$CALLS"
echo '{}'
"""


def _fence(marker: str) -> str:
    blocks = re.findall(r"```bash\n(.*?)```", OPTIONAL.read_text(encoding="utf-8"), re.S)
    found = [b for b in blocks if marker in b]
    assert len(found) == 1, f"{len(found)} fences contain {marker!r}"
    return found[0]


@unittest.skipIf(os.name == "nt", "POSIX shell")
class OptionalPhaseDispatchTests(unittest.TestCase):
    def _calls(self, fence: str, backend: str) -> list:
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / "flowctl"
            stub.write_text(STUB)
            stub.chmod(0o755)
            calls = Path(tmp) / "calls"
            env = dict(os.environ, FLOWCTL=str(stub), BACKEND=backend, CALLS=str(calls),
                       SELECTED_PASSES="adversarial security", TASK_ID="fn-1-x.1")
            result = subprocess.run(["bash", "-c", fence], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return calls.read_text().splitlines() if calls.exists() else []

    def test_deep_pass_dispatches_each_cli_backend(self):
        fence = _fence("deep-pass")
        for backend in ("codex", "copilot", "cursor", "claude"):
            with self.subTest(backend=backend):
                self.assertEqual(self._calls(fence, backend), [
                    f"{backend} deep-pass --pass {p} --primary-findings /tmp/primary-findings.jsonl"
                    " --receipt /r/receipt.json --json" for p in ("adversarial", "security")])
        for backend in ("host", "unknown"):
            with self.subTest(backend=backend):
                self.assertEqual(self._calls(fence, backend), [])

    def test_validate_dispatches_each_cli_backend(self):
        fence = _fence("validate \\")
        for backend in ("codex", "copilot", "cursor", "claude"):
            with self.subTest(backend=backend):
                self.assertEqual(self._calls(fence, backend), [
                    f"{backend} validate --findings-file /tmp/review-findings.jsonl"
                    " --receipt /r/receipt.json --json"])
        for backend in ("host", "unknown"):
            with self.subTest(backend=backend):
                self.assertEqual(self._calls(fence, backend), [])


if __name__ == "__main__":
    unittest.main()
