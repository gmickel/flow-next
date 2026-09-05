"""The CI install verifier must compare complete component payloads."""

import contextlib
import importlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "ci"))
try:
    verifier = importlib.import_module("verify_cursor_install")
finally:
    sys.path.remove(str(ROOT / "scripts" / "ci"))


class CursorInstallVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "source"
        self.dest = Path(self.temp.name) / "installed"
        for rel in (
            "skills/example/SKILL.md",
            "skills/example/templates/helper.py",
            "commands/example.md",
            "agents/example.md",
            "rules/example.mdc",
        ):
            path = self.source / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("source content\n", encoding="utf-8")
        manifest = self.source / ".cursor-plugin/plugin.json"
        manifest.parent.mkdir()
        manifest.write_text(json.dumps({key: f"./{key}" for key in verifier.REQUIRED_COMPONENT_KEYS}))
        shutil.copytree(self.source, self.dest)

    def check(self):
        output = io.StringIO()
        with patch.object(verifier, "SRC", self.source), patch(
            "sys.argv", ["verify_cursor_install.py", "--dest", str(self.dest)]
        ), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = verifier.main()
        return code, output.getvalue()

    def test_matching_install_passes(self):
        code, output = self.check()
        self.assertEqual(code, 0, output)

    def test_missing_nested_skill_payload_fails(self):
        (self.dest / "skills/example/templates/helper.py").unlink()
        code, output = self.check()
        self.assertEqual(code, 1, output)
        self.assertIn("example/templates/helper.py", output)

    def test_extra_nested_skill_payload_fails(self):
        (self.dest / "skills/example/templates/stale.py").write_text("old", encoding="utf-8")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        self.assertIn("example/templates/stale.py", output)

    def test_changed_nested_skill_payload_fails(self):
        (self.dest / "skills/example/templates/helper.py").write_text("old", encoding="utf-8")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        self.assertIn("example/templates/helper.py", output)

    def test_installer_excluded_source_cruft_is_not_required(self):
        for rel in (".DS_Store", "loose.pyc", "__pycache__/helper.pyc"):
            path = self.source / "skills/example" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"ignored")
        code, output = self.check()
        self.assertEqual(code, 0, output)

    def test_installer_excluded_payload_is_rejected_at_destination(self):
        (self.dest / "skills/example/.DS_Store").write_bytes(b"ignored")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        self.assertIn(".DS_Store", output)


if __name__ == "__main__":
    unittest.main()
