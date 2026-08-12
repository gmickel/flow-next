# Session Management

Multiple isolated browser sessions with state persistence and concurrent browsing.

## Named Sessions

Use `--session` flag to isolate browser contexts:

```bash
agent-browser --session auth open https://app.example.com/login
agent-browser --session public open https://example.com

# Commands isolated by session
agent-browser --session auth fill @e1 "user@example.com"
agent-browser --session public get text body
```

## Session Isolation Properties

Each session has independent: cookies, localStorage, sessionStorage, IndexedDB, cache, browsing history, open tabs.

## Session State Persistence

### Auto-Persistence with --session-name

```bash
# Auto-save/restore cookies and localStorage across browser restarts
agent-browser --session-name myapp open https://app.example.com/login
# ... login flow ...
agent-browser close  # State auto-saved to ~/.agent-browser/sessions/

# Next time: state auto-loaded
agent-browser --session-name myapp open https://app.example.com/dashboard
```

### Encrypted State

```bash
export AGENT_BROWSER_ENCRYPTION_KEY=$(openssl rand -hex 32)
agent-browser --session-name secure open https://app.example.com
```

### Manual State Management

```bash
agent-browser state save auth.json     # Save cookies, storage, auth state
agent-browser state load auth.json     # Restore saved state
agent-browser state list               # List saved states
agent-browser state show name.json     # Show state contents
agent-browser state clear name         # Clear saved state
agent-browser state clean --older-than 7  # Clean old states
```

## Common Patterns

### Authenticated Session Reuse

```bash
STATE_FILE="/tmp/auth-state.json"

if [[ -f "$STATE_FILE" ]]; then
    agent-browser state load "$STATE_FILE"
    agent-browser open https://app.example.com/dashboard
else
    agent-browser open https://app.example.com/login
    agent-browser snapshot -i
    agent-browser fill @e1 "$USERNAME"
    agent-browser fill @e2 "$PASSWORD"
    agent-browser click @e3
    agent-browser wait --load networkidle
    agent-browser state save "$STATE_FILE"
fi
```

### Concurrent Scraping

```bash
# Start all sessions
agent-browser --session site1 open https://site1.com &
agent-browser --session site2 open https://site2.com &
agent-browser --session site3 open https://site3.com &
wait

# Extract from each
agent-browser --session site1 get text body > site1.txt
agent-browser --session site2 get text body > site2.txt
agent-browser --session site3 get text body > site3.txt

# Cleanup
agent-browser --session site1 close
agent-browser --session site2 close
agent-browser --session site3 close
```

### A/B Testing

```bash
agent-browser --session variant-a open "https://app.com?variant=a"
agent-browser --session variant-b open "https://app.com?variant=b"
agent-browser --session variant-a screenshot /tmp/variant-a.png
agent-browser --session variant-b screenshot /tmp/variant-b.png
```

## Default Session

When `--session` is omitted, commands use the default session:

```bash
agent-browser open https://example.com
agent-browser snapshot -i
agent-browser close  # Closes default session
```

## Session Cleanup

```bash
agent-browser --session auth close     # Close specific session
agent-browser session list             # List active sessions
agent-browser close                    # Close default session
```

Always close sessions when done to avoid leaked processes. If a previous session wasn't closed properly, `agent-browser close` cleans it up.

## Best Practices

1. **Name sessions semantically**: `--session github-auth` not `--session s1`
2. **Always close when done**: Avoid leaked browser processes
3. **Secure state files**: Don't commit (contain auth tokens), add to `.gitignore`
4. **Use encryption**: Set `AGENT_BROWSER_ENCRYPTION_KEY` for sensitive state
5. **Timeout long sessions**: `timeout 60 agent-browser --session long-task get text body`
