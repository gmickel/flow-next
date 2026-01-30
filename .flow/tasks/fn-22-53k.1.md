# fn-22-53k.1 flowctl: completion_review_status field + selector

## Description

Add infrastructure for epic completion review status tracking.

**Changes to `flowctl.py`:**

1. **`normalize_epic()` (~line 598)** - Add default fields:
   ```python
   if "completion_review_status" not in epic_data:
       epic_data["completion_review_status"] = "unknown"
   if "completion_reviewed_at" not in epic_data:
       epic_data["completion_reviewed_at"] = None
   ```

2. **New command: `epic set-completion-review-status`** - Follow `cmd_epic_set_plan_review_status()` pattern at line 3212:
   ```bash
   flowctl epic set-completion-review-status fn-N --status ship|needs_work|unknown [--json]
   ```

3. **Update `cmd_next()` selector (~line 4072)** - Add `--require-completion-review` flag:
   - New argparse flag: `--require-completion-review` (like `--require-plan-review`)
   - After checking all tasks done, before returning `none`:
     - If flag set AND `completion_review_status != "ship"`, return `{"status": "completion_review", "epic": epic_id, "reason": "needs_completion_review"}`
   - **CRITICAL:** Only check when flag is passed (backwards compatible)

**Pattern reference:** `cmd_epic_set_plan_review_status()` at flowctl.py:3212-3247, `--require-plan-review` handling at flowctl.py:4072

## Acceptance

- [ ] `flowctl show fn-N --json` includes `completion_review_status` and `completion_reviewed_at` fields
- [ ] `flowctl epic set-completion-review-status fn-N --status ship` works
- [ ] `flowctl next --require-completion-review --json` returns `status=completion_review` when epic has all tasks done but `completion_review_status != ship`
- [ ] `flowctl next --json` (without flag) returns `status=none` as before (backwards compatible)
- [ ] Smoke test passes: `./plugins/flow-next/scripts/smoke_test.sh`

## Done summary
Added completion_review_status infrastructure to flowctl: normalize_epic() defaults, epic set-completion-review-status command, and --require-completion-review flag for next selector that returns status=completion_review when all tasks done but review not shipped.
## Evidence
- Commits: 2fb84b06f171d55ed11284db33815f316cf547fa
- Tests: ./plugins/flow-next/scripts/smoke_test.sh (45/45 passed), manual: flowctl show --json, epic set-completion-review-status, next --require-completion-review
- PRs: