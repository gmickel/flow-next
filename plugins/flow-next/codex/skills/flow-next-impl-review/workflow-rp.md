# Implementation Review Workflow — RepoPrompt Backend

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

Use when `BACKEND="rp"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, `REPO_ROOT`, and (optionally) `TASK_ID` / `BASE_COMMIT`.

## Phase 1: Identify Changes (RP)

**Run this BEFORE setup-review so the builder gets a real summary.**

```bash
BRANCH="$(git branch --show-current)"

# Use BASE_COMMIT from arguments if provided (task-scoped review)
# Otherwise fall back to main/master (full branch review)
if [[ -z "$BASE_COMMIT" ]]; then
 DIFF_BASE="main"
 git rev-parse main >/dev/null 2>&1 || DIFF_BASE="master"
else
 DIFF_BASE="$BASE_COMMIT"
fi

git log ${DIFF_BASE}..HEAD --oneline
CHANGED_FILES="$(git diff ${DIFF_BASE}..HEAD --name-only)"
git diff ${DIFF_BASE}..HEAD --stat
```

Save:
- Branch name
- Changed files list
- Commit summary
- DIFF_BASE (for reference in review prompt)

Compose a 1-2 sentence `REVIEW_SUMMARY` describing the changes for the setup-review command below.

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

# Add ALL changed files
for f in $CHANGED_FILES; do
 $FLOWCTL rp select-add --window "$W" --tab "$T" "$f"
done

# Add task spec if known
$FLOWCTL rp select-add --window "$W" --tab "$T" .flow/specs/<task-id>.md
```

**Why this matters:** Chat only sees selected files.

---

## Phase 3: Execute Review (RP)

### Build combined prompt (file composition — no content re-typing)

**Path-persistence rule:** bash vars do NOT survive across prompt turns. Compose these literal unique paths in agent context and type them verbatim in EVERY block that references them (`mktemp` is reserved for paths created and consumed within a single bash block):

- Prompt file: `${TMPDIR:-/tmp}/flow-impl-review-prompt-<task-id-or-branch-slug>-<agent-chosen 4-char suffix>.md`
- Response file: `${TMPDIR:-/tmp}/flow-impl-review-response-<task-id-or-branch-slug>-<suffix>.md`

Build the prompt by deterministic composition — redirect command output into the file, never paste it into a heredoc. Only cheap **scalar** slots (branch, file list, commit summary, focus areas — values you already hold from Phase 1) are filled inline while typing the quoted heredocs below; multi-line command output is always appended via redirection.

```bash
PROMPT_FILE="${TMPDIR:-/tmp}/flow-impl-review-prompt-<task-id-or-branch-slug>-<suffix>.md" # literal path

# 1. Builder handoff — captured via redirection, never re-typed
$FLOWCTL rp prompt-get --window "$W" --tab "$T" > "$PROMPT_FILE"

# 2. Static header (quoted heredoc — no shell expansion; fill the scalar
# [BRACKET] slots inline while typing this block)
cat >> "$PROMPT_FILE" << 'EOF'

---

## IMPORTANT: File Contents
RepoPrompt includes the actual source code of selected files in a `<file_contents>` XML section at the end of this message. You MUST:
1. Locate the `<file_contents>` section
2. Read and analyze the actual source code within it
3. Base your review on the code, not summaries or descriptions

If you cannot find `<file_contents>`, ask for the files to be re-attached before proceeding.

## Changes Under Review
Branch: [BRANCH_NAME]
Files: [LIST CHANGED FILES]
Commits: [COMMIT SUMMARY]

## Original Spec
EOF

# 3. Task spec — appended via redirection, never re-typed (skip when no task id)
[[ -n "$TASK_ID" ]] && $FLOWCTL show "$TASK_ID" >> "$PROMPT_FILE"

# 4. Review criteria (static, quoted heredoc; [USER'S FOCUS AREAS] is a scalar slot)
cat >> "$PROMPT_FILE" << 'EOF'

## Review Focus
[USER'S FOCUS AREAS]

## Review Criteria

Conduct a John Carmack-level review:

1. **Correctness** - Matches spec? Logic errors?
2. **Simplicity** - Simplest solution? Over-engineering?
3. **DRY** - Duplicated logic? Existing patterns?
4. **Architecture** - Data flow? Clear boundaries?
5. **Edge Cases** - Failure modes? Race conditions?
6. **Tests** - Adequate coverage? Testing behavior?
7. **Security** - Injection? Auth gaps?
8. **Vocabulary** - [Include ONLY when `flowctl glossary list --json` reports `total_terms > 0`: "Canonical vocabulary lives in GLOSSARY.md — flag changes that contradict defined terms." Omit this line otherwise.]

## Code-smell baseline (always-on, judgement calls — repo standards override; skip what tooling enforces)
Beyond correctness, name any of these you spot and quote the hunk (each a heuristic, never a hard violation):
Long Method · Large Class · Long Parameter List · Duplicated Code · Feature Envy (uses another object's data more than its own) · Data Clumps (same values always passed together — wants a type) · Primitive Obsession (bare primitives where a small type belongs) · Speculative Generality.

## Scenario Exploration (for changed code only)

Walk through these scenarios mentally for any new/modified code paths:

- [ ] Happy path - Normal operation with valid inputs
- [ ] Invalid inputs - Null, empty, malformed data
- [ ] Boundary conditions - Min/max values, empty collections
- [ ] Concurrent access - Race conditions, deadlocks
- [ ] Network issues - Timeouts, partial failures
- [ ] Resource exhaustion - Memory, disk, connections
- [ ] Security attacks - Injection, overflow, DoS vectors
- [ ] Data corruption - Partial writes, inconsistency
- [ ] Cascading failures - Downstream service issues

Only flag issues that apply to the **changed code** - not pre-existing patterns.

## Requirements coverage (only if the spec has R-IDs like `- **R1:** ...`)
If R-IDs are present, read the epic's `## Acceptance Criteria` (tolerate legacy `## Acceptance` / `## Acceptance criteria`) and emit:
| R-ID | Status | Evidence |
Status ∈ met / partial / not-addressed / deferred. After the table emit `Unaddressed R-IDs: [...]`. A non-deferred `not-addressed` R-ID forces NEEDS_WORK. If no R-IDs anywhere, skip this block entirely.

## Confidence (pick ONE anchor; no interpolation)
- **100** — definitive from code alone (mechanical: off-by-one, wrong type, swapped args).
- **75** — full path traced; a normal caller hits it; reproducible from the diff.
- **50** — depends on conditions visible but not confirmable here (e.g. can this be null? callers not in diff).
- **25** — needs runtime conditions with no direct evidence.
- **0** — speculative; don't file.
Suppression gate: drop findings below 75, EXCEPT P0 at 50+ (those survive). Emit a `Suppressed findings:` count when any dropped.

## Introduced vs pre-existing
Classify each finding: **introduced** (this diff caused or newly exposed it) or **pre_existing** (already on base, untouched — a finding on an unchanged line is pre_existing by default; confirm with `git blame`/base-file read when cheap).
Verdict gate: only `introduced` findings affect the verdict — a review whose survivors are all `pre_existing` ships. List pre-existing under `## Pre-existing issues (not blocking this verdict)` as `[sev, confidence N, introduced=false] file:line — summary`; never drop them. End with `Classification counts: N introduced, M pre_existing.`

## Protected artifacts
NEVER recommend deleting / gitignoring / removing these committed pipeline paths (flag bad CONTENT inside them, never their existence): `.flow/*`, `.flow/bin/*`, `.flow/memory/*`, `.flow/specs/*.md`, `.flow/tasks/*.md`, `docs/plans/*`, `docs/solutions/*`, `scripts/ralph/*`. Discard any such finding during synthesis; emit a `Protected-path filter:` count when any dropped.

## Output Format

For each surviving `introduced` finding:
- **Severity**: Critical / Major / Minor / Nitpick (P0 / P1 / P2 / P3 accepted)
- **Confidence**: 0 / 25 / 50 / 75 / 100 (one of the five discrete anchors)
- **Classification**: introduced
- **File:Line**: Exact location
- **Problem**: What's wrong
- **Suggestion**: How to fix

Then list each `pre_existing` finding under a separate `## Pre-existing issues (not blocking this verdict)` heading using the compact form `[severity, confidence N, introduced=false] file:line — summary`.

After the findings, add (only when applicable): the `## Requirements coverage` table + `Unaddressed R-IDs:` line, and the `Suppressed findings:` / `Classification counts:` / `Protected-path filter:` tally lines named above.

**REQUIRED**: You MUST end your response with exactly one verdict tag. This is mandatory:
`<verdict>SHIP</verdict>` (no blocking `introduced` findings, all R-IDs met or deferred) or `<verdict>NEEDS_WORK</verdict>` (introduced findings or unaddressed R-IDs to fix) or `<verdict>MAJOR_RETHINK</verdict>`

Do NOT skip this tag. The automation depends on it.
EOF
```

### Send to RepoPrompt (single-entry response)

Redirect the review response to the literal response file — it must enter context exactly ONCE, via a single Read of that file (command substitution + `echo` would be the second copy; redirection keeps stdout out of context entirely):

```bash
# Re-declare BOTH literal paths — this may run as a separate prompt turn from the
# build block, and bash vars do not survive across prompt turns (type them verbatim)
PROMPT_FILE="${TMPDIR:-/tmp}/flow-impl-review-prompt-<task-id-or-branch-slug>-<suffix>.md" # same literal path from the build block
RESPONSE_FILE="${TMPDIR:-/tmp}/flow-impl-review-response-<task-id-or-branch-slug>-<suffix>.md" # literal path

$FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file "$PROMPT_FILE" --new-chat --chat-name "Impl Review: $BRANCH" > "$RESPONSE_FILE"

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

**Single-entry rule:** after this block, Read the response file ONCE (Read tool, literal path). That render IS the findings context — it feeds parsing and the fix loop. Do NOT `echo`/`cat` the response; verdict and receipt tallies grep the file directly.

---

## Phase 4: Receipt + Status (RP)

### Write receipt (if REVIEW_RECEIPT_PATH set)

```bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
 ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
 mkdir -p "$(dirname "$REVIEW_RECEIPT_PATH")"

 # Same literal response file from Phase 3 (path-persistence rule — type it verbatim)
 RESPONSE_FILE="${TMPDIR:-/tmp}/flow-impl-review-response-<task-id-or-branch-slug>-<suffix>.md"

 # Optional: capture suppression-gate tally (fn-29.3).
 # Reviewer emits a line like "Suppressed findings: 3 at anchor 50, 7 at anchor 25, 2 at anchor 0."
 SUPPRESSED_JSON="$(grep -iE '^[>*_` ]*suppressed findings[ *_`]*:' "$RESPONSE_FILE" \
 | head -n 1 \
 | sed -E 's/^[^:]+:[[:space:]]*//; s/\.$//' \
 | awk '
 BEGIN { first=1; printf "{" }
 {
 n=split($0, parts, /,[[:space:]]*/)
 for (i=1; i<=n; i++) {
 if (match(parts[i], /([0-9]+)[[:space:]]+at[[:space:]]+anchor[[:space:]]+(0|25|50|75|100)/, m)) {
 if (!first) printf ","
 printf "\"%s\":%s", m[2], m[1]
 first=0
 }
 }
 }
 END { printf "}" }')"

 # Optional: capture introduced vs pre_existing classification tally (fn-29.4).
 # Reviewer emits a line like "Classification counts: 2 introduced, 4 pre_existing."
 # Uses portable grep -Eio so this works on BSD awk / mawk / gawk alike.
 CLASSIFICATION_LINE="$(grep -iE '^[>*_` ]*classification counts[ *_`]*:' "$RESPONSE_FILE" \
 | head -n 1 \
 | sed -E 's/^[^:]+:[[:space:]]*//; s/\.$//')"
 INTRODUCED_COUNT=""
 PRE_EXISTING_COUNT=""
 if [[ -n "$CLASSIFICATION_LINE" ]]; then
 INTRODUCED_COUNT="$(printf '%s' "$CLASSIFICATION_LINE" \
 | grep -Eio '[0-9]+[[:space:]]+introduced' \
 | head -n 1 \
 | grep -Eo '^[0-9]+')"
 PRE_EXISTING_COUNT="$(printf '%s' "$CLASSIFICATION_LINE" \
 | grep -Eio '[0-9]+[[:space:]]+pre[-_ ]?existing' \
 | head -n 1 \
 | grep -Eo '^[0-9]+')"
 # Default the missing bucket to 0 when the other is present
 if [[ -n "$INTRODUCED_COUNT" || -n "$PRE_EXISTING_COUNT" ]]; then
 INTRODUCED_COUNT="${INTRODUCED_COUNT:-0}"
 PRE_EXISTING_COUNT="${PRE_EXISTING_COUNT:-0}"
 fi
 fi

 # Optional: capture unaddressed R-IDs (fn-29.2).
 # Reviewer emits `Unaddressed R-IDs: [R3, R5]` (or `[]` / `none` for empty).
 # Absent line => legacy spec (no R-IDs) — leave field off the receipt entirely.
 UNADDRESSED_JSON=""
 UNADDRESSED_LINE="$(grep -iE '^[>*_` ]*unaddressed([[:space:]]+r[-_ ]?ids?)?[ *_`]*:' "$RESPONSE_FILE" \
 | head -n 1 \
 | sed -E 's/^[^:]+:[[:space:]]*//; s/[[:space:]]*$//; s/\.$//')"
 if [[ -n "$UNADDRESSED_LINE" ]]; then
 # Strip surrounding brackets/quotes; treat "none"/"n/a"/"" as empty list.
 normalized="$(printf '%s' "$UNADDRESSED_LINE" | sed -E 's/^[[:space:]]*\[|\][[:space:]]*$//g; s/[[:space:]]+//g')"
 lower="$(printf '%s' "$normalized" | tr '[:upper:]' '[:lower:]')"
 if [[ "$lower" == "none" || "$lower" == "n/a" || -z "$lower" ]]; then
 UNADDRESSED_JSON="[]"
 else
 # Extract R-ID tokens (R followed by digits), de-dup preserving order.
 rids="$(printf '%s' "$UNADDRESSED_LINE" \
 | grep -oE '\bR[0-9]+\b' \
 | awk '!seen[$0]++')"
 if [[ -z "$rids" ]]; then
 UNADDRESSED_JSON="[]"
 else
 UNADDRESSED_JSON="$(printf '%s' "$rids" \
 | awk 'BEGIN{printf "["} {printf (NR>1?",":"") "\"" $0 "\""} END{printf "]"}')"
 fi
 fi
 fi

 # Build receipt; inject optional fn-29.2/fn-29.3/fn-29.4 signals only when present
 EXTRA_FIELDS=""
 if [[ -n "$SUPPRESSED_JSON" && "$SUPPRESSED_JSON" != "{}" ]]; then
 EXTRA_FIELDS+=",\"suppressed_count\":$SUPPRESSED_JSON"
 fi
 if [[ -n "$INTRODUCED_COUNT" && -n "$PRE_EXISTING_COUNT" ]]; then
 EXTRA_FIELDS+=",\"introduced_count\":$INTRODUCED_COUNT,\"pre_existing_count\":$PRE_EXISTING_COUNT"
 fi
 if [[ -n "$UNADDRESSED_JSON" ]]; then
 EXTRA_FIELDS+=",\"unaddressed\":$UNADDRESSED_JSON"
 fi

 cat > "$REVIEW_RECEIPT_PATH" <<EOF
{"type":"impl_review","id":"<TASK_ID>","mode":"rp","verdict":"$VERDICT"$EXTRA_FIELDS,"timestamp":"$ts"}
EOF
 echo "REVIEW_RECEIPT_WRITTEN: $REVIEW_RECEIPT_PATH"
fi
```

If no verdict tag in response, output `<promise>RETRY</promise>` and stop.

## Optional phases (gated by flags)

When the corresponding flag is set, run these phases from [workflow-common.md](workflow-common.md) — the dispatch matches the `rp` case in each phase (same-chat session continuity is automatic; do NOT pass `--new-chat`):

- `--deep` → "Deep-Pass Phase" (Step D.1 → D.5) — render pass prompts from [deep-passes.md](deep-passes.md) and send via `rp chat-send`
- `--validate` → "Validator Pass" (Step V.1 → V.4) — render validator prompt from [validate-pass.md](validate-pass.md) and send via `rp chat-send`
- `--interactive` → "Interactive Walkthrough Phase" (Step W.1 → W.5) — see [walkthrough.md](walkthrough.md)

See [workflow-common.md](workflow-common.md) "Phase ordering & flag-combination matrix" for the order when multiple flags are set.

---

## Fix Loop (RP)

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is production-grade world-class software and architecture. Never use the plain-text numbered prompt in this loop.**

**CRITICAL: You MUST fix the code BEFORE re-reviewing. Never re-review without making changes.**

**MAX ITERATIONS**: Limit fix+re-review cycles to **${MAX_REVIEW_ITERATIONS:-4}** iterations (default 4, configurable in Ralph's config.env). If still NEEDS_WORK after max rounds, output `<promise>RETRY</promise>` and stop — let the next Ralph iteration start fresh.

If verdict is NEEDS_WORK:

1. **Parse issues** - Extract ALL issues by severity (Critical → Major → Minor) from the response-file Read
2. **Snapshot the pre-fix state** (BEFORE touching any file — literal paths per the path-persistence rule):
 ```bash
 git status --porcelain > "${TMPDIR:-/tmp}/flow-impl-review-snap-pre-<task-id-or-branch-slug>-<suffix>.txt"
 ```
3. **Fix the code** - Address each issue in order
4. **Run tests/lints** - Verify fixes don't break anything
5. **Commit fixes with snapshot-scoped staging** (MANDATORY before re-review — NEVER blanket-stage with `git add --all`):

 **Pre-dirty collision rule:** if a path you edited during the fix already appears in the PRE snapshot, do NOT stage it — path-level staging cannot separate pre-existing hunks from fix hunks. Surface the collision, defer/escalate that finding (report it in the re-review request or final summary), and never sweep pre-existing changes into a review-fix commit.

 ```bash
 SNAP_PRE="${TMPDIR:-/tmp}/flow-impl-review-snap-pre-<task-id-or-branch-slug>-<suffix>.txt" # same literal path from step 2
 SNAP_POST="${TMPDIR:-/tmp}/flow-impl-review-snap-post-<task-id-or-branch-slug>-<suffix>.txt"
 git status --porcelain > "$SNAP_POST"

 # Stage ONLY paths that appear in the post-fix snapshot but not the pre-fix one
 # (covers modified, untracked, deleted, renamed — rename lines stage the new path).
 # Paths already dirty pre-fix are excluded automatically (collision rule above).
 extract_paths() { cut -c4- "$1" | sed 's/^"\(.*\)"$/\1/; s/.* -> //' | sort -u; }
 comm -13 <(extract_paths "$SNAP_PRE") <(extract_paths "$SNAP_POST") \
 | while IFS= read -r p; do git add -- "$p"; done

 if git diff --cached --quiet; then
 echo "No stageable fix paths (all fixer-touched paths collided with pre-existing dirty state) — escalate; do NOT re-review without committed changes"
 else
 git commit -m "fix: address review feedback"
 fi
 ```
 **If you skip this and re-review without committing changes, reviewer will return NEEDS_WORK again.**

6. **Request re-review** (only AFTER step 5):

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

 Redirect the re-review response to the SAME literal response file from Phase 3 (overwrite), then Read it once — the single-entry rule applies to every round:

 ```bash
 cat > "${TMPDIR:-/tmp}/flow-impl-review-rereview-<task-id-or-branch-slug>-<suffix>.md" << 'EOF'
 Issues addressed. Please re-review.

 **REQUIRED**: End with `<verdict>SHIP</verdict>` or `<verdict>NEEDS_WORK</verdict>` or `<verdict>MAJOR_RETHINK</verdict>`
 EOF

 $FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file "${TMPDIR:-/tmp}/flow-impl-review-rereview-<task-id-or-branch-slug>-<suffix>.md" > "${TMPDIR:-/tmp}/flow-impl-review-response-<task-id-or-branch-slug>-<suffix>.md"
 ```

 Re-extract the verdict from the response file (same grep as Phase 3), then Read the file once for the next round's findings.
7. **Repeat** until Ship

**Anti-pattern**: Re-adding already-selected files before re-review. RP auto-refreshes; re-adding can cause issues.

---

## Anti-patterns (RP backend)

- **Calling builder directly** - Must use `setup-review` which wraps it
- **Skipping setup-review** - Window selection MUST happen via this command
- **Hard-coding window IDs** - Never write `--window 1`
- **Missing changed files** - Add ALL changed files to selection
- **Blanket staging (`git add --all`) in the fix loop** - Sweeps pre-existing dirty paths into review-fix commits; use the snapshot-scoped staging
- **Re-typing command output into heredocs** - Handoff/spec/response content moves by redirection (`>`/`>>`) only; echoing a captured response is a duplicate emission
