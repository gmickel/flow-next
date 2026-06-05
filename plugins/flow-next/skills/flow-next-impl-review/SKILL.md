---
name: flow-next-impl-review
description: John Carmack-level implementation review via RepoPrompt or Codex. Use when reviewing code changes, PRs, or implementations. Triggers on /flow-next:impl-review.
user-invocable: false
---

# Implementation Review Mode

**Workflow is backend-split. Read [workflow-common.md](workflow-common.md) for Phase 0 (backend detection + philosophy + trivial-diff triage + phase-ordering matrix + cross-backend deep/validator/walkthrough phases), then read ONLY the file matching your active backend:**

- `BACKEND=codex` → [workflow-codex.md](workflow-codex.md)
- `BACKEND=copilot` → [workflow-copilot.md](workflow-copilot.md)
- `BACKEND=rp` → [workflow-rp.md](workflow-rp.md)

Do not load the other two — only the active backend's file is needed.

Conduct a John Carmack-level review of implementation changes on the current branch.

**Role**: Code Review Coordinator (NOT the reviewer)
**Backends**: RepoPrompt (rp), Codex CLI (codex), or GitHub Copilot CLI (copilot)

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow-*.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Backend Selection

**Priority** (first match wins):
1. `--review=rp|codex|copilot|export|none` argument
2. `FLOW_REVIEW_BACKEND` env var — bare backend (`rp`, `codex`, `copilot`, `none`) OR spec form (`codex:gpt-5.4:xhigh`, `copilot:claude-opus-4.5`)
3. `.flow/config.json` → `review.backend` (same bare / spec forms)
4. **Error** - no auto-detection

### Parse from arguments first

Check $ARGUMENTS for:
- `--review=rp` or `--review rp` → use rp
- `--review=codex` or `--review codex` → use codex
- `--review=copilot` or `--review copilot` → use copilot
- `--review=export` or `--review export` → use export
- `--review=none` or `--review none` → skip review

If found, use that backend and skip all other detection.

### Otherwise read from config

```bash
BACKEND=$($FLOWCTL review-backend)

if [[ "$BACKEND" == "ASK" ]]; then
  echo "Error: No review backend configured."
  echo "Run /flow-next:setup to configure, or pass --review=rp|codex|copilot|none"
  exit 1
fi

echo "Review backend: $BACKEND (override: --review=rp|codex|copilot|none)"
```

### Backend at a glance

- **rp** — RepoPrompt (macOS GUI); builder auto-selects context. Primary backend.
- **codex** — Codex CLI (cross-platform); uses OpenAI models (default `gpt-5.5`). `FLOW_CODEX_MODEL` / `FLOW_CODEX_EFFORT` env vars, or `--spec codex:gpt-5.4:xhigh`.
- **copilot** — GitHub Copilot CLI (cross-platform); supports Claude Opus/Sonnet/Haiku 4.5 and GPT-5.2 families via a Copilot subscription. `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, or `--spec copilot:claude-opus-4.5:xhigh`.

**Spec grammar:** `backend[:model[:effort]]` — `FLOW_REVIEW_BACKEND` and `.flow/config.json review.backend` both accept this. Examples: `codex`, `codex:gpt-5.2`, `copilot:claude-opus-4.5:xhigh`. Per-task `review` (set via `flowctl task set-backend`) overrides env.

## Critical Rules

**For rp backend:**
1. **DO NOT REVIEW CODE YOURSELF** - you coordinate, RepoPrompt reviews
2. **MUST WAIT for actual RP response** - never simulate/skip the review
3. **MUST use `setup-review`** - handles window selection + builder atomically
4. **DO NOT add --json flag to chat-send** - it suppresses the review response
5. **Re-reviews MUST stay in SAME chat** - omit `--new-chat` after first review

**For codex backend:**
1. Use `$FLOWCTL codex impl-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews
3. Parse verdict from command output

**For copilot backend:**
1. Use `$FLOWCTL copilot impl-review` exclusively
2. Pass `--receipt` for session continuity on re-reviews (session only resumes when prior receipt has `mode == "copilot"`)
3. Model + effort resolved via (first match wins): `--spec backend:model:effort` flag, per-task `review`, `FLOW_REVIEW_BACKEND` spec, `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, registry defaults
4. Parse verdict from command output

**For all backends:**
- If `REVIEW_RECEIPT_PATH` set: write receipt after review (any verdict)
- Any failure → output `<promise>RETRY</promise>` and stop

**FORBIDDEN**:
- Self-declaring SHIP without actual backend verdict
- Mixing backends mid-review (stick to one)
- Skipping review when backend is "none" without user consent

## Input

Arguments: $ARGUMENTS
Format: `[task ID] [--base <commit>] [--validate] [--deep[=passes]] [--interactive] [focus areas]`

- `--base <commit>` - Compare against this commit instead of main/master (for task-scoped reviews)
- `--validate` - After NEEDS_WORK verdict, run a validator pass that drops false-positive findings (fn-32.1, opt-in)
- `--deep` / `--deep=<passes>` - Run additional specialized passes (adversarial / security / performance) after primary review (fn-32.2, opt-in)
- `--interactive` - On NEEDS_WORK, walk through each finding with the user (Apply/Defer/Skip/Acknowledge) (fn-32.3, opt-in, Ralph-incompatible)
- Task ID - Optional, for context and receipt tracking
- Focus areas - Optional, specific areas to examine

**Scope behavior:**
- With `--base`: Reviews only changes since that commit (task-scoped)
- Without `--base`: Reviews entire branch vs main/master (full branch review)

**Opt-in flags (fn-32):**
- `--validate` — adds a validator pass on NEEDS_WORK that re-checks each finding
  for false positives. All findings dropping upgrades verdict to SHIP.
- `FLOW_VALIDATE_REVIEW=1` env var — enables `--validate` session-wide (works in Ralph).
- `--deep` — adds adversarial pass always + security/performance auto-enabled
  per diff paths. `--deep=adversarial,security` restricts to listed passes.
- `FLOW_REVIEW_DEEP=1` env var — enables `--deep` session-wide (works in Ralph).
- `--interactive` — per-finding walkthrough on NEEDS_WORK. **No env var form** —
  per-invocation only, always hard-errors in Ralph mode (`REVIEW_RECEIPT_PATH` or
  `FLOW_RALPH=1`) to prevent accidental autonomous engagement.
- Default review behavior (no flags) is unchanged.

## Workflow

```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

### Step 0: Parse Arguments

Parse $ARGUMENTS for:
- `--base <commit>` → `BASE_COMMIT` (if provided, use for scoped diff)
- `--no-triage` → set `TRIAGE_DISABLED=1` (skip trivial-diff pre-check)
- `--validate` → set `VALIDATE=true` (fn-32.1 validator pass on NEEDS_WORK)
- `--deep` / `--deep=<passes>` → set `DEEP=true` + optional `DEEP_PASSES` CSV (fn-32.2)
- `--interactive` → set `INTERACTIVE=true` (fn-32.3 per-finding walkthrough on NEEDS_WORK; Ralph-blocked)
- First positional arg matching `fn-*` → `TASK_ID`
- Remaining args → focus areas

If `--base` not provided, `BASE_COMMIT` stays empty (will fall back to main/master).

**Validate flag + env var:**

```bash
VALIDATE=false
# Parse --validate from $ARGUMENTS (same pattern as --base)
for arg in $ARGUMENTS; do
  case "$arg" in
    --validate) VALIDATE=true ;;
  esac
done

# Env opt-in (Ralph-friendly)
if [[ "${FLOW_VALIDATE_REVIEW:-}" == "1" ]]; then
  VALIDATE=true
fi
```

`VALIDATE` gates the validator pass in [workflow-common.md](workflow-common.md). When false (default),
behavior is unchanged.

**Deep flag + env var:**

```bash
DEEP=false
DEEP_PASSES=""  # optional CSV: "adversarial,security"
for arg in $ARGUMENTS; do
  case "$arg" in
    --deep) DEEP=true ;;
    --deep=*) DEEP=true; DEEP_PASSES="${arg#--deep=}" ;;
  esac
done

# Env opt-in (Ralph-friendly)
if [[ "${FLOW_REVIEW_DEEP:-}" == "1" ]]; then
  DEEP=true
fi
```

`DEEP` gates the deep-pass phase in [workflow-common.md](workflow-common.md). When false (default),
behavior is unchanged.

**Pass selection (when DEEP=true):**

```bash
# If explicit CSV provided, use those passes verbatim.
# Otherwise: adversarial always + security/performance auto-enabled by
# changed-file globs via `flowctl review-deep-auto`.
if [[ -n "$DEEP_PASSES" ]]; then
  SELECTED_PASSES="${DEEP_PASSES//,/ }"
else
  # Determine changed files for auto-enable heuristic
  if [[ -n "$BASE_COMMIT" ]]; then
    CHANGED="$(git diff --name-only "$BASE_COMMIT"..HEAD)"
  else
    DIFF_BASE=main; git rev-parse main >/dev/null 2>&1 || DIFF_BASE=master
    CHANGED="$(git diff --name-only "$DIFF_BASE"..HEAD)"
  fi
  SELECTED_PASSES="$(printf '%s\n' "$CHANGED" | $FLOWCTL review-deep-auto)"
fi
echo "Deep passes selected: $SELECTED_PASSES"
```

See [deep-passes.md](deep-passes.md) for the pass prompt templates, the
auto-enable globs, and merge/promotion rules.

**Interactive flag + Ralph-block (fn-32.3):**

```bash
INTERACTIVE=false
for arg in $ARGUMENTS; do
  case "$arg" in
    --interactive) INTERACTIVE=true ;;
  esac
done

# No env var form — per-invocation only. Ralph must never engage interactive.
if [[ "$INTERACTIVE" == "true" ]]; then
  if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
    echo "Error: --interactive requires a user at the terminal; not compatible with Ralph mode (REVIEW_RECEIPT_PATH or FLOW_RALPH detected)." >&2
    exit 2
  fi
fi
```

`INTERACTIVE` gates the walkthrough phase in [walkthrough.md](walkthrough.md).
When false (default), behavior is unchanged. When true + verdict is
NEEDS_WORK, the skill walks each finding with the user via the platform's
blocking question tool (Apply / Defer / Skip / Acknowledge / LFG-rest).

See [walkthrough.md](walkthrough.md) for the full per-finding flow and
deferred-findings sink contract.

### Step 0.5: Trivial-diff triage (fn-29.6)

Before invoking the configured backend, run a fast pre-check that short-circuits
lockfile-only, docs-only, release-chore, and generated-file diffs. On SKIP, the
receipt is written with `mode: "triage_skip"` / `verdict: "SHIP"` and the
expensive backend call is skipped entirely.

Opt-out: `--no-triage` argument or `FLOW_RALPH_NO_TRIAGE=1` env var.

```bash
if [[ -z "${TRIAGE_DISABLED:-}" && -z "${FLOW_RALPH_NO_TRIAGE:-}" ]]; then
  RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt.json}"
  TRIAGE_ARGS=(triage-skip --receipt "$RECEIPT_PATH" --json)
  [[ -n "$BASE_COMMIT" ]] && TRIAGE_ARGS+=(--base "$BASE_COMMIT")
  [[ -n "$TASK_ID" ]] && TRIAGE_ARGS+=(--task "$TASK_ID")
  # Deterministic-only by default; set FLOW_TRIAGE_LLM=1 to enable LLM judge
  # for ambiguous diffs. Deterministic is conservative — ambiguous → REVIEW.
  [[ -z "${FLOW_TRIAGE_LLM:-}" ]] && TRIAGE_ARGS+=(--no-llm)

  if TRIAGE_OUT=$($FLOWCTL "${TRIAGE_ARGS[@]}" 2>/dev/null); then
    # Exit 0 = SKIP. Receipt already written by flowctl.
    SKIP_REASON=$(echo "$TRIAGE_OUT" | jq -r '.reason // "trivial diff"' 2>/dev/null || echo "trivial diff")
    echo "Triage-skip: $SKIP_REASON"
    echo "VERDICT=SHIP"
    exit 0
  fi
  # Exit 1 = proceed to full review (normal path). Exit >=2 = error, also falls
  # through so impl-review proceeds safely rather than failing on triage.
fi
```

**Opt-out note:** Pass `--no-triage` to force the full backend review (useful
when explicitly validating a suspicious chore diff, or when the deterministic
whitelist misclassifies). `FLOW_RALPH_NO_TRIAGE=1` has the same effect for
Ralph runs.

### Step 1: Detect Backend + Load Workflow

1. Read [workflow-common.md](workflow-common.md) and execute its Phase 0 to resolve `$BACKEND`.
2. Then read **only** the file for that backend:

| `$BACKEND` | File to read |
|------------|--------------|
| `codex`    | [workflow-codex.md](workflow-codex.md) |
| `copilot`  | [workflow-copilot.md](workflow-copilot.md) |
| `rp`       | [workflow-rp.md](workflow-rp.md) |

**Do not read the other backend files.** Each is self-contained for its backend; loading the others wastes context.

### Step 2: Execute the backend workflow

Follow the phases in the per-backend file end-to-end. Each file owns its own Identify → Execute → Verdict → Receipt steps (and, for RP, the full Phase 1-4 setup-review / chat-send / receipt build + Fix Loop). Cross-backend gated phases (Deep-Pass, Validator, Interactive Walkthrough) live in [workflow-common.md](workflow-common.md) — the backend files reference them.

## Fix Loop (INTERNAL - do not exit to Ralph)

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is production-grade world-class software and architecture. Never use AskUserQuestion in this loop.**

If verdict is NEEDS_WORK, loop internally until SHIP:

0. **Deep-pass phase (only if `DEEP=true`)** — see [workflow-common.md](workflow-common.md) "Deep-Pass Phase" section.
   - After primary review completes (any verdict) and before validator,
     run each selected pass via
     `$FLOWCTL <backend> deep-pass --pass <name> --receipt ... --primary-findings ...`.
   - Passes merge into receipt via fingerprint dedup + cross-pass promotion.
   - Deep may upgrade `SHIP → NEEDS_WORK` if it surfaces new blocking findings;
     it never downgrades `NEEDS_WORK → SHIP`.
1. **Validator pass (only if `VALIDATE=true`)** — see [workflow-common.md](workflow-common.md) "Validator Pass" section.
   - Extract findings JSON-lines, dispatch `$FLOWCTL <backend> validate --findings-file ... --receipt ...`
   - If all findings drop → verdict upgrades to SHIP automatically (exit fix loop)
   - Else → only surviving (kept) findings enter the fix loop in step 2
2. **Interactive walkthrough (only if `INTERACTIVE=true` AND verdict still NEEDS_WORK)** — see [walkthrough.md](walkthrough.md).
   - For each surviving finding, ask user via platform blocking question tool: Apply / Defer / Skip / Acknowledge / LFG-rest.
   - Deferred findings appended to `.flow/review-deferred/<branch-slug>.md`.
   - Skip / Acknowledge are no-ops beyond receipt logging.
   - Apply list restricts the fix loop below to just those findings.
   - Receipt gains `walkthrough: {applied, deferred, skipped, acknowledged}`.
3. **Parse issues** from reviewer feedback (Critical → Major → Minor)
4. **Fix code** and run tests/lints
5. **Commit fixes** (mandatory before re-review)
6. **Re-review**:
   - **Codex**: Re-run `flowctl codex impl-review` (receipt enables context)
   - **Copilot**: Re-run `flowctl copilot impl-review` (receipt enables context; must be `mode == "copilot"` to resume)
   - **RP**: `$FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file /tmp/re-review.md` (NO `--new-chat`)
7. **Repeat** until `<verdict>SHIP</verdict>`

**CRITICAL**: For RP, re-reviews must stay in the SAME chat so reviewer has context. Only use `--new-chat` on the FIRST review.
