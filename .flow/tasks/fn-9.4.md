# fn-9.4 flowctl integration lib

## Description

Create flowctl integration library for spawning and parsing output.

### File

`src/lib/flowctl.ts`

### Functions

```typescript
// Find flowctl path (bundled or .flow/bin)
// Note: async due to filesystem checks during path resolution
async function getFlowctlPath(): Promise<string>

// Run flowctl command, parse JSON output
async function flowctl<T>(args: string[]): Promise<T>

// List commands (return minimal types matching flowctl output)
async function getEpics(): Promise<EpicListItem[]>  // id, title, status, tasks (count), done (count)
async function getTasks(epicId: string): Promise<TaskListItem[]>  // id, epic, title, status, priority, depends_on
async function getReadyTasks(epicId: string): Promise<ReadyResponse>  // ready/in_progress/blocked TaskSummary arrays

// Detail commands (return full types via flowctl show)
async function getEpic(epicId: string): Promise<Epic>
async function getTask(taskId: string): Promise<Task>
async function getTaskSpec(taskId: string): Promise<string>
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
- Added `src/lib/flowctl.ts` with path resolution and JSON command runner
- Searches .flow/bin, plugins dir, repo root (via .git/HEAD), then PATH
- Helper functions: getEpics, getTasks, getTaskSpec, getReadyTasks, getEpic, getTask
- FlowctlError class with command, exit code, stderr context

Why:
- TUI needs to invoke flowctl commands and parse results
- Path resolution handles running from subdirectories

Verification:
- 32 tests pass including integration tests with real flowctl
- Lint clean (oxlint)
## Evidence
- Commits: 54a450cc6f6f1d6d2aaa4f46eed3dec2a134d788
- Tests: bun test
- PRs: