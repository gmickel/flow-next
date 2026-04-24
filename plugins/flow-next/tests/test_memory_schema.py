"""Unit tests for memory schema + frontmatter helpers (fn-30 task 1).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers the AC of task 1:
  - AC2: category enum shapes
  - AC3: inline YAML parser reads valid frontmatter, rejects malformed
  - AC4: validate_memory_frontmatter returns errors for required/enum/unknown
  - AC7: PyYAML is optional (tests run whether or not it's installed)
  - AC8: frontmatter round-trip (write -> parse -> equality)
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from typing import Any


def _load_flowctl() -> Any:
    here = Path(__file__).resolve()
    flowctl_path = here.parent.parent / "scripts" / "flowctl.py"
    if not flowctl_path.is_file():
        raise RuntimeError(f"flowctl.py not found at {flowctl_path}")
    spec = importlib.util.spec_from_file_location("flowctl_memory_under_test", flowctl_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


# --- Schema constants ---


class TestMemorySchemaConstants(unittest.TestCase):
    """AC2: category enums are defined and have the expected shape."""

    def test_tracks(self) -> None:
        self.assertEqual(flowctl.MEMORY_TRACKS, ("bug", "knowledge"))

    def test_bug_categories_count(self) -> None:
        self.assertEqual(len(flowctl.MEMORY_CATEGORIES["bug"]), 8)

    def test_knowledge_categories_count(self) -> None:
        self.assertEqual(len(flowctl.MEMORY_CATEGORIES["knowledge"]), 5)

    def test_bug_categories_content(self) -> None:
        self.assertIn("build-errors", flowctl.MEMORY_CATEGORIES["bug"])
        self.assertIn("test-failures", flowctl.MEMORY_CATEGORIES["bug"])
        self.assertIn("ui", flowctl.MEMORY_CATEGORIES["bug"])

    def test_knowledge_categories_content(self) -> None:
        self.assertIn("conventions", flowctl.MEMORY_CATEGORIES["knowledge"])
        self.assertIn("tooling-decisions", flowctl.MEMORY_CATEGORIES["knowledge"])
        self.assertIn("best-practices", flowctl.MEMORY_CATEGORIES["knowledge"])

    def test_required_fields(self) -> None:
        self.assertEqual(
            flowctl.MEMORY_REQUIRED_FIELDS,
            frozenset({"title", "date", "track", "category"}),
        )

    def test_bug_track_fields(self) -> None:
        self.assertEqual(
            flowctl.MEMORY_BUG_FIELDS,
            frozenset({"problem_type", "symptoms", "root_cause", "resolution_type"}),
        )

    def test_knowledge_track_fields(self) -> None:
        self.assertEqual(
            flowctl.MEMORY_KNOWLEDGE_FIELDS, frozenset({"applies_when"})
        )

    def test_enums_nonempty(self) -> None:
        self.assertTrue(len(flowctl.MEMORY_PROBLEM_TYPES) > 0)
        self.assertTrue(len(flowctl.MEMORY_RESOLUTION_TYPES) > 0)
        self.assertEqual(flowctl.MEMORY_STATUS, ("active", "stale"))


# --- Inline YAML parser ---


class TestInlineYAMLParser(unittest.TestCase):
    """AC3: parser reads valid, returns {} on malformed."""

    def test_parse_simple_scalars(self) -> None:
        text = "title: hello\ndate: 2026-04-24\ntrack: bug\n"
        result = flowctl._parse_inline_yaml(text)
        self.assertEqual(result["title"], "hello")
        self.assertEqual(result["date"], "2026-04-24")
        self.assertEqual(result["track"], "bug")

    def test_parse_inline_list(self) -> None:
        text = "tags: [alpha, beta, gamma]\n"
        result = flowctl._parse_inline_yaml(text)
        self.assertEqual(result["tags"], ["alpha", "beta", "gamma"])

    def test_parse_empty_list(self) -> None:
        text = "tags: []\n"
        result = flowctl._parse_inline_yaml(text)
        self.assertEqual(result["tags"], [])

    def test_parse_quoted_scalar(self) -> None:
        text = 'title: "hello world"\n'
        result = flowctl._parse_inline_yaml(text)
        self.assertEqual(result["title"], "hello world")

    def test_parse_single_quoted(self) -> None:
        text = "title: 'single quote'\n"
        result = flowctl._parse_inline_yaml(text)
        self.assertEqual(result["title"], "single quote")

    def test_parse_blank_and_comment_lines(self) -> None:
        text = "\n# comment line\ntitle: hello\n\n"
        result = flowctl._parse_inline_yaml(text)
        self.assertEqual(result, {"title": "hello"})

    def test_parse_malformed_returns_empty(self) -> None:
        # No colon on a non-blank line => malformed.
        text = "title: hello\nno-colon-here\n"
        result = flowctl._parse_inline_yaml(text)
        self.assertEqual(result, {})

    def test_parse_empty_key_rejected(self) -> None:
        text = ": value-without-key\n"
        result = flowctl._parse_inline_yaml(text)
        self.assertEqual(result, {})


class TestParseMemoryFrontmatter(unittest.TestCase):
    """File-level frontmatter parser (handles delimiters + PyYAML fallback)."""

    def test_missing_file_returns_empty(self) -> None:
        self.assertEqual(
            flowctl.parse_memory_frontmatter(Path("/nonexistent/path.md")), {}
        )

    def test_no_frontmatter_returns_empty(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("# Just a heading\n\nNo frontmatter.\n")
            path = Path(f.name)
        try:
            self.assertEqual(flowctl.parse_memory_frontmatter(path), {})
        finally:
            path.unlink()

    def test_partial_delimiter_returns_empty(self) -> None:
        # Only one --- line; no closing delimiter.
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("---\ntitle: hello\n")
            path = Path(f.name)
        try:
            self.assertEqual(flowctl.parse_memory_frontmatter(path), {})
        finally:
            path.unlink()

    def test_parses_valid_frontmatter(self) -> None:
        # Writer quotes date fields; parser preserves them as strings.
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(
                "---\n"
                "title: hello\n"
                'date: "2026-04-24"\n'
                "track: bug\n"
                "category: build-errors\n"
                "tags: [a, b]\n"
                "---\n"
                "\n"
                "Body goes here.\n"
            )
            path = Path(f.name)
        try:
            result = flowctl.parse_memory_frontmatter(path)
            self.assertEqual(result["title"], "hello")
            self.assertEqual(result["date"], "2026-04-24")
            self.assertEqual(result["track"], "bug")
            self.assertEqual(result["category"], "build-errors")
            self.assertEqual(result["tags"], ["a", "b"])
        finally:
            path.unlink()


# --- Validator ---


def _valid_bug_frontmatter() -> dict[str, Any]:
    return {
        "title": "oom in build step",
        "date": "2026-04-24",
        "track": "bug",
        "category": "build-errors",
        "problem_type": "build-error",
        "symptoms": "memory spikes",
        "root_cause": "webpack bundling",
        "resolution_type": "fix",
    }


def _valid_knowledge_frontmatter() -> dict[str, Any]:
    return {
        "title": "prefer pnpm over npm",
        "date": "2026-04-24",
        "track": "knowledge",
        "category": "tooling-decisions",
        "applies_when": "choosing package manager",
    }


class TestValidateFrontmatter(unittest.TestCase):
    """AC4: validator flags missing, unknown, enum violations."""

    def test_valid_bug(self) -> None:
        self.assertEqual(
            flowctl.validate_memory_frontmatter(_valid_bug_frontmatter()), []
        )

    def test_valid_knowledge(self) -> None:
        self.assertEqual(
            flowctl.validate_memory_frontmatter(_valid_knowledge_frontmatter()),
            [],
        )

    def test_missing_required_field(self) -> None:
        fm = _valid_bug_frontmatter()
        del fm["title"]
        errors = flowctl.validate_memory_frontmatter(fm)
        self.assertTrue(any("missing required fields" in e for e in errors))
        self.assertTrue(any("title" in e for e in errors))

    def test_missing_track_specific_bug_field(self) -> None:
        fm = _valid_bug_frontmatter()
        del fm["problem_type"]
        errors = flowctl.validate_memory_frontmatter(fm)
        self.assertTrue(any("bug-track fields" in e for e in errors))

    def test_missing_track_specific_knowledge_field(self) -> None:
        fm = _valid_knowledge_frontmatter()
        del fm["applies_when"]
        errors = flowctl.validate_memory_frontmatter(fm)
        self.assertTrue(any("knowledge-track fields" in e for e in errors))

    def test_invalid_track(self) -> None:
        fm = _valid_bug_frontmatter()
        fm["track"] = "nonsense"
        errors = flowctl.validate_memory_frontmatter(fm)
        self.assertTrue(any("invalid track" in e for e in errors))

    def test_invalid_category_for_track(self) -> None:
        fm = _valid_bug_frontmatter()
        # conventions is a knowledge category, not bug.
        fm["category"] = "conventions"
        errors = flowctl.validate_memory_frontmatter(fm)
        self.assertTrue(any("invalid category" in e for e in errors))

    def test_unknown_field_rejected(self) -> None:
        fm = _valid_bug_frontmatter()
        fm["sekrit_field"] = "oops"
        errors = flowctl.validate_memory_frontmatter(fm)
        self.assertTrue(any("unknown fields" in e for e in errors))
        self.assertTrue(any("sekrit_field" in e for e in errors))

    def test_invalid_problem_type(self) -> None:
        fm = _valid_bug_frontmatter()
        fm["problem_type"] = "wat"
        errors = flowctl.validate_memory_frontmatter(fm)
        self.assertTrue(any("invalid problem_type" in e for e in errors))

    def test_invalid_resolution_type(self) -> None:
        fm = _valid_bug_frontmatter()
        fm["resolution_type"] = "magic"
        errors = flowctl.validate_memory_frontmatter(fm)
        self.assertTrue(any("invalid resolution_type" in e for e in errors))

    def test_invalid_status(self) -> None:
        fm = _valid_knowledge_frontmatter()
        fm["status"] = "sleepy"
        errors = flowctl.validate_memory_frontmatter(fm)
        self.assertTrue(any("invalid status" in e for e in errors))

    def test_optional_fields_accepted(self) -> None:
        fm = _valid_knowledge_frontmatter()
        fm["module"] = "billing"
        fm["tags"] = ["a", "b"]
        fm["status"] = "active"
        fm["last_updated"] = "2026-04-24"
        fm["related_to"] = ["knowledge/conventions/foo-2026-01-01"]
        errors = flowctl.validate_memory_frontmatter(fm)
        self.assertEqual(errors, [])

    def test_non_dict_rejected(self) -> None:
        errors = flowctl.validate_memory_frontmatter("a string")  # type: ignore[arg-type]
        self.assertTrue(any("must be a dict" in e for e in errors))


# --- Round-trip ---


class TestFrontmatterRoundTrip(unittest.TestCase):
    """AC8: write -> parse -> equality, deterministic field order."""

    def _round_trip(self, fm: dict[str, Any]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "entry.md"
            flowctl.write_memory_entry(path, fm, "Body content.\n")
            return flowctl.parse_memory_frontmatter(path)

    def test_round_trip_bug(self) -> None:
        fm = _valid_bug_frontmatter()
        fm["module"] = "src/build.ts"
        fm["tags"] = ["webpack", "oom"]
        parsed = self._round_trip(fm)
        # Parsed may include same keys with same values.
        for key, value in fm.items():
            self.assertEqual(parsed.get(key), value, f"mismatch on {key}")

    def test_round_trip_knowledge(self) -> None:
        fm = _valid_knowledge_frontmatter()
        fm["tags"] = ["pnpm", "tooling"]
        parsed = self._round_trip(fm)
        for key, value in fm.items():
            self.assertEqual(parsed.get(key), value, f"mismatch on {key}")

    def test_write_rejects_invalid(self) -> None:
        fm = _valid_bug_frontmatter()
        del fm["problem_type"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "entry.md"
            with self.assertRaises(ValueError):
                flowctl.write_memory_entry(path, fm, "body")

    def test_deterministic_field_order(self) -> None:
        """title comes before date, date before track — MEMORY_FIELD_ORDER."""
        fm = _valid_bug_frontmatter()
        fm["module"] = "x"
        fm["tags"] = ["a"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "entry.md"
            flowctl.write_memory_entry(path, fm, "body")
            text = path.read_text(encoding="utf-8")
        # Find line positions for known fields.
        lines = text.splitlines()
        indices: dict[str, int] = {}
        for idx, line in enumerate(lines):
            for key in (
                "title",
                "date",
                "track",
                "category",
                "module",
                "tags",
                "problem_type",
            ):
                if line.startswith(f"{key}:"):
                    indices[key] = idx
                    break
        self.assertLess(indices["title"], indices["date"])
        self.assertLess(indices["date"], indices["track"])
        self.assertLess(indices["track"], indices["category"])
        self.assertLess(indices["category"], indices["module"])
        self.assertLess(indices["module"], indices["tags"])
        self.assertLess(indices["tags"], indices["problem_type"])


if __name__ == "__main__":
    unittest.main()
