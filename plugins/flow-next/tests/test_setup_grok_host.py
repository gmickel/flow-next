"""Executable Step-0 platform detection for every host + Codex mirror guard.

Locks:

  (a) Canonical detection bash (extracted from flow-next-setup/workflow.md)
      classifies standalone GROK_AGENT=1 as grok; higher-precedence host
      signals win when present alongside GROK_AGENT; plain shell → codex;
      droid/claude/cursor/codex unregressed. fn-179 (#306) extends this to the
      claude-code rung: keyed on CLAUDECODE + the .claude-plugin manifest,
      placed below the hosts that prove themselves with their own signal.
      A PLUGIN_ROOT carrying .flow-next-opencode-manifest is opencode; GROK_AGENT
      still wins; absence of the file is not an OpenCode signal.
      A PLUGIN_ROOT carrying .flow-next-muse-bundle is muse ahead of every
      inherited marker; MUSE_SESSION_ID alone decides nothing.
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
    "MUSE_SESSION_ID",
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


def _build_claude_install(home: Path) -> Path:
    """Temp Claude-format plugin tree: PLUGIN_ROOT + .claude-plugin/plugin.json.

    fn-179 (#306): the claude-code rung's positive discriminator is this
    manifest at the resolved PLUGIN_ROOT (absent from a Codex install root,
    whose manifest is a top-level plugin.json).
    """
    root = home / "claude-plugins" / "flow-next"
    manifest = root / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text('{"name":"flow-next","version":"0.0.0"}\n', encoding="utf-8")
    return root


def _build_cursor_install(home: Path) -> Path:
    """Temp Cursor install tree: ~/.cursor/plugins/local/flow-next/ + manifest."""
    root = home / ".cursor" / "plugins" / "local" / "flow-next"
    manifest = root / ".cursor-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text('{"name":"flow-next","version":"0.0.0"}\n', encoding="utf-8")
    return root


def _build_opencode_install(home: Path) -> Path:
    """Temp OpenCode install root carrying .flow-next-opencode-manifest."""
    root = home / "opencode"
    root.mkdir(parents=True, exist_ok=True)
    (root / ".flow-next-opencode-manifest").write_text(
        "skills/flow-next-setup/SKILL.md\n", encoding="utf-8"
    )
    return root


def _build_muse_install(home: Path) -> Path:
    """Temp Muse bundle: the install-muse.sh marker beside the Claude manifest."""
    root = _build_claude_install(home)
    (root / ".flow-next-muse-bundle").write_text("flow-next Muse Code bundle\n", encoding="utf-8")
    return root


def _build_neutral_root(home: Path) -> Path:
    """A plugin root that is not under ~/.cursor and carries no host manifest."""
    root = home / "plugin-src" / "flow-next"
    root.mkdir(parents=True, exist_ok=True)
    return root


ROOTS = {
    "neutral": _build_neutral_root,
    "claude": _build_claude_install,
    "cursor": _build_cursor_install,
    "opencode": _build_opencode_install,
    "muse": _build_muse_install,
}

# (case, plugin root kind, host env, expected PLATFORM)
CANONICAL_CASES = (
    ("grok alone", "neutral", {"GROK_AGENT": "1"}, "grok"),
    ("plain shell", "neutral", {}, "codex"),
    ("droid alone", "neutral", {"DROID_PLUGIN_ROOT": "/tmp/droid-plugin"}, "droid"),
    ("droid wins over grok", "neutral",
     {"DROID_PLUGIN_ROOT": "/tmp/droid-plugin", "GROK_AGENT": "1"}, "droid"),
    # CLAUDECODE is inherited by children, GROK_AGENT is set by the grok
    # process itself: a grok child of a Claude shell is grok.
    ("grok wins over inherited CLAUDECODE", "claude",
     {"CLAUDECODE": "1", "GROK_AGENT": "1"}, "grok"),
    ("cursor wins over grok", "cursor", {"CURSOR_AGENT": "1", "GROK_AGENT": "1"}, "cursor"),
    # The env a running plugin skill sees on Claude Code: CLAUDECODE=1,
    # CLAUDE_PLUGIN_ROOT unset.
    ("claude-code plugin skill env", "claude", {"CLAUDECODE": "1"}, "claude-code"),
    # CLAUDE_PLUGIN_ROOT never reaches a plugin skill's Bash env, so it must
    # not decide the host.
    ("CLAUDE_PLUGIN_ROOT alone", "neutral", {"CLAUDE_PLUGIN_ROOT": "/tmp/claude-plugin"}, "codex"),
    # codex exec child of a Claude session: inherits CLAUDECODE, no
    # .claude-plugin/plugin.json at its PLUGIN_ROOT.
    ("inherited CLAUDECODE without claude manifest", "neutral", {"CLAUDECODE": "1"}, "codex"),
    ("droid wins over inherited CLAUDECODE", "claude",
     {"CLAUDECODE": "1", "DROID_PLUGIN_ROOT": "/tmp/droid"}, "droid"),
    ("cursor wins over inherited CLAUDECODE", "cursor",
     {"CURSOR_AGENT": "1", "CLAUDECODE": "1"}, "cursor"),
    ("cursor alone", "cursor", {"CURSOR_AGENT": "1"}, "cursor"),
    # Inherited CURSOR_AGENT with a non-cursor PLUGIN_ROOT is not cursor.
    ("CURSOR_AGENT without install tree", "neutral", {"CURSOR_AGENT": "1"}, "codex"),
    ("CURSOR_AGENT without install tree plus grok", "neutral",
     {"CURSOR_AGENT": "1", "GROK_AGENT": "1"}, "grok"),
    ("opencode manifest at plugin root", "opencode", {}, "opencode"),
    ("grok wins over opencode manifest", "opencode", {"GROK_AGENT": "1"}, "grok"),
    ("inherited CLAUDECODE with opencode manifest", "opencode", {"CLAUDECODE": "1"}, "opencode"),
    ("muse bundle", "muse", {"MUSE_SESSION_ID": "s"}, "muse"),
    # A Muse session launched from a Claude Code shell inherits CLAUDECODE, and
    # the Muse cache also carries the Claude manifest.
    ("muse bundle with inherited CLAUDECODE", "muse",
     {"MUSE_SESSION_ID": "s", "CLAUDECODE": "1"}, "muse"),
    ("muse bundle with inherited grok and droid", "muse",
     {"GROK_AGENT": "1", "DROID_PLUGIN_ROOT": "/tmp/droid"}, "muse"),
    # Codex and Claude Code children of a Muse shell inherit MUSE_SESSION_ID.
    ("inherited MUSE_SESSION_ID on a codex root", "neutral", {"MUSE_SESSION_ID": "s"}, "codex"),
    ("inherited MUSE_SESSION_ID on a claude root", "claude",
     {"MUSE_SESSION_ID": "s", "CLAUDECODE": "1"}, "claude-code"),
)

# The Codex mirror returns codex whatever the host signals say.
MIRROR_CASES = (
    ("every host signal", "cursor", {
        "GROK_AGENT": "1",
        "CURSOR_AGENT": "1",
        "CLAUDECODE": "1",
        "CLAUDE_PLUGIN_ROOT": "/tmp/claude-plugin",
        "DROID_PLUGIN_ROOT": "/tmp/droid-plugin",
    }, "codex"),
    ("plain", "neutral", {}, "codex"),
)


def _run_cases(test: unittest.TestCase, bash: str, cases) -> None:
    for case, root_kind, host_env, expected in cases:
        with test.subTest(case=case), tempfile.TemporaryDirectory() as td:
            home = Path(td)
            root = ROOTS[root_kind](home)
            env = _clean_env(str(home), str(root), **host_env)
            test.assertEqual(_run_detection(bash, env), expected)


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

    def test_detection_table(self) -> None:
        _run_cases(self, self.bash, CANONICAL_CASES)


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

    def test_mirror_detection_table(self) -> None:
        _run_cases(self, self.bash, MIRROR_CASES)


if __name__ == "__main__":
    unittest.main()
