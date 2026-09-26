"""`flowctl glossary list --match <text>` (fn-258 R3).

Only entries whose term or avoid-alias occurs in the text as a whole word,
case-insensitive and whitespace-collapsed; same output shape as the
unfiltered list, and the unfiltered list's empty result when no glossary
exists. Drives the production CLI wire form in a throwaway git repo.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling test helpers
from flowctl_test_support import FLOWCTL_CMD

GLOSSARY = (
    "# Glossary\n\n"
    "## Review backend\n\nThe engine that grades a diff.\n\n"
    "_Avoid_: judge, provider\n\n"
    "## Gate\n\nA pass/fail check.\n\n"
    "_Avoid_: CI\n"
)


class GlossaryMatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        subprocess.run(["git", "init", "-q"], cwd=self.tmpdir, check=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _list(self, *extra: str) -> dict:
        result = subprocess.run(
            [*FLOWCTL_CMD, "glossary", "list", "--json", *extra],
            cwd=str(self.tmpdir),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_match_filters_entries(self) -> None:
        (self.tmpdir / "GLOSSARY.md").write_text(GLOSSARY, encoding="utf-8")
        cases = [
            ("term hit", "pick a review backend", ["Review backend"]),
            ("avoid-alias hit", "ask the judge", ["Review backend"]),
            ("case + whitespace", "the REVIEW\n   Backend and a gate", ["Review backend", "Gate"]),
            ("whole word only", "a decision on precise judgement", []),
            ("no match", "nothing relevant", []),
        ]
        for label, text, expected in cases:
            with self.subTest(case=label):
                payload = self._list("--match", text)
                entries = payload["groups"][0]["entries"]
                self.assertEqual([e["term"] for e in entries], expected)
                self.assertEqual(payload["groups"][0]["count"], len(expected))
                self.assertEqual(payload["total_terms"], len(expected))

    def test_no_glossary_matches_unfiltered_result(self) -> None:
        self.assertEqual(self._list("--match", "gate"), self._list())


if __name__ == "__main__":
    unittest.main()
