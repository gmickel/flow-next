# Plan readiness warning (fn-58)

Load this reference only when the Step 1 readiness soft-check printed its
sentinel (`READINESS_WARN=true`): the input resolved to an existing SPEC that is
not marked ready, in a repo that has adopted readiness. Ready specs, task ids,
freeform ideas (Route B), and non-adopting repos never reach this file.

- **Non-interactive / Ralph / autonomous** (any non-interactive marker: `FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH` set, `FLOW_AUTONOMOUS=1`, or the `mode:autonomous` token parsed in SKILL.md — treat the marker *family* as the gate, not a rigid two-var list): auto-proceed with one stderr line, never block:
 ```bash
 echo "[READINESS]: spec <id> not marked ready — proceeding (non-interactive)" >&2
 ```
**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

- **Interactive**: ask exactly one question via the `plain-text numbered prompt` tool (lead with recommendation; default proceed — planning is non-destructive and often part of getting a spec ready). The option set splits by tracker mode:
 - **`tracker.readyState` not configured** (local readiness):
 - **header**: `Spec not ready`
 - **body**: `<spec-id> is not marked ready (readiness is in use in this repo). Recommended: proceed — planning is non-destructive and refining a draft is normal. Confidence: [high].`
 - **options** (frozen): `proceed` (default — continue to research), `mark-ready-then-proceed` (run `$FLOWCTL spec ready <id> --json`, then continue), `abort` (exit 0 — no spec or task changes made; re-run /flow-next:plan once the spec is blessed)
 - **`tracker.readyState` configured** (tracker-authoritative readiness — one-way pull; never offer local mark-ready — the next sync would silently revert it):
 - **header**: `Spec not ready`
 - **body**: `<spec-id> is not marked ready; readiness projects from the tracker (state: <readyState>). Recommended: proceed — planning is non-destructive. Confidence: [high].`
 - **options** (frozen): `proceed` (default — continue to research), `abort` (exit 0 — no spec or task changes made), `update-tracker-state-then-rerun` (exit 0 with guidance: move the linked issue to "<readyState>" on the board, pull via /flow-next:tracker-sync, re-run /flow-next:plan)

Never a hard block — `abort` / `update-tracker-state-then-rerun` are user choices, not skill-imposed stops (R6).

After the chosen option continues, return to Step 1 and run the scout fan-out.
