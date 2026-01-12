# fn-9.5 Run discovery lib

## Description

Create run discovery library to find and manage Ralph runs.

### File

`src/lib/runs.ts`

### Functions

```typescript
// Scan runs directory for all runs
async function discoverRuns(): Promise<Run[]>

// Detect if run is active (check progress.txt for COMPLETE)
async function isRunActive(runPath: string): Promise<boolean>

// Get latest run (by date-based ID)
function getLatestRun(runs: Run[]): Run | undefined

// Get run details (iteration, epic, etc)
async function getRunDetails(runPath: string): Promise<RunDetails>
```

### Run directory structure

```
scripts/ralph/runs/<run-id>/
├── progress.txt     # Check for COMPLETE marker
├── iter-*.log       # Count for iteration number
├── attempts.json
├── branches.json
└── receipts/
```

### Active detection

Parse progress.txt, look for line containing `promise=COMPLETE` or `<promise>COMPLETE</promise>`.

### Receipts access

```typescript
// Get receipt status for a task
async function getReceiptStatus(runPath: string, taskId: string): Promise<{plan?: boolean, impl?: boolean}>
```

Receipts live in `runs/<id>/receipts/`. Files: `plan-<task-id>.json`, `impl-<task-id>.json`.

### Block reason

```typescript
// Get block reason if task is blocked
async function getBlockReason(taskId: string): Promise<string | null>
```

Block reason files: `.flow/blocks/block-<task-id>.md` or `runs/<id>/block-<task-id>.md`.

### Run validation

`--run <id>` validation rules:
- Exact match required on run ID
- If not found: error "Run '<id>' not found. Available: <list>"
- If corrupt (missing progress.txt): warn but allow
## Acceptance
- [ ] `discoverRuns()` returns Run[] sorted by date (newest first)
- [ ] `isRunActive()` correctly detects COMPLETE marker
- [ ] `getLatestRun()` returns most recent run
- [ ] Handles missing runs directory gracefully
- [ ] Handles empty runs directory
- [ ] `getReceiptStatus()` returns receipt state for task
- [ ] `getBlockReason()` returns block reason or null
- [ ] Run validation returns clear error for invalid run ID
## Done summary
- Added run discovery library with discoverRuns(), isRunActive(), getLatestRun()
- Added getRunDetails() for detailed run information
- Added getReceiptStatus() and getBlockReason() for receipts/blocks
- Added validateRun() with clear error messages for invalid run IDs

Why:
- TUI needs to find and display Ralph runs
- Receipt/block status needed for task detail panel

Verification:
- 23 tests pass covering all functions
- Lint clean
## Evidence
- Commits: f2bcbc2e51ad40985f9b7f9bce17b738d9b8a087
- Tests: bun test
- PRs: