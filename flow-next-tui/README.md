# flow-next-tui

Terminal UI for monitoring [Flow-Next](https://github.com/gmickel/gmickel-claude-marketplace/tree/main/plugins/flow-next) Ralph autonomous agent runs.

**Flow-Next** is a Claude Code plugin for structured task planning and execution. **Ralph** is its autonomous mode - an external loop that runs Claude overnight, completing epics task-by-task with multi-model review gates.

This TUI provides real-time visibility into Ralph runs: task progress, streaming logs, and run state.

## Features

- **Task Progress** - Visual task list with status icons (done/in-progress/todo/blocked)
- **Live Logs** - Streaming output from Ralph iterations with tool icons
- **Task Details** - Markdown spec rendering and receipt status
- **Multi-Epic Support** - Monitors all open epics aggregated
- **Themes** - Dark (default) and light themes with 256-color palette
- **ASCII Mode** - `--no-emoji` for compatibility with limited fonts

## Requirements

- **Bun** - Runtime (macOS/Linux; Windows untested)
- **flow-next** - `.flow/` directory with epics/tasks
- **Ralph** - `scripts/ralph/` scaffolded via `/flow-next:ralph-init`

## Installation

```bash
# From npm (requires Bun runtime)
bun add -g @gmickel/flow-next-tui

# Or run directly
bunx @gmickel/flow-next-tui
```

## Usage

```bash
# Start TUI (auto-selects latest run)
flow-next-tui

# Or use short alias
fntui

# With options
flow-next-tui --light          # Light theme
flow-next-tui --no-emoji       # ASCII icons
flow-next-tui --run <id>       # Select specific run
flow-next-tui -v               # Show version
```

## Keyboard Shortcuts

### Navigation

| Key       | Action        |
| --------- | ------------- |
| `j` / `↓` | Next task     |
| `k` / `↑` | Previous task |

### Output Panel

| Key                | Action         |
| ------------------ | -------------- |
| `g`                | Jump to top    |
| `G`                | Jump to bottom |
| `Space` / `Ctrl+D` | Page down      |
| `Ctrl+U`           | Page up        |

### General

| Key            | Action                 |
| -------------- | ---------------------- |
| `?`            | Toggle help overlay    |
| `Esc`          | Close overlay          |
| `q` / `Ctrl+C` | Quit (detach from run) |

## Layout

```
┌─ flow-next-tui ────────────────────────────────────────────────┐
│ ● RUNNING    fn-9 flow-next-tui MVP         #3    00:05:23     │
│ TaskDetail: fn-9.5 Run discovery lib                           │
├─────────────────────────────────────────────────────────────────┤
│ ┌─ Tasks ──────────┐ ┌─ Detail ────────────────────────────────┐│
│ │ ● fn-9.1 Scaff.. │ │ # fn-9.5 Run discovery lib             ││
│ │ ● fn-9.2 Theme.. │ │                                        ││
│ │ ● fn-9.3 Types.. │ │ ## Description                         ││
│ │ ● fn-9.4 flowc.. │ │ Discover runs in scripts/ralph/runs/   ││
│ │ ◉ fn-9.5 Run d.. │ │ ...                                    ││
│ │ ○ fn-9.6 Log w.. │ │                                        ││
│ └──────────────────┘ └─────────────────────────────────────────┘│
├─ Output ─────────────────────────────────────────────────── #3 ─┤
│ ▸ Read: src/lib/runs.ts                                        │
│ ✓ OK                                                           │
│ $ Bash: bun test src/lib/runs.test.ts                          │
│ ✓ 12 tests passed                                              │
├─────────────────────────────────────────────────────────────────┤
│ j/k navigate │ ? help │ q quit                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Status Icons

| Icon | ASCII | Meaning     |
| ---- | ----- | ----------- |
| `●`  | `[x]` | Done        |
| `◉`  | `[>]` | In Progress |
| `○`  | `[ ]` | Todo        |
| `⊘`  | `[!]` | Blocked     |

## Tool Icons (Output Panel)

| Icon | Tool      |
| ---- | --------- |
| `▸`  | Read      |
| `◂`  | Write     |
| `✎`  | Edit      |
| `$`  | Bash      |
| `◦`  | Glob      |
| `⌕`  | Grep      |
| `◈`  | Task      |
| `⬇`  | WebFetch  |
| `◎`  | WebSearch |
| `✓`  | Success   |
| `✗`  | Failure   |

## Integration with Ralph

The TUI monitors Ralph runs via:

1. **Log files** - Reads `scripts/ralph/runs/<run>/iter-*.log` files
2. **flowctl polling** - Queries task status via `flowctl show`
3. **Receipt files** - Shows review status from `receipts/` directory

### Starting a Run

If no runs exist, the TUI will prompt to spawn Ralph:

```bash
# Manual spawn (TUI will detect it)
cd scripts/ralph && ./ralph.sh
```

### Detaching

`q` or `Ctrl+C` detaches from the TUI without killing Ralph. The run continues in the background.

## Architecture

```
src/
├── index.ts          # CLI entry (commander)
├── app.ts            # Main TUI, state, render
├── components/
│   ├── header.ts     # Status, task, timer
│   ├── task-list.ts  # Navigable task list
│   ├── task-detail.ts # Markdown + receipts
│   ├── output.ts     # Streaming logs
│   ├── status-bar.ts # Bottom hints
│   ├── split-panel.ts # Horizontal layout
│   └── help-overlay.ts # ? modal
├── lib/
│   ├── flowctl.ts    # flowctl integration
│   ├── runs.ts       # Run discovery
│   ├── spawn.ts      # Ralph spawning
│   ├── log-watcher.ts # File watching
│   ├── parser.ts     # stream-json parsing
│   ├── render.ts     # ANSI utilities
│   └── types.ts      # Type definitions
└── themes/
    ├── dark.ts       # Dark palette
    └── light.ts      # Light palette
```

## Development

```bash
cd flow-next-tui

# Install dependencies
bun install

# Run in dev mode
bun run dev

# Run tests
bun test

# Lint
bun run lint
```

## Troubleshooting

### "No .flow/ directory"

Run `flowctl init` or ensure you're in a flow-next project root.

### "No scripts/ralph/"

Run `/flow-next:ralph-init` to scaffold the Ralph harness.

### "flowctl not found"

The TUI searches for flowctl in:

1. `.flow/bin/flowctl`
2. `plugins/flow-next/scripts/flowctl.py`
3. System PATH

### Unicode icons look wrong

Try `--no-emoji` for ASCII fallback, or use a font with good Unicode support (e.g., JetBrains Mono, Fira Code).

## License

MIT
