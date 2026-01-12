# fn-9.2 Theme system (dark/light)

## Description

Create theme system with dark (default) and light variants.

### Files

- `src/themes/index.ts` - exports, theme switching
- `src/themes/dark.ts` - dark palette
- `src/themes/light.ts` - light palette

### Color palette (256 colors)

Dark theme from spec:
```typescript
const DARK = {
  bg: 'terminal default',
  border: 239,
  text: 252,
  dim: 242,
  accent: 81,     // electric cyan
  success: 114,   // muted green
  progress: 75,   // bright blue
  warning: 221,   // amber
  error: 203,     // coral red
  selectedBg: 236
};
```

### Theme objects needed

- `TaskListTheme` - for SelectList wrapping
- `MarkdownTheme` - for task detail
- Color functions: `text()`, `dim()`, `accent()`, etc.

### Switching

Export `getTheme(isLight: boolean)` function.
## Acceptance
- [ ] `import { getTheme, DARK, LIGHT } from './themes'` works
- [ ] Theme has all required colors from spec
- [ ] pi-tui compatible theme objects exportable
- [ ] Colors render correctly in terminal (visual check)
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
