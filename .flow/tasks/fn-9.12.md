# fn-9.12 StatusBar component

## Description

Create StatusBar component for bottom bar with shortcuts and run info.

### File

`src/components/status-bar.ts`

### Layout

```
 q quit  j/k nav  ? help                                  2026-01-12-001
```

Left: keyboard shortcuts
Right: run ID, optional error count

### Interface

```typescript
interface StatusBarProps {
  runId?: string;
  errorCount?: number;
  theme: Theme;
}

class StatusBar implements Component {
  render(width: number): string[]
}
```

Single row, full terminal width.
## Acceptance
- [ ] Shortcuts render on left
- [ ] Run ID renders on right
- [ ] Error count shows if > 0
- [ ] Full width with space between left/right
- [ ] Theme colors applied
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
