"""Unit tests for prospect CLI helpers (fn-33 task 4).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers:
  - `_prospect_parse_frontmatter` happy path + corruption signals
  - `_prospect_detect_corruption` reason strings (R16: byte-for-byte match
    with the Phase 0 inline classifier in workflow.md §0.2)
  - `_prospect_artifact_status` derivation (active / stale / archived)
  - `_prospect_iter_artifacts` (default vs include_archive) listing
  - `_prospect_resolve_id` precedence (full id, slug-only, suffixed)
  - section / survivors / rejected extractors
  - archive move + frontmatter rewrite

Tests do not exercise the argparse layer end-to-end (those go through
smoke tests in task 6); they verify the helpers + descriptor shape.
"""

from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_prospect_cli_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


# ---------- Test data builders ----------------------------------------


def _frontmatter(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "title": "DX improvements",
        "date": "2026-04-24",
        "focus_hint": "DX improvements",
        "volume": 22,
        "survivor_count": 6,
        "rejected_count": 16,
        "rejection_rate": 0.73,
        "artifact_id": "dx-improvements-2026-04-24",
        "promoted_ideas": [],
        "status": "active",
    }
    base.update(overrides)
    return base


def _body(survivors: bool = True, grounding: bool = True) -> str:
    parts: list[str] = ["## Focus", "", "DX wins.", ""]
    if grounding:
        parts.extend(["## Grounding snapshot", "", "- git log: 12 files", ""])
    if survivors:
        parts.extend(
            [
                "## Survivors",
                "",
                "### High leverage (1-3)",
                "",
                "#### 1. Cache scout output",
                "**Summary:** Re-use scout JSON across runs",
                "**Leverage:** Small-diff lever because scout cache key already exists; impact lands on every plan run.",
                "**Size:** S",
                "**Next step:** /flow-next:interview",
                "",
                "### Worth considering (4-7)",
                "",
                "_(none)_",
                "",
                "### If you have the time (8+)",
                "",
                "_(none)_",
                "",
            ]
        )
    parts.extend(["## Rejected", "", "- Bogus idea — out-of-scope: covered by fn-32"])
    return "\n".join(parts) + "\n"


def _write_artifact(
    target: Path, fm_overrides: dict[str, Any] | None = None, body_text: str | None = None
) -> Path:
    fm = _frontmatter(**(fm_overrides or {}))
    body = body_text if body_text is not None else _body()
    flowctl.write_prospect_artifact(target, fm, body)
    return target


# ---------- _prospect_parse_frontmatter -------------------------------


class ParseFrontmatter(unittest.TestCase):
    def test_no_delimiter_returns_none(self) -> None:
        self.assertIsNone(flowctl._prospect_parse_frontmatter("just body\n"))
        self.assertIsNone(flowctl._prospect_parse_frontmatter(""))
        self.assertIsNone(flowctl._prospect_parse_frontmatter("# heading\n"))

    def test_unterminated_delimiter_returns_none(self) -> None:
        self.assertIsNone(
            flowctl._prospect_parse_frontmatter("---\nkey: value\nbody")
        )

    def test_basic_parse(self) -> None:
        text = '---\ntitle: x\ndate: "2026-04-24"\n---\n\nbody\n'
        result = flowctl._prospect_parse_frontmatter(text)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.get("title"), "x")
        self.assertEqual(str(result.get("date")), "2026-04-24")

    def test_inline_list_parse(self) -> None:
        text = '---\ntitle: x\ndate: "2026-04-24"\npromoted_ideas: [1, 3]\n---\n\nb\n'
        result = flowctl._prospect_parse_frontmatter(text)
        self.assertIsNotNone(result)
        assert result is not None
        # PyYAML returns ints; inline parser returns strings — accept both.
        promoted = result.get("promoted_ideas")
        self.assertIsInstance(promoted, list)
        assert promoted is not None
        self.assertEqual(len(promoted), 2)


# ---------- _prospect_detect_corruption (R16 contract) ----------------


class DetectCorruption(unittest.TestCase):
    """Reason strings MUST match the Phase 0 inline classifier byte-for-byte."""

    def _write(self, td: str, text: str, name: str = "p.md") -> Path:
        p = Path(td) / name
        p.write_text(text, encoding="utf-8")
        return p

    def test_clean_artifact_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "dx-2026-04-24.md"
            _write_artifact(target)
            self.assertIsNone(flowctl._prospect_detect_corruption(target))

    def test_no_frontmatter_block(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = self._write(td, "## Just a body\n\nNo YAML.\n")
            self.assertEqual(
                flowctl._prospect_detect_corruption(p),
                "no frontmatter block",
            )

    def test_unparseable_date(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            text = (
                "---\n"
                'title: "x"\n'
                'date: "not-a-date"\n'
                'focus_hint: "x"\n'
                "volume: 1\n"
                "survivor_count: 1\n"
                "rejected_count: 0\n"
                "rejection_rate: 0.0\n"
                'artifact_id: "x-2026-04-24"\n'
                "promoted_ideas: []\n"
                'status: "active"\n'
                "---\n"
                "\n"
                "## Grounding snapshot\n\n- a\n\n## Survivors\n\n"
            )
            p = self._write(td, text)
            self.assertEqual(
                flowctl._prospect_detect_corruption(p),
                "unparseable date",
            )

    def test_missing_grounding_section(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "p.md"
            _write_artifact(target, body_text=_body(grounding=False))
            self.assertEqual(
                flowctl._prospect_detect_corruption(target),
                "missing Grounding snapshot section",
            )

    def test_missing_survivors_section(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "p.md"
            _write_artifact(target, body_text=_body(survivors=False))
            self.assertEqual(
                flowctl._prospect_detect_corruption(target),
                "missing Survivors section",
            )

    def test_unreadable_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            # Point at a path under a directory that doesn't exist — the
            # read fails with OSError and surfaces as "unreadable".
            p = Path(td) / "missing-dir" / "p.md"
            self.assertEqual(
                flowctl._prospect_detect_corruption(p),
                "unreadable",
            )

    def test_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = self._write(td, "")
            self.assertEqual(flowctl._prospect_detect_corruption(p), "empty")

    def test_whitespace_only_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = self._write(td, "   \n\n  \n")
            self.assertEqual(flowctl._prospect_detect_corruption(p), "empty")

    def test_missing_required_field(self) -> None:
        # Drop `volume` from a valid artifact's frontmatter and verify the
        # helper surfaces the missing-field reason.
        with tempfile.TemporaryDirectory() as td:
            text = (
                "---\n"
                'title: "x"\n'
                'date: "2026-04-24"\n'
                'focus_hint: "x"\n'
                "survivor_count: 1\n"
                "rejected_count: 0\n"
                "rejection_rate: 0.0\n"
                'artifact_id: "x-2026-04-24"\n'
                "promoted_ideas: []\n"
                'status: "active"\n'
                "---\n"
                "\n"
                "## Grounding snapshot\n\n- a\n\n## Survivors\n\n"
            )
            p = Path(td) / "p.md"
            p.write_text(text, encoding="utf-8")
            reason = flowctl._prospect_detect_corruption(p)
            self.assertIsNotNone(reason)
            assert reason is not None
            self.assertTrue(reason.startswith("missing frontmatter field:"))
            self.assertIn("volume", reason)


# ---------- _prospect_artifact_status ---------------------------------


class ArtifactStatus(unittest.TestCase):
    def test_active_recent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            today = date(2026, 4, 24)
            target = Path(td) / "p.md"
            _write_artifact(target, fm_overrides={"date": today.isoformat()})
            status, age = flowctl._prospect_artifact_status(target, None, today)
            self.assertEqual(status, "active")
            self.assertEqual(age, 0)

    def test_stale_when_older_than_30_days(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            today = date(2026, 6, 1)
            old_date = today - timedelta(days=45)
            target = Path(td) / "p.md"
            _write_artifact(
                target,
                fm_overrides={"date": old_date.isoformat()},
            )
            status, age = flowctl._prospect_artifact_status(target, None, today)
            self.assertEqual(status, "stale")
            self.assertEqual(age, 45)

    def test_archived_status_takes_precedence_over_age(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            today = date(2026, 6, 1)
            old_date = today - timedelta(days=45)
            target = Path(td) / "p.md"
            _write_artifact(
                target,
                fm_overrides={
                    "date": old_date.isoformat(),
                    "status": "archived",
                },
            )
            status, _age = flowctl._prospect_artifact_status(target, None, today)
            self.assertEqual(status, "archived")

    def test_corruption_propagates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "p.md"
            target.write_text("not a real artifact\n", encoding="utf-8")
            status, age = flowctl._prospect_artifact_status(
                target, "no frontmatter block", date(2026, 4, 24)
            )
            self.assertEqual(status, "corrupt")
            self.assertIsNone(age)


# ---------- _prospect_iter_artifacts ----------------------------------


class IterArtifacts(unittest.TestCase):
    def test_empty_dir_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "prospects"
            d.mkdir()
            self.assertEqual(flowctl._prospect_iter_artifacts(d), [])

    def test_lists_active_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "prospects"
            d.mkdir()
            today = date.today()
            _write_artifact(
                d / "dx-improvements-2026-04-24.md",
                fm_overrides={"date": today.isoformat()},
            )
            artifacts = flowctl._prospect_iter_artifacts(d, today=today)
            self.assertEqual(len(artifacts), 1)
            self.assertEqual(
                artifacts[0]["artifact_id"], "dx-improvements-2026-04-24"
            )
            self.assertEqual(artifacts[0]["status"], "active")
            self.assertEqual(artifacts[0]["survivor_count"], 6)
            self.assertEqual(artifacts[0]["promoted_count"], 0)

    def test_excludes_archive_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "prospects"
            d.mkdir()
            arch = d / "_archive"
            arch.mkdir()
            today = date.today()
            _write_artifact(
                d / "active-2026-04-24.md",
                fm_overrides={"date": today.isoformat(), "artifact_id": "active-2026-04-24"},
            )
            _write_artifact(
                arch / "old-2026-01-01.md",
                fm_overrides={
                    "date": "2026-01-01",
                    "artifact_id": "old-2026-01-01",
                    "status": "archived",
                },
            )
            default = flowctl._prospect_iter_artifacts(d, today=today)
            self.assertEqual(len(default), 1)
            self.assertEqual(default[0]["artifact_id"], "active-2026-04-24")
            with_archive = flowctl._prospect_iter_artifacts(
                d, include_archive=True, today=today
            )
            self.assertEqual(len(with_archive), 2)
            in_archive = [a for a in with_archive if a["in_archive"]]
            self.assertEqual(len(in_archive), 1)
            self.assertEqual(in_archive[0]["artifact_id"], "old-2026-01-01")

    def test_underscore_prefixed_files_at_top_level_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "prospects"
            d.mkdir()
            (d / "_notes.md").write_text("ignore me\n", encoding="utf-8")
            today = date.today()
            _write_artifact(
                d / "real-2026-04-24.md",
                fm_overrides={"date": today.isoformat(), "artifact_id": "real-2026-04-24"},
            )
            artifacts = flowctl._prospect_iter_artifacts(d, today=today)
            self.assertEqual(len(artifacts), 1)
            self.assertEqual(artifacts[0]["artifact_id"], "real-2026-04-24")

    def test_corrupt_artifact_surfaces_with_reason(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "prospects"
            d.mkdir()
            (d / "broken.md").write_text("not yaml\n", encoding="utf-8")
            artifacts = flowctl._prospect_iter_artifacts(d)
            self.assertEqual(len(artifacts), 1)
            self.assertEqual(artifacts[0]["status"], "corrupt")
            self.assertEqual(
                artifacts[0]["corruption"], "no frontmatter block"
            )


# ---------- _prospect_resolve_id --------------------------------------


class ResolveId(unittest.TestCase):
    def _setup(self, d: Path, *artifacts: tuple[str, str]) -> None:
        d.mkdir(parents=True, exist_ok=True)
        for filename, date_str in artifacts:
            target = d / filename
            _write_artifact(
                target,
                fm_overrides={
                    "date": date_str,
                    "artifact_id": target.stem,
                },
            )

    def test_full_id_match(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "prospects"
            self._setup(d, ("dx-improvements-2026-04-24.md", "2026-04-24"))
            r = flowctl._prospect_resolve_id(d, "dx-improvements-2026-04-24")
            self.assertIsNotNone(r)
            assert r is not None
            self.assertEqual(r["artifact_id"], "dx-improvements-2026-04-24")

    def test_slug_only_picks_latest_date(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "prospects"
            self._setup(
                d,
                ("dx-improvements-2026-03-01.md", "2026-03-01"),
                ("dx-improvements-2026-04-24.md", "2026-04-24"),
            )
            r = flowctl._prospect_resolve_id(d, "dx-improvements")
            self.assertIsNotNone(r)
            assert r is not None
            self.assertEqual(r["artifact_id"], "dx-improvements-2026-04-24")

    def test_slug_only_suffixed_disambiguation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "prospects"
            # Same-day suffixed version wins on tiebreak (latest stem).
            self._setup(
                d,
                ("dx-2026-04-24.md", "2026-04-24"),
                ("dx-2026-04-24-2.md", "2026-04-24"),
            )
            r = flowctl._prospect_resolve_id(d, "dx")
            self.assertIsNotNone(r)
            assert r is not None
            self.assertEqual(r["artifact_id"], "dx-2026-04-24-2")

    def test_returns_none_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "prospects"
            d.mkdir()
            self.assertIsNone(flowctl._prospect_resolve_id(d, "nope"))


# ---------- section + structured extraction ---------------------------


class SectionExtractor(unittest.TestCase):
    def test_focus_section_slice(self) -> None:
        text = _body()
        section = flowctl._prospect_extract_section(text, "focus")
        self.assertIsNotNone(section)
        assert section is not None
        self.assertIn("## Focus", section)
        self.assertIn("DX wins.", section)
        # Doesn't bleed into Grounding.
        self.assertNotIn("Grounding snapshot", section)

    def test_grounding_section_slice(self) -> None:
        text = _body()
        section = flowctl._prospect_extract_section(text, "grounding")
        self.assertIsNotNone(section)
        assert section is not None
        self.assertIn("## Grounding snapshot", section)
        self.assertIn("git log: 12 files", section)

    def test_unknown_section_returns_none_via_extract(self) -> None:
        # The CLI guards this earlier; the helper just returns None.
        self.assertIsNone(
            flowctl._prospect_extract_section("body", "unknown")
        )

    def test_missing_section_returns_none(self) -> None:
        self.assertIsNone(
            flowctl._prospect_extract_section("## Other\n\nbody\n", "focus")
        )

    def test_extract_survivors_structured(self) -> None:
        body = _body()
        section = flowctl._prospect_extract_section(body, "survivors") or ""
        survivors = flowctl._prospect_extract_survivors(section)
        self.assertEqual(len(survivors), 1)
        self.assertEqual(survivors[0]["position"], 1)
        self.assertEqual(survivors[0]["title"], "Cache scout output")
        self.assertEqual(survivors[0]["size"], "S")
        self.assertEqual(survivors[0]["bucket"], "High leverage (1-3)")

    def test_extract_rejected(self) -> None:
        section = "## Rejected\n\n- A — out-of-scope: covered\n- B — too-large\n"
        rejected = flowctl._prospect_extract_rejected(section)
        self.assertEqual(len(rejected), 2)
        self.assertEqual(rejected[0]["title"], "A")
        self.assertEqual(rejected[0]["taxonomy"], "out-of-scope")
        self.assertEqual(rejected[0]["reason"], "covered")
        self.assertEqual(rejected[1]["title"], "B")
        self.assertEqual(rejected[1]["taxonomy"], "too-large")
        self.assertEqual(rejected[1]["reason"], "")


# ---------- archive move + frontmatter rewrite ------------------------


class ArchiveCommand(unittest.TestCase):
    """Validate the move-and-rewrite path used by `cmd_prospect_archive`.

    Patches `get_flow_dir` / `ensure_flow_exists` to point at a temp dir so
    the test exercises the real CLI handler without depending on the
    surrounding git repo state.
    """

    def _run_archive(self, prospects_dir: Path, artifact_id: str) -> dict[str, Any]:
        import argparse
        import io
        import sys
        import json

        # Point the helpers at our temp prospects dir's grandparent — that's
        # where `.flow/` lives.
        flow_root = prospects_dir.parent.parent  # tmp/.flow/prospects -> tmp
        original_get_flow_dir = flowctl.get_flow_dir
        original_ensure = flowctl.ensure_flow_exists
        flowctl.get_flow_dir = lambda: flow_root / ".flow"  # type: ignore[assignment]
        flowctl.ensure_flow_exists = lambda: True  # type: ignore[assignment]
        ns = argparse.Namespace(
            artifact_id=artifact_id, json=True, prospect_cmd="archive"
        )
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            try:
                flowctl.cmd_prospect_archive(ns)
            except SystemExit:
                pass
        finally:
            sys.stdout = old_stdout
            flowctl.get_flow_dir = original_get_flow_dir  # type: ignore[assignment]
            flowctl.ensure_flow_exists = original_ensure  # type: ignore[assignment]
        out = captured.getvalue().strip()
        return json.loads(out) if out else {}

    def test_move_and_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            # Layout: <td>/.flow/prospects/<artifact>.md
            flow = Path(td) / ".flow"
            flow.mkdir()
            d = flow / "prospects"
            d.mkdir()
            today = date.today()
            target = d / "dx-improvements-2026-04-24.md"
            _write_artifact(
                target,
                fm_overrides={
                    "date": today.isoformat(),
                    "artifact_id": "dx-improvements-2026-04-24",
                },
            )
            result = self._run_archive(d, "dx-improvements-2026-04-24")
            self.assertTrue(result.get("success"), result)
            self.assertEqual(
                result.get("artifact_id"), "dx-improvements-2026-04-24"
            )
            archived_path = Path(result["to"])
            self.assertTrue(archived_path.exists())
            text = archived_path.read_text(encoding="utf-8")
            self.assertIn("status: archived", text)
            self.assertFalse(target.exists())
            # The archive dir lives under prospects/_archive/.
            self.assertEqual(archived_path.parent.name, "_archive")
            self.assertEqual(archived_path.parent.parent, d)

    def test_already_archived_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            flow = Path(td) / ".flow"
            flow.mkdir()
            d = flow / "prospects"
            arch = d / "_archive"
            arch.mkdir(parents=True)
            today = date.today()
            target = arch / "old-2026-01-01.md"
            _write_artifact(
                target,
                fm_overrides={
                    "date": "2026-01-01",
                    "artifact_id": "old-2026-01-01",
                    "status": "archived",
                },
            )
            result = self._run_archive(d, "old-2026-01-01")
            self.assertFalse(result.get("success", True))
            self.assertIn("already archived", str(result.get("error", "")))


if __name__ == "__main__":
    unittest.main()
