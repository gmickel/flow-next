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

Updated user-facing docs and CHANGELOG for the fn-45 release (1.1.2). `CLAUDE.md:63` "Blocking-question tool" cross-platform row now describes the `sync-codex.sh` plain-text numbered-prompt transform (with `N+1. Other — type your own answer` final option) and explicitly notes the Codex mirror never calls `request_user_input` (Plan-mode-only per openai/codex#10384/#11536/#12694). `agent_docs/adding-skills.md` step 3 parenthetical updated to match. `agent_docs/local-dev.md` gains a "Codex plain-text prompt smoke" subsection after line 59 (before "RP gotchas") with manual verification steps for Codex Desktop Default mode AND Codex CLI — including the explicit 5-option invariant for the setup migration prompt (4 canonical options including `abort` per fn-45.2 + the 5th `Other — type your own answer` added by the fn-45.1 transform), the grep guard, and the regression failure mode. `CHANGELOG.md` gains a `[flow-next 1.1.2]` block above the 1.1.1 entry summarizing the fn-45 release: prose-only `request_user_input` removal (frontmatter `allowed-tools:` listings are intentional residue, out of scope), `flow-next-setup` abort option, and `flow-next-setup` preserve-existing config + repo-custom docs. Version bumped 1.1.1 → 1.1.2 across the 5 manifest surfaces via `scripts/bump.sh patch flow-next`. The actual manual smoke against Codex Desktop + CLI is **DEFERRED** — the implementer (Claude Code) does not have access to Codex Desktop or Codex CLI in this conversation; the procedure is documented in `agent_docs/local-dev.md` for a Codex-equipped operator to execute on the 1.1.2 install. Codex impl-review cycled NEEDS_WORK → SHIP: the first pass caught a smoke-doc invariant drift (Original wording described the rendered prompt as 4 options with `4. abort` final, missing the 5th `Other — type your own answer` from the transform); fix-cycle aligned the smoke invariants and tightened the CHANGELOG `rui_refs` scope claim to prose-only.

## Evidence

- Commits: a86c885 (docs + CHANGELOG + bump), cb7c569 (review-fix: align smoke-prompt invariants + tighten CHANGELOG scope)
- Tests:
  - `./scripts/bump.sh patch flow-next` — 5 manifest surfaces bumped 1.1.1 → 1.1.2; auto-ran sync-codex.sh; all validation guards passed
  - `./scripts/sync-codex.sh` — exit 0; all guards pass (`No request_user_input refs in Codex skill prose`)
  - Idempotency: `find plugins/flow-next/codex -type f -name '*.md' -exec md5sum {} + | sort | md5sum` IDENTICAL across two consecutive sync runs (a0306ce0ef89e59158afd78f654ccad7)
  - Standalone R6 grep guard: `grep -rE '`request_user_input`|request_user_input tool|request_user_input\(|MUST use `request_user_input`|ONLY ask via `request_user_input`' plugins/flow-next/codex/skills/ | grep -v '/templates/'` returns empty
  - `bash plugins/flow-next/scripts/smoke_test.sh` — 130/130 pass
  - Codex impl-review fn-45-codex-plain-text-fallback-for.4 --base 7782a9e: VERDICT=NEEDS_WORK → VERDICT=SHIP (cycle 2, after 1 fix commit)
- Deferred: manual Codex Desktop Default mode + Codex CLI smoke (R8) — implementer cannot run Codex in this conversation; procedure documented in `agent_docs/local-dev.md` for operator execution post-1.1.2 install
- PRs: —
