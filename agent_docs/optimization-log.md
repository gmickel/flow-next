# Optimization log — running scores ledger

Chronological record of eval-driven prompt-optimization runs on flow-next skills/agents.
**Append a row when a mutation is kept OR deliberately discarded** — the discards are as
valuable as the wins (they stop the next agent re-running a dead end). Methodology:
[`optimizing-skills.md`](optimizing-skills.md). Harnesses live under `optimization/<target>/`.

Columns: **quality** = accuracy/coverage/detection metric (the eval that guards against
silent regression); **efficiency** = prompt or output tokens; **status** = kept / held
(no change, guarded a trim) / discarded / shipped.

| date | target | lever | quality | efficiency | status | notes |
|---|---|---|---|---|---|---|
| 2026-07-01 | `impl-review` prompt (all backends) | code-smell baseline + rubric trim + output-format trim | detection **7 → 10/10** on ground-truth corpus (smells 2.5 → 5/5; correctness 5/5 held) | prompt **−27% (−950 tok)**; output −16% | **shipped** (fn-74, PR #184 `47068f9c`) | `optimization/review-prompt/`. Baseline reliably missed Feature Envy / Data Clumps / Primitive Obsession (0/4). No over-flag on clean code. Validated codex + RP (GPT-5.5-high). |
| 2026-07-01 | `impl-review` — full 14-smell list | broad smell list | same detection as 8-smell | +75 tok vs lean | **discarded** | the 6 rare smells (Shotgun Surgery, Message Chains, Middle Man, …) added tokens, no detection. Lean 8-smell won. |
| 2026-07-01 | `plan-review` prompt (all backends) | targeted 4-item spec-quality checklist | detection **8.0 → 9.3/10** (test strategy **0/3 → 3/3**, observability 1/3 → 3/3) | +74 tok (trim already applied) | **shipped** (fn-74, PR #184 `611a77b2`) | plan reviewer already strong; checklist targets its blind spots. P6 (subtle task-ordering) stays hard (1/3). No over-flag. |
| 2026-07-01 | `plan-review` — broad 11-item checklist | broad list | 9.0/10 (< lean's 9.7); **regressed** task-ordering 2→1 | +181 tok | **discarded** | broad list *diluted* focus — the lean, targeted 4-item version beat it on quality AND cost. Less-is-more (2nd instance). |
| ~2026-06 | `repo-scout` agent | output budget | eval set 83% → 100%, accuracy held | output **~40–50% smaller** | shipped | free-form scout prose → planner. The output-budget lever's home turf. |
| ~2026-06 | `context-scout` agent | output budget | accuracy held | output **60–70% leaner** | shipped | ditto. |
| ~2026-06 | `flow-gap-analyst` agent | output budget (per-item verbosity, not item count) | 26/27 gaps preserved | output **50–70% leaner** | shipped | proof the lever generalizes past scouts. Coverage answer-key = the no-feature-loss guard. |
| ~2026-06 | `capture` skill | DRY trim (relocate routing tables) | 15/15 → **14/15** (Decision Context flattened) | — | **discarded** (reverted) | proximity is load-bearing: a routing/taxonomy table beside the step that uses it is applied more reliably. Do NOT relocate. |
| ~2026-06 | `make-pr` skill (~31k tok) | prompt trim | body held 5/5 | **~170 tok** (stale fn-42 archaeology only) | kept (modest) | mostly load-bearing render prose; deeper trims are accuracy-risky per-section work. |

## Standing lessons (distilled from the rows)

- **Less-is-more, twice.** A lean/targeted list beat a broad one on both quality and cost
  (impl 8-vs-14 smells; plan 4-vs-11 checklist). Broad lists dilute the model's focus.
- **Over-flag guard is mandatory for "find X" prompts.** A quality lever that catches more
  on bad input must be checked on *clean* input — the fn-74 winners added valid depth, not
  noise (finding-rate ≈ baseline, `false-missing == 0`).
- **Validate cross-backend** for anything feeding `build_review_prompt` (codex/copilot/
  cursor) — and remember RP keeps a **parallel rubric copy** in the skill markdown
  (`workflow-rp.md` / plan-review `workflow.md`); a prompt change must land in both.
- **Proximity is load-bearing** (capture): don't relocate routing/taxonomy/guardrail
  tables out of the phase that consumes them, even to DRY.
- **Position within a prompt barely matters** (fn-74): a block validated at the top scored
  identically wired lower — the model reads the whole prompt. Wire at the clean code seam.
