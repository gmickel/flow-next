"""Unit tests for `flowctl memory list / read / search` (fn-30 task 3).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers acceptance criteria from the task spec:
  - AC1: list walks the tree and groups by category.
  - AC2: --track filter narrows track.
  - AC3: --category filter narrows category.
  - AC4: --status stale returns stale-only entries.
  - AC5: read accepts full id, slug+date, and slug-only forms.
  - AC6: search returns relevance-ranked results across tracks.
  - AC7: search covers legacy flat files.
  - AC8: --json schemas match.
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
        "flowctl_listreadsearch_under_test", FLOWCTL_PY
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


if __name__ == "__main__":
    unittest.main()
