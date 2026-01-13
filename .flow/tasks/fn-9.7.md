# fn-9.7 SplitPanel component

## Description

Create SplitPanel component for horizontal layout (pi-tui only has vertical Container).

### File

`src/components/split-panel.ts`

### Interface

```typescript
interface SplitPanelProps {
  left: Component;
  right: Component;
  ratio?: number;        // default 0.3 (30% left)
  separator?: string;    // default '│'
}

class SplitPanel implements Component {
  render(width: number): string[]
  handleInput(data: string): void
  invalidate(): void
}
```

### Implementation

1. Calculate left/right widths from ratio
2. Render both children to their widths
3. Pad shorter panel with empty lines to match height
4. Join lines side-by-side with separator
5. Use `visibleWidth()` for ANSI-aware width calculation

### Reference

```typescript
render(width: number): string[] {
  const leftWidth = Math.floor(width * this.ratio);
  const rightWidth = width - leftWidth - 1;
  const leftLines = this.left.render(leftWidth);
  const rightLines = this.right.render(rightWidth);
  const maxHeight = Math.max(leftLines.length, rightLines.length);
  return Array.from({ length: maxHeight }, (_, i) => {
    const l = padToWidth(leftLines[i] || '', leftWidth);
    const r = rightLines[i] || '';
    return l + '│' + r;
  });
}
```
## Acceptance
- [ ] Renders two components side-by-side
- [ ] Ratio controls width split correctly
- [ ] Separator visible between panels
- [ ] Shorter panel padded to match height
- [ ] ANSI codes don't break width calculation
- [ ] Input forwarded to appropriate child
## Done summary
- Added SplitPanel component for horizontal two-panel layout
- Implements configurable ratio (default 0.3) and separator (default │)
- Handles ANSI codes via visibleWidth/padToWidth from render.ts
- Falls back to left-only when width too small

Tests verify all acceptance criteria:
- Side-by-side rendering, ratio control, separator visibility
- Height padding, ANSI handling, input forwarding
## Evidence
- Commits: 8073ab1d1378824ab736cc4ae74c5645280f24d0
- Tests: bun test
- PRs: