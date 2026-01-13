# fn-9.9 TaskDetail component

## Description

Create TaskDetail component showing full task info with markdown rendering.

### File

`src/components/task-detail.ts`

### Features

- Task type icon + full title
- Metadata line: ID, status
- Receipt status: "Plan ✓  Impl ✓" or "Plan ✗  Impl -"
- Markdown spec content via pi-tui Markdown
- Blocked reason from block-fn-X.md if applicable

### Interface

```typescript
interface TaskDetailProps {
  task: Task;
  spec: string;           // markdown content
  receipts?: {plan?: boolean, impl?: boolean};
  blockReason?: string;
  theme: Theme;
}

class TaskDetail implements Component {
  render(width: number): string[]
  handleInput(data: string): void  // scrolling
  invalidate(): void
}
```

### Layout

```
◉ Add form validation with Zod
ID: fn-1.3  Status: in_progress
Plan ✓  Impl ✓

## User Story
As a user I want validation...
```
## Acceptance
- [ ] Header shows status icon + full title
- [ ] Metadata line shows ID and status
- [ ] Receipt indicators render correctly
- [ ] Markdown content renders via pi-tui
- [ ] Blocked tasks show block reason
- [ ] Scrollable if content exceeds height
## Done summary
- Added TaskDetail component with full task info display
- Header: status icon + title, metadata line (ID/status), receipt indicators
- Markdown spec rendering via pi-tui Markdown component
- Block reason display for blocked tasks
- j/k/g/G scroll navigation with arrow key support

Why:
- Component needed for right panel in TUI split view
- Shows detailed task spec when task selected in list

Verification:
- 29 unit tests pass
- All 248 tests pass
- Lint passes (0 errors)
## Evidence
- Commits: 6a597aa3c8d438153e33184ac67bbfa8f4791242
- Tests: bun test
- PRs: