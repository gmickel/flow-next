
> STUB from the fn-101 audit (2026-07-19). The doctrine-violation cleanup: judgment moves back to the host skill. Interview/plan before building.

## Goal & Context

fn-101 section 1 identified surfaces where flowctl makes or approximates judgments the host agent should own.

## Evictions

1. **Triage LLM judge: NOT an eviction (maintainer review 2026-07-19 retracted the audit's initial verdict).** The judge (flowctl.py:26991-27138) stays: a triage skip writes a `verdict: SHIP` receipt, so it is a review-shaped verdict about pipeline-written code; host self-issuing it would be self-blessing, and skip-bias is the expensive failure mode in autonomous loops. It is cheap, sandboxed, timeout-bounded, conservative (falls through to REVIEW on any failure), receipted, opt-out-able. Two changes here:
   a. **Bump the stale default models** (maintainer 2026-07-19): codex judge default `gpt-5-mini` -> `gpt-5.6-luna` @high or `gpt-5.6-terra` @medium (pick at plan after probing what the installed codex CLI accepts; adjust the default `--effort low` to match). Copilot judge default `claude-haiku-4.5` reviewed at the same time. `--model`/`--effort` overrides already exist and stay; no new config leaf unless the plan finds one already fits (review.* namespace).
   b. **CLAUDE.md carve-out note**: add a short sanctioned-exception list to the Architecture "How to spot a mistake" section (pattern: the existing fn-55 delegation carve-out paragraph) naming the licensed subprocess-LLM judgment cases - review-backend dispatch, the triage-skip judge, fn-55 delegation classify - with the one-line rationale (cross-model verdicts about pipeline-written code must not be self-issued by the host). Purpose: the fn-101 audit fleet itself mis-flagged the triage judge off the symptom list; the note stops future audits/contributors from "fixing" sanctioned cases.
2. **memory add overlap auto-routing** (flowctl.py:8522/8571/9077-9090): 0-4 token/tag overlap score; score>=3 silently updates the existing entry instead of creating. Change: always emit `matches` (with scores as retrieval signal) and let the calling skill decide update-vs-create; drop the auto-update branch. test_memory_add.py overlap cases (25 refs) re-pinned to the new contract. Callers to update: capture, qa, make-pr, interview, audit, worker prose.
3. **scope suggest** (flowctl.py:13401-13453, ~53 LOC): whole subcommand is `fire = (1 <= n < 3)` on agent-supplied counts. Change: fold the threshold into the capture skill contract (one sentence + pinned constant in a test); delete the subcommand. Update capture workflow.md:915-920,979 and prune fire/no-fire test cases.
4. **Deep-pass/validator judgment math** (with fn-112's contract work): `_apply_deep_passes_to_receipt` verdict-flip thresholds (flowctl.py:22359) and fingerprint confidence promotion (22147-22155) - decide: keep as autonomous-mode-only schema-checked path (pilot/ralph need a no-agent receipt), but interactive impl-review lets the host judge merge/promotion. Validator receipt mutation (21692) same question. This is the one eviction with a real autonomous-mode constraint - design at interview.

## Acceptance

- CLAUDE.md carries the sanctioned subprocess-LLM carve-out list (review-backend dispatch, triage-skip judge, fn-55 delegation); no OTHER LLM-subprocess judgment sites exist in flowctl.
- Memory add never mutates an existing entry unless the caller passes an explicit `--update <id>`.
- Behavior parity on the deterministic rungs (whitelist skip still skips; receipts unchanged for autonomous consumers).

## Boundaries

- fn-83's plan-sync skip-gate decision binds (not re-opened). `prime classify` axis verdicts stay (fn-101 verdict: contract-consistent, eval-pinned; re-examine only on observed skill overrides). memory migrate legacy extraction stays (deprecated fallback, window closing).
