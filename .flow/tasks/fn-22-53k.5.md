# fn-22-53k.5 ralph: completion review gate in maybe_close_epics

## Description

Gate epic closure on completion review in Ralph.

**Changes to `ralph.sh` template:**

1. **New env var** (near `PLAN_REVIEW` and `WORK_REVIEW`):
   - `COMPLETION_REVIEW=rp|codex|none` - controls backend (no separate REQUIRE_ var; `!= none` is the gate)

2. **Update `maybe_close_epics()` (~line 767):**
   Gate on BOTH status AND receipt:
   ```bash
   if [[ "$all_done" == "1" ]]; then
     if [[ "$COMPLETION_REVIEW" != "none" ]]; then
       review_status="$(json_get completion_review_status "$json")"
       if [[ "$review_status" != "ship" ]]; then
         # Don't close - selector will return completion_review status
         continue
       fi
       # Also verify receipt exists (ralph.sh enforces, not just guard)
       if ! verify_receipt "$RECEIPTS_DIR/completion-${epic}.json" "completion_review" "$epic"; then
         continue
       fi
     fi
     "$FLOWCTL" epic close "$epic" --json >/dev/null 2>&1 || true
   fi
   ```

3. **New prompt template:** `prompt_completion.md`
   - Follow `prompt_plan.md` structure exactly
   - Invoked when selector returns `status=completion_review`
   - Runs `/flow-next:epic-review {{EPIC_ID}}`
   - On SHIP: `flowctl epic set-completion-review-status {{EPIC_ID}} --status ship`
   - On NEEDS_WORK: agent fixes gaps, re-reviews until SHIP

4. **Iteration loop update (~line 876):**
   - Add `elif [[ "$status" == "completion_review" ]]; then` block BEFORE the `else` clause
   - Handle like `plan` status: set env vars, render prompt, run Claude
   - Set `REVIEW_RECEIPT_PATH="$RECEIPTS_DIR/completion-${epic_id}.json"`
   - Set `export FLOW_REVIEW_BACKEND="$COMPLETION_REVIEW"` (skill reads this)
   - When `COMPLETION_REVIEW != none`, pass flag to selector: `$FLOWCTL next --require-completion-review`
   - **CRITICAL:** Must add new status handler before `else` clause or ralph.sh will `fail`

**Pattern reference:** Plan review gate at ralph.sh:876-888, `verify_receipt()` at ralph.sh:773-791

## Acceptance

- [ ] `COMPLETION_REVIEW=rp|codex|none` env var recognized
- [ ] `maybe_close_epics()` checks BOTH `completion_review_status=ship` AND valid receipt
- [ ] Selector called with `--require-completion-review` when `COMPLETION_REVIEW != none`
- [ ] Status `completion_review` triggers `prompt_completion.md`
- [ ] `prompt_completion.md` follows `prompt_plan.md` pattern
- [ ] `FLOW_REVIEW_BACKEND="$COMPLETION_REVIEW"` exported for skill

## Done summary
Added COMPLETION_REVIEW gate to ralph.sh: env var, maybe_close_epics checks status+receipt, selector flag, completion_review status handler with prompt_completion.md, and progress logging.
## Evidence
- Commits: 64b53fd, 7145d57
- Tests: bash -n ralph.sh, smoke_test.sh (45/45 passed)
- PRs: