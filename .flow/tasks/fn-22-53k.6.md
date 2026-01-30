# fn-22-53k.6 ralph-guard: completion_review receipt handling

## Description

Update hook enforcement for completion review receipts.

**Changes to `ralph-guard.py`:**

1. **Update `parse_receipt_path()` (~line 258)**:
   - Handle `completion-fn-N.json` pattern (like `plan-fn-N.json`)
   - Extract epic ID from filename

2. **Track completion review calls** in PostToolUse (~line 278):
   - Track `flowctl codex completion-review` calls
   - Track verdict from response

3. **Receipt validation:**
   - Accept `type: "completion_review"` receipts
   - Validate verdict field exists

4. **Stop-hook routing** in `handle_stop()` (~line 312):
   - When receipt path matches `completion-*.json`, route to `/flow-next:epic-review`
   - Pattern: `if "completion-" in receipt_path: recommend "/flow-next:epic-review <epic_id>"`
   - Same pattern as plan-review routing to `/flow-next:plan-review`

**NOTE:** Epic close gating is enforced in `ralph.sh`, not ralph-guard. The guard hook handles:
- Interactive/manual `flowctl epic close` calls (when outside Ralph loop)
- Receipt file validation
- Tracking codex completion-review calls

**Gap task creation (removed from this task):**
Primary behavior is fix-inline during skill execution. Gap task creation is handled by skill if needed (calls `flowctl task create` directly). No new flowctl command needed.

**Pattern reference:** ralph-guard.py:258-276 for `parse_receipt_path()`, 307-319 for codex tracking

## Acceptance

- [ ] `parse_receipt_path()` handles `completion-fn-N.json` pattern
- [ ] ralph-guard tracks `flowctl codex completion-review` calls
- [ ] Receipt with `type: "completion_review"` accepted and validated
- [ ] Stop-hook routes `completion-*.json` receipts to `/flow-next:epic-review`

## Done summary
Updated ralph-guard.py to support completion_review receipts: parse_receipt_path() handles completion-fn-N.json pattern, PostToolUse tracks codex completion-review calls, handle_stop() routes to /flow-next:epic-review, and receipt validation enforces verdict field for completion receipts.
## Evidence
- Commits: 4801673a142970c0f902978b05d4db4685507c1d
- Tests: python3 -m py_compile ralph-guard.py, smoke_test.sh (45/45 passed)
- PRs: