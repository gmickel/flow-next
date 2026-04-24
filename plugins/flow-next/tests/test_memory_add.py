"""Unit tests for `flowctl memory add` with overlap detection (fn-30 task 2).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers:
  - AC1: new --track/--category creates categorized entry with valid frontmatter
  - AC2: legacy --type auto-maps with deprecation warning
  - AC3: high overlap updates existing entry
  - AC4: moderate overlap creates new with related_to
  - AC5: --no-overlap-check bypasses detection
  - AC6: missing required fields -> exit 2
  - AC7: invalid category -> exit 2 with helpful message
  - AC8: bug track default problem_type derived from category
  - AC9: JSON output shape
  - AC10: overlap scoring across all dimensions
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location("flowctl_add_under_test", FLOWCTL_PY)
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
    """Initialize a fresh .flow/ repo with memory enabled + tree created."""
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


def _run_add(cwd: Path, *args: str, expect_rc: int = 0, input_bytes: bytes | None = None) -> dict[str, Any]:
    """Run `flowctl memory add ...` and return parsed JSON (success path).

    Set expect_rc to assert a non-zero exit; returns the raw stdout string
    in that case.
    """
    cmd = [sys.executable, str(FLOWCTL_PY), "memory", "add", *args, "--json"]
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "FLOW_NO_DEPRECATION": "1"},
    )
    if proc.returncode != expect_rc:
        raise AssertionError(
            f"add unexpected rc={proc.returncode} (expected {expect_rc}): "
            f"stdout={proc.stdout.decode()} stderr={proc.stderr.decode()}"
        )
    if proc.returncode == 0:
        return json.loads(proc.stdout.decode())
    # Non-success: return the error payload string for inspection.
    return {"_stdout": proc.stdout.decode(), "_stderr": proc.stderr.decode()}


# --- Overlap scoring (unit, no filesystem) ---


class TestOverlapScoring(unittest.TestCase):
    """AC10: scoring covers all four dimensions correctly."""

    def test_all_match_gives_4(self) -> None:
        fm = {"title": "OOM in webpack", "tags": ["webpack", "build"], "module": "src/build.ts"}
        score = flowctl._memory_score_overlap(
            "OOM in webpack", ["webpack"], "src/build.ts", fm
        )
        self.assertEqual(score, 4)

    def test_category_only_gives_1(self) -> None:
        fm = {"title": "entirely unrelated", "tags": ["x"], "module": "other/file"}
        score = flowctl._memory_score_overlap(
            "totally different", ["y"], "yet/another", fm
        )
        self.assertEqual(score, 1)

    def test_module_skipped_when_missing(self) -> None:
        fm = {"title": "foo bar", "tags": ["x"]}  # no module
        score = flowctl._memory_score_overlap("foo bar", ["x"], None, fm)
        # title match + tag match + category — module dimension skipped.
        self.assertEqual(score, 3)

    def test_tag_case_insensitive(self) -> None:
        fm = {"title": "x", "tags": ["Webpack"], "module": "a"}
        score = flowctl._memory_score_overlap("y", ["webpack"], "b", fm)
        # category + tag = 2.
        self.assertEqual(score, 2)

    def test_title_fuzzy_tokens(self) -> None:
        fm = {"title": "OOM in the webpack build", "tags": [], "module": ""}
        # 3-token new title shares 2 tokens ("oom", "webpack") with a 6-token
        # existing title. 2/3 == 0.67 >= 0.5 → title matches. (Overlap uses
        # min(new, existing) as denominator.)
        score = flowctl._memory_score_overlap("webpack oom spike", [], None, fm)
        # category + title = 2.
        self.assertEqual(score, 2)


class TestOverlapScan(unittest.TestCase):
    """check_memory_overlap integrates scoring with the filesystem."""

    def test_empty_category_is_low(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp) / "memory"
            (mem / "bug" / "runtime-errors").mkdir(parents=True)
            result = flowctl.check_memory_overlap(
                mem, "bug", "runtime-errors", "anything", [], None
            )
            self.assertEqual(result["level"], "low")

    def test_high_overlap_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp) / "memory"
            (mem / "bug" / "runtime-errors").mkdir(parents=True)
            flowctl.write_memory_entry(
                mem / "bug" / "runtime-errors" / "null-deref-2026-04-01.md",
                {
                    "title": "Null deref in auth",
                    "date": "2026-04-01",
                    "track": "bug",
                    "category": "runtime-errors",
                    "module": "src/auth.ts",
                    "tags": ["auth", "null"],
                    "problem_type": "runtime-error",
                    "symptoms": "x",
                    "root_cause": "y",
                    "resolution_type": "fix",
                },
                "body",
            )
            result = flowctl.check_memory_overlap(
                mem, "bug", "runtime-errors",
                "Null deref in auth middleware",
                ["auth"],
                "src/auth.ts",
            )
            self.assertEqual(result["level"], "high")
            self.assertEqual(len(result["matches"]), 1)
            self.assertEqual(
                result["matches"][0]["id"],
                "bug/runtime-errors/null-deref-2026-04-01",
            )

    def test_moderate_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp) / "memory"
            (mem / "knowledge" / "conventions").mkdir(parents=True)
            flowctl.write_memory_entry(
                mem / "knowledge" / "conventions" / "pnpm-2026-04-01.md",
                {
                    "title": "Prefer pnpm over npm",
                    "date": "2026-04-01",
                    "track": "knowledge",
                    "category": "conventions",
                    "tags": ["pnpm", "tooling"],
                    "applies_when": "choosing pm",
                },
                "",
            )
            # Different title; shared tag pnpm; no module → score = 2.
            result = flowctl.check_memory_overlap(
                mem, "knowledge", "conventions",
                "Lockfile discipline for workspaces",
                ["pnpm"],
                None,
            )
            self.assertEqual(result["level"], "moderate")
            self.assertEqual(len(result["matches"]), 1)


# --- Deprecation mapping ---


class TestLegacyTypeMapping(unittest.TestCase):
    """AC2: legacy --type maps to track/category."""

    def test_pitfall_maps_to_bug_build_errors(self) -> None:
        self.assertEqual(
            flowctl._memory_resolve_legacy_type("pitfall"),
            ("bug", "build-errors"),
        )

    def test_convention_maps_to_knowledge_conventions(self) -> None:
        self.assertEqual(
            flowctl._memory_resolve_legacy_type("convention"),
            ("knowledge", "conventions"),
        )

    def test_decision_maps_to_knowledge_tooling(self) -> None:
        self.assertEqual(
            flowctl._memory_resolve_legacy_type("decision"),
            ("knowledge", "tooling-decisions"),
        )

    def test_unknown_type_returns_none(self) -> None:
        self.assertIsNone(flowctl._memory_resolve_legacy_type("garbage"))

    def test_plural_forms_accepted(self) -> None:
        self.assertEqual(
            flowctl._memory_resolve_legacy_type("pitfalls"),
            ("bug", "build-errors"),
        )


# --- End-to-end via subprocess ---


class TestMemoryAddE2E(unittest.TestCase):
    """Integration: run `memory add` as a subprocess, verify outputs + files."""

    def test_new_schema_creates_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _init_repo(tmp)
            data = _run_add(
                tmp,
                "--track", "bug",
                "--category", "runtime-errors",
                "--title", "Null deref",
                "--module", "src/auth.ts",
                "--tags", "auth,null",
                "--problem-type", "runtime-error",
            )
            self.assertEqual(data["action"], "created")
            self.assertEqual(data["overlap_level"], "low")
            self.assertTrue(data["entry_id"].startswith("bug/runtime-errors/"))
            self.assertEqual(data["warnings"], [])
            # File exists with valid frontmatter.
            path = Path(data["path"])
            self.assertTrue(path.exists())
            fm = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(fm["track"], "bug")
            self.assertEqual(fm["category"], "runtime-errors")
            self.assertEqual(fm["problem_type"], "runtime-error")
            self.assertEqual(fm["tags"], ["auth", "null"])

    def test_legacy_type_backcompat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _init_repo(tmp)
            data = _run_add(tmp, "--type", "pitfall", "Oops entry")
            self.assertEqual(data["action"], "created")
            self.assertTrue(data["entry_id"].startswith("bug/build-errors/"))
            # Warning surfaces in JSON (even with FLOW_NO_DEPRECATION=1,
            # the payload warning is always present — only stderr is muted).
            self.assertTrue(
                any("deprecated" in w for w in data["warnings"]),
                data["warnings"],
            )

    def test_high_overlap_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _init_repo(tmp)
            # First add.
            first = _run_add(
                tmp,
                "--track", "bug",
                "--category", "runtime-errors",
                "--title", "Null deref in auth middleware",
                "--module", "src/auth.ts",
                "--tags", "auth,null",
            )
            self.assertEqual(first["action"], "created")
            # Second add — high overlap (title tokens + tags + module).
            second = _run_add(
                tmp,
                "--track", "bug",
                "--category", "runtime-errors",
                "--title", "Null deref auth middleware",
                "--module", "src/auth.ts",
                "--tags", "auth",
            )
            self.assertEqual(second["action"], "updated")
            self.assertEqual(second["overlap_level"], "high")
            self.assertEqual(second["path"], first["path"])
            # Existing entry now has last_updated.
            fm = flowctl.parse_memory_frontmatter(Path(second["path"]))
            self.assertIn("last_updated", fm)

    def test_moderate_overlap_related_to(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _init_repo(tmp)
            first = _run_add(
                tmp,
                "--track", "knowledge",
                "--category", "conventions",
                "--title", "Prefer pnpm over npm",
                "--tags", "pnpm,tooling",
                "--applies-when", "choosing pm",
            )
            # Different title; shared tag "pnpm"; no module -> score 2.
            second = _run_add(
                tmp,
                "--track", "knowledge",
                "--category", "conventions",
                "--title", "Workspace lockfile hygiene",
                "--tags", "pnpm,workspace",
                "--applies-when", "monorepo",
            )
            self.assertEqual(second["action"], "created")
            self.assertEqual(second["overlap_level"], "moderate")
            self.assertIn(first["entry_id"], second["related_to"])

    def test_no_overlap_check_forces_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _init_repo(tmp)
            _run_add(
                tmp,
                "--track", "bug", "--category", "runtime-errors",
                "--title", "Null deref",
                "--module", "src/auth.ts",
                "--tags", "auth",
            )
            data = _run_add(
                tmp,
                "--track", "bug", "--category", "runtime-errors",
                "--title", "Null deref",
                "--module", "src/auth.ts",
                "--tags", "auth",
                "--no-overlap-check",
            )
            self.assertEqual(data["action"], "created")
            self.assertEqual(data["overlap_level"], "low")

    def test_missing_title_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _init_repo(tmp)
            out = _run_add(
                tmp,
                "--track", "bug", "--category", "runtime-errors",
                expect_rc=2,
            )
            self.assertIn("title", (out.get("_stdout") or "") + (out.get("_stderr") or ""))

    def test_invalid_category_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _init_repo(tmp)
            out = _run_add(
                tmp,
                "--track", "bug", "--category", "not-a-real-category",
                "--title", "x",
                expect_rc=2,
            )
            combined = (out.get("_stdout") or "") + (out.get("_stderr") or "")
            self.assertIn("build-errors", combined)

    def test_stdin_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _init_repo(tmp)
            data = _run_add(
                tmp,
                "--track", "knowledge", "--category", "workflow",
                "--title", "Stdin body entry",
                "--applies-when", "sometimes",
                "--body-file", "-",
                input_bytes=b"## Section\n\nBody from stdin.\n",
            )
            self.assertEqual(data["action"], "created")
            text = Path(data["path"]).read_text(encoding="utf-8")
            self.assertIn("Body from stdin.", text)

    def test_bug_track_default_problem_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _init_repo(tmp)
            data = _run_add(
                tmp,
                "--track", "bug", "--category", "test-failures",
                "--title", "Snapshot mismatch",
                "--tags", "snap",
            )
            fm = flowctl.parse_memory_frontmatter(Path(data["path"]))
            self.assertEqual(fm["problem_type"], "test-failure")
            self.assertEqual(fm["resolution_type"], "fix")


if __name__ == "__main__":
    unittest.main()
