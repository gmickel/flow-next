# fn-12.8 Update TUI test fixtures for new format

## Description
TBD

## Acceptance
- [ ] TBD

## Done summary
- Added 3 new tests for collision-resistant ID format:
  - `getReceiptStatus` with fn-N-xxx.M format
  - `getBlockReason` with fn-N-xxx.M format
  - `discoverRuns` parses epic=fn-N-xxx from progress.txt
- All 382 TUI tests pass
## Evidence
- Commits: 98836eea71c94eee0823b31b8bda2d58afbe3054
- Tests: bun test (382 pass)
- PRs: