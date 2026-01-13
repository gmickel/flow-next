# flow-next-tui

Terminal UI for flow-next Ralph mode. Real-time visibility into autonomous agent runs.

## Quick Commands

```bash
bun install          # Install deps
bun test             # Run tests
bun run dev          # Run TUI (dev)
bun run lint         # oxlint type-aware
bunx ultracite fix   # Format code
```

## Architecture

```
src/
├── index.ts              # CLI entry (commander)
├── app.ts                # Main TUI, state, render loop
├── components/
│   ├── header.ts         # Two-row header (status, task, timer)
│   ├── task-list.ts      # Wraps pi-tui SelectList with status icons
│   ├── task-detail.ts    # Markdown spec + receipt status
│   ├── output.ts         # Streaming iter-*.log with tool icons
│   ├── status-bar.ts     # Bottom bar (help hints)
│   ├── split-panel.ts    # Horizontal layout (pi-tui is vertical-only)
│   └── help-overlay.ts   # ? key overlay
├── lib/
│   ├── flowctl.ts        # flowctl spawn + JSON parsing (DONE)
│   ├── runs.ts           # Run discovery, receipts, blocks (DONE)
│   ├── spawn.ts          # Ralph spawning + detach
│   ├── log-watcher.ts    # Watch iter-*.log files
│   ├── render.ts         # ANSI-aware width/truncation utils
│   └── types.ts          # Task, Epic, Run, LogEntry types (DONE)
└── themes/
    ├── index.ts          # Theme exports + getTheme() (DONE)
    ├── dark.ts           # Dark palette + pi-tui themes (DONE)
    └── light.ts          # Light palette (DONE)
```

## Tech Stack

- **Bun** - runtime, bundler, test runner
- **pi-tui** (@mariozechner/pi-tui) - differential rendering TUI framework
- **oxlint + oxfmt** - linting via ultracite preset
- **commander** - CLI argument parsing

## Key Patterns

### Bun APIs (prefer over Node)

```typescript
// File operations
const file = Bun.file(path);
if (await file.exists()) {
  const content = await file.text();
  const json = await file.json();
}

// Process spawning
const proc = Bun.spawn(['flowctl', 'show', id], {
  stdout: 'pipe',
  stderr: 'pipe',
});
const text = await new Response(proc.stdout).text();
await proc.exited;

// Use node:fs/promises only for readdir, stat (Bun.file is files only)
import { readdir, stat } from 'node:fs/promises';
```

### Error Handling

```typescript
// Custom error classes with structured info
export class FlowctlError extends Error {
  kind: 'exec' | 'parse' | 'api';
  exitCode: number;
  output: string;
}

// Throw on API failures (success: false)
if (!response.success) {
  throw new FlowctlError(cmd, args, 0, response.error ?? 'Unknown', 'api');
}
```

### Path Traversal Protection

```typescript
// Validate IDs before path operations
const TASK_ID_PATTERN = /^fn-\d+(?:\.\d+)?$/;
const RUN_ID_PATTERN = /^[\w-]+$/;

function validateTaskId(taskId: string): void {
  if (!TASK_ID_PATTERN.test(taskId)) {
    throw new Error(`Invalid task ID: ${taskId}`);
  }
}
```

### Testing

```typescript
import { describe, test, expect, beforeEach, afterEach } from 'bun:test';
import { mkdtemp, rm } from 'node:fs/promises';

describe('module', () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'test-'));
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true });
  });

  test('does thing', async () => {
    // Use tempDir for isolated tests
  });
});
```

### Theme System

```typescript
import { getTheme, type Theme } from './themes';

const theme = getTheme(options.light); // false = dark (default)
console.log(theme.accent('highlighted'));
console.log(theme.dim('muted text'));

// pi-tui components use theme.selectList, theme.markdown, theme.editor
```

## pi-tui Reference

Components we use:

- `SelectList` - keyboard-navigable list
- `Markdown` - spec rendering with theming
- `Box` - padding/background wrapper
- `TruncatedText` - ANSI-aware single-line truncation
- `Container` - vertical stacking
- `TUI` - main app with differential rendering

Utilities:

- `visibleWidth()` - terminal column width (ANSI-aware)
- `truncateToWidth()` - truncate with ellipsis
- `wrapTextWithAnsi()` - word wrap preserving ANSI
- `applyBackgroundToLine()` - bg color with padding

Local reference: `/Users/gordon/tmp/pi-mono/packages/tui`

## Design Language

Industrial/utilitarian with electric cyan accent. 256-color palette.

Status icons: `●` done, `◉` in_progress, `○` todo, `⊘` blocked
ASCII mode (--no-emoji): `[x]`, `[>]`, `[ ]`, `[!]`

## References

- Epic spec: `.flow/specs/fn-9.md` or `flowctl cat fn-9`
- Full spec: `plans/flow-next-tui-spec.md`
- flowctl: `plugins/flow-next/scripts/flowctl.py`
- ralph.sh: `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh`
