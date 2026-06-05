---
name: flow-next
description: "Manage .flow/ tasks and specs. Triggers: 'show me my tasks', 'list specs', 'what tasks are there', 'add a task', 'create task', 'what's ready', 'task status', 'show fn-1-add-oauth'. NOT for /flow-next:plan or /flow-next:work."
---

# Flow-Next Task Management

Quick task operations in `.flow/`. For planning features use `/flow-next:plan`, for executing use `/flow-next:work`.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**Discover all commands/options:**
```bash
$FLOWCTL --help
$FLOWCTL <command> --help   # e.g., $FLOWCTL task --help
```

## Quick Reference

```bash
# Check if .flow exists
$FLOWCTL detect --json

# Initialize (if needed)
$FLOWCTL init --json

# List everything (specs + tasks grouped)
$FLOWCTL list --json

# List all specs
$FLOWCTL specs --json

# List all tasks (or filter by spec/status)
$FLOWCTL tasks --json
$FLOWCTL tasks --spec fn-1-add-oauth --json
$FLOWCTL tasks --status todo --json

# View spec with all tasks
$FLOWCTL show fn-1-add-oauth --json
$FLOWCTL cat fn-1-add-oauth              # Spec markdown

# View single task
$FLOWCTL show fn-1-add-oauth.2 --json
$FLOWCTL cat fn-1-add-oauth.2            # Task spec

# What's ready to work on?
$FLOWCTL ready --spec fn-1-add-oauth --json

# Create task under existing spec
$FLOWCTL task create --spec fn-1-add-oauth --title "Fix bug X" --json

# Set task description and acceptance (combined, fewer writes)
$FLOWCTL task set-spec fn-1-add-oauth.2 --description /tmp/desc.md --acceptance /tmp/accept.md --json

# Or use stdin with heredoc (no temp file):
$FLOWCTL task set-description fn-1-add-oauth.2 --file - --json <<'EOF'
Description here
EOF

# Start working on task
$FLOWCTL start fn-1-add-oauth.2 --json

# Mark task done
echo "What was done" > /tmp/summary.md
echo '{"commits":["abc123"],"tests":["npm test"],"prs":[]}' > /tmp/evidence.json
$FLOWCTL done fn-1-add-oauth.2 --summary-file /tmp/summary.md --evidence-json /tmp/evidence.json --json

# Validate structure
$FLOWCTL validate --spec fn-1-add-oauth --json
$FLOWCTL validate --all --json
```

## Common Patterns

### "Add a task for X"

1. Find relevant spec:
   ```bash
   # List all specs
   $FLOWCTL specs --json

   # Or show a specific spec to check its scope
   $FLOWCTL show fn-1 --json
   ```

2. Create task:
   ```bash
   $FLOWCTL task create --spec fn-N --title "Short title" --json
   ```

3. Add description + acceptance (combined):
   ```bash
   cat > /tmp/desc.md << 'EOF'
   **Bug/Feature:** Brief description

   **Details:**
   - Point 1
   - Point 2
   EOF
   cat > /tmp/accept.md << 'EOF'
   - [ ] Criterion 1
   - [ ] Criterion 2
   EOF
   $FLOWCTL task set-spec fn-N.M --description /tmp/desc.md --acceptance /tmp/accept.md --json
   ```

### "What tasks are there?"

```bash
# All specs
$FLOWCTL specs --json

# All tasks
$FLOWCTL tasks --json

# Tasks for specific spec
$FLOWCTL tasks --spec fn-1-add-oauth --json

# Ready tasks for a spec
$FLOWCTL ready --spec fn-1-add-oauth --json
```

### "Show me task X"

```bash
$FLOWCTL show fn-1-add-oauth.2 --json   # Metadata
$FLOWCTL cat fn-1-add-oauth.2           # Full spec
```

(Legacy `fn-1.2` / `fn-1-xxx.2` still works.)

### Create new spec (rare - usually via /flow-next:plan)

```bash
$FLOWCTL spec create --title "Spec title" --json
# Returns: {"success": true, "id": "fn-N-spec-title", ...}
```

## ID Format

- Spec: `fn-N-slug` where slug is derived from title (e.g., `fn-1-add-oauth`, `fn-2-fix-login-bug`)
- Task: `fn-N-slug.M` (e.g., `fn-1-add-oauth.1`, `fn-2-fix-login-bug.2`)

Legacy formats `fn-N` and `fn-N-xxx` (random 3-char suffix) are still supported.

## Notes

- Run `$FLOWCTL --help` to discover all commands and options
- All writes go through flowctl (don't edit JSON/MD files directly)
- `--json` flag gives machine-readable output
- For complex planning/execution, use `/flow-next:plan` and `/flow-next:work`
