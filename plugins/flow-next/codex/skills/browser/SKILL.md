---
name: browser
description: Browser automation via agent-browser CLI. Use when you need to navigate websites, verify deployed UI, test web apps, read online documentation, scrape data, fill forms, capture baseline screenshots before design work, or inspect current page state. Triggers on "check the page", "verify UI", "test the site", "read docs at", "look up API", "visit URL", "browse", "screenshot", "scrape", "e2e test", "login flow", "capture baseline", "see how it looks", "inspect current", "before redesign".
---

# Browser Automation

Browser automation via Vercel's agent-browser CLI. Runs headless by default; use `--headed` for visible window. Uses ref-based selection (@e1, @e2) from accessibility snapshots.

## Setup & Version Check

```bash
# Check installed + print version
command -v agent-browser >/dev/null 2>&1 && agent-browser --version || echo "MISSING: npm i -g agent-browser && agent-browser install"
```

Always run the version check at the start of a browser session. agent-browser iterates quickly — check for updates if the version is more than a week old:

```bash
npm view agent-browser version  # Latest published
```

## Core Workflow

1. **Open** URL
2. **Snapshot** to get refs
3. **Interact** via refs
4. **Re-snapshot** after DOM changes

```bash
agent-browser open https://example.com
agent-browser snapshot -i              # Interactive elements with refs
agent-browser click @e1
agent-browser wait --load networkidle  # Wait for SPA to settle
agent-browser snapshot -i              # Re-snapshot after change
```

## Command Chaining

Commands can be chained with `&&` in a single shell invocation. The browser persists between commands via a background daemon, so chaining is safe and more efficient than separate calls.

```bash
# Chain open + wait + snapshot
agent-browser open https://example.com && agent-browser wait --load networkidle && agent-browser snapshot -i

# Chain multiple interactions
agent-browser fill @e1 "user@example.com" && agent-browser fill @e2 "password123" && agent-browser click @e3
```

**When to chain:** Use `&&` when you don't need intermediate output (e.g., open + wait + screenshot). Run separately when you need to parse output first (e.g., snapshot to discover refs, then interact).

## Essential Commands

### Navigation

```bash
agent-browser open <url>       # Navigate (aliases: goto, navigate)
agent-browser back             # Go back
agent-browser forward          # Go forward
agent-browser reload           # Reload
agent-browser close            # Close browser (aliases: quit, exit)
```

### Snapshots

```bash
agent-browser snapshot           # Full accessibility tree
agent-browser snapshot -i        # Interactive only (recommended)
agent-browser snapshot -i -C     # Include cursor-interactive (divs with onclick, cursor:pointer)
agent-browser snapshot -i --json # JSON for parsing
agent-browser snapshot -c        # Compact (remove empty)
agent-browser snapshot -d 3      # Limit depth
agent-browser snapshot -s "#main" # Scope to selector
```

### Interactions

```bash
agent-browser click @e1              # Click
agent-browser click @e1 --new-tab    # Click and open in new tab
agent-browser dblclick @e1           # Double-click
agent-browser fill @e1 "text"        # Clear + fill input
agent-browser type @e1 "text"        # Type without clearing
agent-browser press Enter            # Key press
agent-browser press Control+a        # Key combination
agent-browser keydown Shift          # Hold key down
agent-browser keyup Shift            # Release key
agent-browser hover @e1              # Hover
agent-browser check @e1              # Check checkbox
agent-browser uncheck @e1            # Uncheck
agent-browser select @e1 "option"    # Dropdown
agent-browser select @e1 "a" "b"     # Multi-select
agent-browser scroll down 500        # Scroll direction + pixels
agent-browser scrollintoview @e1     # Scroll element visible
agent-browser drag @e1 @e2           # Drag and drop
agent-browser upload @e1 file.pdf    # Upload files
```

### Get Info

```bash
agent-browser get text @e1       # Element text
agent-browser get value @e1      # Input value
agent-browser get html @e1       # Element HTML
agent-browser get attr href @e1  # Attribute
agent-browser get title          # Page title
agent-browser get url            # Current URL
agent-browser get count "button" # Count matches
agent-browser get box @e1        # Bounding box (x, y, width, height)
agent-browser get styles @e1     # Computed styles (font, color, bg)
```

### Check State

```bash
agent-browser is visible @e1    # Check visibility
agent-browser is enabled @e1    # Check enabled
agent-browser is checked @e1    # Check checkbox state
```

### Wait

```bash
agent-browser wait @e1                 # Wait for element visible
agent-browser wait 2000                # Wait milliseconds
agent-browser wait --text "Success"    # Wait for text (-t)
agent-browser wait --url "**/dashboard" # Wait for URL pattern (-u)
agent-browser wait --load networkidle  # Wait for network idle (-l)
agent-browser wait --fn "window.ready" # Wait for JS condition (-f)
```

### Screenshots & Capture

```bash
agent-browser screenshot              # Viewport to temp dir
agent-browser screenshot out.png      # Save to file
agent-browser screenshot --full       # Full page
agent-browser screenshot --annotate   # Annotated with numbered element labels
agent-browser pdf out.pdf             # Save as PDF
```

### Diff (Compare Page States)

Compare accessibility tree or visual state before/after changes:

```bash
# Snapshot diff: compare current vs last snapshot
agent-browser snapshot -i              # Baseline
agent-browser click @e2                # Action
agent-browser diff snapshot            # See what changed

# Snapshot diff: compare vs saved file
agent-browser diff snapshot --baseline before.txt

# Visual pixel diff
agent-browser diff screenshot --baseline before.png

# Compare two URLs
agent-browser diff url https://staging.example.com https://prod.example.com
agent-browser diff url <url1> <url2> --wait-until networkidle
agent-browser diff url <url1> <url2> --selector "#main"
agent-browser diff url <url1> <url2> --screenshot  # Visual diff
```

`diff snapshot` uses `+`/`-` like git diff. `diff screenshot` produces a diff image with changed pixels in red + mismatch percentage.

### Semantic Locators

Alternative when you know the element (no snapshot needed):

```bash
agent-browser find role button click --name "Submit"
agent-browser find text "Sign In" click
agent-browser find text "Sign In" click --exact  # Exact match only
agent-browser find label "Email" fill "user@test.com"
agent-browser find placeholder "Search" fill "query"
agent-browser find alt "Logo" click
agent-browser find title "Close" click
agent-browser find testid "submit-btn" click
agent-browser find first ".item" click
agent-browser find last ".item" click
agent-browser find nth 2 "a" hover
```

## Annotated Screenshots (Vision Mode)

Use `--annotate` to take a screenshot with numbered labels overlaid on interactive elements. Each label `[N]` maps to ref `@eN`. Also caches refs — interact immediately without separate snapshot.

```bash
agent-browser screenshot --annotate
# Output includes image path + legend:
#   [1] @e1 button "Submit"
#   [2] @e2 link "Home"
#   [3] @e3 textbox "Email"
agent-browser click @e2  # Use ref from annotated screenshot
```

Use when: unlabeled icon buttons, visual-only elements, canvas/charts (invisible to text snapshots), or spatial reasoning needed.

## JavaScript Evaluation

Use `eval` to run JS in the browser. **Shell quoting can corrupt complex expressions** — use `--stdin` or `-b` to avoid issues.

```bash
# Simple expressions: regular quoting OK
agent-browser eval 'document.title'
agent-browser eval 'document.querySelectorAll("img").length'

# Complex JS: use --stdin with heredoc (RECOMMENDED)
agent-browser eval --stdin <<'EVALEOF'
JSON.stringify(
  Array.from(document.querySelectorAll("img"))
    .filter(i => !i.alt)
    .map(i => ({ src: i.src.split("/").pop(), width: i.width }))
)
EVALEOF

# Alternative: base64 encoding (bypasses all shell escaping)
agent-browser eval -b "$(echo -n 'Array.from(document.querySelectorAll("a")).map(a => a.href)' | base64)"
```

**Rules of thumb:**
- Single-line, no nested quotes → `eval 'expression'` with single quotes
- Nested quotes, arrow functions, template literals, multiline → `eval --stdin <<'EVALEOF'`
- Programmatic/generated scripts → `eval -b` with base64

## Sessions

Parallel isolated browsers (see [auth.md](references/auth.md) for multi-user auth):

```bash
agent-browser --session test1 open site-a.com
agent-browser --session test2 open site-b.com
agent-browser session list
```

### Session Persistence

Auto-save/restore cookies and localStorage across browser restarts:

```bash
agent-browser --session-name myapp open https://app.example.com/login
# ... login flow ...
agent-browser close  # State auto-saved to ~/.agent-browser/sessions/

# Next time: state auto-loaded
agent-browser --session-name myapp open https://app.example.com/dashboard

# Encrypt state at rest
export AGENT_BROWSER_ENCRYPTION_KEY=$(openssl rand -hex 32)
agent-browser --session-name secure open https://app.example.com

# Manage saved states
agent-browser state list
agent-browser state show myapp-default.json
agent-browser state clear myapp
agent-browser state clean --older-than 7
```

## Connect to Existing Chrome

```bash
# Auto-discover running Chrome with remote debugging
agent-browser --auto-connect open https://example.com
agent-browser --auto-connect snapshot

# Or explicit CDP port
agent-browser --cdp 9222 snapshot
```

## Local Files

```bash
agent-browser --allow-file-access open file:///path/to/document.pdf
agent-browser --allow-file-access open file:///path/to/page.html
agent-browser screenshot output.png
```

## iOS Simulator (Mobile Safari)

```bash
# List available iOS simulators
agent-browser device list

# Launch Safari on specific device
agent-browser -p ios --device "iPhone 16 Pro" open https://example.com

# Same workflow: snapshot, interact, re-snapshot
agent-browser -p ios snapshot -i
agent-browser -p ios tap @e1          # Tap (alias for click)
agent-browser -p ios fill @e2 "text"
agent-browser -p ios swipe up         # Mobile gesture
agent-browser -p ios screenshot mobile.png
agent-browser -p ios close
```

**Requires:** macOS with Xcode, Appium (`npm install -g appium && appium driver install xcuitest`).
**Real devices:** Use `--device "<UDID>"` (UDID from `xcrun xctrace list devices`).

## Configuration File

Create `agent-browser.json` in project root for persistent settings:

```json
{
  "headed": true,
  "proxy": "http://localhost:8080",
  "profile": "./browser-data"
}
```

Priority (lowest→highest): `~/.agent-browser/config.json` < `./agent-browser.json` < env vars < CLI flags. Use `--config <path>` or `AGENT_BROWSER_CONFIG` for custom path. All CLI options map to camelCase keys (`--executable-path` → `"executablePath"`).

## Timeouts and Slow Pages

Default Playwright timeout is 60s. For slow pages, use explicit waits:

```bash
agent-browser wait --load networkidle      # Best for slow pages
agent-browser wait "#content"              # Wait for specific element
agent-browser wait @e1                     # Wait for ref
agent-browser wait --url "**/dashboard"    # Wait after redirects
agent-browser wait --fn "document.readyState === 'complete'"
agent-browser wait 5000                    # Fixed duration (last resort)
```

Use `wait --load networkidle` after `open` for consistently slow sites.

## JSON Output

Add `--json` for machine-readable output:

```bash
agent-browser snapshot -i --json
agent-browser get text @e1 --json
agent-browser is visible @e1 --json
```

## Recording & Profiling

```bash
# Video recording
agent-browser record start demo.webm
# ... actions ...
agent-browser record stop
agent-browser record restart take2.webm  # Stop current + start new

# Chrome DevTools profiling
agent-browser profiler start
# ... actions ...
agent-browser profiler stop trace.json
```

See [debugging.md](references/debugging.md) for details.

## Examples

### Form Submission

```bash
agent-browser open https://example.com/form
agent-browser snapshot -i
agent-browser fill @e1 "user@example.com"
agent-browser fill @e2 "password123"
agent-browser click @e3
agent-browser wait --load networkidle
agent-browser snapshot -i  # Verify result
```

### Auth with Saved State

```bash
# Login once
agent-browser open https://app.example.com/login
agent-browser snapshot -i
agent-browser fill @e1 "username"
agent-browser fill @e2 "password"
agent-browser click @e3
agent-browser wait --url "**/dashboard"
agent-browser state save auth.json

# Later: reuse saved auth
agent-browser state load auth.json
agent-browser open https://app.example.com/dashboard
```

More auth patterns in [auth.md](references/auth.md).

### Token Auth (Skip Login)

```bash
agent-browser open api.example.com --headers '{"Authorization": "Bearer <token>"}'
agent-browser snapshot -i --json
```

## Debugging

```bash
agent-browser --headed open example.com  # Show browser window
agent-browser console                    # View console messages
agent-browser errors                     # View page errors
agent-browser highlight @e1              # Highlight element
agent-browser --debug open example.com   # Verbose output
```

See [debugging.md](references/debugging.md) for traces, profiling, video, common issues.

## Session Cleanup

Always close sessions when done to avoid leaked processes:

```bash
agent-browser close                    # Close default session
agent-browser --session name close     # Close specific session
```

If previous session not closed properly, daemon may still be running. `agent-browser close` cleans it up.

## Troubleshooting

**"Browser not launched" error**: Daemon stuck. Kill and retry:
```bash
pkill -f agent-browser && agent-browser open <url>
```

**`--headed` not showing window**: Daemon reuse bug. If daemon started headless, `--headed` is ignored. Kill daemon first:
```bash
agent-browser close
pkill -f "node.*daemon.js.*AGENT_BROWSER"
pkill -f "Google Chrome for Testing"
sleep 1
agent-browser open <url> --headed
```

**Window exists but not visible** (macOS):
```bash
osascript -e 'tell application "Google Chrome for Testing" to activate'
```

**Element not found**: Re-snapshot after page changes. DOM may have updated.

**Ref lifecycle**: Refs (`@e1`, `@e2`) are invalidated when the page changes. Always re-snapshot after clicks that navigate, form submissions, or dynamic content loading.

## References

| Topic | File |
|-------|------|
| Full command reference | [commands.md](references/commands.md) |
| Snapshot refs, lifecycle, troubleshooting | [snapshot-refs.md](references/snapshot-refs.md) |
| Auth, OAuth, 2FA, state persistence | [auth.md](references/auth.md) |
| Sessions, parallel browsers, state | [session-management.md](references/session-management.md) |
| Debugging, profiling, video recording | [debugging.md](references/debugging.md) |
| Proxy, geo-testing, rotating proxies | [proxy.md](references/proxy.md) |
| Network mocking, tabs, frames, dialogs, settings | [advanced.md](references/advanced.md) |
