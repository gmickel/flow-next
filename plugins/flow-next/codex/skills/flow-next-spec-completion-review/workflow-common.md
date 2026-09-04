# Spec Completion Review Workflow — Common

## Unchanged-artifact terminal

`NOT_RETRYABLE: artifact unchanged since last verdict` plus exit `1` stops the
completion autonomous path for human action. It is never a transport refund and
must not trigger reset, `--force`, or redispatch. A human edits the exact
artifact, explicitly resets, or deliberately uses `--force`.

## Philosophy

Spec completion review verifies spec compliance, NOT code quality. impl-review handles code quality per-task. This review catches:
- Requirements that never became tasks (decomposition gaps)
- Requirements partially implemented across tasks (cross-task gaps)
- Scope drift (task marked done without fully addressing spec intent)
- Missing doc updates

---

## Phase 0: Backend Detection

**Run this first. Do not skip.**

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:

```bash
set -e
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Prefer RepoPrompt CE; retain Classic only as the final compatibility rung.
if command -v rpce-cli >/dev/null 2>&1 \
  || [ -x "$HOME/RepoPrompt/repoprompt_ce_cli" ] \
  || [ -x "$HOME/Library/Application Support/RepoPrompt CE/repoprompt_ce_cli" ] \
  || command -v rp-cli >/dev/null 2>&1; then
  RP_ELIGIBLE=1
else
  RP_ELIGIBLE=0
fi

# Priority: --review flag > per-spec `default_review` override > env > config (flag parsed in SKILL.md).
# Resolve the spec id from $ARGUMENTS FIRST so a per-spec `default_review` override routes to the
# right backend before branching (empty → env/config, no regression).
# Text output is bare backend name for back-compat grep. --json returns full
# resolved spec (backend, spec, model, effort, source).
SPEC_ID="${1:-}"   # the spec-id positional arg (canonicalized by review-backend); empty falls back to env/config
BACKEND=$($FLOWCTL review-backend "$SPEC_ID")

if [[ "$BACKEND" == "ASK" ]]; then
  echo "Error: No review backend configured."
  if [ "$RP_ELIGIBLE" = 1 ]; then
    echo "Run /flow-next:setup to configure, or pass --review=rp|codex|copilot|cursor|host|none"
  else
    echo "Run /flow-next:setup to configure, or pass --review=codex|copilot|cursor|host|none"
  fi
  exit 1
fi

echo "Review backend: $BACKEND"
```

**Spec-form env var (optional):** `FLOW_REVIEW_BACKEND` accepts bare or full spec:

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
FLOW_REVIEW_BACKEND=codex:<model>:xhigh $FLOWCTL codex completion-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
FLOW_REVIEW_BACKEND=copilot:<model> $FLOWCTL copilot completion-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
# Cursor folds effort into the model name (no :<effort>):
FLOW_REVIEW_BACKEND=cursor:<model> $FLOWCTL cursor completion-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
# Or pass spec directly:
$FLOWCTL codex completion-review "$SPEC_ID" --spec "codex:<model>:xhigh" --receipt "$RECEIPT_PATH"
```

Per-spec `default_review` (set via `flowctl spec set-backend`) overrides env.

**If backend is "none"**: Skip review, inform user, and exit cleanly (no error).

**Backend at a glance** — the per-backend summary (models, env vars, `--spec` forms) and the `backend[:model[:effort]]` spec grammar live in [references/backend-at-a-glance.md](references/backend-at-a-glance.md). Read it only when you surface backend guidance (the ASK branch above, a recommendation, an override hint); routing does not need it.

**Then branch to the backend-specific workflow file:**

| `$BACKEND` | Read |
|------------|------|
| `codex` | [workflow-codex.md](workflow-codex.md) |
| `copilot` | [workflow-copilot.md](workflow-copilot.md) |
| `cursor` | [workflow-cursor.md](workflow-cursor.md) |
| `host` | [workflow-host.md](workflow-host.md) |
| `rp` | [workflow-rp.md](workflow-rp.md) |

Only the file for the active backend should enter context. Do not read the other backend files.

**Foreground rule — review CLI calls are blocking.** Run every `flowctl <backend> …` review command as a single **foreground** Bash call with a generous timeout (10 minutes; verdicts typically land in 1–7). **Never** launch one with `run_in_background` + a monitor/poll — a background completion does not reliably resume a subagent context, and the call is bounded, so blocking is safe and simpler.

---

## Fix Loop (INTERNAL - do not exit to Ralph)

**The fix loop never pauses for user confirmation.** Every valid finding is fixed and re-reviewed automatically — the goal is complete spec compliance. A loop that stops to ask, or that exits with a valid finding unfixed, has broken this. Never use the plain-text numbered prompt in this loop.

**MAX ITERATIONS (backend-agnostic — rp, codex, copilot, cursor, host):**
The codex/copilot/cursor handlers reserve a round before dispatch; the selected
rp/host workflows call the same `review-rounds` reserve/record surface.
Verdict-bearing attempts consume the reservation; no-verdict transport failures
are recorded and refunded.

When a delivered `NEEDS_WORK` consumes round
`${MAX_REVIEW_ITERATIONS:-8}`, it is the terminal capped verdict:

- codex/copilot/cursor already self-wrote `needs_work` while handling that
  verdict; do not duplicate it.
- host/rp continue to SKILL.md's Step 0.5 checkpoint immediately, write
  `needs_work` exactly once, then emit `ESCALATE:` and exit 4. Do not attempt
  another reserve/dispatch first.

The exit-4 cap refusal and transport-failure semantics are stated in SKILL.md
directly under the Step 0.5 checkpoint; the unchanged-artifact terminal is at
the top of this file.

**ANTI-PATTERN (never do either):** (1) a delivered verdict is never a
transport failure. Once flowctl parses `VERDICT=...` the round is consumed and
recorded; do not re-dispatch or re-frame a `NEEDS_WORK` as a backend/sandbox
problem to claim a refund. (2) Never widen the reviewer sandbox. Reviewers are
read-only by contract; a sandbox-blocked reviewer means something asked it to
mutate the workspace. Fix that, do not pass `--sandbox workspace-write` /
`danger-full-access` or set `CODEX_SANDBOX` (Windows resolves via `auto`).

If verdict is NEEDS_WORK, loop internally until SHIP or the iteration cap:

1. **Parse issues** from reviewer feedback (missing requirements, incomplete implementations)
2. **Fix code** and run tests/lints
3. **Commit fixes** (mandatory before re-review; RP backend uses the snapshot-scoped staging in workflow-rp.md — never blanket-stage with `git add --all`). Then, when step 2's green run included one of the repo's full-gate commands (the same `(gate_id, exact command string)` identity the worker's Phase 5 maps — e.g. the repo's parallel full-suite entrypoint), nothing changed between that run and this commit, and the tree is clean at the committed fix HEAD: write the receipt — `<FLOWCTL> gate receipt --gate <gate_id> --command "<cmd>"` — so later gates honor it instead of re-running the identical command. Focused/partial test commands NEVER mint a full-gate receipt (identity is the exact full command string). A dirty tree, edits after the run, or any doubt about identity → mint nothing (fail closed; the later gate simply re-runs).
4. **Re-review**:
   - **Codex**: Re-run `flowctl codex completion-review` (receipt enables context)
   - **Copilot**: Re-run `flowctl copilot completion-review` (receipt enables context; must be `mode == "copilot"` to resume)
   - **Cursor**: Re-run `flowctl cursor completion-review` (receipt enables context; must be `mode == "cursor"` to resume)
   - **Host**: Continue through [workflow-host.md](workflow-host.md)'s selected
     re-review path.
   - **RP**: `$FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file <literal re-review path from workflow-rp.md's fix loop>` (NO `--new-chat`; stdout redirected to the same literal response file, Read once)
5. **Repeat** until `<verdict>SHIP</verdict>` — or a delivered `NEEDS_WORK`
   consumes the final round. On that final host/rp verdict, run the terminal
   status step below before the cap terminal; never rely on a later step after
   exit 4.

**RP re-reviews stay in the same chat.** `--new-chat` belongs to the first review only — a re-review carrying it drops the reviewer's context and has broken this.

## Record the terminal verdict exactly once

`flowctl <backend> completion-review` self-writes `completion_review_status` / `completion_reviewed_at` from the parsed verdict on codex/copilot/cursor (fn-112). **Every gate reads one satisfying set — `{ship, not_required}`. Without a write somewhere, a standalone completion review leaves `completion_review_status: unknown`, which satisfies nothing: `flowctl next --require-completion-review` keeps demanding the review (pilot's gate), make-pr's Open-items / draft heuristic reads stale state, and tracker-sync never reaches a terminal rung. A work 3g policy skip is different — it persists `not_required` (requirement satisfied, no review ran), so those gates pass without a receipt; `ship` stays the only value claiming a review actually happened and the only one that reaches tracker-sync's `verified` label.** The standalone command remains for rp and for repairing a missed write:

For host/rp, execute the SKILL.md Step 0.5 checkpoint again now. The
just-recorded terminal attempt is newer than the stored status, so that shared
checkpoint is the sole writer and emits the terminal only after persistence
succeeds. Codex/copilot/cursor handlers already self-write status; their next
invocation also runs Step 0.5 first, so a handler-side write failure recovers
without another reviewer dispatch.

For host and rp, write once on every delivered terminal path — Step 0.5 maps
SHIP → `ship` (exit 0), capped-NEEDS_WORK → `needs_work` (exit 4), and
NEEDS_HUMAN → `needs_human` (exit 4, `ESCALATE: reviewer requested human
review`). A delivered NEEDS_HUMAN is terminal at ANY round: never reserve or
dispatch another review for it. The write happens immediately after the
final verdict is recorded and before `ESCALATE:` / exit 4; no later control
flow is assumed. Transport failure, malformed verdict, and retry outcomes are
non-terminal and never write completion status.

## Anti-patterns (all backends)

**Hard invariants:**
- **The coordinator never authors a verdict.** A SHIP with no backend response behind it has broken this.
- **One backend per review.** A transcript that dispatches a second backend after the first answered has broken this.
- **Review is never skipped silently.** A `none` backend that ends the run without informing the user and exiting cleanly has broken this.

- **Reviewing yourself** - You coordinate; the backend reviews
- **No receipt** - when `REVIEW_RECEIPT_PATH` is set, every verdict writes a receipt; a verdict reported with no receipt at that path has broken this
- **Ignoring verdict** - the verdict tag is extracted from the backend response and acted on; a run that continues without reading it has broken this
- **Mixing backends** - Stick to one backend for the entire review session
- **Checking code quality** - That's impl-review's job; focus on spec compliance
- **Backgrounding the review CLI** - Never `run_in_background` + monitor/poll a `flowctl <backend>` review call; one blocking foreground Bash call with a long timeout (Foreground rule, Phase 0)

Backend-specific anti-patterns live in each `workflow-<backend>.md` file.
