---
satisfies: [R5, R6]
---
# fn-159-convergence-aware-review-terminals-and.4 Per-surface calibration: plan/completion severity + confidence gate, impl settled-plan clause

## Description
Per-surface blocking calibration in the three review prompts (outcome-anchored P0-P3, plan confidence gate, name-the-bad-outcome rule, impl settled-plan clause, completion inheritance) PLUS the NEEDS_HUMAN grammar lines + guidance in the prompt templates (absorbed from .3 — round-2 P1) PLUS the single deliberate rebaseline of ALL rendered-prompt parity/size invariants and hash pins.

**Size:** M
**Files:** `optimization/reached-path/evidence/fn136/review-output-format-token-delta.json` (rebaseline or supersede with an fn-159 evidence artifact — `test_actual_token_measurement_is_bound_to_assembled_prompts` binds candidate hashes + token deltas to every assembled prompt; regenerate via the documented procedure, never hand-edit), `plugins/flow-next/skills/flow-next-plan-review/references/plan-review-prompt.md`, `plugins/flow-next/skills/flow-next-impl-review/references/impl-review-prompt.md` (+ standalone-review-prompt.md if it restates severity), `plugins/flow-next/skills/flow-next-spec-completion-review/references/completion-review-prompt.md`, matching `*_FALLBACK` constants + plan-kind ratchet rule 2 in `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_prompt_text_pinned.py`, `plugins/flow-next/tests/test_review_prompt_template_parity.py` (+ its rendered fixtures / size-contract assertions)

### Approach
- Plan prompt severity line (plan-review-prompt.md:65): outcome-anchored definitions — P0 = following the plan produces a wrong or impossible implementation; P1 = material ambiguity likely to mislead a competent implementer; P2/P3 = consistency/polish, never blocking.
- Plan confidence gate (drop <75, P0 exempt at 50+), copied verbatim from the impl prompt block; suppression applies BEFORE the ratchet contract evaluates blockers.
- Blocking rule: NEEDS_WORK-driving findings must name the concrete bad downstream outcome. Tighten plan-kind ratchet rule 2 in `build_convergence_ratchet_block` to require the same. Encode the fn-153-blocks / fn-156-FYI worked example.
- Impl prompt: settled-plan clause (Decision Context / knowledge/decisions findings are FYI, never blocking) mirroring `agents/pr-comment-resolver.md:63-70`.
- Completion prompt: inherit plan-surface severity definitions verbatim.
- **NEEDS_HUMAN template lines (absorbed from .3):** verdict grammar line (`SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN`; completion: no MAJOR_RETHINK) + 2-3 sentences of guidance (design-judgment escalation, never a soft NEEDS_WORK; MAJOR_RETHINK stays "approach is wrong") in all four canonical templates + byte-parity fallbacks, AND in the pinned ralph-init `prompt_{plan,work,completion}.md` templates (round-3: they're in TEMPLATE_HASHES too — .3 touches no pinned file at all).
- **Parity/size rebaseline — SINGLE PASS for every prompt edit in this spec (round-2 P1):** read `test_review_prompt_template_parity.py` invariants FIRST (rendered text outside `## Output Format` stable, no size growth, masked-hash fixtures); then either (a) deliberately rebaseline rendered fixtures + size contract with rationale AND before/after token counts in the commit message, or (b) trim obsolete prompt text to fit the size budget. Never a blind fixture update. .3 touches zero pinned files; pins churn exactly once, here.

### Investigation targets
**Required:**
- `plugins/flow-next/tests/test_review_prompt_template_parity.py` — FULL read: every invariant, fixture, size assertion
- `plugins/flow-next/skills/flow-next-plan-review/references/plan-review-prompt.md` — full read
- `plugins/flow-next/skills/flow-next-impl-review/references/impl-review-prompt.md` — gate block + clause placement
- `plugins/flow-next/scripts/flowctl.py:8478-8900` — rubric blocks, fallbacks
- `plugins/flow-next/scripts/flowctl.py:11006-11101` — `build_convergence_ratchet_block` ratchet rule text (rule 2 prose at :11053-11056) <!-- Updated by plan-sync: fn-159-convergence-aware-review-terminals-and.7 landed the hash guard before the cap branch, shifting this region forward (was :9598-9660 pre-.1); fn-159-convergence-aware-review-terminals-and.2 landed the structured-findings ratchet (function now takes prior_items/max_total_chars/scaffold_only params, not just prior_findings prose), shifting it further to :11006-11101 and changing its signature — the plan-kind rule-2 tightening in this task now edits the structured-item rendering path, not a plain prose string -->
- `plugins/flow-next/agents/pr-comment-resolver.md:60-75`

**Optional:**
- `agent_docs/optimizing-skills.md` — token-budget discipline for prompt edits

### Key context
- fn-142 (maintainability block, same plan prompt) lands AFTER fn-159 or rebases — do not accommodate here.
- Never touch VALIDATOR_TEMPLATE_FALLBACK / DEEP_PASSES_FALLBACK.
- Prompts stay concise; definitions one tight block each; no rubric rewrites (spec boundary).

### Acceptance
- [ ] Plan prompt: outcome severities + confidence gate + bad-outcome rule; plan-kind ratchet rule 2 tightened; worked example present
- [ ] Impl prompt: settled-plan clause; completion prompt: inherited definitions
- [ ] Fallback byte-parity + hash pins + rendered-fixture/size invariants ALL green via deliberate rebaseline with rationale + token counts
- [ ] `python3 -m unittest test_prompt_text_pinned test_review_prompt_template_parity -q`
## Acceptance
- [ ] R5, R6 satisfied; parity suite rebaselined deliberately (rationale + token counts), never blindly
## Done summary
Per-surface review blocking calibration across all hash-pinned prompts in one pass: plan prompt gains outcome-anchored P0-P3 severities, the verbatim impl confidence gate (suppression before the ratchet contract), the name-the-bad-outcome blocking rule and the fn-153/fn-156 worked example; completion inherits the severity definitions; impl gains the settled-plan (Decision Context) FYI clause; all four templates + byte-parity fallbacks + ralph-init prompt_{plan,work,completion}.md gain the NEEDS_HUMAN verdict grammar + guidance; plan-kind ratchet rule 2 tightened in build_convergence_ratchet_block (review_type threaded through cursor fitting/rereview). Parity/pin/fixture/token-evidence deliberately rebaselined once via a committed generator (schema v2, baseline dc74a6c7, tiktoken, +310/+308 max delta budget); commit message carries rationale + before/after token counts.
## Evidence
- Commits: 698d3e0c5d7bb5588eb23e3df98155850ba3e9fb
- Tests: baseline: green (cd plugins/flow-next/tests && python3 -m unittest test_review_convergence_cap test_host_review_backend test_prompt_text_pinned test_review_prompt_template_parity -q), cd plugins/flow-next/tests && python3 -m unittest test_review_convergence_cap test_host_review_backend test_prompt_text_pinned test_review_prompt_template_parity test_tracker_distribution -q (222 passed), cd plugins/flow-next/tests && python3 -m unittest test_review_prompt_template_parity test_review_prompt_constraints test_prompt_text_pinned -q (37 passed), python3 scripts/run_tests_parallel.py (3977 ran, 0 failures, 0 errors, 4 skipped), uvx ruff@0.16.0 check . (clean), ./scripts/sync-codex.sh x2 (idempotent)
- PRs: