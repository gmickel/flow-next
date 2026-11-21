---
name: flow-next-plan-review
description: Carmack-level review of a flow-next spec or plan via the configured backend. Use when asked to review a plan or spec.
user-invocable: false
---

# Plan Review Mode

Conduct a John Carmack-level review of spec plans.

**Role**: Code Review Coordinator (NOT the reviewer)
**Backends**: Codex CLI (`codex`), GitHub Copilot CLI (`copilot`), Cursor CLI (`cursor`),
Claude Code CLI (`claude`), a configured review command (`command:<label>`), or host-native (`host`).

- **CLI backends (`codex`, `copilot`, `cursor`, `claude`, `command`):** run directly from the **CLI Fast Path** below after [workflow.md](workflow.md) Phase 0 & 1 — no extra backend file read needed.
- **`BACKEND=host`:** read [workflow-host.md](workflow-host.md) after [workflow.md](workflow.md) Phase 0 & 1.
- **`BACKEND=none` or unknown explicit value:** terminate from [workflow.md](workflow.md) Phase 0 without reading `workflow-host.md`.

Read [working-rules.md](../../references/working-rules.md) first unless you already have this run; it holds for every step of this skill.

## Preamble — execute common routing exactly once

Read and execute [workflow.md](workflow.md) Phase 0 once. It defines `$FLOWCTL`,
parses an explicit `--review` mode before configured-backend resolution,
resolves `SPEC_ID`, and handles `ASK`, `none` and unknown values. Never invoke
`flowctl review-backend` a second time.

## Common Critical Rules

- The coordinator never self-declares a verdict.
- Stick to one backend for the full review/fix cycle.
- If `REVIEW_RECEIPT_PATH` is set, every review verdict writes a receipt.
- Any backend/transport failure outputs `RETRY: no verdict (backend or transport failure)` and stops;
  never silently fall back to a different backend. When its `CLI message:` reports a usage, credit
  or spend limit, report that message and stop instead of `RETRY:`; a retry fails the same way. Autonomous callers
  receive the same retry terminal and decide whether to re-enter. A no-verdict
  dispatch is refunded and recorded by flowctl; never manually reset the review
  counter for a transport failure. Exit 5 / `TRANSPORT_UNHEALTHY` means stop
  automatic retries and repair the backend.
- `none` skips only when selected explicitly or resolved from configuration.
- **Foreground rule:** run every `flowctl <backend> plan-review` call as one **blocking foreground** Bash call with a generous timeout (10 minutes; verdicts typically land in 1–7) — never `run_in_background` + monitor/poll (a background completion does not reliably resume a subagent context). Host-backend subagent dispatches are also blocking.

## Input

Arguments: $ARGUMENTS

Format: `<flow-spec-id> [focus areas] [--review=<mode>] [mode:autonomous]`. `mode:autonomous` marks an
unattended run (working-rules.md's review loop applies); it is not a focus area.

## Workflow

1. Execute [workflow.md](workflow.md) Phase 0 and Phase 1 (saves the mandatory checkpoint).
2. If Phase 0 returns for `none` or an unknown value, stop.
3. For `codex`, `copilot`, `cursor`, `claude`, or `command`, execute the **CLI Fast Path** below; for `host`, read and follow [workflow-host.md](workflow-host.md).
4. Carry the verdict directly into the shared Fix Loop below until its terminal contract is satisfied.

## CLI Fast Path (`codex`, `copilot`, `cursor`, `claude`, `command`)

Use `$FLOWCTL "$BACKEND" plan-review` exclusively — never call `codex exec`, `claude -p`, `cursor-agent`, or `copilot` directly, never reconstruct the prompt in prose, and never fabricate a first-call resume id. Always pass `--receipt` (re-reviews resume only when the prior receipt matches the same backend mode, and same label for `command`).

- **`claude` same-family advisory:** on a Claude Code host, writer and reviewer share a model family; the receipt records it and the run proceeds (prefer `codex` or `host` when family independence matters).
- **`cursor`:** effort is baked into the model name (`cursor:<model>`); `cursor:<model>:<effort>` is rejected.
- **`command`:** when `--review=command:<label>` named a label, pass `--spec "command:<label>"` on the first review and every fix-loop re-review; a bare `--review=command` leaves the label to the configured backend (`FLOW_REVIEW_COMMAND_<LABEL>`).

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
SPEC_ID="<spec id resolved in workflow.md Phase 0>"            # substitute literally
BACKEND="<codex|copilot|cursor|claude|command>"                # substitute literally
REVIEW_SPEC="<command:<label> when --review named one, else empty>"
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-$(git rev-parse --show-toplevel)/.flow/tmp/plan-review-receipt-${SPEC_ID}.json}"

args=("$SPEC_ID" --receipt "$RECEIPT_PATH")
[ -n "$REVIEW_SPEC" ] && args+=(--spec "$REVIEW_SPEC")
"$FLOWCTL" "$BACKEND" plan-review "${args[@]}"
```

Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN`. The handler owns `plan_review_status`, `plan_reviewed_at`, cumulative rounds, and receipt writes. A re-review repeats this same fence after updating the spec/tasks.

## Fix Loop (INTERNAL)

**The fix loop never pauses for user confirmation**; never use plain-text numbered prompt in it. Which findings it fixes, and which it lists as follow-ups, follows the Review section of [working-rules.md](../../references/working-rules.md).

`MAJOR_RETHINK` is not a fix-loop input. Surface the reviewer's rationale and
stop with `BLOCKED: DESIGN_CONFLICT`. `NEEDS_HUMAN` is not one either: stop and hand the
reviewer's question to the person, on every backend. Only `NEEDS_WORK` enters the loop.

Attended: one fix pass, then one re-review, whose verdict is terminal. When working-rules.md's
review loop applies (an unattended run, or a request to review until SHIP), repeat the steps
below until SHIP or an `ESCALATE:`. The flowctl cap below stays as the backstop; never keep an
agent-side counter.

**The cap is enforced deterministically by flowctl:** every dispatch reserves a
spec-scoped round before launch. SHIP / NEEDS_WORK / MAJOR_RETHINK / NEEDS_HUMAN consume it;
a no-verdict transport failure is durably recorded and refunded. At
`${MAX_REVIEW_ITERATIONS:-8}` verdict rounds, flowctl refuses with `ESCALATE:`
and exit 4. More than `${MAX_REVIEW_TRANSPORT_FAILURES:-2}` consecutive
no-verdict failures stop separately with `TRANSPORT_UNHEALTHY` + exit 5.
Callers invoke plan-review once and act on its terminal result. The verdict
counter resets only on SHIP or an explicit re-plan, never on an edit, fresh
invocation, or transport failure.**

**ANTI-PATTERN:** a delivered verdict is never a transport failure - never
re-dispatch or re-frame `NEEDS_WORK` as a backend/sandbox problem to claim a
refund. And never widen the reviewer sandbox: reviewers are read-only by
contract, so a sandbox-blocked reviewer means something asked it to mutate the
workspace. Fix that instead (Windows resolves via `auto`).

When the verdict is `NEEDS_WORK`:

1. Parse all valid issues from reviewer feedback.
2. Fix the user-edited current spec, never a checkpoint copy: read the spec
   file now (`spec_path` from `$FLOWCTL show <SPEC_ID> --json`), edit it in
   place with targeted edits (a whole-file rewrite drops a person's edits), then
   persist that file. The file on disk is the input, so an edit the user made
   between cycles survives; on a `set-plan` failure, surface its error and stop
   the cycle.

   ```bash
   $FLOWCTL spec set-plan <SPEC_ID> --file <spec path> --json
   ```

3. Sync affected task specs when requirements, acceptance, design decisions,
   interfaces, retry/error semantics, or state values changed.
4. Re-enter the SAME selected backend file's re-review step. Never load or mix
   another backend. Codex/Copilot/Cursor/Claude/command resume only through a same-mode receipt;
   host uses a fresh read-only subagent.
5. Attended, stop after that one re-review: `SHIP` completes; `NEEDS_WORK` surfaces the
   surviving findings to the caller, never a second fix pass. In the review loop, repeat
   from step 1 as above.

**Done when:** the review ends in one of exactly five states — a `SHIP` from the
backend, a re-review `NEEDS_WORK` with its surviving findings surfaced, a
`MAJOR_RETHINK` escalated as `BLOCKED: DESIGN_CONFLICT`, a
`RETRY: no verdict (backend or transport failure)` from a backend/transport failure, or flowctl's
`ESCALATE:` cap refusal with the surviving findings surfaced. A round that ends
with a `NEEDS_WORK` neither fixed in the current spec nor re-entered into the
same backend has broken this.

**Maintainability pointer.** When the verdict's `maintainability:` block names a finding
(anything other than `none identified`): read
[references/maintainability-pointer.md](references/maintainability-pointer.md) and record it.

Recovery after context compaction:

```bash
"$FLOWCTL" checkpoint restore --spec <SPEC_ID> --json
```

Every re-review follows the selected backend file's receipt/status rules.
