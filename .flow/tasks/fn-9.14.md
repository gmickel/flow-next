# fn-9.14 App integration and state

## Description

Wire up all components into main App with state management.

### File

`src/app.ts`

### State

```typescript
interface AppState {
  runs: Run[];
  currentRun?: Run;
  tasks: Task[];
  selectedTaskIndex: number;
  outputBuffer: LogEntry[];
  iteration: number;
  elapsed: number;
  showHelp: boolean;
  error?: string;
}
```

### Polling

- flowctl tasks: every 2s
- Timer: every 1s
- Log watcher: on file change

### Layout

```
┌────────────────────────────────────────────────────┐
│ Header (2 rows)                                     │
├─────────────────┬──────────────────────────────────┤
│ TaskList        │ TaskDetail                        │
│                 │                                   │
├─────────────────┴──────────────────────────────────┤
│ OutputPanel                                         │
├────────────────────────────────────────────────────┤
│ StatusBar                                           │
└────────────────────────────────────────────────────┘
```

### Auto-compact mode

Triggers: width < 120 OR height < 30

**Compact layout:**
- Header: single row (status + task ID + timer)
- TaskList: hidden
- TaskDetail: hidden
- OutputPanel: full width
- StatusBar: visible

**Preserved behavior in compact:**
- j/k still cycles through tasks (blind nav)
- ? help overlay still works
- q quit works

### Startup

1. Check .flow/ exists → if not: error "No .flow/ directory. Run flowctl init or ensure you're in a flow-next project."
2. Check scripts/ralph/ exists → if not: error "No scripts/ralph/. Run /flow-next:ralph-init to scaffold Ralph."
3. Discover runs
4. Auto-select latest OR prompt "No runs found. Start Ralph now? [y/n]"

On error: render error view with message + exit code 1 (not crash)
## Acceptance
- [ ] All components render in layout
- [ ] Task selection updates detail panel
- [ ] Log entries stream to output panel
- [ ] Timer updates every second
- [ ] j/k navigates task list
- [ ] ? toggles help overlay
- [ ] q quits cleanly
- [ ] Auto-compact triggers on small terminals (< 120x30)
- [ ] Compact mode hides TaskList/Detail, shows Output full-width
- [ ] j/k still works in compact mode
- [ ] Missing .flow/ shows specific error message
- [ ] Missing scripts/ralph/ shows specific error message
- [ ] Error view renders cleanly (not exception trace)
## Done summary
- Implemented App class with AppState interface and pi-tui Component integration
- Wired Header, TaskList, TaskDetail, OutputPanel, StatusBar, HelpOverlay components
- Added polling (tasks 2s, timer 1s), log watcher integration
- Implemented auto-compact mode for small terminals (< 120x30)
- Added startup validation (.flow/, scripts/ralph/) with clean error messages
- Run discovery and auto-select latest; prompt to spawn ralph if no runs

Verified via bun test (386 tests pass), bun lint (0 errors)
## Evidence
- Commits: 9060bb7
- Tests: bun test
- PRs: