---
satisfies: [R20, R22, R23]
---

## Description

Codex mirror sync + comprehensive unit tests for the new behavior. R22 backward-compat invariant is enforced via deterministic static checks (per spec — NOT via interactive-skill markdown diffs / fixtures). Section merge contract from fn-44 Edge Cases is test-covered. mickel.tech PR URL is recorded (or explicitly marked deferred-non-blocking) before this gate closes.

**Size:** M
**Files:**
- `plugins/flow-next/tests/test_interview_scope_flag.py` (NEW: scope parsing, aliases, conflicts, pass behavior, merge contract)
- `plugins/flow-next/tests/test_capture_biz_routing.py` (NEW: routing destinations + sparse-layer suggestion)
- `plugins/flow-next/tests/test_r22_invariant.py` (NEW: deterministic static checks per R22)
- `plugins/flow-next/tests/test_template_canonical.py` (NEW: template exists, scope-owner annotations, drift guard scans all skill markdown)
- `plugins/flow-next/codex/` (regenerated)

## Approach

Run `bash scripts/sync-codex.sh` after T1-T3, T5-T7 land. Verify:
- 24 skills, 21 agents synced
- `templates/spec.md` mirrored to `plugins/flow-next/codex/templates/spec.md`
- `questions-business.md` + `questions-technical.md` + `questions-shared.md` mirrored
- Drift guard from T1 passes — scans ALL skill markdown (not just SKILL.md)
- R30 vocabulary guard passes

**R22 deterministic invariant tests** (no markdown fixture, no transcript harness):
- `flowctl scope resolve` (no args) → prints `technical` (default)
- `flowctl scope bank technical` → prints path to `questions-technical.md`; `flowctl scope bank business` → prints `questions-business.md`
- `flowctl scope write-policy technical --current-sections-json <empty>` returns a write-set containing only tech-owned section names; NO biz section names; NO placeholders; `## Decision Context` stays FLAT (no H3 introduction)
- Capture's routing rules are documented in `flow-next-capture/workflow.md` (per T5); R22 test parses workflow.md and asserts: (a) the 9-row signal-category routing table is present with the exact destinations from R24, (b) the threshold rule `1 <= count < 3` is stated explicitly, (c) the no-fire-at-zero rule (R22 preservation) is stated explicitly. This is a content/contract test on the skill's documented rules — capture's runtime routing is host-agent-driven (per the architectural skill-vs-flowctl rule in CLAUDE.md), so we test the contract, not a `capture_route()` helper that doesn't exist.
- `flowctl spec skeleton` output byte-for-byte identical to a literal expected string encoded in the test file (the same string `flowctl spec create` writes today, NOT a fixture file)

**Scope flag tests** (per R1-R3, R6-R9): `--scope=business`, `--scope=technical`, `--scope=both`, `--biz`, `--tech`, `--biz --tech` (error), `--scope=foo` (error), `--scope=business --tech` (error). Pass-behavior tests verify biz-only writes biz, tech-only writes tech, both runs sequentially.

`flowctl scope resolve` invocation form: SKILL.md calls it as `"$FLOWCTL" scope resolve --json --raw "$ARGUMENTS"` (single-string `--raw` arg → flowctl tokenizes via shlex internally). <!-- Updated by plan-sync: fn-44-symmetric-interview.2 shipped `--raw "$ARGUMENTS"` to preserve quoted paths with spaces; tests should exercise the `--raw` form (not the bare-argv form) for parity with what SKILL.md actually invokes. -->

**Both-pass write-policy contract**: `SCOPE=both` requires TWO `flowctl scope write-policy` calls — biz first, then recompute `current-sections` from the post-biz state (with `biz_pass_ran=true`, `decision_context_has_h3` likely flipped to true, `tech_sections_have_content` updated for placeholder-vs-real distinction), then tech. <!-- Updated by plan-sync: fn-44-symmetric-interview.2 codex-review Major #4 — a single pre-edit policy call cannot correctly decide tech-pass Decision Context shape (the biz pass may have promoted FLAT → substructured) or tech-pass placeholder overwrite. Tests for `--scope=both` must assert TWO write-policy calls observed (or the test invokes write-policy twice with biz-then-tech current-sections JSONs and verifies both returned policies are honored). -->

**Strategy Conflicts aux section**: the auxiliary-sections enumeration in section-merge tests must include `## Strategy Conflicts` alongside `## Strategy Alignment` / `## Glossary Conflicts` / `## Conversation Evidence` / `## Resolved via Codebase` / `## Resolved via Project Docs`. <!-- Updated by plan-sync: fn-44-symmetric-interview.2 finalized the aux-section list per behavior (e) — Strategy Conflicts is preserved byte-for-byte across scope changes alongside the existing aux sections. -->

**Section merge contract tests** (from spec Edge Cases):
- Tech pass on a FLAT `## Decision Context` (1.0.2 / zero-flag spec, no H3s, no biz sections): biz sections untouched; `## Decision Context` stays FLAT — NO H3 introduction (R22 backward-compat invariant: no new visible markdown structure under default tech-only path)
- Tech pass on a spec with populated `### Motivation` (post-biz-pass): biz sections + `### Motivation` unchanged byte-for-byte; only `### Implementation Tradeoffs` written
- Biz pass on a FLAT `## Decision Context` (tech-only spec from 1.0.2): existing flat body promoted byte-for-byte to `### Implementation Tradeoffs`; new `### Motivation` H3 written as sibling
- Biz pass on a spec with populated `### Implementation Tradeoffs` H3: tech sections + `### Implementation Tradeoffs` unchanged byte-for-byte; only `### Motivation` written
- Either pass with auxiliary sections present (Strategy Alignment etc.): aux sections unchanged
- R-IDs: existing entries never renumbered, never replaced; new entries appended with next-unused number

**Capture routing tests** (per R24, R25): two layers — (1) **Contract test on workflow.md content** (per Major #4 fix above): parse capture workflow.md, assert the 9-category routing table is present + threshold rule documented + no-fire-at-zero rule documented. The threshold rule and no-fire-at-zero rule statements may live in either §2.6 (routing prose) OR Phase 6 (Biz-suggestion footer prose/comments) — the test must scan the whole file, not a single section. <!-- Updated by plan-sync: fn-44-symmetric-interview.5 placed the `1 <= N < 3` threshold + R22 no-fire-at-zero comments in Phase 6's Biz-suggestion footer code block, not §2.6; tests must search the full workflow.md, not anchor a single section. --> (2) **Threshold runtime test**: invoke `flowctl scope suggest --signal-categories-count <N>` for N ∈ {0, 1, 2, 3, 5} and assert outputs are {no-fire, fire, fire, no-fire, no-fire} respectively. Plain-mode exit codes: 0 = fire, 1 = no-fire (per `scope suggest --help`); `--json` mode always exits 0 with `{"fire": bool, ...}` payload. Tests should pin one mode (recommended: plain, since SKILL.md invokes plain via `if "$FLOWCTL" scope suggest ... >/dev/null; then`). <!-- Updated by plan-sync: fn-44-symmetric-interview.5 confirmed the plain-mode exit-code contract (0=fire, 1=no-fire) matches what capture's Phase 6 footer relies on; tests must exercise the same signaling mode. --> No `capture_route()` helper — capture's actual routing happens host-agent-side (skill-driven per CLAUDE.md), tested via skill-content contract.

**Question-bank structural parity tests** (per R4, R5, T3): parse `questions-business.md` and `questions-technical.md`; assert (a) both files have H2-headed buckets with the same `## ` style, (b) bucket bodies are short bullet-list topic prompts (no paragraphs, no routing-destination annotations, no per-bucket metadata), (c) bullet count per bucket is comparable (within 2x of tech bank's mean). Detects accidental verbose-biz-bank divergence.

**R26 project-docs investigation tests**: parse interview SKILL.md `--scope=business` block; assert it contains explicit instructions to read `README.md`, `CHANGELOG.md`, `STRATEGY.md`, `GLOSSARY.md`, `knowledge/decisions/`, `.flow/specs/` index, `docs/` BEFORE drafting questions; assert it names `## Resolved via Project Docs` as the audit section. Symmetric to the existing codebase-investigation block test (which lives implicitly today).

**Template tests** (per R11, R17, R21): file exists at canonical path; scope-owner HTML comments present; CLAUDE.md links to template (not inline-duplicates); drift guard correctly fails on a temporary skill-markdown-with-canonical-sequence violation. <!-- Updated by plan-sync: fn-44-symmetric-interview.7 added a sync-codex.sh sed rewrite so the regenerated Codex mirror gets `../../../templates/spec.md` (correct relative depth from `plugins/flow-next/codex/skills/<skill>/`), vs the canonical `plugins/flow-next/templates/spec.md`. Tests that scan codex-mirror skill markdown for template references should expect the rewritten relative path, not the canonical one. The R21 drift guard targets the duplicated section sequence (`## Goal & Context` → `## Architecture & Data Models` → `## API Contracts` within 30 lines), not path references — so the guard test is unaffected, but template-path-presence tests on the codex mirror need to match the rewritten form. -->

## Investigation targets

**Required:**
- `plugins/flow-next/tests/test_flow_gitignore.py:1-25` — existing test scaffold (importlib.util pattern)
- Production flowctl subcommands from T1 (`flowctl scope resolve` / `bank` / `write-policy` / `flowctl spec skeleton`) — this task tests them via subprocess invocation. No test-only helpers module — runtime coupling between SKILL.md and tests via shared subcommand.
- `scripts/sync-codex.sh` (final validation block) — what passes look like
- fn-44 spec R20, R22, R23 + Edge Cases section merge contract

**Optional:**
- `plugins/flow-next/tests/test_expand_bare_spec_id.py` — recent test addition as pattern

## Acceptance

- [ ] `bash scripts/sync-codex.sh` passes; all R-guards green; drift guard scans all skill markdown (not just SKILL.md)
- [ ] `templates/spec.md` mirrored to codex
- [ ] Question banks (biz + tech + shared) mirrored
- [ ] R22 deterministic invariant tests pass (no markdown-diff fixture; assertions via subprocess calls to `flowctl scope resolve` / `flowctl scope bank` / `flowctl scope write-policy` / `flowctl scope suggest` / `flowctl spec skeleton`)
- [ ] Scope flag tests cover all valid + conflicting combinations
- [ ] Section merge contract tests pass: byte-for-byte preservation of unowned section bodies; aux sections preserved; R-IDs append-only
- [ ] Capture routing tests cover all 9 signal categories + threshold edge cases (count=0/1/2/3/5) for sparse-layer suggestion
- [ ] Question-bank structural parity test passes: `questions-business.md` matches `questions-technical.md` shape (H2 buckets, 4-5-bullet topic-prompt density, no decoration)
- [ ] R26 project-docs investigation test passes: SKILL.md `--scope=business` block names the doc sources + `## Resolved via Project Docs` audit section
- [ ] Template tests: file at path, scope-owner annotations, CLAUDE.md links not duplicates, drift guard detects skill-markdown violations
- [ ] Full test suite passes (current count 463+, expect ~480+ after additions)
- [ ] **T8's mickel.tech PR URL recorded** in `fn-44-symmetric-interview.8` evidence — or, if R19 is incomplete at gate time, explicitly marked deferred-non-blocking in this task's done summary. Flow-next release MUST NOT silently ship while the mickel.tech PR is in draft state with no recorded URL.


## Done summary

## Evidence
