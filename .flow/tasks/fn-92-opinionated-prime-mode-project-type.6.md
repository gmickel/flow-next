---
satisfies: [R4, R5, R6]
---

## Description
workflow.md Phase 2 extensions: execution evidence + operability ladder + hard gates.

**Size:** M | **Files:** `plugins/flow-next/skills/flow-next-prime/workflow.md` (Phase 2 + the gate evaluation)

## Approach
- NON-MUTATING EXECUTION POLICY first (the round-3 critical, spec Edge Cases): static resolution for all documented commands; execution only for allowlisted evidence classes (check-mode lint/typecheck, test discovery, bounded build, --help/--dry-run, gated boot probe); formatters check-mode only; setup/migrate/seed/deploy/destructive/network NEVER executed; pre/post `git status --porcelain` snapshots invalidate evidence on unexpected tracked changes; G3 = resolves-vs-safe-sampled-execution split.
- Phase 2 (L44-97 seam): tier-1 build execution (bounded, portable timeout per classification.md); PER-SURFACE/MEMBER verification with the resolution-18 budget (deployable-first sampling, max ~5 executions, ~10 min global cap, affected-command substitution, NOT ASSESSED listing); tier-3 boot probe with ready-signal gate + external-SaaS qualifier + not-probed-on-this-host rule; agent-file quoted-command HOST extraction + execution (extraction-failure flag when fenced blocks exist but zero commands resolve); hook-content reads (never execute); .env cross-ref per DE1 scoping; stacks.md verify column drives commands.
- Progress observability per resolution 20: start/completion/timeout lines per surface/member, elapsed vs budget, NOT ASSESSED printed as budget exhausts.
- Hard gates G1-G3 evaluation + the Level-2 cap rule (consumes pillars.md task-1 wording).
- Ladder computation: per-surface tiers, shape ceilings, at-ceiling reporting + sideways moves, min-deployable headline aggregation (resolution 17).

## Key context
- Evidence rules absolute: unverified-counts-as-fail; every verdict quotes evidence. HP-sensitive quoting: key names never values.

## Acceptance
- [ ] Ladder graded from executed evidence: per-surface tiers + min-deployable aggregation, ceilings, SaaS gate, not-probed rule (R4)
- [ ] Member budget enforced with progress lines + NOT ASSESSED output (resolutions 18/20)
- [ ] Gates G1-G3 cap level at 2 with failure named; extraction-failure flags, never vacuous pass (R5)
- [ ] Substance executions per R6 wired, each quoting evidence, ALL compliant with the non-mutating policy (worktree snapshot guard present; DE4/setup never executed; BS3 via boot probe)

## Done summary
Extended prime `workflow.md` Phase 2 into the full execution-evidence + operability-ladder + hard-gate stage: a non-mutating execution policy (static resolution always; execution only for allowlisted check-mode/discovery/bounded-build/gated-boot classes; setup/migrate/seed/deploy/destructive/network never run; pre/post worktree snapshot guard; G3 resolves-vs-safe-execution split), tier-1 build (G1/BS2), test discovery (G2/TS4), tier-3 boot probe with ready-signal + external-SaaS + not-probed-on-host gates (BS3/AO3), per-surface/member sampling (deployable-first, ~5 execs, ~10 min cap, affected-command substitution, NOT ASSESSED listing + progress lines), agent-file quoted-command extraction/execute (G3/DC2) with extraction-failure flag, HP7 hook reads (never execute), DE1 per-member env cross-ref, the operability ladder (per-surface tiers, shape ceilings with sideways moves, min-deployable aggregation), and the G1-G3 Level-2 cap. Codex mirror regenerated; em-dash-free; fenced blocks re-declare vars.
## Evidence
- Commits: efb96015292efac8c89c5818e3ffdfb3ef1d960b
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' (1615 OK, 2 skipped), python3 -m py_compile plugins/flow-next/scripts/flowctl.py (OK), map_smoke_test.sh (75/75), glossary_smoke_test.sh (80/80), scripts/sync-codex.sh (all mirror guards pass)
- PRs: