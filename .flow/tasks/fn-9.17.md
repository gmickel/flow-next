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
- Added `spawn.ts` with ralph spawning and detach functionality
- `findRalphScript()` searches scripts/ralph then plugin template
- `spawnRalph()` spawns detached, polls for new run ID
- `isRalphRunning()` checks progress.txt for COMPLETE marker

- Enables TUI to spawn ralph without blocking
- Clean Ctrl+C exit won't kill spawned ralph process

- All tests pass (383 total, 7 new for spawn.ts)
- Lint clean
## Evidence
- Commits: 49e181519aafc7d70070cd354bdddbf1f161565b
- Tests: bun test
- PRs: