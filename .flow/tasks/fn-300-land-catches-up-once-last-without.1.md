---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8]
---
# fn-300-land-catches-up-once-last-without.1 Reorder land's catch-up last, re-anchor patience, read strictness

## Description
One cohesive change to land's workflow: move the behind-base catch-up from the conflicts step to the end of the gate sequence, pin it to the gated head, re-anchor the patience timer on the last authored push, count consecutive catch-ups from commit history, and read strictness. Docs and changelog travel with it.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-land/workflow.md`, `plugins/flow-next/skills/flow-next-land/SKILL.md`, `plugins/flow-next/codex/skills/flow-next-land/**` (regenerated), `plugins/flow-next/docs/orchestration.md`, `CHANGELOG.md`
**Touches:** [plugins/flow-next/skills/flow-next-land/**, plugins/flow-next/codex/skills/flow-next-land/**, plugins/flow-next/docs/orchestration.md, CHANGELOG.md]

### Approach
- First settle the fork the plan could not observe: does GitHub report `mergeStateStatus: BEHIND` (REST `mergeable_state: behind`) only when strict status checks apply? Probe on a scratch repository with strict off and on (ruleset), and record the answer in the done summary. If it does, R4 reads that state and adds no rules call; if not, read `gh api repos/<o>/<r>/rules/branches/<base>` (effective rules, active only) plus classic protection.
- Keep the mergeability read and the conflict stop where they are (`workflow.md:38-44`); move only the catch-up action to after patience (`workflow.md:78-84`) and before `land.mergeVerdictCommand` (`workflow.md:86-94`).
- Catch-up via `gh api -X PUT repos/<o>/<r>/pulls/<n>/update-branch -f expected_head_sha=<gated head>` instead of `gh pr update-branch`; a 422 for a moved head returns `RESOLVING`.
- Count catch-ups by walking first parents from the gated head with `gh api repos/<o>/<r>/commits/<sha>` (it returns `parents[]` and `committer.login`; `gh pr view --json commits` carries neither and caps at 100): a catch-up is a two-parent merge whose second parent is reachable from the base and whose committer is `web-flow`. Stop at the first non-catch-up commit; that commit is the patience anchor, and the existing fallbacks (`workflow.md:81-83`) read it. Any failed or incomplete read: `RESOLVING` for the tick, never treated as authored.
- Detect a queue-required base before any catch-up, independently of the strictness shortcut: the effective rules for the base (`gh api repos/<o>/<r>/rules/branches/<base>`, rule type `merge_queue`). Unreadable: treat as no queue.
- Red CI where every commit since the last green head is a catch-up: `BLOCKED` naming the base move, no repair (`workflow.md:59-68`).
- Stack layers (`references/stacks.md`) and the merge-queue path (`workflow.md:115`) keep today's behaviour; a base with a merge-queue rule is not caught up.
- Net line count of the land skill text must not grow: tighten neighbouring prose to pay for the new sentences.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-land/workflow.md` - all gates, catch-up, patience, verdict command, merge
- `plugins/flow-next/skills/flow-next-land/SKILL.md:13-44` - authorized repairs, verdict vocabulary, dry-run rule
- `plugins/flow-next/skills/flow-next-land/references/stacks.md` - stack layers to leave unchanged

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-prime/pillars.md:166` - existing wording for classic-or-rulesets protection
- `plugins/flow-next/docs/orchestration.md:506` - patience sentence to update
- `plugins/flow-next/tests/test_land_config.py`, `test_land_named_pr.py`, `test_skill_prose_diet.py` - existing land tests

### Key context
- Land owns no persistent files (`SKILL.md:22`); counts must come from PR history, as CI repair counts already do (`workflow.md:68`).
- A catch-up is a push, so today it restarts patience (`workflow.md:81`); that is the defect R2 removes.
- flow-next.dev's land page (`src/content/docs/autonomy/land.mdx:41-66`) and `flowctl/configuration.mdx:54` describe catch-up order and patience; update them on a local site branch, not pushed, as the release walk publishes them.
## Acceptance
- [ ] The strictness probe result (behind state vs rules read) is recorded in the done summary, and R4 follows it
- [ ] workflow.md: mergeability and conflicts first; catch-up after patience and before the verdict command; pinned with expected_head_sha; moved head -> RESOLVING
- [ ] Patience counts from the newest authored commit; fallbacks read that commit
- [ ] Two consecutive catch-ups plus a moved base -> NEEDS_HUMAN naming the moving base; red CI on a catch-up-only head -> BLOCKED, no repair
- [ ] Stack layers and merge-queue bases unchanged; a merge-queue base is not caught up
- [ ] Land skill text has no net line growth; codex mirror regenerated; focused land tests and sync check pass
- [ ] Scratch-repo observation recorded per R6, one line per scenario with the verdict seen: strict on (ruleset) and off; catch-up deferred until review, threads, CI and patience pass; head moved before update-branch -> 422 -> RESOLVING (distinguished from other refusals, which stay BLOCKED); patience anchored on the authored commit, including the no-push-date fallback; stale approval dismissed on catch-up -> AWAITING_REVIEW; two catch-ups plus a base move -> NEEDS_HUMAN; red CI on a catch-up-only head -> BLOCKED with no repair spent; queue-required base -> no catch-up; rules read unavailable -> strictness treated as required, queue as absent; base moved after the catch-up with strict off -> merge as the rules allow
- [ ] CHANGELOG Unreleased entry; orchestration.md and flow-next.dev land/configuration pages updated (site on a local branch)
## Done summary
Land catches up last: mergeability and conflicts are read first; a PR missing base commits (compare API behind_by > 0, independent of strict rules) is caught up only when being behind alone stops an authorized merge, after patience and before the verdict command. The update is pinned with update-branch expected_head_sha (moved head -> RESOLVING). A base requiring a merge queue is never caught up. Catch-ups are counted by walking first parents (web-flow two-parent merges from the base); two on top with the base still moving -> NEEDS_HUMAN; an incomplete history read -> RESOLVING. Patience counts from the last authored push, with the fallbacks read from that commit. Red CI on a catch-up-only head -> BLOCKED naming the base move, no repair. Stack layers keep their early catch-up. Land's text stays at 226 lines (words +~85). Runtime docs, config schema description, CHANGELOG and Codex mirror updated; flow-next.dev land and configuration pages on local site branch docs/fn-300-land-catch-up (76e6354, 2cfaaf9), not pushed.

Strictness probe (read-only, existing PRs): a no-rules repo PR 14 commits behind reads mergeStateStatus CLEAN (mf-factory-testbed#1); a strict-ruleset repo PR 28 behind reads BEHIND (turborepo-shadcn-nextjs#523). So BEHIND encodes strictness only; behind detection uses compare instead (review round 1 finding).

Open item for the person: R6 scratch-repository observation (strict on via ruleset and off; deferral, expected-head 422, patience anchor, stale approval, two-catch-up stop, red catch-up-only CI, queue base, unreadable reads) needs a scratch GitHub repository on the maintainer's account; the live-tick comparison on this project's PRs comes after release.

Decisions:
- Plan route came from the staged_prs detector matching "stacked PR" in the spec text; followed the code decision (one planning hop).
- No strictness read added: behind is detected by compare, and the catch-up happens whether or not strict rules require it.
- Site docs committed locally, not pushed (unreleased feature).

stage: impl-review - ran [round 1 three-axis NEEDS_WORK (2 findings), fix 81b26428, re-review SHIP] (model: codex gpt-6-astra high)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 4848b3fa1e8be853492d670fac8300a2823f76ff, 81b2642835c0c7a03c1d1349d802b48411f3f4ef
- Tests: pytest test_land_named_pr test_land_config test_skill_prose_diet test_flow_config_schema_drift test_shipped_links: 37 passed, ./scripts/sync-codex.sh: mirror regenerated and fresh, flow-next.dev astro build (docs/fn-300-land-catch-up): 84 pages, complete, read-only probe: mergeStateStatus vs behind_by across 10 open PRs (BEHIND only under strict rules)
- PRs: