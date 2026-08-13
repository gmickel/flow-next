# Debugging

When browser automation fails or behaves unexpectedly.

## Headed Mode

Show visible browser window to see what's happening:

```bash
agent-browser --headed open example.com
agent-browser --headed snapshot -i
agent-browser --headed click @e1
```

## Console & Errors

View browser console output and page errors:

```bash
agent-browser console          # View console messages
agent-browser console --clear  # Clear console log
agent-browser errors           # View page errors
agent-browser errors --clear   # Clear error log
```

## Highlight Elements

Visually identify elements (use with `--headed`):

```bash
agent-browser highlight @e1
agent-browser highlight "#selector"
```

## Traces

Record browser traces for detailed debugging:

```bash
agent-browser trace start           # Start recording
# ... do interactions ...
agent-browser trace stop trace.zip  # Save trace file
```

Open traces in Playwright Trace Viewer: `npx playwright show-trace trace.zip`

## Video Recording

Capture browser automation as video for debugging or documentation:

```bash
# Start recording
agent-browser record start ./demo.webm

# Perform actions
agent-browser open https://example.com
agent-browser snapshot -i
agent-browser click @e1

# Stop and save
agent-browser record stop

# Restart with new file (stops current + starts new)
agent-browser record restart ./take2.webm
```

### Recording Tips

- Add `agent-browser wait 500` pauses for human-viewable recordings
- Use descriptive filenames: `login-flow-2024-01-15.webm`
- Combine with screenshots for key frames
- Always stop recording on error:
  ```bash
  cleanup() { agent-browser record stop 2>/dev/null || true; }
  trap cleanup EXIT
  ```

**Output format:** WebM (VP8/VP9 codec), compatible with all modern browsers.

## Chrome DevTools Profiling

Capture performance profiles for analysis:

```bash
# Start profiling
agent-browser profiler start

# Perform actions to profile
agent-browser open https://app.example.com
agent-browser wait --load networkidle

# Stop and save
agent-browser profiler stop ./trace.json
```

### Custom trace categories

```bash
agent-browser profiler start --categories "devtools.timeline,v8.execute,blink.user_timing"
```

Default categories: `devtools.timeline`, `v8.execute`, `blink`, `blink.user_timing`, `latencyInfo`, `renderer.scheduler`, `toplevel`.

### Viewing profiles

- **Chrome DevTools:** Performance panel → Load profile
- **Perfetto UI:** https://ui.perfetto.dev/ — drag and drop JSON
- **Trace Viewer:** `chrome://tracing`

**Limitations:** Chromium-only. Trace data capped at 5M events. 30s timeout on stop.

## Debug Output

Add `--debug` for verbose output:

```bash
agent-browser --debug open example.com
agent-browser --debug click @e1
```

## State Checks

Verify element state before interacting:

```bash
agent-browser is visible @e1    # Returns true/false
agent-browser is enabled @e1    # Check if interactive
agent-browser is checked @e1    # Checkbox state
```

With JSON output:
```bash
agent-browser is visible @e1 --json
# {"success":true,"data":true}
```

## Common Issues

### Element not found
- Re-snapshot: DOM may have changed
- Check visibility: `is visible @e1`
- Try `--headed` to see actual page state

### Click does nothing
- Element may be covered: try `scrollintoview @e1` first
- Element may be disabled: check `is enabled @e1`
- SPA not ready: add `wait --load networkidle`

### Form not submitting
- Check for validation errors in snapshot
- Some forms need `press Enter` instead of button click
- Wait for network: `wait --load networkidle`

### Auth redirect loops
- Save state after successful login: `state save auth.json`
- Check cookies: `cookies`
- Verify URL pattern: `get url`
