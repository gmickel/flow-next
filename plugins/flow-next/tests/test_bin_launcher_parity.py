"""Unit tests for bin/ vs scripts/ flowctl launcher parity.

Asserts the two committed bash launchers differ by exactly one line (the
``exec`` target path), that the variants match the documented strings, and
that substituting the bin form for the scripts form yields byte-identical
files. Also checks ``bin/flowctl`` exists and is executable.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SRC_SCRIPTS = ROOT / "scripts" / "flowctl"
SRC_BIN = ROOT / "bin" / "flowctl"

SCRIPTS_EXEC = 'exec "${FLOW_PY[@]}" "$SCRIPT_DIR/flowctl.py" "$@"'
BIN_EXEC = 'exec "${FLOW_PY[@]}" "$SCRIPT_DIR/../scripts/flowctl.py" "$@"'


class TestBinLauncherParity(unittest.TestCase):
    """bin/flowctl and scripts/flowctl differ by exactly the exec target path."""

    def test_bin_flowctl_exists_and_is_executable(self) -> None:
        self.assertTrue(SRC_BIN.is_file(), f"missing launcher: {SRC_BIN}")
        self.assertTrue(
            os.access(SRC_BIN, os.X_OK),
            f"bin/flowctl is not executable: {SRC_BIN}",
        )

    def test_exactly_one_exec_line_differs(self) -> None:
        scripts_lines = SRC_SCRIPTS.read_text(encoding="utf-8").splitlines()
        bin_lines = SRC_BIN.read_text(encoding="utf-8").splitlines()

        self.assertEqual(
            len(scripts_lines),
            len(bin_lines),
            "launchers must have the same number of lines",
        )

        diffs = [
            (i, s, b)
            for i, (s, b) in enumerate(zip(scripts_lines, bin_lines))
            if s != b
        ]
        self.assertEqual(
            len(diffs),
            1,
            f"expected exactly one differing line, got {len(diffs)}: {diffs!r}",
        )

        _idx, scripts_line, bin_line = diffs[0]
        self.assertEqual(
            scripts_line,
            SCRIPTS_EXEC,
            "scripts/flowctl exec line drifted from the documented form",
        )
        self.assertEqual(
            bin_line,
            BIN_EXEC,
            "bin/flowctl exec line drifted from the documented form",
        )
        self.assertTrue(
            scripts_line.startswith("exec ") and bin_line.startswith("exec "),
            "the sole differing line must be the exec line",
        )

    def test_byte_identical_after_substituting_bin_exec(self) -> None:
        scripts_bytes = SRC_SCRIPTS.read_bytes()
        bin_text = SRC_BIN.read_text(encoding="utf-8")
        # Swap the bin exec line for the scripts exec line; result must match
        # scripts/flowctl byte-for-byte (same endings, same content).
        normalized = bin_text.replace(BIN_EXEC, SCRIPTS_EXEC)
        self.assertEqual(
            normalized.encode("utf-8"),
            scripts_bytes,
            "after substituting the bin exec line, launchers must be byte-identical",
        )


if __name__ == "__main__":
    unittest.main()
