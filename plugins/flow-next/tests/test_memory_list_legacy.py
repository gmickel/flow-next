"""Unit tests for `flowctl memory list-legacy` (fn-35.2).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers:
  - AC: list-legacy text mode lists entries with mechanical default labels
  - AC: list-legacy --json returns the documented shape
    {"files": [{"filename", "entry_count", "entries": [...]}]}
  - AC: empty repo → "No legacy files found." (text) / {"files": []} (json)
  - AC: mechanical defaults match _memory_classify_mechanical output
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _init_repo(tmp: Path) -> Path:
    """Initialize a fresh .flow/ repo with memory enabled + tree created."""
    subprocess.check_call(
        ["git", "init", "-q"], cwd=tmp, stdout=subprocess.DEVNULL
    )
    subprocess.check_call(
        ["git", "config", "user.email", "t@t"], cwd=tmp
    )
    subprocess.check_call(
        ["git", "config", "user.name", "t"], cwd=tmp
    )
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


def _run(cwd: Path, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(FLOWCTL_PY), *args],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "FLOW_NO_DEPRECATION": "1"},
    )
    return proc.returncode, proc.stdout.decode(), proc.stderr.decode()


class TestMemoryListLegacy(unittest.TestCase):
    """`flowctl memory list-legacy` — text + JSON shape contract."""

    def test_empty_repo_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _init_repo(tmp_path)
            rc, out, err = _run(tmp_path, "memory", "list-legacy")
            self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
            self.assertIn("No legacy files found", out)

    def test_empty_repo_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _init_repo(tmp_path)
            rc, out, err = _run(tmp_path, "memory", "list-legacy", "--json")
            self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
            data = json.loads(out)
            self.assertTrue(data["success"])
            self.assertEqual(data["files"], [])

    def test_two_entries_in_pitfalls_json(self) -> None:
        """Pitfalls with two entries → entry_count=2, mechanical defaults bug/build-errors."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mem = _init_repo(tmp_path)
            (mem / "pitfalls.md").write_text(
                "# Pitfalls\n\n"
                "## 2026-03-01 Race condition\n"
                "Worker race during shutdown.\n\n"
                "---\n\n"
                "## 2026-03-15 Null crash\n"
                "Crash on empty payload.\n",
                encoding="utf-8",
            )
            rc, out, err = _run(tmp_path, "memory", "list-legacy", "--json")
            self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
            data = json.loads(out)
            self.assertEqual(len(data["files"]), 1)
            f = data["files"][0]
            self.assertEqual(f["filename"], "pitfalls.md")
            self.assertEqual(f["entry_count"], 2)
            self.assertEqual(len(f["entries"]), 2)
            for e in f["entries"]:
                # Source-of-truth: pitfalls.md → ("bug", "build-errors").
                self.assertEqual(e["mechanical_track"], "bug")
                self.assertEqual(e["mechanical_category"], "build-errors")
                # Required keys present.
                for key in ("title", "body", "tags", "date"):
                    self.assertIn(key, e)
            titles = [e["title"] for e in f["entries"]]
            self.assertEqual(titles, ["Race condition", "Null crash"])

    def test_text_mode_lists_filename_and_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mem = _init_repo(tmp_path)
            (mem / "conventions.md").write_text(
                "# Conventions\n\n## Use pnpm\nProject standard.\n",
                encoding="utf-8",
            )
            rc, out, err = _run(tmp_path, "memory", "list-legacy")
            self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
            self.assertIn("conventions.md", out)
            self.assertIn("1 entry", out)
            # Default label visible to humans.
            self.assertIn("knowledge/conventions", out)

    def test_multiple_legacy_files_separate_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mem = _init_repo(tmp_path)
            (mem / "pitfalls.md").write_text(
                "# Pitfalls\n\n## 2026-03-01 Race\nx.\n", encoding="utf-8"
            )
            (mem / "decisions.md").write_text(
                "# Decisions\n\n## 2026-02-01 Postgres\ny.\n", encoding="utf-8"
            )
            rc, out, err = _run(tmp_path, "memory", "list-legacy", "--json")
            self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
            data = json.loads(out)
            names = [f["filename"] for f in data["files"]]
            self.assertIn("pitfalls.md", names)
            self.assertIn("decisions.md", names)
            # Mechanical defaults differ per file.
            by_name = {f["filename"]: f for f in data["files"]}
            self.assertEqual(
                by_name["decisions.md"]["entries"][0]["mechanical_track"],
                "knowledge",
            )
            self.assertEqual(
                by_name["decisions.md"]["entries"][0]["mechanical_category"],
                "tooling-decisions",
            )


