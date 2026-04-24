"""Unit tests for prospect artifact writer + slug helpers (fn-33 task 3).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers:
  - slug derivation (focus hint → slug, empty / unicode / collisions)
  - same-day collision suffixing (-2, -3, ...)
  - YAML frontmatter round-trip including optional flags
  - body rendering with bucketed survivors + optional fields
  - atomic write-then-rename: artifact exists after writer returns
  - concurrent-create race: second writer at same artifact_id raises
"""

from __future__ import annotations

import importlib.util
import re
import tempfile
import unittest
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_prospect_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


def _required_frontmatter(**overrides: Any) -> dict[str, Any]:
    """Return a complete prospect frontmatter dict for tests."""
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


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Cheap parser — splits the YAML block between `---` delimiters."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "frontmatter block missing"
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip()
    return fm


# -------- slug + id helpers ---------------------------------------------


class SlugDerivation(unittest.TestCase):
    def test_no_hint_falls_back_to_open_ended(self) -> None:
        self.assertEqual(flowctl._prospect_slug(None), "open-ended")
        self.assertEqual(flowctl._prospect_slug(""), "open-ended")

    def test_basic_concept_hint(self) -> None:
        self.assertEqual(
            flowctl._prospect_slug("DX improvements"), "dx-improvements"
        )

    def test_path_hint(self) -> None:
        self.assertEqual(
            flowctl._prospect_slug("plugins/flow-next/skills/"),
            "plugins-flow-next-skills",
        )

    def test_unicode_falls_back_when_empty(self) -> None:
        # Pure non-ASCII slugifies to empty → falls back to open-ended.
        self.assertEqual(flowctl._prospect_slug("日本語"), "open-ended")

    def test_collapses_punctuation_and_spaces(self) -> None:
        self.assertEqual(
            flowctl._prospect_slug("review-skill polish!!!"),
            "review-skill-polish",
        )

    def test_long_hint_truncated(self) -> None:
        slug = flowctl._prospect_slug(
            "a very long focus hint that absolutely will exceed the slugify cap"
        )
        self.assertIsNotNone(slug)
        self.assertLessEqual(len(slug), 40)


class NextIdAllocation(unittest.TestCase):
    def test_first_slot_no_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            self.assertEqual(
                flowctl._prospect_next_id(d, "dx", "2026-04-24"),
                "dx-2026-04-24",
            )

    def test_collision_suffix_2(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "dx-2026-04-24.md").write_text("placeholder", encoding="utf-8")
            self.assertEqual(
                flowctl._prospect_next_id(d, "dx", "2026-04-24"),
                "dx-2026-04-24-2",
            )

    def test_collision_suffix_3(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "dx-2026-04-24.md").write_text("a", encoding="utf-8")
            (d / "dx-2026-04-24-2.md").write_text("b", encoding="utf-8")
            self.assertEqual(
                flowctl._prospect_next_id(d, "dx", "2026-04-24"),
                "dx-2026-04-24-3",
            )

    def test_creates_dir_if_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "nested" / "prospects"
            self.assertFalse(d.exists())
            flowctl._prospect_next_id(d, "dx", "2026-04-24")
            self.assertTrue(d.is_dir())


# -------- frontmatter validation ----------------------------------------


class FrontmatterValidation(unittest.TestCase):
    def test_complete_required_passes(self) -> None:
        errors = flowctl.validate_prospect_frontmatter(_required_frontmatter())
        self.assertEqual(errors, [])

    def test_missing_required_field_fails(self) -> None:
        fm = _required_frontmatter()
        fm.pop("artifact_id")
        errors = flowctl.validate_prospect_frontmatter(fm)
        self.assertTrue(any("artifact_id" in e for e in errors))

    def test_unknown_field_rejected(self) -> None:
        fm = _required_frontmatter(extra_thing="nope")
        errors = flowctl.validate_prospect_frontmatter(fm)
        self.assertTrue(any("unknown" in e for e in errors))

    def test_invalid_status_rejected(self) -> None:
        fm = _required_frontmatter(status="bogus")
        errors = flowctl.validate_prospect_frontmatter(fm)
        self.assertTrue(any("status" in e for e in errors))

    def test_optional_floor_violation_accepted(self) -> None:
        fm = _required_frontmatter(floor_violation=True)
        self.assertEqual(flowctl.validate_prospect_frontmatter(fm), [])

    def test_optional_generation_under_volume_accepted(self) -> None:
        fm = _required_frontmatter(generation_under_volume=True)
        self.assertEqual(flowctl.validate_prospect_frontmatter(fm), [])

    def test_promoted_ideas_must_be_list(self) -> None:
        fm = _required_frontmatter(promoted_ideas="not-a-list")
        errors = flowctl.validate_prospect_frontmatter(fm)
        self.assertTrue(any("promoted_ideas" in e for e in errors))

    def test_non_dict_input(self) -> None:
        errors = flowctl.validate_prospect_frontmatter("oops")
        self.assertEqual(errors, ["frontmatter must be a dict"])


