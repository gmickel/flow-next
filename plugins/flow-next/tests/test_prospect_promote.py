"""Unit tests for `flowctl prospect promote` (fn-33 task 5).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers:
  - Basic promote: epic created, spec contains Source link + survivor context.
  - Idempotency refuse: second promote of same idea exits 2.
  - --force override: appends another epic-id to promoted_to[N].
  - Out-of-range / zero / negative --idea exits 2.
  - Corrupt artifact refuses (exit 3, matches `read`).
  - promoted_ideas + promoted_to round-trip via the canonical reader.
  - Slug-only id resolves to latest dated artifact.
  - --epic-title override.
  - Frontmatter dict rendering survives PyYAML round-trip.
  - Inline-yaml fallback parser handles the rendered dict (no-PyYAML safety).
  - `_prospect_rewrite_in_place` writes atomically and is reused by archive.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_prospect_promote_under_test", FLOWCTL_PY
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
        "survivor_count": 2,
        "rejected_count": 16,
        "rejection_rate": 0.73,
        "artifact_id": "dx-improvements-2026-04-24",
        "promoted_ideas": [],
        "status": "active",
    }
    base.update(overrides)
    return base


def _body() -> str:
    return (
        "## Focus\n"
        "\n"
        "DX wins.\n"
        "\n"
        "## Grounding snapshot\n"
        "\n"
        "- git log: 12 files\n"
        "\n"
        "## Survivors\n"
        "\n"
        "### High leverage (1-3)\n"
        "\n"
        "#### 1. Cache scout output\n"
        "**Summary:** Re-use scout JSON across runs\n"
        "**Leverage:** Small-diff lever because scout cache key already exists; impact lands on every plan run.\n"
        "**Size:** S\n"
        "**Affected areas:** plan-skill, scout-runtime\n"
        "**Risk notes:** stale cache could hide drift\n"
        "**Next step:** /flow-next:interview\n"
        "\n"
        "#### 2. Faster smoke\n"
        "**Summary:** Trim smoke runtime to <30s\n"
        "**Leverage:** Small-diff lever because most steps are sequential I/O; impact lands on every CI run.\n"
        "**Size:** M\n"
        "**Next step:** /flow-next:interview\n"
        "\n"
        "### Worth considering (4-7)\n"
        "\n"
        "_(none)_\n"
        "\n"
        "### If you have the time (8+)\n"
        "\n"
        "_(none)_\n"
        "\n"
        "## Rejected\n"
        "\n"
        "- Bogus idea — out-of-scope: covered by fn-32\n"
    )


def _seed_project(td: Path, fm_overrides: dict[str, Any] | None = None) -> Path:
    """Create a minimal `.flow/` project under `td` with a seeded artifact."""
    flow = td / ".flow"
    (flow / "epics").mkdir(parents=True)
    (flow / "specs").mkdir()
    (flow / "tasks").mkdir()
    (flow / "prospects").mkdir()
    (flow / "meta.json").write_text(
        '{"next_epic": 1, "schema_version": 1}\n', encoding="utf-8"
    )
    fm = _frontmatter(**(fm_overrides or {}))
    target = flow / "prospects" / f"{fm['artifact_id']}.md"
    flowctl.write_prospect_artifact(target, fm, _body())
    return target


def _run_promote(
    flow_root: Path,
    artifact_id: str,
    idea: int,
    *,
    force: bool = False,
    epic_title: str | None = None,
    use_json: bool = True,
) -> tuple[dict[str, Any], int]:
    """Run cmd_prospect_promote with patched get_flow_dir / ensure_flow_exists."""
    original_get_flow_dir = flowctl.get_flow_dir
    original_ensure = flowctl.ensure_flow_exists
    flowctl.get_flow_dir = lambda: flow_root / ".flow"  # type: ignore[assignment]
    flowctl.ensure_flow_exists = lambda: True  # type: ignore[assignment]
    ns = argparse.Namespace(
        artifact_id=artifact_id,
        idea=idea,
        force=force,
        epic_title=epic_title,
        json=use_json,
        prospect_cmd="promote",
    )
    captured = io.StringIO()
    captured_err = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = captured
    sys.stderr = captured_err
    exit_code = 0
    try:
        try:
            flowctl.cmd_prospect_promote(ns)
        except SystemExit as e:
            exit_code = int(e.code) if e.code is not None else 0
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        flowctl.get_flow_dir = original_get_flow_dir  # type: ignore[assignment]
        flowctl.ensure_flow_exists = original_ensure  # type: ignore[assignment]
    out = captured.getvalue().strip()
    if use_json and out:
        return json.loads(out), exit_code
    return {"_text": out, "_stderr": captured_err.getvalue()}, exit_code


# ---------- Frontmatter dict rendering (writer-side) -----------------


class FrontmatterDictRendering(unittest.TestCase):
    def test_inline_dict_render(self) -> None:
        rendered = flowctl._format_prospect_yaml_value(
            {"1": ["fn-1-a", "fn-2-b"], "2": ["fn-3-c"]}, "promoted_to"
        )
        self.assertTrue(rendered.startswith("{"))
        self.assertTrue(rendered.endswith("}"))
        # Keys (numeric strings) sort numerically before string fallback.
        self.assertIn('"1": [fn-1-a, fn-2-b]', rendered)
        self.assertIn('"2": [fn-3-c]', rendered)

    def test_int_keys_sort_numerically(self) -> None:
        rendered = flowctl._format_prospect_yaml_value(
            {10: ["a"], 2: ["b"], 1: ["c"]}, "promoted_to"
        )
        # Sorted: 1, 2, 10 — string sort would produce 1, 10, 2.
        self.assertEqual(rendered, "{1: [c], 2: [b], 10: [a]}")

    def test_validate_rejects_non_dict_promoted_to(self) -> None:
        fm = _frontmatter(promoted_to="not a dict")
        errors = flowctl.validate_prospect_frontmatter(fm)
        self.assertTrue(any("promoted_to must be a dict" in e for e in errors))

    def test_validate_accepts_dict_promoted_to(self) -> None:
        fm = _frontmatter(promoted_to={"1": ["fn-1-a"]})
        errors = flowctl.validate_prospect_frontmatter(fm)
        self.assertEqual(errors, [])

    def test_inline_yaml_fallback_parses_flow_mapping(self) -> None:
        text = (
            'promoted_to: {"1": [fn-1-a, fn-2-b], "2": [fn-3-c]}\n'
            "promoted_ideas: [1, 2]\n"
            "title: x\n"
        )
        result = flowctl._parse_inline_yaml(text)
        self.assertIn("promoted_to", result)
        self.assertEqual(
            result["promoted_to"],
            {"1": ["fn-1-a", "fn-2-b"], "2": ["fn-3-c"]},
        )

    def test_inline_yaml_empty_flow_mapping(self) -> None:
        result = flowctl._parse_inline_yaml("promoted_to: {}\ntitle: x\n")
        self.assertEqual(result.get("promoted_to"), {})


# ---------- Round-trip through prospect parser -----------------------


class FrontmatterRoundTrip(unittest.TestCase):
    def test_dict_round_trips_via_canonical_reader(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "x.md"
            fm = _frontmatter(
                promoted_ideas=[1, 2],
                promoted_to={"1": ["fn-1-a", "fn-2-b"], "2": ["fn-3-c"]},
            )
            flowctl.write_prospect_artifact(target, fm, _body())
            text = target.read_text(encoding="utf-8")
            parsed = flowctl._prospect_parse_frontmatter(text)
            self.assertIsNotNone(parsed)
            assert parsed is not None
            promoted_to = parsed.get("promoted_to")
            self.assertIsInstance(promoted_to, dict)
            assert isinstance(promoted_to, dict)
            # PyYAML may type keys as int; inline-parser as str. Coerce
            # for assert.
            keys_as_str = {str(k): v for k, v in promoted_to.items()}
            self.assertEqual(
                keys_as_str["1"], ["fn-1-a", "fn-2-b"]
            )
            self.assertEqual(keys_as_str["2"], ["fn-3-c"])


# ---------- Shared in-place rewriter ---------------------------------


class RewriteInPlace(unittest.TestCase):
    def test_rewrite_overwrites_existing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "x.md"
            flowctl.write_prospect_artifact(target, _frontmatter(), _body())
            new_fm = _frontmatter(promoted_ideas=[3])
            flowctl._prospect_rewrite_in_place(target, new_fm, _body())
            text = target.read_text(encoding="utf-8")
            self.assertIn("promoted_ideas: [3]", text)

    def test_rewrite_validates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "x.md"
            flowctl.write_prospect_artifact(target, _frontmatter(), _body())
            broken = _frontmatter()
            del broken["title"]  # required field
            self.assertRaises(
                ValueError,
                flowctl._prospect_rewrite_in_place,
                target,
                broken,
                _body(),
            )


# ---------- Promote happy path ---------------------------------------


class PromoteBasic(unittest.TestCase):
    def test_creates_epic_with_source_link(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _seed_project(tdp)
            result, code = _run_promote(
                tdp, "dx-improvements-2026-04-24", 1
            )
            self.assertEqual(code, 0, result)
            self.assertTrue(result.get("success"))
            self.assertEqual(result["idea"], 1)
            self.assertIn("fn-1", result["epic_id"])
            self.assertEqual(result["epic_title"], "Cache scout output")
            self.assertEqual(
                result["source_link"],
                ".flow/prospects/dx-improvements-2026-04-24.md#idea-1",
            )
            spec_path = Path(result["spec_path"])
            self.assertTrue(spec_path.exists())
            spec_text = spec_path.read_text(encoding="utf-8")
            self.assertIn("## Source", spec_text)
            self.assertIn("## Overview", spec_text)
            self.assertIn("Re-use scout JSON across runs", spec_text)
            self.assertIn("Small-diff lever because scout cache key", spec_text)
            self.assertIn(
                ".flow/prospects/dx-improvements-2026-04-24.md#idea-1",
                spec_text,
            )
            self.assertIn("DX improvements", spec_text)  # focus hint
            self.assertIn("plan-skill, scout-runtime", spec_text)  # affected areas
            self.assertIn("stale cache could hide drift", spec_text)  # risk notes
            self.assertIn(
                "S (from prospect ranking)", spec_text
            )

    def test_artifact_frontmatter_updated(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            target = _seed_project(tdp)
            result, code = _run_promote(
                tdp, "dx-improvements-2026-04-24", 1
            )
            self.assertEqual(code, 0, result)
            self.assertTrue(result.get("artifact_updated"))
            text = target.read_text(encoding="utf-8")
            parsed = flowctl._prospect_parse_frontmatter(text)
            assert parsed is not None
            promoted_ideas = parsed.get("promoted_ideas") or []
            # Round-trip type: PyYAML int / inline-parser str — coerce.
            self.assertEqual([int(x) for x in promoted_ideas], [1])
            promoted_to = parsed.get("promoted_to") or {}
            keys_as_str = {str(k): v for k, v in promoted_to.items()}
            self.assertIn("1", keys_as_str)
            self.assertEqual(len(keys_as_str["1"]), 1)
            self.assertTrue(keys_as_str["1"][0].startswith("fn-"))

    def test_text_mode_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _seed_project(tdp)
            result, code = _run_promote(
                tdp, "dx-improvements-2026-04-24", 1, use_json=False
            )
            self.assertEqual(code, 0, result)
            self.assertIn("Promoted idea #1", result["_text"])
            self.assertIn("Cache scout output", result["_text"])
            self.assertIn("/flow-next:interview", result["_text"])


# ---------- Idempotency / --force ------------------------------------


class Idempotency(unittest.TestCase):
    def test_second_promote_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _seed_project(tdp)
            _, c1 = _run_promote(tdp, "dx-improvements-2026-04-24", 1)
            self.assertEqual(c1, 0)
            result, c2 = _run_promote(tdp, "dx-improvements-2026-04-24", 1)
            self.assertEqual(c2, 2)
            self.assertFalse(result.get("success", True))
            self.assertIn("already promoted", str(result.get("error", "")))

    def test_force_appends_another_epic_id(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            target = _seed_project(tdp)
            r1, _ = _run_promote(tdp, "dx-improvements-2026-04-24", 1)
            r2, c2 = _run_promote(
                tdp, "dx-improvements-2026-04-24", 1, force=True
            )
            self.assertEqual(c2, 0)
            self.assertNotEqual(r1["epic_id"], r2["epic_id"])
            text = target.read_text(encoding="utf-8")
            parsed = flowctl._prospect_parse_frontmatter(text)
            assert parsed is not None
            promoted_to = parsed.get("promoted_to") or {}
            keys_as_str = {str(k): v for k, v in promoted_to.items()}
            ids = keys_as_str["1"]
            self.assertEqual(len(ids), 2)
            self.assertIn(r1["epic_id"], ids)
            self.assertIn(r2["epic_id"], ids)


# ---------- Edge cases -----------------------------------------------


class EdgeCases(unittest.TestCase):
    def test_zero_idea_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _seed_project(tdp)
            result, code = _run_promote(
                tdp, "dx-improvements-2026-04-24", 0
            )
            self.assertEqual(code, 2)
            self.assertIn(">= 1", str(result.get("error", "")))

    def test_negative_idea_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _seed_project(tdp)
            result, code = _run_promote(
                tdp, "dx-improvements-2026-04-24", -3
            )
            self.assertEqual(code, 2)
            self.assertIn(">= 1", str(result.get("error", "")))

    def test_out_of_range_idea_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _seed_project(tdp)
            result, code = _run_promote(
                tdp, "dx-improvements-2026-04-24", 99
            )
            self.assertEqual(code, 2)
            self.assertIn("out of range", str(result.get("error", "")))

    def test_corrupt_artifact_refuses_with_exit_3(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _seed_project(tdp)
            broken = tdp / ".flow" / "prospects" / "broken-2026-04-24.md"
            broken.write_text("not a real artifact\n", encoding="utf-8")
            result, code = _run_promote(tdp, "broken-2026-04-24", 1)
            self.assertEqual(code, 3)
            self.assertEqual(result.get("status"), "corrupt")
            self.assertIn("no frontmatter", str(result.get("corruption", "")))

    def test_missing_artifact_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _seed_project(tdp)
            result, code = _run_promote(tdp, "nonexistent", 1)
            self.assertNotEqual(code, 0)
            self.assertFalse(result.get("success", True))
            self.assertIn("not found", str(result.get("error", "")))

    def test_slug_only_resolves_to_latest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _seed_project(
                tdp,
                fm_overrides={
                    "date": "2026-03-01",
                    "artifact_id": "dx-improvements-2026-03-01",
                },
            )
            # Add second, newer artifact.
            fm2 = _frontmatter()
            target2 = (
                tdp / ".flow" / "prospects" / f"{fm2['artifact_id']}.md"
            )
            flowctl.write_prospect_artifact(target2, fm2, _body())
            # Slug-only — should resolve to the newer (2026-04-24) one.
            result, code = _run_promote(tdp, "dx-improvements", 1)
            self.assertEqual(code, 0, result)
            self.assertEqual(
                result["artifact_id"], "dx-improvements-2026-04-24"
            )

    def test_epic_title_override(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _seed_project(tdp)
            result, code = _run_promote(
                tdp,
                "dx-improvements-2026-04-24",
                1,
                epic_title="Custom Override Title",
            )
            self.assertEqual(code, 0, result)
            self.assertEqual(result["epic_title"], "Custom Override Title")
            self.assertIn("custom-override-title", result["epic_id"])


if __name__ == "__main__":
    unittest.main()
