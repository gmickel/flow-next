"""Unit tests for `flowctl memory search --status` filter (fn-34 task 2).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers:
  - Default `--status active` excludes stale entries.
  - `--status stale` returns only stale entries.
  - `--status all` returns both active and stale.
  - Invalid `--status` value rejected.
  - Existing `memory list --status` still works (no regression).
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
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_search_status_under_test", FLOWCTL_PY
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


def _seed_entries(memory_dir: Path) -> None:
    """Two active + one stale entry, all matching query 'webpack'."""
    (memory_dir / "bug" / "build-errors").mkdir(parents=True, exist_ok=True)
    flowctl.write_memory_entry(
        memory_dir / "bug" / "build-errors" / "webpack-oom-2026-04-01.md",
        {
            "title": "webpack OOM during prod build",
            "date": "2026-04-01",
            "track": "bug",
            "category": "build-errors",
            "tags": ["webpack", "oom"],
            "problem_type": "build-error",
            "symptoms": "build dies with OOM",
            "root_cause": "memory cap too low",
            "resolution_type": "fix",
        },
        "Fixed by raising NODE_OPTIONS heap.\n",
    )
    flowctl.write_memory_entry(
        memory_dir / "bug" / "build-errors" / "webpack-cache-2026-04-15.md",
        {
            "title": "webpack cache invalidation regressed",
            "date": "2026-04-15",
            "track": "bug",
            "category": "build-errors",
            "tags": ["webpack", "cache"],
            "problem_type": "build-error",
            "symptoms": "stale outputs",
            "root_cause": "cache key omitted env",
            "resolution_type": "fix",
        },
        "Cache key now includes NODE_ENV.\n",
    )
    flowctl.write_memory_entry(
        memory_dir / "bug" / "build-errors" / "webpack-old-2026-01-01.md",
        {
            "title": "webpack old advice (stale)",
            "date": "2026-01-01",
            "track": "bug",
            "category": "build-errors",
            "tags": ["webpack"],
            "problem_type": "build-error",
            "symptoms": "old symptom",
            "root_cause": "old reason",
            "resolution_type": "fix",
            "status": "stale",
            "last_audited": "2026-04-01",
            "audit_notes": "obsolete after vite migration",
        },
        "Stale advice body.\n",
    )


def _run(cwd: Path, *args: str, expect_rc: int = 0) -> dict[str, Any]:
    cmd = [sys.executable, str(FLOWCTL_PY), *args, "--json"]
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
    if proc.returncode == 0:
        return json.loads(proc.stdout.decode())
    return {"_stdout": proc.stdout.decode(), "_stderr": proc.stderr.decode()}


def _categorized_ids(matches: list[dict[str, Any]]) -> set[str]:
    return {
        m["entry_id"] for m in matches if m.get("track") in ("bug", "knowledge")
    }


class TestMemorySearchStatus(unittest.TestCase):
    def test_default_active_excludes_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(Path(tmp), "memory", "search", "webpack")
            ids = _categorized_ids(data["matches"])
            self.assertIn("bug/build-errors/webpack-oom-2026-04-01", ids)
            self.assertIn("bug/build-errors/webpack-cache-2026-04-15", ids)
            self.assertNotIn("bug/build-errors/webpack-old-2026-01-01", ids)

    def test_status_stale_returns_only_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(
                Path(tmp), "memory", "search", "webpack", "--status", "stale"
            )
            ids = _categorized_ids(data["matches"])
            self.assertEqual(
                ids, {"bug/build-errors/webpack-old-2026-01-01"}
            )

    def test_status_all_returns_both(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(
                Path(tmp), "memory", "search", "webpack", "--status", "all"
            )
            ids = _categorized_ids(data["matches"])
            self.assertIn("bug/build-errors/webpack-oom-2026-04-01", ids)
            self.assertIn("bug/build-errors/webpack-cache-2026-04-15", ids)
            self.assertIn("bug/build-errors/webpack-old-2026-01-01", ids)

    def test_invalid_status_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            # argparse's choices=... fails with rc=2 before the cmd runs.
            result = _run(
                Path(tmp),
                "memory",
                "search",
                "webpack",
                "--status",
                "wat",
                expect_rc=2,
            )
            self.assertIn("invalid choice", result["_stderr"])

    def test_list_status_still_works(self) -> None:
        """No regression on the existing `memory list --status` filter."""
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(Path(tmp), "memory", "list", "--status", "stale")
            ids = {e["entry_id"] for e in data["entries"]}
            self.assertEqual(
                ids, {"bug/build-errors/webpack-old-2026-01-01"}
            )


if __name__ == "__main__":
    unittest.main()