# -------- writer + round-trip -------------------------------------------


class WriteProspectArtifact(unittest.TestCase):
    def test_writes_and_creates_parent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "prospects" / "dx-2026-04-24.md"
            self.assertFalse(target.parent.exists())
            flowctl.write_prospect_artifact(
                target, _required_frontmatter(), "## Focus\n\nbody\n"
            )
            self.assertTrue(target.exists())
            text = target.read_text(encoding="utf-8")
            self.assertIn("---\n", text)
            self.assertIn("## Focus", text)

    def test_frontmatter_field_order(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "dx.md"
            flowctl.write_prospect_artifact(
                target,
                _required_frontmatter(floor_violation=True),
                "body",
            )
            text = target.read_text(encoding="utf-8")
            # Required fields appear in PROSPECT_FIELD_ORDER; floor_violation
            # is optional and lands after status.
            order_keys = [
                line.split(":", 1)[0]
                for line in text.split("---\n", 2)[1].splitlines()
                if ":" in line
            ]
            self.assertEqual(order_keys[0], "title")
            self.assertEqual(order_keys[1], "date")
            self.assertIn("floor_violation", order_keys)
            self.assertGreater(
                order_keys.index("floor_violation"),
                order_keys.index("status"),
            )

    def test_round_trip_optional_flags(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "dx.md"
            flowctl.write_prospect_artifact(
                target,
                _required_frontmatter(
                    floor_violation=True, generation_under_volume=True
                ),
                "body",
            )
            text = target.read_text(encoding="utf-8")
            fm = _parse_frontmatter(text)
            self.assertEqual(fm["floor_violation"], "true")
            self.assertEqual(fm["generation_under_volume"], "true")

    def test_omits_optional_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "dx.md"
            flowctl.write_prospect_artifact(
                target, _required_frontmatter(), "body"
            )
            text = target.read_text(encoding="utf-8")
            self.assertNotIn("floor_violation", text)
            self.assertNotIn("generation_under_volume", text)

    def test_date_round_trips_quoted(self) -> None:
        # PyYAML would coerce 2026-04-24 to a date object; we quote so it
        # survives as a string regardless of which parser reads it back.
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "dx.md"
            flowctl.write_prospect_artifact(
                target, _required_frontmatter(), "body"
            )
            text = target.read_text(encoding="utf-8")
            self.assertIn('date: "2026-04-24"', text)

    def test_promoted_ideas_serializes_as_inline_list(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "dx.md"
            flowctl.write_prospect_artifact(
                target,
                _required_frontmatter(promoted_ideas=[1, 3]),
                "body",
            )
            text = target.read_text(encoding="utf-8")
            self.assertIn("promoted_ideas: [1, 3]", text)

    def test_invalid_frontmatter_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "dx.md"
            fm = _required_frontmatter()
            fm.pop("title")
            with self.assertRaises(ValueError):
                flowctl.write_prospect_artifact(target, fm, "body")
            self.assertFalse(target.exists())

    def test_concurrent_create_raises_file_exists(self) -> None:
        # Simulates two writers passing the same path past `_prospect_next_id`
        # — the writer must not silently clobber.
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "dx.md"
            flowctl.write_prospect_artifact(
                target, _required_frontmatter(), "first"
            )
            with self.assertRaises(FileExistsError):
                flowctl.write_prospect_artifact(
                    target, _required_frontmatter(), "second"
                )
            self.assertIn("first", target.read_text(encoding="utf-8"))

    def test_no_temp_files_left_behind(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            target = d / "dx.md"
            flowctl.write_prospect_artifact(
                target, _required_frontmatter(), "body"
            )
            tmp_files = list(d.glob(".tmp.*"))
            self.assertEqual(tmp_files, [])


# -------- body rendering ------------------------------------------------


class RenderProspectBody(unittest.TestCase):
    def _ranked(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "high_leverage": [
                {
                    "position": 1,
                    "title": "Cache scout output",
                    "summary": "Re-use scout JSON across runs",
                    "leverage": (
                        "Small-diff lever because scout cache key already "
                        "exists; impact lands on every plan run."
                    ),
                    "size": "S",
                    "affected_areas": [
                        "plugins/flow-next/skills/flow-next-plan",
                    ],
                    "risk_notes": "stale cache risk if scout deps change",
                    "persona": "senior-maintainer",
                },
                {
                    "position": 2,
                    "title": "Snapshot stale memory",
                    "summary": "Surface stale memory entries pre-plan",
                    "leverage": (
                        "Small-diff lever because memory list already "
                        "supports filters; impact lands on plan grounding."
                    ),
                    "size": "S",
                },
            ],
            "worth_considering": [
                {
                    "position": 4,
                    "title": "Audit unused scouts",
                    "summary": "Trim scouts never referenced",
                    "leverage": (
                        "Small-diff lever because catalog is centralized; "
                        "impact lands on plan latency."
                    ),
                    "size": "M",
                }
            ],
            "if_you_have_the_time": [],
        }

    def _drops(self) -> list[dict[str, Any]]:
        return [
            {
                "title": "Rewrite review backend",
                "taxonomy": "out-of-scope",
                "reason": "covered by fn-32",
            },
            {
                "title": "Add LLM scoring",
                "taxonomy": "backward-incompat",
                "reason": "violates prose-only ranking decision",
            },
        ]

    def test_body_has_required_sections(self) -> None:
        body = flowctl.render_prospect_body(
            "DX improvements",
            "- git log: 12 files\n- open epics: fn-33",
            self._ranked(),
            self._drops(),
        )
        self.assertIn("## Focus", body)
        self.assertIn("## Grounding snapshot", body)
        self.assertIn("## Survivors", body)
        self.assertIn("### High leverage (1-3)", body)
        self.assertIn("### Worth considering (4-7)", body)
        self.assertIn("### If you have the time (8+)", body)
        self.assertIn("## Rejected", body)

    def test_each_survivor_has_required_subfields(self) -> None:
        body = flowctl.render_prospect_body(
            "DX", "snapshot", self._ranked(), []
        )
        self.assertIn("#### 1. Cache scout output", body)
        self.assertIn("**Summary:** Re-use scout JSON across runs", body)
        self.assertIn("**Leverage:** Small-diff lever because scout", body)
        self.assertIn("**Size:** S", body)
        self.assertIn("**Next step:** /flow-next:interview", body)

    def test_optional_body_fields_render_when_present(self) -> None:
        body = flowctl.render_prospect_body(
            "DX", "snapshot", self._ranked(), []
        )
        self.assertIn(
            "**Affected areas:** plugins/flow-next/skills/flow-next-plan",
            body,
        )
        self.assertIn(
            "**Risk notes:** stale cache risk if scout deps change", body
        )
        self.assertIn("**Persona:** senior-maintainer", body)

    def test_optional_fields_skipped_when_absent(self) -> None:
        body = flowctl.render_prospect_body(
            "DX", "snapshot", self._ranked(), []
        )
        # Survivor #2 has no optional fields — confirm none leak.
        # Slice from "#### 2." to next "####" or end.
        seg = body.split("#### 2. Snapshot stale memory", 1)[1]
        seg = seg.split("####", 1)[0]
        self.assertNotIn("**Affected areas:**", seg)
        self.assertNotIn("**Risk notes:**", seg)
        self.assertNotIn("**Persona:**", seg)

    def test_empty_buckets_render_none_marker(self) -> None:
        body = flowctl.render_prospect_body(
            "DX", "snapshot", self._ranked(), []
        )
        # `if_you_have_the_time` is empty → renders `_(none)_`.
        seg = body.split("### If you have the time (8+)", 1)[1]
        self.assertIn("_(none)_", seg.split("##", 1)[0])

    def test_drops_render_with_taxonomy(self) -> None:
        body = flowctl.render_prospect_body(
            "DX", "snapshot", self._ranked(), self._drops()
        )
        self.assertIn(
            "- Rewrite review backend — out-of-scope: covered by fn-32", body
        )
        self.assertIn(
            "- Add LLM scoring — backward-incompat: violates prose-only ranking decision",
            body,
        )

    def test_drops_empty_renders_none_marker(self) -> None:
        body = flowctl.render_prospect_body(
            "DX", "snapshot", self._ranked(), []
        )
        seg = body.split("## Rejected", 1)[1]
        self.assertIn("_(none)_", seg)

    def test_open_ended_focus_renders_marker(self) -> None:
        body = flowctl.render_prospect_body(
            "", "snapshot", self._ranked(), []
        )
        self.assertIn("_(open-ended)_", body)


# -------- end-to-end: write + parse round-trip ---------------------------


class EndToEnd(unittest.TestCase):
    def test_full_artifact_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            artifact_id = flowctl._prospect_next_id(d, "dx", "2026-04-24")
            self.assertEqual(artifact_id, "dx-2026-04-24")
            target = d / f"{artifact_id}.md"
            ranked = {
                "high_leverage": [
                    {
                        "position": 1,
                        "title": "T1",
                        "summary": "S1",
                        "leverage": (
                            "Small-diff lever because X; impact lands on Y."
                        ),
                        "size": "S",
                    }
                ],
                "worth_considering": [],
                "if_you_have_the_time": [],
            }
            body = flowctl.render_prospect_body("focus", "snapshot", ranked, [])
            fm = _required_frontmatter(
                artifact_id=artifact_id,
                survivor_count=1,
                rejected_count=0,
                rejection_rate=0.0,
                volume=1,
            )
            flowctl.write_prospect_artifact(target, fm, body)
            text = target.read_text(encoding="utf-8")
            self.assertIn(f"artifact_id: {artifact_id}", text)
            self.assertIn("#### 1. T1", text)
            # Second invocation same day → suffix -2.
            artifact_id_2 = flowctl._prospect_next_id(d, "dx", "2026-04-24")
            self.assertEqual(artifact_id_2, "dx-2026-04-24-2")


if __name__ == "__main__":
    unittest.main()
