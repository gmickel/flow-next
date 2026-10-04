
# Implementation review: other backends, flags and steering

Reached from [SKILL.md](SKILL.md) for the host backend, for `--deep`, `--validate`,
`--interactive`, `--no-triage`, `FLOW_VALIDATE_REVIEW=1` or `FLOW_REVIEW_DEEP=1`, and for an
instruction about reviewer topology. `BACKEND`,
`FLOWCTL`, `REVIEW_ID` and `DIFF_BASE` come from SKILL.md's setup; do not resolve the backend again.
The backend's workflow file and the Fix Loop below own the verdict handling; of SKILL.md §4
(the CLI fast path) only its `OVERRIDDEN:` line ending an unattended loop applies here.

**Workflow is backend-split. Read ONLY the file matching your active backend; [workflow-common.md](workflow-common.md) holds the philosophy and the trivial-diff triage. The opt-in `--deep`/`--validate`/`--interactive` phase detail (including the phase-ordering matrix) lives in [optional-phases.md](optional-phases.md), loaded only when a flag fires:**

- `BACKEND=codex`, `claude`, `copilot` or `cursor` → [workflow-cli.md](workflow-cli.md)
- `BACKEND=host` → [workflow-host.md](workflow-host.md)

Do not load the other one. Each file carries its own Critical Rules and anti-patterns; both apply the panel rule in [SKILL.md](SKILL.md).

Conduct a John Carmack-level review of implementation changes on the current branch.

**Role**: Code Review Coordinator (NOT the reviewer)
**Backends**: Codex CLI (codex), GitHub Copilot CLI (copilot), Cursor CLI (cursor), Claude Code CLI (claude), or host-native (`host`)

Read [working-rules.md](../../references/working-rules.md) first unless you already have this run; it holds for every step of this skill.

## Preamble

SKILL.md's setup already resolved `$BACKEND` and handled ASK, `none`, `rp` and `export`; never run
[workflow-common.md](workflow-common.md) Phase 0's `review-backend` call or ASK handling again.
Run only its `$FLOWCTL` setup lines, then parse the flags in Step 0.

## Backend Selection

**Priority** (first match wins):
1. `--review=codex|copilot|cursor|claude|host|none` argument
2. `FLOW_REVIEW_BACKEND` env var — bare backend (`codex`, `copilot`, `cursor`, `claude`, `host`, `none`) OR spec form (`codex:<model>:xhigh`, `copilot:<model>`, `cursor:<model>`, `claude:<model>:<effort>`); `host` is bare-only (`host:<model>` is rejected)
3. `.flow/config.json` → `review.backend` (same bare / spec forms)
4. **Error** - no auto-detection

### Parse from arguments first

Check $ARGUMENTS for:
- `--review=codex` or `--review codex` → use codex
- `--review=copilot` or `--review copilot` → use copilot
- `--review=cursor` or `--review cursor` → use cursor
- `--review=claude` or `--review claude` → use claude
- `--review=host` or `--review host` → use host
- `--review=rp` or `--review=export` (either spelling) → removed; SKILL.md's setup already showed the removal notice and stopped
- `--review=none` or `--review none` → skip review

If found, use that backend and skip all other detection.

### Otherwise: SKILL.md resolved it

No `--review` flag → `$BACKEND` comes from SKILL.md's setup: the single `flowctl review-backend "$REVIEW_ID"` call with ASK handling included. Do not re-resolve here.

### Backend detail (model / effort / spec grammar) — on demand

The per-backend "at a glance" descriptions, the `backend[:model[:effort]]` spec grammar, and the `FLOW_REVIEW_BACKEND` spec-form examples live in [references/backend-specs.md](references/backend-specs.md). Read it only when you must surface backend guidance to the user or resolve a model/effort spec — a normal review already has `$BACKEND` and needs nothing from it.

## Critical Rules

**Rules** for `codex`, `copilot`, `cursor`, and `claude` live at the top of [workflow-cli.md](workflow-cli.md), with each backend's notes at its end.

**For host backend:**
`host` is bare-only. After selection, read [workflow-host.md](workflow-host.md).
The review must use a fresh, tool-enforced read-only reviewer from a different
model family and fail closed when no cross-family pin is available.

**For all backends:**
- If `REVIEW_RECEIPT_PATH` set: write receipt after review (any verdict)
- Any failure → output `RETRY: no verdict (backend or transport failure)` and stop

**Hard invariants:**
- **The coordinator never authors a verdict.** A SHIP with no backend response behind it has broken this.
- **One backend per review.** A transcript that dispatches a second backend after the first answered has broken this.
- **Review is never skipped silently.** A `none` backend that ends the run without saying so has broken this. A caller that skips a change under the working-rules.md risk rule records a `stage:` line instead of invoking this skill; that skip needs no question.

## Input

Arguments: $ARGUMENTS
Format: `[task ID] [--base <commit>] [--validate] [--deep[=passes]] [--interactive] [focus areas]`

- `--base <commit>` - Compare against this commit instead of main/master (for task-scoped reviews)
- `--validate` - After NEEDS_WORK verdict, run a validator pass that drops false-positive findings (opt-in)
- `--deep` / `--deep=<passes>` - Run additional specialized passes (adversarial / security / performance) after primary review (opt-in)
- `--interactive` - On NEEDS_WORK, walk through each finding with the user (Apply/Defer/Skip/Acknowledge) (opt-in)
- Task ID - Optional, for context and receipt tracking
- Focus areas - Optional, specific areas to examine

**Scope behavior:**
- With `--base`: Reviews only changes since that commit (task-scoped)
- Without `--base`: Reviews entire branch vs main/master (full branch review)

**Opt-in flags:**
- `--validate` — adds a validator pass on NEEDS_WORK that re-checks each finding
  for false positives. All findings dropping upgrades verdict to SHIP.
- `FLOW_VALIDATE_REVIEW=1` env var — enables `--validate` session-wide.
- `--deep` — adds adversarial pass always + security/performance auto-enabled
  per diff paths. `--deep=adversarial,security` restricts to listed passes.
- `FLOW_REVIEW_DEEP=1` env var — enables `--deep` session-wide.
- `--interactive` — per-finding walkthrough on NEEDS_WORK. **No env var form** —
  per-invocation only.
- Default review behavior (no flags) is unchanged.

## Workflow

```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

### Step 0: Parse Arguments

Parse $ARGUMENTS for:
- `--base <commit>` → `BASE_COMMIT` (if provided, use for scoped diff)
- `--no-triage` → set `TRIAGE_DISABLED=1` (skip trivial-diff pre-check)
- `--validate` → set `VALIDATE=true` (validator pass on NEEDS_WORK)
- `--deep` / `--deep=<passes>` → set `DEEP=true` + optional `DEEP_PASSES` CSV
- `--interactive` → set `INTERACTIVE=true` (per-finding walkthrough on NEEDS_WORK)
- First positional arg matching `fn-*` → `TASK_ID`
- Remaining args → focus areas

If `--base` not provided, `BASE_COMMIT` stays empty (will fall back to main/master).

**Opt-in flags + env vars — ONE parse fence for `--validate` / `--deep` / `--interactive`:**

```bash
VALIDATE=false
DEEP=false
DEEP_PASSES=""  # optional CSV: "adversarial,security"
INTERACTIVE=false
for arg in $(printf '%s\n' "$ARGUMENTS"); do   # command substitution word-splits under bash AND zsh; an unquoted $ARGUMENTS does not split under zsh (otherwise flags such as --validate are silently dropped)
  case "$arg" in
    --validate) VALIDATE=true ;;
    --deep) DEEP=true ;;
    --deep=*) DEEP=true; DEEP_PASSES="${arg#--deep=}" ;;
    --interactive) INTERACTIVE=true ;;
  esac
done

# Env opt-ins. --interactive has NO env var form — per-invocation only.
if [[ "${FLOW_VALIDATE_REVIEW:-}" == "1" ]]; then
  VALIDATE=true
fi
if [[ "${FLOW_REVIEW_DEEP:-}" == "1" ]]; then
  DEEP=true
fi

# Optional-phase COUNT: sizes the scope-ownership lease the backend
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

if [[ "$DEEP" == "true" || "$VALIDATE" == "true" || "$INTERACTIVE" == "true" ]]; then
  echo "OPTIONAL PHASES ACTIVE — STOP. Read optional-phases.md (deep=$DEEP validate=$VALIDATE interactive=$INTERACTIVE) before continuing."
fi
```

When that sentinel prints, STOP and Read [optional-phases.md](optional-phases.md) before any further step — it owns the phase-ordering + flag-combination matrix, the deep-pass selection bash, the validator dispatch, and the walkthrough steps (per-finding loop detail in [walkthrough.md](walkthrough.md), pass prompt templates in [deep-passes.md](deep-passes.md)). All three phases are default-OFF: when no flag fires, run the primary review only and write no `validator` / `deep_passes` / `walkthrough` receipt keys.

### Step 0.5: Trivial-diff triage

Before invoking the configured backend, run a fast pre-check that short-circuits
lockfile-only, docs-only, release-chore, and generated-file diffs. On SKIP, the
receipt is written with `mode: "triage_skip"` / `verdict: "SHIP"` and the
expensive backend call is skipped entirely.

Opt-out: `--no-triage` argument.

```bash
if [[ -z "${TRIAGE_DISABLED:-}" ]]; then
  # Only a first-round route may skip review; probe failure falls through.
  if ROUTE="$($FLOWCTL review-route ${TASK_ID:+"$TASK_ID"} --json)" \
      && [[ "$(jq -r '.action // empty' <<<"$ROUTE")" == "fanout" ]]; then
    TASK_ID="$(jq -r '.task_id // empty' <<<"$ROUTE")"
    RECEIPT_PATH="$(jq -r '.receipt_path' <<<"$ROUTE")"
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
  fi
  # Exit 1 = proceed to full review (normal path). Exit >=2 = error, also falls
  # through so impl-review proceeds safely rather than failing on triage.
fi
```

**Opt-out note:** Pass `--no-triage` to force the full backend review (useful
when explicitly validating a suspicious chore diff, or when the deterministic
whitelist misclassifies).

The deterministic rule table, the SKIP receipt shape, and the `FLOW_TRIAGE_LLM=1`
judge live in [references/triage-rules.md](references/triage-rules.md) — read it
only when a triage result needs justifying or auditing.

### Step 1: Load Backend Workflow

1. `$BACKEND` was already resolved by SKILL.md's setup — do NOT re-run it.
2. Read **only** the file for that backend, per the routing table at the top of this file.

**Do not read the other workflow file.** Each is self-contained; loading both wastes context.

### Step 2: Execute the backend workflow

Follow the phases in the workflow file end-to-end. Each file owns its own Identify → Execute → Verdict → Receipt steps. Cross-backend gated phases (Deep-Pass, Validator, Interactive Walkthrough) live in [optional-phases.md](optional-phases.md) — the backend files reference them.

## Fix Loop (INTERNAL)

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

**The fix loop never pauses for user confirmation**; never use plain-text numbered prompt in it. Which findings it fixes, and which it lists as follow-ups, follows the Review section of [working-rules.md](../../references/working-rules.md).

**One fix pass, one re-review.** Fix those findings, commit, then re-review once with a single reviewer. That re-review's verdict is terminal unless working-rules.md's review loop applies (an unattended run, or a request to review until SHIP): never start a second fix pass. The round cap below stays as a safety net.

**MAJOR_RETHINK is NOT a fix-loop input.** Every backend can emit `MAJOR_RETHINK` (a valid verdict tag), but it means the *design/approach* is wrong — not something to patch finding-by-finding. Do NOT enter the fix loop on it. Escalate immediately: surface the reviewer's rationale to the caller and stop with a typed **`BLOCKED: DESIGN_CONFLICT`**. A re-approach is a human/worker decision, never an ad-hoc patch. Only `NEEDS_WORK` drives the loop below.

**MAX ITERATIONS (backend-agnostic — codex, copilot, cursor, claude, host):**
flowctl reserves a per-task round before every task-scoped dispatch. A delivered
SHIP / NEEDS_WORK / MAJOR_RETHINK / NEEDS_HUMAN consumes it; a no-verdict transport failure
is durably recorded and refunded. A first round of three draws (any backend)
sits behind exactly ONE reservation and counts as ONE round — the cap bounds
rounds, not draws. At `${MAX_REVIEW_ITERATIONS:-8}` verdict
rounds it refuses with `ESCALATE:` + exit 4. When the reviewer marks the same
finding `not-fixed` in three consecutive rounds, the recording command ends
with `ESCALATE: review loop stalled` + exit 4 after its verdict is recorded:
stop there, no further fix pass. More than
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
   problem, or claim a refund for it. `NEEDS_WORK` is fix-loop input (terminal
   after the re-review), full stop.
2. **Never widen the reviewer sandbox.** Reviewers are read-only by contract
   (Unix default `read-only`). A sandbox-blocked reviewer means something
   asked it to mutate the workspace: fix that, do not pass
   `--sandbox workspace-write` / `danger-full-access` or set `CODEX_SANDBOX`.
   The one exception is Windows, where `auto` already resolves for you.

**On `NEEDS_WORK` — STOP and Read [references/fix-loop.md](references/fix-loop.md)** before any further step: it owns the ordered loop (optional deep / validator / walkthrough hooks, parse issues, fix code, run tests and lints, commit fixes, the single per-backend re-review). Do not improvise the loop from memory. On `SHIP` the review is complete and nothing further is read.
