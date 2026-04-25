You are running one Ralph plan gate iteration.

Inputs:
- EPIC_ID={{EPIC_ID}}
- PLAN_REVIEW={{PLAN_REVIEW}} (may be spec form, e.g. `codex:gpt-5.4:xhigh`)
- PLAN_REVIEW_BACKEND={{PLAN_REVIEW_BACKEND}} (bare backend name — use this for branching)
- REQUIRE_PLAN_REVIEW={{REQUIRE_PLAN_REVIEW}}

The full spec is also exported as `FLOW_REVIEW_BACKEND` for flowctl to resolve model + effort.

Steps:
1) Re-anchor:
 - scripts/ralph/flowctl show {{EPIC_ID}} --json
 - scripts/ralph/flowctl cat {{EPIC_ID}}
 - git status
 - git log -10 --oneline

2) Save checkpoint (recovery point if context compacts during review cycles):
 ```bash
 scripts/ralph/flowctl checkpoint save --epic {{EPIC_ID}} --json
 ```

Ralph mode rules (must follow):
- Branch on PLAN_REVIEW_BACKEND (bare name), NOT the full PLAN_REVIEW spec.
 Spec form (e.g. `codex:gpt-5.4:xhigh`) carries model + effort; the backend
 name picks the wrapper and the full spec flows through `FLOW_REVIEW_BACKEND`.
- If PLAN_REVIEW_BACKEND=rp: use `flowctl rp` wrappers (setup-review, select-add, prompt-get, chat-send).
- If PLAN_REVIEW_BACKEND=codex: use `flowctl codex` wrappers (plan-review with --receipt).
- If PLAN_REVIEW_BACKEND=copilot: use `flowctl copilot` wrappers (plan-review with --receipt). Never call `copilot` directly; never pass `--continue`.
- Write receipt via bash heredoc (no Write tool) if `REVIEW_RECEIPT_PATH` set.
- If any rule is violated, output `<promise>RETRY</promise>` and stop.

3) Plan review gate (branch on bare backend; full spec is already in env):
 - If PLAN_REVIEW_BACKEND=rp: run `/flow-next:plan-review {{EPIC_ID}} --review=rp`
 - If PLAN_REVIEW_BACKEND=codex: run `/flow-next:plan-review {{EPIC_ID}} --review=codex`
 - If PLAN_REVIEW_BACKEND=copilot: run `/flow-next:plan-review {{EPIC_ID}} --review=copilot`
 - If PLAN_REVIEW_BACKEND=export: run `/flow-next:plan-review {{EPIC_ID}} --review=export`
 - If PLAN_REVIEW_BACKEND=none:
 - If REQUIRE_PLAN_REVIEW=1: output `<promise>RETRY</promise>` and stop.
 - Else: set ship and stop:
 `scripts/ralph/flowctl epic set-plan-review-status {{EPIC_ID}} --status ship --json`

 Note: when PLAN_REVIEW is spec form (e.g. `codex:gpt-5.4:xhigh`), the
 /flow-next:plan-review skill picks up the spec from `FLOW_REVIEW_BACKEND`
 automatically — no extra flag needed.

4) The skill will loop internally until `<verdict>SHIP</verdict>`:
 - First review uses `--new-chat`
 - If NEEDS_WORK: skill fixes plan AND syncs affected task specs, re-reviews in SAME chat (no --new-chat)
 - Repeats until SHIP
 - Only returns to Ralph after SHIP or MAJOR_RETHINK
 - If context compacts mid-review: `scripts/ralph/flowctl checkpoint restore --epic {{EPIC_ID}} --json`

5) IMMEDIATELY after SHIP verdict, write receipt (for rp mode):
 ```bash
 mkdir -p "$(dirname '{{REVIEW_RECEIPT_PATH}}')"
 ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
 cat > '{{REVIEW_RECEIPT_PATH}}' <<EOF
 {"type":"plan_review","id":"{{EPIC_ID}}","mode":"rp","verdict":"SHIP","timestamp":"$ts","iteration":{{RALPH_ITERATION}}}
 EOF
 ```
 For codex mode, receipt is written automatically by `flowctl codex plan-review --receipt`.
 For copilot mode, receipt is written automatically by `flowctl copilot plan-review --receipt`.
 **CRITICAL: Copy EXACTLY. The `"id":"{{EPIC_ID}}"` and `"verdict":"SHIP"` fields are REQUIRED.**
 Missing id/verdict = verification fails = forced retry.

6) After SHIP:
 - `scripts/ralph/flowctl epic set-plan-review-status {{EPIC_ID}} --status ship --json`
 - stop (do NOT output promise tag)

7) If MAJOR_RETHINK (rare):
 - `scripts/ralph/flowctl epic set-plan-review-status {{EPIC_ID}} --status needs_work --json`
 - output `<promise>FAIL</promise>` and stop

8) On hard failure, output `<promise>FAIL</promise>` and stop.

## ⛔ FORBIDDEN OUTPUT
**NEVER output `<promise>COMPLETE</promise>`** — this prompt handles ONE epic only.
Ralph detects all-work-complete automatically via the selector. Outputting COMPLETE here is INVALID and will be ignored.
