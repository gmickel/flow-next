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
- `BACKEND=host` → [workflow-host.md](workflow-host.md)
- `BACKEND=rp` → [workflow-rp.md](workflow-rp.md)

Do not load the other backend files. `BACKEND=none` and explicit
`--review=export` terminate from the common workflow without loading any backend
file.

Conduct a John Carmack-level review of spec plans.

**Role**: Code Review Coordinator (NOT the reviewer)
**Backends** (branch on the common workflow's `RP_ELIGIBLE` probe):
- When `RP_ELIGIBLE=1`: RepoPrompt (rp), Codex CLI (codex), GitHub Copilot CLI
 (copilot), Cursor CLI (cursor), or host-native (`host`)
- When `RP_ELIGIBLE=0`: Codex CLI, GitHub Copilot CLI, Cursor CLI, or
 host-native — rp remains accepted explicitly but errors at runtime

## Preamble — execute common routing exactly once

Read and execute [workflow.md](workflow.md) Phase 0 once. It defines `$FLOWCTL`,
probes RepoPrompt eligibility, parses an explicit `--review` mode before
configured-backend resolution, resolves `SPEC_ID`, and handles `ASK`, `none`,
and `export`. Never invoke `flowctl review-backend` a second time.

When `RP_ELIGIBLE=0`, never steer the user toward rp. An explicit
`--review=rp`, `FLOW_REVIEW_BACKEND=rp`, or `review.backend=rp` remains valid
input and fails through the rp runtime check.

## Backend Selection

Priority (first match wins):

1. `--review=rp|codex|copilot|cursor|host|export|none`
2. Per-spec `default_review`
3. `FLOW_REVIEW_BACKEND`
4. `.flow/config.json` `review.backend`
5. Error — no auto-detection

Configured values accept `backend[:model[:effort]]`; `cursor` takes a model but
no effort, and `host`, `rp`, and `none` are bare-only. `export` is a one-off
mode, never a configured backend.

## Common Critical Rules

- The coordinator never self-declares a verdict.
- Stick to one backend for the full review/fix cycle.
- If `REVIEW_RECEIPT_PATH` is set, every review verdict writes a receipt.
- Any backend/transport failure outputs `<promise>RETRY</promise>` and stops;
 never silently fall back to a different backend. Autonomous/Ralph callers
 receive the same retry terminal and decide whether to re-enter. A no-verdict
 dispatch is refunded and recorded by flowctl; never manually reset the review
 counter for a transport failure. Exit 5 / `TRANSPORT_UNHEALTHY` means stop
 automatic retries and repair the backend.
- `none` skips only when selected explicitly or resolved from configuration.
- `export` emits the existing external-review artifact and terminal output,
 then returns; it never loads configured-backend guidance, writes a review
 receipt/status, or enters the fix loop.
- **Foreground rule:** run every `flowctl <backend> plan-review` call as one **blocking foreground** Bash call with a generous timeout (10 minutes; verdicts typically land in 1–7) — never `run_in_background` + monitor/poll (a background completion does not reliably resume a subagent context). Host-backend subagent dispatches are also blocking.

Backend-specific invocation, availability, model, session-continuity, receipt,
and anti-pattern rules live only in the selected backend file.

## Input

Arguments: $ARGUMENTS

Format: `<flow-spec-id> [focus areas] [--review=<mode>]`

## Workflow

1. Execute [workflow.md](workflow.md) Phase 0.
2. If it returns for `none` or `export`, stop. Do not read a backend file.
3. Read exactly the selected `workflow-<backend>.md`.
4. Execute one backend dispatch and return its verdict here.
5. Apply the shared Fix Loop below.

## Fix Loop (INTERNAL - do not exit to Ralph)

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid
issues and re-review. Never use the plain-text numbered prompt in this loop.**

`MAJOR_RETHINK` is not a fix-loop input. Surface the reviewer's rationale and
stop with `BLOCKED: DESIGN_CONFLICT` (Ralph: `<promise>RETRY</promise>`). Only
`NEEDS_WORK` enters the loop.

Fix+re-review cycles are bounded at `${MAX_REVIEW_ITERATIONS:-4}`. The counter
is flowctl-owned; never keep an agent-side counter. On cap exhaustion, surface
surviving findings and stop (Ralph: `<promise>RETRY</promise>`).

**The cap is enforced deterministically by flowctl:** every dispatch reserves a
spec-scoped round before launch. SHIP / NEEDS_WORK / MAJOR_RETHINK consume it;
a no-verdict transport failure is durably recorded and refunded. At
`${MAX_REVIEW_ITERATIONS:-4}` verdict rounds, flowctl refuses with `ESCALATE:`
and exit 4. More than `${MAX_REVIEW_TRANSPORT_FAILURES:-2}` consecutive
no-verdict failures stop separately with `TRANSPORT_UNHEALTHY` + exit 5.
Callers invoke plan-review once and act on its terminal result. The verdict
counter resets only on SHIP or an explicit re-plan, never on an edit, fresh
invocation, or transport failure.**

When the verdict is `NEEDS_WORK`:

1. Parse all valid issues from reviewer feedback.
2. Fix the user-edited current spec, never a checkpoint copy:

 ```bash
 $FLOWCTL spec set-plan <SPEC_ID> --file - --json <<'EOF'
 <updated current spec content>
 EOF
 ```

3. Sync affected task specs when requirements, acceptance, design decisions,
 interfaces, retry/error semantics, or state values changed.
4. Re-enter the SAME selected backend file's re-review step. Never load or mix
 another backend. Codex/Copilot/Cursor resume only through a same-mode receipt;
 host uses a fresh read-only subagent; rp stays in the same chat.
5. Repeat until `SHIP`, `MAJOR_RETHINK`, backend failure, or deterministic cap.

Recovery after context compaction:

```bash
$FLOWCTL checkpoint restore --spec <SPEC_ID> --json
```

For rp, only the first review uses `--new-chat`; all re-reviews stay in the same
chat. Every re-review follows the selected backend file's receipt/status rules.
