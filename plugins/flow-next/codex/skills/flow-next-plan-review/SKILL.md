---
name: flow-next-plan-review
description: Carmack-level review of a flow-next spec or plan via the configured backend. Use when asked to review a plan or spec.
user-invocable: false
---

# Plan Review Mode

**Workflow is backend-split. Read [workflow.md](workflow.md) for common
orchestration and backend resolution, then read ONLY the file matching the
selected review backend:**

- `BACKEND=codex` → [workflow-codex.md](workflow-codex.md)
- `BACKEND=copilot` → [workflow-copilot.md](workflow-copilot.md)
- `BACKEND=cursor` → [workflow-cursor.md](workflow-cursor.md)
- `BACKEND=claude` → [workflow-claude.md](workflow-claude.md)
- `BACKEND=host` → [workflow-host.md](workflow-host.md)

Do not load the other backend files. `BACKEND=none` and an explicit
`--review=rp` or `--review=export` terminate from the common workflow without
loading any backend file.

Conduct a John Carmack-level review of spec plans.

**Role**: Code Review Coordinator (NOT the reviewer)
**Backends**: Codex CLI (codex), GitHub Copilot CLI (copilot), Cursor CLI (cursor),
Claude Code CLI (claude), or host-native (`host`)

Read [working-rules.md](../../references/working-rules.md) first unless you already have this run; it holds for every step of this skill.

## Preamble — execute common routing exactly once

Read and execute [workflow.md](workflow.md) Phase 0 once. It defines `$FLOWCTL`,
parses an explicit `--review` mode before configured-backend resolution,
resolves `SPEC_ID`, and handles `ASK`, `none`, `rp` and `export`. Never invoke
`flowctl review-backend` a second time.

## Backend Selection

Priority (first match wins):

1. `--review=codex|copilot|cursor|claude|host|none`
2. Per-spec `default_review`
3. `FLOW_REVIEW_BACKEND`
4. `.flow/config.json` `review.backend`
5. Error — no auto-detection

Configured values accept `backend[:model[:effort]]`; `cursor` takes a model but
no effort, `claude` takes `claude[:<model>[:<effort>]]`, and `host` and `none` are bare-only.

## Common Critical Rules

- The coordinator never self-declares a verdict.
- Stick to one backend for the full review/fix cycle.
- If `REVIEW_RECEIPT_PATH` is set, every review verdict writes a receipt.
- Any backend/transport failure outputs `RETRY: no verdict (backend or transport failure)` and stops;
  never silently fall back to a different backend. Autonomous callers
  receive the same retry terminal and decide whether to re-enter. A no-verdict
  dispatch is refunded and recorded by flowctl; never manually reset the review
  counter for a transport failure. Exit 5 / `TRANSPORT_UNHEALTHY` means stop
  automatic retries and repair the backend.
- `none` skips only when selected explicitly or resolved from configuration.
- **Foreground rule:** run every `flowctl <backend> plan-review` call as one **blocking foreground** Bash call with a generous timeout (10 minutes; verdicts typically land in 1–7) — never `run_in_background` + monitor/poll (a background completion does not reliably resume a subagent context). Host-backend subagent dispatches are also blocking.

Backend-specific invocation, availability, model, session-continuity, receipt,
and anti-pattern rules live only in the selected backend file.

## Input

Arguments: $ARGUMENTS

Format: `<flow-spec-id> [focus areas] [--review=<mode>] [mode:autonomous]`. `mode:autonomous` marks an
unattended run (working-rules.md's review loop applies); it is not a focus area.

## Workflow

1. Execute [workflow.md](workflow.md) Phase 0.
2. If it returns for `none`, `rp` or `export`, stop. Do not read a backend file.
3. Read exactly the selected `workflow-<backend>.md`.
4. Execute one backend dispatch and carry its verdict directly into the shared
   Fix Loop below.
5. Continue in that loop until its terminal contract is satisfied.

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
2. Fix the user-edited current spec, never a checkpoint copy: edit the spec
   file in place (`spec_path` from `$FLOWCTL show <SPEC_ID> --json`), then
   persist that file. The file on disk is the input, so an edit the user made
   between cycles survives; on a `set-plan` failure, surface its error and stop
   the cycle.

   ```bash
   $FLOWCTL spec set-plan <SPEC_ID> --file <spec path> --json
   ```

3. Sync affected task specs when requirements, acceptance, design decisions,
   interfaces, retry/error semantics, or state values changed.
4. Re-enter the SAME selected backend file's re-review step. Never load or mix
   another backend. Codex/Copilot/Cursor/Claude resume only through a same-mode receipt;
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
$FLOWCTL checkpoint restore --spec <SPEC_ID> --json
```

Every re-review follows the selected backend file's receipt/status rules.
