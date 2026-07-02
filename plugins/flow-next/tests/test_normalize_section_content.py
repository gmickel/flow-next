"""Task-section content normalization (fn-79, R1–R6).

`task set-acceptance` / `set-description` must replace the WHOLE section —
agent-supplied content beginning with its own `## …` H2 used to layer a rogue
sibling section (fn-78 damage shape). Covers:

- `normalize_section_content` (pure): leading title-variant strip, embedded
  H2→H3 demotion, fenced-code-block skip, `## Acceptance Tests` negative case,
  legacy `## Acceptance criteria` variant, byte-preservation of clean input.
- `patch_task_section`: idempotent set-acceptance (no layering), self-heal of
  singly- and doubly-layered files, unrelated-section preservation, unchanged
  duplicate/missing error semantics.
- CLI end-to-end: `task create --acceptance-file` with a leading-H2 file,
  `task set-acceptance` twice byte-idempotent.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_normalize_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


# ── normalize_section_content (pure) ───────────────────────────────────────


class NormalizeTestCase(unittest.TestCase):
    def test_leading_exact_title_stripped(self) -> None:
        out = flowctl.normalize_section_content(
            "## Acceptance", "## Acceptance\n- R1: thing\n"
        )
        self.assertEqual(out, "- R1: thing\n")

    def test_leading_decorated_variant_stripped(self) -> None:
        out = flowctl.normalize_section_content(
            "## Acceptance", "## Acceptance Criteria (fn-78 R1–R6)\n- R1: x\n"
        )
        self.assertEqual(out, "- R1: x\n")

    def test_legacy_lowercase_criteria_variant_stripped(self) -> None:
        out = flowctl.normalize_section_content(
            "## Acceptance", "## Acceptance criteria\n- R1: x\n"
        )
        self.assertEqual(out, "- R1: x\n")

    def test_separator_suffix_variants_stripped(self) -> None:
        for title in (
            "## Acceptance — updated",
            "## Acceptance: v2",
            "## Acceptance - old",
            "## Acceptance Criteria: final",
        ):
            out = flowctl.normalize_section_content(
                "## Acceptance", f"{title}\n- R1: x"
            )
            self.assertEqual(out, "- R1: x", f"title not stripped: {title!r}")

    def test_acceptance_tests_demoted_not_stripped(self) -> None:
        # Arbitrary different word after the section word is NOT a title
        # variant — it is content, demoted to H3.
        out = flowctl.normalize_section_content(
            "## Acceptance", "## Acceptance Tests\n- t1\n"
        )
        self.assertEqual(out, "### Acceptance Tests\n- t1\n")

    def test_embedded_h2_demoted(self) -> None:
        out = flowctl.normalize_section_content(
            "## Acceptance", "- R1: x\n\n## Notes\nprose\n"
        )
        self.assertEqual(out, "- R1: x\n\n### Notes\nprose\n")

    def test_h2_inside_backtick_fence_untouched(self) -> None:
        content = "- R1: x\n```bash\n## not a heading\n```\n"
        self.assertEqual(
            flowctl.normalize_section_content("## Acceptance", content), content
        )

    def test_h2_inside_tilde_fence_untouched(self) -> None:
        content = "- R1: x\n~~~\n## not a heading\n~~~\n"
        self.assertEqual(
            flowctl.normalize_section_content("## Acceptance", content), content
        )

    def test_h2_after_closed_fence_demoted(self) -> None:
        out = flowctl.normalize_section_content(
            "## Acceptance", "```\n## fenced\n```\n## after\n"
        )
        self.assertEqual(out, "```\n## fenced\n```\n### after\n")

    def test_h3_and_prose_untouched_clean_roundtrip(self) -> None:
        content = "- R1: x\n### Sub\nprose ## not-a-heading\n"
        self.assertEqual(
            flowctl.normalize_section_content("## Acceptance", content), content
        )

    def test_description_variant_no_criteria_word(self) -> None:
        # `Criteria` is an Acceptance-only legacy word; for Description it is
        # content → demoted, not stripped.
        out = flowctl.normalize_section_content(
            "## Description", "## Description Criteria\nbody\n"
        )
        self.assertEqual(out, "### Description Criteria\nbody\n")

    def test_description_exact_and_suffix_stripped(self) -> None:
        out = flowctl.normalize_section_content(
            "## Description", "## Description — v2\nbody\n"
        )
        self.assertEqual(out, "body\n")


# ── patch_task_section (splice + self-heal) ────────────────────────────────


def _task_md(acceptance_block: str) -> str:
    return (
        "# fn-1.1 Title\n\n"
        "## Description\nDesc body\n\n"
        f"## Acceptance\n{acceptance_block}\n"
        "\n## Done summary\nTBD\n\n"
        "## Evidence\n- Commits:\n- Tests:\n- PRs:\n"
    )


class PatchTaskSectionTestCase(unittest.TestCase):
    def test_set_acceptance_idempotent_no_layering(self) -> None:
        current = _task_md("- [ ] old")
        new = "## Acceptance Criteria (fn-79 R1)\n- R1: new\n\n## Extra\nnote"
        once = flowctl.patch_task_section(current, "## Acceptance", new)
        self.assertEqual(once.count("\n## Acceptance"), 1)
        self.assertIn("### Extra", once)
        self.assertNotIn("\n## Extra", once)
        twice = flowctl.patch_task_section(once, "## Acceptance", new)
        self.assertEqual(once, twice)

    def test_self_heal_single_layered_file(self) -> None:
        # fn-78 damage shape: rogue title-variant section after the target.
        damaged = _task_md(
            "- R1: new\n\n## Acceptance Criteria (fn-78 R1–R6)\n- R1: old"
        )
        healed = flowctl.patch_task_section(
            damaged, "## Acceptance", "- R1: final"
        )
        self.assertNotIn("Acceptance Criteria", healed)
        self.assertNotIn("- R1: old", healed)
        self.assertIn("## Acceptance\n- R1: final", healed)
        self.assertEqual(healed.count("\n## Acceptance"), 1)

    def test_self_heal_doubly_layered_file(self) -> None:
        damaged = _task_md(
            "- R1: newest\n\n"
            "## Acceptance Criteria (round 2)\n- R1: mid\n\n"
            "## Acceptance criteria\n- R1: oldest"
        )
        healed = flowctl.patch_task_section(
            damaged, "## Acceptance", "- R1: final"
        )
        self.assertNotIn("Acceptance Criteria", healed)
        self.assertNotIn("Acceptance criteria", healed)
        self.assertNotIn("mid", healed)
        self.assertNotIn("oldest", healed)
        self.assertEqual(healed.count("\n## Acceptance"), 1)

    def test_self_heal_preserves_unrelated_sections(self) -> None:
        damaged = _task_md(
            "- R1: new\n\n## Acceptance Criteria (stale)\n- R1: old"
        )
        healed = flowctl.patch_task_section(
            damaged, "## Acceptance", "- R1: final"
        )
        for heading in ("## Description", "## Done summary", "## Evidence"):
            self.assertIn(heading, healed)
        self.assertIn("Desc body", healed)
        self.assertIn("- Commits:", healed)

    def test_rogue_variant_not_contiguous_is_boundary(self) -> None:
        # A title-variant H2 NOT directly after the target section stays a
        # hard boundary (fold is contiguity-scoped).
        content = (
            "# fn-1.1 T\n\n## Acceptance\n- new\n\n"
            "## Done summary\nTBD\n\n"
            "## Acceptance Criteria (orphan)\n- orphan\n"
        )
        out = flowctl.patch_task_section(content, "## Acceptance", "- final")
        self.assertIn("## Acceptance Criteria (orphan)", out)
        self.assertIn("- orphan", out)

    def test_fenced_h2_in_stored_section_not_a_boundary(self) -> None:
        # Content with a fence-preserved `## ` line persisted in the section:
        # the next patch must replace the WHOLE section (fenced line is not a
        # boundary — no stale content left behind) and stay idempotent.
        new = "- R1: x\n```bash\n## not a heading\n```\nafter fence"
        current = _task_md(new)
        once = flowctl.patch_task_section(current, "## Acceptance", new)
        self.assertEqual(once.count("\n## Acceptance"), 1)
        twice = flowctl.patch_task_section(once, "## Acceptance", new)
        self.assertEqual(once, twice)
        # Replacement with different content leaves no stale fenced remnant.
        replaced = flowctl.patch_task_section(once, "## Acceptance", "- fresh")
        self.assertNotIn("## not a heading", replaced)
        self.assertNotIn("after fence", replaced)
        self.assertIn("## Acceptance\n- fresh", replaced)

    def test_fenced_canonical_heading_no_duplicate_error(self) -> None:
        # A byte-exact `## Acceptance` INSIDE a fence is content, not a
        # duplicate heading — patching must succeed and replace cleanly.
        new = "- R1: x\n```\n## Acceptance\n```"
        current = _task_md(new)
        healed = flowctl.patch_task_section(current, "## Acceptance", "- ok")
        self.assertEqual(healed.count("\n## Acceptance"), 1)
        self.assertIn("## Acceptance\n- ok", healed)

    def test_get_task_section_fence_aware(self) -> None:
        body = "- R1: x\n```bash\n## not a heading\n```\ntail"
        content = _task_md(body)
        self.assertEqual(
            flowctl.get_task_section(content, "## Acceptance"), body
        )

    def test_validate_headings_fenced_canonical_not_duplicate(self) -> None:
        # A persisted fenced `## Acceptance` is content — validate must not
        # report it as a duplicate heading (write/read/validate parity).
        content = _task_md("- R1: x\n```\n## Acceptance\n```")
        self.assertEqual(flowctl.validate_task_spec_headings(content), [])

    def test_validate_headings_fenced_heading_does_not_satisfy(self) -> None:
        # A fenced heading must NOT satisfy the required-heading presence
        # check — the real section is missing.
        content = (
            "# fn-1.1 T\n\n## Description\nbody\n\n"
            "```\n## Acceptance\n```\n\n"
            "## Done summary\nTBD\n\n## Evidence\n- Commits:\n"
        )
        errors = flowctl.validate_task_spec_headings(content)
        self.assertIn("Missing required heading: ## Acceptance", errors)

    def test_duplicate_canonical_heading_still_raises(self) -> None:
        content = _task_md("- a") + "\n## Acceptance\n- dup\n"
        with self.assertRaises(ValueError) as ctx:
            flowctl.patch_task_section(content, "## Acceptance", "- x")
        self.assertIn("duplicate heading", str(ctx.exception))

    def test_missing_section_still_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            flowctl.patch_task_section(
                "# fn-1.1 T\n\n## Description\nbody\n", "## Acceptance", "- x"
            )
        self.assertIn("not found", str(ctx.exception))


# ── CLI end-to-end (create --acceptance-file, set-acceptance twice) ───────


class CliEndToEndTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self._run("init")
        out = self._run("spec", "create", "--title", "Normalize test", "--json")
        self.spec_id = json.loads(out)["id"]

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, *argv: str) -> str:
        proc = subprocess.run(
            [sys.executable, str(FLOWCTL_PY), *argv],
            cwd=self.tmpdir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode, 0, f"flowctl {' '.join(argv)} failed: {proc.stderr}"
        )
        return proc.stdout

    def test_create_with_leading_h2_acceptance_file(self) -> None:
        acc = self.tmpdir / "acc.md"
        acc.write_text(
            "## Acceptance Criteria (fn-79 R1–R3)\n- R1: works\n\n## Notes\nn1\n"
        )
        out = self._run(
            "task", "create", "--spec", self.spec_id,
            "--title", "T1", "--acceptance-file", str(acc), "--json",
        )
        task_id = json.loads(out)["id"]
        md = (self.tmpdir / ".flow" / "tasks" / f"{task_id}.md").read_text()
        self.assertEqual(md.count("\n## Acceptance"), 1)
        self.assertNotIn("Acceptance Criteria", md)
        self.assertIn("### Notes", md)
        # Skeleton stays well-formed: validate-critical headings all present.
        for heading in ("## Description", "## Done summary", "## Evidence"):
            self.assertIn(heading, md)

    def test_set_acceptance_twice_byte_idempotent(self) -> None:
        out = self._run(
            "task", "create", "--spec", self.spec_id, "--title", "T2", "--json"
        )
        task_id = json.loads(out)["id"]
        acc = self.tmpdir / "acc2.md"
        acc.write_text("## Acceptance Criteria — v2\n- R1: x\n\n## More\nm\n")
        md_path = self.tmpdir / ".flow" / "tasks" / f"{task_id}.md"
        self._run("task", "set-acceptance", task_id, "--file", str(acc), "--json")
        first = md_path.read_text()
        self.assertEqual(first.count("\n## Acceptance"), 1)
        self.assertIn("### More", first)
        self._run("task", "set-acceptance", task_id, "--file", str(acc), "--json")
        self.assertEqual(md_path.read_text(), first)


if __name__ == "__main__":
    unittest.main()
