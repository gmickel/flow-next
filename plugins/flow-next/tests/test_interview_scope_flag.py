"""Unit tests for `flowctl scope` plumbing consumed by /flow-next:interview
(fn-44.9, covers R1-R3, R6-R9, R23 — scope flag parsing + per-pass write
policy contract).

Drives the production flowctl subcommands via subprocess (same surface
SKILL.md invokes). NO test-only helpers — runtime coupling between SKILL.md
and these tests via shared `flowctl scope resolve` / `flowctl scope bank` /
`flowctl scope write-policy`.

Coverage:

  - `flowctl scope resolve --json --raw "$ARGUMENTS"` parses every valid +
    conflicting form: zero-flag default, `--biz`, `--tech`, `--scope=business`,
    `--scope=technical`, `--scope=both`, `--biz --tech` (conflict),
    `--scope=foo` (invalid), `--scope=business --tech` (conflict). Quoted
    paths with spaces round-trip cleanly via shlex inside flowctl.
  - `flowctl scope bank <scope>` resolves to the expected bank filename per
    R4/R5 (questions-business.md vs questions-technical.md).
  - `flowctl scope write-policy <scope>` honors the per-pass merge contract
    from fn-44 spec Edge Cases:
      - biz pass writes biz-owned + Acceptance + Decision Context;
        preserves tech sections byte-for-byte; writes placeholder lines
        under EMPTY tech sections; promotes FLAT → SUBSTRUCTURED with
        `### Motivation` H3 (and FLAT body → `### Implementation Tradeoffs`).
      - tech pass writes tech-owned + Acceptance + Decision Context;
        preserves biz sections byte-for-byte; FLAT stays FLAT under
        zero-biz-pass conditions (R22 backward-compat invariant);
        SUBSTRUCTURED preserves `### Motivation` byte-for-byte, writes
        only `### Implementation Tradeoffs`.
      - both pass writes everything; computes biz policy first then re-
        computes for tech with biz-pass-ran state (TWO write-policy calls
        per the SKILL.md contract).
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


def _run(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FLOWCTL_PY), *args],
        capture_output=True,
        text=True,
        input=stdin,
        timeout=30,
    )


def _resolve(
    raw: str | None = None,
    *,
    json_mode: bool = True,
    fused: bool = False,
) -> dict:
    """Invoke `flowctl scope resolve --json --raw <raw>` and parse JSON.

    Default form (`fused=False`) is the TWO-TOKEN form `--raw VALUE` — the
    production path SKILL.md invokes via `"$FLOWCTL" scope resolve --json
    --raw "$ARGUMENTS"`. flowctl's pre-processing fuses this into
    `--raw=VALUE` before argparse so values that begin with `--` (e.g.,
    `--biz`, `--scope=business`) survive argparse's flag-detection.

    `fused=True` exercises the single-token form `--raw=VALUE` directly —
    redundant once flowctl's pre-processing fuses, but useful for
    regression coverage on the wire-format escape hatch.
    """
    cmd = ["scope", "resolve"]
    if json_mode:
        cmd.append("--json")
    if raw is not None:
        if fused:
            cmd.append(f"--raw={raw}")
        else:
            # Two-token form — what SKILL.md invokes in production.
            cmd.extend(["--raw", raw])
    proc = _run(*cmd)
    if json_mode:
        if proc.returncode not in (0, 2):
            raise AssertionError(
                f"unexpected exit {proc.returncode}: stderr={proc.stderr}"
            )
        try:
            return {"_rc": proc.returncode, **json.loads(proc.stdout)}
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"non-JSON output: stdout={proc.stdout!r} stderr={proc.stderr!r}"
            ) from exc
    return {
        "_rc": proc.returncode,
        "_stdout": proc.stdout.strip(),
        "_stderr": proc.stderr,
    }


class TestScopeResolveValidForms(unittest.TestCase):
    """R1 / R2: every valid flag form resolves to the expected scope; default
    is `technical` when no scope flag is passed (R22 backward-compat)."""

    def test_zero_flag_default_is_technical(self) -> None:
        # SKILL.md invocation: `--raw "$ARGUMENTS"` with `$ARGUMENTS=""`
        result = _resolve("")
        self.assertTrue(result["success"])
        self.assertEqual(result["scope"], "technical")
        self.assertEqual(result["remaining_args"], [])

    def test_zero_flag_reports_defaulted_true(self) -> None:
        """No scope flag → `defaulted: true` so the skill knows to ask the
        scope question instead of silently running the technical default."""
        result = _resolve("fn-1")
        self.assertTrue(result["success"])
        self.assertEqual(result["scope"], "technical")
        self.assertTrue(result["defaulted"])

    def test_explicit_flags_report_defaulted_false(self) -> None:
        for raw in ("--tech", "--biz", "--scope=technical", "--scope=both fn-1"):
            result = _resolve(raw)
            self.assertTrue(result["success"], raw)
            self.assertFalse(result["defaulted"], raw)

    def test_zero_flag_plain_default(self) -> None:
        """Plain (non-JSON) mode also defaults to `technical`."""
        result = _resolve("", json_mode=False)
        self.assertEqual(result["_rc"], 0)
        self.assertEqual(result["_stdout"], "technical")

    def test_biz_alias_resolves_to_business(self) -> None:
        result = _resolve("--biz")
        self.assertTrue(result["success"])
        self.assertEqual(result["scope"], "business")

    def test_tech_alias_resolves_to_technical(self) -> None:
        result = _resolve("--tech")
        self.assertTrue(result["success"])
        self.assertEqual(result["scope"], "technical")

    def test_scope_business_explicit(self) -> None:
        result = _resolve("--scope=business")
        self.assertTrue(result["success"])
        self.assertEqual(result["scope"], "business")

    def test_scope_technical_explicit(self) -> None:
        result = _resolve("--scope=technical")
        self.assertTrue(result["success"])
        self.assertEqual(result["scope"], "technical")

    def test_scope_both(self) -> None:
        result = _resolve("--scope=both")
        self.assertTrue(result["success"])
        self.assertEqual(result["scope"], "both")

    def test_preserves_other_tokens_in_order(self) -> None:
        """Flow IDs / paths / other flags pass through untouched."""
        result = _resolve("--biz fn-1 --docs")
        self.assertTrue(result["success"])
        self.assertEqual(result["scope"], "business")
        self.assertEqual(result["remaining_args"], ["fn-1", "--docs"])

    def test_preserves_quoted_path_with_spaces(self) -> None:
        """shlex tokenization inside flowctl preserves quoted paths."""
        result = _resolve('--biz "docs/my spec.md"')
        self.assertTrue(result["success"])
        self.assertEqual(result["scope"], "business")
        self.assertEqual(result["remaining_args"], ["docs/my spec.md"])


class TestScopeResolveProductionInvocationForm(unittest.TestCase):
    """Critical wire-form coverage — what SKILL.md ACTUALLY invokes via
    `"$FLOWCTL" scope resolve --json --raw "$ARGUMENTS"` (two-token form).
    Argparse rejects `--raw VALUE` when VALUE begins with `--`; flowctl's
    pre-processing fuses the two tokens before argparse sees them. Tests
    exercise the wire form, NOT the workaround.
    """

    def test_two_token_raw_biz_alone(self) -> None:
        """SKILL.md: `--raw "--biz"` (user typed `/flow-next:interview --biz`)
        — single-flag value, no other args. Must work via two-token form."""
        result = _resolve("--biz", fused=False)
        self.assertEqual(result["_rc"], 0)
        self.assertTrue(result["success"])
        self.assertEqual(result["scope"], "business")

    def test_two_token_raw_tech_alone(self) -> None:
        result = _resolve("--tech", fused=False)
        self.assertEqual(result["_rc"], 0)
        self.assertEqual(result["scope"], "technical")

    def test_two_token_raw_scope_business(self) -> None:
        """SKILL.md: `--raw "--scope=business"` — long form, leading `--`."""
        result = _resolve("--scope=business", fused=False)
        self.assertEqual(result["_rc"], 0)
        self.assertEqual(result["scope"], "business")

    def test_two_token_raw_scope_both(self) -> None:
        result = _resolve("--scope=both", fused=False)
        self.assertEqual(result["_rc"], 0)
        self.assertEqual(result["scope"], "both")

    def test_two_token_raw_scope_with_flow_id(self) -> None:
        """SKILL.md: `--raw "--scope=business fn-1"` — production case."""
        result = _resolve("--scope=business fn-1", fused=False)
        self.assertEqual(result["_rc"], 0)
        self.assertEqual(result["scope"], "business")
        self.assertEqual(result["remaining_args"], ["fn-1"])

    def test_two_token_raw_biz_with_flow_id(self) -> None:
        result = _resolve("--biz fn-1", fused=False)
        self.assertEqual(result["_rc"], 0)
        self.assertEqual(result["scope"], "business")
        self.assertEqual(result["remaining_args"], ["fn-1"])

    def test_two_token_raw_conflict_detected(self) -> None:
        """Conflict resolution works through the two-token form too."""
        result = _resolve("--biz --tech", fused=False)
        self.assertEqual(result["_rc"], 2)
        self.assertFalse(result["success"])
        self.assertIn("conflicting scope flags", result["error"])

    def test_two_token_raw_empty_value(self) -> None:
        """SKILL.md: `--raw ""` (zero-flag interview invocation)."""
        result = _resolve("", fused=False)
        self.assertEqual(result["_rc"], 0)
        self.assertEqual(result["scope"], "technical")

    def test_fused_form_still_works(self) -> None:
        """The single-token `--raw=VALUE` escape hatch still works — kept
        for backward compat with callers that might prefer it."""
        result = _resolve("--biz", fused=True)
        self.assertEqual(result["_rc"], 0)
        self.assertEqual(result["scope"], "business")


class TestScopeResolveConflicts(unittest.TestCase):
    """R3: every conflicting form errors with explicit message + non-zero exit
    (in both plain and JSON modes). JSON-mode errors go to stdout as a parseable
    error envelope; plain-mode errors go to stderr."""

    def _expect_conflict_json(self, raw: str, *fragments: str) -> None:
        result = _resolve(raw)
        self.assertNotEqual(result["_rc"], 0, "expected non-zero exit")
        self.assertFalse(result["success"])
        for fragment in fragments:
            self.assertIn(fragment, result["error"])

    def test_biz_tech_conflict(self) -> None:
        self._expect_conflict_json("--biz --tech", "conflicting scope flags")

    def test_scope_business_plus_tech_conflict(self) -> None:
        self._expect_conflict_json(
            "--scope=business --tech", "conflicting scope flags"
        )

    def test_scope_technical_plus_biz_conflict(self) -> None:
        self._expect_conflict_json(
            "--scope=technical --biz", "conflicting scope flags"
        )

    def test_scope_both_plus_biz_conflict(self) -> None:
        self._expect_conflict_json(
            "--scope=both --biz", "conflicting scope flags"
        )

    def test_invalid_scope_value(self) -> None:
        result = _resolve("--scope=foo")
        self.assertNotEqual(result["_rc"], 0)
        self.assertFalse(result["success"])
        self.assertIn("invalid --scope value", result["error"])

    def test_bare_scope_without_value_rejected(self) -> None:
        result = _resolve("--scope")
        self.assertNotEqual(result["_rc"], 0)
        self.assertFalse(result["success"])
        self.assertIn("--scope requires a value", result["error"])

    def test_plain_mode_error_goes_to_stderr(self) -> None:
        """Plain mode: error message on stderr, non-zero exit."""
        result = _resolve("--biz --tech", json_mode=False)
        self.assertNotEqual(result["_rc"], 0)
        self.assertIn("conflicting scope flags", result["_stderr"])


class TestScopeBank(unittest.TestCase):
    """R4 / R5: scope-to-bank-filename mapping."""

    def _bank(self, scope: str) -> dict:
        proc = _run("scope", "bank", scope, "--json")
        self.assertEqual(proc.returncode, 0, msg=f"stderr: {proc.stderr}")
        return json.loads(proc.stdout)

    def test_business_resolves_to_questions_business(self) -> None:
        payload = self._bank("business")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["bank_filename"], "questions-business.md")

    def test_technical_resolves_to_questions_technical(self) -> None:
        payload = self._bank("technical")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["bank_filename"], "questions-technical.md")

    def test_both_uses_technical_bank_path(self) -> None:
        """`both`-mode loads both banks at runtime; the path subcommand
        returns the technical filename (broader file). Biz phase loads
        questions-business.md separately."""
        payload = self._bank("both")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["bank_filename"], "questions-technical.md")

    def test_invalid_scope_errors(self) -> None:
        proc = _run("scope", "bank", "foo", "--json")
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["success"])
        self.assertIn("invalid scope", payload["error"])

    def test_bank_files_exist_at_resolved_paths(self) -> None:
        """T3 lands both bank files at the resolved paths."""
        for scope in ("business", "technical"):
            payload = self._bank(scope)
            path = Path(payload["path"])
            self.assertTrue(
                path.is_file(),
                f"{scope} bank path does not exist: {path}",
            )


class TestScopeWritePolicyTechPass(unittest.TestCase):
    """R7 / R8: tech pass writes only tech-owned sections; preserves biz
    sections byte-for-byte; FLAT stays FLAT under zero-biz-pass conditions
    (R22 backward-compat invariant)."""

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

    def test_tech_pass_empty_state_writes_tech_only(self) -> None:
        policy = self._policy("technical", {})
        # Tech-owned sections + Acceptance + Decision Context are writable.
        for section in (
            "Architecture & Data Models",
            "API Contracts",
            "Edge Cases & Constraints",
            "Acceptance Criteria",
            "Decision Context",
        ):
            self.assertIn(section, policy["writable"], section)
        # Biz sections are preserved.
        for section in ("Goal & Context", "Boundaries"):
            self.assertIn(section, policy["preserved"], section)
        # No placeholder writes by tech pass.
        self.assertEqual(policy["placeholder_write"], [])

    def test_tech_pass_flat_dc_stays_flat(self) -> None:
        """R22 invariant: zero-biz-pass spec keeps `## Decision Context`
        FLAT — no H3 introduction under default tech-only path."""
        policy = self._policy(
            "technical",
            {
                "decision_context_has_h3": False,
                "biz_pass_ran": False,
                "tech_sections_have_content": {},
            },
        )
        self.assertEqual(policy["decision_context"]["shape"], "flat")
        self.assertEqual(policy["decision_context"]["writable_h3"], [])
        self.assertEqual(policy["decision_context"]["preserved_h3"], [])
        self.assertFalse(
            policy["decision_context"]["promote_flat_to_implementation_tradeoffs"]
        )

    def test_tech_pass_substructured_when_biz_ran(self) -> None:
        """After a biz pass, Decision Context is SUBSTRUCTURED; tech preserves
        `### Motivation`, writes only `### Implementation Tradeoffs`."""
        policy = self._policy(
            "technical",
            {
                "decision_context_has_h3": True,
                "biz_pass_ran": True,
                "tech_sections_have_content": {},
            },
        )
        self.assertEqual(policy["decision_context"]["shape"], "substructured")
        self.assertIn(
            "Implementation Tradeoffs", policy["decision_context"]["writable_h3"]
        )
        self.assertIn(
            "Motivation", policy["decision_context"]["preserved_h3"]
        )


class TestScopeWritePolicyBizPass(unittest.TestCase):
    """R6: biz pass writes biz-owned + Acceptance + Decision Context;
    preserves tech sections byte-for-byte; writes placeholder lines under
    EMPTY tech sections; promotes FLAT → SUBSTRUCTURED."""

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

    def test_biz_pass_empty_state_writes_biz_only(self) -> None:
        policy = self._policy("business", {})
        for section in (
            "Goal & Context",
            "Boundaries",
            "Acceptance Criteria",
            "Decision Context",
        ):
            self.assertIn(section, policy["writable"], section)
        for section in (
            "Architecture & Data Models",
            "API Contracts",
            "Edge Cases & Constraints",
        ):
            self.assertIn(section, policy["preserved"], section)

    def test_biz_pass_promotes_flat_dc_when_no_h3(self) -> None:
        """FLAT body from a prior tech-only pass gets byte-for-byte
        promoted under `### Implementation Tradeoffs`; `### Motivation` is
        written as a new sibling H3."""
        policy = self._policy(
            "business",
            {
                "decision_context_has_h3": False,
                "biz_pass_ran": False,
                "tech_sections_have_content": {
                    "Architecture & Data Models": True,
                    "API Contracts": True,
                    "Edge Cases & Constraints": True,
                },
            },
        )
        self.assertEqual(policy["decision_context"]["shape"], "substructured")
        self.assertIn("Motivation", policy["decision_context"]["writable_h3"])
        self.assertIn(
            "Implementation Tradeoffs",
            policy["decision_context"]["preserved_h3"],
        )
        self.assertTrue(
            policy["decision_context"]["promote_flat_to_implementation_tradeoffs"]
        )

    def test_biz_pass_preserves_existing_h3_tradeoffs(self) -> None:
        """When H3s already exist: preserve `### Implementation Tradeoffs`
        byte-for-byte; write/refine ONLY `### Motivation`."""
        policy = self._policy(
            "business",
            {
                "decision_context_has_h3": True,
                "biz_pass_ran": False,
                "tech_sections_have_content": {},
            },
        )
        self.assertEqual(policy["decision_context"]["shape"], "substructured")
        self.assertIn("Motivation", policy["decision_context"]["writable_h3"])
        self.assertIn(
            "Implementation Tradeoffs",
            policy["decision_context"]["preserved_h3"],
        )
        self.assertFalse(
            policy["decision_context"]["promote_flat_to_implementation_tradeoffs"]
        )

    def test_biz_pass_writes_placeholder_under_empty_tech_sections(self) -> None:
        """biz pass writes `*Pending technical-scope interview pass.*` under
        empty tech sections so read-back makes intentional emptiness
        visible."""
        policy = self._policy(
            "business",
            {
                "decision_context_has_h3": False,
                "biz_pass_ran": False,
                "tech_sections_have_content": {
                    "Architecture & Data Models": False,
                    "API Contracts": False,
                    "Edge Cases & Constraints": False,
                },
            },
        )
        self.assertEqual(
            sorted(policy["placeholder_write"]),
            [
                "API Contracts",
                "Architecture & Data Models",
                "Edge Cases & Constraints",
            ],
        )

    def test_biz_pass_skips_placeholder_when_tech_has_content(self) -> None:
        """Refine mode: tech sections with real content are left untouched
        (no placeholder overwrite)."""
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
        # Only sections without content get the placeholder.
        self.assertEqual(policy["placeholder_write"], ["API Contracts"])


class TestScopeWritePolicyBothPass(unittest.TestCase):
    """R9: --scope=both requires TWO write-policy calls per the SKILL.md
    contract — biz first, then recompute current-sections from the post-biz
    state and compute fresh tech policy. Single pre-edit policy can't decide
    tech-pass DC shape correctly."""

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

    def test_both_pass_writable_covers_all_seven_sections(self) -> None:
        policy = self._policy("both", {})
        for section in (
            "Goal & Context",
            "Architecture & Data Models",
            "API Contracts",
            "Edge Cases & Constraints",
            "Acceptance Criteria",
            "Boundaries",
            "Decision Context",
        ):
            self.assertIn(section, policy["writable"], section)

    def test_both_pass_two_call_contract(self) -> None:
        """SKILL.md must call write-policy TWICE for --scope=both: first biz,
        then re-compute current-sections (biz_pass_ran=true) and call for
        technical. Verify both decision shapes are correctly computed."""
        # Phase 1: biz policy from initial empty state.
        empty = {
            "decision_context_has_h3": False,
            "biz_pass_ran": False,
            "tech_sections_have_content": {},
        }
        biz_policy = self._policy("business", empty)
        # Biz pass promotes FLAT → SUBSTRUCTURED, writes Motivation H3.
        self.assertEqual(biz_policy["decision_context"]["shape"], "substructured")
        self.assertTrue(
            biz_policy["decision_context"]["promote_flat_to_implementation_tradeoffs"]
        )

        # Phase 2: SKILL.md REBUILDS current-sections with biz_pass_ran=true
        # (Motivation H3 now exists; placeholder lines under empty tech
        # sections counted as "no content" for tech-pass overwrite).
        post_biz = {
            "decision_context_has_h3": True,
            "biz_pass_ran": True,
            "tech_sections_have_content": {
                "Architecture & Data Models": False,
                "API Contracts": False,
                "Edge Cases & Constraints": False,
            },
        }
        tech_policy = self._policy("technical", post_biz)
        # Tech pass now sees SUBSTRUCTURED — writes only Implementation
        # Tradeoffs, preserves Motivation byte-for-byte.
        self.assertEqual(tech_policy["decision_context"]["shape"], "substructured")
        self.assertIn(
            "Implementation Tradeoffs", tech_policy["decision_context"]["writable_h3"]
        )
        self.assertIn(
            "Motivation", tech_policy["decision_context"]["preserved_h3"]
        )
        # The single-pre-edit policy for `both` (returned by `scope
        # write-policy both ...`) cannot deliver this — verify the both-mode
        # policy reflects the biz-pass result for first-phase, NOT the tech
        # pass's preservation semantics.
        single_both = self._policy("both", empty)
        # `both` writable is the union — tech AND biz sections both included.
        self.assertIn("Goal & Context", single_both["writable"])
        self.assertIn(
            "Architecture & Data Models", single_both["writable"]
        )
        # The shape decision in the single-call form is necessarily
        # speculative for tech-pass — the per-pass invocation is the contract.


class TestScopeWritePolicyJsonContract(unittest.TestCase):
    """R23: write-policy emits structured JSON contracts. Invalid input
    routes to JSON error envelope."""

    def test_invalid_scope_returns_json_error(self) -> None:
        proc = _run(
            "scope",
            "write-policy",
            "foo",
            "--current-sections-json",
            "-",
            stdin="{}",
        )
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["success"])
        self.assertIn("invalid scope", payload["error"])

    def test_invalid_json_returns_json_error(self) -> None:
        proc = _run(
            "scope",
            "write-policy",
            "technical",
            "--current-sections-json",
            "-",
            stdin="not-json",
        )
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["success"])
        self.assertIn("invalid current-sections JSON", payload["error"])

    def test_missing_file_returns_json_error(self) -> None:
        proc = _run(
            "scope",
            "write-policy",
            "technical",
            "--current-sections-json",
            "/nonexistent/path/sections.json",
        )
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["success"])
        self.assertIn("not found", payload["error"])


class TestSkillUsesProductionSubcommands(unittest.TestCase):
    """Runtime coupling: SKILL.md must call the production flowctl
    subcommands (no inline reimplementation). Verify by reading SKILL.md
    and asserting the invocations match what these tests drive."""

    def setUp(self) -> None:
        self.skill_path = INTERVIEW_DIR / "SKILL.md"
        self.body = self.skill_path.read_text(encoding="utf-8")

    def test_skill_invokes_scope_resolve_with_raw(self) -> None:
        """SKILL.md uses `"$FLOWCTL" scope resolve --json --raw "$ARGUMENTS"`
        — preserves quoted paths with spaces."""
        self.assertIn(
            'scope resolve --json --raw "$ARGUMENTS"',
            self.body,
            "SKILL.md must invoke scope resolve with --raw",
        )

    def test_skill_invokes_scope_bank(self) -> None:
        self.assertIn('scope bank', self.body)

    def test_skill_invokes_scope_write_policy(self) -> None:
        self.assertIn('scope write-policy', self.body)

    def test_skill_extracts_defaulted_flag(self) -> None:
        """SKILL.md must read `.defaulted` from the resolve JSON — gates the
        scope question when no flag was passed."""
        self.assertIn("'.defaulted // false'", self.body)
        self.assertIn("Scope selection when no flag passed", self.body)

    def test_skill_carries_skip_contract(self) -> None:
        """SKILL.md must define the skipped-question contract: skips never
        resolve to the recommendation; they park under Open Questions and a
        consent checkpoint fires before write-back."""
        self.assertIn("Skipped Questions Are Not Answers", self.body)
        self.assertIn("park-open", self.body)
        self.assertIn("fill-assumptions", self.body)
        self.assertIn("*(assumed — unconfirmed)*", self.body)

    def test_skill_documents_two_call_both_pass(self) -> None:
        """SKILL.md must document the TWO write-policy calls for
        `--scope=both` per fn-44.2 Codex review fix."""
        # Search for the recompute / per-pass discussion.
        self.assertRegex(
            self.body,
            r"(recompute|two calls|TWO calls|biz first|biz_pass_ran=true)",
            "SKILL.md must document the both-pass two-call contract",
        )


if __name__ == "__main__":
    unittest.main()
