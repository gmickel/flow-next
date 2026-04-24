---
satisfies: [R2, R3, R12, R18]
---

## Description

Phases 2-4 of the skill: persona-seeded candidate generation, two-pass critique with rejection floor, and bucketed ranking. This is the LLM-heavy section of the workflow; Phase 1 (from task 1) feeds the grounding snapshot into Phase 2.

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-prospect/workflow.md` (extend from task 1)
- `plugins/flow-next/skills/flow-next-prospect/personas.md` (new — persona seed prompts)

## Approach

**Phase 2 — Generate (divergent-convergent):**
- Prompt explicitly separates divergent phase ("wide net, encourage contrarian takes, no self-judging") from convergent handoff.
- Personas used: at least 2 from `senior-maintainer`, `first-time-user`, `adversarial-reviewer`. Persona prompts live in `personas.md`; the skill picks 2-3 based on focus hint (or defaults to senior-maintainer + first-time-user when no hint).
- Volume enforcement:
  - No hint → target 15-25 candidates.
  - `N ideas` → generate ≥N (allow LLM to exceed).
  - `top N` → generate ceil(N * 1.8) candidates (so that after 40% rejection, ≥N survive).
  - `raise the bar` → generate 25-30 candidates (broader net for harder critique).
- Candidate shape: `title`, `summary` (1 line), `affected_areas` (paths/subsystems), `size` (S/M/L/XL), `risk_notes`.
- Output: flat YAML/JSON list handed to Phase 3 as a separate prompt input — Phase 3 does NOT see Phase 2's system prompt (prevents rationalization).

**Phase 3 — Critique (separate prompt):**
- Input: Phase 2 candidate list + grounding snapshot (NOT the focus hint — protects against sycophancy under user rebuttal).
- Output: `{verdict: keep|drop, reason, taxonomy}` per candidate using the rejection taxonomy `duplicates-open-epic | out-of-scope | insufficient-signal | too-large | backward-incompat | other`.
- **Rejection floor forcing function (R12):**
  - Default target: ≥40% rejection rate.
  - `raise the bar` hint: 60-70% target.
  - If critique rejects fewer than the floor, skill surfaces a floor violation via blocking question: "critique rejected only X% (below ≥40% floor). Options: `regenerate | loosen-floor | ship-anyway`".
- Taxonomy serves double duty: forces specific reasons (not "could be useful someday") and feeds the Rejected section of the artifact.

**Phase 4 — Rank survivors (bucketed):**
- Survivors go into three labeled buckets:
  - `High leverage (1-3)` — small-diff, large-impact
  - `Worth considering (4-7)` — solid mid-leverage
  - `If you have the time (8+)` — lower priority
- Each survivor carries a forced-format leverage sentence: `"Small-diff lever because X; impact lands on Y."`
- No numeric scores (ranking past position 5 is near-random; buckets stabilize top-3).
- Survivor positions renumber sequentially (1-indexed); bucket assignment is a separate axis.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-prospect/workflow.md` (from task 1) — extend, don't duplicate
- `plugins/flow-next/skills/flow-next-impl-review/deep-passes.md` — multi-persona pass structure as inspiration (single-chat, not parallel)

**Optional:**
- `plugins/flow-next/agents/quality-auditor.md` — adversarial-reviewer persona prior art

## Key context

- LLMs exhibit mode collapse post-RLHF — the same 5-8 "obvious" ideas emerge without persona seeding. Distinct personas anchor in different semantic regions, measurably increasing diversity.
- Two-pass separation prevents sycophancy: the critique pass can't defend its own generation if it doesn't have the generator's prompt.
- Prior-session survivors (when resuming) are fed as "already proposed, still open" grounding — NOT re-ranked. Prevents resurrection bias.

## Acceptance

- [ ] `personas.md` defines ≥3 persona prompts (senior-maintainer, first-time-user, adversarial-reviewer); workflow.md specifies which to pick based on focus hint.
- [ ] Phase 2 generates 15-25 candidates by default; `top N` and `N ideas` hints respected per the volume-semantics table.
- [ ] Phase 3 critique is a separate prompt that doesn't see Phase 2's system prompt or the focus hint.
- [ ] Phase 3 uses the fixed rejection taxonomy; output shape documented.
- [ ] Rejection floor enforced: default ≥40%, `raise the bar` 60-70%; floor violation triggers blocking question with 3 options.
- [ ] Phase 4 produces bucketed ranking (High leverage / Worth considering / If you have the time); each survivor has a leverage sentence in the forced format.
- [ ] No numeric scores emitted anywhere in the survivor output.

## Done summary
Phases 2-4 of /flow-next:prospect landed: persona-seeded divergent generation (volume table covers default / top N / N ideas / raise the bar; >=2 of senior-maintainer / first-time-user / adversarial-reviewer, picked by focus-hint kind), separate-prompt critique with fixed rejection taxonomy + 40%/60% rejection floor enforced via blocking question (regenerate | loosen-floor | ship-anyway), and bucketed rank (High leverage 1-3 / Worth considering 4-7 / If you have the time 8+) with forced-format leverage sentence ("Small-diff lever because X; impact lands on Y.") - no numeric scores. Personas sidecar added at plugins/flow-next/skills/flow-next-prospect/personas.md; workflow.md +412 lines; SKILL.md phase summary updated. Smoke 125/125 still green.
## Evidence
- Commits: ae368af4fd735e982992d1c8722b1ac6331768ad
- Tests: plugins/flow-next/scripts/smoke_test.sh (125/125 pass)
- PRs: