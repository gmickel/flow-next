# RepoPrompt Wrapper Reference

Use `flowctl rp` wrappers only.

## Primary Command (Ralph mode)

```bash
# Atomic setup: pick-window + builder
eval "$($FLOWCTL rp setup-review --repo-root "$REPO_ROOT" --summary "...")"
# Returns: W=<window> T=<tab>
```

This is the **only** way to initialize a review session. Do not call `pick-window` or `builder` individually.

## Post-Setup Commands

After `setup-review`, use these with `$W` and `$T`:

```bash
# Get/modify selection
flowctl rp select-get --window "$W" --tab "$T"
flowctl rp select-add --window "$W" --tab "$T" path/to/file

# Get/set prompt
flowctl rp prompt-get --window "$W" --tab "$T"
flowctl rp prompt-set --window "$W" --tab "$T" --message-file /tmp/prompt.md

# Execute review
flowctl rp chat-send --window "$W" --tab "$T" --message-file /tmp/review.md --new-chat --chat-name "Review: X"

# Export (non-Ralph)
flowctl rp prompt-export --window "$W" --tab "$T" --out ~/Desktop/export.md
```

## Key Rules

1. **Always use setup-review first** - handles window selection atomically
2. **Always pass --window and --tab** - required for all post-setup commands
3. **--window must be numeric** - comes from setup-review output
4. **Use --message-file (not --message)** - write prompt to file first, then pass path

## Common Mistakes

- `--message "text"` → WRONG, use `--message-file /path/to/file`
- `setup-review <epic-id>` → WRONG, use `setup-review --repo-root ... --summary ...`
- `select-add --paths ...` → WRONG, use `select-add --window "$W" --tab "$T" <path>`
- `chat-send --json` → WRONG, suppresses review text; if you see `{"chat": null}` you used --json incorrectly

## Re-Review Rule (CRITICAL)

First review: `chat-send ... --new-chat --chat-name "..."`
Re-reviews: `chat-send ... --message-file /tmp/re-review.md` (NO --new-chat)

**Why**: Reviewer needs context from previous feedback. New chat = lost context = reviewer repeats same issues.
