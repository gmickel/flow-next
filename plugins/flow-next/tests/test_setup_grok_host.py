"""fn-126 R4 — executable Step-0 platform detection + Codex mirror guard.

Locks:

  (a) Canonical detection bash (extracted from flow-next-setup/workflow.md)
      classifies standalone GROK_AGENT=1 as grok; higher-precedence host
      signals win when present alongside GROK_AGENT; plain shell → codex;
      droid/claude/cursor/codex unregressed.
  (b) Codex mirror Step-0 is unconditional PLATFORM=codex — even with
      GROK_AGENT=1 and every other host signal set, the mirror returns codex.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_setup_grok_host -q
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
CANONICAL_WF = PLUGIN / "skills" / "flow-next-setup" / "workflow.md"
MIRROR_WF = PLUGIN / "codex" / "skills" / "flow-next-setup" / "workflow.md"

# Host signals the detection cascade keys on — scrub so the ambient agent shell
# cannot poison fixture classification (this test often runs inside Claude/Grok).
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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _extract_step0_detection_bash(text: str, *, source: str) -> str:
    """Extract the Step-0 platform-detection bash fence.

    Anchor: Step-0 heading → first ```bash fence under it. Exactly one match.
    """
    heads = list(_STEP0_HEADING.finditer(text))
    if len(heads) != 1:
        raise AssertionError(
            f"{source}: expected exactly one Step-0 heading, found {len(heads)}"
        )
    after = text[heads[0].end() :]
    # Stop at the next ## heading so we only look inside Step 0.
    next_h2 = re.search(r"(?m)^## ", after)
    step0 = after[: next_h2.start()] if next_h2 else after
    fences = list(_FIRST_BASH_FENCE.finditer(step0))
    if len(fences) != 1:
        raise AssertionError(
            f"{source}: expected exactly one ```bash fence under Step 0, "
            f"found {len(fences)}"
        )
    return fences[0].group(1)


def _clean_env(home: str, plugin_root: str, **extra: str) -> dict[str, str]:
    """Minimal env: scrub host signals, pin HOME/PLUGIN_ROOT, keep PATH."""
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in HOST_ENV_KEYS
    }
    env["HOME"] = home
    env["PLUGIN_ROOT"] = plugin_root
    # Drop any residual host keys, then apply fixture overrides.
    for k in HOST_ENV_KEYS:
        env.pop(k, None)
    env.update(extra)
    return env


def _run_detection(bash_body: str, env: dict[str, str]) -> str:
    script = f"set -eu\n{bash_body}\nprintf '%s\\n' \"$PLATFORM\"\n"
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


def _build_cursor_install(home: Path) -> Path:
    """Temp Cursor install tree: ~/.cursor/plugins/local/flow-next/ + manifest."""
    root = home / ".cursor" / "plugins" / "local" / "flow-next"
    manifest = root / ".cursor-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text('{"name":"flow-next","version":"0.0.0"}\n', encoding="utf-8")
    return root


@unittest.skipUnless(_BASH, "bash required to execute the Step-0 detection fence")
class TestCanonicalDetectionExecutable(unittest.TestCase):
    """R4: run the ACTUAL canonical Step-0 bash under controlled fixtures."""

    @classmethod
    def setUpClass(cls) -> None:
        if not CANONICAL_WF.is_file():
            raise AssertionError(f"missing {CANONICAL_WF}")
        cls.bash = _extract_step0_detection_bash(
            _read(CANONICAL_WF), source="canonical workflow"
        )
        # Sanity: the extracted body is the multi-host cascade, not unconditional.
        if "GROK_AGENT" not in cls.bash:
            raise AssertionError(
                "canonical Step-0 bash missing GROK_AGENT rung — extraction wrong?"
            )
        if 'PLATFORM="codex"' not in cls.bash:
            raise AssertionError("canonical Step-0 bash missing codex fallback")

    def _run(self, plugin_root: str | None = None, **host_env: str) -> str:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            # Default plugin root: neutral path (not under ~/.cursor).
            pr = plugin_root or str(home / "plugin-src" / "flow-next")
            Path(pr).mkdir(parents=True, exist_ok=True)
            env = _clean_env(str(home), pr, **host_env)
            return _run_detection(self.bash, env)

    def test_exactly_one_step0_bash_fence(self) -> None:
        # Extraction already asserts; re-run for an explicit unit-test name.
        body = _extract_step0_detection_bash(
            _read(CANONICAL_WF), source="canonical workflow"
        )
        self.assertIn("GROK_AGENT", body)
        self.assertIn("DROID_PLUGIN_ROOT", body)
        self.assertIn("CLAUDE_PLUGIN_ROOT", body)
        self.assertIn("CURSOR_AGENT", body)

    def test_grok_agent_alone_is_grok(self) -> None:
        self.assertEqual(self._run(GROK_AGENT="1"), "grok")

    def test_plain_shell_is_codex(self) -> None:
        self.assertEqual(self._run(), "codex")

    def test_droid_wins_over_grok(self) -> None:
        self.assertEqual(
            self._run(DROID_PLUGIN_ROOT="/tmp/droid-plugin", GROK_AGENT="1"),
            "droid",
        )

    def test_claude_wins_over_grok(self) -> None:
        self.assertEqual(
            self._run(CLAUDE_PLUGIN_ROOT="/tmp/claude-plugin", GROK_AGENT="1"),
            "claude-code",
        )

    def test_cursor_wins_over_grok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            cursor_root = _build_cursor_install(home)
            env = _clean_env(
                str(home),
                str(cursor_root),
                CURSOR_AGENT="1",
                GROK_AGENT="1",
            )
            self.assertEqual(_run_detection(self.bash, env), "cursor")

    def test_droid_alone(self) -> None:
        self.assertEqual(self._run(DROID_PLUGIN_ROOT="/tmp/droid-plugin"), "droid")

    def test_claude_alone(self) -> None:
        self.assertEqual(
            self._run(CLAUDE_PLUGIN_ROOT="/tmp/claude-plugin"), "claude-code"
        )

    def test_cursor_alone(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            cursor_root = _build_cursor_install(home)
            env = _clean_env(str(home), str(cursor_root), CURSOR_AGENT="1")
            self.assertEqual(_run_detection(self.bash, env), "cursor")

    def test_cursor_agent_without_install_tree_falls_to_codex(self) -> None:
        # Inherited CURSOR_AGENT + non-cursor PLUGIN_ROOT → codex (not cursor).
        self.assertEqual(self._run(CURSOR_AGENT="1"), "codex")

    def test_cursor_agent_without_install_plus_grok_is_grok(self) -> None:
        # No cursor path match → fall through; GROK_AGENT then wins over else.
        self.assertEqual(self._run(CURSOR_AGENT="1", GROK_AGENT="1"), "grok")


@unittest.skipUnless(_BASH, "bash required to execute the mirror Step-0 detection fence")
class TestMirrorUnconditionalCodex(unittest.TestCase):
    """R4: Codex mirror Step-0 is unconditional PLATFORM=codex."""

    @classmethod
    def setUpClass(cls) -> None:
        if not MIRROR_WF.is_file():
            raise AssertionError(
                f"missing {MIRROR_WF} — run ./scripts/sync-codex.sh first"
            )
        cls.bash = _extract_step0_detection_bash(
            _read(MIRROR_WF), source="codex mirror workflow"
        )

    def test_mirror_bash_has_no_host_detection_branches(self) -> None:
        for signal in (
            "GROK_AGENT",
            "CURSOR_AGENT",
            "DROID_PLUGIN_ROOT",
            "CLAUDE_PLUGIN_ROOT",
        ):
            self.assertNotIn(
                signal,
                self.bash,
                f"mirror Step-0 bash must not branch on {signal}",
            )
        self.assertIn('PLATFORM="codex"', self.bash)

    def test_mirror_returns_codex_with_every_host_signal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            cursor_root = _build_cursor_install(home)
            env = _clean_env(
                str(home),
                str(cursor_root),
                GROK_AGENT="1",
                CURSOR_AGENT="1",
                CLAUDE_PLUGIN_ROOT="/tmp/claude-plugin",
                DROID_PLUGIN_ROOT="/tmp/droid-plugin",
            )
            self.assertEqual(_run_detection(self.bash, env), "codex")

    def test_mirror_returns_codex_plain(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            pr = home / "plugin"
            pr.mkdir()
            env = _clean_env(str(home), str(pr))
            self.assertEqual(_run_detection(self.bash, env), "codex")


class TestGrokProfileContract(unittest.TestCase):
    """fn-126 R2 (codex impl-review P1): lock the FULL Grok profile in the
    canonical setup workflow (not just detection), via exact-substring checks
    against known markers — so half-configured Grok support fails the test."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wf = _read(CANONICAL_WF)

    def test_generic_review_menu_excludes_grok(self) -> None:
        # Catch-all review menu must exclude cursor AND grok, else grok
        # double-matches the dedicated grok menu and may emit a host-less menu.
        self.assertNotIn("**When `PLATFORM` is NOT `cursor`**", self.wf)
        self.assertIn("neither `cursor` nor `grok`", self.wf)

    def test_dedicated_grok_review_menu(self) -> None:
        self.assertIn("When `PLATFORM=grok`", self.wf)

    def test_grok_skips_codex_agents_copy(self) -> None:
        self.assertIn("Grok never copies `.codex/agents`", self.wf)

    def test_grok_no_ralph_convert_recommended(self) -> None:
        self.assertIn("on Cursor **and Grok** recommend CONVERT", self.wf)

    def test_grok_snippet_target_claude_md(self) -> None:
        self.assertIn("lifecycle snippet targets CLAUDE.md", self.wf)


if __name__ == "__main__":
    unittest.main()
