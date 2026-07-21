# Flow-Next Usage Guide

Task tracking for AI agents. All state lives in `.flow/`.

**Plugin-mode repos (Claude Code, `setup_mode: "plugin"`):** `flowctl` is already on the agent's PATH - read every `.flow/bin/flowctl` below as bare `flowctl` (plugin mode has no `.flow/bin/`).

## CLI

```bash
.flow/bin/flowctl --help              # All commands
.flow/bin/flowctl <cmd> --help        # Command help
```

## IDs

- Specs: `fn-N-slug` where slug is derived from title (e.g., fn-1-add-oauth, fn-2-fix-login-bug)
- Tasks: `fn-N-slug.M` (e.g., fn-1-add-oauth.1, fn-2-fix-login-bug.2)

**Backwards compatibility**: Legacy formats `fn-N`, `fn-N-xxx`, `fn-N.M`, and `fn-N-xxx.M` still work.

## Common Commands

The typical flow. Everything else (deps, block/reset, memory, glossary, config, tracker sync, checkpoints, Ralph): `.flow/bin/flowctl --help` and `.flow/bin/flowctl <cmd> --help`.

```bash
.flow/bin/flowctl list                          # all specs + tasks grouped
.flow/bin/flowctl show fn-1-add-oauth.2         # spec or task detail (cat for raw markdown)
.flow/bin/flowctl ready --spec fn-1-add-oauth   # tasks ready to work on
.flow/bin/flowctl spec create --title "..." --branch fn-1-add-oauth --json
.flow/bin/flowctl spec set-plan fn-1-add-oauth --file plan.md
.flow/bin/flowctl task create --spec fn-1-add-oauth --title "..." --deps fn-1-add-oauth.1 --description-file d.md --acceptance-file a.md --satisfies R1,R3
.flow/bin/flowctl start fn-1-add-oauth.2        # claim task
.flow/bin/flowctl done fn-1-add-oauth.2 --summary-file s.md --evidence-json e.json
.flow/bin/flowctl task reset fn-1-add-oauth.2   # back to todo
.flow/bin/flowctl validate --all                # check structure
```

## Orchestration & model steering

flow-next skills are prompts the host agent executes — so you (the host) can route work across model families with zero code. **Defaults are pre-tuned; none of this is required** — reach for it only when your model mix, subscriptions, or taste differ. Full guide: [`docs/orchestration.md`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/docs/orchestration.md) · https://flow-next.dev/orchestration/

**Headless CLI bridges** — drive another harness from a Bash call with a *self-contained* prompt (full context in, digest back). The delegate writes code and never touches git; no recursive delegation.

```bash
# codex exec DEFAULTS to a read-only sandbox. Redirect stdin from /dev/null —
# spawned by another agent it hangs indefinitely on inherited non-TTY stdin.
# ALWAYS pass --skip-git-repo-check: outside a trusted git repo codex refuses in ~1s
# with the error only in the log — a fire-and-forget caller sees a clean, silent failure.
codex exec -s read-only --skip-git-repo-check "<self-contained investigation prompt>" </dev/null               # read-only investigation
# WRITE mode: the flag also disables codex's git-repo preflight — your rollback boundary.
# Assert the intended workspace FIRST (or `git init` a scratch dir), so the flag only
# suppresses the silent-refusal failure mode, never the safety check:
[ "$(git rev-parse --show-toplevel 2>/dev/null)" = "<intended-repo-root>" ] && \
codex exec --sandbox workspace-write --skip-git-repo-check -o out.md "<self-contained impl prompt>" </dev/null  # implement + capture result via -o/--output-last-message (never stdout scraping; --full-auto is deprecated)

# cursor-agent: -p print mode; --force actually APPLIES edits (else proposed-only).
# Run it INSIDE a git repo (`git init` scratch dirs first): in a non-repo dir it blocks on an
# interactive workspace-trust prompt and exits "successfully" with empty output.
CURSOR_API_KEY=... cursor-agent -p --force --model <id> "<prompt>"                        # model IDs are volatile → cursor-agent --list-models

# claude -p: the same bridge in REVERSE — drive Claude headlessly from a Codex/Cursor host.
claude -p "<self-contained prompt>" --output-format text --allowedTools "Read,Bash" </dev/null  # prompt BEFORE --allowedTools (variadic — it swallows trailing args); edits need --permission-mode acceptEdits

# grok: xAI's Grok Build CLI (v0.2.x alpha) - a full headless EDITING agent, same class as codex
# exec / cursor-agent, on its own quota. FLAGS BEFORE -p: `-p/--single` consumes the NEXT token as
# the prompt, so `grok -p --always-approve "..."` misparses (live-verified failure mode).
grok -m grok-4.5-high -p "<self-contained prompt>" </dev/null                              # read-only one-shot: prints and exits
grok --permission-mode acceptEdits -m grok-4.5-high -p "<self-contained prompt>" </dev/null  # WRITE mode (edits files - run inside a trusted git dir; --always-approve = blanket). Extras: --check self-verify loop, --best-of-n N parallel attempts, --json-schema structured output, --reasoning-effort. Grok 4.5 = fast + cheap first-draft; route to bulk/implementation, not UI or final taste-critical work.
```

The codex bridge also works FROM a Codex host (same-family self-bridge): `codex exec -m gpt-5.6-terra -c model_reasoning_effort=medium "<prompt>"` steers a different GPT tier reliably even where `spawn_agent`/Multi-Agent-V2 per-spawn model steering is broken (openai/codex#33268 and friends, Jul 2026). Keep the child prompt flat - no nested subagents.

Harness-relative: every direction works — from Claude Code the bridges are `codex exec` / `cursor-agent`; from Codex or Cursor they are `claude -p` / the other CLI. Any harness that can run Bash can conduct the others.

**flow-next shortcuts** — the same bridges, packaged as config:

```bash
# The raw codex exec bridge above is the interactive route. delegate:codex is the same
# bridge with deterministic rails for unattended loops; its task and spec paths are the brief.
# Delegate implementation to codex (host keeps gating/git/review; codex only writes code)
.flow/bin/flowctl config set work.delegate codex     # value MUST be `codex` to activate (OFF by default, consent-gated)
# …or per-run, no config:  /flow-next:work fn-1-add-oauth delegate:codex
# Steer the delegate: work.delegateModel (default gpt-5.6-terra, passed as -m) +
# work.delegateEffort (default medium, passed as -c model_reasoning_effort=)

# Cross-family review — the model that writes is never the model that reviews
.flow/bin/flowctl config set review.backend codex                                 # or cursor:composer-2.5
.flow/bin/flowctl task set-backend fn-1-add-oauth.3 --review cursor:composer-2.5   # per-task review: override
```

**Prompted orchestration** — describe the policy; the host judges per item, no parameter required:

```text
Work the ready specs — decide per spec by complexity: auth/migration tasks you
implement yourself; plain CRUD is delegated (delegate:codex). Reviews from codex either way.

Run /flow-next:work fn-12 with delegate:codex. If a task's review comes back
NEEDS_WORK twice, stop delegating it and implement it yourself on the session model.
```

None of these pairings are fixed — any stage of any flow-next pipeline (research, implementation, review, QA) can route to whatever harness you can reach from Bash: describe the arrangement in the invocation or your instruction files and the host builds it.

Make any of this durable by writing it into `CLAUDE.md`/`AGENTS.md` — the host reads your instruction files every session and flow-next skills inherit them automatically.

## Workflow

1. `.flow/bin/flowctl specs` - list all specs
2. `.flow/bin/flowctl ready --spec fn-N-slug` - find available tasks
3. `.flow/bin/flowctl start fn-N-slug.M` - claim task
4. Implement the task
5. `.flow/bin/flowctl done fn-N-slug.M --summary-file ... --evidence-json ...` - complete

If a sandbox denies `git commit`, still complete `done` with the evidence you have and record the restriction in the summary - never block the task on a commit you cannot make.

## Verification scoping

Per-task Quick commands list FOCUSED suites for the files you touch - that is what workers baseline and verify per task. The FULL suite runs once at the final gate; prefer the repo's parallel test entrypoint when one exists (see the project instruction file for the canonical command).

## Evidence JSON Format

```json
{"commits": ["<sha>"], "tests": ["<command>"], "prs": []}
```

## Parallel Worktrees

Runtime state (status, assignee, etc.) is stored in `.git/flow-state/` (or `$FLOW_STATE_DIR` when set), shared across worktrees.

## Pre-1.0 layout porting

Rename `.flow/epics/` to `.flow/specs/` (merge JSON into an existing `specs/` if present). Rewrite keys: `meta.json` `next_epic` -> `next_spec` and `schema_version` -> 3; each task JSON `epic`/`epic_id` -> `spec`/`spec_id`; write `.flow/.flow_version` with payload `1.0.0`. Run `.flow/bin/flowctl validate --all`.

## More Info

- Human docs: https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/docs/flowctl.md
- CLI reference: `.flow/bin/flowctl --help`
