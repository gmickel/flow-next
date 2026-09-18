---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-248-capture-the-resolved-spec-template.1 Implement capture: the resolved spec template decides which sections are written

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
A team's `SPEC.md` now governs every section of a captured spec. Capture used to prepend `## Conversation Evidence` and append `## Requirement coverage` outside the resolved template; it now writes only the sections the template names, as headings or in the `auxiliary_sections` list, and existing triggers still decide whether a permitted section appears.

- R1: capture workflow §2.2 carries the one-sentence rule; the bundled template's auxiliary list gains `Requirement coverage` so default output is unchanged.
- R2: evidence collection and the §4.1 `[user]` findability check are unchanged; the §4.3 chat-correction rule and the split-proposal slices write the block only when the spec or template has it, and never recreate it.
- R3: §1.1 records an `AskUserQuestion` selection as `> user (turn N, selected): "<label>"` with no agent gloss.
- R4: the template customization comment and a new "Leaving a section out" section in the scaffold guide state the opt-out, that no tool reads the evidence block, and the from-scratch-template consequence.
- R5: `docs/prose.md` gains "Project instruction files layer on top", including the deliberate absence of a length rule.
- R6: Codex mirror regenerated twice with an identical result; the pinned `Conversation Evidence` token stays in the `[user]` row; changelog entry credits @flecamos (#443, #447) and records the from-scratch-template behavior change.
- R7: isolated in-host capture run in two scratch repos. Bundled template produced a spec with `## Conversation Evidence`; a `SPEC.md` without that entry produced a spec without it. Both carried `## Requirement coverage` on the planned route, both passed `flowctl validate`, and the findability check retagged two reworded `[user]` lines in each run. The run was performed by the change's author, so it proves the mechanics and not that a fresh agent reads the rule the same way.

Review: one codex fan-out round (gpt-6-astra, three draws) returned NEEDS_WORK with a single shared P2 finding: §2.2 promised the template's order and then forced evidence first and coverage last. Fixed in eb0ee894 by making position the template's call, with the bundled list entries carrying today's defaults. The codex re-review was not run, on the maintainer's instruction (no codex usage left); Cursor Bugbot on the PR is the remaining review. Full suite after the fix: 221 files, 4996 tests, 0 failures; ruff clean.

Prose growth (G1): capture's always-loaded workflow grows by about six lines. The lines replace an unconditional instruction with the rule that makes the template authoritative, which is the behavior #443 asked for; nothing is restated.

Not covered here: the flow-next.dev capture page and scaffold guide are downstream of this repo and follow after merge. The Codex mirror sync also regenerated `codex/docs/flow-next/README.md`, which was already stale on main (the 5.5.0 note was never synced).

stage: implement - ran (model: claude-fable-5-1; delegated: 0)
## Evidence
- Commits: 8376f913, eb0ee894
- Tests: python3 scripts/run_tests_parallel.py (221 files, 4996 tests, 0 failures, 0 errors), uvx ruff@0.16.0 check . (clean), ./scripts/sync-codex.sh x2 (idempotent), isolated capture run in two scratch repos: bundled template writes ## Conversation Evidence, custom SPEC.md without the entry omits it, both pass flowctl validate
- PRs: