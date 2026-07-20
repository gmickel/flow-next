# Plan Review Workflow

---

## CRITICAL: RepoPrompt Commands Are SLOW - DO NOT RETRY

**READ THIS BEFORE RUNNING ANY COMMANDS:**

1. **`setup-review` takes 5-15 MINUTES** - It runs the RepoPrompt context builder which indexes files. This is NORMAL. Do NOT assume it is stuck.

2. **`chat-send` takes 2-10 MINUTES** - It waits for the LLM to generate a full review. This is NORMAL. Do NOT assume it is stuck.

3. **Run commands directly and WAIT** - Do NOT use background jobs. Just run the command and wait:
 ```bash
 # Run setup-review - takes 5-15 minutes, just wait
 $FLOWCTL rp setup-review --repo-root "$REPO_ROOT" --summary "..."
 # You will see file paths printed as it indexes - this is progress, not errors
 ```

4. **Output is progress, not errors** - The context builder prints file paths as it indexes. Seeing many lines of output is NORMAL. Do not interpret this as an error loop.

5. **NEVER retry these commands** - If you run them again, you will create duplicate reviews and waste time. Run ONCE and WAIT.

6. **Exit code 0 = success** - When the command finishes, check the exit code. If it is 0, it worked.

**If a command has been running for less than 15 minutes, WAIT. Do not retry. Do not output <promise>RETRY</promise>.**

---

## Philosophy

The reviewer model only sees selected files. RepoPrompt's Builder discovers context you'd miss (rp backend). Codex, Copilot, and Cursor use context hints from flowctl (codex/copilot/cursor backends).

---

## Phase 0: Backend Detection

**Run this first. Do not skip.**

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:

```bash
set -e
FLOWCTL="$HOME/.codex/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Priority: --review flag > per-spec `default_review` override > env > config (flag parsed in SKILL.md).
# Resolve the spec id from $ARGUMENTS FIRST so a per-spec `default_review` override routes to the
# right backend before branching (empty → env/config, no regression).
# Text output is bare backend name for back-compat grep. --json returns full
# resolved spec (backend, spec, model, effort, source).
SPEC_ID="${1:-}" # the spec-id positional arg (canonicalized by review-backend); empty falls back to env/config
BACKEND=$($FLOWCTL review-backend "$SPEC_ID")

if [[ "$BACKEND" == "ASK" ]]; then
 echo "Error: No review backend configured."
 echo "Run /flow-next:setup to configure, or pass --review=rp|codex|copilot|cursor|none"
 exit 1
fi

echo "Review backend: $BACKEND (override: --review=rp|codex|copilot|cursor|none)"
```

**Spec-form env var (optional):** `FLOW_REVIEW_BACKEND` accepts bare or full spec:

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
FLOW_REVIEW_BACKEND=codex:gpt-5.5:xhigh $FLOWCTL codex plan-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
FLOW_REVIEW_BACKEND=copilot:claude-opus-4.5 $FLOWCTL copilot plan-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
# Cursor folds effort into the model name (no :<effort>):
FLOW_REVIEW_BACKEND=cursor:gpt-5.5-high $FLOWCTL cursor plan-review "$SPEC_ID" --files "$CODE_FILES" --receipt "$RECEIPT_PATH"
# Or pass spec directly:
$FLOWCTL codex plan-review "$SPEC_ID" --spec "codex:gpt-5.5:xhigh" --receipt "$RECEIPT_PATH"
```

Per-spec `default_review` (set via `flowctl spec set-backend`) overrides env.

**If backend is "none"**: Skip review, inform user, and exit cleanly (no error).

**Then branch to backend-specific workflow below.**

---

## Codex Backend Workflow

Use when `BACKEND="codex"`.

### Step 0: Save Checkpoint

**Before review** (protects against context compaction):
```bash
SPEC_ID="${1:-}"
$FLOWCTL checkpoint save --spec "$SPEC_ID" --json
```

### Step 1: Execute Review

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/plan-review-receipt-${SPEC_ID}.json}" # fn-90 R5: spec-scoped default (concurrent specs no longer collide); explicit REVIEW_RECEIPT_PATH still wins

# --files: comma-separated CODE files for reviewer context
# Spec/task specs are auto-included; pass files the plan will CREATE or MODIFY
# Read spec to identify affected paths, then list key files
CODE_FILES="$(awk '/^## Key files/{f=1;next} /^## /{f=0} f' ".flow/specs/${SPEC_ID}.md" | grep -oE '`[^`]+\.[A-Za-z0-9]+`' | tr -d '`' | grep -vE '^https?:' | sort -u | head -20 | paste -sd, -)"
[ -z "$CODE_FILES" ] && CODE_FILES="$(grep -oE '[A-Za-z0-9_./-]+\.(py|ts|tsx|js|jsx|go|rs|rb|java|php|c|cpp|h|md|sh)' ".flow/specs/${SPEC_ID}.md" | grep -vE '^https?:' | sort -u | head -20 | paste -sd, -)" # real anchors from the spec's Key files, never a hardcoded guess

$FLOWCTL codex plan-review "$SPEC_ID" --files "$CODE_FILES" --receipt "$RECEIPT_PATH"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK`.**

### Step 2: Update Status

```bash
# Based on verdict
$FLOWCTL spec set-plan-review-status "$SPEC_ID" --status ship --json
# OR
$FLOWCTL spec set-plan-review-status "$SPEC_ID" --status needs_work --json
```

### Step 3: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix plan via `$FLOWCTL spec set-plan`
3. Re-run step 1 (receipt enables session continuity)
4. Repeat until SHIP

### Step 4: Receipt

Receipt is written automatically by `flowctl codex plan-review` when `--receipt` provided.
Format: `{"type":"plan_review","id":"<spec-id>","mode":"codex","verdict":"<verdict>","session_id":"<thread_id>","timestamp":"..."}`

---

## Copilot Backend Workflow

Use when `BACKEND="copilot"`.

### Step 0: Save Checkpoint

**Before review** (protects against context compaction):
```bash
SPEC_ID="${1:-}"
$FLOWCTL checkpoint save --spec "$SPEC_ID" --json
```

### Step 1: Execute Review

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/plan-review-receipt-${SPEC_ID}.json}" # fn-90 R5: spec-scoped default (concurrent specs no longer collide); explicit REVIEW_RECEIPT_PATH still wins

# --files: comma-separated CODE files for reviewer context
# Spec/task specs are auto-included; pass files the plan will CREATE or MODIFY
CODE_FILES="$(awk '/^## Key files/{f=1;next} /^## /{f=0} f' ".flow/specs/${SPEC_ID}.md" | grep -oE '`[^`]+\.[A-Za-z0-9]+`' | tr -d '`' | grep -vE '^https?:' | sort -u | head -20 | paste -sd, -)"
[ -z "$CODE_FILES" ] && CODE_FILES="$(grep -oE '[A-Za-z0-9_./-]+\.(py|ts|tsx|js|jsx|go|rs|rb|java|php|c|cpp|h|md|sh)' ".flow/specs/${SPEC_ID}.md" | grep -vE '^https?:' | sort -u | head -20 | paste -sd, -)" # real anchors from the spec's Key files, never a hardcoded guess

# Runtime config:
# --spec <spec> full spec (backend:model:effort), highest priority
# FLOW_REVIEW_BACKEND spec-form ok: copilot:claude-opus-4.5:xhigh
# FLOW_COPILOT_MODEL fills missing model only (default gpt-5.5)
# FLOW_COPILOT_EFFORT fills missing effort only (default high)

$FLOWCTL copilot plan-review "$SPEC_ID" --files "$CODE_FILES" --receipt "$RECEIPT_PATH"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK`.**

### Step 2: Update Status

```bash
# Based on verdict
$FLOWCTL spec set-plan-review-status "$SPEC_ID" --status ship --json
# OR
$FLOWCTL spec set-plan-review-status "$SPEC_ID" --status needs_work --json
```

### Step 3: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix plan via `$FLOWCTL spec set-plan`
3. Re-run step 1 (receipt enables session continuity when `mode == "copilot"`)
4. Repeat until SHIP

### Step 4: Receipt

Receipt is written automatically by `flowctl copilot plan-review` when `--receipt` provided.
Format: `{"type":"plan_review","id":"<spec-id>","mode":"copilot","verdict":"<verdict>","session_id":"<uuid>","model":"<model>","effort":"<effort>","spec":"copilot:<model>:<effort>","timestamp":"..."}`

The `spec` field is the canonical round-trippable form (added in fn-28.3). `model` + `effort` remain for backward compatibility.

Session resume guard: re-review only resumes the copilot session when the existing receipt at `$RECEIPT_PATH` has `mode == "copilot"`. Cross-backend switches start a fresh session.

---

## Cursor Backend Workflow

Use when `BACKEND="cursor"`.

### Step 0: Save Checkpoint

**Before review** (protects against context compaction):
```bash
SPEC_ID="${1:-}"
$FLOWCTL checkpoint save --spec "$SPEC_ID" --json
```

### Step 1: Execute Review

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/plan-review-receipt-${SPEC_ID}.json}" # fn-90 R5: spec-scoped default (concurrent specs no longer collide); explicit REVIEW_RECEIPT_PATH still wins

# --files: comma-separated CODE files for reviewer context
# Spec/task specs are auto-included; pass files the plan will CREATE or MODIFY
CODE_FILES="$(awk '/^## Key files/{f=1;next} /^## /{f=0} f' ".flow/specs/${SPEC_ID}.md" | grep -oE '`[^`]+\.[A-Za-z0-9]+`' | tr -d '`' | grep -vE '^https?:' | sort -u | head -20 | paste -sd, -)"
[ -z "$CODE_FILES" ] && CODE_FILES="$(grep -oE '[A-Za-z0-9_./-]+\.(py|ts|tsx|js|jsx|go|rs|rb|java|php|c|cpp|h|md|sh)' ".flow/specs/${SPEC_ID}.md" | grep -vE '^https?:' | sort -u | head -20 | paste -sd, -)" # real anchors from the spec's Key files, never a hardcoded guess

# Runtime config:
# --spec <spec> full spec (cursor:<model>), highest priority
# FLOW_REVIEW_BACKEND spec-form ok: cursor:gpt-5.5-high
# FLOW_CURSOR_MODEL fills missing model only (default gpt-5.5-high)
# Cursor folds effort into the model name — no :<effort>, no FLOW_CURSOR_EFFORT.

$FLOWCTL cursor plan-review "$SPEC_ID" --files "$CODE_FILES" --receipt "$RECEIPT_PATH"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK`.**

The runner invokes `cursor-agent -p --output-format json --trust --mode ask` with `cwd=repo_root` (`--mode ask` is read-only).

### Step 2: Update Status

```bash
# Based on verdict
$FLOWCTL spec set-plan-review-status "$SPEC_ID" --status ship --json
# OR
$FLOWCTL spec set-plan-review-status "$SPEC_ID" --status needs_work --json
```

### Step 3: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix plan via `$FLOWCTL spec set-plan`
3. Re-run step 1 (receipt enables session continuity when `mode == "cursor"`)
4. Repeat until SHIP

### Step 4: Receipt

Receipt is written automatically by `flowctl cursor plan-review` when `--receipt` provided.
Format: `{"type":"plan_review","id":"<spec-id>","mode":"cursor","verdict":"<verdict>","session_id":"<uuid>","model":"<model>","spec":"cursor:<model>","timestamp":"..."}`

There is **no `effort` key** — effort is not a Cursor field. The `spec` field is the canonical round-trippable form.

Session resume guard: re-review only resumes the cursor session when the existing receipt at `$RECEIPT_PATH` has `mode == "cursor"`. The first call omits `--resume` and captures Cursor's returned `session_id`; continuations pass `--resume <session_id>`. Cross-backend switches start a fresh session.

---

## RepoPrompt Backend Workflow

Use when `BACKEND="rp"`.

## Phase 1: Read the Plan (RP)

**Run this BEFORE setup-review so the builder gets a real summary.**

**If Flow issue:**
```bash
$FLOWCTL show <id> --json
$FLOWCTL cat <id>
```

Save output for inclusion in review prompt. Compose a 1-2 sentence `REVIEW_SUMMARY` for the setup-review command below.

**Save checkpoint** (protects against context compaction during review):
```bash
$FLOWCTL checkpoint save --spec <id> --json
```
This creates `.flow/.checkpoint-<id>.json` with full state. If compaction occurs during review-fix cycles, restore with `$FLOWCTL checkpoint restore --spec <id>`.

---

### Atomic Setup Block

**Only run ONCE. Uses the summary composed in Phase 1.**

```bash
# Atomic: pick-window + builder (uses REVIEW_SUMMARY from Phase 1)
eval "$($FLOWCTL rp setup-review --repo-root "$REPO_ROOT" --summary "$REVIEW_SUMMARY" --create)"

# Verify we have W and T
if [[ -z "${W:-}" || -z "${T:-}" ]]; then
 echo "<promise>RETRY</promise>"
 exit 0
fi

echo "Setup complete: W=$W T=$T"
```

If this block fails, output `<promise>RETRY</promise>` and stop. Do not improvise.
**Do NOT re-run setup-review** — the builder runs inside it. Re-running = double context build.

---

## Phase 2: Augment Selection (RP)

Builder selects context automatically. Review and add must-haves:

```bash
# See what builder selected
$FLOWCTL rp select-get --window "$W" --tab "$T"

# Always add the spec
$FLOWCTL rp select-add --window "$W" --tab "$T" .flow/specs/<spec-id>.md

# Always add ALL task specs for this spec
for task_spec in .flow/tasks/${SPEC_ID}.*.md; do
 [[ -f "$task_spec" ]] && $FLOWCTL rp select-add --window "$W" --tab "$T" "$task_spec"
done

# Add PRD/architecture docs if found
$FLOWCTL rp select-add --window "$W" --tab "$T" docs/prd.md
```

**Why this matters:** Chat only sees selected files. Reviewer needs both spec AND task specs to check for consistency.

---

## Phase 3: Execute Review (RP)

### Build combined prompt (file composition — no content re-typing)

**Path-persistence rule:** bash vars do NOT survive across prompt turns. Compose these literal unique paths in agent context and type them verbatim in EVERY block that references them (`mktemp` is reserved for paths created and consumed within a single bash block):

- Prompt file: `${TMPDIR:-/tmp}/flow-plan-review-prompt-<spec-id>-<agent-chosen 4-char suffix>.md`
- Response file: `${TMPDIR:-/tmp}/flow-plan-review-response-<spec-id>-<suffix>.md`

Build the prompt by deterministic composition — redirect command output into the file, never paste it into a heredoc. Only cheap **scalar** slots (`[USER'S FOCUS AREAS]`) are filled inline while typing the quoted heredocs below; multi-line command output is always appended via redirection.

```bash
PROMPT_FILE="${TMPDIR:-/tmp}/flow-plan-review-prompt-<spec-id>-<suffix>.md" # literal path

# 1. Builder handoff — captured via redirection, never re-typed
$FLOWCTL rp prompt-get --window "$W" --tab "$T" > "$PROMPT_FILE"

# 2. Static header (quoted heredoc — no shell expansion)
cat >> "$PROMPT_FILE" << 'EOF'

---

## IMPORTANT: File Contents
RepoPrompt includes the actual source code of selected files in a `<file_contents>` XML section at the end of this message. You MUST:
1. Locate the `<file_contents>` section
2. Read and analyze the actual source code within it
3. Base your review on the code, not summaries or descriptions

If you cannot find `<file_contents>`, ask for the files to be re-attached before proceeding.

## Plan Under Review
EOF

# 3. Plan under review — appended via redirection, never re-typed
$FLOWCTL show "$SPEC_ID" >> "$PROMPT_FILE"

# 4. Review criteria (static, quoted heredoc; [USER'S FOCUS AREAS] is a scalar slot
# filled inline while typing this block)
cat >> "$PROMPT_FILE" << 'EOF'

## Review Focus
[USER'S FOCUS AREAS]

## Review Scope

You are reviewing:
1. **Spec** - The high-level plan
2. **Task specs** - Individual task breakdowns

**CRITICAL**: Check for consistency between spec and tasks. Flag if:
- Task specs contradict or miss spec requirements
- Task acceptance criteria don't align with spec acceptance criteria
- Task approaches would need to change based on spec design decisions
- Spec mentions states/enums/types that tasks don't account for

## Review Criteria

Conduct a John Carmack-level review:

1. **Completeness** - All requirements covered? Missing edge cases?
2. **Feasibility** - Technically sound? Dependencies clear?
3. **Parallelizability** - Do independent tasks touch disjoint files? Flag overlapping file scopes that will cause merge conflicts.
4. **Clarity** - Specs unambiguous? Acceptance criteria testable?
5. **Architecture** - Right abstractions? Clean boundaries?
6. **Risks** - Blockers identified? Security gaps? Mitigation?
7. **Scope** - Right-sized? Over/under-engineering?
8. **Task sizing** - M tasks preferred. Flag over-splitting: 7+ tasks? Sequential S tasks that should be combined?
9. **Testability** - How will we verify this works?
10. **Consistency** - Do task specs align with spec?
11. **Vocabulary** - [Include ONLY when `flowctl glossary list --json` reports `total_terms > 0`: "Canonical vocabulary lives in GLOSSARY.md — flag specs/tasks that contradict defined terms." Omit this line otherwise.]

**Also explicitly verify (commonly-missed):** a stated **test strategy**; **observability** (logging/metrics/progress) for any async/batch work; each task **sized for one iteration and correctly ordered** by dependency; and stated **non-functional requirements** (performance, security, privacy).

## Protected artifacts
NEVER recommend deleting / gitignoring / removing these committed pipeline paths (flag bad CONTENT inside them, never their existence): `.flow/*`, `.flow/bin/*`, `.flow/memory/*`, `.flow/specs/*.md`, `.flow/tasks/*.md`, `docs/plans/*`, `docs/solutions/*`, `scripts/ralph/*`. Discard any such finding during synthesis; emit a `Protected-path filter:` count when any dropped.

## Output Format

For each issue:
- **Severity**: Critical / Major / Minor / Nitpick
- **Location**: Which task or section (e.g., "fn-1.3 Description" or "Spec Acceptance #2")
- **Problem**: What's wrong
- **Suggestion**: How to fix

After the issues list, emit a `Protected-path filter:` line tallying findings dropped by the protected-path filter (omit when nothing was dropped).

**REQUIRED**: You MUST end your response with exactly one verdict tag. This is mandatory:
`<verdict>SHIP</verdict>` or `<verdict>NEEDS_WORK</verdict>` or `<verdict>MAJOR_RETHINK</verdict>`

Do NOT skip this tag. The automation depends on it.
EOF
```

### Send to RepoPrompt (single-entry response)

**fn-90 R5 — deterministic cap gate (run BEFORE every review dispatch, including this first one):**

```bash
$FLOWCTL review-rounds increment <SPEC_ID> --kind plan --json
```

At the cap this refuses with an `ESCALATE:` marker + exit 4. That is NOT a retryable error: do NOT dispatch the review, do NOT retry — surface the ESCALATE message to the caller and stop (Ralph/autonomous: NEEDS_HUMAN). Only proceed to `chat-send` when the increment succeeds.

Redirect the review response to the literal response file — it must enter context exactly ONCE, via a single Read of that file (command substitution + `echo` would be the second copy; redirection keeps stdout out of context entirely):

```bash
# Re-declare BOTH literal paths — this may run as a separate prompt turn from the
# build block, and bash vars do not survive across prompt turns (type them verbatim)
PROMPT_FILE="${TMPDIR:-/tmp}/flow-plan-review-prompt-<spec-id>-<suffix>.md" # same literal path from the build block
RESPONSE_FILE="${TMPDIR:-/tmp}/flow-plan-review-response-<spec-id>-<suffix>.md" # literal path

$FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file "$PROMPT_FILE" --new-chat --chat-name "Plan Review: <SPEC_ID>" > "$RESPONSE_FILE"

VERDICT="$(tr -d '\r' < "$RESPONSE_FILE" \
 | grep -oE '<verdict>(SHIP|NEEDS_WORK|MAJOR_RETHINK)</verdict>' \
 | tail -n 1 \
 | sed -E 's#</?verdict>##g')"

if [[ -z "$VERDICT" ]]; then
 echo "No verdict tag found in response"
 echo "<promise>RETRY</promise>"
 exit 0
fi
echo "VERDICT=$VERDICT"
```

**WAIT** for response. Takes 1-5+ minutes.

**Single-entry rule:** after this block, Read the response file ONCE (Read tool, literal path). That render IS the findings context — it feeds parsing and the fix loop. Do NOT `echo`/`cat` the response; verdict extraction greps the file directly.

---

## Phase 4: Receipt + Status (RP)

### Write receipt (if REVIEW_RECEIPT_PATH set)

```bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
 ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
 mkdir -p "$(dirname "$REVIEW_RECEIPT_PATH")"
 cat > "$REVIEW_RECEIPT_PATH" <<EOF
{"type":"plan_review","id":"<SPEC_ID>","mode":"rp","verdict":"$VERDICT","timestamp":"$ts"}
EOF
 echo "REVIEW_RECEIPT_WRITTEN: $REVIEW_RECEIPT_PATH"
fi
```

### Update status

```bash
# If SHIP (convergence — reset the fn-90 R5 deterministic cap counter too)
$FLOWCTL spec set-plan-review-status <SPEC_ID> --status ship --json
$FLOWCTL review-rounds reset <SPEC_ID> --kind plan --json

# If NEEDS_WORK or MAJOR_RETHINK
$FLOWCTL spec set-plan-review-status <SPEC_ID> --status needs_work --json
```

If no verdict tag, output `<promise>RETRY</promise>` and stop.

---

## Fix Loop (RP)

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is production-grade world-class software and architecture. Never use the plain-text numbered prompt in this loop.**

**CRITICAL: You MUST fix the plan BEFORE re-reviewing. Never re-review without making changes.**

**MAJOR_RETHINK is NOT a fix-loop input.** `MAJOR_RETHINK` is a valid verdict tag, but it means the *plan/approach* is wrong — not something to patch finding-by-finding. Do NOT enter the fix loop on it. Escalate immediately: surface the reviewer's rationale to the caller and stop with a typed **`BLOCKED: DESIGN_CONFLICT`** (Ralph mode: output `<promise>RETRY</promise>`). A re-plan is a human decision, never an ad-hoc patch. Only `NEEDS_WORK` drives the loop below.

**MAX ITERATIONS**: Limit fix+re-review cycles to **${MAX_REVIEW_ITERATIONS:-4}** iterations (default 4, configurable in Ralph's config.env). If still NEEDS_WORK after max rounds, output `<promise>RETRY</promise>` and stop — let the next Ralph iteration start fresh. **The cap is now ALSO enforced deterministically by flowctl (fn-90 R5): on codex/copilot/cursor each `flowctl <backend> plan-review` dispatch increments a cumulative spec-scoped counter (`plan_review_rounds`) internally; on rp — which dispatches via `rp chat-send` — this workflow calls `flowctl review-rounds increment <spec-id> --kind plan` before every dispatch (same counter). Either surface REFUSES at the cap with an `ESCALATE:` marker + exit 4. The flowctl counter survives across fresh `/flow-next:plan-review` invocations, so a caller-side "re-invoke until SHIP" outer loop can no longer reset the cap by re-entering — it resets ONLY on a SHIP verdict or an explicit re-plan (`flowctl spec reset-review-rounds <spec-id>`), never on a fresh invocation or a spec edit.**

If verdict is NEEDS_WORK:

1. **Parse issues** - Extract ALL issues by severity (Critical → Major → Minor)
2. **Fix the spec** - Address each issue.
3. **Update spec in flowctl** (MANDATORY before re-review):
 ```bash
 # Option A: stdin heredoc (preferred, no temp file)
 $FLOWCTL spec set-plan <SPEC_ID> --file - --json <<'EOF'
 <updated spec content>
 EOF

 # Option B: temp file (if content has single quotes) — literal unique path
 # per the path-persistence rule
 $FLOWCTL spec set-plan <SPEC_ID> --file "${TMPDIR:-/tmp}/flow-plan-review-updated-plan-<spec-id>-<suffix>.md" --json
 ```
 **If you skip this step and re-review with same content, reviewer will return NEEDS_WORK again.**

 **Recovery**: If context compaction occurred, restore from checkpoint first:
 ```bash
 $FLOWCTL checkpoint restore --spec <SPEC_ID> --json
 ```

4. **Sync affected task specs** - If spec changes affect task specs, update them:
 ```bash
 $FLOWCTL task set-spec <TASK_ID> --file - --json <<'EOF'
 <updated task spec content>
 EOF
 ```
 Task specs need updating when spec changes affect:
 - State/enum values referenced in tasks
 - Acceptance criteria that tasks implement
 - Approach/design decisions tasks depend on
 - Lock/retry/error handling semantics
 - API signatures or type definitions

5. **Request re-review** (only AFTER steps 3-4):

 **IMPORTANT**: Do NOT re-add files already in the selection. RepoPrompt auto-refreshes
 file contents on every message. Only use `select-add` for NEW files created during fixes:
 ```bash
 # Only if fixes created new files not in original selection
 if [[ -n "$NEW_FILES" ]]; then
 $FLOWCTL rp select-add --window "$W" --tab "$T" $NEW_FILES
 fi
 ```

 Then send re-review request (NO --new-chat, stay in same chat).

 **CRITICAL: Do NOT summarize fixes.** RP auto-refreshes file contents - reviewer sees your changes automatically. Just request re-review. Any summary wastes tokens and duplicates what reviewer already sees.

 Redirect the re-review response to the SAME literal response file from Phase 3 (overwrite), then Read it once — the single-entry rule applies to every round.

 **fn-90 R5 cap gate first** — increment before EVERY re-review dispatch; exit 4 = cap reached → do NOT dispatch, surface the ESCALATE message and stop (never retry):

 ```bash
 $FLOWCTL review-rounds increment <SPEC_ID> --kind plan --json
 ```

 ```bash
 cat > "${TMPDIR:-/tmp}/flow-plan-review-rereview-<spec-id>-<suffix>.md" << 'EOF'
 Issues addressed. Please re-review.

 **REQUIRED**: End with `<verdict>SHIP</verdict>` or `<verdict>NEEDS_WORK</verdict>` or `<verdict>MAJOR_RETHINK</verdict>`
 EOF

 $FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file "${TMPDIR:-/tmp}/flow-plan-review-rereview-<spec-id>-<suffix>.md" > "${TMPDIR:-/tmp}/flow-plan-review-response-<spec-id>-<suffix>.md"
 ```

 Re-extract the verdict from the response file (same grep as Phase 3), then Read the file once for the next round's findings.
6. **Repeat** until Ship

**Anti-pattern**: Re-adding already-selected files before re-review. RP auto-refreshes; re-adding can cause issues.

**Anti-pattern**: Re-reviewing without calling `spec set-plan` first. This wastes reviewer time and loops forever.

**Anti-pattern**: Updating spec without syncing affected task specs. Causes reviewer to flag consistency issues again.

---

## Anti-patterns

**All backends:**
- **Reviewing yourself** - You coordinate; the backend reviews
- **No receipt** - If REVIEW_RECEIPT_PATH is set, you MUST write receipt
- **Ignoring verdict** - Must extract and act on verdict tag
- **Mixing backends** - Stick to one backend for the entire review session

**RP backend only:**
- **Calling builder directly** - Must use `setup-review` which wraps it
- **Skipping setup-review** - Window selection MUST happen via this command
- **Hard-coding window IDs** - Never write `--window 1`

**Codex backend only:**
- **Using `--last` flag** - Conflicts with parallel usage; use `--receipt` instead
- **Direct codex calls** - Must use `flowctl codex` wrappers

**Copilot backend only:**
- **Direct copilot calls** - Must use `flowctl copilot` wrappers
- **Inventing `--model`/`--effort` CLI flags** - Use `--spec` for a full backend:model:effort value, or `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars to fill individual fields
- **Using `--continue`** - Conflicts with parallel usage; session resume uses `--resume=<uuid>` under the hood via `--receipt`
- **Assuming cross-backend session continuity** - Resume only works when prior receipt has `mode == "copilot"`

**Cursor backend only:**
- **Direct cursor-agent calls** - Must use `flowctl cursor` wrappers
- **Inventing a `--model` CLI flag** - Use `--spec` for a full `cursor:<model>` value, or the `FLOW_CURSOR_MODEL` env var to fill the model
- **Passing an effort** - Cursor has no effort field; `cursor:<model>:<effort>` is rejected. Pick a model whose name already encodes the effort
- **Fabricating a first-call `--resume` id** - The first call omits `--resume`; persist Cursor's returned `session_id` and resume with that via `--receipt`
- **Assuming cross-backend session continuity** - Resume only works when prior receipt has `mode == "cursor"`
