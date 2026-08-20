"""OpenCode-host setup contracts: detection rung + silent-skip Ralph.

Locks:

  (a) workflow.md contains the we-control manifest-file detection line, and
      the OpenCode rung is ordered after grok and before the else→codex
      fallback in the Step-0 cascade.
  (b) Executable Step-0 bash: PLUGIN_ROOT carrying
      .flow-next-opencode-manifest classifies as opencode; GROK_AGENT still
      wins; absence of the file is not an OpenCode signal.
  (c) PLATFORM=opencode never offers Ralph; lifecycle snippet + routing
      target AGENTS.md.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_setup_opencode_host -q
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
PLUGIN = HERE.parent.parent
WORKFLOW = PLUGIN / "skills" / "flow-next-setup" / "workflow.md"

HOST_ENV_KEYS = (
    "DROID_PLUGIN_ROOT",
    "CLAUDE_PLUGIN_ROOT",
    "CURSOR_AGENT",
    "GROK_AGENT",
    "CLAUDECODE",
    "CURSOR_TRACE_ID",
    "CODEX_HOME",
)

_BASH = shutil.which("bash")

_STEP0_HEADING = re.compile(
    r"(?m)^## Step 0: Resolve plugin path and detect platform\s*$"
)
_FIRST_BASH_FENCE = re.compile(r"(?ms)^```bash\n(.*?)(?:^```\s*$)", re.MULTILINE)

MANIFEST_DETECT = '[ -f "${PLUGIN_ROOT}/.flow-next-opencode-manifest" ]'


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _extract_step0_detection_bash(text: str) -> str:
    heads = list(_STEP0_HEADING.finditer(text))
    if len(heads) != 1:
        raise AssertionError(
            f"expected exactly one Step-0 heading, found {len(heads)}"
        )
    after = text[heads[0].end() :]
    next_h2 = re.search(r"(?m)^## ", after)
    step0 = after[: next_h2.start()] if next_h2 else after
    fences = list(_FIRST_BASH_FENCE.finditer(step0))
    if len(fences) != 1:
        raise AssertionError(
            f"expected exactly one ```bash fence under Step 0, found {len(fences)}"
        )
    return fences[0].group(1)


class TestOpencodeDetectionProse(unittest.TestCase):
    """Manifest-file rung is present and ordered after grok, before codex."""

    def setUp(self) -> None:
        self.assertTrue(WORKFLOW.is_file(), f"missing {WORKFLOW}")
        self.text = _read(WORKFLOW)
        self.bash = _extract_step0_detection_bash(self.text)

    def test_manifest_file_detection_line(self) -> None:
        self.assertIn(MANIFEST_DETECT, self.bash)
        self.assertIn(MANIFEST_DETECT, self.text)
        self.assertIn('PLATFORM="opencode"', self.bash)
        # Positive file we control — never an env var, never an absence signal.
        self.assertNotIn("OPENCODE", self.bash.replace("opencode", ""))
        self.assertNotIn("! -f", self.bash)

    def test_opencode_rung_after_grok_before_codex_fallback(self) -> None:
        grok = self.bash.index('PLATFORM="grok"')
        opencode = self.bash.index('PLATFORM="opencode"')
        fallback = self.bash.index("else\n  PLATFORM=\"codex\"")
        self.assertLess(grok, opencode)
        self.assertLess(opencode, fallback)
        # Manifest check is the opencode condition, not a later comment.
        detect_at = self.bash.index(MANIFEST_DETECT)
        self.assertLess(detect_at, opencode)
        self.assertGreater(detect_at, grok)


@unittest.skipUnless(_BASH, "bash required to execute the Step-0 detection fence")
class TestOpencodeDetectionExecutable(unittest.TestCase):
    """Run the actual canonical Step-0 bash under OpenCode fixtures."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.bash = _extract_step0_detection_bash(_read(WORKFLOW))
        if MANIFEST_DETECT not in cls.bash:
            raise AssertionError(
                "canonical Step-0 bash missing OpenCode manifest rung"
            )

    def _run(self, plugin_root: Path, home: Path, **host_env: str) -> str:
        env = {
            k: v for k, v in os.environ.items() if k not in HOST_ENV_KEYS
        }
        env["HOME"] = str(home)
        env["PLUGIN_ROOT"] = str(plugin_root)
        for k in HOST_ENV_KEYS:
            env.pop(k, None)
        env.update(host_env)
        script = f"set -eu\n{self.bash}\nprintf '%s\\n' \"$PLATFORM\"\n"
        proc = subprocess.run(
            [_BASH, "-c", script],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode != 0:
            raise AssertionError(
                f"detection bash failed (rc={proc.returncode}):\n"
                f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
            )
        return proc.stdout.strip()

    def test_manifest_at_plugin_root_is_opencode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            root = home / "opencode"
            root.mkdir()
            (root / ".flow-next-opencode-manifest").write_text(
                "skills/flow-next-setup/SKILL.md\n", encoding="utf-8"
            )
            self.assertEqual(self._run(root, home), "opencode")

    def test_plain_plugin_root_without_manifest_is_codex(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            root = home / "plugin"
            root.mkdir()
            self.assertEqual(self._run(root, home), "codex")

    def test_grok_wins_over_opencode_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            root = home / "opencode"
            root.mkdir()
            (root / ".flow-next-opencode-manifest").write_text(
                "skills/flow-next-setup/SKILL.md\n", encoding="utf-8"
            )
            self.assertEqual(
                self._run(root, home, GROK_AGENT="1"), "grok"
            )

    def test_inherited_claudecode_without_claude_manifest_is_opencode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            root = home / "opencode"
            root.mkdir()
            (root / ".flow-next-opencode-manifest").write_text(
                "skills/flow-next-setup/SKILL.md\n", encoding="utf-8"
            )
            self.assertEqual(
                self._run(root, home, CLAUDECODE="1"), "opencode"
            )


class TestOpencodeSetupProfile(unittest.TestCase):
    """PLATFORM=opencode: AGENTS.md target, default review menu, no Ralph."""

    def setUp(self) -> None:
        self.text = _read(WORKFLOW)

    def test_ralph_silently_skipped(self) -> None:
        self.assertIn(
            '[[ "$PLATFORM" == "cursor" || "$PLATFORM" == "grok" '
            '|| "$PLATFORM" == "opencode" ]]',
            self.text,
        )
        self.assertIn("unsupported on OpenCode", self.text)
        self.assertIn("Cursor/Grok/OpenCode", self.text)

    def test_lifecycle_and_routing_target_agents_md(self) -> None:
        self.assertIn("For **OpenCode** (`PLATFORM=opencode`)", self.text)
        self.assertIn("OpenCode reads AGENTS.md", self.text)
        self.assertIn(
            "Codex / Cursor / Grok / OpenCode → `AGENTS.md`", self.text
        )

    def test_flat_slash_rewrite_documented(self) -> None:
        self.assertIn("s|/flow-next:|/flow-next-|g", self.text)
        self.assertIn("/flow-next-<name>", self.text)

    def test_uses_default_review_menu(self) -> None:
        self.assertIn(
            "OpenCode uses this default Host + None menu", self.text
        )
        self.assertNotIn("When `PLATFORM=opencode`", self.text.split("**Review question**")[1].split("**Docs question**")[0])


if __name__ == "__main__":
    unittest.main()
