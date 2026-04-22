## Description

Wire Copilot into the Ralph autonomous loop. Covers ralph-guard.py (blocks direct `copilot` usage, requires going via flowctl wrapper), ralph-init templates (config.env, prompt_plan/work/completion, ralph.sh), and the ralph-init skill itself.

**Size:** M
**Files:**
- `plugins/flow-next/scripts/hooks/ralph-guard.py`
- `plugins/flow-next/skills/flow-next-ralph-init/SKILL.md`
- `plugins/flow-next/skills/flow-next-ralph-init/templates/config.env`
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh`
- `plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_plan.md`
- `plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_work.md`
- `plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_completion.md`

## Approach

**ralph-guard.py:**
- Mirror the codex block at `plugins/flow-next/scripts/hooks/ralph-guard.py:247-269`. Add a copilot block that:
  - Blocks direct `copilot` invocations (detect `\bcopilot\b` in command, except when prefixed by `flowctl\s+copilot` or `${FLOWCTL}.*copilot`)
  - Blocks `--continue` flag on any copilot invocation (conflicts with parallel sessions; per spec risk #1)
- Add parallel state key `copilot_review_succeeded` (like `codex_review_succeeded` at ralph-guard.py:16, 48, 59, 316, 320, 427-438, 490, 514, 530). Extend the OR gate at line 315-322: `state["chat_send_succeeded"] or state["codex_review_succeeded"] or state["copilot_review_succeeded"]`.

**flow-next-ralph-init skill:**
- `SKILL.md` lines 29-48, 82-85: add `HAVE_COPILOT` detection alongside `HAVE_RP` / `HAVE_CODEX`. Add copilot as a valid answer to the backend-choice question. Map answer to `WORK_REVIEW=copilot` / `PLAN_REVIEW=copilot` / `COMPLETION_REVIEW=copilot`.
- `templates/config.env` lines 7-26: document copilot alongside rp/codex. Add knobs:
  - `FLOW_COPILOT_MODEL` (default `claude-opus-4.5`)
  - `FLOW_COPILOT_EFFORT` (default `high`)
  - `FLOW_COPILOT_EMBED_MAX_BYTES` (default 512000)
  - **Note (task-3 finding):** `FLOW_COPILOT_MODEL`/`FLOW_COPILOT_EFFORT` flow through `_resolve_copilot_model_effort()` (env > arg > default cascade) and land in the receipt (`model`, `effort` keys). No CLI flags — env-only. Document accordingly in config.env comments.
<!-- Updated by plan-sync: task 3 landed env-cascade resolver; receipts stamp resolved values -->
- `templates/ralph.sh`:
  - Lines 227-233 (UI display): add copilot to backend display strings
  - Lines 277-312 (spinner messages for plan/impl/completion review UI): add copilot variants
  - Lines 383-390 (default + export logic): add copilot branch to export `FLOW_REVIEW_BACKEND=copilot` etc.
  - Line 497 (status keys)
  - Lines 925-957: export chosen backend to env per gate (add copilot)
  - Lines 1061-1098 (receipt verification): currently `[[ "$PLAN_REVIEW" == "rp" || "$PLAN_REVIEW" == "codex" ]]` — add `|| ... == "copilot"` to all three `PLAN_REVIEW` / `WORK_REVIEW` / `COMPLETION_REVIEW` gates.
- `templates/prompt_plan.md` lines 5-50: add `If PLAN_REVIEW=copilot: run /flow-next:plan-review ... --review=copilot` branch
- `templates/prompt_work.md` lines 6-35: add `--review=copilot` variant alongside codex
- `templates/prompt_completion.md` (same pattern — repo-scout inferred; grep to confirm exact lines)

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/hooks/ralph-guard.py:247-269` — codex block to mirror
- `plugins/flow-next/scripts/hooks/ralph-guard.py:315-322` — OR gate for review-succeeded state
- `plugins/flow-next/skills/flow-next-ralph-init/SKILL.md` — backend detection + question block
- `plugins/flow-next/skills/flow-next-ralph-init/templates/config.env` — full file
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh:1061-1098` — receipt verification gates
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh:925-957` — backend export logic

**Optional:**
- `plans/ralph-e2e-notes.md` — for context on ralph testing (no updates required here — task 7 handles docs)

## Acceptance

- [ ] ralph-guard.py blocks bare `copilot` invocations (not prefixed by flowctl) and returns a helpful error
- [ ] ralph-guard.py blocks any copilot command containing `--continue`
- [ ] `copilot_review_succeeded` state key is tracked on successful `flowctl copilot *-review` calls and gates downstream hooks
- [ ] `config.env` documents all three `FLOW_COPILOT_*` env vars with defaults
- [ ] `ralph.sh` treats `copilot` as valid for `PLAN_REVIEW`, `WORK_REVIEW`, `COMPLETION_REVIEW`
- [ ] `prompt_plan.md` / `prompt_work.md` / `prompt_completion.md` all have a copilot branch
- [ ] ralph-init skill offers Copilot as a choice when `copilot` CLI is on PATH
- [ ] Unit-equivalent: `PLAN_REVIEW=copilot WORK_REVIEW=copilot bash ralph.sh` (ralph smoke path) does not hit "unknown backend" errors

## Done summary

(filled in when task completes)

## Evidence

(filled in when task completes)
