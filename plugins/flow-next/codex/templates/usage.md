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
- Charts share the native `fn-N` domain with specs (never the same id)
- Tracker-keyed ids coexist and resolve (`wor-17-slug`, `gh-123-slug`, `gl-456-slug`). Default: `config set tracker.specIds tracker`.

**Backwards compatibility**: Legacy formats `fn-N`, `fn-N-xxx`, `fn-N.M`, and `fn-N-xxx.M` still work.

## Chart (optional pre-capture discovery)

One oversized/unclear idea whose **destination is nameable but route is not** (a direction like "make X more Y" is refused - narrow it or run prospect); one decision (`<chart-id>.D<n>`) per invocation; never a pilot stage. `chart frontier` is the sole work-mode selection input; `chart claim` then `chart resolve --answer-file` close it; every work invocation ends with one greppable `CHART_VERDICT=...` line. Chart never writes specs; capture ingests the briefing.

## Common Commands

The typical flow. Everything else (deps, block/reset, memory, glossary, config, tracker sync, checkpoints, Ralph): `.flow/bin/flowctl --help` and `.flow/bin/flowctl <cmd> --help`.

```bash
.flow/bin/flowctl list                          # all specs + tasks grouped
.flow/bin/flowctl show fn-1-add-oauth.2         # spec or task detail (cat for raw markdown)
.flow/bin/flowctl ready --spec fn-1-add-oauth   # tasks ready to work on
.flow/bin/flowctl spec create --title "..." --plan-file plan.md --json
.flow/bin/flowctl task create --spec fn-1-add-oauth --from-json tasks.json
# tasks.json: [{"title":"...","satisfies":["R1"]},{"title":"...","deps":[1]}]
# edit: set-description/set-acceptance/set-spec, set-plan
.flow/bin/flowctl start fn-1-add-oauth.2        # claim task
.flow/bin/flowctl done fn-1-add-oauth.2 --summary-file s.md --evidence-json e.json
.flow/bin/flowctl task reset fn-1-add-oauth.2   # back to todo
.flow/bin/flowctl validate --all                # check structure
```

## Orchestration & model steering

flow-next skills are prompts the host agent executes — so you (the host) can route work across model families with zero code. **Defaults are pre-tuned; none of this is required** — reach for it only when your model mix, subscriptions, or taste differ. Full guide: [`docs/orchestration.md`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/docs/orchestration.md) · https://flow-next.dev/orchestration/

**Tiers and reach.** A **tier** is what kind of model a job wants — `reviewer`, `implementer`, `fast scout`, `thinking scout`, or unset (the session model, and the majority). **Reach** is how *this* harness gets one: the in-session model, an in-host subagent, another CLI over a bridge, or not available. Write your preferences once as `<tier>: <model>` (optionally `at <effort>`) in `CLAUDE.md` / `AGENTS.md` — `$flow-next-setup` scaffolds the block commented out, and the model names are yours, verified against your own account. Routing precedence, highest first: an explicit argument in the invocation, then that routing block, then the agent definition's own default, then the session model — a model this harness cannot reach falls back to the session model, says so once, and continues. Tier definitions: [`docs/orchestration.md`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/docs/orchestration.md#tiers--what-kind-of-model-a-job-wants); per-harness reach: [`docs/reach/`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/docs/reach/README.md).

**Headless CLI bridges** — drive another harness from a Bash call with a *self-contained* prompt (full context in, digest back). **Safety rule for every recipe below: the bridged child writes code; the host keeps git, judgment, and the verdict.** The child never commits, never decides scope, never issues a review verdict, and never spawns a bridge of its own.

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
# Model + effort are separate flags: `-m <model> --reasoning-effort high` (NOT a fused `-m <model>-high`).
grok -m <model> --reasoning-effort high -p "<self-contained prompt>" </dev/null             # read-only one-shot
grok --always-approve --no-plan -m <model> --reasoning-effort high -p "<self-contained prompt>" </dev/null  # WRITE mode (blanket; trusted git dir ONLY - acceptEdits skips Bash and silently truncates shell-using tasks). Extras: --check, --best-of-n N, --json-schema. Ask the CLI what it offers (`grok --help`, host catalog) rather than copying an identifier from a doc.
```

The codex bridge also works FROM a Codex host (same-family self-bridge): `codex exec -m <model> -c model_reasoning_effort=<effort> "<prompt>"` steers a different tier of the same family reliably even where `spawn_agent`/Multi-Agent-V2 per-spawn model steering is broken (openai/codex#33268 and friends, Jul 2026). Keep the child prompt flat - no nested subagents.

**Which tier to bridge to:** on well-specified work a value-tier implementer matches a strong-tier one on correctness at roughly two-thirds the wall clock, so send clear, well-scoped tasks to the value tier and escalate to the strong tier only for the genuinely gnarly ones. Spec quality is what makes that trade safe — a vague brief burns the saving on rework.

**Thin-wrapper recipe:** a quick interactive bridge call can stay raw. For a long-running, unattended, or parallel bridge, dispatch a thin fast-tier subagent that composes the self-contained prompt, runs the bridge **in the foreground**, verifies non-empty/parseable output, repairs environment or flag failures once, and returns only a digest. The wrapper never changes the task, model, or verdict and never delegates recursively; judgment stays with the host.

Harness-relative: every direction works — from Claude Code the bridges are `codex exec` / `cursor-agent`; from Codex or Cursor they are `claude -p` / the other CLI. Any harness that can run Bash can conduct the others.

**Cursor host** — agent-frontmatter tiering is ignored on Cursor; routing lives in the AGENTS.md routing block plus the model named in the dispatch itself (setup scaffolds the block). Distinct from the headless `cursor` CLI backend below. Full reach page: [`docs/reach/cursor.md`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/docs/reach/cursor.md).

- **Naming a model:** Cursor takes its own identifiers, and they are volatile — ask the harness (`cursor-agent --list-models`, host catalog) instead of copying one from a document.
- **Tier degrade:** `agents/*.md` family aliases resolve to **inherit** (the session model) on Cursor; no alias rewrite exists or is planned. Naming the model in the dispatch is the escape hatch.
- **`review.backend host`:** bare only (`host:<model>` rejected). The model comes from the AGENTS.md routing block — **not** from the backend string. Host-native fresh-context subagent; preferred from inside Cursor.
- **≠ `cursor` CLI backend:** `review.backend cursor:…` / `cursor-agent` is a separate headless subprocess path (multi-family reach from outside Cursor; circular from inside).
- **Cross-family rule:** reviewer family ≠ writer family (measured from the writer).

```bash
# In-session impl + host review (reviewer tier comes from the AGENTS.md routing block)
.flow/bin/flowctl config set review.backend host     # or per-run: --review=host
# $flow-next-work fn-12  → session implements; the host review runs the reviewer tier from your routing block

# Bridges FROM a Cursor host (same recipes as above, reverse direction)
claude -p "<self-contained prompt>" --output-format text --allowedTools "Read,Bash" </dev/null
codex exec -s read-only --skip-git-repo-check "<prompt>" </dev/null
```

**flow-next config shortcuts** — the routing flow-next machinery reads for itself. Implementation offload has no packaged config: use the bridge recipes above, and make them standing policy by writing them into `CLAUDE.md`/`AGENTS.md`.

```bash
# Cross-family review — the model that writes is never the model that reviews
.flow/bin/flowctl config set review.backend codex                              # or host | cursor:<model>
.flow/bin/flowctl task set-backend fn-1-add-oauth.3 --review cursor:<model>     # per-task review: override
```

**Prompted orchestration** — describe the policy; the host judges per item, no parameter required:

```text
Work the ready specs — decide per spec by complexity: auth/migration tasks you
implement yourself; plain CRUD goes out to a codex exec bridge. Reviews from codex either way.

Run $flow-next-work fn-12, bridging implementation to codex exec. If a task's review
comes back NEEDS_WORK twice, stop bridging it and implement it yourself on the session model.
```

None of these pairings are fixed — any stage of any flow-next pipeline (research, implementation, review, QA) can route to whatever harness you can reach from Bash: describe the arrangement in the invocation or your instruction files and the host builds it.

Make any of this durable by writing it into `CLAUDE.md`/`AGENTS.md` — the host reads your instruction files every session and flow-next skills inherit them automatically.

## Workflow

1. `.flow/bin/flowctl specs` - list all specs
2. `.flow/bin/flowctl ready --spec fn-N-slug` - find available tasks
3. `.flow/bin/flowctl start fn-N-slug.M` - claim task
4. Implement the task, then `git commit` the work (the evidence JSON cites this commit)
5. `.flow/bin/flowctl done fn-N-slug.M --summary-file ... --evidence-json ...` - complete
6. Stage the receipt: `done` writes the summary into the tracked task file AFTER your commit - include it in your next commit (it lists the path under `modified_paths` and prints a note when the file is left dirty)

If a sandbox denies `git commit`, still complete `done` with the evidence you have and record the restriction in the summary - never block the task on a commit you cannot make; the receipt then needs a later commit by whoever can make one.

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
