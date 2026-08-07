"""Unit tests for `flowctl memory` core verbs: add, list/read/search,
search --status, and list-legacy.

Consolidates the former micro-suites (zero assertion loss):
  - test_memory_add.py           — `memory add` + overlap signal (fn-30 / fn-113)
  - test_memory_list_read_search.py — `memory list / read / search` (fn-30 task 3)
  - test_memory_search_status.py — `memory search --status` filter (fn-34 task 2)
  - test_memory_list_legacy.py   — `memory list-legacy` (fn-35.2)

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers (add — fn-30 / fn-113):
  - AC1: new --track/--category creates categorized entry with valid frontmatter
  - AC2: legacy --type auto-maps with deprecation warning
  - AC3: high overlap WITHOUT --update creates a new entry AND surfaces matches
  - AC3b: explicit --update <id> updates that entry (merge semantics)
  - AC4: moderate overlap creates new with related_to
  - AC5: --no-overlap-check bypasses scoring (empty matches)
  - AC6: missing required fields -> exit 2
  - AC7: invalid category -> exit 2 with helpful message
  - AC8: bug track default problem_type derived from category
  - AC9: JSON output shape includes matches
  - AC10: overlap scoring across all dimensions

Covers (list / read / search — fn-30 task 3):
  - AC1: list walks the tree and groups by category.
  - AC2: --track filter narrows track.
  - AC3: --category filter narrows category.
  - AC4: --status stale returns stale-only entries.
  - AC5: read accepts full id, slug+date, and slug-only forms.
  - AC6: search returns relevance-ranked results across tracks.
  - AC7: search covers legacy flat files.
  - AC8: --json schemas match.

Covers (search --status — fn-34 task 2):
  - Default `--status active` excludes stale entries.
  - `--status stale` returns only stale entries.
  - `--status all` returns both active and stale.
  - Invalid `--status` value rejected.
  - Existing `memory list --status` still works (no regression).

Covers (list-legacy — fn-35.2):
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
from contextlib import contextmanager
from pathlib import Path
from typing import Any

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import flowctl  # noqa: E402  (path-injected import)


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


@contextmanager
def _chdir(target: Path):
    prev = Path.cwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(prev)


def _init_repo(tmp: Path, *, git: bool = False) -> Path:
    """Initialize a fresh .flow/ repo with memory enabled + tree created."""
    if git:
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
            f"rc={proc.returncode} (expected {expect_rc}): "
            f"args={args} stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    if proc.returncode == 0:
        return json.loads(proc.stdout.decode())
    return {"_stdout": proc.stdout.decode(), "_stderr": proc.stderr.decode()}


def _run_raw(cwd: Path, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(FLOWCTL_PY), *args],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "FLOW_NO_DEPRECATION": "1"},
    )
    return proc.returncode, proc.stdout.decode(), proc.stderr.decode()


def _seed_entries(memory_dir: Path) -> None:
    """Drop a fixed set of entries across bug + knowledge + stale + legacy."""
    (memory_dir / "bug" / "runtime-errors").mkdir(parents=True, exist_ok=True)
    flowctl.write_memory_entry(
        memory_dir / "bug" / "runtime-errors" / "null-deref-in-auth-2026-05-01.md",
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
        "Accessing user.role without a guard led to undefined propagation.",
    )
    flowctl.write_memory_entry(
        memory_dir / "bug" / "runtime-errors" / "null-deref-in-auth-2026-06-01.md",
        {
            "title": "Null deref in auth middleware v2",
            "date": "2026-06-01",
            "track": "bug",
            "category": "runtime-errors",
            "module": "src/auth.ts",
            "tags": ["auth"],
            "problem_type": "runtime-error",
            "symptoms": "still 500",
            "root_cause": "regression",
            "resolution_type": "fix",
        },
        "Regression surfaced after refactor.",
    )

    (memory_dir / "knowledge" / "conventions").mkdir(parents=True, exist_ok=True)
    flowctl.write_memory_entry(
        memory_dir / "knowledge" / "conventions" / "prefer-satisfies-2026-05-02.md",
        {
            "title": "Prefer satisfies over as for type assertions",
            "date": "2026-05-02",
            "track": "knowledge",
            "category": "conventions",
            "tags": ["typescript"],
            "applies_when": "writing typescript types",
        },
        "Using `satisfies` preserves literal types while ensuring conformance.",
    )
    flowctl.write_memory_entry(
        memory_dir / "knowledge" / "conventions" / "stale-rule-2026-01-01.md",
        {
            "title": "Old convention",
            "date": "2026-01-01",
            "track": "knowledge",
            "category": "conventions",
            "tags": ["old"],
            "applies_when": "never",
            "status": "stale",
            "stale_reason": "superseded",
            "stale_date": "2026-04-24",
        },
        "Obsolete convention.",
    )

    # Legacy flat file.
    (memory_dir / "pitfalls.md").write_text(
        "# Pitfalls\n\n"
        "## 2026-01-01 manual\n"
        "Legacy pitfall about null deref in auth middleware.\n\n"
        "---\n\n"
        "## 2026-02-01 manual\n"
        "Another legacy pitfall about caching.\n",
        encoding="utf-8",
    )


def _seed_webpack_entries(memory_dir: Path) -> None:
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


def _categorized_ids(matches: list[dict[str, Any]]) -> set[str]:
    return {
        m["entry_id"] for m in matches if m.get("track") in ("bug", "knowledge")
    }


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
            self.assertGreaterEqual(result["matches"][0]["score"], 3)

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
            self.assertEqual(result["matches"][0]["score"], 2)


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


# --- add: end-to-end via subprocess ---


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
            self.assertEqual(data["matches"], [])
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

    def test_high_overlap_creates_and_surfaces_matches(self) -> None:
        """fn-113: high overlap WITHOUT --update creates; matches emitted."""
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
            self.assertEqual(first["matches"], [])
            # Second add — high overlap (title tokens + tags + module).
            # Must CREATE (not auto-update) and surface the match signal.
            second = _run_add(
                tmp,
                "--track", "bug",
                "--category", "runtime-errors",
                "--title", "Null deref auth middleware",
                "--module", "src/auth.ts",
                "--tags", "auth",
            )
            self.assertEqual(second["action"], "created")
            self.assertEqual(second["overlap_level"], "high")
            self.assertNotEqual(second["path"], first["path"])
            self.assertEqual(len(second["matches"]), 1)
            self.assertEqual(second["matches"][0]["id"], first["entry_id"])
            self.assertGreaterEqual(second["matches"][0]["score"], 3)
            # Existing entry was NOT mutated (no last_updated).
            fm_first = flowctl.parse_memory_frontmatter(Path(first["path"]))
            self.assertNotIn("last_updated", fm_first)
            # Two files on disk.
            cat = tmp / ".flow" / "memory" / "bug" / "runtime-errors"
            md_files = [p for p in cat.iterdir() if p.suffix == ".md"]
            self.assertEqual(len(md_files), 2)

    def test_explicit_update_mutates_named_entry(self) -> None:
        """fn-113: --update <id> is the only path that mutates an existing entry."""
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _init_repo(tmp)
            first = _run_add(
                tmp,
                "--track", "bug",
                "--category", "runtime-errors",
                "--title", "Null deref in auth middleware",
                "--module", "src/auth.ts",
                "--tags", "auth,null",
            )
            self.assertEqual(first["action"], "created")
            updated = _run_add(
                tmp,
                "--track", "bug",
                "--category", "runtime-errors",
                "--title", "Null deref auth middleware",
                "--module", "src/auth.ts",
                "--tags", "auth,middleware",
                "--update", first["entry_id"],
                "--body-file", "-",
                input_bytes=b"Follow-up notes from re-run.\n",
            )
            self.assertEqual(updated["action"], "updated")
            self.assertEqual(updated["path"], first["path"])
            self.assertEqual(updated["entry_id"], first["entry_id"])
            # Matches still emitted as retrieval signal on --update.
            self.assertEqual(updated["overlap_level"], "high")
            self.assertEqual(len(updated["matches"]), 1)
            self.assertEqual(updated["matches"][0]["id"], first["entry_id"])
            fm = flowctl.parse_memory_frontmatter(Path(updated["path"]))
            self.assertIn("last_updated", fm)
            tags = [str(t).lower() for t in (fm.get("tags") or [])]
            self.assertIn("middleware", tags)
            self.assertIn("auth", tags)
            body = Path(updated["path"]).read_text(encoding="utf-8")
            self.assertIn("Follow-up notes from re-run.", body)
            self.assertIn("## Update ", body)
            # Still only one file (no silent create alongside --update).
            cat = tmp / ".flow" / "memory" / "bug" / "runtime-errors"
            md_files = [p for p in cat.iterdir() if p.suffix == ".md"]
            self.assertEqual(len(md_files), 1)

    def test_update_unknown_id_exits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _init_repo(tmp)
            out = _run_add(
                tmp,
                "--track", "bug",
                "--category", "runtime-errors",
                "--title", "x",
                "--update", "bug/runtime-errors/does-not-exist-2026-01-01",
                expect_rc=1,
            )
            combined = (out.get("_stdout") or "") + (out.get("_stderr") or "")
            self.assertIn("not found", combined.lower())

    def test_update_rejects_cross_bucket_id(self) -> None:
        """--update must not mutate an entry outside the requested track/category."""
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _init_repo(tmp)
            first = _run_add(
                tmp,
                "--track", "bug",
                "--category", "runtime-errors",
                "--title", "Cross bucket seed",
            )
            out = _run_add(
                tmp,
                "--track", "bug",
                "--category", "build-errors",
                "--title", "Cross bucket attempt",
                "--update", first["entry_id"],
                expect_rc=1,
            )
            combined = (out.get("_stdout") or "") + (out.get("_stderr") or "")
            self.assertIn("not the requested", combined)

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
            self.assertEqual(len(second["matches"]), 1)
            self.assertEqual(second["matches"][0]["id"], first["entry_id"])
            self.assertEqual(second["matches"][0]["score"], 2)

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
            self.assertEqual(data["matches"], [])

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


# --- list ---


class TestMemoryList(unittest.TestCase):
    def test_list_groups_by_category(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            with _chdir(Path(tmp)):
                data = _run(Path(tmp), "memory", "list")
            # Active filter by default — stale entry excluded.
            ids = [e["entry_id"] for e in data["entries"]]
            self.assertIn(
                "bug/runtime-errors/null-deref-in-auth-2026-05-01", ids
            )
            self.assertIn(
                "knowledge/conventions/prefer-satisfies-2026-05-02", ids
            )
            self.assertNotIn(
                "knowledge/conventions/stale-rule-2026-01-01", ids
            )
            legacy_names = [l["filename"] for l in data["legacy"]]
            self.assertIn("pitfalls.md", legacy_names)

    def test_list_filter_track(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(Path(tmp), "memory", "list", "--track", "bug")
            tracks = {e["track"] for e in data["entries"]}
            self.assertEqual(tracks, {"bug"})
            # Legacy is suppressed when a track filter is passed.
            self.assertEqual(data["legacy"], [])

    def test_list_filter_category(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(
                Path(tmp),
                "memory",
                "list",
                "--track",
                "bug",
                "--category",
                "runtime-errors",
            )
            cats = {e["category"] for e in data["entries"]}
            self.assertEqual(cats, {"runtime-errors"})

    def test_list_status_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(Path(tmp), "memory", "list", "--status", "stale")
            ids = [e["entry_id"] for e in data["entries"]]
            self.assertIn("knowledge/conventions/stale-rule-2026-01-01", ids)
            self.assertTrue(all(e["status"] == "stale" for e in data["entries"]))

    def test_list_status_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(Path(tmp), "memory", "list", "--status", "all")
            statuses = {e["status"] for e in data["entries"]}
            self.assertIn("stale", statuses)
            self.assertIn("active", statuses)

    def test_list_invalid_category(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            out = _run(
                Path(tmp),
                "memory",
                "list",
                "--track",
                "bug",
                "--category",
                "nonsense",
                expect_rc=1,
            )
            self.assertIn("invalid --category", out["_stdout"] + out["_stderr"])


# --- read ---


class TestMemoryRead(unittest.TestCase):
    def test_read_full_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(
                Path(tmp),
                "memory",
                "read",
                "bug/runtime-errors/null-deref-in-auth-2026-05-01",
            )
            self.assertEqual(
                data["entry_id"],
                "bug/runtime-errors/null-deref-in-auth-2026-05-01",
            )
            self.assertEqual(data["frontmatter"]["track"], "bug")

    def test_read_slug_plus_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(
                Path(tmp),
                "memory",
                "read",
                "null-deref-in-auth-2026-05-01",
            )
            self.assertTrue(data["entry_id"].endswith("null-deref-in-auth-2026-05-01"))

    def test_read_slug_latest_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(Path(tmp), "memory", "read", "null-deref-in-auth")
            # Two entries share the slug; 2026-06-01 is newer.
            self.assertTrue(data["entry_id"].endswith("2026-06-01"))

    def test_read_legacy_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(Path(tmp), "memory", "read", "legacy/pitfalls")
            self.assertTrue(data["legacy"])
            self.assertIn("null deref", data["body"])

    def test_read_legacy_entry_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(Path(tmp), "memory", "read", "legacy/pitfalls#2")
            self.assertEqual(data["index"], 2)
            self.assertIn("caching", data["body"])

    def test_read_unknown_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            out = _run(
                Path(tmp), "memory", "read", "does-not-exist", expect_rc=1
            )
            self.assertIn("not found", out["_stdout"] + out["_stderr"])


# --- search ---


class TestMemorySearch(unittest.TestCase):
    def test_search_ranks_by_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(
                Path(tmp),
                "memory",
                "search",
                "null deref auth",
            )
            self.assertGreater(len(data["matches"]), 0)
            top = data["matches"][0]
            self.assertTrue(top["entry_id"].startswith("bug/runtime-errors/"))
            self.assertGreater(top["score"], 0)

    def test_search_covers_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(Path(tmp), "memory", "search", "caching")
            ids = [m["entry_id"] for m in data["matches"]]
            # Only legacy file mentions "caching".
            self.assertTrue(
                any(mid.startswith("legacy/") for mid in ids),
                f"expected legacy match, got {ids}",
            )

    def test_search_track_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(
                Path(tmp),
                "memory",
                "search",
                "null deref",
                "--track",
                "knowledge",
            )
            # No knowledge entries mention null deref → zero matches.
            self.assertEqual(data["matches"], [])

    def test_search_module_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(
                Path(tmp),
                "memory",
                "search",
                "null deref",
                "--module",
                "src/auth.ts",
            )
            self.assertTrue(data["matches"])
            self.assertTrue(
                all(m["module"] == "src/auth.ts" for m in data["matches"])
            )

    def test_search_tag_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(
                Path(tmp),
                "memory",
                "search",
                "null deref",
                "--tags",
                "null",
            )
            self.assertTrue(data["matches"])

    def test_search_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            data = _run(
                Path(tmp),
                "memory",
                "search",
                "null deref auth",
                "--limit",
                "1",
            )
            self.assertEqual(len(data["matches"]), 1)

    def test_search_empty_query_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_entries(mem)
            out = _run(Path(tmp), "memory", "search", "   ", expect_rc=1)
            self.assertIn("empty", out["_stdout"] + out["_stderr"])


# --- direct resolver unit tests (no subprocess) ---


class TestResolveReadTarget(unittest.TestCase):
    def test_resolve_full_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp) / "memory"
            _seed_entries(mem)
            r = flowctl._memory_resolve_read_target(
                mem, "bug/runtime-errors/null-deref-in-auth-2026-05-01"
            )
            self.assertIsNotNone(r)
            self.assertEqual(r["kind"], "categorized")

    def test_resolve_slug_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp) / "memory"
            _seed_entries(mem)
            r = flowctl._memory_resolve_read_target(mem, "null-deref-in-auth")
            self.assertEqual(r["kind"], "categorized")
            self.assertEqual(r["entry"]["date"], "2026-06-01")

    def test_resolve_legacy_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp) / "memory"
            _seed_entries(mem)
            r = flowctl._memory_resolve_read_target(mem, "legacy/pitfalls")
            self.assertEqual(r["kind"], "legacy_file")

    def test_resolve_legacy_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp) / "memory"
            _seed_entries(mem)
            r = flowctl._memory_resolve_read_target(mem, "legacy/pitfalls#1")
            self.assertEqual(r["kind"], "legacy_entry")
            self.assertEqual(r["index"], 1)

    def test_resolve_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp) / "memory"
            _seed_entries(mem)
            r = flowctl._memory_resolve_read_target(mem, "no-such-entry")
            self.assertIsNone(r)


class TestIterEntries(unittest.TestCase):
    def test_iter_filter_track(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp) / "memory"
            _seed_entries(mem)
            entries = flowctl._memory_iter_entries(mem, track="bug")
            self.assertTrue(entries)
            self.assertTrue(all(e["track"] == "bug" for e in entries))

    def test_iter_filter_category(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp) / "memory"
            _seed_entries(mem)
            entries = flowctl._memory_iter_entries(
                mem, track="bug", category="runtime-errors"
            )
            self.assertTrue(entries)
            self.assertTrue(
                all(e["category"] == "runtime-errors" for e in entries)
            )


class TestSearchScoring(unittest.TestCase):
    def test_title_weights_higher_than_body(self) -> None:
        q = ["webpack"]
        title_hit = {"title": ["webpack"], "tags": [], "body": [], "misc": []}
        body_hit = {"title": [], "tags": [], "body": ["webpack"], "misc": []}
        self.assertGreater(
            flowctl._memory_score_search(q, title_hit),
            flowctl._memory_score_search(q, body_hit),
        )

    def test_tags_weight_higher_than_body(self) -> None:
        q = ["webpack"]
        tag_hit = {"title": [], "tags": ["webpack"], "body": [], "misc": []}
        body_hit = {"title": [], "tags": [], "body": ["webpack"], "misc": []}
        self.assertGreater(
            flowctl._memory_score_search(q, tag_hit),
            flowctl._memory_score_search(q, body_hit),
        )

    def test_zero_when_no_overlap(self) -> None:
        self.assertEqual(
            flowctl._memory_score_search(
                ["foo"],
                {"title": ["bar"], "tags": [], "body": [], "misc": []},
            ),
            0.0,
        )


# --- search --status (fn-34 task 2) ---


class TestMemorySearchStatus(unittest.TestCase):
    def test_default_active_excludes_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_webpack_entries(mem)
            data = _run(Path(tmp), "memory", "search", "webpack")
            ids = _categorized_ids(data["matches"])
            self.assertIn("bug/build-errors/webpack-oom-2026-04-01", ids)
            self.assertIn("bug/build-errors/webpack-cache-2026-04-15", ids)
            self.assertNotIn("bug/build-errors/webpack-old-2026-01-01", ids)

    def test_status_stale_returns_only_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mem = _init_repo(Path(tmp))
            _seed_webpack_entries(mem)
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
            _seed_webpack_entries(mem)
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
            _seed_webpack_entries(mem)
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
            _seed_webpack_entries(mem)
            data = _run(Path(tmp), "memory", "list", "--status", "stale")
            ids = {e["entry_id"] for e in data["entries"]}
            self.assertEqual(
                ids, {"bug/build-errors/webpack-old-2026-01-01"}
            )


# --- list-legacy (fn-35.2) ---


class TestMemoryListLegacy(unittest.TestCase):
    """`flowctl memory list-legacy` — text + JSON shape contract."""

    def test_empty_repo_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _init_repo(tmp_path, git=True)
            rc, out, err = _run_raw(tmp_path, "memory", "list-legacy")
            self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
            self.assertIn("No legacy files found", out)

    def test_empty_repo_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _init_repo(tmp_path, git=True)
            rc, out, err = _run_raw(tmp_path, "memory", "list-legacy", "--json")
            self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
            data = json.loads(out)
            self.assertTrue(data["success"])
            self.assertEqual(data["files"], [])

    def test_two_entries_in_pitfalls_json(self) -> None:
        """Pitfalls with two entries → entry_count=2, mechanical defaults bug/build-errors."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mem = _init_repo(tmp_path, git=True)
            (mem / "pitfalls.md").write_text(
                "# Pitfalls\n\n"
                "## 2026-03-01 Race condition\n"
                "Worker race during shutdown.\n\n"
                "---\n\n"
                "## 2026-03-15 Null crash\n"
                "Crash on empty payload.\n",
                encoding="utf-8",
            )
            rc, out, err = _run_raw(tmp_path, "memory", "list-legacy", "--json")
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
            mem = _init_repo(tmp_path, git=True)
            (mem / "conventions.md").write_text(
                "# Conventions\n\n## Use pnpm\nProject standard.\n",
                encoding="utf-8",
            )
            rc, out, err = _run_raw(tmp_path, "memory", "list-legacy")
            self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
            self.assertIn("conventions.md", out)
            self.assertIn("1 entry", out)
            # Default label visible to humans.
            self.assertIn("knowledge/conventions", out)

    def test_multiple_legacy_files_separate_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mem = _init_repo(tmp_path, git=True)
            (mem / "pitfalls.md").write_text(
                "# Pitfalls\n\n## 2026-03-01 Race\nx.\n", encoding="utf-8"
            )
            (mem / "decisions.md").write_text(
                "# Decisions\n\n## 2026-02-01 Postgres\ny.\n", encoding="utf-8"
            )
            rc, out, err = _run_raw(tmp_path, "memory", "list-legacy", "--json")
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
            mem = _init_repo(tmp_path, git=True)
            (mem / "pitfalls.md").write_text(
                "# Pitfalls\n\n## 2026-03-01 Race\nx.\n", encoding="utf-8"
            )
            rc, out, err = _run_raw(
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
            mem = _init_repo(tmp_path, git=True)
            (mem / "pitfalls.md").write_text(
                "# Pitfalls\n\n## 2026-03-01 Race\nx.\n", encoding="utf-8"
            )
            rc, out, err = _run_raw(
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
            mem = _init_repo(tmp_path, git=True)
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
