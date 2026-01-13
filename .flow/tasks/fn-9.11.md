# fn-9.11 Header component

## Description

Create Header component with two-row layout.

### File

`src/components/header.ts`

### Layout

Row 1:
- Status icon (▸ running, ⏸ idle, ✓ done)
- "flow-next" branding (left)
- Current task ID + title in 「brackets」(right, truncated)
- Timer MM:SS (far right)

Row 2:
- Iteration number + progress (e.g., "Iter #3 · 3/7 tasks")
- Epic ID and title (truncated)

### Interface

```typescript
interface HeaderProps {
  state: 'running' | 'idle' | 'complete';
  task?: Task;
  epic?: Epic;
  iteration: number;
  taskProgress: {done: number, total: number};
  elapsed: number;        // seconds
  theme: Theme;
}

class Header implements Component {
  render(width: number): string[]
}
```

### Timer

Update via external interval, format as MM:SS.
## Acceptance
- [ ] Two rows render correctly
- [ ] Status icon matches state
- [ ] Task title truncated when needed
- [ ] Timer shows MM:SS format
- [ ] Progress shows X/Y tasks format
- [ ] Epic title truncated when needed
## Done summary
- Added Header component with two-row layout per spec
- Row 1: status icon + branding, task in brackets, timer MM:SS
- Row 2: iteration + progress, epic ID + title
- Supports ASCII icons via useAscii prop
- All tests (21) pass
## Evidence
- Commits: 4c9b9d7aa2091e5609652c2f0e7e7a364c222b28
- Tests: bun test src/components/header.test.ts
- PRs: