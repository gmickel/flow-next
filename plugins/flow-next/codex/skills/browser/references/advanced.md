# Advanced Features

## Network Interception

Mock or block network requests:

```bash
# Intercept and track requests
agent-browser network route "**/api/*"

# Block requests (ads, analytics)
agent-browser network route "**/analytics/*" --abort

# Mock response
agent-browser network route "**/api/user" --body '{"name":"Test User"}'

# Remove route
agent-browser network unroute "**/api/*"

# View tracked requests
agent-browser network requests
agent-browser network requests --filter api
```

## Tabs

```bash
agent-browser tab                # List tabs
agent-browser tab new            # New blank tab
agent-browser tab new url.com    # New tab with URL
agent-browser tab 2              # Switch to tab 2
agent-browser tab close          # Close current tab
agent-browser tab close 2        # Close tab 2
```

## Windows

```bash
agent-browser window new         # New browser window
```

## Frames (iframes)

```bash
agent-browser frame "#iframe-selector"  # Switch to iframe
agent-browser snapshot -i               # Snapshot within iframe
agent-browser click @e1                 # Interact within iframe
agent-browser frame main                # Back to main frame
```

## Dialogs

Handle alert/confirm/prompt dialogs:

```bash
agent-browser dialog accept              # Accept dialog
agent-browser dialog accept "input text" # Accept prompt with text
agent-browser dialog dismiss             # Dismiss/cancel dialog
```

## Mouse Control

Low-level mouse operations:

```bash
agent-browser mouse move 100 200       # Move to coordinates
agent-browser mouse down               # Press left button
agent-browser mouse down right         # Press right button
agent-browser mouse up                 # Release button
agent-browser mouse wheel -500         # Scroll wheel (negative = up)
```

## Drag and Drop

```bash
agent-browser drag @e1 @e2             # Drag e1 to e2
agent-browser drag "#source" "#target"
```

## File Upload

```bash
agent-browser upload @e1 /path/to/file.pdf
agent-browser upload @e1 file1.jpg file2.jpg  # Multiple files
```

## Browser Settings

### Viewport

```bash
agent-browser set viewport 1920 1080
```

### Device Emulation

```bash
agent-browser set device "iPhone 14"
agent-browser set device "Pixel 5"
```

### Geolocation

```bash
agent-browser set geo 37.7749 -122.4194  # San Francisco
```

### Offline Mode

```bash
agent-browser set offline on
agent-browser set offline off
```

### Color Scheme

```bash
agent-browser set media dark
agent-browser set media light
agent-browser set media light reduced-motion  # Light + reduced motion
```

### Extra HTTP Headers

```bash
agent-browser set headers '{"X-Key":"value"}'
```

### HTTP Basic Auth

```bash
agent-browser set credentials user pass
```

## CDP Mode

Connect to existing browser via Chrome DevTools Protocol:

```bash
# Auto-discover running Chrome with remote debugging
agent-browser --auto-connect open https://example.com
agent-browser --auto-connect snapshot

# Connect to Electron app or Chrome with explicit port
# Start Chrome: google-chrome --remote-debugging-port=9222
agent-browser --cdp 9222 snapshot
agent-browser --cdp 9222 click @e1
agent-browser connect 9222  # Alternative: connect command
```

Use cases: control Electron apps, connect to existing Chrome sessions, WebView2 apps.

## JavaScript Evaluation

```bash
# Simple expressions
agent-browser eval 'document.title'
agent-browser eval 'window.scrollTo(0, 1000)'
agent-browser eval 'localStorage.getItem("token")'

# Complex JS: use --stdin (RECOMMENDED for anything with nested quotes)
agent-browser eval --stdin <<'EVALEOF'
JSON.stringify(
  Array.from(document.querySelectorAll("img"))
    .filter(i => !i.alt)
    .map(i => ({ src: i.src.split("/").pop(), width: i.width }))
)
EVALEOF

# Base64 encoding (bypasses all shell escaping)
agent-browser eval -b "$(echo -n 'Array.from(document.querySelectorAll("a")).map(a => a.href)' | base64)"
```

## Bounding Box & Styles

Get element position, size, and computed styles:

```bash
agent-browser get box @e1
# {"x":100,"y":200,"width":150,"height":40}

agent-browser get styles @e1
# font, color, background, etc.
```

## Browser Extensions

Load browser extensions:

```bash
agent-browser --extension /path/to/extension open example.com
# Multiple extensions
agent-browser --extension /ext1 --extension /ext2 open example.com
# Via env var (comma-separated)
AGENT_BROWSER_EXTENSIONS="/ext1,/ext2" agent-browser open example.com
```

## Custom Browser Executable

Use system Chrome or lightweight builds:

```bash
agent-browser --executable-path /usr/bin/google-chrome open example.com

# Or via environment
AGENT_BROWSER_EXECUTABLE_PATH=/path/to/chromium agent-browser open example.com
```

Useful for: serverless (`@sparticuz/chromium`), system browser, custom Chromium builds.

## Ignore HTTPS Errors

For self-signed certs or SSL inspection proxies:

```bash
agent-browser --ignore-https-errors open https://self-signed.example.com
```

## Environment Variables

```bash
AGENT_BROWSER_SESSION="mysession"            # Default session name
AGENT_BROWSER_EXECUTABLE_PATH="/path/chrome" # Custom browser path
AGENT_BROWSER_EXTENSIONS="/ext1,/ext2"       # Comma-separated extension paths
AGENT_BROWSER_PROVIDER="browserbase"         # Cloud browser provider
AGENT_BROWSER_STREAM_PORT="9223"             # WebSocket streaming port
AGENT_BROWSER_HOME="/path/to/agent-browser"  # Custom install location
AGENT_BROWSER_CONFIG="/path/to/config.json"  # Custom config file
AGENT_BROWSER_ENCRYPTION_KEY="hex-key"       # Encrypt session state at rest
```
