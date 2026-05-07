---
satisfies: [R1, R2, R3, R27]
---

## Description

Scaffold the new skill at `plugins/flow-next/skills/flow-next-make-pr/` (4 files: `SKILL.md`, `workflow.md`, `phases.md`, plus the `mermaid-rules.md` ref file written in Task 5). Implement Phase 0 pre-flight: epic resolution from arg or branch-match, base-branch detection cascade, all-tasks-done validation, existing-PR refusal. Plus the slash command file at `commands/flow-next/make-pr.md`.

**Size:** M (4-5 small files, scaffolding + Phase 0 logic)
**Files:** `plugins/flow-next/skills/flow-next-make-pr/{SKILL.md, workflow.md, phases.md}`, `plugins/flow-next/commands/flow-next/make-pr.md`

## Approach

- **Template = `flow-next-audit`.** Multi-file structure (SKILL+workflow+phases), NOT-Ralph-blocked pattern, mode-detection block. Copy structure verbatim, replace content.
- **SKILL.md frontmatter** (5-line block per `flow-next-audit/SKILL.md:1-6`):
  ```yaml
  ---
  name: flow-next-make-pr
  description: Render a cognitive-aid PR body from flow-next state and open via gh. Triggers on /flow-next:make-pr...
  user-invocable: false
  allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task
  ---
  ```
- **NO Ralph-block guard at top.** Per spec R24, this skill IS Ralph-safe (autonomous-loop terminus). Pattern is the inverse of `flow-next-prospect/SKILL.md:37-46` — instead detect Ralph (`FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH`) and force `--draft` + skip `AskUserQuestion`. Document this in workflow.md.
- **Mode detection block** following `flow-next-audit/SKILL.md:30-42` shape, but parsing flag list (not single token): `--draft`, `--ready`, `--no-mermaid`, `--base <ref>`, `--memory`, `--dry-run`. Strip recognized tokens from `$ARGUMENTS`; remainder is optional epic-id.
- **Pre-check setup-version block** boilerplate verbatim from `flow-next-audit/SKILL.md:87-99`.
- **flowctl path resolution** opens with the standard 3-line block: `FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"`.
- **Phase 0 in workflow.md:**
  - Resolve `$EPIC_ID` from arg → match current branch name against `.flow/epics/*.json` `branch_name` field → ask user if neither resolves (or hard-error in Ralph).
  - Base-branch detection cascade: `--base` flag → `origin/main` → `main` → `origin/master` → `master` → ask (interactive) / hard-error (Ralph). Verify via `git rev-parse --verify --quiet <ref>`.
  - Validate: `git rev-parse --verify HEAD`, `git merge-base --is-ancestor <base> HEAD` (HEAD is ahead of base), all tasks under epic in `done` (warn-and-prompt if not).
  - **Existing-PR refusal — MUST filter on `.state == "OPEN"`** (validated empirically during fn-42 spike). `gh pr view --json url,state,number 2>/dev/null` returns rc=0 for CLOSED and MERGED PRs just as readily as OPEN — a bare "JSON returned = refuse" check would false-positive on reused branches (branch had a previous PR that was closed without merge or was merged + pushed-again to). Correct check: `EXISTING=$(gh pr view --json url,state,number 2>/dev/null | jq -r 'select(.state == "OPEN") | .url')` — refuse iff `EXISTING` is non-empty, with hint to use `/flow-next:resolve-pr`. Empty `EXISTING` (no PR, or only CLOSED/MERGED PRs on branch) = clean to proceed. Exit 1 + "no pull requests found" stderr from `gh pr view` is also clean-to-proceed.
  - **`gh` pre-flight:** `command -v gh && gh auth status --hostname github.com >/dev/null` before anything else. Surface install/auth instructions if missing.
- **Slash command file** at `commands/flow-next/make-pr.md` mirrors `commands/flow-next/audit.md:1-14` byte-for-byte except name/desc/argument-hint. 14-line stanza with `# IMPORTANT: This command MUST invoke the skill flow-next-make-pr` + `**Arguments:** $ARGUMENTS` + one-sentence pass-through. NO flag parsing, NO logic.
- **Tool naming convention (cross-platform):** canonical files use Claude-native names (`AskUserQuestion`, `Task`). Don't write inline cross-platform tables. `sync-codex.sh` rewrites for Codex. Optional one-line maintainer breadcrumb is fine.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-audit/SKILL.md:1-99` — full template (frontmatter, mode detection, pre-check, flowctl path resolution)
- `plugins/flow-next/skills/flow-next-audit/workflow.md:1-50` — phase structure pattern
- `plugins/flow-next/commands/flow-next/audit.md:1-14` — slash command template
- `plugins/flow-next/skills/flow-next-prospect/SKILL.md:37-46` — Ralph-block pattern (we're the INVERSE — detect Ralph but proceed)

**Optional:**
- `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md:78` — `gh pr view` PR-existence check pattern
- `plugins/flow-next/skills/flow-next-strategy/SKILL.md:64-73` — alternate Ralph-block message style

## Acceptance

- [ ] `plugins/flow-next/skills/flow-next-make-pr/SKILL.md` exists with correct frontmatter (`name`, `description` matching the spec's slash command, `user-invocable: false`, `allowed-tools` listing the right tools), pre-check block, flowctl path resolution, mode-detection block parsing all flags listed in API Contracts.
- [ ] `plugins/flow-next/skills/flow-next-make-pr/workflow.md` documents Phase 0 pre-flight: epic resolution, base detection cascade, branch-validity checks, existing-PR refusal via `gh pr view --json url,state` **filtered on `.state == "OPEN"` (jq select)** — closed/merged PRs on the branch must NOT trigger refusal (validated empirically during fn-42 spike); gh pre-flight (`command -v` + `gh auth status`).
- [ ] `plugins/flow-next/skills/flow-next-make-pr/phases.md` documents the 5-phase outline (Phase 0 → 1 → 2 → 3 → 4 → 5) with Done-when checklists per phase.
- [ ] `plugins/flow-next/commands/flow-next/make-pr.md` mirrors `audit.md` shape (14-line stanza, no logic).
- [ ] Skill is **NOT** Ralph-blocked: no `FLOW_RALPH`/`REVIEW_RECEIPT_PATH` exit-2 guard at top of SKILL.md. Instead workflow.md documents Ralph behavior — detect env, skip `AskUserQuestion`, force `--draft`, emit PR URL to stdout.
- [ ] Skill prose includes the explicit hallucination-guardrail callout (10 mitigations from practice-scout findings — folded into Task 3 spec for the body-rendering side, but Phase 0 prose includes the meta-rule: "every claim in the body must trace to a structured field in the export-cognitive-aid payload — never fabricate file paths, SHAs, R-ID attributions, or 'why' reasoning").

## Done summary

_(populated by /flow-next:work after task completes)_

## Evidence

_(populated by /flow-next:work after task completes)_
