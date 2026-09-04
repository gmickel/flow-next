"""fn-220: spec create/skeleton render templates/spec.md via the override cascade."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"

_CANONICAL_H2S = {
    "Goal & Context",
    "Architecture & Data Models",
    "API Contracts",
    "Edge Cases & Constraints",
    "Acceptance Criteria",
    "Boundaries",
    "Decision Context",
}

_LEGACY_FIXTURE = """# fn-1 Legacy

## Overview
legacy goal body

## Acceptance
- **R1:** legacy criterion. Errors: none

## Boundaries / non-goals
- out of scope item

## Decision context
- chose the smaller design
"""

_NO_HEADINGS = """# Title

## Unrelated
nope
"""


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_spec_template_cascade_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


def _h2s(text: str) -> set[str]:
    return set(re.findall(r"^## (.+)$", text, re.MULTILINE))


class TestSpecTemplateCascade(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._cwd = os.getcwd()
        os.chdir(self.root)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.root, check=True, capture_output=True
        )
        code, out, err = self._run("init", "--json")
        self.assertEqual(code, 0, err or out)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _run(self, *argv: str) -> "tuple[int, str, str]":
        """Invoke production argparse routing; return (code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with mock.patch.object(sys, "argv", ["flowctl", *argv]):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    flowctl.main()
                except SystemExit as e:
                    code = int(e.code or 0)
        return code, out.getvalue(), err.getvalue()

    def test_skeleton_json_canonical_h2s_no_frontmatter(self) -> None:
        code, out, err = self._run("spec", "skeleton", "--json")
        self.assertEqual(code, 0, err or out)
        payload = json.loads(out)
        skeleton = payload["skeleton"]
        self.assertEqual(_h2s(skeleton), _CANONICAL_H2S)
        self.assertFalse(skeleton.startswith("---"))

    def test_spec_create_substitutes_h1_and_canonical_h2s(self) -> None:
        code, out, err = self._run(
            "spec", "create", "--title", "Cascade fixture", "--json"
        )
        self.assertEqual(code, 0, err or out)
        spec_id = json.loads(out)["id"]
        md = (self.root / ".flow" / "specs" / f"{spec_id}.md").read_text(
            encoding="utf-8"
        )
        h1 = next((ln for ln in md.splitlines() if ln.startswith("# ")), "")
        self.assertEqual(h1, f"# {spec_id} Cascade fixture")
        self.assertEqual(_h2s(md), _CANONICAL_H2S)

    def test_override_cascade_spec_md_then_spec_md_then_bundled(self) -> None:
        spec_upper = (
            "# <spec-id> <Title>\n\n"
            "## Goal & Context\nfrom SPEC.md\n\n"
            "## Acceptance Criteria\n- **R1:** x. Errors: none\n"
        )
        spec_lower = (
            "# <spec-id> <Title>\n\n"
            "## Goal & Context\nfrom spec.md\n\n"
            "## Acceptance Criteria\n- **R1:** y. Errors: none\n"
        )
        (self.root / "SPEC.md").write_text(spec_upper, encoding="utf-8")
        (self.root / "spec.md").write_text(spec_lower, encoding="utf-8")

        code, out, err = self._run("spec", "skeleton")
        self.assertEqual(code, 0, err or out)
        self.assertEqual(out, spec_upper)

        (self.root / "SPEC.md").unlink()
        code, out, err = self._run("spec", "skeleton")
        self.assertEqual(code, 0, err or out)
        self.assertEqual(out, spec_lower)

        (self.root / "spec.md").unlink()
        code, out, err = self._run("spec", "skeleton", "--json")
        self.assertEqual(code, 0, err or out)
        self.assertEqual(_h2s(json.loads(out)["skeleton"]), _CANONICAL_H2S)

    def test_crlf_override_normalized_to_lf(self) -> None:
        (self.root / "spec.md").write_bytes(
            b"# <spec-id> <Title>\r\n\r\n## Goal & Context\r\nx\r\n"
        )
        code, out, err = self._run("spec", "skeleton")
        self.assertEqual(code, 0, err or out)
        self.assertNotIn("\r", out)

    def test_exporter_synonyms_legacy_and_negative(self) -> None:
        goal = flowctl._export_parse_first_present_section(
            _LEGACY_FIXTURE, flowctl._EXPORT_GOAL_AND_CONTEXT_HEADINGS
        )
        boundaries = flowctl._export_parse_boundaries(_LEGACY_FIXTURE)
        criteria, _residue = flowctl._export_scan_acceptance_criteria(
            _LEGACY_FIXTURE
        )
        decision = flowctl._export_parse_first_present_section(
            _LEGACY_FIXTURE, flowctl._EXPORT_DECISION_CONTEXT_HEADINGS
        )
        self.assertTrue(goal.strip())
        self.assertTrue(boundaries)
        self.assertTrue(criteria)
        self.assertEqual(criteria[0]["id"], "R1")
        self.assertTrue(criteria[0]["text"])
        self.assertTrue(decision.strip())

        self.assertEqual(
            flowctl._export_parse_first_present_section(
                _NO_HEADINGS, flowctl._EXPORT_GOAL_AND_CONTEXT_HEADINGS
            ),
            "",
        )
        self.assertEqual(flowctl._export_parse_boundaries(_NO_HEADINGS), [])
        self.assertEqual(
            flowctl._export_scan_acceptance_criteria(_NO_HEADINGS)[0], []
        )
        self.assertEqual(
            flowctl._export_parse_first_present_section(
                _NO_HEADINGS, flowctl._EXPORT_DECISION_CONTEXT_HEADINGS
            ),
            "",
        )

    def test_validate_warns_once_on_legacy_headings(self) -> None:
        code, out, err = self._run(
            "spec", "create", "--title", "Legacy headings fixture", "--json"
        )
        self.assertEqual(code, 0, err or out)
        spec_id = json.loads(out)["id"]

        code, out, err = self._run("validate", "--spec", spec_id, "--json")
        self.assertEqual(code, 0, err or out)
        canonical = json.loads(out)
        self.assertIn("warnings", canonical)
        self.assertEqual(
            [w for w in canonical["warnings"] if "legacy spec headings" in w],
            [],
        )

        legacy_path = self.root / "legacy.md"
        legacy_path.write_text(_LEGACY_FIXTURE, encoding="utf-8")
        code, out, err = self._run(
            "spec", "set-plan", spec_id, "--file", str(legacy_path), "--json"
        )
        self.assertEqual(code, 0, err or out)

        code, out, err = self._run("validate", "--spec", spec_id, "--json")
        self.assertEqual(code, 0, err or out)
        legacy = json.loads(out)
        hits = [w for w in legacy["warnings"] if "legacy spec headings" in w]
        self.assertEqual(len(hits), 1, legacy.get("warnings"))


if __name__ == "__main__":
    unittest.main()
