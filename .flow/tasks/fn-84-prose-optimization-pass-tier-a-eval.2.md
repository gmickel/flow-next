---
satisfies: [R1, R2, R3, R4, R5, R6, R8]
---

## Description
Re-run the eval-gated loop on the `capture` skill. Suite ALREADY EXISTS (`optimization/capture/`) but capture changed in fn-82 (merged) — RE-BASELINE on current main first (MIGRATING `results.tsv` to the extended auditable schema), then attempt one mutation. Baseline was at ceiling (15/15) → trim-that-holds unless a real blind spot is diagnosed.

**Size:** S/M (re-baseline + one mutation, suite scaffold exists)
**Files:** `optimization/capture/{results.tsv,changelog.md,baseline/*}`; `plugins/flow-next/skills/flow-next-capture/{SKILL.md,workflow.md,phases.md}` (mutation if kept); `agent_docs/optimization-log.md`; `CHANGELOG.md`; `plugins/flow-next/codex/**`

## Approach
- **Migrate `results.tsv`** to the extended schema (`experiment accuracy_score accuracy_max quality_score tokens_before tokens_after runs model status description`).
- **Re-baseline (R2):** refresh `baseline/{SKILL,workflow,phases}.md` from current main, re-run the existing evals N times, record a fresh baseline row — the fn-82 folds may have shifted the score; NEVER mutate before this row exists.
- **Run-trick (side-effect-free, no worktree):** `mode:autofix` WITHOUT `--yes` prints the read-back payload, exit-2 on overwrite — the existing README documents it.
- **Existing accuracy evals:** source-tagging `[user]/[paraphrase]/[inferred]`, read-back-before-write, no-silent-overwrite (`--rewrite`-gated), C3 override-refusal — keep all.
- **Quality lever (blind spot):** `[inferred]`-tagging discipline — if its scoring eval isn't already in the suite, add it and RE-BASELINE under the expanded eval set BEFORE mutating (Major-B); then try a LEAN clarifier; keep only if tagging-accuracy rises. If already at ceiling with no real miss, honestly discard + log.
- Run-trick is side-effect-free + non-interactive (`mode:autofix`) — output-only child, no worktree, no canned-answer queue needed (C/D covered).

## Investigation targets
Required:
- `optimization/capture/` — existing suite (README run-trick, evals.md, results.tsv, baseline/)
- `plugins/flow-next/skills/flow-next-capture/workflow.md` — prose being optimized (bulk, 1024L)
- `agent_docs/optimizing-skills.md` — proximity + accuracy-guard rules
Optional:
- `plugins/flow-next/skills/flow-next-capture/phases.md`

## Key context
- Frozen grammars: `## Conversation Evidence`; source tags; tally line `Source: [user] N · [paraphrase] M · [inferred] L`; exit-2 refusal — assert unchanged.
- capture DRY-trim already regressed 15→14 by relocating routing tables (proximity) — do NOT re-run that dead end.
- Existing `optimization/capture/` fixtures already scrubbed; re-verify with the privacy grep after any fixture touch.

## Acceptance
- [ ] `results.tsv` migrated to the extended auditable schema; fresh baseline row on current main before any mutation (R2)
- [ ] ≥1 quality-lever experiment attempted (kept OR honestly discarded with rationale), lever has a scoring eval (R4)
- [ ] Every kept row accuracy held/raised AND tokens↓/quality↑; discards logged with the regression (R3)
- [ ] Frozen grammars asserted unchanged; no relocated consuming-phase tables (R5)
- [ ] Privacy grep clean over `optimization/capture/` (R1)
- [ ] `optimization-log.md` row per experiment (R6)
- [ ] `sync-codex.sh` regenerated + committed IF prose changed; `pytest` + `smoke_test.sh` green; `CHANGELOG` `## Unreleased`; no bump (R8)

## Done summary
Re-baselined the `capture` suite on current main and confirmed capture holds at ceiling — **no prose change** (a mature, twice-optimized skill, exactly as the spec's ceiling-rule anticipates). Fable review: SHIP.

**Re-baseline (R2):** refreshed `baseline/` from current-main capture prose, migrated `results.tsv` to the fn-84 extended schema (history carried as h0–h3), and added **E6 (`[inferred]`-tagging accuracy)** as the quality-lever scoring eval BEFORE the fresh baseline (Major-B). Fresh baseline **18/18** — accuracy 15/15 + E6 quality 3/3: C1 6/6 (N=2, both clean once the borderline was checked), C2 6/6 (biz-rich: cat-3 metric → outcome-AC R6 + `### Motivation`, SUBSTRUCTURED), C3 6/6 (override refused, exit 2, named fn-91, hand-edit preserved). **Confirms the fn-82 far-copy dedupe did not regress capture**, and E6 shows capture's `[inferred]` discipline is correct (conservative — never falsely attributes to the user).

**Both experiments honestly discarded (ceiling, no verifiable headroom):**
- Quality lever (`[inferred]`-discipline): E6 at ceiling 3/3 → a clarifier cannot raise a ceiling eval, and capture already tags the safe direction. Discarded (mathematically unkeepable under the ratchet), not run.
- Trim: routing/taxonomy tables in workflow.md are load-bearing (pre-fn-84 exp1's DRY trim regressed C2 15→14); the only non-routing candidate (§5.0 strategy-override heredoc) is unexercised by C1/C2/C3 → a trim there "holds trivially" = weak-ratchet. Discarded; follow-up logged (needs a strategy-override fixture).

**Fable review SHIP** — it refuted its own adversarial premise (verified against the skill contract that the C1 `[inferred]`-in-Boundaries score is contract-CORRECT, the unrun lever is unkeepable at ceiling, the trim discard follows fn-84's weak-ratchet doctrine). Applied its 2 MINOR suite-text fixes: scoped E2's `[inferred]` prohibition to user biz-SIGNAL content (not any biz-labeled section, per workflow.md L298/L325), and de-overlapped E1 (content fidelity) from E6 (tag direction).

**R6/R8:** `optimization-log.md` row added; **no CHANGELOG entry / no mirror regen** (nothing user-facing changed — capture prose is byte-identical); test surface unchanged (flowctl/tests untouched; suite was green in fn-84.1). No version bump.

**Net:** re-baseline confirms + broadens coverage (E6); zero prose change; both experiments honest discards.
## Evidence
- Commits:
- Tests: no flowctl/test change — surface unchanged since fn-84.1's green run (1425 passed / 2 skipped), fable-model review against our review rules: SHIP (refuted its own adversarial premise; 2 suite-text fixes applied)
- PRs: