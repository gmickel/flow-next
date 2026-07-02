# Spec Completion Review Workflow — RepoPrompt Backend

Use when `BACKEND="rp"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, `REPO_ROOT`, and `SPEC_ID`.

## Phase 1: Gather Context (RP)

**Run this BEFORE setup-review so the builder gets a real summary.**

```bash
BRANCH="$(git branch --show-current)"

# Get spec and task list (spec body enters context once here — used to compose
# REVIEW_SUMMARY; the Phase 3 prompt file gets its own copy via redirection)
$FLOWCTL cat "$SPEC_ID"
TASKS_JSON="$($FLOWCTL tasks --spec "$SPEC_ID" --json)"

# Get changed files on branch
DIFF_BASE="main"
git rev-parse main >/dev/null 2>&1 || DIFF_BASE="master"
git log ${DIFF_BASE}..HEAD --oneline
CHANGED_FILES="$(git diff ${DIFF_BASE}..HEAD --name-only)"
git diff ${DIFF_BASE}..HEAD --stat
```

Save:
- Spec ID and spec body
- Task list (IDs and titles)
- Branch name
- Changed files list

Compose a 1-2 sentence `REVIEW_SUMMARY` for the setup-review command below.

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

# Add spec
$FLOWCTL rp select-add --window "$W" --tab "$T" ".flow/specs/$SPEC_ID.md"

# Add all task specs
for task_id in $(echo "$TASKS_JSON" | jq -r '.[].id'); do
  $FLOWCTL rp select-add --window "$W" --tab "$T" ".flow/tasks/$task_id.md"
done

# Add ALL changed files
for f in $CHANGED_FILES; do
  $FLOWCTL rp select-add --window "$W" --tab "$T" "$f"
done
```

**Why this matters:** Chat only sees selected files.

---

## Phase 3: Execute Review (RP)

### Build combined prompt (file composition — no content re-typing)

**Path-persistence rule:** bash vars do NOT survive across tool calls. Compose these literal unique paths in agent context and type them verbatim in EVERY block that references them (`mktemp` is reserved for paths created and consumed within a single bash block):

- Prompt file: `${TMPDIR:-/tmp}/flow-completion-review-prompt-<spec-id>-<agent-chosen 4-char suffix>.md`
- Response file: `${TMPDIR:-/tmp}/flow-completion-review-response-<spec-id>-<suffix>.md`

Build the prompt by deterministic composition — redirect command output into the file, never paste it into a heredoc. Only cheap **scalar** slots (`[SPEC_ID]`, `[BRANCH_NAME]`, task-id list) are filled inline while typing the quoted heredocs below; multi-line command output is always appended via redirection.

```bash
PROMPT_FILE="${TMPDIR:-/tmp}/flow-completion-review-prompt-<spec-id>-<suffix>.md"   # literal path

# 1. Builder handoff — captured via redirection, never re-typed
$FLOWCTL rp prompt-get --window "$W" --tab "$T" > "$PROMPT_FILE"

# 2. Static header (quoted heredoc — no shell expansion; fill the scalar
#    [BRACKET] slots inline while typing this block)
cat >> "$PROMPT_FILE" << 'EOF'

---

## IMPORTANT: File Contents
RepoPrompt includes the actual source code of selected files in a `<file_contents>` XML section at the end of this message. You MUST:
1. Locate the `<file_contents>` section
2. Read and analyze the actual source code within it
3. Base your review on the code, not summaries or descriptions

If you cannot find `<file_contents>`, ask for the files to be re-attached before proceeding.

## Spec Under Review
Spec: [SPEC_ID]
Branch: [BRANCH_NAME]
Tasks: [LIST TASK IDs]

## Spec Body
EOF

# 3. Spec body — appended via redirection, never re-typed
$FLOWCTL cat "$SPEC_ID" >> "$PROMPT_FILE"

# 4. Review criteria (static, quoted heredoc)
cat >> "$PROMPT_FILE" << 'EOF'

## Review Focus: Spec Compliance

This is NOT a code quality review — impl-review handles that per-task.

Your job: Verify the combined implementation delivers everything the spec requires.

### Three-Phase Approach

**Phase 1: Extract Requirements**
Read the spec and list ALL explicit requirements as bullets:
- Features/functionality to implement
- Docs to update (README, API docs, etc.)
- Tests to add
- Config/schema changes
- Any other deliverables

**Phase 2: Verify Implementation**
For each requirement from Phase 1:
- [ ] Is it implemented in the changed files?
- [ ] Is the implementation complete (not partial)?
- [ ] Does it match the spec intent?

**Phase 3: Reverse Coverage (Code → Spec)**
For each new/modified file in the changed files list:
- Identify which spec requirement it serves
- Flag any file that doesn't trace to a spec requirement

If the spec has a `## Requirement coverage` traceability table, use it as the primary reference for mapping files to requirements.

Classification for untraced changes:
- `UNDOCUMENTED_ADDITION` — new functionality not in spec (scope creep)
- `LEGITIMATE_SUPPORT` — refactoring/infrastructure needed to implement a requirement (OK)
- `UNRELATED_CHANGE` — changes outside spec scope (may be accidental)

Report untraced changes but don't auto-reject. UNDOCUMENTED_ADDITION is a flag for acknowledgment, not automatic NEEDS_WORK.

### What to Check
- Requirements that never became tasks (decomposition gaps)
- Requirements partially implemented across tasks (cross-task gaps)
- Scope drift (task marked done without fully addressing spec intent)
- Missing doc updates specified in acceptance criteria
- Scope creep (code changes that don't trace to spec requirements)

### What NOT to Check
- Code style, patterns, architecture (impl-review covers this)
- Test quality (impl-review covers this)
- Performance (impl-review covers this)
- Legitimate refactoring needed to implement requirements (flag as LEGITIMATE_SUPPORT but don't block)

## Requirements coverage (if spec has R-IDs)

If the spec numbers its acceptance criteria like `- **R1:** ...`, `- **R2:** ...`,
produce a per-R-ID coverage table. Read the spec's `## Acceptance` section
(or the legacy `## Acceptance criteria` heading — reviewer MUST tolerate both).
If no R-IDs are present, skip this block entirely — Phase 2 and Phase 3 above
still apply.

This forward coverage (spec → code) is **additive to Phase 3 reverse coverage
(code → spec)**. Both phases feed the final verdict.

For each R-ID, classify status:

| Status | Meaning |
|--------|---------|
| met | Implementation delivers the requirement with appropriate tests/evidence |
| partial | Implementation advances the requirement but leaves gaps |
| not-addressed | Implementation does not advance this requirement at all |
| deferred | Spec explicitly defers this requirement to a later spec/PR |

Report as a markdown table in the review output:

| R-ID | Status | Evidence |
|------|--------|----------|
| R1 | met | src/auth.ts:42 + tests/auth.test.ts:17 |
| R2 | partial | implementation exists but no error-path tests |
| R3 | not-addressed | — |

After the table, emit one line listing every `not-addressed` R-ID that is NOT
explicitly deferred in the spec:

> Unaddressed R-IDs: [R3, R5]

If there are zero unaddressed R-IDs, emit `Unaddressed R-IDs: []` or omit the
line entirely. Deferred R-IDs are never listed here.

**Verdict gate:** any `not-addressed` R-ID that is NOT marked `deferred` in the
spec MUST flip the verdict to `NEEDS_WORK`, regardless of reverse-coverage
findings.

## Confidence calibration

Rate each gap on exactly one of these 5 discrete anchors. Do not use interpolated values (no 33, 80, 90).

| Anchor | Meaning |
|--------|---------|
| 100 | Verifiable from the code alone, zero interpretation. A definitive logic error (off-by-one in a tested algorithm, wrong return type, swapped arguments, clear type error). The bug is mechanical. |
| 75 | Full execution path traced: "input X enters here, takes this branch, reaches line Z, produces wrong result." Reproducible from the code alone. A normal caller will hit it. |
| 50 | Depends on conditions visible but not fully confirmable from this diff — e.g., whether a value can actually be null depends on callers not in the diff. Surfaces only as P0-escape or via soft-bucket routing. |
| 25 | Requires runtime conditions with no direct evidence — specific timing, specific input shapes, specific external state. |
| 0 | Speculative. Not worth filing. |

## Suppression gate

After all gaps/findings are collected:
1. Suppress findings below anchor 75.
2. **Exception:** P0 severity findings at anchor 50+ survive the gate. Critical-but-uncertain issues must not be silently dropped.
3. Report the suppressed count by anchor in a `Suppressed findings` section of the review output.

Example:

> Suppressed findings: 3 at anchor 50, 7 at anchor 25, 2 at anchor 0.

## Introduced vs pre-existing classification

For each gap, classify whether this branch's diff caused it:

- **introduced** — this spec's branch is responsible for the gap (new requirement not implemented, or a requirement this spec was supposed to satisfy and did not)
- **pre_existing** — the gap predates this spec's branch (the requirement was already not satisfied on the base branch; this spec did not touch the relevant code). Pre-existing gaps do not block this verdict.

Evidence methods:
- `git blame <file> <line>` to see when the line was last touched
- Read the base-branch version of the file directly
- Check the spec scope: a gap about an area this spec never claimed to touch is `pre_existing`

**Verdict gate:** only `introduced` gaps affect the verdict. A spec-completion-review whose sole surviving gaps are all `pre_existing` MUST ship.

Pre-existing gaps go under a separate `## Pre-existing issues (not blocking this verdict)` heading:

```
## Pre-existing issues (not blocking this verdict)

- [confidence 75, introduced=false] missing migration docs in README — predates this spec
```

Never delete pre-existing gaps from the report — they stay visible for future prioritization.

## Protected artifacts

The following paths are flow-next / project-pipeline artifacts. Any gap/finding recommending their deletion, gitignore, or removal MUST be discarded during synthesis. Do not flag these paths for cleanup under any circumstances:

- `.flow/*` — flow-next state, specs, tasks, runtime
- `.flow/bin/*` — bundled flowctl
- `.flow/memory/*` — learnings store (pitfalls, conventions, decisions)
- `.flow/specs/*.md` — specs (decision artifacts)
- `.flow/tasks/*.md` — task specs (decision artifacts)
- `docs/plans/*` — plan artifacts (if project uses this convention)
- `docs/solutions/*` — solutions artifacts (if project uses this convention)
- `scripts/ralph/*` — Ralph harness (when present)

These files are intentionally committed. They are the pipeline's state, not clutter. An agent that deletes them destroys the project's planning trail and breaks Ralph autonomous runs.

If you notice genuine issues with content INSIDE these files (e.g., a spec that contradicts itself, a stale runtime value, a memory entry that's wrong), flag the content — not the file's existence.

**Protected-path filter.** Before emitting findings, scan each for recommendations to delete, gitignore, or `rm -rf` any path matching the protected list above. Drop those findings. If you drop any, report the drop count in a `Protected-path filter:` line in the review output (e.g. `Protected-path filter: dropped 2 findings`). Omit the line when nothing was dropped.

## Output Format

**Forward coverage (Spec → Code):** for each `introduced` gap:
- **Requirement**: What the spec says
- **Status**: Missing / Partial / Wrong
- **Confidence**: 0 / 25 / 50 / 75 / 100 (one of the five discrete anchors)
- **Classification**: introduced
- **Evidence**: What you found (or didn't find) in the code

List each `pre_existing` gap under the dedicated non-blocking section above using the compact form `[confidence N, introduced=false] requirement — summary`.

**Reverse coverage (Code → Spec):**
For each untraced change:
- **File**: Changed file path
- **Classification**: UNDOCUMENTED_ADDITION / LEGITIMATE_SUPPORT / UNRELATED_CHANGE
- **Note**: Brief explanation

(Note: the reverse-coverage `Classification` uses untraced-change labels, distinct from the `introduced` / `pre_existing` per-gap classification above.)

After the findings list, emit:
- The `## Requirements coverage` table and `Unaddressed R-IDs:` line (only when the spec uses R-IDs; otherwise skip).
- A `Suppressed findings:` line tallying anchors dropped by the gate (omit when nothing was suppressed).
- A `Classification counts:` line tallying `introduced` vs `pre_existing` gaps, e.g. `Classification counts: 1 introduced, 0 pre_existing.`.
- A `Protected-path filter:` line tallying gaps dropped by the protected-path filter (omit when nothing was dropped).

**REQUIRED**: You MUST end your response with exactly one verdict tag. This is mandatory:
`<verdict>SHIP</verdict>` or `<verdict>NEEDS_WORK</verdict>`

- SHIP: All `introduced` spec requirements are implemented and every R-ID is `met` or `deferred` (pre-existing gaps do not block)
- NEEDS_WORK: One or more `introduced` requirements are missing, partial, or wrong — or any non-deferred R-ID is `not-addressed`

Do NOT skip this tag. The automation depends on it.
EOF
```

**Note:** The scalar bracket slots (`[SPEC_ID]`, `[BRANCH_NAME]`, `[LIST TASK IDs]`) are filled inline while typing the heredoc — they are cheap value substitutions. Multi-line content (handoff, spec body) is NEVER typed by hand; it arrives via the redirections above.

### Send to RepoPrompt and Parse Verdict (single-entry response)

Redirect the review response to the literal response file — it must enter context exactly ONCE, via a single Read of that file (command substitution + `echo` would be the second copy; redirection keeps stdout out of context entirely):

```bash
RESPONSE_FILE="${TMPDIR:-/tmp}/flow-completion-review-response-<spec-id>-<suffix>.md"   # literal path

$FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file "$PROMPT_FILE" --new-chat --chat-name "Spec Completion Review: $SPEC_ID" > "$RESPONSE_FILE"

# Extract verdict tag from the response file
VERDICT="$(tr -d '\r' < "$RESPONSE_FILE" \
  | grep -oE '<verdict>(SHIP|NEEDS_WORK)</verdict>' \
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

**Single-entry rule:** after this block, Read the response file ONCE (Read tool, literal path). That render IS the gaps context — it feeds parsing and the fix loop. Do NOT `echo`/`cat` the response; verdict and receipt tallies grep the file directly.

---

## Phase 4: Receipt + Status (RP)

### Write receipt (if REVIEW_RECEIPT_PATH set)

Receipt written after SHIP verdict (not on NEEDS_WORK):

```bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mkdir -p "$(dirname "$REVIEW_RECEIPT_PATH")"

  # Same literal response file from Phase 3 (path-persistence rule — type it verbatim)
  RESPONSE_FILE="${TMPDIR:-/tmp}/flow-completion-review-response-<spec-id>-<suffix>.md"

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
  # Reviewer emits a line like "Classification counts: 1 introduced, 0 pre_existing."
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
    if [[ -n "$INTRODUCED_COUNT" || -n "$PRE_EXISTING_COUNT" ]]; then
      INTRODUCED_COUNT="${INTRODUCED_COUNT:-0}"
      PRE_EXISTING_COUNT="${PRE_EXISTING_COUNT:-0}"
    fi
  fi

  # Optional: capture unaddressed R-IDs (fn-29.2).
  # Reviewer emits `Unaddressed R-IDs: [R3, R5]` (or `[]` / `none` for empty).
  # Absent line => spec has no R-IDs — leave field off the receipt entirely.
  UNADDRESSED_JSON=""
  UNADDRESSED_LINE="$(grep -iE '^[>*_` ]*unaddressed([[:space:]]+r[-_ ]?ids?)?[ *_`]*:' "$RESPONSE_FILE" \
    | head -n 1 \
    | sed -E 's/^[^:]+:[[:space:]]*//; s/[[:space:]]*$//; s/\.$//')"
  if [[ -n "$UNADDRESSED_LINE" ]]; then
    normalized="$(printf '%s' "$UNADDRESSED_LINE" | sed -E 's/^[[:space:]]*\[|\][[:space:]]*$//g; s/[[:space:]]+//g')"
    lower="$(printf '%s' "$normalized" | tr '[:upper:]' '[:lower:]')"
    if [[ "$lower" == "none" || "$lower" == "n/a" || -z "$lower" ]]; then
      UNADDRESSED_JSON="[]"
    else
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
{"type":"completion_review","id":"$SPEC_ID","mode":"rp","verdict":"SHIP"$EXTRA_FIELDS,"timestamp":"$ts"}
EOF
  echo "REVIEW_RECEIPT_WRITTEN: $REVIEW_RECEIPT_PATH"
fi
```

---

## Fix Loop (RP)

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is complete spec compliance. Never use AskUserQuestion in this loop.**

**CRITICAL: You MUST fix the code BEFORE re-reviewing. Never re-review without making changes.**

**MAX ITERATIONS**: Limit fix+re-review cycles to **${MAX_REVIEW_ITERATIONS:-3}** iterations (default 3, configurable in Ralph's config.env). If still NEEDS_WORK after max rounds, output `<promise>RETRY</promise>` and stop — let the next Ralph iteration start fresh.

If verdict is NEEDS_WORK:

1. **Parse issues** - Extract ALL gaps (missing requirements, partial implementations) from the response-file Read
2. **Snapshot the pre-fix state** (BEFORE touching any file — literal paths per the path-persistence rule):
   ```bash
   git status --porcelain > "${TMPDIR:-/tmp}/flow-completion-review-snap-pre-<spec-id>-<suffix>.txt"
   ```
3. **Fix the code** - Implement missing functionality
4. **Run tests/lints** - Verify fixes don't break anything
5. **Commit fixes with snapshot-scoped staging** (MANDATORY before re-review — NEVER `git add -A`):

   **Pre-dirty collision rule:** if a path you edited during the fix already appears in the PRE snapshot, do NOT stage it — path-level staging cannot separate pre-existing hunks from fix hunks. Surface the collision, defer/escalate that finding (report it in the re-review request or final summary), and never sweep pre-existing changes into a review-fix commit.

   ```bash
   SNAP_PRE="${TMPDIR:-/tmp}/flow-completion-review-snap-pre-<spec-id>-<suffix>.txt"    # same literal path from step 2
   SNAP_POST="${TMPDIR:-/tmp}/flow-completion-review-snap-post-<spec-id>-<suffix>.txt"
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
     git commit -m "fix: address completion review gaps"
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
   cat > "${TMPDIR:-/tmp}/flow-completion-review-rereview-<spec-id>-<suffix>.md" << 'EOF'
   Gaps addressed. Please re-review for spec compliance.

   **REQUIRED**: End with `<verdict>SHIP</verdict>` or `<verdict>NEEDS_WORK</verdict>`
   EOF

   $FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file "${TMPDIR:-/tmp}/flow-completion-review-rereview-<spec-id>-<suffix>.md" > "${TMPDIR:-/tmp}/flow-completion-review-response-<spec-id>-<suffix>.md"
   ```

   Re-extract the verdict from the response file (same grep as Phase 3), then Read the file once for the next round's gaps.
7. **Repeat** until SHIP

**Anti-pattern**: Re-adding already-selected files before re-review. RP auto-refreshes; re-adding can cause issues.

---

## Anti-patterns (RP backend)

- **Calling builder directly** - Must use `setup-review` which wraps it
- **Skipping setup-review** - Window selection MUST happen via this command
- **Hard-coding window IDs** - Never write `--window 1`
- **Missing task specs** - Add ALL task specs to selection
- **`git add -A` in the fix loop** - Sweeps pre-existing dirty paths into review-fix commits; use the snapshot-scoped staging
- **Re-typing command output into heredocs** - Handoff/spec/response content moves by redirection (`>`/`>>`) only; echoing a captured response is a duplicate emission
