"""cp1252 / non-UTF-8 robustness for flowctl (issue #167).

A legacy Windows console codepage (cp1252) plus a non-UTF-8 source subtree
(e.g. a German C/C++ tree carrying 0xfc ü / 0xe4 ä / 0xf6 ö / 0xdf ß) triggers
two independent flowctl faults:

  1. ``find_references()`` decodes ``git grep`` output with a hard
     ``encoding="utf-8"`` and no ``errors=`` — any grep hit whose file bytes
     are not valid UTF-8 raises ``UnicodeDecodeError`` (the impl-review
     read-side counterpart to #123). This is unavoidable by keeping edited
     files UTF-8: ``gather_context_hints`` greps each symbol repo-wide, so one
     legacy file anywhere is enough.
  2. flowctl's own stdout/stderr on a cp1252 console raises
     ``UnicodeEncodeError`` when printing non-ASCII ('→', umlauts).

These tests lock the read-side defensive decode and the startup stdio
reconfigure. Pure Python — no real codepage required.
"""

import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402


@contextmanager
def _chdir(path: Path):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def _init_repo_with_cp1252_file(root: Path) -> None:
    """A throwaway git repo whose one tracked file carries non-UTF-8 bytes.

    git grep searches tracked files, so staging is enough — no commit (which
    keeps the fixture independent of commit-signing setups)."""
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    # The searched symbol sits on the SAME non-UTF-8 line so the cp1252 bytes
    # land on git grep's stdout.
    (root / "legacy.c").write_bytes(
        b"int widget = 1;\n// \xfc\xe4\xf6 umlaut comment mentioning widget\n"
    )
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)


class FindReferencesCp1252(unittest.TestCase):
    def test_find_references_tolerates_non_utf8_grep_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            _init_repo_with_cp1252_file(root)
            with _chdir(root):
                # Must not raise UnicodeDecodeError, and must still locate the
                # reference despite the offending bytes on the matched line.
                refs = flowctl.find_references("widget", [])
        self.assertTrue(
            any(p.endswith("legacy.c") for p, _ in refs),
            f"expected a legacy.c hit, got {refs!r}",
        )


class StdioReconfigureUtf8(unittest.TestCase):
    def test_helper_forces_utf8_on_reconfigurable_streams(self):
        fake_out = mock.Mock()
        fake_err = mock.Mock()
        with mock.patch.object(sys, "stdout", fake_out), mock.patch.object(
            sys, "stderr", fake_err
        ):
            flowctl._reconfigure_stdio_utf8()
        fake_out.reconfigure.assert_called_once_with(
            encoding="utf-8", errors="replace"
        )
        fake_err.reconfigure.assert_called_once_with(
            encoding="utf-8", errors="replace"
        )

    def test_helper_is_noop_on_streams_without_reconfigure(self):
        # io.StringIO (unittest / pytest capture) has no reconfigure attribute —
        # the helper must leave such streams untouched, never raise.
        with mock.patch.object(sys, "stdout", io.StringIO()), mock.patch.object(
            sys, "stderr", io.StringIO()
        ):
            flowctl._reconfigure_stdio_utf8()

    def test_helper_swallows_reconfigure_failure(self):
        boom = mock.Mock()
        boom.reconfigure.side_effect = ValueError("already detached")
        with mock.patch.object(sys, "stdout", boom), mock.patch.object(
            sys, "stderr", boom
        ):
            flowctl._reconfigure_stdio_utf8()  # must not propagate

    def test_main_reconfigures_stdio_at_startup(self):
        # main() must force UTF-8 stdio before doing any work; verify the wiring
        # (argparse aborts on the missing subcommand, which is fine here).
        with mock.patch.object(flowctl, "_reconfigure_stdio_utf8") as m, mock.patch.object(
            sys, "argv", ["flowctl"]
        ):
            with self.assertRaises(SystemExit):
                flowctl.main()
        m.assert_called_once()


class DualCopyInvariant(unittest.TestCase):
    """The repo dogfoods a byte-identical ``.flow/bin/flowctl.py``; the #167
    fixes must land in BOTH copies or the live dogfood CLI runs stale code."""

    CANONICAL = REPO_ROOT / "plugins" / "flow-next" / "scripts" / "flowctl.py"
    DOGFOOD = REPO_ROOT / ".flow" / "bin" / "flowctl.py"

    def test_two_copies_byte_identical(self):
        self.assertEqual(
            self.CANONICAL.read_bytes(),
            self.DOGFOOD.read_bytes(),
            "scripts/flowctl.py and .flow/bin/flowctl.py must be byte-identical",
        )

    def test_both_copies_carry_the_167_fixes(self):
        for p in (self.CANONICAL, self.DOGFOOD):
            text = p.read_text(encoding="utf-8")
            self.assertIn("_reconfigure_stdio_utf8", text)
            self.assertIn(
                'result.stdout.decode("utf-8", errors="replace")',
                text,
                "find_references must decode git-grep bytes defensively",
            )


class WorkerResultRecoveryProse(unittest.TestCase):
    """Issue #167 item 1 — the work loop's Verify-Completion step must carry a
    recovery heuristic for a lost/error worker result (the harness-level
    ``[Tool result missing due to internal error]`` case), not just the
    status-not-done case."""

    PHASES = (
        REPO_ROOT
        / "plugins"
        / "flow-next"
        / "skills"
        / "flow-next-work"
        / "phases.md"
    )
    CODEX_PHASES = (
        REPO_ROOT
        / "plugins"
        / "flow-next"
        / "codex"
        / "skills"
        / "flow-next-work"
        / "phases.md"
    )

    def test_3d_documents_missing_result_recovery(self):
        text = self.PHASES.read_text(encoding="utf-8")
        lower = text.lower()
        self.assertIn("result missing", lower)
        # Distinguish already-done vs code-present-but-unfinalized via git.
        self.assertIn("git log", text)
        self.assertIn("git status", text)
        # Spawn a re-anchoring continuation worker rather than blocking.
        self.assertIn("continuation", lower)
        self.assertIn("re-anchor", lower)

    def test_codex_mirror_carries_recovery_prose(self):
        text = self.CODEX_PHASES.read_text(encoding="utf-8").lower()
        self.assertIn("result missing", text)
        self.assertIn("continuation", text)


if __name__ == "__main__":
    unittest.main()
