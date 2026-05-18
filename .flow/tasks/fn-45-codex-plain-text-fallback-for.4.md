---
satisfies: [R7, R8, R9]
---

## Description

Update user-facing docs to reflect the new sync-codex.sh transform contract: `CLAUDE.md` cross-platform-patterns "Blocking-question tool" row, `agent_docs/adding-skills.md` step 3 parenthetical, `agent_docs/local-dev.md` new "Codex plain-text prompt smoke" subsection. Add `CHANGELOG.md` `[flow-next 1.1.2]` entry above the 1.1.1 entry summarizing the transform + validation guards.

**Size:** S

**Files:**
- `CLAUDE.md` (line 63 row + possibly line 27 prose)
- `agent_docs/adding-skills.md` (step 3 parenthetical, ~line 9)
- `agent_docs/local-dev.md` (new subsection after line 59, before "RP gotchas" at line 61)
- `CHANGELOG.md` (new `[flow-next 1.1.2]` block above 1.1.1)

## Approach

- `CLAUDE.md` line 63 "Blocking-question tool" row: replace "sync rewrites to `request_user_input` for Codex" with "sync transforms `AskUserQuestion` into a plain-text numbered-prompt instruction (with `N+1. Other — type your own answer` final option) for the Codex mirror; the mirror never calls `request_user_input` (Plan-mode-only per openai/codex#10384)". Keep "Droid (currently) sees the canonical name" if still accurate. Match the row's existing terse style.
- `CLAUDE.md` line 27 (skill-architecture prose): verify whether the existing parenthetical needs updating. If it mentions `AskUserQuestion` directly without referencing the Codex transform, leave unless misleading.
- `agent_docs/adding-skills.md` step 3 parenthetical: replace "sync-codex.sh rewrites to `request_user_input` for Codex" with a description of the plain-text numbered-prompt transform. Keep step 3's existing terse one-line shape.
- `agent_docs/local-dev.md` new "## Codex plain-text prompt smoke" subsection (after line 59, before "## RP gotchas"): document the manual verification steps — open marketplace repo (with `.flow/epics/` present) in Codex Desktop Default mode, run `/flow-next:setup`, confirm numbered plain-text consent prompt with `Other — type your own answer` as final option, confirm no `request_user_input` call attempt. Repeat on Codex CLI. Record any deviation in the subsection or in this task's summary.
- `CHANGELOG.md`: new `## [flow-next 1.1.2]` block above the `[flow-next 1.1.1]` block (line 5). Use keep-a-changelog format: `### Fixed` (or `### Changed`) bullets summarizing the transform replacement + validation guards. Match the terse style of the 1.1.1 entry.

## Investigation targets

**Required**:
- `CLAUDE.md:60-70` — cross-platform-patterns table; the "Blocking-question tool" row sits in this range
- `CLAUDE.md:20-35` — skill-architecture prose mentioning `AskUserQuestion`
- `agent_docs/adding-skills.md:1-30` — checklist; step 3 has the parenthetical to update
- `agent_docs/local-dev.md:30-65` — "Smoke tests" section + "RP gotchas" boundary
- `CHANGELOG.md:1-15` — current head; 1.1.2 entry format

**Optional**:
- `plugins/flow-next/.claude-plugin/plugin.json` / `.codex-plugin/plugin.json` — version bump (1.1.1 → 1.1.2) if convention requires; check `scripts/bump.sh` or recent release commits for precedent

## Key context

- The CHANGELOG entry version (1.1.2) is contingent on the manifest version bump. If the marketplace repo convention bumps manifests via `scripts/bump.sh patch flow-next` (precedent from fn-37 / fn-43), this task may need to invoke it. Recent release pattern: `chore(install-codex): copy top-level templates/ dir (R20 install gap, 1.1.1)` shows patch-bump commits.
- The manual smoke (R8) requires running `/flow-next:setup` on Codex Desktop Default mode AND Codex CLI. This task captures the procedure in `agent_docs/local-dev.md`; the actual smoke runs are operator-level (cannot be CI-automated). Record observed behavior in the subsection or in the task summary so future agents can replicate.
- Depends on fn-45.1 having landed (sync transform in place). Verify the Codex mirror behavior before writing the local-dev.md subsection — the docs reflect actual mirror behavior, not aspirational.

## Acceptance

- [ ] `CLAUDE.md:63` "Blocking-question tool" row updated to describe the plain-text numbered-prompt transform.
- [ ] `agent_docs/adding-skills.md` step 3 parenthetical updated to match.
- [ ] `agent_docs/local-dev.md` gains "## Codex plain-text prompt smoke" subsection (after line 59, before "## RP gotchas") with manual verification procedure for Codex Desktop Default mode + Codex CLI.
- [ ] `CHANGELOG.md` gains `[flow-next 1.1.2]` block above `[flow-next 1.1.1]` summarizing the transform + validation guards in keep-a-changelog format.
- [ ] Manual smoke executed (or explicitly deferred with a TODO in the task summary if Codex Desktop / CLI unavailable to the implementer) — confirm `/flow-next:setup` on Codex Desktop Default mode + CLI prints numbered plain-text consent prompt with `Other — type your own answer` final option, no `request_user_input` call attempt.
- [ ] Version manifests bumped 1.1.1 → 1.1.2 if convention requires (check `scripts/bump.sh` precedent).
- [ ] `./scripts/sync-codex.sh` re-run after any canonical doc edits; mirror clean.

## Done summary
Shipped fn-45 release docs + CHANGELOG 1.1.2: CLAUDE.md cross-platform row + adding-skills.md step 3 + local-dev.md "Codex plain-text prompt smoke" subsection (5-option invariant: 4 canonical + `Other` from transform) + CHANGELOG entry summarizing the fn-45 spec (sync transform, abort option, setup preserve-existing). Version bumped 1.1.1 → 1.1.2 across 5 manifest surfaces. Manual Codex Desktop / CLI smoke DEFERRED to a Codex-equipped operator (procedure documented).
## Evidence
- Commits: a86c885, cb7c569, cdcd9dbf86e23f1e337dacb561cc4b76c835fdbc
- Tests: ./scripts/bump.sh patch flow-next (5 manifests bumped + sync ran clean), ./scripts/sync-codex.sh (all guards pass, idempotent across two runs), bash plugins/flow-next/scripts/smoke_test.sh (130/130 pass), R6 grep guard (fn-45.1) verified: no forbidden request_user_input prose patterns survive in Codex mirror under plugins/flow-next/codex/skills/ (excluding /templates/), flowctl codex impl-review fn-45-codex-plain-text-fallback-for.4 --base 7782a9e: NEEDS_WORK -> SHIP (cycle 2)
- PRs: