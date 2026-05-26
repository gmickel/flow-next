## Overview

Two scoped bug fixes inside `plugins/flow-next/scripts/flowctl.py`, both surfaced during fn-48's make-pr run (PR #146 carries the workaround prose):

1. **Bug 1 (R1, R2)** — R-ID parser regex extends from `R\d+` → `R\d+[a-z]?`. Capture-driven specs with sub-scoped criteria like `R4a` and `R4b` are currently silently dropped from the parsed acceptance-criteria array.
2. **Bug 2 (R3, R4)** — `_export_memory_during_spec` falls back deterministically when `spec.created` is null (specs created in the same session as `flowctl init`, or pre-timestamp-population specs). Currently returns empty `[]`; should surface entries via earliest-task-created OR branch-first-commit OR diff-touched-memory detection.

Plus smoke coverage for both (R5) and end-to-end verification that future make-pr runs against fn-48 no longer need the workaround prose (R6).

## Conversation Evidence

> user (recent turn): "capture the two flowctl spec export-cognitive-aid bugs surfaced during fn-48 make-pr: (1) the R-ID parser silently drops criteria with non-standard suffix forms like R4a/R4b, and (2) the memory_during_spec time-window filter returns zero entries when the spec's created timestamp is null (e.g. specs created via /flow-next:capture in the same session as flowctl init). Both are bug-track, both block honest cognitive-aid rendering when they fire."

> earlier in session (paraphrased from `/flow-next:make-pr fn-48` execution): The export of fn-48 reported `acceptance_count: 7` when the spec body has 9 R-IDs (R1, R2, R3, R4a, R4b, R5, R6, R7, R8) — R4a and R4b were silently dropped from the parsed list. Separately, `memory_during_spec.decisions[]` returned 0 entries despite fn-48.2 having written `.flow/memory/knowledge/decisions/factory-droid-platform-status-2026-05-2026-05-25.md`; the spec's `created` field was null in the JSON metadata.

## Goal & Context
<!-- Source-tag breakdown: 65% [user], 35% [paraphrase] -->

`flowctl spec export-cognitive-aid` is the load-bearing input to `/flow-next:make-pr` — it aggregates spec, tasks, memory, glossary, strategy, and diff into a single structured payload the PR-body renderer consumes. [paraphrase] Two silent-drop bugs in the parser surface honestly during real make-pr runs and break the PR body's honest-when-unclear contract: an R-ID parser that misses suffix forms (R4a / R4b), and a memory time-window filter that excludes legitimate entries when `spec.created` is null. [user]

Both bugs block honest cognitive-aid rendering when they fire. [user] The PR-body skill's own hallucination guardrails (`No hallucinated SHAs`, `No R-ID misattribution`, `Trace every claim`) push the body to honestly surface "this didn't parse" — but the user-facing experience is a PR description that's incomplete by default and requires an honest-note workaround the user shouldn't have to write. Fixing the parser closes the gap at the source.

Both bugs were discovered during the fn-48 make-pr execution and worked-around with explicit "Parser note:" and "Export caveat:" prose in PR #146. [paraphrase] Future make-pr runs should not need that workaround.

## Architecture & Data Models
<!-- Source-tag breakdown: 100% [paraphrase] -->

Two scoped bug fixes inside `plugins/flow-next/scripts/flowctl.py`:

**Bug 1 — R-ID parser suffix support.** The acceptance-criteria parser in `cmd_spec_export_cognitive_aid` (and its helpers) currently recognizes only `R<digits>` form (regex roughly `\bR\d+\b`). Capture-driven specs that emerge with sub-scoped criteria like `R4a`, `R4b` (semantically different criteria sharing a logical parent) are silently dropped from the parsed acceptance-criteria array. The user-visible symptom: `acceptance_count` is wrong and `uncovered_r_ids` reports `[]` for criteria the spec body actually declares. Fix: extend the regex to `R\d+[a-z]?` (or equivalent suffix-tolerant form). Surface ALL declared R-IDs in `spec.spec_sections.acceptance_criteria[]`. Lexical sort order must place `R4a` before `R4b` and both after `R4` (if both exist) and before `R5`.

**Bug 2 — memory time-window filter null-safe.** `_export_memory_during_spec` uses `spec.created` as the lower bound of the time-window filter. When `spec.created` is null (specs created in the same session as `flowctl init`, or specs that pre-date the timestamp population), the filter behaves as if no spec timestamp exists — and the implementation currently fails closed (returns 0 entries) rather than falling back. Fix options (implementer chooses): fall back to the earliest `tasks[].created` timestamp; fall back to the earliest commit on the spec's branch via `git log <branch> --reverse --format=%ci -1`; or skip the time-window filter entirely when `spec.created` is null and instead use commit-touched-memory-entry detection (`git diff --name-only <base>..HEAD -- .flow/memory/`).

No public-API or CLI-surface changes — `flowctl spec export-cognitive-aid` keeps the same flag set and return shape. Existing callers (make-pr, future cognitive-aid consumers) get richer / more accurate payloads transparently.

## Edge Cases & Constraints
<!-- Source-tag breakdown: 100% [paraphrase] -->

- **R-ID format guardrails.** Suffix support must not break stable-R-ID semantics — `R4a` and `R4b` are independent criteria; the parser must NOT collapse them into a single `R4` row. Sibling R-IDs sort lexically (`R4a` before `R4b`); this matches existing review-receipt ordering.
- **Capture's own R-ID rule.** `/flow-next:capture` allocates sequentially from R1 in creation order. Suffix forms only emerge when the user (or a downstream `/flow-next:plan` pass) deliberately introduces sub-scoped criteria. The parser must accept them; capture itself does not need to emit them.
- **Time-window fallback determinism.** Whichever fallback the implementer picks (earliest task, branch first-commit, diff-touched), the choice must be deterministic so that two consecutive `export-cognitive-aid` runs return the same memory entries. No "best-effort" non-determinism.
- **No upstream `spec.created` backfill.** Out of scope — backfilling timestamps on existing spec JSON metadata is a separate concern (would touch flowctl init / capture / migrate). This spec only fixes the consumer (`export-cognitive-aid`) to be null-safe.
- **Smoke coverage.** Both bugs need smoke tests that reproduce the pre-fix behavior and confirm the post-fix behavior. Without them, the fix can regress silently.
- **Prior parser-fragility lessons.** Memory entries `bug/build-errors/fn-44-review-cycle-lessons-2026-05-21`, `bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08`, and `bug/data/migrationrollback-cli-10-review-cycle-2026-05-08` document parser-contract failures and null/missing-field crash patterns inside flowctl.py — required reading before touching the export parser. Same class of failure mode.

## Acceptance Criteria
<!-- Source-tag breakdown: 30% [user], 70% [paraphrase] -->

- **R1:** `flowctl spec export-cognitive-aid <spec-id> --json` recognizes acceptance-criteria R-IDs with single-letter suffixes (e.g. `R4a`, `R4b`) and includes them in `spec.spec_sections.acceptance_criteria[]` and `tasks_summary.uncovered_r_ids` calculations. Sibling R-IDs sort lexically (`R4` < `R4a` < `R4b` < `R5`). [paraphrase]
- **R2:** Re-running the export against fn-48 (the originally-affected spec) returns `acceptance_count == 9` (was 7 pre-fix) and recognizes R4a + R4b in the parsed list. [user] (turn) / [paraphrase]
- **R3:** When `spec.created` is null, `memory_during_spec.{decisions,bugs,architecture_patterns}[]` returns entries via a deterministic fallback (earliest-task-created OR branch-first-commit OR diff-touched detection — implementer picks the simplest that works in the test fixture) rather than silently returning `[]`. [user] (turn) / [paraphrase]
- **R4:** Re-running the export against fn-48 with the null-safe filter active surfaces the `factory-droid-platform-status-2026-05-2026-05-25` decision entry in `memory_during_spec.decisions[]` (was `[]` pre-fix). [paraphrase]
- **R5:** A smoke test reproduces both pre-fix behaviors against a synthetic spec fixture (one with `R<n><suffix>` criteria, one with `spec.created: null`) and asserts the post-fix outputs match expected. The smoke is added to `plugins/flow-next/scripts/smoke_test.sh` (or a dedicated test file the smoke harness runs). [paraphrase]
- **R6:** End-to-end `/flow-next:make-pr` against fn-48 (or a synthetic similar spec) no longer requires the "Parser note" / "Export caveat" prose workarounds that PR #146 carries. [paraphrase]

## Boundaries
<!-- Source-tag breakdown: 60% [user], 40% [paraphrase] -->

In scope:
- The two specific parser bugs identified in PR #146 ([user] turn — "the two bugs").
- Smoke test coverage that reproduces and verifies each bug fix.
- The single file `plugins/flow-next/scripts/flowctl.py` (and helpers it imports).
- Optional: `plugins/flow-next/docs/spec-template.md` note documenting that suffixed R-IDs (R4a, R4b) are now officially supported — implementer decides whether to bless the suffix form as canonical or just tolerate it.

Out of scope:
- **Backfilling `spec.created`** on existing spec JSON. Separate concern; the fix is consumer-side null-safety, not producer-side timestamp population. [paraphrase]
- **Generalizing R-ID format beyond `R\d+[a-z]?`** (e.g. supporting `R1.1`, `R-AUTH-3`, etc.). The suffix form `R4a` is the observed pattern; broader format support waits for a real need. [paraphrase]
- **Re-emitting affected PR bodies.** PR #146's honest-note workarounds stay; future PRs benefit from the fix.
- Changes to `/flow-next:capture`, `/flow-next:plan`, or `/flow-next:make-pr` skill prose — those skills already render whatever the export produces.
- Changes to the spec-completion-review or impl-review skills (orthogonal to export).
- Closing fn-48 (status=open despite all tasks done) — separate housekeeping, not blocking fn-49.

## Strategy Alignment

Active tracks served by this plan:
- **Spec-driven team patterns** — `/flow-next:make-pr` is the methodology's PR-as-cognitive-aid surface; honest rendering depends on the export producing accurate input. Fixing the parser closes a foundational gap.
- **Cross-platform parity** — pure Python parser fix; benefits Claude Code / Codex / Droid identically. No platform-specific code paths.

## Decision Context

### Motivation
<!-- Source-tag breakdown: 50% [user], 50% [paraphrase] -->

Prioritization: both bugs are bug-track ([user] — "Both are bug-track"). They don't add behavior; they fix incorrect-by-design parsing that produces silently-wrong cognitive-aid output. The user-facing impact is asymmetric — when the bugs fire, the make-pr skill's honest-when-unclear contract pushes the body to surface workaround prose, which works but trains reviewers to expect noisy PR bodies on flow-next changes. Fixing at the source removes the noise.

Both bugs were discovered organically by running real make-pr on a real spec (fn-48); they're not theoretical failure modes. The fact that fn-48 needed BOTH workarounds in a single PR body suggests the failure rate is higher than the pre-PR-#146 visibility implied. [paraphrase]

Why two tasks (not one combined): the bugs are independent (one is regex, one is timestamp/fallback logic) and live in different functions inside `flowctl.py`. Splitting allows parallel work and lets either ship independently if the other hits scope creep.

Why no separate integration-verification task: R6 (end-to-end make-pr no longer needs workaround prose) is satisfied jointly when both T1 and T2 land. Either task's own end-to-end verification covers half; the joint case is verified at the next make-pr invocation against any spec, which is cheap to spot-check without dedicated task ceremony.

## Quick commands

```bash
# Reproduce Bug 1 (R-ID suffix drop) against fn-48:
.flow/bin/flowctl spec export-cognitive-aid fn-48-backend-split-review-workflows-flowctl --base origin/main --json \
  | jq '.spec.spec_sections.acceptance_criteria[].id'
# Expected pre-fix: 7 IDs (R1, R2, R3, R5, R6, R7, R8). Post-fix: 9 (adds R4a, R4b).

# Reproduce Bug 2 (memory_during_spec empty) against fn-48:
.flow/bin/flowctl spec export-cognitive-aid fn-48-backend-split-review-workflows-flowctl --base origin/main --json \
  | jq '.memory_during_spec.decisions | length'
# Expected pre-fix: 0. Post-fix: 1 (the factory-droid-platform-status decision).

# Smoke (after each task):
bash plugins/flow-next/scripts/smoke_test.sh
```

## Early proof point

Task **fn-49.1** (R-ID parser suffix support) validates the test-and-fix loop with the simpler of the two bugs (single regex extension + lexical-sort check). If it fails or the smoke pattern doesn't reproduce reliably, re-evaluate the test-fixture strategy before tackling fn-49.2 (which has implementer-choice fallback logic with more design surface).

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | R-ID parser recognizes `R\d+[a-z]?` form | fn-49.1 | — |
| R2  | Re-export fn-48 returns acceptance_count=9 | fn-49.1 | — |
| R3  | Null-safe memory time-window filter | fn-49.2 | — |
| R4  | Re-export fn-48 surfaces Droid decision in memory_during_spec | fn-49.2 | — |
| R5  | Smoke tests for both pre/post-fix behaviors | fn-49.1, fn-49.2 | Each task adds its own smoke fixture |
| R6  | make-pr against fn-48 no longer needs workaround prose | fn-49.1, fn-49.2 | Verified jointly when both land; spot-checked at next make-pr |

## References

- Source analysis: this session's fn-48 make-pr execution (PR #146 carries the workaround prose).
- Memory entries (required reading before touching the export parser):
  - `bug/build-errors/fn-44-review-cycle-lessons-2026-05-21` — parser contract failures from fn-44 / 1.1.4 work; relevant to `_export_parse_acceptance_criteria` heading-variant tolerance
  - `bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08` — absent spec fields silently passing validation then crashing on export/cat; same class of bug as `spec.created` null causing time-window filter to fail closed
  - `bug/data/migrationrollback-cli-10-review-cycle-2026-05-08` — atomic write + spec JSON field handling pitfalls
- Affected file: `plugins/flow-next/scripts/flowctl.py` (the `cmd_spec_export_cognitive_aid` function and `_export_memory_during_spec` helper)
- PR #146 (fn-48 merge commit `54269f7`) — the workaround prose this spec removes
