---
satisfies: [R2, R3, R4]
---
# fn-202-route-aware-next-step-guidance-in.2 Plan interactive menu: Recommended-next line with plan-review-skip guardrail

## Description
Add the recommendation line to plan's INTERACTIVE next-steps surface only.

**Files:** plugins/flow-next/skills/flow-next-plan/references/next-steps-menu.md (above the `Next steps:` numbered list, ~line 10). steps.md Step 8 itself is NOT edited (its summary also prints under AUTONOMOUS=1, which must stay recommendation-free; next-steps-menu.md loads only on the interactive path — the placement IS the autonomy guard).

**Approach:** same line shape as capture's. The judged decision is plan-review-vs-straight-to-work: prose states the guardrail — a skip-plan-review recommendation is legal ONLY when the plan matches one of the two ceremony shapes pipeline-variations names (docs/chore-class; small-task-class with no design risk); ANY remaining design risk → recommend plan-review (cheapest measured catch). Judgment inputs: task sizes/count, design risk surfaced during research, blast radius. Re-judge at every menu print (go-deeper/simplify rounds change the risk picture — stale advice is worse than none). Link docs/pipeline-variations.md once; guide nameable on genuine ambiguity; no rubric copy; numbered options and the go-deeper/simplify loop text stay byte-identical. Mind test_skill_prose_diet pins on steps.md (exactly one `config get`; gate-then-reference ordering) — untouched since steps.md is untouched.

**Touches:** [plugins/flow-next/skills/flow-next-plan/references/next-steps-menu.md]

## Acceptance
- next-steps-menu.md prints exactly ONE `Recommended next:` line above the unchanged numbered list; re-judged on every menu re-print (stated in prose)
- Skip-plan-review recommendation constrained to the two named ceremony shapes; any other skip recommendation is defined as a conduct failure in the prose
- steps.md diff is EMPTY (autonomy branch untouched by construction); test_skill_prose_diet green
- One pipeline-variations link; no rubric copy; no size-based language
- Error surface: none (prose-only, no bash added)

## Done summary
Added the route-aware `Recommended next:` line to plan's interactive next-steps menu (`plugins/flow-next/skills/flow-next-plan/references/next-steps-menu.md`): exactly one mandatory line above the unchanged numbered list, re-judged at every menu print, judging plan-review-vs-straight-to-work per `docs/pipeline-variations.md` (linked once, no rubric copy). Skip-plan-review is legal only for the two named ceremony shapes (docs/chore-class; small-task-class with no design risk) and the line must name which; any other skip recommendation is defined as a conduct failure; signals-conflict falls back to `/flow-next:guide`. steps.md diff is empty by construction (next-steps-menu.md loads only on the interactive path, so AUTONOMOUS=1 stays recommendation-free). Numbered options and go-deeper/simplify loop text byte-identical; no bash added.

baseline: green (focused suite pre-edit)
Verify: `flowctl gate classify` → FULL (force-full skills prefix); Quick-command suite green at HEAD; receipt minted `9d256777-unittest`. Focused extra run incl. test_flowctl_surface also green.

stage: impl-review - skipped(policy: PARALLEL_WAVE - conductor owns review after integration; REVIEW_MODE=none)
## Evidence
- Commits: 40a12f9b
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_skill_prose_diet -q (integrated head, green), uvx ruff@0.16.0 check . (green)
- PRs: