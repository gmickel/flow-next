# fn-9.3 Types and interfaces

## Description

Define TypeScript types/interfaces for all data structures.

### File

`src/lib/types.ts`

### Types needed

```typescript
interface Epic {
  id: string;          // fn-N
  title: string;
  status: 'open' | 'closed';
  branch_name: string;
  spec_path: string;
}

interface Task {
  id: string;          // fn-N.M
  epic: string;
  title: string;
  status: 'pending' | 'in_progress' | 'done' | 'blocked';
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
- `epic.json` - sample epic from `flowctl show fn-1 --json`
- `tasks.json` - sample tasks from `flowctl tasks --epic fn-1 --json`
- `ready.json` - sample from `flowctl ready --epic fn-1 --json`

Use fixtures in tests to validate type compatibility.
## Acceptance
- [ ] All types exportable from `./lib/types`
- [ ] Types match flowctl JSON output structure
- [ ] Test fixtures in `test/fixtures/` validate types
- [ ] No `any` types
- [ ] TypeScript compiles without errors
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
