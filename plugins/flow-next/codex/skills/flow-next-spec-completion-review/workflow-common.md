# Spec Completion Review Workflow — Common

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

# Priority: --review flag > per-spec `default_review` override > env > config (flag parsed in SKILL.md).
# Resolve the spec id from $ARGUMENTS FIRST so a per-spec `default_review` override routes to the
# right backend before branching. Substitute it literally: a Bash-prompt turn leaves $1 empty,
# which would silently route to the global backend.
# Text output is bare backend name for back-compat grep. --json returns full
# resolved spec (backend, spec, model, effort, source).
SPEC_ID="<fn-N spec id from \$ARGUMENTS>"
$FLOWCTL show "$SPEC_ID" --json >/dev/null \
  || { echo "Error: no spec '$SPEC_ID' - pass the spec id to review" >&2; exit 1; }
BACKEND=$($FLOWCTL review-backend "$SPEC_ID")

if [[ "$BACKEND" == "ASK" ]]; then
  echo "Error: No review backend configured."
  echo "Run /flow-next:setup to configure, or pass --review=codex|copilot|cursor|claude|host|none"
  exit 1
fi

echo "Review backend: $BACKEND"
```

**If backend is "none"**: Skip review, inform user, and exit cleanly (no error).

**Then branch to the backend-specific workflow file:**

| `$BACKEND` | Read |
|------------|------|
| `codex` | [workflow-codex.md](workflow-codex.md) |
| `copilot` | [workflow-copilot.md](workflow-copilot.md) |
| `cursor` | [workflow-cursor.md](workflow-cursor.md) |
| `claude` | [workflow-claude.md](workflow-claude.md) |
| `host` | [workflow-host.md](workflow-host.md) |

Only the file for the active backend should enter context. Do not read the other backend files.

**Foreground rule — review CLI calls are blocking.** Run every `flowctl <backend> …` review command as a single **foreground** Bash call with a generous timeout (10 minutes; verdicts typically land in 1–7). **Never** launch one with `run_in_background` + a monitor/poll — a background completion does not reliably resume a subagent context, and the call is bounded, so blocking is safe and simpler.

---

## Fix Loop (INTERNAL)

**The fix loop never pauses for user confirmation**; never use plain-text numbered prompt in it. Which findings it fixes, and which it lists as follow-ups, follows the Review section of [working-rules.md](../../references/working-rules.md).

**MAX ITERATIONS (backend-agnostic — codex, copilot, cursor, claude, host):**
The codex/copilot/cursor/claude handlers reserve a round before dispatch; the host
workflow calls the same `review-rounds` reserve/record surface.
Verdict-bearing attempts consume the reservation; no-verdict transport failures
are recorded and refunded.

When a delivered `NEEDS_WORK` consumes round
`${MAX_REVIEW_ITERATIONS:-8}`, it is the terminal capped verdict:

- codex/copilot/cursor/claude already self-wrote `needs_work` while handling that
  verdict; do not duplicate it.
- host: [references/terminal-status.md § Capped round](references/terminal-status.md#capped-round).

The exit-4 cap refusal and transport-failure semantics are stated in SKILL.md
directly under the Step 0.5 checkpoint, and so is the unchanged-artifact terminal.

**ANTI-PATTERN (never do either):** (1) a delivered verdict is never a
transport failure. Once flowctl parses `VERDICT=...` the round is consumed and
recorded; do not re-dispatch or re-frame a `NEEDS_WORK` as a backend/sandbox
problem to claim a refund. (2) Never widen the reviewer sandbox. Reviewers are
read-only by contract; a sandbox-blocked reviewer means something asked it to
mutate the workspace. Fix that, do not pass `--sandbox workspace-write` /
`danger-full-access` or set `CODEX_SANDBOX` (Windows resolves via `auto`).

If the verdict is NEEDS_WORK, fix and re-review (working-rules.md, Review):

1. **Parse issues** from reviewer feedback (missing requirements, incomplete implementations)
2. **Fix code** and run the focused tests for it
3. **Commit fixes**, with one `Declined #<n>: <reason>` line in the message for each finding listed as a follow-up (mandatory before re-review; never blanket-stage with `git add --all`). Then, only when step 2's green run included one of the repo's full-gate commands: read [fix-gate-receipt.md](../../references/fix-gate-receipt.md) and mint its receipt.
4. **Re-review**:
   - **Codex**: Re-run `flowctl codex completion-review` (receipt enables context)
   - **Copilot**: Re-run `flowctl copilot completion-review` (receipt enables context; must be `mode == "copilot"` to resume)
   - **Cursor**: Re-run `flowctl cursor completion-review` (receipt enables context; must be `mode == "cursor"` to resume)
   - **Host**: Continue through [workflow-host.md](workflow-host.md)'s selected
     re-review path.
5. **Stop.** Attended, the re-review's verdict is terminal: `SHIP` completes; `NEEDS_WORK`
   hands the surviving findings to the caller, never a second fix pass. When working-rules.md's
   review loop applies (an unattended run, or a request to review until SHIP), repeat steps 1-4
   until SHIP or an `ESCALATE:`. On host, run the terminal status step below on the final
   verdict. The iteration cap stays as the backstop (`ESCALATE:`, exit 4).

## Record the terminal verdict exactly once

`flowctl <backend> completion-review` self-writes `completion_review_status` / `completion_reviewed_at` from the parsed verdict on codex/copilot/cursor/claude. **Every gate reads one satisfying set — `{ship, not_required}`. Without a write somewhere, a standalone completion review leaves `completion_review_status: unknown`, which satisfies nothing: `flowctl next --require-completion-review` keeps demanding the review (pilot's gate), make-pr's Open-items / draft heuristic reads stale state, and tracker-sync never reaches a terminal rung. A work 3g policy skip is different — it persists `not_required` (requirement satisfied, no review ran), so those gates pass without a receipt; `ship` stays the only value claiming a review actually happened and the only one that reaches tracker-sync's `verified` label.** The standalone command remains for repairing a missed write:

`host`: read [references/terminal-status.md](references/terminal-status.md) and run it on the
final verdict.

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
