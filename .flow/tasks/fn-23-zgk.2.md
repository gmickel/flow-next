# fn-23-zgk.2 Update ID regex patterns

## Description
Update all regex patterns that parse epic/task IDs to support variable-length slugs while maintaining backwards compatibility with existing formats.

**Size:** M
**Files:** 
- `plugins/flow-next/scripts/flowctl.py` (4 regex locations)
- `plugins/flow-next/scripts/hooks/ralph-guard.py` (1 location)

## Approach

<!-- Updated by plan-sync: fn-23-zgk.1 already updated flowctl.py regexes with alternation pattern -->

**Already done in fn-23-zgk.1:** flowctl.py regex updates at lines 629, 1781, 4214, 6496 using:
```python
r"^fn-(\d+)(?:-[a-z0-9][a-z0-9-]*[a-z0-9]|-[a-z0-9]{1,3})?(?:\.(\d+))?$"
```

**Remaining work:** Update ralph-guard.py receipt parsing at lines 276, 280, 284:
```python
# Current: r"plan-(fn-\d+(?:-[a-z0-9]{3})?)\.json$"
# New: r"plan-(fn-\d+(?:-[a-z0-9][a-z0-9-]*[a-z0-9]|-[a-z0-9]{1,3})?)\.json$"
```
Same pattern for impl and completion matches

## Key context

The regex must accept all three formats:
- `fn-1` (legacy numeric only)
- `fn-1-abc` (current 3-char random)
- `fn-1-add-oauth-login` (new slugified)

Pattern explanation:
- `[a-z0-9]` - must start with alphanumeric
- `(?:[a-z0-9-]*[a-z0-9])?` - optional middle with hyphens, must end alphanumeric
- This prevents leading/trailing hyphens in slug
## Acceptance
<!-- Updated by plan-sync: flowctl.py items already done in fn-23-zgk.1 -->
- [x] `parse_id("fn-1")` returns valid (legacy format) - done in fn-23-zgk.1
- [x] `parse_id("fn-1-abc")` returns valid (3-char format) - done in fn-23-zgk.1
- [x] `parse_id("fn-1-add-oauth")` returns valid (slug format) - done in fn-23-zgk.1
- [x] `parse_id("fn-1.2")` returns valid (legacy task) - done in fn-23-zgk.1
- [x] `parse_id("fn-1-abc.2")` returns valid (3-char task) - done in fn-23-zgk.1
- [x] `parse_id("fn-1-add-oauth.2")` returns valid (slug task) - done in fn-23-zgk.1
- [x] `parse_id("fn-1-")` returns invalid (trailing hyphen) - done in fn-23-zgk.1
- [x] `parse_id("fn-1--double")` returns invalid (double hyphen) - done in fn-23-zgk.1
- [x] File glob patterns match all three formats - done in fn-23-zgk.1
- [ ] ralph-guard receipt parsing works with slug format
- [ ] All 45 smoke tests pass
## Done summary
Updated ralph-guard.py parse_receipt_path() regex to support variable-length slugs. All 45 smoke tests pass.
## Evidence
- Commits: c14a11f9566da386af16bf10b570c854eeb3f9da
- Tests: python3 regex acceptance tests (all pass), smoke_test.sh (45/45 pass)
- PRs: