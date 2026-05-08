---
satisfies: [R5, R12, R17, R24]
---

## Description

Sweep the medium- and low-density skills (everything not covered by T7a, T7b, T8) for `epic` -> `spec` prose updates. Each skill is a small individual change; the bundle keeps T9 a single coherent worker pass since the files are disjoint. **Owns the `flow-next-setup` upgrade-detection branch** -- this task adds the interactive AskUserQuestion-prompted migration path that R5 + R24 require (the deterministic CLI path lives in T3). Setup template files (`flow-next-setup/templates/*.md`) live in this task's scope (R17 -- the templates that get rendered into user repos on `/flow-next:setup`).

**Size:** M
**Files (14 skill directories):**
- `plugins/flow-next/skills/flow-next/SKILL.md` (25 refs -- bare meta-router skill)
- `plugins/flow-next/skills/flow-next-deps/SKILL.md` (25 refs)
- `plugins/flow-next/skills/flow-next-plan-review/` (60 refs)
- `plugins/flow-next/skills/flow-next-plan/` (40 refs across SKILL.md + steps.md)
- `plugins/flow-next/skills/flow-next-work/` (34 refs across SKILL.md + phases.md)
- `plugins/flow-next/skills/flow-next-setup/` (36 refs -- including templates/usage.md, agents-md-snippet.md, claude-md-snippet.md AND new upgrade-detection workflow branch)
- `plugins/flow-next/skills/flow-next-prospect/` (21 refs)
- `plugins/flow-next/skills/flow-next-interview/` (15 refs)
- `plugins/flow-next/skills/flow-next-sync/` (14 refs)
- `plugins/flow-next/skills/flow-next-impl-review/` (7 refs)
- `plugins/flow-next/skills/flow-next-export-context/` (3 refs)
- `plugins/flow-next/skills/flow-next-strategy/` (4 refs)
- `plugins/flow-next/skills/flow-next-audit/` (1 ref)
- `plugins/flow-next/skills/flow-next-memory-migrate/` (1 ref)

## Approach

- Per-skill prose pass: "epic" -> "spec" where it refers to the flow-next artefact; CLI verbs `flowctl epic *` -> `flowctl spec *`; `--epic <id>` flag -> `--spec <id>` in help/prose.
- Specifically watch for:
  - flow-next-plan/steps.md: 33 refs, includes Step 5 epic spec creation (`flowctl epic create + set-plan` heredoc).
  - flow-next-plan-review: refers to "epic spec" throughout review-prompt construction.
  - flow-next-setup/templates/usage.md, agents-md-snippet.md, claude-md-snippet.md: 28 refs combined (R17 -- these ship to user repos via /flow-next:setup, ending up in user CLAUDE.md / AGENTS.md).
  - flow-next-setup itself: T4's banner-aware upgrade detection lives here as a NEW workflow branch (R5 + R24 interactive arm).
- **flow-next-setup upgrade-detection branch (NEW; R5/R24)**:
  - Detect at workflow entry: pre-1.0 `.flow/` (`.flow/epics/` exists, no `.flow/.flow_version` sentinel).
  - When detected, prompt the user via `AskUserQuestion` with three options: (a) Migrate now (recommended) -- dispatches to `flowctl migrate-rename --yes`, summarizes result; (b) Defer (writes `.flow/.banner-acknowledged` so the next `flowctl` invocation suppresses the banner for 7 days); (c) Suppress banner permanently -- prints instructions for `FLOW_NO_AUTO_MIGRATE=1`.
  - This is the interactive arm of the consented-migrate design. The deterministic arm (`flowctl migrate-rename --yes`) lives in T3.
  - Use canonical Claude-native tool names (`AskUserQuestion`); sync-codex.sh rewrites for Codex mirror in T13.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next/SKILL.md` (bare meta-router, 25 refs).
- `plugins/flow-next/skills/flow-next-plan/steps.md` (33 refs).
- `plugins/flow-next/skills/flow-next-plan-review/` (60 refs across SKILL.md + workflow.md).
- `plugins/flow-next/skills/flow-next-setup/templates/usage.md, agents-md-snippet.md, claude-md-snippet.md`.
- `plugins/flow-next/skills/flow-next-setup/workflow.md` (add upgrade-detection branch).

## Key context

- The setup template files are the highest-leverage per-install surface: injected into every user repo on `/flow-next:setup`. Get the spec vocabulary right.
- The upgrade-detection branch is the interactive arm of R5's two-path migration. Without it, only `flowctl migrate-rename --yes` works.

## Acceptance

- [ ] All 14 skill directories scanned and updated; zero remaining `flowctl epic` or `--epic <id>` references in user-facing prose.
- [ ] flow-next-plan/steps.md Step 5 uses `flowctl spec create + spec set-plan` heredoc.
- [ ] flow-next-setup workflow.md has an "upgrade detected" branch that prompts via `AskUserQuestion` with three options (migrate / defer / suppress) and dispatches to `flowctl migrate-rename --yes` on user accept.
- [ ] flow-next-setup template files (usage.md, agents-md-snippet.md, claude-md-snippet.md) use spec vocabulary -- new user repos get clean prose. (R17 setup templates).
- [ ] `AskUserQuestion` call in setup upgrade branch uses canonical Claude-native name (sync-codex.sh rewrites for Codex mirror in T13).

## Done summary

## Evidence
- Commits:
- Tests:
- PRs:
