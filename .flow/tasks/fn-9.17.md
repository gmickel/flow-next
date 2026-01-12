# fn-9.17 Run spawning and detach

## Description
Implement ralph spawning and detach behavior for TUI.

### File

`src/lib/spawn.ts`

### Functions

```typescript
// Locate ralph.sh
function findRalphScript(): string | null

// Spawn ralph detached, return run ID
async function spawnRalph(epicId: string): Promise<{runId: string, pid: number}>

// Check if ralph is running for a run
async function isRalphRunning(runId: string): Promise<boolean>
```

### ralph.sh location

Search order:
1. `scripts/ralph/ralph.sh` (repo-local after /flow-next:ralph-init)
2. `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh`
3. Error with instructions to run `/flow-next:ralph-init`

### Detach semantics

- Spawn ralph via `Bun.spawn` with `detached: true`
- TUI Ctrl+C exits cleanly, ralph keeps running
- Store PID for potential future actions (stop/signal)

### Run ID

Ralph creates run ID in format `YYYY-MM-DD-NNN`. After spawn, poll `scripts/ralph/runs/` to detect new run.
## Acceptance
- [ ] `findRalphScript()` locates ralph.sh or returns null
- [ ] `spawnRalph()` starts ralph detached
- [ ] TUI exit (Ctrl+C) does not kill spawned ralph
- [ ] Run ID returned matches new run directory
- [ ] Missing ralph.sh shows helpful error message
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
