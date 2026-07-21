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

Compare `.flow/meta.json` `setup_version` to the plugin version; on mismatch, escalate once per plugin version. Fail-open throughout: a missing `jq`, `.flow/meta.json`, or plugin manifest silently continues.

```bash
SETUP_MODE=$(jq -r '.setup_mode // empty' .flow/meta.json 2>/dev/null)
SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
VERSION_ACK=$(jq -r '.version_ack // empty' .flow/meta.json 2>/dev/null)
if [[ "$SETUP_MODE" == "plugin" ]]; then
  # fn-121 plugin mode: no local copies exist to go stale - the version compare is
  # moot. Check only the CLAUDE.md snippet contract (sentinel vs the plugin's
  # expected v1; keep the literal in sync with SNIPPET_SCHEMA_VERSION in flowctl.py).
  SNIP_ACK=$(jq -r '.snippet_ack // empty' .flow/meta.json 2>/dev/null)
  SNIP_VER=$(grep -m1 -o 'flow-next:snippet:v[0-9]*' CLAUDE.md 2>/dev/null | grep -o '[0-9]*$')
  if [[ "${SNIP_VER:-missing}" != "1" ]]; then
    if [[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_AUTONOMOUS:-}" == "1" || "${ARGUMENTS:-}" == *mode:autonomous* \
          || "$SNIP_ACK" == "1" ]]; then
      echo "CLAUDE.md flow-next snippet contract v${SNIP_VER:-missing} != plugin v1. Refresh via /flow-next:setup or the interactive ask." >&2
    else
      echo "FLOW_SNIPPET_ASK ${SNIP_VER:-missing} 1"
    fi
  fi
elif [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
  if [[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" \
        || "${FLOW_AUTONOMOUS:-}" == "1" || "${ARGUMENTS:-}" == *mode:autonomous* \
        || "$VERSION_ACK" == "$PLUGIN_VER" ]]; then
    echo "Local setup v${SETUP_VER} differs from plugin v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts." >&2
  else
    echo "FLOW_SETUP_ASK ${SETUP_VER} ${PLUGIN_VER}"
  fi
fi
```

If the block printed a `FLOW_SNIPPET_ASK` line (plugin mode only; suppressed to the stderr note under the autonomy markers above), before proceeding ask the user with AskUserQuestion (the CLAUDE.md flow-next snippet block is on an older contract than this plugin version; refresh the marker block?), offering exactly the options **Refresh now**, **Remind me next version**, **Skip this run**, then continue the skill whichever is chosen:
- **Refresh now**: run `"${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl" setup-block apply --file CLAUDE.md --template "${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/skills/flow-next-setup/templates/claude-md-snippet-plugin.md" --json`; if it returns `action: ask`, re-run as `setup-block resolve` with the same `--file`/`--template` plus `--choice overwrite --json` - this question WAS the consent. Marker-bounded: content outside the block is never touched.
- **Remind me next version**: record the acknowledgement so this contract version is not re-asked (fail-open: on any error, continue anyway):
  ```bash
  rm -f .flow/meta.json.tmp && jq '.snippet_ack = "1"' .flow/meta.json > .flow/meta.json.tmp && mv .flow/meta.json.tmp .flow/meta.json
  ```
- **Skip this run**: continue without writing anything; the next invocation asks again.

If the block printed a `FLOW_SETUP_ASK` line, before proceeding ask the user with AskUserQuestion (local setup differs from the plugin; refresh now?), offering exactly the options **Refresh now**, **Remind me next version**, **Skip this run**, then continue the skill whichever is chosen:
- **Refresh now**: pause and have the user run `/flow-next:setup` in this session (do not run setup yourself), then continue once it finishes.
- **Remind me next version**: record the acknowledgement so this version is not re-asked (only a later plugin version re-arms it), then continue. Run this self-contained write (fail-open: on any error, continue anyway):
  ```bash
  PJ="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
  PV=$(jq -r '.version' "$PJ" 2>/dev/null)
  [[ -n "$PV" && "$PV" != "null" ]] && rm -f .flow/meta.json.tmp && jq --arg v "$PV" '.version_ack = $v' .flow/meta.json > .flow/meta.json.tmp && mv .flow/meta.json.tmp .flow/meta.json
  ```
- **Skip this run**: continue without writing anything; the next invocation asks again.

Any other output (the one-line differs notice, or nothing) is non-blocking: continue.

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

**RepoPrompt eligibility** (compute once, before any question below):

```bash
# Prefer RepoPrompt CE; retain Classic only as the final compatibility rung.
if command -v rpce-cli >/dev/null 2>&1 \
  || [ -x "$HOME/RepoPrompt/repoprompt_ce_cli" ] \
  || [ -x "$HOME/Library/Application Support/RepoPrompt CE/repoprompt_ce_cli" ] \
  || command -v rp-cli >/dev/null 2>&1; then
  RP_ELIGIBLE=1
else
  RP_ELIGIBLE=0
fi
```

Suppression governs *proposals only* — an explicit `--research=rp` / `--review=rp` argument (parsed above) is always honored and errors at runtime if rp-cli is missing, exactly as today.

**Plan depth** (parse from args or ask):
- `--depth=short` or "quick" or "minimal" → SHORT
- `--depth=standard` or "normal" → STANDARD
- `--depth=deep` or "comprehensive" or "detailed" → DEEP
- Default: SHORT (simpler is better)

**If `AUTONOMOUS=1`:** skip every question below — apply the autonomous defaults above and continue.

**If REVIEW_BACKEND is rp, codex, or none** (already configured): Only ask research question. Show override hint.

When `RP_ELIGIBLE=0` (not macOS, no rp-cli): do NOT ask about RepoPrompt — context-scout cannot run here. Research = `repo-scout`; ask nothing in this branch and continue.

When `RP_ELIGIBLE=1`:

```
Quick setup: Use RepoPrompt for deeper context?
a) Yes, context-scout (slower, thorough)
b) No, repo-scout (faster)

(Reply: "a", "b", or just tell me)
(Tip: --depth=short|standard|deep, --review=rp|codex|none)
```

**If REVIEW_BACKEND is ASK** (not configured): Ask all questions (do NOT use AskUserQuestion tool).

When `RP_ELIGIBLE=1`:

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

When `RP_ELIGIBLE=0` (not macOS, no rp-cli): omit the Research question entirely (research = `repo-scout`) and drop the RepoPrompt review option:

```
Quick setup before planning:

1. **Plan depth** — How detailed?
   a) Short — problem, acceptance, key context only
   b) Standard (default) — + approach, risks, test notes
   c) Deep — + phases, alternatives, rollout plan

2. **Review** — Run Carmack-level review after?
   a) Codex CLI
   b) Export for external LLM
   c) None (configure later)

(Reply: "1a 2c", or just tell me naturally)
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

**CRITICAL — Step 1 (Research)**: You MUST launch ALL scouts in the **depth-appropriate set** (steps.md tier table — the full set at STANDARD/DEEP; the full set MINUS the three web-research scouts at SHORT) in ONE parallel Task call. Do NOT skip scouts within that set or run them sequentially. Each scout in the set provides unique signal.

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
