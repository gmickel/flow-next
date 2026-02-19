---
name: flow-next-export-context
description: Export RepoPrompt context for external LLM review (ChatGPT, Claude web, etc.). Use when you want to review code or plans with an external model. Triggers on /flow-next:export-context.
---

# Export Context Mode

Build RepoPrompt context and export to a markdown file for use with external LLMs (ChatGPT Pro, Claude web, etc.).

**Use case**: When you want Carmack-level review but prefer to use an external model.

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:
```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
$FLOWCTL <command>
```

## Input

Arguments: $ARGUMENTS
Format: `<type> <target> [focus areas]`

Types:
- `plan <epic-id>` - Export plan review context
- `impl` - Export implementation review context (current branch)

Examples:
- `/flow-next:export-context plan fn-1 focus on security`
- `/flow-next:export-context impl focus on the auth changes`

## Setup

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

## Workflow

### Step 1: Determine Type

Parse arguments to determine if this is a plan or impl export.

### Step 2: Gather Content

**For plan export:**
```bash
$FLOWCTL show <epic-id> --json
$FLOWCTL cat <epic-id>
```

**For impl export:**
```bash
git branch --show-current
git log main..HEAD --oneline 2>/dev/null || git log master..HEAD --oneline
git diff main..HEAD --name-only 2>/dev/null || git diff master..HEAD --name-only
```

### Step 3: Setup RepoPrompt

```bash
eval "$($FLOWCTL rp setup-review --repo-root "$REPO_ROOT" --summary "<summary based on type>" --create)"
```

### Step 4: Augment Selection

```bash
$FLOWCTL rp select-get --window "$W" --tab "$T"

# Add relevant files
$FLOWCTL rp select-add --window "$W" --tab "$T" <files>
```

### Step 5: Build Review Prompt

Get builder's handoff:
```bash
$FLOWCTL rp prompt-get --window "$W" --tab "$T"
```

Build combined prompt with review criteria (same as plan-review or impl-review).

Set the prompt:
```bash
cat > /tmp/export-prompt.md << 'EOF'
[COMBINED PROMPT WITH REVIEW CRITERIA]
EOF

$FLOWCTL rp prompt-set --window "$W" --tab "$T" --message-file /tmp/export-prompt.md
```

### Step 6: Export

```bash
OUTPUT_FILE=~/Desktop/review-export-$(date +%Y%m%d-%H%M%S).md
$FLOWCTL rp prompt-export --window "$W" --tab "$T" --out "$OUTPUT_FILE"
open "$OUTPUT_FILE"
```

### Step 7: Inform User

```
Exported review context to: $OUTPUT_FILE

The file contains:
- Full file tree with selected files marked
- Code maps (signatures/structure)
- Complete file contents
- Review prompt with Carmack-level criteria

Paste into ChatGPT Pro, Claude web, or your preferred LLM.
After receiving feedback, return here to implement fixes.
```

## Note

This skill is for **manual** external review only. It does not work with Ralph autonomous mode (no receipts, no status updates).
