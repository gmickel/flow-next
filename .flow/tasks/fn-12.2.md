# fn-12.2 Update parse_id() regex for dual-pattern support

## Description
TBD

## Acceptance
- [ ] TBD

## Done summary
- Updated `parse_id()` regex: `fn-(\d+)(?:-[a-z0-9]{3})?(?:\.(\d+))?`
- Updated `epic_id_from_task()` to preserve suffix via string split
- Verified with tests for legacy and new formats
## Evidence
- Commits: 75be01ae97efbede5cdf1b0b49e52ad835e5a551
- Tests: inline python test
- PRs: