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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
