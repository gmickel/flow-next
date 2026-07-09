# Review-prompt autoresearch harness (fn-74)

A **backend-in-the-loop** eval harness for optimizing the flow-next review prompts
(`build_review_prompt` impl/plan + the RP skill rubrics) for **quality AND efficiency**.
This is the concrete instantiation of the methodology in
[`agent_docs/optimizing-skills.md`](../../agent_docs/optimizing-skills.md) — and the
template to copy for the *next* review-prompt tweak. Scores land in
[`agent_docs/optimization-log.md`](../../agent_docs/optimization-log.md).

## What makes this pattern different from the subagent-reads-prompt loop

The base methodology runs a candidate prompt via a read-only `Explore` subagent. This
harness instead puts the **real review backend in the loop** — it monkeypatches the
*actual* `flowctl.build_review_prompt` (swapping rubric-block constants / injecting a
candidate block), then runs the prompt through **codex `exec`**, **RP** (`rp-cli
setup-review` + `chat-send`), or **cursor-agent** — the same engines a real review uses.
Four techniques carry the rigor:

1. **Ground-truth corpus + answer key.** `orders.py` (10 planted issues: 5 correctness
   bugs + 5 Fowler smells) / `spec_corpus.md` (10 planted plan weaknesses). Detection is
   a deterministic keyword OR-match per planted item → a hard number, not a vibe.
2. **Over-flag check on a CLEAN input.** `orders_clean.py` / `spec_clean.md` — a *good*
   artifact. A kept mutation must NOT invent findings on clean input (measured:
   finding-rate ≈ baseline, verdicts unchanged, `false-missing == 0`). This is the guard
   the base doc calls "accuracy eval," made concrete for reviews.
3. **Cross-backend validation.** flow-next reviews run on codex/copilot/cursor/RP, so the
   winner is confirmed on ≥2 engines (fn-74: codex GPT-5.5-high **and** RP GPT-5.5-high —
   the RP baseline scored identically, 7/10, which validated the whole eval).
4. **Efficiency measured alongside quality.** `len(prompt)//4` (prompt tokens, the lever
   we control) + codex `output_tokens` + wall-time, every run. Keep only mutations that
   improve one axis without regressing the other.

## Files

| File | Role |
|---|---|
| `reveval.py` | impl harness — variants (`baseline`/`fowler`/`trim`/`fowler_trim`/`ft_tighter`), codex runner, detection scorer, summary table |
| `orders.py` | impl ground-truth corpus (5 correctness + 5 smell) |
| `orders_clean.py` | impl clean corpus (over-flag check) |
| `reveval_clean.py` | impl over-flag runner |
| `reveval_plan.py` | plan harness (variants `plan_baseline`/`plan_checklist`/`plan_lean`) |
| `spec_corpus.md` / `spec_clean.md` | plan ground-truth / clean corpora |
| `reveval_plan_clean.py` | plan over-flag runner |
| `reveval_rp_run.py` | EXAMPLE: run the two prompts through the **RP** backend (set window/tab from a fresh `flowctl rp setup-review --json` first) |
| `reveval_parse_guard.py` | **OFFLINE** regression guard (fn-90 R8) — no live model. Replays the poisoned-stream verdict parse (tool-output + quoted-grammar literals) and the convergence-ratchet contract so the Cursor review-backend loop-runaway class is caught on every gate run. Runnable standalone; also wrapped by `plugins/flow-next/tests/test_reveval_parse_guard.py`. |

## Run

```bash
cd optimization/review-prompt
REVEVAL_RUNS=2 python3 reveval.py baseline ft_tighter     # impl, 2 runs each
REVEVAL_RUNS=3 python3 reveval_plan.py                    # plan
REVEVAL_RUNS=3 python3 reveval_clean.py                   # impl over-flag on clean code
```
Env: `REVEVAL_RUNS` (default 2), `REVEVAL_MODEL` (default `gpt-5.5`), `REVEVAL_EFFORT` (`high`).
Each run persists raw reviews (`out_<variant>_<n>.md`) for inspection.

> **Note:** the winning fn-74 mutations are already SHIPPED into `build_review_prompt`, so
> today `v_baseline()` (which calls the real builder) already includes them — the harness
> variants would *double-apply*. To re-optimize, redefine the variant transforms against
> the current production prompt (baseline = as-shipped). The point of keeping this dir is
> the reusable *scaffold* (corpus + runner + scorer + over-flag), not the frozen variants.

## Method (the rules)

Baseline → ONE small tweak → run → compare on BOTH axes → **keep if it improves quality
and/or efficiency without regressing the other, else throw it away.** Record every
experiment (kept or discarded) in `agent_docs/optimization-log.md`. Two fn-74 findings
worth remembering: **less-is-more** (a lean, targeted list beat a broad one *twice* — the
6 rare code smells and the broad 11-item plan checklist both *diluted* focus), and
**position barely matters** (a block validated at the top of the prompt performed
identically wired lower — the model reads the whole prompt).
