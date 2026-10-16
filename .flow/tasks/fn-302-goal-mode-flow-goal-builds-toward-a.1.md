---
satisfies: [R1, R1a, R2, R3, R4, R5, R6, R7, R8, R9, R9a, R10, R11]
---
# fn-302-goal-mode-flow-goal-builds-toward-a.1 Implement Goal mode: flow --goal builds toward a goal spec's bar

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Added goal mode: `/flow-next:flow --goal <spec-id or source>` (implies `--auto`) works toward a goal spec's criteria. New gated references `skills/flow-next-flow/references/goal-mode.md` (resolve or capture the goal, drive one open child through the `flow --auto` hop loop, measure in a scratch worktree, decide, mint the next child, open questions, the `## Goal log`, verdicts with `GOAL_MET`, `--tick`/`--explain` at goal scale) and `skills/flow-next-capture/references/from-goal.md` (capture's `from:goal` token: the source stands in for the conversation, no compaction check, goal and logged children excluded from duplicates, goal capture skips the split gate, child refusals become open questions).

Base rules that would contradict a goal run now state their scope: auto.md's argument rule, stage and gh allowlists, probe rule, selection, explain stop and merge continuation; tail.md's one-PR binding (per child in goal mode); working rules' follow-up and discovery lines; capture's compaction, split and prior-capture gates; flowctl's `spec ready` help and the readiness docs ("consent gate"). Fence verdicts carry `GOAL_REASON_PREFIX` / `GOAL_SPEC`, unset (byte-identical lines) outside goal mode. Routing row in route-matrix-more.md; flow skill description gains one clause. Docs: skills reference, seven reach pages, GLOSSARY (goal spec, goal log), CHANGELOG with credit for #559. flow-next.dev pages are on local branch docs/fn-302-goal-mode (6e636f4), held for 9.0.0.

Tests: `--goal` argument shapes, `--backlog` ignored with `--goal`, `GOAL_MET` grammar, goal prefix on guard stops, capture `from:goal` parse and lookalike, goal-mode.md mirror parity, from-goal.md reachability. Full suite 4047 tests green; ruff clean; sync-codex --check fresh.

Spec note: item 3's "flowctl-help.txt and its hash regenerate" did not apply: the `spec ready` help string is not in the cached root help, so only MANIFEST.json regenerated.

stage: impl-review - ran (model: gpt-6-astra) - codex, 3-reviewer panel then 3 single re-reviews; 8 of 9 findings fixed; loop ended ESCALATE (stall) on #9 alone
OPEN_ITEM: R10's test run needs a throwaway GitHub repository the person approves creating (for --until=merge) and the person's answer on its person-judged criterion; run it, or defer R10.

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 9954e210ee9329c44d3eda07f82fe75127d14149, 9faa24e982389ab93b574f42308c03b5033f839c, e5f53866a7beb587eef78bb6fed10e7275cd6762, 78b96f2ed0c62dc86d9b9380f0de63db9868acf2
- Tests: python3 scripts/run_tests_parallel.py (4047 tests, 0 failures), uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check
- PRs: