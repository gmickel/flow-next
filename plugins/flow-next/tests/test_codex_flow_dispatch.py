"""Generate and install flow, then resolve its dispatches at the consumer layout."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[3]


@unittest.skipIf(sys.platform == "win32" or not shutil.which("bash"), "requires bash")
class CodexFlowDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.repo = cls.root / "repo"
        shutil.copytree(REPO / "scripts", cls.repo / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__"))
        cls.plugin = cls.repo / "plugins/flow-next"
        shutil.copytree(REPO / "plugins/flow-next", cls.plugin,
                        ignore=shutil.ignore_patterns("codex", "tests", "__pycache__"))
        cls.consumer = cls.root / "consumer"
        cls.consumer.mkdir()
        cls.env = dict(os.environ, CODEX_HOME=str(cls.consumer))
        for name in list(cls.env):
            if name.startswith(("CODEX_MODEL_", "CODEX_REASONING_EFFORT")):
                cls.env.pop(name)
        for script in ("sync-codex.sh", "install-codex.sh"):
            result = subprocess.run(
                ["bash", str(cls.repo / "scripts" / script)],
                env=cls.env, capture_output=True, text=True, timeout=300,
            )
            if result.returncode:
                raise AssertionError(f"{script}:\n{result.stdout}\n{result.stderr}")
        sync = (cls.repo / "scripts/sync-codex.sh").read_text()
        cls.guard = sync.split("<<'FLOW_DISPATCH_GUARD'\n", 1)[1].split(
            "\nFLOW_DISPATCH_GUARD", 1
        )[0]
        cls.source = cls.plugin / "skills/flow-next-flow"
        cls.installed = cls.consumer / "skills/flow-next-flow"

    def run_guard(self, mirror):
        return subprocess.run(
            [sys.executable, "-c", self.guard, str(self.source), str(mirror)],
            capture_output=True, text=True, timeout=30,
        )

    def test_installed_dispatch_inventory_and_land_reachability(self):
        result = self.run_guard(self.installed)
        self.assertEqual(result.returncode, 0, result.stderr)
        # Follow actual references from the conductor to both dispatch modes.
        skill = (self.installed / "SKILL.md").read_text()
        for entry in ("auto.md", "workflow.md"):
            self.assertIn(entry, skill)
            body = (self.installed / entry).read_text()
            self.assertIn("references/tail.md", body)
        workflow = (self.installed / "workflow.md").read_text()
        self.assertIn("references/route-matrix.md", workflow)
        for relative in ("auto.md", "references/tail.md", "references/route-matrix.md"):
            with self.subTest(relative=relative):
                body = (self.installed / relative).read_text()
                targets = re.findall(r"`\$(flow-next-[a-z-]+)(?=[ `])", body)
                self.assertIn("flow-next-land", targets)
                for target in targets:
                    self.assertTrue((self.consumer / "skills" / target / "SKILL.md").is_file())

    def test_guard_rejects_regressed_dispatch_and_missing_target(self):
        with tempfile.TemporaryDirectory(dir=self.root) as tmp:
            skills = Path(tmp) / "skills"
            shutil.copytree(self.consumer / "skills", skills)
            mirror = skills / "flow-next-flow"
            tail = mirror / "references/tail.md"
            original = tail.read_text()
            tail.write_text(original.replace("$flow-next-land", "/flow-next:land"))
            self.assertNotEqual(self.run_guard(mirror).returncode, 0)
            tail.write_text(original)
            land = skills / "flow-next-land/SKILL.md"
            land.rename(land.with_suffix(".hidden"))
            self.assertNotEqual(self.run_guard(mirror).returncode, 0)

    def test_installed_shell_dispatch_identity_preserves_authority_gate(self):
        def allowlist(path):
            text = path.read_text()
            start = text.index('case "$DISPATCH_TARGET" in')
            return text[start:text.index("esac", start) + len("esac")]

        source = allowlist(self.source / "auto.md")
        installed = allowlist(self.installed / "auto.md")
        self.assertEqual(source, installed)
        for target, authorized, spec, pr, allowed in (
            ("/flow-next:land", "1", "fn-241", "429", True),
            ("/flow-next:land", "0", "fn-241", "429", False),
            ("/flow-next:land", "1", "", "429", False),
            ("/flow-next:land", "1", "fn-241", "", False),
            ("/flow-next:work", "0", "", "", True),
            ("/flow-next:tracker-sync reconcile", "0", "", "", True),
            ("/flow-next:release", "1", "fn-241", "429", False),
        ):
            with self.subTest(target=target, authorized=authorized, spec=spec, pr=pr):
                result = subprocess.run(
                    ["bash", "-c", 'DISPATCH_TARGET="$1"\n' + installed, "test", target],
                    env=dict(self.env, LAND_AUTHORIZED=authorized,
                             LAND_SCOPE_SPEC=spec, LAND_SCOPE_PR=pr),
                    capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(result.returncode == 0, allowed, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
