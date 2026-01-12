# fn-9.4 flowctl integration lib

## Description

Create flowctl integration library for spawning and parsing output.

### File

`src/lib/flowctl.ts`

### Functions

```typescript
// Find flowctl path (bundled or .flow/bin)
function getFlowctlPath(): string

// Run flowctl command, parse JSON output
async function flowctl<T>(args: string[]): Promise<T>

// Specific commands
async function getEpics(): Promise<Epic[]>
async function getTasks(epicId: string): Promise<Task[]>
async function getTaskSpec(taskId: string): Promise<string>
async function getReadyTasks(epicId: string): Promise<{ready: Task[], in_progress: Task[], blocked: Task[]}>
```

### flowctl location (for npm-distributed TUI)

Search order:
1. `.flow/bin/flowctl` (installed via `/flow-next:setup`)
2. `./plugins/flow-next/scripts/flowctl` (repo-local plugin checkout)
3. `flowctl` or `flowctl.py` on PATH
4. Error with message: "flowctl not found. Run `/flow-next:setup` or ensure flow-next plugin is installed."

### Invocation

flowctl.py is a Python script with shebang. Invoke via:
```typescript
Bun.spawn(['python3', flowctlPath, ...args])
// OR if shebang works:
Bun.spawn([flowctlPath, ...args])
```

Detect which works and cache the method.

### Error handling

- Parse JSON errors gracefully
- Return typed error objects
- Handle non-zero exit codes
## Acceptance
- [ ] `getFlowctlPath()` finds flowctl or throws helpful error
- [ ] `flowctl(['epics', '--json'])` returns parsed JSON
- [ ] `getTasks('fn-1')` returns Task[] matching types
- [ ] `getTaskSpec('fn-1.1')` returns markdown string
- [ ] Errors include context (command, exit code, stderr)
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
