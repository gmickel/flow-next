# fn-12.4 Update epic create to generate fn-N-xxx format

## Description
TBD

## Acceptance
- [ ] TBD

## Done summary
- Updated `cmd_epic_create()` to generate suffix via `generate_epic_suffix()`
- New epics now use `fn-N-xxx` format (e.g., fn-1-5lh)
- Verified with test: creates fn-1-xxx, fn-2-yyy correctly
## Evidence
- Commits: df07feea2d2082f975b51cdf3c721b8fc5c29381
- Tests: manual epic create test
- PRs: