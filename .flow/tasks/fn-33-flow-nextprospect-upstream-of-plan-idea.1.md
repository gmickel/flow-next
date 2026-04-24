---
satisfies: [R1, R5, R8, R17]
---

## Description

Skeleton for the `/flow-next:prospect` skill plus Phase 0 (resume check) + Phase 1 (grounding snapshot) + the Ralph-block guard.

This task is the **early proof point** for the epic — if grounding can't produce a useful snapshot from a real repo, the whole generate-critique pipeline downstream is pointless. Ship this first with zero LLM involvement; verify the snapshot is sane before wiring Phases 2-5.

**Size:** M
**Files:**
- `plugins/flow-next/commands/flow-next/prospect.md` (new — slash command entry)
- `plugins/flow-next/skills/flow-next-prospect/SKILL.md` (new — skill manifest, thin index)
- `plugins/flow-next/skills/flow-next-prospect/workflow.md` (new — Phase 0 + Phase 1 prose)

## Approach

- Multi-file skill layout following `flow-next-resolve-pr/` precedent (SKILL.md as thin index, workflow.md carries phases).
- Frontmatter: `name: flow-next-prospect`, `description: ...` (action-oriented), `user-invocable: false`, `allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task` (inline skill — do NOT set `context: fork`).
- Ralph-block: copy verbatim pattern from `plugins/flow-next/skills/flow-next-impl-review/SKILL.md:217-222` — exit 2 when `REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1` set. Document in workflow.md that there's no env-var opt-in.
- Phase 0 resume check:
  - Glob `.flow/prospects/*.md`, filter by frontmatter `date` within 30 days.
  - For each candidate, try to parse frontmatter; mark `status: corrupt` if parse fails or required sections (`## Grounding snapshot`, `## Survivors`) are missing.
  - If 1+ active artifacts found, present via blocking-question tool: "extend | fresh | open #N". Corrupt artifacts shown in the list but not offered for extension.
  - Phase 0 exits early if user picks "open #N" (just prints artifact path).
- Phase 1 grounding with graceful degradation:
  - `git log --since="30 days ago" --name-only --pretty=format:` — skip with `scanned: none (no git)` if `.git` missing.
  - `flowctl epic list --status open --json` — skip with `scanned: none (no open epics)` if empty.
  - `CHANGELOG.md` first 50 lines — skip if absent.
  - `flowctl memory search "$focus_hint" --json` (if `memory.enabled=true` and focus present).
  - `.flow/memory/_audit/*.md` latest entry (if exists; read stale-flagged section only).
  - Focus-hint path resolution: if hint looks like a path (`plugins/flow-next/skills/`) and resolves to nothing, ask via blocking question whether to continue open-ended or narrow differently.
  - Output: structured 30-50 line snapshot (NOT raw file dumps) — titles and tags only for memory/epics; distilled for CHANGELOG.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md:217-222` — Ralph-block pattern to copy
- `plugins/flow-next/skills/flow-next-resolve-pr/SKILL.md` — multi-file skill layout template (thin-index style)
- `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md` — phase-by-phase workflow structure
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:78-92` — AskUserQuestion discipline
- `plugins/flow-next/skills/flow-next-impl-review/walkthrough.md:40-46` — platform tool table

**Optional:**
- `plugins/flow-next/skills/flow-next-plan/SKILL.md` — pre-check setup-version pattern
- `plugins/flow-next/commands/flow-next/*.md` — slash-command entry templates

## Key context

- Skill stays inline (no `context: fork`) so `AskUserQuestion` remains available — subagents can't call it (Claude Code issues #12890, #34592).
- Structured snapshots keep grounding context lean — titles + tags, not bodies. Bloated context measurably degrades downstream generation quality.

## Acceptance

- [ ] `/flow-next:prospect [hint]` is a valid slash command registered via `plugins/flow-next/commands/flow-next/prospect.md`.
- [ ] `SKILL.md` frontmatter correct: no `context: fork`, includes `AskUserQuestion` in allowed tools.
- [ ] Ralph-block guard matches fn-32 `--interactive` pattern byte-for-byte and exits 2 under `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH`.
- [ ] Phase 0 resume check: lists `.flow/prospects/*.md` from last 30 days with frontmatter parsed; corrupt artifacts marked but not offered for extension; blocking question routes user.
- [ ] Phase 1 grounding emits a structured 30-50-line snapshot; each data source has a graceful-degradation fallback (`scanned: none (reason)`).
- [ ] Manual smoke on the flow-next repo itself: `prospect DX` produces a readable grounding snapshot.

## Done summary
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
