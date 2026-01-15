---
name: flow-next-work
description: Execute a Flow epic or task systematically with git setup, task tracking, quality checks, and commit workflow. Use when implementing a plan or working through a spec. Triggers on /flow-next:work with Flow IDs (fn-1, fn-1.2).
---

# Flow work

Execute a plan systematically. Focus on finishing.

Follow this skill and linked workflows exactly. Deviations cause drift, bad gates, retries, and user frustration.

**IMPORTANT**: This plugin uses `.flow/` for ALL task tracking. Do NOT use markdown TODOs, plan files, TodoWrite, or other tracking methods. All task state must be read and written via `flowctl`.

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:
```bash
FLOWCTL="${CLAUDE_PLUGIN_ROOT}/scripts/flowctl"
$FLOWCTL <command>
```

**Hard requirements (non-negotiable):**
- You MUST run `flowctl done` for each completed task and verify the task status is `done`.
- You MUST stage with `git add -A` (never list files). This ensures `.flow/` and `scripts/ralph/` (if present) are included.
- Do NOT claim completion until `flowctl show <task>` reports `status: done`.
- Do NOT invoke `/flow-next:impl-review` until tests/Quick commands are green.

**Role**: execution lead, plan fidelity first.
**Goal**: complete every task in order with tests.

## Ralph Mode Rules (always follow)

If `REVIEW_RECEIPT_PATH` is set or `FLOW_RALPH=1`:
- **Must** use `flowctl done` and verify task status is `done` before committing.
- **Must** stage with `git add -A` (never list files).
- **Do NOT** use TodoWrite for tracking.

## Input

Full request: $ARGUMENTS

Accepts:
- Flow epic ID `fn-N` to work through all tasks
- Flow task ID `fn-N.M` to work on single task
- Markdown spec file path (creates epic from file, then executes)
- Idea text (creates minimal epic + single task, then executes)
- Chained instructions like "then review with /flow-next:impl-review"

Examples:
- `/flow-next:work fn-1`
- `/flow-next:work fn-1.3`
- `/flow-next:work docs/my-feature-spec.md`
- `/flow-next:work Add rate limiting`
- `/flow-next:work fn-1 then review via /flow-next:impl-review`

If no input provided, ask for it.

## FIRST: Parse Options or Ask Questions

Check available backends and configured preference:
```bash
HAVE_RP=$(which rp-cli >/dev/null 2>&1 && echo 1 || echo 0)
HAVE_CODEX=$(which codex >/dev/null 2>&1 && echo 1 || echo 0)

# Check configured backend (priority: env > config)
CONFIGURED_BACKEND="${FLOW_REVIEW_BACKEND:-}"
if [[ -z "$CONFIGURED_BACKEND" ]]; then
  CONFIGURED_BACKEND="$($FLOWCTL config get review.backend 2>/dev/null | jq -r '.value // empty')"
fi
```

### Option Parsing (skip questions if found in arguments)

Parse the arguments for these patterns. If found, use them and skip corresponding questions:

**Branch mode**:
- `--branch=current` or `--current` or "current branch" or "stay on this branch" → current branch
- `--branch=new` or `--new-branch` or "new branch" or "create branch" → new branch
- `--branch=worktree` or `--worktree` or "isolated worktree" or "worktree" → isolated worktree

**Review mode**:
- `--review=codex` or "review with codex" or "codex review" or "use codex" → Codex CLI (GPT 5.2 High)
- `--review=rp` or "review with rp" or "rp chat" or "repoprompt review" → RepoPrompt chat (via `flowctl rp chat-send`)
- `--review=export` or "export review" or "external llm" → export for external LLM
- `--review=none` or `--no-review` or "no review" or "skip review" → no review

### If options NOT found in arguments

**Skip review question if**: Ralph mode (`FLOW_RALPH=1`) OR backend already configured (`CONFIGURED_BACKEND` not empty). In these cases, only ask branch question:

```
Quick setup: Where to work?
a) Current branch  b) New branch  c) Isolated worktree

(Reply: "a", "current", or just tell me)
```

**Otherwise**, output questions based on available backends (do NOT use AskUserQuestion tool):

**If both rp-cli AND codex available:**
```
Quick setup before starting:

1. **Branch** — Where to work?
   a) Current branch
   b) New branch
   c) Isolated worktree

2. **Review** — Run Carmack-level review after?
   a) Yes, Codex CLI (cross-platform, GPT 5.2 High)
   b) Yes, RepoPrompt chat (macOS, visual builder)
   c) Yes, export for external LLM (ChatGPT, Claude web)
   d) No

(Reply: "1a 2a", "current branch, codex review", or just tell me naturally)
```

**If only rp-cli available:**
```
Quick setup before starting:

1. **Branch** — Where to work?
   a) Current branch
   b) New branch
   c) Isolated worktree

2. **Review** — Run Carmack-level review after?
   a) Yes, RepoPrompt chat
   b) Yes, export for external LLM
   c) No

(Reply: "1a 2a", "current branch, export review", or just tell me naturally)
```

**If only codex available:**
```
Quick setup before starting:

1. **Branch** — Where to work?
   a) Current branch
   b) New branch
   c) Isolated worktree

2. **Review** — Run Carmack-level review after?
   a) Yes, Codex CLI (GPT 5.2 High)
   b) Yes, export for external LLM
   c) No

(Reply: "1a 2a", "current branch, codex", or just tell me naturally)
```

**If neither rp-cli nor codex available:**
```
Quick setup: Where to work?
a) Current branch  b) New branch  c) Isolated worktree

(Reply: "a", "current", or just tell me)
```

Wait for response. Parse naturally — user may reply terse or ramble via voice.

**Defaults when empty/ambiguous:**
- Branch = `new`
- Review = configured backend if set, else `codex` if available, else `rp` if available, else `none`

**Defaults when no review backend available:**
- Branch = `new`
- Review = `none`

**Do NOT read files or write code until user responds.**

## Workflow

After setup questions answered, read [phases.md](phases.md) and execute each phase in order.

**Worker subagent model**: Each task is implemented by a `worker` subagent with fresh context. This prevents context bleed between tasks and keeps re-anchor info with the implementation. The main conversation handles task selection and looping; worker handles implementation, commits, and reviews.

If user chose review, pass the review mode to the worker. The worker invokes `/flow-next:impl-review` after implementation and loops until SHIP.

## Guardrails

- Don't start without asking branch question
- Don't start without plan/epic
- Don't skip tests
- Don't leave tasks half-done
- Never use TodoWrite for task tracking
- Never create plan files outside `.flow/`
