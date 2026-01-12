# fn-9.10 OutputPanel component

## Description

Create OutputPanel component for streaming log output with auto-scroll.

### File

`src/components/output.ts`

### Features

- Bordered with "─Iteration N─" header
- Tool icons by type
- Auto-scroll to bottom (unless user scrolled up)
- 500 line buffer (configurable)
- Scroll with arrow keys

### Interface

```typescript
interface OutputPanelProps {
  buffer: LogEntry[];
  iteration: number;
  theme: Theme;
  maxBuffer?: number;     // default 500
}

class OutputPanel implements Component {
  appendLine(entry: LogEntry): void
  render(width: number): string[]
  handleInput(data: string): void
  invalidate(): void
}
```

### Auto-scroll detection

Track if user scrolled up manually. Reset when at bottom.

### Tool icons

- `→` file ops (Read/Write/Glob)
- `⚡` bash
- `◆` API calls
- `✓` success (green)
- `✗` failure (red)
## Acceptance
- [ ] Border renders with iteration number
- [ ] Tool icons show by type
- [ ] Auto-scrolls when new lines added
- [ ] User scroll up disables auto-scroll
- [ ] Scrolling to bottom re-enables auto-scroll
- [ ] Buffer limited to maxBuffer lines
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
