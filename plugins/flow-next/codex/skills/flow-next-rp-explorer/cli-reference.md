# rp-cli Command Reference

> Requires RepoPrompt v1.5.62+

## Basic Usage

```bash
rp-cli -e '<command>'                  # Run single command
rp-cli -e '<cmd1> && <cmd2>'           # Chain commands
rp-cli -w <id> -e '<command>'          # Target specific window
rp-cli -w <id> -t <tab> -e '<cmd>'     # Target window + tab (v1.5.62+)
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
rp-cli -e 'tree'                    # Full tree
rp-cli -e 'tree --folders'          # Folders only
rp-cli -e 'tree --mode selected'    # Selected files only
```

## Code Structure (TOKEN EFFICIENT)

```bash
rp-cli -e 'structure src/'          # Signatures for path
rp-cli -e 'structure .'             # Whole project
rp-cli -e 'structure --scope selected'  # Selected files only
```

## Search

```bash
rp-cli -e 'search "pattern"'
rp-cli -e 'search "TODO" --extensions .ts,.tsx'
rp-cli -e 'search "error" --context-lines 3'
rp-cli -e 'search "function" --max-results 20'
```

## Read Files

```bash
rp-cli -e 'read path/to/file.ts'
rp-cli -e 'read file.ts --start-line 50 --limit 30'  # Slice
rp-cli -e 'read file.ts --start-line -20'            # Last 20 lines
```

## Selection Management

```bash
rp-cli -e 'select add src/'         # Add to selection
rp-cli -e 'select set src/ lib/'    # Replace selection
rp-cli -e 'select clear'            # Clear selection
rp-cli -e 'select get'              # View selection
```

## Context Export

```bash
rp-cli -e 'context'                 # Full context
rp-cli -e 'context --include prompt,selection,tree'
rp-cli -e 'context --all > output.md'  # Export to file
```

## Prompt Export (v1.5.61+)

```bash
# Export full context (files, tree, codemaps) to markdown file
rp-cli -e 'prompt export /path/to/output.md'
```

## AI-Powered Builder

```bash
rp-cli -e 'builder "understand auth system"'
rp-cli -e 'builder "find API endpoints" --type plan'
```

## Chat

```bash
rp-cli -e 'chat "How does auth work?"'
rp-cli -e 'chat "Design new feature" --mode plan'
rp-cli -e 'newchat "Start fresh discussion"'  # New chat
```

Note: Chats are bound to compose tabs. Use `workspace tab` to bind to a specific tab before chatting.

## Workspaces & Tabs

```bash
rp-cli -e 'workspace list'          # List workspaces
rp-cli -e 'workspace switch "Name"' # Switch workspace
rp-cli -e 'workspace tabs'          # List tabs
rp-cli -e 'workspace tab "TabName"' # Bind to tab (for chat isolation)
```

## Workflow Shorthand Flags

```bash
# Quick one-liner workflows
rp-cli --workspace MyProject --select-set src/ --export-context ~/out.json
rp-cli --workspace MyProject --select-set src/ --export-prompt ~/context.md
rp-cli --chat "How does auth work?"
rp-cli --builder "implement user authentication"
```

## Script Files (.rp)

Save repeatable workflows:

```bash
# export.rp
workspace switch MyProject
select set src/
context --all > output.md
```

Run with: `rp-cli --exec-file ~/scripts/export.rp`

## Tab Isolation

`builder` creates an isolated compose tab automatically. Use `-t` to target it directly:
```bash
# Builder returns: Tab: <UUID> • <Name>
# Target that tab for follow-up commands:
rp-cli -w W -t "<UUID or Name>" -e 'select get'
rp-cli -w W -t "<UUID or Name>" -e 'chat "review" --mode chat'

# Or chain commands to stay in same tab:
rp-cli -w W -e 'builder "..." && select add file.ts && chat "review"'
```

## Notes

- Requires RepoPrompt v1.5.62+ with MCP Server enabled
- Use `rp-cli -d <cmd>` for detailed help on any command
- Token-efficient: `structure` gives signatures without full content
- Progress notifications show during builder/chat execution
