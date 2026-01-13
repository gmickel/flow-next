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
- Created StatusBar component with shortcuts on left, run ID + error count on right
- Handles truncation at narrow widths gracefully
- 18 tests covering rendering, width constraints, and updates
## Evidence
- Commits: c762230c61f55d475b6db57bedb18fcd3de91f29
- Tests: bun test src/components/status-bar.test.ts
- PRs: