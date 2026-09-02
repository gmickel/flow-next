---
name: flow-next-impl-review
description: Carmack-level implementation review of changes via the configured backend. Use when asked to review code or a diff in a flow-next repo.
user-invocable: false
---

# Implementation Review Mode

**Workflow is backend-split. Read [workflow-common.md](workflow-common.md) for Phase 0 (backend detection + philosophy + trivial-diff triage), then read ONLY the file matching your active backend. The opt-in `--deep`/`--validate`/`--interactive` phase detail (including the phase-ordering matrix) lives in [optional-phases.md](optional-phases.md), loaded only when a flag fires:**

- `BACKEND=codex` → [workflow-codex.md](workflow-codex.md)
- `BACKEND=copilot` → [workflow-copilot.md](workflow-copilot.md)
- `BACKEND=cursor` → [workflow-cursor.md](workflow-cursor.md)
- `BACKEND=host` → [workflow-host.md](workflow-host.md)
- `BACKEND=rp` → [workflow-rp.md](workflow-rp.md)

Do not load the others — only the active backend's file is needed. Each backend file carries its own Critical Rules and anti-patterns.

Conduct a John Carmack-level review of implementation changes on the current branch.

**Role**: Code Review Coordinator (NOT the reviewer)
**Backends** (branch on the Phase 0 `RP_ELIGIBLE` probe):
- When `RP_ELIGIBLE=1`: RepoPrompt (rp), Codex CLI (codex), GitHub Copilot CLI (copilot), Cursor CLI (cursor), or host-native (`host`)
- When `RP_ELIGIBLE=0`: Codex CLI (codex), GitHub Copilot CLI (copilot), Cursor CLI (cursor), or host-native (`host`) — rp is macOS-only; never list it in guidance you surface (`--review=rp` stays accepted)

## Preamble — execute Phase 0 exactly once

**The executable Phase 0 lives in [workflow-common.md](workflow-common.md) §"Phase 0: Backend Detection" — Read it and execute it ONCE, before any other bash in this skill.** It defines `$FLOWCTL` (bundled — NOT installed globally; `which flowctl` fails, expected), probes `RP_ELIGIBLE`, resolves `$BACKEND` via the single `flowctl review-backend` call, and handles the ASK / `none` cases. Every later bash block here (triage, deep-pass selection) uses the `$FLOWCTL` it defines. Never invoke `flowctl review-backend` a second time in the same run.

Exception: a `--review=<backend>` argument (see Backend Selection below) wins — when present, set `BACKEND` from the flag and skip Phase 0's `review-backend` call + ASK handling (still run its `$FLOWCTL` / `RP_ELIGIBLE` setup lines).

When `RP_ELIGIBLE=0` (not macOS, no supported RepoPrompt CLI), never *steer* the user toward rp: every backend summary, recommendation, or override hint you surface presents only the runnable configured backends `codex`, `copilot`, `cursor`, `host` (plus `none`). `export` is not an impl-review mode at all — a manual export review lives in `/flow-next:plan-review --review=export`; never present it here. Suppression is not a ban: an explicit `--review=rp`, `FLOW_REVIEW_BACKEND=rp`, or `review.backend=rp` still resolves to rp and errors at runtime via `require_rp_cli()`.

## Backend Selection

**Priority** (first match wins):
1. `--review=rp|codex|copilot|cursor|host|none` argument
2. `FLOW_REVIEW_BACKEND` env var — bare backend (`rp`, `codex`, `copilot`, `cursor`, `host`, `none`) OR spec form (`codex:gpt-5.4:xhigh`, `copilot:claude-opus-4.5`, `cursor:gpt-5.5-high`); `host` is bare-only (`host:<model>` is rejected)
3. `.flow/config.json` → `review.backend` (same bare / spec forms)
4. **Error** - no auto-detection

### Parse from arguments first

Check $ARGUMENTS for:
- `--review=rp` or `--review rp` → use rp
- `--review=codex` or `--review codex` → use codex
- `--review=copilot` or `--review copilot` → use copilot
- `--review=cursor` or `--review cursor` → use cursor
- `--review=host` or `--review host` → use host
- `--review=export` or `--review export` → fail closed: report that `export` is not an impl-review backend and stop before any dispatch; the manual path is `/flow-next:plan-review --review=export`
- `--review=none` or `--review none` → skip review

If found, use that backend and skip all other detection.

### Otherwise: Phase 0 resolves it

No `--review` flag → `$BACKEND` comes from [workflow-common.md](workflow-common.md) Phase 0 (executed once per the Preamble): the single `flowctl review-backend "$REVIEW_ID"` call with ASK handling included. Do not re-resolve here.

### Backend detail (model / effort / spec grammar) — on demand

The per-backend "at a glance" descriptions, the `backend[:model[:effort]]` spec grammar, and the `FLOW_REVIEW_BACKEND` spec-form examples live in [references/backend-specs.md](references/backend-specs.md). Read it only when you must surface backend guidance to the user or resolve a model/effort spec — a normal review already has `$BACKEND` and needs nothing from it. When `RP_ELIGIBLE=0`, omit the **rp** line from any guidance you surface (explicit `--review=rp` still honored).

## Critical Rules

**Per-backend rules** for `rp`, `codex`, `copilot`, and `cursor` live at the top of each `workflow-<backend>.md` — read the active backend's file (routing table above) and follow its Critical Rules section.

**For host backend (fn-123 R5 / fn-126):**
`host` is bare-only. After selection, read [workflow-host.md](workflow-host.md).
The review must use a fresh, tool-enforced read-only reviewer from a different
model family and fail closed when no cross-family pin is available.

**For all backends:**
- If `REVIEW_RECEIPT_PATH` set: write receipt after review (any verdict)
- Any failure → output `<promise>RETRY</promise>` and stop

**Hard invariants:**
- **The coordinator never authors a verdict.** A SHIP with no backend response behind it has broken this.
- **One backend per review.** A transcript that dispatches a second backend after the first answered has broken this.
- **Review is never skipped without consent.** A `none` backend that ends the run without the user's consent has broken this.

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

**Opt-in flags + env vars — ONE parse fence (fn-110) for `--validate` / `--deep` / `--interactive`:**

```bash
VALIDATE=false
DEEP=false
DEEP_PASSES=""  # optional CSV: "adversarial,security"
INTERACTIVE=false
for arg in $(printf '%s\n' "$ARGUMENTS"); do   # command substitution word-splits under bash AND zsh; an unquoted $ARGUMENTS does not split under zsh (dogfood E1: --validate silently dropped)
  case "$arg" in
    --validate) VALIDATE=true ;;
    --deep) DEEP=true ;;
    --deep=*) DEEP=true; DEEP_PASSES="${arg#--deep=}" ;;
    --interactive) INTERACTIVE=true ;;
  esac
done

# Env opt-ins (Ralph-friendly). --interactive has NO env var form — per-invocation only.
if [[ "${FLOW_VALIDATE_REVIEW:-}" == "1" ]]; then
  VALIDATE=true
fi
if [[ "${FLOW_REVIEW_DEEP:-}" == "1" ]]; then
  DEEP=true
fi

# Optional-phase COUNT (PR #392): sizes the scope-ownership lease the backend
# workflows hold through the post-finalize phases (one exec allowance per
# pass). --deep counts one per selected pass (3 when unrestricted: adversarial
# + the auto-gated security/performance passes), --validate one,
# --interactive one. Carry this number into the finalize / host record blocks
# as a LITERAL - shell state does not survive across prompt turns.
OPTIONAL_PHASES_COUNT=0
if [[ "$DEEP" == "true" ]]; then
  if [[ -n "$DEEP_PASSES" ]]; then
    OPTIONAL_PHASES_COUNT=$((OPTIONAL_PHASES_COUNT + $(printf '%s' "$DEEP_PASSES" | tr ',' '\n' | grep -c .)))
  else
    OPTIONAL_PHASES_COUNT=$((OPTIONAL_PHASES_COUNT + 3))
  fi
fi
[[ "$VALIDATE" == "true" ]] && OPTIONAL_PHASES_COUNT=$((OPTIONAL_PHASES_COUNT + 1))
[[ "$INTERACTIVE" == "true" ]] && OPTIONAL_PHASES_COUNT=$((OPTIONAL_PHASES_COUNT + 1))
echo "OPTIONAL_PHASES_COUNT=$OPTIONAL_PHASES_COUNT"
# 1 when a held phase resumes the primary reviewer session (--deep /
# --validate); the interactive walkthrough alone never needs one.
PHASES_RESUME_SESSION=0
[[ "$DEEP" == "true" || "$VALIDATE" == "true" ]] && PHASES_RESUME_SESSION=1
echo "PHASES_RESUME_SESSION=$PHASES_RESUME_SESSION"

# Ralph-block (fn-32.3): Ralph must never engage interactive.
if [[ "$INTERACTIVE" == "true" ]]; then
  if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
    echo "Error: --interactive requires a user at the terminal; not compatible with Ralph mode (REVIEW_RECEIPT_PATH or FLOW_RALPH detected)." >&2
    exit 2
  fi
fi

if [[ "$DEEP" == "true" || "$VALIDATE" == "true" || "$INTERACTIVE" == "true" ]]; then
  echo "OPTIONAL PHASES ACTIVE — STOP. Read optional-phases.md (deep=$DEEP validate=$VALIDATE interactive=$INTERACTIVE) before continuing."
fi
```

When that sentinel prints, STOP and Read [optional-phases.md](optional-phases.md) before any further step — it owns the phase-ordering + flag-combination matrix, the deep-pass selection bash, the validator dispatch, and the walkthrough steps (per-finding loop detail in [walkthrough.md](walkthrough.md), pass prompt templates in [deep-passes.md](deep-passes.md)). All three phases are default-OFF: when no flag fires, run the primary review only and write no `validator` / `deep_passes` / `walkthrough` receipt keys.

### Step 0.5: Trivial-diff triage (fn-29.6)

Before invoking the configured backend, run a fast pre-check that short-circuits
lockfile-only, docs-only, release-chore, and generated-file diffs. On SKIP, the
receipt is written with `mode: "triage_skip"` / `verdict: "SHIP"` and the
expensive backend call is skipped entirely.

Opt-out: `--no-triage` argument or `FLOW_RALPH_NO_TRIAGE=1` env var.

```bash
if [[ -z "${TRIAGE_DISABLED:-}" && -z "${FLOW_RALPH_NO_TRIAGE:-}" ]]; then
  ROUTE="$($FLOWCTL review-route ${TASK_ID:+"$TASK_ID"} --json)"   # pure: canonical TASK_ID + receipt path (no rotation, no state change)
  TASK_ID="$(jq -r '.task_id // empty' <<<"$ROUTE")"
  RECEIPT_PATH="$(jq -r '.receipt_path' <<<"$ROUTE")"
  # Subcommand + one literal flag stay on the command line (the Ralph guard
  # blocks a variable in either of the two tokens after the launcher).
  TRIAGE_ARGS=(--receipt "$RECEIPT_PATH")
  [[ -n "$BASE_COMMIT" ]] && TRIAGE_ARGS+=(--base "$BASE_COMMIT")
  [[ -n "$TASK_ID" ]] && TRIAGE_ARGS+=(--task "$TASK_ID")
  # Deterministic-only by default; set FLOW_TRIAGE_LLM=1 to enable LLM judge
  # for ambiguous diffs. Deterministic is conservative — ambiguous → REVIEW.
  [[ -z "${FLOW_TRIAGE_LLM:-}" ]] && TRIAGE_ARGS+=(--no-llm)

  if TRIAGE_OUT=$($FLOWCTL triage-skip --json "${TRIAGE_ARGS[@]}" 2>/dev/null); then
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

The deterministic rule table, the SKIP receipt shape, and the `FLOW_TRIAGE_LLM=1`
judge live in [references/triage-rules.md](references/triage-rules.md) — read it
only when a triage result needs justifying or auditing.

### Step 1: Load Backend Workflow

1. `$BACKEND` was already resolved by workflow-common.md Phase 0 (Preamble) — do NOT re-run it.
2. Read **only** the file for that backend, per the routing table at the top of this file.

**Do not read the other backend files.** Each is self-contained for its backend; loading the others wastes context.

### Step 2: Execute the backend workflow

Follow the phases in the per-backend file end-to-end. Each file owns its own Identify → Execute → Verdict → Receipt steps (and, for RP, the full Phase 1-4 setup-review (5-15 min, DO NOT RETRY) / chat-send (2-10 min, DO NOT RETRY) / receipt build + Fix Loop). Cross-backend gated phases (Deep-Pass, Validator, Interactive Walkthrough) live in [optional-phases.md](optional-phases.md) — the backend files reference them.

## Fix Loop (INTERNAL - do not exit to Ralph)

**The fix loop never pauses for user confirmation.** Every valid finding is fixed and re-reviewed automatically — the goal is production-grade world-class software and architecture. A loop that stops to ask, or that exits with a valid finding unfixed, has broken this. Never use the plain-text numbered prompt in this loop.

**MAJOR_RETHINK is NOT a fix-loop input.** Every backend can emit `MAJOR_RETHINK` (a valid verdict tag), but it means the *design/approach* is wrong — not something to patch finding-by-finding. Do NOT enter the fix loop on it. Escalate immediately: surface the reviewer's rationale to the caller and stop with a typed **`BLOCKED: DESIGN_CONFLICT`** (Ralph mode: output `<promise>RETRY</promise>`). A re-approach is a human/worker decision, never an ad-hoc patch. Only `NEEDS_WORK` drives the loop below.

**MAX ITERATIONS (backend-agnostic — rp, codex, copilot, cursor, host):**
flowctl reserves a per-task round before every task-scoped dispatch. A delivered
SHIP / NEEDS_WORK / MAJOR_RETHINK / NEEDS_HUMAN consumes it; a no-verdict transport failure
is durably recorded and refunded. A first-round three-draw fan-out (codex/host)
sits behind exactly ONE reservation and counts as ONE round — the cap bounds
rounds, not draws. At `${MAX_REVIEW_ITERATIONS:-8}` verdict
rounds it refuses with `ESCALATE:` + exit 4. More than
`${MAX_REVIEW_TRANSPORT_FAILURES:-2}` consecutive no-verdict failures stop
separately with `TRANSPORT_UNHEALTHY` + exit 5: repair the backend, never reset
the verdict counter. This loop is internal; callers invoke impl-review once.
The counter resets only on SHIP or explicit re-plan, never on an edit, fresh
invocation, or transport failure.**

**Unchanged-artifact terminal:** `NOT_RETRYABLE: artifact unchanged since last verdict` exits `1` before a review is sent. It is a human-action terminal:
autonomous loops must stop without refunding, resetting, adding `--force`, or
redispatching. The human may edit the artifact, explicitly reset, or choose a
deliberate `--force` dispatch.

**ANTI-PATTERN (never do either):**
1. **A delivered verdict is never a transport failure.** Once flowctl parses
   `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN`, the round is consumed and the
   attempt is recorded; transport classification is unreachable past that
   point. Do not re-dispatch, re-frame a `NEEDS_WORK` as a backend/sandbox
   problem, or claim a refund for it. `NEEDS_WORK` is fix-loop input, full
   stop.
2. **Never widen the reviewer sandbox.** Reviewers are read-only by contract
   (Unix default `read-only`). A sandbox-blocked reviewer means something
   asked it to mutate the workspace: fix that, do not pass
   `--sandbox workspace-write` / `danger-full-access` or set `CODEX_SANDBOX`.
   The one exception is Windows, where `auto` already resolves for you.

**On `NEEDS_WORK` — STOP and Read [references/fix-loop.md](references/fix-loop.md)** before any further step: it owns the ordered loop (optional deep / validator / walkthrough hooks, parse issues, fix code, run tests and lints, commit fixes, per-backend re-review command, repeat until `<verdict>SHIP</verdict>` or the cap above). Do not improvise the loop from memory. On `SHIP` the review is complete and nothing further is read.
