"""Unit tests for `flowctl memory mark-fresh` (fn-34 task 2).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers:
  - mark-fresh on a stale entry: clears status (back to active default),
    clears audit_notes, stamps last_audited (today).
  - mark-fresh on a non-stale entry: stamps last_audited, no error.
  - --audited-by records `marked fresh (audited-by: X)` in audit_notes.
  - --json output shape.
  - Body preserved.
  - Unknown id → error.
  - Legacy id rejected with migrate hint.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_mark_fresh_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


@contextmanager
def _chdir(target: Path):
    prev = Path.cwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(prev)


def _init_repo(tmp: Path) -> Path:
    subprocess.check_call(
        [sys.executable, str(FLOWCTL_PY), "init", "--json"],
        cwd=tmp,
        stdout=subprocess.DEVNULL,
    )
    subprocess.check_call(
        [
            sys.executable,
            str(FLOWCTL_PY),
            "config",
            "set",
            "memory.enabled",
            "true",
            "--json",
        ],
        cwd=tmp,
        stdout=subprocess.DEVNULL,
    )
    subprocess.check_call(
        [sys.executable, str(FLOWCTL_PY), "memory", "init", "--json"],
        cwd=tmp,
        stdout=subprocess.DEVNULL,
    )
    return tmp / ".flow" / "memory"


def _seed_stale_entry(memory_dir: Path) -> Path:
    """Seed an entry already flagged stale."""
    entry_dir = memory_dir / "knowledge" / "conventions"
    entry_dir.mkdir(parents=True, exist_ok=True)
    path = entry_dir / "old-rule-2026-01-01.md"
    flowctl.write_memory_entry(
        path,
        {
            "title": "Old convention",
            "date": "2026-01-01",
            "track": "knowledge",
            "category": "conventions",
            "tags": ["old"],
            "applies_when": "writing typescript",
            "status": "stale",
            "last_audited": "2026-04-01",
            "audit_notes": "stale because superseded",
        },
        "Convention body content.\n",
    )
    return path


def _seed_active_entry(memory_dir: Path) -> Path:
    entry_dir = memory_dir / "knowledge" / "conventions"
    entry_dir.mkdir(parents=True, exist_ok=True)
    path = entry_dir / "fresh-rule-2026-04-01.md"
    flowctl.write_memory_entry(
        path,
        {
            "title": "Fresh convention",
            "date": "2026-04-01",
            "track": "knowledge",
            "category": "conventions",
            "applies_when": "writing typescript",
        },
        "Body.\n",
    )
    return path


def _run(cwd: Path, *args: str, expect_rc: int = 0) -> dict[str, Any]:
    cmd = [sys.executable, str(FLOWCTL_PY), *args]
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "FLOW_NO_DEPRECATION": "1"},
    )
    if proc.returncode != expect_rc:
        raise AssertionError(
            f"rc={proc.returncode} (expected {expect_rc}): args={args} "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    out_text = proc.stdout.decode()
    if out_text.strip().startswith("{"):
        try:
            return json.loads(out_text)
        except json.JSONDecodeError:
            pass
    return {"_stdout": out_text, "_stderr": proc.stderr.decode()}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class TestMarkFreshHappyPath(unittest.TestCase):
    def test_clears_stale_flag_and_stamps_last_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_stale_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-fresh",
                "knowledge/conventions/old-rule-2026-01-01",
                "--json",
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "active")
            self.assertEqual(result["last_audited"], _today())
            self.assertEqual(result["audit_notes"], "")

            fm = flowctl.parse_memory_frontmatter(path)
            # status removed entirely (active is the default; minimal frontmatter).
            self.assertNotIn("status", fm)
            self.assertNotIn("audit_notes", fm)
            self.assertEqual(fm["last_audited"], _today())

    def test_no_op_on_non_stale_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_active_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-fresh",
                "fresh-rule-2026-04-01",
                "--json",
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "active")
            self.assertEqual(result["last_audited"], _today())

            fm = flowctl.parse_memory_frontmatter(path)
            self.assertNotIn("status", fm)
            self.assertEqual(fm["last_audited"], _today())

    def test_audited_by_records_breadcrumb(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_stale_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-fresh",
                "old-rule-2026-01-01",
                "--audited-by",
                "audit-skill",
                "--json",
            )
            self.assertEqual(
                result["audit_notes"],
                "marked fresh (audited-by: audit-skill)",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(
                fm["audit_notes"],
                "marked fresh (audited-by: audit-skill)",
            )

    def test_body_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_stale_entry(mem)
            _run(
                Path(tmp),
                "memory",
                "mark-fresh",
                "old-rule-2026-01-01",
                "--json",
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn("Convention body content.", text)


class TestMarkFreshErrors(unittest.TestCase):
    def test_unknown_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_stale_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-fresh",
                "does-not-exist",
                "--json",
                expect_rc=1,
            )
            self.assertFalse(result["success"])
            self.assertIn("not found", result["error"])

    def test_legacy_id_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_stale_entry(mem)
            (mem / "decisions.md").write_text(
                "## 2026-01-01 manual\nDecision body.\n", encoding="utf-8"
            )
            result = _run(
                Path(tmp),
                "memory",
                "mark-fresh",
                "legacy/decisions.md",
                "--json",
                expect_rc=1,
            )
            self.assertFalse(result["success"])
            self.assertIn("legacy", result["error"].lower())


class TestMarkFreshRoundTrip(unittest.TestCase):
    def test_stale_then_fresh_roundtrip(self) -> None:
        """mark-stale then mark-fresh leaves entry in active default."""
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_active_entry(mem)
            _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "fresh-rule-2026-04-01",
                "--reason",
                "test",
                "--json",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["status"], "stale")
            self.assertEqual(fm["audit_notes"], "test")

            _run(
                Path(tmp),
                "memory",
                "mark-fresh",
                "fresh-rule-2026-04-01",
                "--json",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertNotIn("status", fm)
            self.assertNotIn("audit_notes", fm)
            self.assertEqual(fm["last_audited"], _today())


if __name__ == "__main__":
    unittest.main()
