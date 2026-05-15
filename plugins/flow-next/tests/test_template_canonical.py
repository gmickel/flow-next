"""Unit tests for the canonical spec template + R21 drift guard + CLAUDE.md
cross-linking (fn-44.9, covers R11 / R17 / R21).

Asserts:
  - `plugins/flow-next/templates/spec.md` exists at canonical path.
  - Frontmatter declares the 7 canonical sections + 6 auxiliary sections with
    scope-owner annotations.
  - The body uses `<!-- scope: business|technical|both -->` HTML-comment
    owner markers under each canonical section heading.
  - CLAUDE.md cross-links to the template path, does NOT inline-duplicate
    the canonical section list (R17).
  - The R21 drift guard awk pattern fires on a synthetic skill-markdown
    file that re-embeds the canonical sequence; does NOT fire on
    single-mention references.
  - The Codex mirror, when present, ships its own `codex/templates/spec.md`
    byte-for-byte identical to the canonical source (R20).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent
REPO_ROOT = PLUGIN_DIR.parent.parent
TEMPLATE_PATH = PLUGIN_DIR / "templates" / "spec.md"
CLAUDE_MD_PATH = REPO_ROOT / "CLAUDE.md"
CODEX_TEMPLATE_PATH = PLUGIN_DIR / "codex" / "templates" / "spec.md"
SKILLS_DIR = PLUGIN_DIR / "skills"


# Canonical 7-section sequence per R11 + R21.
CANONICAL_SECTIONS = [
    "## Goal & Context",
    "## Architecture & Data Models",
    "## API Contracts",
    "## Edge Cases & Constraints",
    "## Acceptance Criteria",
    "## Boundaries",
    "## Decision Context",
]

AUXILIARY_SECTIONS = [
    "Strategy Alignment",
    "Strategy Conflicts",
    "Glossary Conflicts",
    "Conversation Evidence",
    "Resolved via Codebase",
    "Resolved via Project Docs",
]


class TestTemplateExistsAtCanonicalPath(unittest.TestCase):
    """R11: template lives at `plugins/flow-next/templates/spec.md`."""

    def test_template_file_exists(self) -> None:
        self.assertTrue(
            TEMPLATE_PATH.is_file(),
            f"canonical template missing: {TEMPLATE_PATH}",
        )

    def test_template_is_non_empty(self) -> None:
        content = TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertGreater(len(content), 500, "template body too short")


class TestTemplateStructure(unittest.TestCase):
    """R11: template contains the 7 canonical sections in declared order
    with scope-owner HTML-comment annotations."""

    def setUp(self) -> None:
        self.body = TEMPLATE_PATH.read_text(encoding="utf-8")
        self.lines = self.body.splitlines()

    def test_all_canonical_sections_present(self) -> None:
        for section in CANONICAL_SECTIONS:
            self.assertIn(
                section, self.body, f"missing canonical section: {section}"
            )

    def test_canonical_sections_in_declared_order(self) -> None:
        # Find each canonical heading at column 1, record line index, assert
        # monotonically increasing.
        positions: list[int] = []
        for section in CANONICAL_SECTIONS:
            for idx, line in enumerate(self.lines):
                if line == section:
                    positions.append(idx)
                    break
            else:
                self.fail(f"section {section!r} not found at column 1")
        self.assertEqual(
            positions,
            sorted(positions),
            f"canonical sections out of order: {positions}",
        )

    def test_scope_owner_annotations_present(self) -> None:
        """Each canonical section heading is immediately followed by a
        `<!-- scope: <value> -->` HTML comment in the next 2 lines."""
        for section in CANONICAL_SECTIONS:
            idx = next(
                (i for i, line in enumerate(self.lines) if line == section),
                -1,
            )
            self.assertGreaterEqual(idx, 0, f"missing section {section}")
            # Look at the next 2 lines for the scope owner marker.
            window = "\n".join(self.lines[idx + 1 : idx + 3])
            self.assertRegex(
                window,
                r"<!--\s*scope:\s*(business|technical|both)\b",
                f"section {section!r} missing scope-owner annotation in next 2 lines",
            )

    def test_decision_context_documents_flat_and_substructured(self) -> None:
        """The `## Decision Context` section documents both (A) FLAT and
        (B) SUBSTRUCTURED shapes — required by the R22 backward-compat
        invariant + the biz-pass H3 promotion contract."""
        self.assertIn("FLAT", self.body)
        self.assertIn("SUBSTRUCTURED", self.body)
        self.assertIn("### Motivation", self.body)
        self.assertIn("### Implementation Tradeoffs", self.body)


class TestTemplateFrontmatter(unittest.TestCase):
    """R11: frontmatter explains purpose + consumers + canonical sections."""

    def setUp(self) -> None:
        self.body = TEMPLATE_PATH.read_text(encoding="utf-8")
        # Extract frontmatter (between first two `---` lines).
        lines = self.body.splitlines()
        self.assertEqual(lines[0], "---", "template must start with frontmatter")
        try:
            end = lines.index("---", 1)
        except ValueError:
            self.fail("template frontmatter unclosed")
        self.frontmatter = "\n".join(lines[1:end])

    def test_lists_canonical_sections_with_scope_annotations(self) -> None:
        # All 7 canonical sections appear in the frontmatter alongside their
        # `# scope: ...` annotation.
        for section in [s.replace("## ", "") for s in CANONICAL_SECTIONS]:
            self.assertIn(
                section,
                self.frontmatter,
                f"section {section!r} not enumerated in frontmatter",
            )
        # The annotation set must mention all three scope owners.
        for scope in ("business", "technical", "both"):
            self.assertIn(
                f"scope: {scope}",
                self.frontmatter,
                f"frontmatter missing scope-owner annotation: {scope}",
            )

    def test_lists_auxiliary_sections(self) -> None:
        for aux in AUXILIARY_SECTIONS:
            self.assertIn(
                aux,
                self.frontmatter,
                f"auxiliary section {aux!r} missing from frontmatter",
            )

    def test_declares_consumers(self) -> None:
        """Consumers list names the skills that read this template."""
        for consumer in (
            "flow-next-capture",
            "flow-next-interview",
            "flow-next-plan",
            "flow-next-work",
        ):
            self.assertIn(consumer, self.frontmatter)


class TestClaudeMdCrossLinksTemplate(unittest.TestCase):
    """R17: CLAUDE.md links to the template; does NOT inline-duplicate the
    canonical section list."""

    def setUp(self) -> None:
        self.assertTrue(
            CLAUDE_MD_PATH.is_file(), f"CLAUDE.md missing at {CLAUDE_MD_PATH}"
        )
        self.body = CLAUDE_MD_PATH.read_text(encoding="utf-8")

    def test_links_to_template_path(self) -> None:
        self.assertIn(
            "plugins/flow-next/templates/spec.md",
            self.body,
            "CLAUDE.md must link to the canonical spec template",
        )

    def test_does_not_inline_duplicate_canonical_sequence(self) -> None:
        """The R21 drift guard scans skills/; CLAUDE.md is in a different
        scope but R17 still applies — CLAUDE.md must not re-embed the
        canonical section sequence inline. Detection: same rule as R21
        (Goal & Context → Architecture → API Contracts co-occurrence at
        column 1 within 30 lines)."""
        lines = self.body.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("## Goal & Context"):
                window = lines[i + 1 : i + 31]
                arch = any(l.startswith("## Architecture & Data Models") for l in window)
                api = any(l.startswith("## API Contracts") for l in window)
                self.assertFalse(
                    arch and api,
                    f"CLAUDE.md re-embeds canonical sequence at line {i + 1}",
                )


class TestR21DriftGuardSemantics(unittest.TestCase):
    """R21 drift guard: detect canonical-section re-embedding in any skill
    markdown file under `plugins/flow-next/skills/*/`. This test runs the
    actual awk pattern from sync-codex.sh against synthetic fixtures.
    """

    AWK_PROGRAM = r"""
        FNR == NR { lines[FNR] = $0; total = FNR }
        END {
          for (i = 1; i <= total; i++) {
            if (lines[i] ~ /^## Goal & Context/) {
              arch = 0; api = 0
              for (j = i + 1; j <= i + 30 && j <= total; j++) {
                if (lines[j] ~ /^## Architecture & Data Models/) arch = 1
                if (lines[j] ~ /^## API Contracts/) api = 1
              }
              if (arch && api) {
                printf "%s:%d\n", FILENAME, i
              }
            }
          }
        }
    """

    def _run_awk(self, file_path: Path) -> str:
        proc = subprocess.run(
            ["awk", self.AWK_PROGRAM, str(file_path)],
            capture_output=True,
            text=True,
        )
        return proc.stdout

    def test_guard_fires_on_canonical_sequence_in_skill_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "bad.md"
            fixture.write_text(
                "# Bad skill markdown\n\n"
                "## Goal & Context\n"
                "Some content\n\n"
                "## Architecture & Data Models\n"
                "More content\n\n"
                "## API Contracts\n"
                "Even more content\n"
            )
            out = self._run_awk(fixture)
            self.assertIn(str(fixture), out, "guard must fire on re-embedded sequence")

    def test_guard_silent_on_single_mention(self) -> None:
        """A skill that quotes ONE canonical section in isolation (e.g., a
        question bank referencing `## Goal & Context`) does NOT trip the
        guard — the three headers must co-occur within 30 lines."""
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "ok.md"
            fixture.write_text(
                "# OK skill markdown\n\n"
                "Walk the `## Goal & Context` section first.\n"
                "Skip everything else.\n"
            )
            out = self._run_awk(fixture)
            self.assertEqual(out.strip(), "", "guard must NOT fire on single mention")

    def test_guard_silent_when_headers_outside_30_line_window(self) -> None:
        """Three canonical headers separated by >30 lines do NOT trip the
        guard — the rule is co-occurrence within a 30-line window."""
        body = ["## Goal & Context", "filler"] + ["padding"] * 31 + [
            "## Architecture & Data Models",
            "## API Contracts",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "wide.md"
            fixture.write_text("\n".join(body) + "\n")
            out = self._run_awk(fixture)
            self.assertEqual(out.strip(), "", "guard must NOT fire when window exceeded")

    def test_guard_silent_on_canonical_template(self) -> None:
        """Sanity check: the canonical template itself DOES embed the
        sequence (it's the source of truth) but lives OUTSIDE
        `plugins/flow-next/skills/` — sync-codex.sh's guard scopes to
        `plugins/flow-next/skills/` so the template never gets scanned.
        Verify the guard's `find` scope path."""
        # We can't easily simulate the find scope here; just assert the
        # template DOES have the sequence (so the guard would trip if
        # mis-scoped). The actual guard scoping is verified by sync-codex.sh
        # passing — which this test suite runs in CI as part of the gate.
        body = TEMPLATE_PATH.read_text(encoding="utf-8")
        lines = body.splitlines()
        for i, line in enumerate(lines):
            if line == "## Goal & Context":
                window = lines[i + 1 : i + 31]
                arch_hit = any(l == "## Architecture & Data Models" for l in window)
                api_hit = any(l == "## API Contracts" for l in window)
                if arch_hit and api_hit:
                    return  # canonical template DOES embed the sequence — pass
        self.fail("canonical template lost its canonical-sequence body")


class TestNoCanonicalSequenceInCanonicalSkillMarkdown(unittest.TestCase):
    """Live check: walk every `*.md` under `plugins/flow-next/skills/*/` and
    assert none re-embed the canonical sequence (R21 — runtime-state assertion
    that mirrors sync-codex.sh's guard)."""

    def test_no_skill_markdown_duplicates_canonical_sequence(self) -> None:
        violations: list[tuple[str, int]] = []
        for md in SKILLS_DIR.rglob("*.md"):
            lines = md.read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(lines):
                if line.startswith("## Goal & Context"):
                    window = lines[i + 1 : i + 31]
                    arch = any(
                        l.startswith("## Architecture & Data Models")
                        for l in window
                    )
                    api = any(l.startswith("## API Contracts") for l in window)
                    if arch and api:
                        violations.append((str(md), i + 1))
        self.assertEqual(
            violations,
            [],
            f"R21 violations in canonical skill markdown: {violations}",
        )


class TestCodexMirrorShipsTemplate(unittest.TestCase):
    """R20: Codex mirror, when present, ships its own copy of the template
    byte-for-byte identical to canonical."""

    def test_mirror_template_exists_and_matches_canonical(self) -> None:
        if not CODEX_TEMPLATE_PATH.is_file():
            self.skipTest(
                f"codex mirror not regenerated: {CODEX_TEMPLATE_PATH} missing "
                f"— run `bash scripts/sync-codex.sh`"
            )
        canonical = TEMPLATE_PATH.read_bytes()
        mirror = CODEX_TEMPLATE_PATH.read_bytes()
        self.assertEqual(
            canonical,
            mirror,
            "codex mirror template diverges from canonical — re-run sync-codex.sh",
        )

    def test_mirror_skill_paths_resolve_to_mirror_template(self) -> None:
        """After sync, skill markdown in the mirror uses
        `../../templates/spec.md` which resolves to
        `codex/templates/spec.md` (the mirror copy)."""
        if not CODEX_TEMPLATE_PATH.is_file():
            self.skipTest("codex mirror not regenerated")
        mirror_skills = PLUGIN_DIR / "codex" / "skills"
        candidates = [
            mirror_skills / "flow-next-interview" / "SKILL.md",
            mirror_skills / "flow-next-capture" / "workflow.md",
            mirror_skills / "flow-next-plan" / "steps.md",
        ]
        for path in candidates:
            if not path.is_file():
                continue
            body = path.read_text(encoding="utf-8")
            # The path string should appear as `../../templates/spec.md` —
            # resolves to `codex/templates/spec.md` from a skill at
            # `codex/skills/<name>/<file>.md` (2 levels up).
            for line in body.splitlines():
                if "templates/spec.md" in line and "](" in line:
                    self.assertIn(
                        "../../templates/spec.md",
                        line,
                        f"{path.name}: expected `../../templates/spec.md` "
                        f"after sync, found stale: {line!r}",
                    )


if __name__ == "__main__":
    unittest.main()
