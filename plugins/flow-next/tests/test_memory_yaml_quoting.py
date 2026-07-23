"""Unit tests for memory YAML quoting + silent-drop warning (issue #235).

Run:
    python3 -m unittest test_memory_yaml_quoting -q

Covers:
  - memory add titles starting with ', ", -  round-trip via frontmatter
  - _yaml_scalar_needs_quoting unit assertions for the new gates
  - inline-parser round-trip of quoted escapes (embedded double quotes)
  - malformed entry skip emits stderr warning
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_yaml_quoting_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


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


if __name__ == "__main__":
    unittest.main()
