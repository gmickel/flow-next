---
satisfies: [R3, R6, R7, R8, R9]
---

## Description
Consolidation + authoritative reconciler — runs after fn-84.1–.8 land. Assemble the cross-cutting deliverables and reconcile the shared files the per-skill tasks only touched locally (Minor-6): final target-map update, ratchet-integrity audit across all suites (extended schema), reclassification list, PR net-effect table, CHANGELOG finalize, authoritative mirror regen on merged main.

**Size:** S/M (aggregation, no new eval loops)
**Files:** `agent_docs/optimizing-skills.md` (target map, ~L159-166); `agent_docs/optimization-log.md` (verify complete); `CHANGELOG.md` (`## Unreleased` finalize); `plugins/flow-next/codex/**` (final regen); PR-body draft (net-effect table — rendered at make-pr time)

## Approach
- **Target map (R6):** mark the 8 Tier-A skills done in the `## Target map` table; note Tier A complete.
- **Ratchet-integrity audit (R3):** for each `optimization/<skill>/results.tsv` (extended schema), verify every `status=keep` row has `accuracy_score/accuracy_max ≥ baseline ratio` AND (`tokens_after < tokens_before` OR `quality_score` up); surface any violation loudly (a kept accuracy-drop is a spec failure).
- **Net-effect table (R7):** per skill — always-loaded tokens before/after, accuracy before/after, quality levers kept — sourced directly from `results.tsv` columns. This is the table the make-pr body renders.
- **Reclassification list (R9):** list any skill that hit the time-box / weak-eval escape and was pushed to fn-85, with rationale — silent scope-shrink forbidden.
- **Shared-file reconcile (Minor-6):** verify `optimization-log.md` has a row per experiment across all 8 tasks; finalize the `## Unreleased` CHANGELOG entry; run `./scripts/sync-codex.sh` once on merged main as the authoritative mirror regen.
- **Final privacy sweep (Major-5/A):** run the Quick-commands privacy grep SCOPED to fn-84's 8 Tier-A dirs (`optimization/{plan,capture,interview,make-pr,audit,prospect,qa,strategy}/`) with synthetic test domains allowlisted — must return nothing. Legacy suites (plan-sync-gate/worker-anchor/quality-auditor) are OUT of scope and NOT gated here (they already contain synthetic/real test addresses; fixing them is not fn-84's job).

## Investigation targets
Required:
- `agent_docs/optimizing-skills.md` — target-map table to update
- `agent_docs/optimization-log.md` — verify a row exists per experiment across all 8 tasks
- `optimization/*/results.tsv` — the ratchet ledgers to audit (extended schema)
Optional:
- `optimization/capture/results.tsv`, `optimization/make-pr/results.tsv` — re-baseline rows landed here

## Acceptance
- [ ] `optimizing-skills.md` target map marks all 8 Tier-A skills done; Tier A noted complete (R6)
- [ ] Every `optimization/<skill>/results.tsv` audited via the extended schema — zero kept mutations with accuracy drop / no token-or-quality gain, or violations surfaced explicitly (R3)
- [ ] Net-effect table assembled (tokens + accuracy + levers per skill) for the PR body, sourced from results.tsv (R7)
- [ ] Any reclassified-out skill listed with rationale (R9)
- [ ] Scoped privacy grep (8 Tier-A dirs, synthetic domains allowlisted) returns nothing (Major-5/A)
- [ ] `optimization-log.md` complete; `CHANGELOG` `## Unreleased` finalized; authoritative `sync-codex.sh` regen on merged main; final `pytest` + `smoke_test.sh` green; no version bump (R8)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
