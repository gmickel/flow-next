# fn-9.15 CLI entry point

## Description

Create CLI entry point with argument parsing.

### File

`src/index.ts`

### CLI options

```
flow-next-tui [options]

Options:
  --light              Use light theme
  --no-emoji           Use ASCII icons instead of unicode
  --run <id>           Select specific run
  -h, --help           Show help
  -v, --version        Show version
```

### --no-emoji behavior

Replaces unicode icons with ASCII equivalents:
- Status: `●` → `[x]`, `◉` → `[>]`, `○` → `[ ]`, `⊘` → `[!]`
- Tools: `→` → `>`, `⚡` → `$`, `◆` → `*`
- Header: `▸` → `>`, `⏸` → `||`, `✓` → `ok`

Propagate via `RenderOptions.useAscii` to all components.

### Implementation

Use commander for parsing.

### Shebang

First line of `src/index.ts`:
```typescript
#!/usr/bin/env bun
```

Required for global npm installs to work.

### Entry flow

1. Parse args
2. Create App with options
3. Start TUI render loop
4. Handle SIGINT/SIGTERM for cleanup
## Acceptance
- [ ] `bun run src/index.ts --help` shows usage
- [ ] `--light` switches to light theme
- [ ] `--run <id>` selects specific run
- [ ] `--no-emoji` switches to ASCII icons throughout
- [ ] `--version` shows package version
- [ ] Ctrl+C exits cleanly
- [ ] Shebang present: `#!/usr/bin/env bun`
## Done summary
- Wired index.ts to createApp() with options mapping
- Added --run <id> option (was positional, now proper option per spec)
- Added signal handlers before parseAsync
- Verified: --help, --version, shebang all work
- Tests pass (386), lint clean
## Evidence
- Commits: 5b8b6cde99931c6c4fadc5f1d3826c9270f18867
- Tests: bun test
- PRs: