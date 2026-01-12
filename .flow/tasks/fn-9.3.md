# fn-9.3 Types and interfaces

## Description

Define TypeScript types/interfaces for all data structures.

### File

`src/lib/types.ts`

### Types needed

```typescript
// NOTE: Status values match flowctl.py EPIC_STATUS and TASK_STATUS constants
interface Epic {
  id: string;          // fn-N
  title: string;
  status: 'open' | 'done';  // flowctl EPIC_STATUS
  branch_name: string;
  spec_path: string;
}

interface Task {
  id: string;          // fn-N.M
  epic: string;
  title: string;
  status: 'todo' | 'in_progress' | 'done' | 'blocked';  // flowctl TASK_STATUS
  depends_on: string[];
  spec_path: string;
}

interface Run {
  id: string;          // YYYY-MM-DD-NNN
  path: string;        // full path to run dir
  epic?: string;
  active: boolean;
  iteration: number;
}

interface LogEntry {
  type: 'tool' | 'response' | 'error';
  tool?: string;       // Read, Write, Bash, etc.
  content: string;
  success?: boolean;
}

type TaskStatus = Task['status'];
type RunState = 'running' | 'complete' | 'crashed';
```

### Matching flowctl JSON output

Types should match structure from `flowctl --json` commands.

### Test fixtures

Create `test/fixtures/` with sample JSON:
- `epic.json` - sample epic from `flowctl show fn-9 --json`
- `task.json` - sample task from `flowctl show fn-9.1 --json`
- `tasks.json` - sample tasks from `flowctl tasks --epic fn-9 --json`
- `ready.json` - sample from `flowctl ready --epic fn-9 --json`

Use fixtures in tests to validate type compatibility.
## Acceptance
- [ ] All types exportable from `./lib/types`
- [ ] Types match flowctl JSON output structure
- [ ] Test fixtures in `test/fixtures/` validate types
- [ ] No `any` types
- [ ] TypeScript compiles without errors
## Done summary
- Added complete TypeScript types matching flowctl JSON output
- Created Epic, Task, Run, LogEntry, ReadyResponse interfaces
- Added test fixtures from actual flowctl output (epic.json, task.json, ready.json)
- Tests validate type compatibility

Why:
- TUI needs typed parsing of flowctl commands
- Fixtures enable testing without live flowctl

Verification:
- bun test passes (4 tests)
- bun run lint passes (0 warnings)
- bunx tsc --noEmit passes
## Evidence
- Commits: 2a78dc25c8c99da4c44f83ce1cb6b2d9dfffd829
- Tests: bun test, bun run lint, bunx tsc --noEmit
- PRs: