# fn-9.6 Log watcher and parser lib

## Description

Create log watcher and stream-json parser for iter-*.log files.

### Files

- `src/lib/log-watcher.ts` - fs.watch wrapper
- `src/lib/parser.ts` - stream-json format parser

### LogWatcher

```typescript
class LogWatcher extends EventEmitter {
  constructor(runPath: string)
  start(): void
  stop(): void
  // Events: 'line', 'error', 'new-iteration'
}
```

### Watching strategy

1. Watch run directory for new iter-*.log files
2. Tail-follow current iteration log
3. Debounce file change events (100ms)
4. Track byte position for incremental reads

### Parser

stream-json format (from Claude --watch):
```json
{"type":"tool_call","tool":"Read","input":{...}}
{"type":"tool_result","content":"..."}
{"type":"text","content":"..."}
```

Parse into LogEntry with tool icons:
- Read/Write/Glob → `→`
- Bash → `⚡`
- API calls → `◆`
- success → `✓`
- failure → `✗`

### Testing strategy

**Parser tests** (pure function, easy to test):
- Unit test: JSON line → LogEntry mapping
- Test various tool types, malformed lines

**LogWatcher tests** (I/O, harder):
- Use temp directory with test log files
- Append content, verify 'line' events fire
- May need polling fallback on some platforms
## Acceptance
- [ ] LogWatcher emits 'line' events for new log content
- [ ] Detects new iter-*.log files appearing
- [ ] Parser extracts tool type and content from stream-json
- [ ] Parser assigns correct icons per tool type
- [ ] Handles malformed JSON lines gracefully (skip, don't crash)
- [ ] `stop()` properly cleans up watchers
## Done summary
- Added LogWatcher class with fs.watch for run directory and iter-*.log files
- Added parser for stream-json format with tool icons (unicode + ASCII)
- Implemented debounced reads, byte position tracking, iteration detection
- Full test coverage (42 tests)
## Evidence
- Commits: ccd55aeb0edcfb8a235b22158aa83ce1c53c7bf1
- Tests: bun test
- PRs: