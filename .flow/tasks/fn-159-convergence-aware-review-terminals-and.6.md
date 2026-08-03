---
satisfies: [R10, R11, R12, R13]
---
# fn-159-convergence-aware-review-terminals-and.6 Docs + CHANGELOG + STRATEGY sentence + propagation/sync + downstream chain

## Description
Docs, CHANGELOG, STRATEGY.md sentence, propagation, codex sync, full gate, and the maintainer downstream chain.

**Size:** M
**Files:** `CHANGELOG.md`, `STRATEGY.md`, `plugins/flow-next/docs/{flowctl.md,ralph.md,troubleshooting.md,orchestration.md,review-findings.md}`, `GLOSSARY.md`, `.flow/bin/flowctl.py` + `flowctl_tracker/` (propagation), `plugins/flow-next/codex/**` (regen only), downstream repos per maintainer instructions

### Approach
- CHANGELOG `## Unreleased`: expand the existing 4→8 draft entry to cover the full fn-159 story, user-outcome-first per agent_docs/releasing.md (converging loops stop wasting rounds; stuck loops escalate early; reviewers can hand a judgment call to a human; plan reviews stop blocking on outcome-free prose). No version bump (batched-release rule).
- flowctl.md: hash-guard + NOT_RETRYABLE stanza + --force in the review-rounds section; the `review-artifact` CLI verb (domain-separated blob builders) and the side-effect-free `rp mode-probe` command landed by .7 — document both in the review-rounds/CLI reference section; stall rules + both new ESCALATE variants + NEEDS_HUMAN in the deterministic-cap section; verdict grammar mentions; land.reviewTrigger row already updated in .5 — verify. <!-- Updated by plan-sync: fn-159-convergence-aware-review-terminals-and.7 landed the review-artifact CLI + rp mode-probe, not yet documented anywhere -->
- ralph.md: cap section notes stall/NEEDS_HUMAN escalation routes; guard table row from .5 — verify; verdict enum note matches ralph-guard.
- troubleshooting.md: NOT_RETRYABLE entry (distinct from cap ESCALATE); ratchet description now structured-findings; reset runbook gains human-only caveat.
- review-findings.md: consumer note — flowctl's detector/ratchet now read findings.items (fn-159).
- orchestration.md ratchet mention. <!-- Updated by plan-sync: fn-159-convergence-aware-review-terminals-and.3 already extended GLOSSARY.md's Receipt entry with the NEEDS_HUMAN verdict enum + escalation-persistence sentence — verify only, do not re-edit or double-list it here. -->
- STRATEGY.md: extend the Ralph-track quality-discipline sentence to name convergence-aware review terminals (trajectory-based early escalation + reviewer-emitted NEEDS_HUMAN). Nothing else.
- Final gate: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py` (the .py target, NEVER the bash launcher) + rsync flowctl_tracker + `python3 scripts/gen_tracker_manifest.py` + `./scripts/sync-codex.sh` twice (commit mirror diff) + `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`.
- Downstream chain (maintainer-local, same workstream): flow-next.dev repo at `~/work/flow-next.dev` (Starlight pages for review caps / land / orchestration; BOTH nav sources if any page added: `src/lib/site.ts` navGroups + `astro.config.mjs` sidebar; gate `pnpm build`), docs-site changelog entry staged, AI×SDLC guide at `~/work/AI-x-SDLC-Starter-Kit` swept (explicit per-page checked-no-op recorded in the task summary), Obsidian vault notes at `~/work/GordonsVault/Spaces/Projects/flow-next` (Autonomy + Release Timeline; direct file edits, not git). Follow `~/work/agent-instructions/downstream-properties.md` incl. narrative discipline. **Unavailable-repo outcome:** if a downstream repo is missing on the machine running this task, record `downstream: <repo> unavailable — needs maintainer walk` in the task summary; that line is the durable evidence CI/another implementer checks, and the task still completes.

### Investigation targets
**Required:**
- `agent_docs/releasing.md` — changelog ordering rules + rejection test
- `plugins/flow-next/docs/flowctl.md` — review-cap + review-rounds + land config sections
- `~/work/agent-instructions/downstream-properties.md` — the downstream walk contract

**Optional:**
- `plugins/flow-next/docs/README.md` — index bullets mentioning the cap

### Key context
- Docs-only files do NOT bump plugin version; the whole spec stages under Unreleased.
- test_tracker_distribution fails on missed propagation — run the full copy/rsync/manifest sequence, not a subset.

### Acceptance
- [ ] CHANGELOG Unreleased entry covers raise + detector + NEEDS_HUMAN + calibration, outcome-first
- [ ] All listed repo docs updated; no doc states default 4
- [ ] STRATEGY.md single-sentence extension only
- [ ] Propagation + manifest + double sync-codex committed; full suite + ruff green
- [ ] Downstream chain walked with per-property outcome noted (updated / checked-no-op)
## Acceptance
- [ ] R10, R11, R12, R13 satisfied
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
