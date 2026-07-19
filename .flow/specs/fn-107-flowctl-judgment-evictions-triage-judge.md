# fn-107 flowctl judgment evictions: triage judge, memory overlap, scope suggest

> STUB from the fn-101 audit (2026-07-19). The doctrine-violation cleanup: judgment moves back to the host skill. Interview/plan before building.

## Goal & Context

fn-101 section 1 identified surfaces where flowctl makes or approximates judgments the host agent should own.

## Evictions

1. **Triage LLM judge** (flowctl.py:26991-27138, ~245 LOC): `flowctl triage-skip`'s ambiguous rung shells `codex exec --model gpt-5-mini` to answer "is this diff worth a full review?" - the CLAUDE.md symptom verbatim. Change: deterministic whitelist rung stays; ambiguous cases return verdict AMBIGUOUS + reason to the calling skill, which judges itself. Update impl-review SKILL/workflow callsites.
2. **memory add overlap auto-routing** (flowctl.py:8522/8571/9077-9090): 0-4 token/tag overlap score; score>=3 silently updates the existing entry instead of creating. Change: always emit `matches` (with scores as retrieval signal) and let the calling skill decide update-vs-create; drop the auto-update branch. test_memory_add.py overlap cases (25 refs) re-pinned to the new contract. Callers to update: capture, qa, make-pr, interview, audit, worker prose.
3. **scope suggest** (flowctl.py:13401-13453, ~53 LOC): whole subcommand is `fire = (1 <= n < 3)` on agent-supplied counts. Change: fold the threshold into the capture skill contract (one sentence + pinned constant in a test); delete the subcommand. Update capture workflow.md:915-920,979 and prune fire/no-fire test cases.
4. **Deep-pass/validator judgment math** (with fn-106's contract work): `_apply_deep_passes_to_receipt` verdict-flip thresholds (flowctl.py:22359) and fingerprint confidence promotion (22147-22155) - decide: keep as autonomous-mode-only schema-checked path (pilot/ralph need a no-agent receipt), but interactive impl-review lets the host judge merge/promotion. Validator receipt mutation (21692) same question. This is the one eviction with a real autonomous-mode constraint - design at interview.

## Acceptance

- flowctl spawns no LLM subprocesses for judgment anywhere (grep-able invariant: no `codex exec`/`copilot -p` outside the review-dispatch transport).
- Memory add never mutates an existing entry unless the caller passes an explicit `--update <id>`.
- Behavior parity on the deterministic rungs (whitelist skip still skips; receipts unchanged for autonomous consumers).

## Boundaries

- fn-83's plan-sync skip-gate decision binds (not re-opened). `prime classify` axis verdicts stay (fn-101 verdict: contract-consistent, eval-pinned; re-examine only on observed skill overrides). memory migrate legacy extraction stays (deprecated fallback, window closing).
