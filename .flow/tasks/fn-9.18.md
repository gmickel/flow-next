# fn-9.18 Render utilities (ANSI-aware)

## Description
ANSI-aware rendering utilities for terminal width/padding/truncation.

### File

`src/lib/render.ts`

### Functions

```typescript
// Get visible width ignoring ANSI codes
function visibleWidth(text: string): number

// Pad text to exact width (handles ANSI)
function padToWidth(text: string, width: number): string

// Truncate with ellipsis preserving ANSI reset
function truncateToWidth(text: string, width: number, ellipsis?: string): string

// Strip all ANSI codes
function stripAnsi(text: string): string
```

### pi-tui utilities

Check if pi-tui exports these (it likely does). If so, re-export.
If not, implement using ANSI regex patterns.

### Testing

Unit tests for each function with:
- Plain text
- Text with color codes
- Text with nested styles
- Edge cases (empty, exact width, over width)
## Acceptance
- [ ] `visibleWidth()` ignores ANSI escape codes
- [ ] `padToWidth()` pads to exact visible width
- [ ] `truncateToWidth()` adds ellipsis at visible width
- [ ] All functions handle empty strings
- [ ] Unit tests pass for plain and styled text
## Done summary
- Added src/lib/render.ts with ANSI-aware utilities
- Re-exported visibleWidth/truncateToWidth from pi-tui
- Implemented padToWidth and stripAnsi locally
- Full test coverage for plain/styled/edge cases
## Evidence
- Commits: 2f4dcd0748500a6e861249674987a8f2fad72c31
- Tests: bun test src/lib/render.test.ts
- PRs: