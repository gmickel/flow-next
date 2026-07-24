---
satisfies: [R2, R10, R12]
---
# fn-130-reached-path-skill-prompt-optimization.9 Gate Strategy first-run and update branches

## Description
Apply one conservative Strategy cold-branch extraction: route absent/husk first-run versus generated update behavior without broad prose trimming. Make PR and Pilot are separate tasks 130.11 and 130.12.

**Size:** S
**Files:** `plugins/flow-next/skills/flow-next-strategy/**`; existing Strategy optimization assets/tests; `optimization/reached-path/strategy-*`; corresponding Codex mirror.

### Approach
- Verify task input hashes match `V1/B1`; compare candidates only against `B1`.
- Select absent/husk first-run or generated update path while preserving foreign/user-authored non-clobber and confirmation behavior.
- Keep shared strategy vocabulary and write safety at the consuming action sites.
- Score and log each mutation separately; retain discards.

### Frozen fixtures
- missing STRATEGY.md; husk; foreign file Keep; foreign file abort; generated first-run; generated update with preserved custom content; malformed/unknown classification.

### Investigation targets
**Required**
- `plugins/flow-next/skills/flow-next-strategy/SKILL.md` — route classification and mutually exclusive phases.
- Existing Strategy tests and optimization artifacts.

**Optional**
- fn-84/fn-85 optimization constraints.

## Acceptance
- [ ] Task input hashes match `V1/B1`; Strategy has an independent `B1`/candidate ledger and every candidate can be kept or discarded without affecting Make PR or Pilot.
- [ ] First-run/update routing preserves husk/foreign/generated classification, user-content non-clobber, questions, writes, and summary.
- [ ] Unknown/malformed state fails open toward the safe classification path.
- [ ] Existing and new route assertions pass on canonical and Codex mirror.
- [ ] Reached-path improvement and every discard reason are recorded without claiming unmeasured wall-time gains.

## Done summary
Conservatively split Strategy's mutually exclusive first-run and update workflows into selected direct references while keeping classification, foreign-file non-clobber, Ralph safety, and downstream handoff in the root router. Added fail-safe malformed-state handling, an exact V1/B1 candidate ledger with retained discards, and canonical route/metric tests; Codex mirror regeneration remains conductor-owned.
## Evidence
- Commits: 0a4400f7, ed9b6206, 63e9942e, 3e4e92ee, f3d1ff79, f7c85984, e901aa00, 1ab5bb3b, 0f08c608, c00dc797, c0142c0d, 97e9793a
- Tests: ./scripts/sync-codex.sh twice: 28 skills, 22 agents, idempotent, python3 scripts/run_tests_parallel.py: 2,286 run, 3 skipped, 0 failures/errors, bash plugins/flow-next/scripts/smoke_test.sh from /tmp: 136 passed, 0 failed, flow-next.dev build: Astro check 0 errors/warnings/hints; 74 pages built, git diff --check and changed-reference existence audit: passed, Prime authenticated Claude baseline and candidate: 7/7 each; 6/6 synthetic plus negative control
- PRs:
