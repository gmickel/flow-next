# fn-32-opt-in-review-flags.3 --interactive flag: per-finding walkthrough + Ralph-block + deferred sink

## Description

Implement `--interactive` flag. On NEEDS_WORK, walk through each finding with the user via blocking question tool. Four actions per finding: Apply / Defer / Skip / Acknowledge. Deferred findings go to `.flow/review-deferred/<branch-slug>.md`. Hard-errors in Ralph mode.

**Size:** M

**Files:**
- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md` — flag parsing + Ralph-block
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md` — walkthrough flow
- `plugins/flow-next/skills/flow-next-impl-review/walkthrough.md` (new) — per-finding question flow + defer sink rules

## Skill parse + Ralph-block

```bash
INTERACTIVE=false
for arg in $ARGUMENTS; do
  case "$arg" in
    --interactive) INTERACTIVE=true ;;
  esac
done

# Ralph-block
if [[ "$INTERACTIVE" == "true" ]]; then
  if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
    echo "Error: --interactive requires a user at the terminal; not compatible with Ralph mode (REVIEW_RECEIPT_PATH or FLOW_RALPH detected)."
    exit 2
  fi
fi
```

**No env var form.** `--interactive` is per-invocation only to prevent accidental Ralph engagement. Documented explicitly in skill.

## walkthrough.md

### Flow

Active only when: NEEDS_WORK verdict + `--interactive` flag set + not in Ralph mode.

<!-- Updated by plan-sync: fn-32.2 merged set includes deep-pass findings tagged `pass: adversarial|security|performance` with fingerprint-deduped primary+deep collisions (primary wins, confidence promoted one anchor step). Walkthrough consumes the merged set from the receipt / findings output without caring about which pass produced each finding. -->

For each finding in the primary review output (or merged set if `--deep` also set — see fn-32.2 fingerprint merge + cross-pass promotion, or validated set if `--validate` also set):

1. Pre-load platform blocking question tool (Claude Code only): `ToolSearch select:AskUserQuestion` if not loaded.
2. Present question:

   ```
   Finding N/M:
   [P1, confidence 75, introduced] src/auth.ts:42 — null deref in middleware

   Detail: Accessing user.role without a guard leads to undefined when the
   session cookie is missing. The middleware runs before any authentication
   resolver, so undefined propagates into permission checks.

   Suggested fix: Add a current_user guard before line 42.

   What should the agent do?
     1. Apply — implement the suggested fix
     2. Defer — leave unresolved; record in .flow/review-deferred/<branch>.md
     3. Skip — ignore this finding entirely
     4. Acknowledge — note it but take no action (not a bug, or intentional)
     5. LFG the rest — apply recommended action for this + all remaining findings
   ```

3. Use platform blocking question tool:
   - Claude Code: `AskUserQuestion`
   - Codex: `request_user_input`
   - Gemini: `ask_user`
   - Pi: `ask_user` (requires pi-ask-user extension)
   - Fallback: numbered list in chat only when no blocking tool exists in harness

4. Record decision. Accumulate:
   - Apply list (findings to fix)
   - Defer list (findings to record)
   - Skip list (findings to log-only)
   - Acknowledge list (findings noted but not actioned)

5. **"LFG the rest" option**: remainder of findings get their recommended action auto-applied:
   - `safe_auto` → Apply
   - `gated_auto` / `manual` → Defer
   - `advisory` → Acknowledge
   - (classification inferred from severity + confidence if no explicit autofix_class)

   Then exit the walkthrough loop.

### After walkthrough

1. **Apply list**: dispatch fixer (worker agent or equivalent) to implement fixes for those findings only
2. **Defer list**: append to `.flow/review-deferred/<branch-slug>.md`:

   ```markdown
   # Deferred review findings — <branch-slug>

   ## <YYYY-MM-DD HH:MM> — review session <receipt-id>

   - [P1, confidence 75, introduced] src/auth.ts:42 — null deref in middleware
     - Suggested: Add current_user guard before line 42
     - Deferred reason: <user can optionally provide on defer, or default to "deferred by user">

   - [P2, confidence 50, introduced] src/cart.ts:88 — off-by-one on empty cart
     - Suggested: Use >= 1 instead of > 0
     - Deferred reason: needs product decision
   ```

   Format is append-only. Each review session creates a new `##` section with timestamp + receipt ID. User revisits this file manually.

