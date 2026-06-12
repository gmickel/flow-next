---
name: flow-next-plan
description: Create structured build plans from feature requests or Flow IDs. Use when planning features or designing implementation. Triggers on /flow-next:plan with text descriptions or Flow IDs (fn-1-add-oauth, fn-1-add-oauth.2, or legacy fn-1, fn-1.2, fn-1-xxx, fn-1-xxx.2).
user-invocable: false
---

# Flow plan

Turn a rough idea into a spec with tasks in `.flow/`. This skill does not write code.

Follow this skill and linked workflows exactly. Deviations cause drift, bad gates, retries, and user frustration.

**IMPORTANT**: This plugin uses `.flow/` for ALL task tracking. Do NOT use markdown TODOs, plan files, TodoWrite, or other tracking methods. All task state must be read and written via `flowctl`.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `steps.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Pre-check: Local setup version

If `.flow/meta.json` exists and has `setup_version`, compare to plugin version:
```bash
SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
if [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" ]]; then
  [[ "$SETUP_VER" = "$PLUGIN_VER" ]] || echo "Plugin updated to v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts (current: v${SETUP_VER})."
fi
```
Continue regardless (non-blocking).

**Role**: product-minded planner with strong repo awareness.
**Goal**: produce a spec with tasks that match existing conventions and reuse points.
**Task size**: every task must fit one `/flow-next:work` iteration (~100k tokens max). If it won't, split it.

## The Golden Rule: No Implementation Code

**Plans are specs, not implementations.** Do NOT write the code that will be implemented.

### Code IS allowed:
- **Signatures/interfaces** (what, not how): `function validate(input: string): Result`
- **Patterns from this repo** (with file:line ref): "Follow pattern at `src/auth.ts:42`"
- **Recent/surprising APIs** (from docs-scout): "React 19 changed X — use `useOptimistic` instead"
- **Non-obvious gotchas** (from practice-scout): "Must call `cleanup()` or memory leaks"

### Code is FORBIDDEN:
- Complete function implementations
- Full class/module bodies
- "Here's what you'll write" blocks
- Copy-paste ready snippets (>10 lines)

**Why:** Implementation happens in `/flow-next:work` with fresh context. Writing it here wastes tokens in planning, review, AND implementation — then causes drift when the implementer does it differently anyway.

## Input

Full request: $ARGUMENTS

Accepts:
- Feature/bug description in natural language
- Flow spec ID `fn-N-slug` (e.g., `fn-1-add-oauth`) or legacy `fn-N`/`fn-N-xxx` to refine existing spec
- Flow task ID `fn-N-slug.M` (e.g., `fn-1-add-oauth.2`) or legacy `fn-N.M`/`fn-N-xxx.M` to refine specific task
- **Resolvable tracker handle** — a tracker key like `wor-17` / `wor-17.2` that `flowctl show` resolves to the linked spec/task (fn-52.10). Treated as the existing spec/task, **never** as a new idea (R16). See the handle-recognition rule in Step 1.
- Chained instructions like "then review with /flow-next:plan-review"

Examples:
- `/flow-next:plan Add OAuth login for users`
- `/flow-next:plan fn-1-add-oauth`
- `/flow-next:plan fn-1` (legacy formats fn-1, fn-1-xxx still supported)
- `/flow-next:plan fn-1-add-oauth then review via /flow-next:plan-review`

If empty, ask: "What should I plan? Give me the feature or bug in 1-5 sentences." Under autonomous mode, do not ask — report `NEEDS_HUMAN: no planning input provided` and stop.

## FIRST: Parse Options or Ask Questions

Check configured backend:
```bash
REVIEW_BACKEND=$($FLOWCTL review-backend)
```
Returns: `ASK` (not configured), or `rp`/`codex`/`none` (configured).

### Autonomous mode (mode:autonomous / FLOW_AUTONOMOUS)

Parse `$ARGUMENTS` for the literal token `mode:autonomous` (strip it, same shape as capture's `mode:autofix` — a NEW parse branch, never overloading that token). Also honor the env var `FLOW_AUTONOMOUS=1` as a secondary signal (process-level drivers). Either signal → `AUTONOMOUS=1`.

Under `AUTONOMOUS=1`:
- **Ask NO setup questions.** Explicit passthrough flags (`--depth`, `--research`, `--review`) win as usual; for anything unset, apply the autonomous defaults: depth = `short`, research = `grep` (repo-scout), review = configured backend (`none` when `REVIEW_BACKEND` is `ASK`).
- **Never hang on a question.** If a genuinely unanswerable ambiguity remains (e.g. empty input), stop cleanly with a one-line `NEEDS_HUMAN: <reason>` report instead of asking.
- Autonomy ≠ Ralph: neither `mode:autonomous` nor `FLOW_AUTONOMOUS` activates ralph-guard hooks or any receipt path — they gate question suppression only.

### Option Parsing (skip questions if found in arguments)

Parse the arguments for these patterns. If found, use them and skip questions:

**Research approach**:
- `--research=rp` or `--research rp` or "use rp" or "context-scout" or "use repoprompt" → context-scout (errors at runtime if rp-cli missing)
- `--research=grep` or `--research grep` or "use grep" or "repo-scout" or "fast" → repo-scout

**Review mode**:
- `--review=codex` or "review with codex" or "codex review" or "use codex" → Codex CLI (GPT 5.5 High)
- `--review=rp` or "review with rp" or "rp chat" or "repoprompt review" → RepoPrompt chat (via `flowctl rp chat-send`)
- `--review=export` or "export review" or "external llm" → export for external LLM
- `--review=none` or `--no-review` or "no review" or "skip review" → no review

### If options NOT found in arguments

**Plan depth** (parse from args or ask):
- `--depth=short` or "quick" or "minimal" → SHORT
- `--depth=standard` or "normal" → STANDARD
- `--depth=deep` or "comprehensive" or "detailed" → DEEP
- Default: SHORT (simpler is better)

**If `AUTONOMOUS=1`:** skip every question below — apply the autonomous defaults above and continue.

**If REVIEW_BACKEND is rp, codex, or none** (already configured): Only ask research question. Show override hint:

```
Quick setup: Use RepoPrompt for deeper context?
a) Yes, context-scout (slower, thorough)
b) No, repo-scout (faster)

(Reply: "a", "b", or just tell me)
(Tip: --depth=short|standard|deep, --review=rp|codex|none)
```

**If REVIEW_BACKEND is ASK** (not configured): Ask all questions (do NOT use AskUserQuestion tool):

```
Quick setup before planning:

1. **Plan depth** — How detailed?
   a) Short — problem, acceptance, key context only
   b) Standard (default) — + approach, risks, test notes
   c) Deep — + phases, alternatives, rollout plan

2. **Research** — Use RepoPrompt for deeper context?
   a) Yes, context-scout (slower, thorough)
   b) No, repo-scout (faster)

3. **Review** — Run Carmack-level review after?
   a) Codex CLI
   b) RepoPrompt
   c) Export for external LLM
   d) None (configure later)

(Reply: "1a 2b 3d", or just tell me naturally)
```

Wait for response. Parse naturally — user may reply terse ("1a 2b") or ramble via voice.

**Defaults when empty/ambiguous:**
- Depth = `standard` (balanced detail)
- Research = `grep` (repo-scout)
- Review = configured backend if set, else `none`

## Workflow

Read [steps.md](steps.md) and follow each step in order.

**Step 1 readiness soft-check (fn-58)**: existing-spec inputs get an adoption-gated readiness check BEFORE the scout fan-out — warn-not-block, default proceed; repos that never adopted readiness see nothing. Details in steps.md Step 1.

**Step 8.5 HTML render lens (opt-in)**: when `artifacts.html.enabled` is true, planning regenerates `.flow/artifacts/<spec-id>/spec.html` with the plan layer (task DAG + R-ID coverage) per the shared disclosure reference ([`plugins/flow-next/references/html-artifacts.md`](../../references/html-artifacts.md)) — generated only after the Step 8 refinement loop exits, link line replaced in place in the spec md. With the mode off/unset there is zero artifact-related behavior or output. Details in steps.md Step 8.5.

**CRITICAL — Step 1 (Research)**: You MUST launch ALL scouts listed in steps.md in ONE parallel Task call. Do NOT skip scouts or run them sequentially. Each scout provides unique signal.

If user chose review:
- Option 2a: run `/flow-next:plan-review` after Step 4, fix issues until it passes
- Option 2b: run `/flow-next:plan-review` with export mode after Step 4

## Output

All plans go into `.flow/`:
- Spec: `.flow/specs/fn-N-slug.json` + `.flow/specs/fn-N-slug.md`
- Tasks: `.flow/tasks/fn-N-slug.M.json` + `.flow/tasks/fn-N-slug.M.md`
- Render lens (only when `artifacts.html.enabled`): `.flow/artifacts/fn-N-slug/spec.html` (steps.md Step 8.5)

**Never write plan files outside `.flow/`. Never use TodoWrite for task tracking.**

## Output rules

- Only create/update specs and tasks via flowctl
- No code changes
- No plan files outside `.flow/`
- R-IDs are mandatory on new spec acceptance criteria — use `- **Rn:** ...` prose prefix format; never renumber after first review cycle (see `steps.md` R-ID rule)
