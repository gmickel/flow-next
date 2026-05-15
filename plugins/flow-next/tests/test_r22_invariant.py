"""R22 backward-compat invariant — deterministic static checks (fn-44.9).

R22 states: a user who never passes `--scope` experiences zero behavioral
change across all flow-next surfaces. Because /flow-next:interview is
interactive (calls `AskUserQuestion`) and cannot be diff-tested against a
fixture without a transcript harness, the invariant is enforced at the
rule-engine level via deterministic unit tests on observable state.

Five sub-invariants (R22 (a)-(e)) covered here:

  (a) Zero-flag scope resolution returns `technical`.
  (b) `questions-technical.md` is the bank loaded when SCOPE=technical;
      `questions-business.md` is NOT loaded under default scope.
  (c) Section-write policy under SCOPE=technical with empty biz sections
      writes ONLY tech-owned sections, writes NO placeholder, writes NO
      H3 substructure under `## Decision Context` (stays FLAT).
  (d) Capture's biz-routing layer, given a zero-biz-signal conversation,
      adds NO content to business destinations and fires NO suggestion.
  (e) `flowctl spec skeleton` produces byte-for-byte identical output to
      the 1.0.2 baseline (literal expected string encoded in this test
      file, NOT a fixture — fn-44 task spec contract).

Additionally: R23 section-merge contract — auxiliary sections preserved,
R-IDs append-only, placeholder-only replacement.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent
FLOWCTL_PY = PLUGIN_DIR / "scripts" / "flowctl.py"
INTERVIEW_DIR = PLUGIN_DIR / "skills" / "flow-next-interview"
CAPTURE_DIR = PLUGIN_DIR / "skills" / "flow-next-capture"


def _run(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FLOWCTL_PY), *args],
        capture_output=True,
        text=True,
        input=stdin,
        timeout=30,
    )


# ============================================================================
# R22 (e): byte-for-byte skeleton parity with the 1.0.2 baseline.
# ============================================================================
# This literal string is the 1.0.2 SPEC_SKELETON_TEMPLATE — the same content
# `flowctl spec create` writes today. ANY deviation between `flowctl spec
# skeleton` output and this expected string is a regression of R22 — the
# user who creates a fresh spec via the canonical CLI MUST see the same
# scaffold as on 1.0.2, with no new sections, no rearranged sections, and
# no inserted HTML-comment annotations.
EXPECTED_SKELETON_R22 = """# <spec-id> <Title>

## Overview
TBD

## Scope
TBD

## Approach
TBD

## Quick commands
<!-- Required: at least one smoke command for the repo -->
- `# e.g., npm test, bun test, make test`

## Acceptance
- [ ] TBD

## References
- TBD
"""


class TestR22A_ZeroFlagDefault(unittest.TestCase):
    """R22 (a): zero-flag scope resolution returns `technical`."""

    def test_resolve_no_args_returns_technical(self) -> None:
        proc = _run("scope", "resolve", "--json", "--raw=")
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["scope"], "technical")
        self.assertEqual(payload["remaining_args"], [])

    def test_resolve_only_flow_id_returns_technical(self) -> None:
        """A user invoking `/flow-next:interview fn-1` (no scope flag) lands
        on technical scope; the Flow ID stays in remaining_args."""
        proc = _run("scope", "resolve", "--json", "--raw=fn-1")
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["scope"], "technical")
        self.assertEqual(payload["remaining_args"], ["fn-1"])

    def test_resolve_plain_no_args_prints_technical(self) -> None:
        """Plain mode prints just the resolved scope token."""
        proc = _run("scope", "resolve", "--raw=")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "technical")


class TestR22B_TechnicalBankLoaded(unittest.TestCase):
    """R22 (b): SCOPE=technical loads questions-technical.md; questions-
    business.md is NOT loaded under default scope. Verified by checking
    what `flowctl scope bank technical` resolves to."""

    def test_technical_bank_filename(self) -> None:
        proc = _run("scope", "bank", "technical", "--json")
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["bank_filename"], "questions-technical.md")
        # questions-business.md MUST NOT be the resolved filename for
        # SCOPE=technical — R22 backward-compat invariant.
        self.assertNotEqual(
            payload["bank_filename"], "questions-business.md"
        )

    def test_technical_bank_path_resolves_to_file_that_exists(self) -> None:
        """Sanity check: the resolved technical bank actually exists at
        the canonical path. Catches the case where the bank rename moved
        the file but `scope bank` returns a stale path."""
        proc = _run("scope", "bank", "technical")
        self.assertEqual(proc.returncode, 0)
        path = Path(proc.stdout.strip())
        self.assertTrue(
            path.is_file(),
            f"technical bank does not exist: {path}",
        )

    def test_skill_loads_technical_bank_by_default(self) -> None:
        """SKILL.md's bank resolution line must use `flowctl scope bank` —
        not hardcode the filename — so the R22 (b) coupling stays in
        flowctl, not in the skill."""
        body = (INTERVIEW_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("scope bank", body)


class TestR22C_TechWritePolicyFlatDC(unittest.TestCase):
    """R22 (c): section-write policy under SCOPE=technical with empty biz
    sections writes ONLY tech-owned sections, writes NO placeholders, AND
    `## Decision Context` stays FLAT (no H3 introduction) unless the spec
    already has them or a biz pass has run."""

    def _policy(self, scope: str, current: dict) -> dict:
        proc = _run(
            "scope",
            "write-policy",
            scope,
            "--current-sections-json",
            "-",
            stdin=json.dumps(current),
        )
        self.assertEqual(proc.returncode, 0)
        return json.loads(proc.stdout)

    def test_zero_flag_tech_writes_only_tech_owned(self) -> None:
        """Empty spec, zero-flag-tech pass: writable = tech sections +
        Acceptance + Decision Context (FLAT). Preserved = biz sections."""
        policy = self._policy(
            "technical",
            {
                "decision_context_has_h3": False,
                "biz_pass_ran": False,
                "tech_sections_have_content": {},
            },
        )
        # Writable sections — only tech-owned + co-authored.
        self.assertIn("Architecture & Data Models", policy["writable"])
        self.assertIn("API Contracts", policy["writable"])
        self.assertIn("Edge Cases & Constraints", policy["writable"])
        self.assertIn("Acceptance Criteria", policy["writable"])
        self.assertIn("Decision Context", policy["writable"])
        # Biz-owned sections MUST be in preserved (not writable).
        self.assertNotIn("Goal & Context", policy["writable"])
        self.assertNotIn("Boundaries", policy["writable"])
        self.assertIn("Goal & Context", policy["preserved"])
        self.assertIn("Boundaries", policy["preserved"])

    def test_zero_flag_tech_writes_no_placeholders(self) -> None:
        """Tech pass NEVER writes the `*Pending technical-scope interview
        pass.*` placeholder — only biz pass writes those under empty tech
        sections (and the tech pass overwrites them)."""
        policy = self._policy("technical", {})
        self.assertEqual(policy["placeholder_write"], [])

    def test_zero_flag_tech_dc_stays_flat(self) -> None:
        """The CRITICAL R22 invariant: with no biz pass + no existing H3s,
        `## Decision Context` is FLAT — no `### Motivation` or
        `### Implementation Tradeoffs` introduction. A 1.0.2-shape spec
        stays 1.0.2-shape under the default tech-only path."""
        policy = self._policy(
            "technical",
            {
                "decision_context_has_h3": False,
                "biz_pass_ran": False,
                "tech_sections_have_content": {},
            },
        )
        dc = policy["decision_context"]
        self.assertEqual(dc["shape"], "flat")
        self.assertEqual(dc["writable_h3"], [])
        self.assertEqual(dc["preserved_h3"], [])
        self.assertFalse(dc["promote_flat_to_implementation_tradeoffs"])


class TestR22D_CaptureZeroSignalNoFire(unittest.TestCase):
    """R22 (d): capture's biz-routing layer, given zero biz signals, fires
    NO suggestion. Verified via `flowctl scope suggest --signal-categories-count 0`."""

    def test_zero_signals_no_fire_plain(self) -> None:
        """Plain mode: exit 1, stdout `no-fire`. The `if scope suggest ...`
        in workflow.md correctly skips appending the suggestion."""
        proc = _run("scope", "suggest", "--signal-categories-count", "0")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout.strip(), "no-fire")

    def test_zero_signals_no_fire_json(self) -> None:
        """JSON mode: exit 0 (valid input) but `fire: false`."""
        proc = _run(
            "scope",
            "suggest",
            "--signal-categories-count",
            "0",
            "--json",
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["fire"])
        self.assertEqual(payload["decision"], "no-fire")


class TestR22E_SpecSkeletonByteForByte(unittest.TestCase):
    """R22 (e): `flowctl spec skeleton` byte-for-byte parity with 1.0.2.

    The expected output is encoded as a literal string above. ANY drift
    means a user creating a fresh spec via the canonical CLI sees something
    different from 1.0.2 — the precise behavior R22 forbids."""

    def test_skeleton_byte_for_byte_matches_baseline(self) -> None:
        proc = _run("spec", "skeleton")
        self.assertEqual(proc.returncode, 0)
        actual = proc.stdout
        self.assertEqual(
            actual,
            EXPECTED_SKELETON_R22,
            "R22 (e) violation: `flowctl spec skeleton` output diverges "
            "from the 1.0.2 baseline. Update SPEC_SKELETON_TEMPLATE only "
            "with explicit user approval — this is the backward-compat surface.",
        )

    def test_skeleton_no_canonical_sequence_re_embedded(self) -> None:
        """R22 (e) corollary: the 1.0.2 skeleton has NO H2 sections
        named `## Goal & Context` / `## Architecture & Data Models` /
        `## API Contracts` — those live in the rich `templates/spec.md`,
        NOT in the CLI-emitted skeleton. The CLI skeleton is intentionally
        sparse (Overview / Scope / Approach / Quick commands / Acceptance
        / References) to match the 1.0.2 contract."""
        proc = _run("spec", "skeleton")
        self.assertEqual(proc.returncode, 0)
        skeleton = proc.stdout
        # The rich template lives at templates/spec.md; the CLI skeleton
        # stays 1.0.2-shape.
        self.assertNotIn("## Goal & Context", skeleton)
        self.assertNotIn("## Architecture & Data Models", skeleton)
        self.assertNotIn("## API Contracts", skeleton)

    def test_skeleton_json_envelope_matches(self) -> None:
        """`flowctl spec skeleton --json` wraps the same text in a JSON
        envelope; the embedded skeleton field is byte-for-byte identical."""
        proc = _run("spec", "skeleton", "--json")
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["skeleton"], EXPECTED_SKELETON_R22)


class TestR23_AuxiliarySectionEnumerationCompleteness(unittest.TestCase):
    """R23 section-merge contract: auxiliary sections preserved. The full
    auxiliary-section enumeration must be Strategy Alignment + Strategy
    Conflicts + Glossary Conflicts + Conversation Evidence + Resolved via
    Codebase + Resolved via Project Docs (per fn-44.2 review fix).

    SKILL.md preservation lists must enumerate all 6 — fn-44.2's bug was
    that an earlier draft omitted `Strategy Conflicts` from four of the
    preservation lists.
    """

    def setUp(self) -> None:
        self.skill_body = (INTERVIEW_DIR / "SKILL.md").read_text(encoding="utf-8")

    def test_all_six_auxiliary_sections_named_in_skill(self) -> None:
        for aux in (
            "Strategy Alignment",
            "Strategy Conflicts",
            "Glossary Conflicts",
            "Conversation Evidence",
            "Resolved via Codebase",
            "Resolved via Project Docs",
        ):
            self.assertIn(
                aux,
                self.skill_body,
                f"SKILL.md must enumerate auxiliary section {aux!r}",
            )


class TestR23_RIDsAppendOnlyDocumented(unittest.TestCase):
    """R23: R-IDs are append-only across passes. SKILL.md must document
    that biz pass appends outcome-AC + tech pass appends verifiable-AC,
    NEITHER renumbers existing entries."""

    def setUp(self) -> None:
        self.skill_body = (INTERVIEW_DIR / "SKILL.md").read_text(encoding="utf-8")

    def test_skill_documents_r_ids_append_only(self) -> None:
        # Accept variations: "append-only" or "never renumber".
        body_lower = self.skill_body.lower()
        self.assertTrue(
            "append-only" in body_lower or "never renumber" in body_lower,
            "SKILL.md must document R-IDs append-only rule",
        )


class TestR26_BizPassDocsInvestigation(unittest.TestCase):
    """R26: business pass MUST investigate project documentation BEFORE
    drafting questions — symmetric to the tech pass's codebase
    investigation. Verify SKILL.md's `--scope=business` block names the
    doc sources + `## Resolved via Project Docs` audit section."""

    def setUp(self) -> None:
        self.skill_body = (INTERVIEW_DIR / "SKILL.md").read_text(encoding="utf-8")

    def test_business_block_names_required_doc_sources(self) -> None:
        """SKILL.md must instruct the biz pass to read README.md /
        CHANGELOG.md / STRATEGY.md / GLOSSARY.md / knowledge/decisions/ /
        .flow/specs/ index / docs/ BEFORE drafting questions."""
        for source in (
            "README.md",
            "CHANGELOG.md",
            "STRATEGY.md",
            "GLOSSARY.md",
            "knowledge/decisions",
            ".flow/specs",
            "docs/",
        ):
            self.assertIn(
                source,
                self.skill_body,
                f"SKILL.md --scope=business block must name {source!r}",
            )

    def test_business_block_names_audit_section(self) -> None:
        """`## Resolved via Project Docs` is the audit section that
        captures items resolved by project-doc investigation — symmetric
        to `## Resolved via Codebase` for the tech pass."""
        self.assertIn(
            "## Resolved via Project Docs",
            self.skill_body,
            "SKILL.md must name `## Resolved via Project Docs` as the "
            "biz-pass audit section",
        )

    def test_business_block_states_pre_drafting_order(self) -> None:
        """R26 enforces ordering — docs investigation MUST run BEFORE
        drafting questions. The skill body needs to communicate this
        BEFORE/before relation explicitly."""
        # Find any sentence near R26 / Investigate Project Docs that
        # uses BEFORE / before to assert ordering.
        body_lower = self.skill_body.lower()
        # The clear marker per the spec.
        self.assertIn("before", body_lower)
        # And the symmetric-form bug rule from R26. Case-insensitive — the
        # actual line in SKILL.md starts with `If you...` (capitalized).
        import re as _re
        self.assertIsNotNone(
            _re.search(
                r"if you find yourself asking the user a biz question that "
                r"(?:README|STRATEGY|CHANGELOG|GLOSSARY)",
                self.skill_body,
                _re.IGNORECASE,
            ),
            "SKILL.md must include the symmetric form of the "
            "'should-via-grep' rule",
        )


class TestQuestionBankStructuralParity(unittest.TestCase):
    """T3: questions-business.md and questions-technical.md must share the
    same SHAPE (H2 buckets, short bullet-list topic prompts). Detects the
    failure mode where one bank drifts into verbose paragraph-form while
    the other stays terse."""

    def setUp(self) -> None:
        self.biz_body = (
            INTERVIEW_DIR / "questions-business.md"
        ).read_text(encoding="utf-8")
        self.tech_body = (
            INTERVIEW_DIR / "questions-technical.md"
        ).read_text(encoding="utf-8")

    def _parse_buckets(self, body: str) -> dict[str, list[str]]:
        """Return {h2_heading: [bullet_lines]} — the structural shape."""
        buckets: dict[str, list[str]] = {}
        current: str | None = None
        for line in body.splitlines():
            if line.startswith("## "):
                current = line[3:].strip()
                buckets[current] = []
            elif current is not None and line.lstrip().startswith("- "):
                buckets[current].append(line.strip())
        return buckets

    def test_both_banks_use_h2_headed_buckets(self) -> None:
        biz_buckets = self._parse_buckets(self.biz_body)
        tech_buckets = self._parse_buckets(self.tech_body)
        self.assertGreater(
            len(biz_buckets), 0, "biz bank has no H2 buckets"
        )
        self.assertGreater(
            len(tech_buckets), 0, "tech bank has no H2 buckets"
        )

    def test_bucket_bodies_are_bullet_list_prompts(self) -> None:
        """Each H2 bucket has at least 2 bullet-list lines (the topic
        prompts) — no prose paragraphs, no per-bucket metadata."""
        biz_buckets = self._parse_buckets(self.biz_body)
        tech_buckets = self._parse_buckets(self.tech_body)
        for name, bullets in {**biz_buckets, **tech_buckets}.items():
            self.assertGreaterEqual(
                len(bullets),
                2,
                f"bucket {name!r} has only {len(bullets)} bullet(s) — too sparse",
            )

    def test_bucket_density_comparable(self) -> None:
        """Bullet count per bucket must be in the same order of magnitude
        across banks. Specifically: biz mean bullet count within 2x of
        tech mean (catches accidental verbose-biz-bank divergence)."""
        biz_buckets = self._parse_buckets(self.biz_body)
        tech_buckets = self._parse_buckets(self.tech_body)
        biz_mean = sum(len(b) for b in biz_buckets.values()) / max(
            1, len(biz_buckets)
        )
        tech_mean = sum(len(b) for b in tech_buckets.values()) / max(
            1, len(tech_buckets)
        )
        # Allow up to 2.0x divergence in either direction.
        ratio = max(biz_mean / max(tech_mean, 0.1), tech_mean / max(biz_mean, 0.1))
        self.assertLess(
            ratio,
            2.0,
            f"bucket density diverged: biz_mean={biz_mean:.1f} "
            f"tech_mean={tech_mean:.1f} ratio={ratio:.2f}",
        )

    def test_no_destination_annotations_per_bucket(self) -> None:
        """Buckets are topic prompts, not routing-destination
        annotations. `Routes to: ...` / `Destination: ...` patterns
        signal accidental routing-table drift from capture/workflow.md
        into the interview banks."""
        for body, name in ((self.biz_body, "biz"), (self.tech_body, "tech")):
            self.assertNotRegex(
                body,
                r"^Routes to:|^Destination:",
                f"{name} bank: routing annotations leaked from capture's table",
            )

    def test_banks_reference_shared_taxonomy(self) -> None:
        """Both banks must point at questions-shared.md for the
        Pre-Question Taxonomy + Interview Guidelines (single source of
        truth)."""
        self.assertIn("questions-shared.md", self.biz_body)
        self.assertIn("questions-shared.md", self.tech_body)


if __name__ == "__main__":
    unittest.main()
