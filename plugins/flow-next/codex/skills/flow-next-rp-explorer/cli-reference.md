# RepoPrompt CE CLI Command Reference

> Requires RepoPrompt CE 1.1.0+ and `rpce-cli`.

## Basic Usage

```bash
rpce-cli -e '<command>' # Run single command
rpce-cli -e '<cmd1> && <cmd2>' # Chain commands
rpce-cli -w <id> -e '<command>' # Target specific window
rpce-cli -w <id> -t <tab> -e '<cmd>' # Target window + tab (CE 1.1.0+)
```

## Core Commands

| Command | Aliases | Purpose |
|---------|---------|---------|
| `tree` | - | File/folder tree |
| `structure` | `map` | Code signatures (token-efficient) |
| `search` | `grep` | Search with context |
| `read` | `cat` | Read file contents |
| `select` | `sel` | Manage file selection |
| `context` | `ctx` | Export workspace context |
| `builder` | - | AI-powered file selection |
| `chat` | - | Send to AI chat |

## File Tree

```bash
rpce-cli -e 'tree' # Full tree
rpce-cli -e 'tree --folders' # Folders only
rpce-cli -e 'tree --mode selected' # Selected files only
```

## Code Structure (TOKEN EFFICIENT)

```bash
rpce-cli -e 'structure src/' # Signatures for path
rpce-cli -e 'structure .' # Whole project
rpce-cli -e 'structure --scope selected' # Selected files only
```

## Search

```bash
rpce-cli -e 'search "pattern"'
rpce-cli -e 'search "TODO" --extensions .ts,.tsx'
rpce-cli -e 'search "error" --context-lines 3'
rpce-cli -e 'search "function" --max-results 20'
```

## Read Files

```bash
rpce-cli -e 'read path/to/file.ts'
rpce-cli -e 'read file.ts --start-line 50 --limit 30' # Slice
rpce-cli -e 'read file.ts --start-line -20' # Last 20 lines
```

## Selection Management

```bash
rpce-cli -e 'select add src/' # Add to selection
rpce-cli -e 'select set src/ lib/' # Replace selection
rpce-cli -e 'select clear' # Clear selection
rpce-cli -e 'select get' # View selection
```

## Context Export

```bash
rpce-cli -e 'context' # Full context
rpce-cli -e 'context --include prompt,selection,tree'
rpce-cli -e 'context --all > output.md' # Export to file
```

## Prompt Export

```bash
# Export full context (files, tree, codemaps) to markdown file
rpce-cli -e 'prompt export /path/to/output.md'
```

## AI-Powered Builder

```bash
rpce-cli -e 'builder "understand auth system"'
rpce-cli -e 'builder "find API endpoints" --response-type plan'
```

## Chat

```bash
rpce-cli -e 'chat "How does auth work?"'
rpce-cli -e 'plan "Design new feature"'
rpce-cli -e 'chat "Start fresh discussion" --new' # New chat
```

Note: Chats are bound to compose tabs. Use `workspace tab` to bind to a specific tab before chatting.

## Workspaces & Tabs

```bash
rpce-cli -e 'workspace list' # List workspaces
rpce-cli -e 'workspace switch "Name"' # Switch workspace
rpce-cli -e 'tabs list' # List tabs
rpce-cli -t "TabName" -e 'context' # Bind to tab (for chat isolation)
```

## Workflow Shorthand Flags

```bash
# Quick one-liner workflows
rpce-cli --workspace MyProject --select-set src/ --export-context ~/out.json
rpce-cli --workspace MyProject --select-set src/ --export-prompt ~/context.md
rpce-cli --chat "How does auth work?"
rpce-cli --builder "implement user authentication"
```

## Script Files (.rp)

Save repeatable workflows:

```bash
# export.rp
workspace switch MyProject
select set src/
context --all > output.md
```

Run with: `rpce-cli --exec-file ~/scripts/export.rp`

## Tab Isolation

`builder` creates an isolated compose tab automatically. Use `-t` to target it directly:
```bash
# Builder returns: Tab: <UUID> • <Name>
# Target that tab for follow-up commands:
rpce-cli -w W -t "<UUID or Name>" -e 'select get'
rpce-cli -w W -t "<UUID or Name>" -e 'chat "review"'

# Or chain commands to stay in same tab:
rpce-cli -w W -e 'builder "..." && select add file.ts && chat "review"'
```

## Notes

- Requires RepoPrompt CE 1.1.0+ with its MCP server enabled
- Use `rpce-cli -d <cmd>` for detailed help on any command
- Token-efficient: `structure` gives signatures without full content
- Progress notifications show during builder/chat execution
