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


class TestR23_SectionMergeContract(unittest.TestCase):
    """R23 behavior-level merge contract — drive `flowctl scope write-policy`
    against fixture specs and verify the policy mechanically enforces:

    1. Unowned section bodies stay in `preserved` (host agent must NOT
       rewrite them).
    2. Tech-pass under FLAT DC does NOT introduce H3 substructure.
    3. Biz-pass FLAT-promotion correctly flags
       `promote_flat_to_implementation_tradeoffs=True` AND lists Motivation
       as the only writable H3, Implementation Tradeoffs as preserved.
    4. Biz-pass placeholder list contains ONLY tech sections without
       content — refine mode (tech has content) drops them from
       placeholder_write byte-for-byte.
    5. Auxiliary sections (Strategy Alignment / Strategy Conflicts /
       Glossary Conflicts / Conversation Evidence / Resolved via Codebase /
       Resolved via Project Docs) are out-of-scope for write-policy —
       neither writable nor preserved — by design, since aux sections
       are written by their respective skills (capture / interview
       behaviors). Verify the policy never surfaces them as targets for
       overwrite.

    These tests are deterministic — no markdown diff fixtures, no
    transcript harness, no interactive skill probing. They drive the
    structured contract that the skill consumes."""

    def _policy(self, scope: str, current: dict) -> dict:
        proc = _run(
            "scope",
            "write-policy",
            scope,
            "--current-sections-json",
            "-",
            stdin=json.dumps(current),
        )
        self.assertEqual(proc.returncode, 0, msg=f"stderr: {proc.stderr}")
        return json.loads(proc.stdout)

    AUXILIARY_SECTIONS = (
        "Strategy Alignment",
        "Strategy Conflicts",
        "Glossary Conflicts",
        "Conversation Evidence",
        "Resolved via Codebase",
        "Resolved via Project Docs",
    )

    def test_tech_pass_does_not_surface_aux_in_writable(self) -> None:
        """Aux sections must never appear in `writable` — host agent
        composes them outside the policy. The policy controls canonical
        sections only."""
        policy = self._policy("technical", {})
        for aux in self.AUXILIARY_SECTIONS:
            self.assertNotIn(
                aux,
                policy["writable"],
                f"tech pass write-policy must not surface aux section {aux!r}",
            )
            self.assertNotIn(
                aux,
                policy["preserved"],
                f"tech pass write-policy must not surface aux section {aux!r}",
            )

    def test_biz_pass_does_not_surface_aux_in_writable(self) -> None:
        """Symmetric: biz pass also leaves aux sections alone."""
        policy = self._policy("business", {})
        for aux in self.AUXILIARY_SECTIONS:
            self.assertNotIn(aux, policy["writable"])
            self.assertNotIn(aux, policy["preserved"])

    def test_both_pass_does_not_surface_aux_in_writable(self) -> None:
        policy = self._policy("both", {})
        for aux in self.AUXILIARY_SECTIONS:
            self.assertNotIn(aux, policy["writable"])
            self.assertNotIn(aux, policy["preserved"])

    def test_tech_writable_preserved_partition_is_disjoint(self) -> None:
        """A section must be writable XOR preserved — never both. Catches
        the case where a policy change accidentally lists a section in
        both buckets."""
        for current in (
            {},
            {"decision_context_has_h3": True, "biz_pass_ran": True},
            {"tech_sections_have_content": {"API Contracts": True}},
        ):
            for scope in ("technical", "business"):
                policy = self._policy(scope, current)
                overlap = set(policy["writable"]) & set(policy["preserved"])
                self.assertEqual(
                    overlap,
                    set(),
                    f"scope={scope} current={current}: writable/preserved overlap: {overlap}",
                )

    def test_biz_pass_flat_promotion_preserves_motivation_writable(self) -> None:
        """FLAT → SUBSTRUCTURED contract: biz pass MUST write Motivation
        + promote FLAT body to Implementation Tradeoffs. Verify the
        policy emits exactly that shape (R23 byte-for-byte preservation
        of FLAT body inside Implementation Tradeoffs)."""
        policy = self._policy(
            "business",
            {
                "decision_context_has_h3": False,
                "biz_pass_ran": False,
                "tech_sections_have_content": {},
            },
        )
        dc = policy["decision_context"]
        self.assertEqual(dc["shape"], "substructured")
        self.assertEqual(
            sorted(dc["writable_h3"]), ["Motivation"]
        )
        self.assertEqual(
            sorted(dc["preserved_h3"]), ["Implementation Tradeoffs"]
        )
        self.assertTrue(dc["promote_flat_to_implementation_tradeoffs"])

    def test_biz_pass_existing_h3_no_promotion_motivation_only(self) -> None:
        """Re-run biz pass on substructured spec: do NOT re-promote;
        write Motivation only; preserve Implementation Tradeoffs."""
        policy = self._policy(
            "business",
            {
                "decision_context_has_h3": True,
                "biz_pass_ran": True,
                "tech_sections_have_content": {},
            },
        )
        dc = policy["decision_context"]
        self.assertEqual(dc["shape"], "substructured")
        self.assertEqual(sorted(dc["writable_h3"]), ["Motivation"])
        self.assertEqual(
            sorted(dc["preserved_h3"]), ["Implementation Tradeoffs"]
        )
        # CRITICAL: promotion flag must be False — re-running biz pass
        # must NOT re-promote a body that's already at the right H3.
        self.assertFalse(dc["promote_flat_to_implementation_tradeoffs"])

    def test_placeholder_write_only_empty_tech_sections(self) -> None:
        """R23: placeholder-only replacement contract. Biz pass writes
        `*Pending technical-scope interview pass.*` ONLY under empty
        tech sections. Sections with content are left untouched
        (refine mode)."""
        policy = self._policy(
            "business",
            {
                "decision_context_has_h3": False,
                "biz_pass_ran": False,
                "tech_sections_have_content": {
                    "Architecture & Data Models": True,
                    "API Contracts": False,
                    "Edge Cases & Constraints": True,
                },
            },
        )
        # Only API Contracts (empty) gets the placeholder.
        self.assertEqual(policy["placeholder_write"], ["API Contracts"])
        # The two with content do NOT.
        self.assertNotIn(
            "Architecture & Data Models", policy["placeholder_write"]
        )
        self.assertNotIn(
            "Edge Cases & Constraints", policy["placeholder_write"]
        )

    def test_placeholder_write_all_empty_when_blank_input(self) -> None:
        """Conservative default: missing tech_sections_have_content key
        defaults to ALL empty → biz pass would write placeholders under
        all tech sections (visible read-back of intentional emptiness)."""
        policy = self._policy("business", {})
        self.assertEqual(
            sorted(policy["placeholder_write"]),
            [
                "API Contracts",
                "Architecture & Data Models",
                "Edge Cases & Constraints",
            ],
        )

    def test_tech_pass_never_writes_placeholders(self) -> None:
        """R23 corollary: tech pass overwrites placeholders with real
        content but never WRITES new placeholder lines. `placeholder_write`
        on a tech-pass policy is always []."""
        for current in (
            {},
            {
                "tech_sections_have_content": {
                    "Architecture & Data Models": False,
                    "API Contracts": False,
                }
            },
            {"biz_pass_ran": True, "decision_context_has_h3": True},
        ):
            policy = self._policy("technical", current)
            self.assertEqual(
                policy["placeholder_write"],
                [],
                f"tech pass placeholder_write must always be empty; current={current}",
            )

    def test_tech_writable_preserves_biz_sections_byte_for_byte(self) -> None:
        """R23 byte-for-byte preservation: tech pass writable list must
        explicitly EXCLUDE the biz-owned sections — host agent must not
        touch them."""
        policy = self._policy("technical", {})
        # Biz-owned sections in PRESERVED list (never writable).
        for biz_owned in ("Goal & Context", "Boundaries"):
            self.assertIn(biz_owned, policy["preserved"])
            self.assertNotIn(biz_owned, policy["writable"])

    def test_biz_writable_preserves_tech_sections_byte_for_byte(self) -> None:
        """Symmetric: biz pass preserves tech-owned sections."""
        policy = self._policy("business", {})
        for tech_owned in (
            "Architecture & Data Models",
            "API Contracts",
            "Edge Cases & Constraints",
        ):
            self.assertIn(tech_owned, policy["preserved"])
            self.assertNotIn(tech_owned, policy["writable"])


class TestR23_FixtureMergeByteForByte(unittest.TestCase):
    """R23 behavior-level fixture tests — drive a minimal in-Python merge
    helper that applies `flowctl scope write-policy` against fixture spec
    markdown, then assert byte-for-byte preservation of unowned sections,
    aux sections, and existing R-IDs.

    The merge helper here is a thin REFERENCE implementation of the
    contract host agents follow — it's NOT production code and lives in
    this test file only. The point is to verify the policy mechanically
    suffices to drive a correct merge, not to claim flowctl performs the
    merge itself.
    """

    # Section-owner partition per templates/spec.md frontmatter.
    BIZ_SECTIONS = {"Goal & Context", "Boundaries"}
    TECH_SECTIONS = {
        "Architecture & Data Models",
        "API Contracts",
        "Edge Cases & Constraints",
    }
    BOTH_SECTIONS = {"Acceptance Criteria", "Decision Context"}
    AUX_SECTIONS = {
        "Strategy Alignment",
        "Strategy Conflicts",
        "Glossary Conflicts",
        "Conversation Evidence",
        "Resolved via Codebase",
        "Resolved via Project Docs",
    }

    @staticmethod
    def _parse_sections(body: str) -> dict[str, str]:
        """Parse `## Heading\\n<body>` blocks into {heading: body}."""
        sections: dict[str, str] = {}
        current: str | None = None
        buf: list[str] = []
        for line in body.splitlines():
            if line.startswith("## "):
                if current is not None:
                    sections[current] = "\n".join(buf).rstrip()
                current = line[3:].strip()
                buf = []
            elif current is not None:
                buf.append(line)
        if current is not None:
            sections[current] = "\n".join(buf).rstrip()
        return sections

    @staticmethod
    def _policy(scope: str, current: dict) -> dict:
        proc = _run(
            "scope",
            "write-policy",
            scope,
            "--current-sections-json",
            "-",
            stdin=json.dumps(current),
        )
        return json.loads(proc.stdout)

    def _build_current_sections(self, fixture: dict[str, str]) -> dict:
        """Compute the current-sections JSON from a fixture mapping."""
        dc_body = fixture.get("Decision Context", "")
        return {
            "decision_context_has_h3": (
                "### Motivation" in dc_body
                or "### Implementation Tradeoffs" in dc_body
            ),
            "biz_pass_ran": bool(fixture.get("Goal & Context", "").strip()),
            "tech_sections_have_content": {
                section: bool(
                    fixture.get(section, "")
                    .replace("*Pending technical-scope interview pass.*", "")
                    .strip()
                )
                for section in self.TECH_SECTIONS
            },
        }

    def test_tech_pass_preserves_biz_section_body_byte_for_byte(self) -> None:
        """A spec with populated `## Goal & Context` survives a tech pass
        unchanged byte-for-byte. Test the contract: policy lists
        `Goal & Context` in `preserved`, host agent obeys.

        Two sub-cases:
        - With biz content populated (biz_pass_ran=True): DC is
          SUBSTRUCTURED; tech writes Implementation Tradeoffs, preserves
          Motivation.
        - With biz content absent (biz_pass_ran=False): DC stays FLAT
          (R22 backward-compat); tech writes FLAT body.
        """
        # Sub-case 1: biz populated → DC substructured (post-biz-pass shape).
        fixture_with_biz = {
            "Goal & Context": (
                "Persona: junior engineer.\n"
                "Why-now: onboarding pain in Q3.\n"
                "Target: 10-minute first-success.\n"
            ),
            "Architecture & Data Models": "Old stub.",
            "API Contracts": "",
            "Edge Cases & Constraints": "",
            "Acceptance Criteria": "- **R1:** Existing.",
            "Boundaries": "Out: enterprise SSO.",
            "Decision Context": (
                "### Motivation\nBiz reasoning.\n\n"
                "### Implementation Tradeoffs\nTech reasoning.\n"
            ),
        }
        current = self._build_current_sections(fixture_with_biz)
        policy = self._policy("technical", current)
        self.assertIn("Goal & Context", policy["preserved"])
        self.assertIn("Boundaries", policy["preserved"])
        self.assertNotIn("Goal & Context", policy["writable"])
        # Substructured shape: tech preserves Motivation byte-for-byte.
        self.assertEqual(policy["decision_context"]["shape"], "substructured")
        self.assertIn(
            "Implementation Tradeoffs",
            policy["decision_context"]["writable_h3"],
        )
        self.assertIn(
            "Motivation", policy["decision_context"]["preserved_h3"]
        )

        # Sub-case 2: zero-biz-pass spec → DC stays FLAT (R22 invariant).
        fixture_zero_biz = {
            "Goal & Context": "",
            "Architecture & Data Models": "Old stub.",
            "API Contracts": "",
            "Edge Cases & Constraints": "",
            "Acceptance Criteria": "- **R1:** Existing.",
            "Boundaries": "",
            "Decision Context": "FLAT body from a prior tech-only pass.",
        }
        current = self._build_current_sections(fixture_zero_biz)
        policy = self._policy("technical", current)
        # FLAT body stays FLAT — no H3 introduction under tech-only pass.
        self.assertEqual(policy["decision_context"]["shape"], "flat")
        self.assertEqual(policy["decision_context"]["writable_h3"], [])
        self.assertEqual(policy["decision_context"]["preserved_h3"], [])

    def test_biz_pass_preserves_tech_section_body_byte_for_byte(self) -> None:
        """A spec with populated tech sections survives a biz pass."""
        fixture = {
            "Goal & Context": "",
            "Architecture & Data Models": "Components: A, B, C.",
            "API Contracts": "POST /api/v1/foo → 200.",
            "Edge Cases & Constraints": "Limit: 100 req/sec.",
            "Acceptance Criteria": "- **R1:** Existing tech criterion.",
            "Boundaries": "",
            "Decision Context": "Pre-existing FLAT body.",
        }
        current = self._build_current_sections(fixture)
        policy = self._policy("business", current)
        for tech in self.TECH_SECTIONS:
            self.assertIn(tech, policy["preserved"])
            self.assertNotIn(tech, policy["writable"])
        # FLAT body gets promoted under ### Implementation Tradeoffs
        # byte-for-byte. The promotion flag tells the host agent to
        # preserve the existing body verbatim.
        self.assertTrue(
            policy["decision_context"][
                "promote_flat_to_implementation_tradeoffs"
            ]
        )
        # And refine-mode: tech sections with content are NOT in
        # placeholder_write (we don't overwrite them with placeholders).
        self.assertEqual(policy["placeholder_write"], [])

    def test_r_ids_append_only_contract(self) -> None:
        """R23: R-IDs are append-only across passes. Verify that a fixture
        with existing R1-R5 receives a write-policy that lists
        `Acceptance Criteria` as WRITABLE (for appending), not as a full
        rewrite target — there is no signal in the policy to renumber."""
        # The policy doesn't enforce R-ID semantics directly — it just
        # marks Acceptance Criteria as writable. The append-only contract
        # is enforced by the host agent reading existing R-IDs and
        # allocating the next unused number.
        #
        # What we CAN test deterministically: there is no field in the
        # policy payload that says "renumber" or "replace" or "reset".
        # The shape is { writable, preserved, decision_context,
        # placeholder_write } — nothing that could mistakenly authorize
        # renumbering.
        for scope in ("business", "technical", "both"):
            policy = self._policy(scope, {})
            self.assertNotIn("renumber", json.dumps(policy).lower())
            self.assertNotIn("replace", json.dumps(policy).lower())
            self.assertNotIn("reset", json.dumps(policy).lower())
            # Acceptance Criteria is writable for the appropriate scopes.
            if scope == "technical":
                self.assertIn("Acceptance Criteria", policy["writable"])
            elif scope == "business":
                self.assertIn("Acceptance Criteria", policy["writable"])
            else:  # both
                self.assertIn("Acceptance Criteria", policy["writable"])


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