3. **Skip / Acknowledge lists**: log in receipt but no further action

### Branch slug derivation

```bash
BRANCH=$(git branch --show-current)
BRANCH_SLUG=$(echo "$BRANCH" | tr '/' '-' | tr -cd 'a-zA-Z0-9-')
DEFER_FILE=".flow/review-deferred/${BRANCH_SLUG}.md"
```

Create `.flow/review-deferred/` directory if absent.

### Receipt extension

```python
if walkthrough_result:
    receipt_data["walkthrough"] = {
        "applied": len(apply_list),
        "deferred": len(defer_list),
        "skipped": len(skip_list),
        "acknowledged": len(acknowledge_list),
    }
```

### Verdict after walkthrough

- If Apply list empty → verdict stays NEEDS_WORK (no fixer dispatch; user chose not to fix anything)
- If Apply list non-empty + fixer completes → re-review by dispatching fresh impl-review invocation, then original walkthrough session exits

Actually simpler: after walkthrough, invoke fixer for Apply list, commit changes, and exit. Re-review is a separate user action. Keep walkthrough session bounded.

## Acceptance

- **AC1:** `--interactive` flag parsed; no env var form exists.
- **AC2:** Ralph detection (`REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1`) hard-errors with clear message on `--interactive` attempt.
- **AC3:** Walkthrough loop presents one finding at a time via blocking question tool (AskUserQuestion / request_user_input / ask_user).
- **AC4:** Four action options per finding (Apply / Defer / Skip / Acknowledge) plus "LFG the rest" escape hatch.
- **AC5:** Apply list dispatches fixer; only those findings get implemented.
- **AC6:** Defer list appended to `.flow/review-deferred/<branch-slug>.md` with timestamp + receipt ID section.
- **AC7:** `.flow/review-deferred/` directory created if absent.
- **AC8:** Receipt carries `walkthrough` object with counts per decision type.
- **AC9:** Skip / Acknowledge decisions are no-op beyond receipt logging.
- **AC10:** "LFG the rest" auto-classifies remaining findings by severity + confidence and exits loop.
- **AC11:** walkthrough.md documents the full flow including pre-load rule for AskUserQuestion.

## Dependencies

- None hard. Can land independently of tasks 1 & 2 (no shared code paths, just shared flag-parsing infrastructure).

## Done summary
Implemented fn-32.3 --interactive flag: SKILL.md parses the flag and hard-errors on Ralph env (REVIEW_RECEIPT_PATH / FLOW_RALPH) with exit 2 (no env-var form — per-invocation only). New walkthrough.md documents the per-finding flow (Apply / Defer / Skip / Acknowledge / LFG-rest) via platform blocking tools (AskUserQuestion / request_user_input / ask_user) with pre-load rule for deferred tool schemas. New flowctl review-walkthrough-defer appends deferred findings to .flow/review-deferred/<branch-slug>.md (append-only, auto-creates directory, stamps each session with timestamp + receipt id + session_id; per-finding deferred_reason override supported). New flowctl review-walkthrough-record stamps receipt.walkthrough counts (applied/deferred/skipped/acknowledged/lfg_rest) and walkthrough_timestamp without ever flipping verdict. workflow.md Step W.1-W.5 covers the full phase across all backends. .flow/bin mirror synced. 12 new smoke tests added (help, required args, sink creation, append-only multi-session, empty no-op, --branch override, verdict preservation, receipt creation, lfg-rest truthy parsing, Ralph-block enforcement); 125/125 total smoke tests pass. All 11 AC covered.
## Evidence
- Commits: b3bf3b71e455be0b2de6900c9f0d8edde7980bc3
- Tests: bash plugins/flow-next/scripts/smoke_test.sh (125 passed, 0 failed); bash Ralph-block trace (5 cases); flowctl review-walkthrough-defer/-record manual smoke (branch slug, append-only, empty no-op, --branch override, receipt preservation, lfg-rest parsing)
- PRs: