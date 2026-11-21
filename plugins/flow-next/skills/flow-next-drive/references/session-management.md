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

See `state save|load|list|show|clear|clean` in [commands.md](commands.md). For authenticated session reuse with expiry handling, see [auth.md](auth.md) §Token Refresh Handling.

## Common Patterns

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

## Cleanup and Best Practices

Omitting `--session` uses the default session. Always close sessions when done to avoid leaked browser processes:

```bash
agent-browser --session auth close     # Close specific session
agent-browser session list             # List active sessions
agent-browser close                    # Close default session
```

1. **Name sessions semantically**: `--session github-auth` not `--session s1`
2. **Secure state files**: Don't commit (contain auth tokens), add to `.gitignore`
3. **Use encryption**: Set `AGENT_BROWSER_ENCRYPTION_KEY` for sensitive state
4. **Timeout long sessions**: `timeout 60 agent-browser --session long-task get text body`