class TestMemoryMigrateMechanicalOnly(unittest.TestCase):
    """fn-35.2: migrate is now mechanical-only; --no-llm is a no-op."""

    def test_method_mechanical_model_null_in_json(self) -> None:
        """JSON receipt shape preserved: method=mechanical, model=null."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mem = _init_repo(tmp_path)
            (mem / "pitfalls.md").write_text(
                "# Pitfalls\n\n## 2026-03-01 Race\nx.\n", encoding="utf-8"
            )
            rc, out, err = _run(
                tmp_path, "memory", "migrate", "--yes", "--json"
            )
            self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
            data = json.loads(out)
            self.assertTrue(data["success"])
            self.assertEqual(len(data["migrated"]), 1)
            entry = data["migrated"][0]
            self.assertEqual(entry["method"], "mechanical")
            self.assertIsNone(entry["model"])

    def test_no_llm_flag_is_noop(self) -> None:
        """--no-llm runs identical mechanical path (kept for backcompat)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mem = _init_repo(tmp_path)
            (mem / "pitfalls.md").write_text(
                "# Pitfalls\n\n## 2026-03-01 Race\nx.\n", encoding="utf-8"
            )
            rc, out, err = _run(
                tmp_path, "memory", "migrate", "--yes", "--no-llm", "--json"
            )
            self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
            data = json.loads(out)
            self.assertTrue(data["success"])
            self.assertEqual(data["migrated"][0]["method"], "mechanical")
            self.assertIsNone(data["migrated"][0]["model"])

    def test_json_pipeline_clean_with_classifier_env_set(self) -> None:
        """Even with FLOW_MEMORY_CLASSIFIER_BACKEND set, --json stdout stays parseable."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mem = _init_repo(tmp_path)
            (mem / "pitfalls.md").write_text(
                "# Pitfalls\n\n## 2026-03-01 Race\nx.\n", encoding="utf-8"
            )
            env = {
                **os.environ,
                "FLOW_MEMORY_CLASSIFIER_BACKEND": "codex",
                "FLOW_NO_DEPRECATION": "1",  # suppress hint to keep stderr quiet
            }
            proc = subprocess.run(
                [
                    sys.executable,
                    str(FLOWCTL_PY),
                    "memory",
                    "migrate",
                    "--yes",
                    "--json",
                ],
                cwd=tmp_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertEqual(proc.returncode, 0)
            # stdout must be valid JSON (no stderr leak).
            data = json.loads(proc.stdout.decode())
            self.assertTrue(data["success"])
            self.assertEqual(data["migrated"][0]["method"], "mechanical")


class TestClassifierFunctionsRemoved(unittest.TestCase):
    """fn-35.2 R7: six subprocess functions are gone from the module."""

    def test_subprocess_classifier_functions_absent(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "flowctl_under_test_fn35", FLOWCTL_PY
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        for name in (
            "_memory_classify_run_codex",
            "_memory_classify_run_copilot",
            "_memory_classify_select_backend",
            "_memory_classify_build_prompt",
            "_memory_classify_parse_response",
            "_memory_classify_entry",
        ):
            self.assertFalse(
                hasattr(mod, name),
                f"{name} should have been removed in fn-35.2",
            )

    def test_preserved_helpers_still_present(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "flowctl_under_test_fn35_preserved", FLOWCTL_PY
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        self.assertTrue(hasattr(mod, "_memory_classify_mechanical"))
        self.assertTrue(hasattr(mod, "_memory_parse_legacy_entries"))
        # New subcommand handler.
        self.assertTrue(hasattr(mod, "cmd_memory_list_legacy"))


if __name__ == "__main__":
    unittest.main()
