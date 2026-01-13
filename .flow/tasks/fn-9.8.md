# fn-9.8 TaskList component

## Description

Create TaskList component implementing navigable task list with status icons.
Uses pi-tui Component interface with custom rendering (not wrapping SelectList
due to different rendering requirements: status icons, blocked indicators, etc.)

### File

`src/components/task-list.ts`

### Features

- Status icons: ● done, ◉ in_progress, ○ todo, ⊘ blocked
- Full task ID (fn-N.M) + truncated title
- Blocked tasks (status: blocked) show dependency indicator: `→ 1.3`
- Selected row background highlight (manual bg+fg per segment to preserve status colors)
- j/k and arrow navigation with wrap-around
- Scroll indicator when tasks exceed maxVisible

### Interface

```typescript
interface TaskListProps {
  tasks: EpicTask[];
  selectedIndex: number;
  onSelect: (task: EpicTask) => void;
  theme: Theme;
  // Optional extensions
  onSelectionChange?: (task: EpicTask, index: number) => void;
  maxVisible?: number;  // default: 10
  useAscii?: boolean;   // default: false
}

class TaskList implements Component {
  render(width: number): string[]
  handleInput(data: string): void
  invalidate(): void
  // Helpers
  setTasks(tasks: EpicTask[]): void
  getSelectedTask(): EpicTask | undefined
  getSelectedIndex(): number
  setSelectedIndex(index: number): void
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
- Added TaskList component with status icons (●/◉/○/⊘)
- Implemented j/k and arrow navigation with wrap-around
- Added selected row background highlight

- Matches pi-tui Component interface for integration
- ASCII mode (--no-emoji) support included

- 44 tests passing
- Lint clean
## Evidence
- Commits: 83ac1bc75db3c7e8d5979793f1d4be7e1652dde7
- Tests: bun test src/components/task-list.test.ts
- PRs: