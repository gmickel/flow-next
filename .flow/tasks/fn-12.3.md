# fn-12.3 Update scan_max_epic_id() to ignore suffix

## Description
TBD

## Acceptance
- [ ] TBD

## Done summary
- Updated regex in `scan_max_epic_id()` to match optional suffix
- Extracts numeric part correctly for both fn-N.json and fn-N-xxx.json
## Evidence
- Commits: 62f1d2637ed58b6776432a17b64d0e5b3936b8d5
- Tests: inline regex test
- PRs: