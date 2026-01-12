# fn-9.8 TaskList component

## Description

Create TaskList component wrapping pi-tui SelectList with custom styling.

### File

`src/components/task-list.ts`

### Features

- Status icons: ● done, ◉ in_progress, ○ pending, ⊘ blocked
- Task ID + truncated title
- Blocked tasks show dependency: `→ 1.3`
- Selected row background highlight
- j/k navigation

### Interface

```typescript
interface TaskListProps {
  tasks: Task[];
  selectedIndex: number;
  onSelect: (task: Task) => void;
  theme: Theme;
}

class TaskList implements Component {
  render(width: number): string[]
  handleInput(data: string): void
  invalidate(): void
}
```

### Rendering

For each task:
```
◉ fn-1.3 Add validation...
⊘ fn-1.4 Fix bug → 1.3
```

Use theme colors for status icons.
## Acceptance
- [ ] Status icons render with correct colors
- [ ] j/k changes selection
- [ ] Selected row has background highlight
- [ ] Blocked tasks show dependency indicator
- [ ] Long titles truncated with ellipsis
- [ ] onSelect callback fires on Enter
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
