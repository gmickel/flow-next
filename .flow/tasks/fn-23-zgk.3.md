# fn-23-zgk.3 Update error messages and CLI help

## Description
Update all error messages and CLI help text that reference ID format to show the new slug-based format.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`

## Approach

1. Find all error messages with "Expected format: fn-N or fn-N-xxx":
   ```bash
   grep -n "Expected format" plugins/flow-next/scripts/flowctl.py
   ```
   (~30 occurrences)

2. Update format string to:
   ```
   "Expected format: fn-N or fn-N-slug (e.g., fn-1, fn-1-abc, fn-1-add-oauth)"
   ```

3. Update CLI help text (argparse `help=` strings):
   ```bash
   grep -n 'help=".*fn-' plugins/flow-next/scripts/flowctl.py
   ```
   (~15 occurrences)

4. Update examples to use descriptive slugs:
   - `fn-1-abc` → `fn-1-add-auth` (for epic examples)
   - Keep showing both formats in format descriptions

## Key context

Use find-replace with care - some messages are for epics (`fn-N`), some for tasks (`fn-N.M`). Keep the distinction.
## Acceptance
- [ ] All "Expected format" messages updated (~30 locations)
- [ ] All CLI `help=` strings updated (~15 locations)
- [ ] Examples use descriptive slugs (add-auth, fix-bug, etc.)
- [ ] Epic format shows: `fn-N or fn-N-slug`
- [ ] Task format shows: `fn-N.M or fn-N-slug.M`
- [ ] No hardcoded `fn-1-abc` examples remain (except in backwards compat notes)
- [ ] `flowctl --help` shows new format
- [ ] `flowctl epic --help` shows new format
## Done summary
Updated 31 error messages and 31 CLI help strings to use slug-based ID format with descriptive examples (fn-1-add-auth instead of fn-1-abc).
## Evidence
- Commits: 13fbff5fa74a0b8fc1ef53e98a50cdc03b65d03a, 530a71346b1acd1bb15a49e051c29c9ff271aed8
- Tests: smoke_test.sh (45 tests pass)
- PRs: