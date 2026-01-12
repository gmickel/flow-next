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
- Implemented 256-color palette with dark (default) and light themes
- Added color helper functions: text(), dim(), accent(), success(), progress(), warning(), error(), border()
- Created pi-tui compatible theme objects: SelectListTheme, MarkdownTheme, EditorTheme
- Added getTheme(isLight) switching function

Why:
- Terminal TUI needs consistent theming across all components
- 256-color palette ensures compatibility with most terminals

Verification:
- bun test passes (14 tests)
- bun run lint passes
- TypeScript check passes
## Evidence
- Commits: 55d8d24, 70e05a1
- Tests: bun test
- PRs: