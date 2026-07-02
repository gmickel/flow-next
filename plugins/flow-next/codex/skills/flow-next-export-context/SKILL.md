---
name: flow-next-export-context
description: Export RepoPrompt context to a markdown file for review with an external LLM (ChatGPT, Claude web, etc.). Use when you want Carmack-level review but prefer an external model. Triggers on "export context", "export for external review", "export plan for ChatGPT", "export impl review context", "review with an external model", "export review context".
---

# Export Context Mode

Build RepoPrompt context and export to a markdown file for use with external LLMs (ChatGPT Pro, Claude web, etc.).

**Use case**: When you want Carmack-level review but prefer to use an external model.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks use `$FLOWCTL`:

```bash
FLOWCTL="$HOME/.codex/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Input

Arguments: $ARGUMENTS
Format: `<type> <target> [focus areas]`

Types:
- `plan <spec-id>` - Export plan review context
- `impl` - Export implementation review context (current branch)

This skill is phrase-triggered (no slash command) — invoke it by asking in natural language; the host agent parses `<type> <target> [focus areas]` from the request.

Examples:
- "export context for plan fn-1, focus on security"
- "export impl review context, focus on the auth changes"

## Setup

```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

## Workflow

### Step 1: Determine Type

Parse arguments to determine if this is a plan or impl export.

### Step 2: Gather Content

**For plan export:**
```bash
$FLOWCTL show <spec-id> --json
$FLOWCTL cat <spec-id>
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

### Step 5: Build Review Prompt (file composition — no content re-typing)

**Path-persistence rule:** bash vars do NOT survive across prompt turns. Compose a literal unique prompt path in agent context — `${TMPDIR:-/tmp}/flow-export-prompt-<target>-<agent-chosen 4-char suffix>.md` — and type it verbatim in every block that references it.

Build the prompt by deterministic composition — the handoff is captured via redirection, never pasted into a heredoc; only the static review criteria (same criteria as plan-review or impl-review) are typed, once, in the quoted heredoc:

```bash
PROMPT_FILE="${TMPDIR:-/tmp}/flow-export-prompt-<target>-<suffix>.md" # literal path

# 1. Builder handoff — captured via redirection, never re-typed
$FLOWCTL rp prompt-get --window "$W" --tab "$T" > "$PROMPT_FILE"

# 2. Review criteria (static, quoted heredoc — same criteria block as
# plan-review or impl-review, per the export type)
cat >> "$PROMPT_FILE" << 'EOF'
<review criteria — static block>
EOF

$FLOWCTL rp prompt-set --window "$W" --tab "$T" --message-file "$PROMPT_FILE"
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
