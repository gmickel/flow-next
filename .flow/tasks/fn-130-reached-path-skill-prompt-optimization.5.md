---
satisfies: [R2, R6, R12]
---
# fn-130-reached-path-skill-prompt-optimization.5 Repair Prime eval and route cheap modes

## Description
Repair Prime agentic-eval authentication isolation, establish a green current-main judgment baseline, then route classify-only, report-only, full assessment, and remediation references so cheap modes do not load irrelevant material.

**Size:** M
**Files:** `optimization/prime/{README.md,run_agentic_eval.py,fixtures/**,expectations.json,results/**}`, `plugins/flow-next/skills/flow-next-prime/{SKILL.md,workflow.md,classification.md,pillars.md,playbooks.md,remediation.md}`, `plugins/flow-next/tests/test_prime_eval.py`, route fixtures, corresponding Codex mirror.

### Approach
- First reproduce and fix the zero-token `OAuth session expired` harness path without weakening filesystem/sentinel/instruction-leak isolation; preserve authenticated default config and limit setting sources.
- Require all seven existing topology fixtures and the worktree-sibling negative control to meet the current blocking threshold before changing Prime prose.
- Parse `--classify-only` in the root and route directly to classification; report-only must not load remediation; full/no-fix and full/fix load only their required material.
- Preserve classifier axes, confidence, would-ask discipline, playbook selection, report shape, fix consent, and no-write cheap modes.
- Keep deterministic emitter tests and agentic judgment tests distinct.

### Frozen fixtures
- Existing greenfield, greenfield-x-constellation, real-repo-flow-next, tier-a-siblings, tier-b-home-base, workspace-parent, worktree-sibling.
- Mode cross-product: classify-only, report-only, full/no fixes, full/fixes selected, unknown classification; authenticated and unavailable backend.

### Investigation targets
**Required**
- `optimization/prime/run_agentic_eval.py` — isolation and backend invocation.
- `optimization/prime/expectations.json` — current answer contract.
- `.flow/memory/bug/integration/claude-p-clean-room-on-oauth-logins-2026-07-16.md` — known OAuth isolation recipe.
- `plugins/flow-next/skills/flow-next-prime/SKILL.md:100-120` — classify-only promise.
- `plugins/flow-next/skills/flow-next-prime/workflow.md:9-30` — current full-workflow load.

**Optional**
- `plugins/flow-next/tests/test_prime_eval.py` — deterministic fixture/emitter gates.

## Acceptance
- [ ] Task input prompt hashes match version-adjusted `V1/B1`; every structural candidate compares against `B1`, never original `B0`.
- [ ] Offline isolation self-test, auth preflight, and instruction-leak probe pass; authentication failure is classified as invalid/skip, never scored as model judgment.
- [ ] Version-adjusted `V1/B1` meets the documented seven-fixture/negative-control blocking threshold before a Prime mutation is evaluated.
- [ ] Classify-only loads classification without full workflow/pillars/playbooks/remediation; report-only excludes remediation; full paths load only required branches.
- [ ] Classification axes, confidence, would-ask, playbook, report, consent, write behavior, and outputs meet baseline on deterministic and agentic suites.
- [ ] Route traces and measured reductions are recorded separately for classify/report/full/fix paths.
- [ ] If the authenticated baseline cannot be made trustworthy, no Prime canonical mutation lands; the task records the harness blocker and discard.
## Done summary
Repaired Prime's authenticated Claude eval path with OAuth-preserving isolation, auth/leak preflight, and invalid-run classification; both baseline and candidate passed all seven judgment fixtures. Routed classify-only directly to classification.md, preserved report/fix side effects, and recorded B1-linked reductions (65.94% classify-only; every measured route smaller); Codex mirror regeneration remains deferred to the wave conductor.
## Evidence
- Commits: 0a4400f7, ed9b6206, 63e9942e, 3e4e92ee, f3d1ff79, f7c85984, e901aa00, 1ab5bb3b, 0f08c608, c00dc797, c0142c0d, 97e9793a
- Tests: ./scripts/sync-codex.sh twice: 28 skills, 22 agents, idempotent, python3 scripts/run_tests_parallel.py: 2,286 run, 3 skipped, 0 failures/errors, bash plugins/flow-next/scripts/smoke_test.sh from /tmp: 136 passed, 0 failed, flow-next.dev build: Astro check 0 errors/warnings/hints; 74 pages built, git diff --check and changed-reference existence audit: passed, Prime authenticated Claude baseline and candidate: 7/7 each; 6/6 synthetic plus negative control
- PRs:
