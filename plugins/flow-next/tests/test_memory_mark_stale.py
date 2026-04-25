"""Unit tests for `flowctl memory mark-stale` (fn-34 task 2).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers:
  - Sets status: stale, last_audited (today), audit_notes from --reason.
  - --audited-by appends `(audited-by: X)` suffix to audit_notes.
  - --json output shape.
  - --reason missing → exit 2 (argparse `required=True`).
  - Re-marking already-stale entry is idempotent (last_audited + audit_notes
    update; no error).
  - Body content preserved across the write.
  - Unknown id → error.
  - Legacy id rejected with migrate hint.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
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
        "flowctl_mark_stale_under_test", FLOWCTL_PY
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


def _seed_entry(memory_dir: Path) -> Path:
    """Drop one categorized entry; return its path."""
    entry_dir = memory_dir / "bug" / "runtime-errors"
    entry_dir.mkdir(parents=True, exist_ok=True)
    path = entry_dir / "null-deref-in-auth-2026-05-01.md"
    flowctl.write_memory_entry(
        path,
        {
            "title": "Null deref in auth middleware",
            "date": "2026-05-01",
            "track": "bug",
            "category": "runtime-errors",
            "module": "src/auth.ts",
            "tags": ["auth", "null"],
            "problem_type": "runtime-error",
            "symptoms": "500 on /me",
            "root_cause": "user.role accessed without guard",
            "resolution_type": "fix",
        },
        "Body: user.role propagation issue; fix added a guard.\n",
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


class TestMarkStaleHappyPath(unittest.TestCase):
    def test_sets_status_audit_notes_and_last_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "bug/runtime-errors/null-deref-in-auth-2026-05-01",
                "--reason",
                "src/auth.ts moved to src/middleware/auth.ts",
                "--json",
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "stale")
            self.assertEqual(result["last_audited"], _today())
            self.assertEqual(
                result["audit_notes"],
                "src/auth.ts moved to src/middleware/auth.ts",
            )

            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["status"], "stale")
            self.assertEqual(fm["last_audited"], _today())
            self.assertEqual(
                fm["audit_notes"],
                "src/auth.ts moved to src/middleware/auth.ts",
            )

    def test_body_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "null-deref-in-auth-2026-05-01",
                "--reason",
                "x",
                "--json",
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn(
                "user.role propagation issue; fix added a guard.", text
            )

    def test_audited_by_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "null-deref-in-auth",
                "--reason",
                "code path removed",
                "--audited-by",
                "audit-skill",
                "--json",
            )
            self.assertEqual(
                result["audit_notes"],
                "code path removed (audited-by: audit-skill)",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertIn("(audited-by: audit-skill)", fm["audit_notes"])

    def test_human_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "null-deref-in-auth-2026-05-01",
                "--reason",
                "x",
            )
            self.assertIn("Flagged stale", result["_stdout"])
            self.assertIn(_today(), result["_stdout"])


class TestMarkStaleErrors(unittest.TestCase):
    def test_missing_reason_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "null-deref-in-auth-2026-05-01",
                expect_rc=2,
            )
            combined = result["_stdout"] + result["_stderr"]
            self.assertTrue(
                re.search(r"--reason", combined),
                f"expected argparse to mention --reason; got: {combined!r}",
            )

    def test_unknown_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entry(mem)
            result = _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "does-not-exist",
                "--reason",
                "x",
                "--json",
                expect_rc=1,
            )
            self.assertFalse(result["success"])
            self.assertIn("not found", result["error"])

    def test_legacy_id_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entry(mem)
            (mem / "pitfalls.md").write_text(
                "## 2026-01-01 manual\nLegacy entry.\n", encoding="utf-8"
            )
            result = _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "legacy/pitfalls.md",
                "--reason",
                "x",
                "--json",
                expect_rc=1,
            )
            self.assertFalse(result["success"])
            self.assertIn("legacy", result["error"].lower())
            self.assertIn("migrate", result["error"])


class TestMarkStaleIdempotent(unittest.TestCase):
    def test_remark_updates_audit_notes_and_last_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            path = _seed_entry(mem)
            _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "null-deref-in-auth-2026-05-01",
                "--reason",
                "first reason",
                "--json",
            )
            second = _run(
                Path(tmp),
                "memory",
                "mark-stale",
                "null-deref-in-auth-2026-05-01",
                "--reason",
                "second reason",
                "--audited-by",
                "second-pass",
                "--json",
            )
            self.assertTrue(second["success"])
            self.assertEqual(
                second["audit_notes"],
                "second reason (audited-by: second-pass)",
            )
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["status"], "stale")
            self.assertEqual(
                fm["audit_notes"],
                "second reason (audited-by: second-pass)",
            )


if __name__ == "__main__":
    unittest.main()
