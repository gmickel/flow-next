# fn-9.13 HelpOverlay component

## Description

Create HelpOverlay component showing keybindings.

### File

`src/components/help-overlay.ts`

### Features

- Modal overlay on ? key
- Lists all keyboard shortcuts
- Dismiss with Esc or ?

### Interface

```typescript
class HelpOverlay implements Component {
  render(width: number): string[]
  handleInput(data: string): void
}
```

### Content

```
┌─ Help ─────────────────────────────┐
│                                     │
│  j/k      Navigate task list        │
│  ?        Show/hide this help       │
│  q        Quit (detach if running)  │
│  Esc      Close overlay             │
│  Ctrl+C   Same as q                 │
│                                     │
│         Press ? or Esc to close     │
└─────────────────────────────────────┘
```

Use pi-tui overlay system if available, or render centered box.
## Acceptance
- [ ] Overlay renders centered
- [ ] All keybindings listed
- [ ] Esc dismisses overlay
- [ ] ? toggles overlay
- [ ] Theme colors applied
## Done summary
- Added HelpOverlay component with keybinding list
- Centered modal box, toggles on ? key
- Esc or ? dismisses overlay
- 26 tests covering visibility, input, centering
## Evidence
- Commits: 8ddf481
- Tests: bun test src/components/help-overlay.test.ts
- PRs: