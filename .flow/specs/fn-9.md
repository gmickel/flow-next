# flow-next-tui MVP

Terminal UI for flow-next Ralph mode. Real-time visibility into autonomous agent runs.

## Overview

Wrapper around `ralph.sh` and `flowctl` providing rich terminal interface for monitoring. Log-based monitoring model - reads logs and polls flowctl, no process attachment required.

## Scope

**In scope:**
- Two-row header (status, task, timer, epic info)
- Task list with status icons (●/◉/○/⊘)
- Task detail with markdown + receipt status
- Output panel streaming iter-*.log
- Keyboard nav (j/k/q/?)
- Dark + light themes, --no-emoji ASCII mode
- Run management (auto-select latest, spawn ralph)
- Help overlay
- Auto-compact mode for small terminals (< 120x30)
- Ralph spawning and detach behavior

**Out of scope:**
- Multi-run tabs (v0.2)
- Search overlay (v0.2)
- ETA calculation (v0.2)

## Tech Stack

- **pi-tui** (@mariozechner/pi-tui) - differential rendering TUI
- **Bun** - runtime, bundler
- **oxlint + oxfmt** - linting (ultracite config)
- **npm** - publish as @gmickel/flow-next-tui (source, requires Bun)

## Architecture

```
src/
├── index.ts              # CLI entry (commander)
├── app.ts                # Main TUI, state, render
├── components/
│   ├── header.ts         # Two-row header
│   ├── task-list.ts      # Wraps SelectList
│   ├── task-detail.ts    # Markdown + receipts
│   ├── output.ts         # Streaming output
│   ├── status-bar.ts     # Bottom bar
│   ├── split-panel.ts    # Horizontal layout
│   └── help-overlay.ts   # ? help
├── lib/
│   ├── flowctl.ts        # Spawn helpers (path resolution)
│   ├── runs.ts           # Run discovery, receipts, blocks
│   ├── spawn.ts          # Ralph spawning + detach
│   ├── log-watcher.ts    # Watch iter-*.log
│   ├── parser.ts         # stream-json parser
│   ├── render.ts         # ANSI-aware utilities
│   └── types.ts          # Task, Epic, Run
└── themes/
    ├── index.ts
    ├── dark.ts
    └── light.ts
```

## Key Design Decisions

1. **Log-based monitoring** - TUI reads logs/polls flowctl, doesn't attach to process
2. **Custom SplitPanel** - pi-tui only has vertical Container, must build horizontal split
3. **Active run detection** - Check progress.txt for COMPLETE marker
4. **flowctl location** - Search: .flow/bin → plugins/flow-next/scripts → PATH
5. **Packaging** - Publish TS source with `#!/usr/bin/env bun` shebang, requires Bun (macOS/Linux; Windows best-effort)
6. **Render utilities** - Centralized ANSI-aware width/truncation

## Quick Commands

```bash
# Dev
cd flow-next-tui && bun install && bun run dev

# Test
bun test

# Lint
bun run lint

# Build + run
bun run build && bun run start
```

## Acceptance

- [ ] Header shows run state, current task, timer
- [ ] Task list navigable with j/k, shows status icons
- [ ] Detail panel renders markdown specs
- [ ] Output panel streams iter-*.log with tool icons
- [ ] Themes switchable via --light flag
- [ ] --no-emoji switches to ASCII icons
- [ ] Help overlay on ? key
- [ ] Auto-compact on small terminals (< 120x30)
- [ ] Can spawn ralph if no runs exist
- [ ] Ctrl+C detaches without killing ralph
- [ ] Missing requirements show helpful errors

## References

- Full spec: `plans/flow-next-tui-spec.md`
- pi-tui: `/Users/gordon/tmp/pi-mono/packages/tui`
- flowctl: `plugins/flow-next/scripts/flowctl.py`
- ralph.sh: `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh`
