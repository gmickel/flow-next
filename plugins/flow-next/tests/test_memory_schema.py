"""Unit tests for the memory schema, YAML quoting, and read budgets.

Consolidates the former micro-suites (zero assertion loss):
  - test_memory_schema.py       — schema + frontmatter helpers (fn-30 task 1)
  - test_memory_yaml_quoting.py — YAML quoting + silent-drop warning (issue #235)
  - test_memory_performance.py  — deterministic read budgets + direct-ID
    safety (fn-122.8)

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers (schema — fn-30 task 1):
  - AC2: category enum shapes
  - AC3: inline YAML parser reads valid frontmatter, rejects malformed
  - AC4: validate_memory_frontmatter returns errors for required/enum/unknown
  - AC7: PyYAML is optional (tests run whether or not it's installed)
  - AC8: frontmatter round-trip (write -> parse -> equality)

Covers (YAML quoting — issue #235):
  - memory add titles starting with ', ", -  round-trip via frontmatter
  - _yaml_scalar_needs_quoting unit assertions for the new gates
  - inline-parser round-trip of quoted escapes (embedded double quotes)
  - malformed entry skip emits stderr warning

Covers (read budgets — fn-122.8 evidence):
  On the 24-entry fixture, pre-change exact-ID resolution performed 48 entry
  reads (the full corpus, twice per entry); it now performs one validated
  target read. Metadata/search enumeration moves from 2N to N entry reads.
  Same live-repo ``memory list --status all --json`` benchmark, five runs on
  2026-07-21: pre median 0.19 s (0.19-0.20), post 0.19 s (0.19-0.19), so
  startup-dominated wall time is stable while I/O halves.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from contextlib import contextmanager, redirect_stderr
from pathlib import Path
from typing import Any
from unittest import mock

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import flowctl  # noqa: E402  (path-injected import)


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


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


def _run_add(cwd: Path, *args: str) -> dict[str, Any]:
    cmd = [sys.executable, str(FLOWCTL_PY), "memory", "add", *args, "--json"]
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "FLOW_NO_DEPRECATION": "1"},
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"add unexpected rc={proc.returncode}: "
            f"stdout={proc.stdout.decode()} stderr={proc.stderr.decode()}"
        )
    return json.loads(proc.stdout.decode())


def _run_list(cwd: Path) -> dict[str, Any]:
    cmd = [sys.executable, str(FLOWCTL_PY), "memory", "list", "--json"]
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "FLOW_NO_DEPRECATION": "1"},
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"list unexpected rc={proc.returncode}: "
            f"stdout={proc.stdout.decode()} stderr={proc.stderr.decode()}"
        )
    return json.loads(proc.stdout.decode())


# --- Schema constants ---


class TestMemorySchemaConstants(unittest.TestCase):
    """AC2: category enums are defined and have the expected shape."""

    def test_tracks(self) -> None:
        self.assertEqual(flowctl.MEMORY_TRACKS, ("bug", "knowledge"))

    def test_bug_categories_count(self) -> None:
        self.assertEqual(len(flowctl.MEMORY_CATEGORIES["bug"]), 8)

    def test_knowledge_categories_count(self) -> None:
        # 6 knowledge categories since 0.39.0 (added "decisions" per
        # plugins/flow-next/docs/teams.md decision-records discussion).
        self.assertEqual(len(flowctl.MEMORY_CATEGORIES["knowledge"]), 6)

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
        self.assertEqual(flowctl.MEMORY_STATUS, ("active", "stale", "hardened"))


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

    def test_audit_fields_accepted(self) -> None:
        """fn-34: last_audited + audit_notes validate without raising."""
        fm = _valid_knowledge_frontmatter()
        fm["status"] = "stale"
        fm["last_audited"] = "2026-04-25"
        fm["audit_notes"] = "module renamed in PR #42"
        errors = flowctl.validate_memory_frontmatter(fm)
        self.assertEqual(errors, [])

    def test_audit_fields_in_optional_set(self) -> None:
        """fn-34: schema constants include the two new audit fields."""
        self.assertIn("last_audited", flowctl.MEMORY_OPTIONAL_FIELDS)
        self.assertIn("audit_notes", flowctl.MEMORY_OPTIONAL_FIELDS)
        # Field order: last_audited / audit_notes appear before related_to.
        order = flowctl.MEMORY_FIELD_ORDER
        self.assertIn("last_audited", order)
        self.assertIn("audit_notes", order)
        self.assertLess(order.index("last_audited"), order.index("related_to"))
        self.assertLess(order.index("audit_notes"), order.index("related_to"))
        # last_audited is in the quoted-string set so PyYAML doesn't coerce it.
        self.assertIn("last_audited", flowctl._MEMORY_QUOTED_STRING_FIELDS)

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

    def test_round_trip_audit_fields(self) -> None:
        """fn-34: last_audited stays a string after round-trip (not date)."""
        fm = _valid_bug_frontmatter()
        fm["status"] = "stale"
        fm["last_audited"] = "2026-04-25"
        fm["audit_notes"] = "module path moved"
        parsed = self._round_trip(fm)
        self.assertEqual(parsed["last_audited"], "2026-04-25")
        self.assertEqual(parsed["audit_notes"], "module path moved")
        self.assertEqual(parsed["status"], "stale")

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


# --- YAML quoting + silent-drop warning (issue #235) ---


class TestYamlScalarNeedsQuoting(unittest.TestCase):
    """Unit assertions for the quoting gate (issue #235 bug 1)."""

    def test_needs_quoting_true_cases(self) -> None:
        for text in ("'x", '"x', "- x", "-", "? x", " leading", "trailing "):
            with self.subTest(text=repr(text)):
                self.assertTrue(
                    flowctl._yaml_scalar_needs_quoting(text),
                    f"expected quoting for {text!r}",
                )

    def test_needs_quoting_false_cases(self) -> None:
        for text in ("normal title", "-dash-no-space", "?question"):
            with self.subTest(text=repr(text)):
                self.assertFalse(
                    flowctl._yaml_scalar_needs_quoting(text),
                    f"unexpected quoting for {text!r}",
                )

    def test_mid_string_comment_hash_needs_quoting(self) -> None:
        # Whitespace-then-# opens a YAML comment on read (issue #332).
        for text in ("landed in #140", "tab\t#140", "a # b"):
            with self.subTest(text=repr(text)):
                self.assertTrue(
                    flowctl._yaml_scalar_needs_quoting(text),
                    f"expected quoting for {text!r}",
                )

    def test_non_comment_hash_stays_unquoted(self) -> None:
        for text in ("C#/F# langs", "issue#140", "sharp# end"):
            with self.subTest(text=repr(text)):
                self.assertFalse(
                    flowctl._yaml_scalar_needs_quoting(text),
                    f"unexpected quoting for {text!r}",
                )


def _pyyaml_available() -> bool:
    try:
        import yaml  # noqa: F401
    except ImportError:
        return False
    return True


class TestCommentHashRoundTrip(unittest.TestCase):
    """A mid-string ' #' value survives both readers (issue #332 cause a)."""

    VALUE = "A title — the resync itself landed in #140"

    @unittest.skipUnless(_pyyaml_available(), "PyYAML not installed")
    def test_conforming_parser_round_trip(self) -> None:
        import yaml

        rendered = flowctl._format_yaml_value(self.VALUE, key="title")
        parsed = yaml.safe_load(f"title: {rendered}\n")
        self.assertEqual(parsed["title"], self.VALUE)

    def test_inline_parser_round_trip(self) -> None:
        rendered = flowctl._format_yaml_value(self.VALUE, key="title")
        self.assertTrue(rendered.startswith('"') and rendered.endswith('"'))
        parsed = flowctl._parse_inline_yaml(f"title: {rendered}\n")
        self.assertEqual(parsed.get("title"), self.VALUE)


class TestFlowListSplitQuoteAware(unittest.TestCase):
    """Flow-list splitting is quote/depth aware (issue #332 cause b)."""

    def test_reporter_two_element_list(self) -> None:
        first = "Own it separately — rejected by the operator, who chose otherwise."
        second = "Record it as a dep — rejected: it would misstate a priority."
        text = f'alternatives_considered: ["{first}", "{second}"]\n'
        parsed = flowctl._parse_inline_yaml(text)
        self.assertEqual(parsed["alternatives_considered"], [first, second])

    def test_list_with_commas_quotes_and_colons_round_trip(self) -> None:
        tags = ["a, b", 'say "hi", now', "key: value", "plain"]
        rendered = flowctl._format_yaml_value(tags, key="tags")
        parsed = flowctl._parse_inline_yaml(f"tags: {rendered}\n")
        self.assertEqual(parsed.get("tags"), tags)

    def test_apostrophe_item_not_treated_as_quote(self) -> None:
        text = "tags: [don't worry, ok]\n"
        parsed = flowctl._parse_inline_yaml(text)
        self.assertEqual(parsed["tags"], ["don't worry", "ok"])

    def test_split_helper_depth_and_escapes(self) -> None:
        self.assertEqual(
            flowctl._split_flow_items('"a\\", b", [c, d], e'),
            ['"a\\", b"', " [c, d]", " e"],
        )

    def test_quoted_mapping_value_with_comma(self) -> None:
        # A quote after a mapping key separator opens a quoted value.
        parsed = flowctl._parse_inline_yaml(
            'promoted_to: {"1": "alpha, beta", "2": ok}\n'
        )
        self.assertEqual(
            parsed["promoted_to"], {"1": "alpha, beta", "2": "ok"}
        )

    def test_quoted_mapping_value_unescapes(self) -> None:
        # Double-quoted mapping keys/values/list-items are unescaped,
        # matching the top-level scalar and list branches.
        parsed = flowctl._parse_inline_yaml(
            'promoted_to: {"1": "say \\"hi\\", now", "2": ["a\\"b", c]}\n'
        )
        self.assertEqual(
            parsed["promoted_to"],
            {"1": 'say "hi", now', "2": ['a"b', "c"]},
        )


class TestInlineParserRoundTrip(unittest.TestCase):
    """_format_yaml_value → _parse_inline_yaml preserves escapes (bug 1b)."""

    def test_embedded_double_quotes_round_trip(self) -> None:
        title = 'say "hello", world'
        rendered = flowctl._format_yaml_value(title, key="title")
        # Must be quoted with escapes so the inline parser can recover.
        self.assertTrue(rendered.startswith('"') and rendered.endswith('"'))
        fm_text = f"title: {rendered}\n"
        parsed = flowctl._parse_inline_yaml(fm_text)
        self.assertEqual(parsed.get("title"), title)

    def test_leading_quote_chars_round_trip(self) -> None:
        for title in ("'leading single", '"leading double', "- leading dash"):
            with self.subTest(title=title):
                rendered = flowctl._format_yaml_value(title, key="title")
                parsed = flowctl._parse_inline_yaml(f"title: {rendered}\n")
                self.assertEqual(parsed.get("title"), title)

    def test_list_item_embedded_quotes_round_trip(self) -> None:
        tags = ['say "hi"', "plain"]
        rendered = flowctl._format_yaml_value(tags, key="tags")
        parsed = flowctl._parse_inline_yaml(f"tags: {rendered}\n")
        self.assertEqual(parsed.get("tags"), tags)


class TestMemoryAddLeadingSpecialTitles(unittest.TestCase):
    """memory add with titles starting ', ", -  parses and lists (bug 1 e2e)."""

    def test_titles_with_leading_specials_round_trip(self) -> None:
        cases = [
            ("'quoted single lead", "when 'foo applies"),
            ('"quoted double lead', 'when "bar applies'),
            ("- leading dash title", "- when dash applies"),
        ]
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _init_repo(tmp)
            created_ids: list[str] = []
            for title, applies_when in cases:
                with self.subTest(title=title):
                    data = _run_add(
                        tmp,
                        "--track",
                        "knowledge",
                        "--category",
                        "conventions",
                        "--title",
                        title,
                        "--applies-when",
                        applies_when,
                        "--no-overlap-check",
                    )
                    self.assertEqual(data["action"], "created")
                    path = Path(data["path"])
                    self.assertTrue(path.exists())
                    fm = flowctl.parse_memory_frontmatter(path)
                    self.assertEqual(fm.get("title"), title)
                    self.assertEqual(fm.get("applies_when"), applies_when)
                    created_ids.append(data["entry_id"])

            listed = _run_list(tmp)
            # list JSON groups entries; collect all entry ids / titles.
            listed_titles: set[str] = set()
            listed_ids: set[str] = set()
            entries = listed.get("entries") or listed.get("items") or []
            if isinstance(entries, dict):
                # Grouped-by-category form: values are lists of entry dicts.
                flat: list[Any] = []
                for v in entries.values():
                    if isinstance(v, list):
                        flat.extend(v)
                    elif isinstance(v, dict):
                        for vv in v.values():
                            if isinstance(vv, list):
                                flat.extend(vv)
                entries = flat
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                if "title" in entry:
                    listed_titles.add(str(entry["title"]))
                eid = entry.get("entry_id") or entry.get("id") or ""
                if eid:
                    listed_ids.add(str(eid))
            for title, _ in cases:
                self.assertIn(title, listed_titles, listed)
            for eid in created_ids:
                self.assertIn(eid, listed_ids, listed)


class TestMalformedEntryStderrWarning(unittest.TestCase):
    """Malformed frontmatter is skipped with a stderr warning (bug 2)."""

    def test_iter_skips_malformed_and_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            mem = Path(tmp_str) / "memory"
            cat = mem / "bug" / "runtime-errors"
            cat.mkdir(parents=True)
            # Valid companion so the walk is non-empty either way.
            flowctl.write_memory_entry(
                cat / "valid-entry-2026-05-01.md",
                {
                    "title": "Valid entry",
                    "date": "2026-05-01",
                    "track": "bug",
                    "category": "runtime-errors",
                    "tags": ["ok"],
                    "problem_type": "runtime-error",
                    "symptoms": "x",
                    "root_cause": "y",
                    "resolution_type": "fix",
                },
                "body",
            )
            bad = cat / "broken-entry-2026-05-02.md"
            # Delimiters present but body is not parseable key:value frontmatter.
            bad.write_text(
                "---\nthis is not: valid: yaml: : :\n:::\n---\nbody\n",
                encoding="utf-8",
            )

            buf = io.StringIO()
            with redirect_stderr(buf):
                entries = flowctl._memory_iter_entries(mem)
            err = buf.getvalue()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["title"], "Valid entry")
            self.assertIn("malformed frontmatter", err)
            self.assertIn(str(bad), err)
            self.assertIn("flowctl: skipping", err)


# --- Read budgets + direct-ID safety (fn-122.8) ---


class TestMemoryReadBudgets(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.memory = Path(self._tmp.name) / "memory"
        self.paths: list[Path] = []
        for index in range(24):
            path = (
                self.memory
                / "knowledge"
                / "conventions"
                / f"entry-{index:02d}-2026-07-21.md"
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            flowctl.write_memory_entry(
                path,
                {
                    "title": f"Entry {index:02d}",
                    "date": "2026-07-21",
                    "track": "knowledge",
                    "category": "conventions",
                    "applies_when": "testing read budgets",
                },
                f"Body {index:02d}.\n",
            )
            self.paths.append(path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _count_reads(self):
        """Count content reads regardless of which primitive did the read.

        `_memory_read_entry` reads through `Path.open(newline="")` — newline
        translation has to stay off so a CRLF body survives a frontmatter-only
        rewrite — while the metadata path still uses `Path.read_text`.
        Instrument both, or the budget assertions silently measure nothing.
        """
        real_read = Path.read_text
        real_open = Path.open
        counts: Counter[str] = Counter()
        # `read_text` is implemented on top of `open`; the depth guard keeps a
        # single logical read from being counted by both wrappers.
        depth: list[int] = []

        def counting_read(path, *args, **kwargs):
            counts[str(path)] += 1
            depth.append(1)
            try:
                return real_read(path, *args, **kwargs)
            finally:
                depth.pop()

        def counting_open(path, *args, **kwargs):
            mode = kwargs.get("mode", args[0] if args else "r")
            if not depth and not any(flag in mode for flag in ("w", "a", "x", "+")):
                counts[str(path)] += 1
            return real_open(path, *args, **kwargs)

        @contextmanager
        def patcher():
            with mock.patch.object(Path, "read_text", counting_read):
                with mock.patch.object(Path, "open", counting_open):
                    yield

        return patcher(), counts

    def test_metadata_and_search_iterations_read_each_entry_once(self) -> None:
        patcher, counts = self._count_reads()
        with patcher:
            metadata = flowctl._memory_iter_entries(self.memory)
        self.assertEqual(len(metadata), len(self.paths))
        self.assertTrue(all(entry["body"] == "" for entry in metadata))
        self.assertTrue(all(entry["raw"] == "" for entry in metadata))
        self.assertEqual({counts[str(path)] for path in self.paths}, {1})

        patcher, counts = self._count_reads()
        with patcher:
            searchable = flowctl._memory_iter_entries(
                self.memory, include_body=True
            )
        self.assertEqual(len(searchable), len(self.paths))
        self.assertTrue(all(entry["body"].startswith("Body") for entry in searchable))
        self.assertTrue(all(entry["raw"] == "" for entry in searchable))
        self.assertEqual({counts[str(path)] for path in self.paths}, {1})

    def test_full_id_reads_only_the_validated_target(self) -> None:
        target_id = "knowledge/conventions/entry-17-2026-07-21"
        patcher, counts = self._count_reads()
        with patcher:
            resolved = flowctl._memory_resolve_read_target(self.memory, target_id)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["entry"]["entry_id"], target_id)
        self.assertTrue(resolved["entry"]["body"].startswith("Body"))
        self.assertTrue(resolved["entry"]["raw"].startswith("---\n"))
        self.assertEqual(sum(counts.values()), 1)
        self.assertEqual(counts[str(self.paths[17])], 1)

    def test_ambiguous_slug_scan_is_one_read_each_plus_selected_target(self) -> None:
        patcher, counts = self._count_reads()
        with patcher:
            resolved = flowctl._memory_resolve_read_target(self.memory, "entry-17")
            self.assertIsNotNone(resolved)
            selected = Path(resolved["entry"]["path"])
            flowctl._memory_read_entry(selected)
        self.assertEqual(counts[str(selected)], 2)
        self.assertEqual(
            {counts[str(path)] for path in self.paths if path != selected}, {1}
        )

    def test_full_id_grammar_and_containment_reject_traversal_and_symlink(self) -> None:
        self.assertIsNone(
            flowctl._memory_resolve_read_target(
                self.memory, "knowledge/conventions/../secret-2026-07-21"
            )
        )
        outside = Path(self._tmp.name) / "outside-2026-07-21.md"
        outside.write_text(self.paths[0].read_text(encoding="utf-8"), encoding="utf-8")
        link = self.memory / "knowledge" / "conventions" / "linked-2026-07-21.md"
        link.symlink_to(outside)
        self.assertIsNone(
            flowctl._memory_resolve_read_target(
                self.memory, "knowledge/conventions/linked-2026-07-21"
            )
        )
        loop = self.memory / "knowledge" / "conventions" / "loop-2026-07-21.md"
        loop.symlink_to(loop.name)
        self.assertIsNone(
            flowctl._memory_resolve_read_target(
                self.memory, "knowledge/conventions/loop-2026-07-21"
            )
        )


if __name__ == "__main__":
    unittest.main()
