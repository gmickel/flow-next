# Spec Completion Review Workflow — RepoPrompt Backend

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

Use when `BACKEND="rp"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, `REPO_ROOT`, and `SPEC_ID`.

## Critical rules (rp backend)

1. **The coordinator never reviews code itself** - you coordinate, RepoPrompt reviews. A verdict with no RP response behind it has broken this.
2. **Every verdict comes from an actual RP response** - a simulated or skipped review has broken this.
3. **Window selection and the builder run through `setup-review`** - calling the builder directly has broken this.
4. **`chat-send` carries no `--json` flag** - it suppresses the review response; a `{"chat": null}` result has broken this.
5. **Re-reviews stay in the same chat** - omit `--new-chat` after the first review; a re-review carrying it has broken this.

## Phase 1: Gather Context (RP)

**Run this BEFORE setup-review so the builder gets a real summary.**

```bash
BRANCH="$(git branch --show-current)"

# Get spec and task list (spec body enters context once here; the Phase 3 prompt
# file gets its own copy via redirection)
$FLOWCTL cat "$SPEC_ID"
TASKS_JSON="$($FLOWCTL tasks --spec "$SPEC_ID" --json)"

# Get changed files on branch
DIFF_BASE="main"
git rev-parse main >/dev/null 2>&1 || DIFF_BASE="master"
REVIEW_SNAPSHOT_FILE="${TMPDIR:-/tmp}/flow-completion-review-snapshot-<spec-id>-<suffix>.env"
REVIEW_HEAD_SHA="$(git rev-parse HEAD)"
REVIEW_BASE_SHA="$(git merge-base "$DIFF_BASE" "$REVIEW_HEAD_SHA")"
printf 'REVIEW_HEAD_SHA=%q\nREVIEW_BASE_SHA=%q\n' \
 "$REVIEW_HEAD_SHA" "$REVIEW_BASE_SHA" > "$REVIEW_SNAPSHOT_FILE"
git log ${DIFF_BASE}..HEAD --oneline
CHANGED_FILES="$(git diff ${DIFF_BASE}..HEAD --name-only)"
git diff ${DIFF_BASE}..HEAD --stat
```

Save:
- Spec ID and spec body
- Task list (IDs and titles)
- Branch name
- Changed files list

Compose a 1-2 sentence summary in agent context for the setup-review command below.

---

### Atomic Setup Block

**Only run ONCE. Type the Phase 1 summary into this block.**

```bash
# Self-contained complete CE contract plus the current spec/task text.
REVIEW_INSTRUCTIONS_FILE="${TMPDIR:-/tmp}/flow-completion-review-instructions-<spec-id>-<suffix>.md"
RESPONSE_FILE="${TMPDIR:-/tmp}/flow-completion-review-response-<spec-id>-<suffix>.md"
SETUP_FILE="${TMPDIR:-/tmp}/flow-completion-review-setup-<spec-id>-<suffix>.env"
cat > "$REVIEW_INSTRUCTIONS_FILE" << 'EOF'
Verify every current spec requirement against the completed implementation.
Read the actual code/tests and distinguish implemented, partial, missing, and
deferred requirements. Identify unrelated scope and evidence gaps. For R-ID
specs emit the complete coverage table and `Unaddressed R-IDs: [...]`.

For each gap emit Severity, Confidence exactly 0/25/50/75/100, and
Classification introduced or pre_existing. Suppress below 75 except P0 at
50+; only introduced gaps block. Never recommend deleting protected `.flow/*`, generated
plugin mirrors, spec/task records, review receipts, or Ralph artifacts.
Emit suppression/classification/protected-path tallies when applicable.
End with exactly one tag: <verdict>SHIP</verdict>,
<verdict>NEEDS_WORK</verdict>, or <verdict>NEEDS_HUMAN</verdict>.
EOF
$FLOWCTL cat "$SPEC_ID" >> "$REVIEW_INSTRUCTIONS_FILE"
for task_spec in .flow/tasks/${SPEC_ID}.*.md; do
 [[ -f "$task_spec" ]] && printf '\n\n' >> "$REVIEW_INSTRUCTIONS_FILE" \
 && sed -n 'p' "$task_spec" >> "$REVIEW_INSTRUCTIONS_FILE"
done
# Global acceptance criteria (fn-137): emits nothing when .flow/criteria.md absent.
# A nonzero exit is a validation error - fix .flow/criteria.md before re-running.
printf '\n\n' >> "$REVIEW_INSTRUCTIONS_FILE"
$FLOWCTL criteria prompt-block >> "$REVIEW_INSTRUCTIONS_FILE" || exit 1

RESERVATION_FILE="${TMPDIR:-/tmp}/flow-completion-review-reservation-<spec-id>-<suffix>.json"
ARTIFACT_FILE="${TMPDIR:-/tmp}/flow-completion-review-artifact-<spec-id>-<suffix>.blob"
DIFF_FILE="${TMPDIR:-/tmp}/flow-completion-review-dispatch-<spec-id>-<suffix>.diff"
# Phase 1's snapshot anchors do not survive across prompt turns: source them
# before hashing. Unbound anchors would run `git diff ..`, hash an empty blob,
# and falsely refuse the next round as NOT_RETRYABLE.
REVIEW_SNAPSHOT_FILE="${TMPDIR:-/tmp}/flow-completion-review-snapshot-<spec-id>-<suffix>.env"
source "$REVIEW_SNAPSHOT_FILE"
PROBED_RP_MODE="$($FLOWCTL rp mode-probe --json | jq -er '.mode')" || exit $?
if [[ "$PROBED_RP_MODE" == "ce" ]]; then
 [[ -n "${REVIEW_BASE_SHA:-}" && -n "${REVIEW_HEAD_SHA:-}" ]] \
 || { echo "unbound review snapshot; not reserving a round" >&2; exit 1; }
 git diff "$REVIEW_BASE_SHA..$REVIEW_HEAD_SHA" > "$DIFF_FILE" \
 || { echo "git diff failed; not reserving a round" >&2; exit 1; }
 [[ -s "$DIFF_FILE" || "$REVIEW_BASE_SHA" == "$REVIEW_HEAD_SHA" ]] \
 || { echo "empty diff over a non-empty range; not reserving a round" >&2; exit 1; }
 $FLOWCTL review-artifact completion "$SPEC_ID" --diff-file "$DIFF_FILE" --output "$ARTIFACT_FILE" --json
 ROUND_JSON="$($FLOWCTL review-rounds increment "$SPEC_ID" --kind plan \
 --review-type completion --artifact-file "$ARTIFACT_FILE" --json)"
 ROUND_EXIT=$?
 if [[ "$ROUND_EXIT" -ne 0 ]]; then
 printf '%s\n' "$ROUND_JSON"
 # NOT_RETRYABLE + exit 1 is human action only: no refund, force, reset,
 # or autonomous redispatch.
 exit "$ROUND_EXIT"
 fi
 if [[ "$(printf '%s' "$ROUND_JSON" | jq -r '.replayed // false')" == "true" ]]; then
 # Apply NEEDS_HUMAN > MAJOR_RETHINK > NEEDS_WORK > all-SHIP and stop
 # with no dispatch.
 printf '%s\n' "$ROUND_JSON"
 # A superseded replay never votes (a concurrent SHIP reset the counter).
 if [[ "$(printf '%s' "$ROUND_JSON" | jq -r '[.replays[]? | select(.superseded != true) | .verdict] | if index("NEEDS_HUMAN") then "NEEDS_HUMAN" else "" end')" == "NEEDS_HUMAN" ]]; then
 echo "ESCALATE: reviewer requested human review" >&2
 exit 4
 fi
 exit 0
 fi
 printf '%s' "$ROUND_JSON" > "$RESERVATION_FILE"
fi
$FLOWCTL rp setup-review --repo-root "$REPO_ROOT" \
 --summary-file "$REVIEW_INSTRUCTIONS_FILE" --response-type review \
 --response-file "$RESPONSE_FILE" --create > "$SETUP_FILE"
SETUP_EXIT=$?
if [[ "$SETUP_EXIT" -ne 0 ]]; then
 : > "$RESPONSE_FILE"
 if [[ "$PROBED_RP_MODE" == "ce" ]]; then
 RECORD_JSON="$($FLOWCTL review-rounds record "$SPEC_ID" --kind plan \
 --review-type completion --backend rp --output-file "$RESPONSE_FILE" \
 --reservation-id "$(jq -er '.reservation_id' "$RESERVATION_FILE")" \
 --exit-code "$SETUP_EXIT" --json)"
 RECORD_EXIT=$?
 printf '%s\n' "$RECORD_JSON"
 if [[ "$RECORD_EXIT" -ne 0 ]]; then
 exit "$RECORD_EXIT"
 fi
 fi
 exit "$SETUP_EXIT"
fi
source "$SETUP_FILE"

if [[ -z "${W:-}" || -z "${T:-}" || -z "${RP_MODE:-}" ]]; then
 echo "<promise>RETRY</promise>"
 exit 0
fi
if [[ "$RP_MODE" == "ce" && ( -z "${CHAT_ID:-}" || ! -s "$RESPONSE_FILE" ) ]]; then
 echo "<promise>RETRY</promise>"
 exit 0
fi

echo "Setup complete: mode=$RP_MODE W=$W T=$T"
```

If this block fails, output `<promise>RETRY</promise>` and stop. Do not improvise.
**Do NOT re-run setup-review** — the builder runs inside it. Re-running = double context build.

---

## Phase 2: Augment Selection (RP)

CE already returned the terminal review. Classic alone uses its published-tab
selection/chat compatibility flow:

```bash
SETUP_FILE="${TMPDIR:-/tmp}/flow-completion-review-setup-<spec-id>-<suffix>.env"
source "$SETUP_FILE"
if [[ "$RP_MODE" == "classic" ]]; then
 $FLOWCTL rp select-get --window "$W" --tab "$T"
 $FLOWCTL rp select-add --window "$W" --tab "$T" ".flow/specs/$SPEC_ID.md"
 for task_id in $(echo "$TASKS_JSON" | jq -r '.tasks[].id'); do
 $FLOWCTL rp select-add --window "$W" --tab "$T" ".flow/tasks/$task_id.md"
 done
 for f in $CHANGED_FILES; do
 $FLOWCTL rp select-add --window "$W" --tab "$T" "$f"
 done
fi
```

**Why this matters:** Chat only sees selected files.

---

## Phase 3: Execute Review (RP)

### Build combined prompt (file composition — no content re-typing)

**Path-persistence rule:** bash vars do NOT survive across prompt turns. Compose these literal unique paths in agent context and type them verbatim in EVERY block that references them (`mktemp` is reserved for paths created and consumed within a single bash block):

- Prompt file: `${TMPDIR:-/tmp}/flow-completion-review-prompt-<spec-id>-<agent-chosen 4-char suffix>.md`
- Response file: `${TMPDIR:-/tmp}/flow-completion-review-response-<spec-id>-<suffix>.md`

Build the prompt by deterministic composition — redirect command output into the file, never paste it into a heredoc. Only cheap **scalar** slots (`[SPEC_ID]`, `[BRANCH_NAME]`, task-id list) are filled inline while typing the quoted heredocs below; multi-line command output is always appended via redirection.

```bash
SETUP_FILE="${TMPDIR:-/tmp}/flow-completion-review-setup-<spec-id>-<suffix>.env"
source "$SETUP_FILE"
PROMPT_FILE="${TMPDIR:-/tmp}/flow-completion-review-prompt-<spec-id>-<suffix>.md" # literal path
if [[ "$RP_MODE" == "classic" ]]; then

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

## Spec Under Review
Spec: [SPEC_ID]
Branch: [BRANCH_NAME]
Tasks: [LIST TASK IDs]

## Spec Body
EOF

# 3. Spec body — appended via redirection, never re-typed
$FLOWCTL cat "$SPEC_ID" >> "$PROMPT_FILE"

# 4. Global acceptance criteria (fn-137) — emits nothing when .flow/criteria.md absent.
# A nonzero exit is a validation error - fix .flow/criteria.md before re-running.
printf '\n\n' >> "$PROMPT_FILE"
$FLOWCTL criteria prompt-block >> "$PROMPT_FILE" || exit 1

# 5. Review criteria (static, quoted heredoc)
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
- **Severity**: Critical / Major / Minor / Nitpick
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
`<verdict>SHIP</verdict>` or `<verdict>NEEDS_WORK</verdict>` or `<verdict>NEEDS_HUMAN</verdict>`

- SHIP: All `introduced` spec requirements are implemented and every R-ID is `met` or `deferred` (pre-existing gaps do not block)
- NEEDS_WORK: One or more `introduced` requirements are missing, partial, or wrong — or any non-deferred R-ID is `not-addressed`

Do NOT skip this tag. The automation depends on it.
EOF
fi
```

**Note:** The scalar bracket slots (`[SPEC_ID]`, `[BRANCH_NAME]`, `[LIST TASK IDs]`) are filled inline while typing the heredoc — they are cheap value substitutions. Multi-line content (handoff, spec body) is NEVER typed by hand; it arrives via the redirections above.

### Send to RepoPrompt and Parse Verdict (single-entry response)

The spec-scoped plan-counter reservation happens immediately before the single
CE builder/review call (or before Classic setup). After the verdict is
recorded, the shared terminal owner re-reads the latest completion attempt and
live cap counters from `review-rounds attempts`.

At the cap this refuses with an `ESCALATE:` marker + exit 4. That is NOT a
retryable error: do NOT dispatch the review or invent a completion verdict.
Surface the ESCALATE message to the caller and stop without writing completion
status (Ralph/autonomous: NEEDS_HUMAN). Only proceed to `chat-send` when the
increment succeeds.

Redirect the review response to the literal response file — it must enter context exactly ONCE, via a single Read of that file (command substitution + `echo` would be the second copy; redirection keeps stdout out of context entirely):

```bash
# Re-declare BOTH literal paths — this may run as a separate prompt turn from the
# build block, and bash vars do not survive across prompt turns (type them verbatim)
PROMPT_FILE="${TMPDIR:-/tmp}/flow-completion-review-prompt-<spec-id>-<suffix>.md" # same literal path from the build block
RESPONSE_FILE="${TMPDIR:-/tmp}/flow-completion-review-response-<spec-id>-<suffix>.md" # literal path
SETUP_FILE="${TMPDIR:-/tmp}/flow-completion-review-setup-<spec-id>-<suffix>.env"
source "$SETUP_FILE"
# Snapshot anchors do not survive across prompt turns — source before hashing.
REVIEW_SNAPSHOT_FILE="${TMPDIR:-/tmp}/flow-completion-review-snapshot-<spec-id>-<suffix>.env"
source "$REVIEW_SNAPSHOT_FILE"

if [[ "$RP_MODE" == "classic" ]]; then
 # Final Classic prompt exists now: its one reservation is immediately before
 # chat-send and its id travels to record.
 DIFF_FILE="${TMPDIR:-/tmp}/flow-completion-review-dispatch-<spec-id>-<suffix>.diff"
 ARTIFACT_FILE="${TMPDIR:-/tmp}/flow-completion-review-artifact-<spec-id>-<suffix>.blob"
 RESERVATION_FILE="${TMPDIR:-/tmp}/flow-completion-review-reservation-<spec-id>-<suffix>.json"
 [[ -n "${REVIEW_BASE_SHA:-}" && -n "${REVIEW_HEAD_SHA:-}" ]] \
 || { echo "unbound review snapshot; not reserving a round" >&2; exit 1; }
 git diff "$REVIEW_BASE_SHA..$REVIEW_HEAD_SHA" > "$DIFF_FILE" \
 || { echo "git diff failed; not reserving a round" >&2; exit 1; }
 [[ -s "$DIFF_FILE" || "$REVIEW_BASE_SHA" == "$REVIEW_HEAD_SHA" ]] \
 || { echo "empty diff over a non-empty range; not reserving a round" >&2; exit 1; }
 $FLOWCTL review-artifact completion "$SPEC_ID" --diff-file "$DIFF_FILE" --output "$ARTIFACT_FILE" --json
 ROUND_JSON="$($FLOWCTL review-rounds increment "$SPEC_ID" --kind plan \
 --review-type completion --artifact-file "$ARTIFACT_FILE" --json)"
 ROUND_EXIT=$?
 if [[ "$ROUND_EXIT" -ne 0 ]]; then
 printf '%s\n' "$ROUND_JSON"
 # NOT_RETRYABLE is a human terminal, never a transport refund/retry.
 exit "$ROUND_EXIT"
 fi
 if [[ "$(printf '%s' "$ROUND_JSON" | jq -r '.replayed // false')" == "true" ]]; then
 printf '%s\n' "$ROUND_JSON"
 # A superseded replay never votes (a concurrent SHIP reset the counter).
 if [[ "$(printf '%s' "$ROUND_JSON" | jq -r '[.replays[]? | select(.superseded != true) | .verdict] | if index("NEEDS_HUMAN") then "NEEDS_HUMAN" else "" end')" == "NEEDS_HUMAN" ]]; then
 echo "ESCALATE: reviewer requested human review" >&2
 exit 4
 fi
 exit 0
 fi
 printf '%s' "$ROUND_JSON" > "$RESERVATION_FILE"
 $FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file "$PROMPT_FILE" --new-chat --chat-name "Spec Completion Review: $SPEC_ID" > "$RESPONSE_FILE"
 RP_EXIT=$?
else
 RP_EXIT=0
fi

# Extract verdict tag from the response file
VERDICT="$(tr -d '\r' < "$RESPONSE_FILE" \
 | grep -oE '<verdict>(SHIP|NEEDS_WORK|NEEDS_HUMAN)</verdict>' \
 | tail -n 1 \
 | sed -E 's#</?verdict>##g')"

# Round-8 ordering: recording happens in Phase 4, AFTER the receipt inputs are
# assembled, so `record` journals the exact intended payload in the same
# transaction that consumes the reservation. Persist the dispatch facts — bash
# vars do not survive across prompt turns.
REVIEW_DISPATCH_FILE="${TMPDIR:-/tmp}/flow-completion-review-dispatch-result-<spec-id>-<suffix>.env"
printf 'RP_EXIT=%q\nVERDICT=%q\n' "$RP_EXIT" "$VERDICT" > "$REVIEW_DISPATCH_FILE"
```

**WAIT** for response. Takes 1-5+ minutes.

Do not echo the verdict or enter the fix loop from this block: Phase 4's
recorder is the gate, and nothing may run after a failed recorder.

The Phase 4 `record` call refunds no-verdict reservations and logs the failure. After
more than `${MAX_REVIEW_TRANSPORT_FAILURES:-2}` consecutive failures it exits
5 / `TRANSPORT_UNHEALTHY`: stop for backend repair, never reset the review
counter. No command may follow a failed recorder and make that Bash fence
successful. Only `RECORD_EXIT=0` proves this dispatch was appended as the latest
durable completion attempt consumed by the shared terminal owner.

**Single-entry rule:** after this block, Read the response file ONCE (Read tool, literal path). That render IS the gaps context — it feeds parsing and the fix loop. Do NOT `echo`/`cat` the response; verdict and receipt tallies grep the file directly.

---

## Phase 4: Receipt + Status (RP)

### SHIP owns its cap reset

`review-rounds record` atomically resets the shared plan counter and advances
its hash epoch on SHIP. Direct `review-rounds reset` and `--force` are
human-only recovery tools; never issue either from the autonomous workflow.

### Finalize the round: receipt inputs, then record, then publish

This is the single recorder fence. Assemble receipt inputs FIRST for every
delivered verdict (including NEEDS_HUMAN), hand them to `review-rounds record`,
and only then publish. A no-verdict transport failure assembles nothing, so a
refund never consumes receipt inputs. The payload carries an EMPTY `attempt_timestamp`:
that is the request for `record` to stamp its own attempt clock into the
journaled payload, which pre-record assembly cannot know.

```bash
# Literal paths from Phase 3 (path-persistence rule — type them verbatim)
RESPONSE_FILE="${TMPDIR:-/tmp}/flow-completion-review-response-<spec-id>-<suffix>.md"
RESERVATION_FILE="${TMPDIR:-/tmp}/flow-completion-review-reservation-<spec-id>-<suffix>.json"
REVIEW_SNAPSHOT_FILE="${TMPDIR:-/tmp}/flow-completion-review-snapshot-<spec-id>-<suffix>.env"
REVIEW_DISPATCH_FILE="${TMPDIR:-/tmp}/flow-completion-review-dispatch-result-<spec-id>-<suffix>.env"
source "$REVIEW_SNAPSHOT_FILE"
source "$REVIEW_DISPATCH_FILE"

RECEIPT_ARGS=()
if [[ -n "${REVIEW_RECEIPT_PATH:-}" && -n "$VERDICT" ]]; then
 ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
 mkdir -p "$(dirname "$REVIEW_RECEIPT_PATH")"

 # Optional: capture suppression-gate tally (fn-29.3).
 # Reviewer emits a line like "Suppressed findings: 3 at anchor 50, 7 at anchor 25, 2 at anchor 0."
 # Portable (BSD awk / mawk / gawk alike) — the 3-arg match(str,re,arr) form is
 # gawk-only and syntax-errors on stock macOS awk, and RP is macOS-gated, so it
 # would break exactly where it runs. grep -Eio + sed + paste is portable.
 _SUPPRESSED_PAIRS="$(grep -iE '^[>*_` ]*suppressed findings[ *_`]*:' "$RESPONSE_FILE" \
 | head -n 1 \
 | sed -E 's/^[^:]+:[[:space:]]*//; s/\.$//' \
 | grep -Eio '[0-9]+[[:space:]]+at[[:space:]]+anchor[[:space:]]+(0|25|50|75|100)' \
 | sed -E 's/^([0-9]+)[[:space:]]+at[[:space:]]+anchor[[:space:]]+([0-9]+)$/"\2":\1/' \
 | paste -sd, -)"
 SUPPRESSED_JSON="{${_SUPPRESSED_PAIRS}}" # empty → {}, populated → {"50":3,...}

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

 RECEIPT_INPUT="${TMPDIR:-/tmp}/flow-completion-review-receipt-<spec-id>-<suffix>.json"
 if ! cat > "$RECEIPT_INPUT" <<EOF
{"type":"completion_review","id":"$SPEC_ID","mode":"rp","verdict":"$VERDICT"$EXTRA_FIELDS,"base":"$REVIEW_BASE_SHA","head":"$REVIEW_HEAD_SHA","timestamp":"$ts","attempt_timestamp":""}
EOF
 then
 echo "<promise>RETRY</promise>"
 exit 0
 fi
 RECEIPT_ARGS=(--receipt-target "$REVIEW_RECEIPT_PATH" --receipt-payload-file "$RECEIPT_INPUT")
fi

# Record with the receipt inputs already in hand. Nothing may run after a
# failed recorder — no verdict echo, no receipt, no status owner, no fix loop.
# `--status-target completion` JOURNALS the terminal status; it does not write
# it here. Because a receipt target is journaled in the same finalization, the
# status lands only when that receipt publishes — via the `review-findings
# attach` below, or via the pre-increment replay gate in a later invocation. A
# failed attach therefore leaves NO terminal status behind, which is what keeps
# the Step 0.5 checkpoint's retry from becoming permanent.
RESERVATION_ID="$(jq -er '.reservation_id' "$RESERVATION_FILE")" \
 || { echo "no reservation id for this dispatch; refusing to finalize" >&2; exit 2; }
RECORD_JSON="$($FLOWCTL review-rounds record "$SPEC_ID" --kind plan \
 --review-type completion --backend rp --output-file "$RESPONSE_FILE" \
 --reservation-id "$RESERVATION_ID" --status-target completion \
 ${RECEIPT_ARGS[@]+"${RECEIPT_ARGS[@]}"} \
 --exit-code "$RP_EXIT" --json)"
RECORD_EXIT=$?
printf '%s\n' "$RECORD_JSON"
if [[ "$RECORD_EXIT" -ne 0 ]]; then
 exit "$RECORD_EXIT"
fi
# A concurrent SHIP landed while this review ran: the verdict was recorded as
# evidence, charged no round, and wrote no status. Routing it as a live
# terminal would fix-loop (or write a terminal status) against a pre-SHIP
# artifact, so stop here — the receipt/attach leg belongs to the SHIP's round.
if [[ "$(printf '%s' "$RECORD_JSON" | jq -r '.superseded // false')" == "true" ]]; then
 echo "VERDICT=SUPERSEDED"
 echo "review superseded by a newer SHIP — durable state unchanged; verdict recorded as evidence only" >&2
 exit 0
fi

if [[ -z "$VERDICT" ]]; then
 echo "No verdict tag found in response"
 echo "<promise>RETRY</promise>"
 exit 0
fi
echo "VERDICT=$VERDICT"

if [[ -n "${REVIEW_RECEIPT_PATH:-}" && -n "$VERDICT" ]]; then
 ATTEMPT_AT="$(printf '%s' "$RECORD_JSON" \
 | jq -r '.attempts[-1].timestamp // ""')"
 if [[ -z "$ATTEMPT_AT" ]]; then
 echo "<promise>RETRY</promise>"
 exit 0
 fi
 # Publish the journaled payload only — never re-derive it here.
 if ! "$FLOWCTL" review-findings attach \
 --reservation-id "$RESERVATION_ID" \
 --receipt "$REVIEW_RECEIPT_PATH" \
 --json >/dev/null; then
 echo "<promise>RETRY</promise>"
 exit 0
 fi
 if ! jq -e --arg id "$SPEC_ID" --arg attempt_at "$ATTEMPT_AT" --arg verdict "$VERDICT" \
 '.type == "completion_review"
 and .id == $id
 and .verdict == $verdict
 and .mode == "rp"
 and .attempt_timestamp == $attempt_at' \
 "$REVIEW_RECEIPT_PATH" >/dev/null; then
 echo "<promise>RETRY</promise>"
 exit 0
 fi
 echo "REVIEW_RECEIPT_WRITTEN: $REVIEW_RECEIPT_PATH"
fi

if [[ "$VERDICT" == "NEEDS_HUMAN" ]]; then
 echo "ESCALATE: reviewer requested human review" >&2
 exit 4
fi
```

---

## Fix Loop (RP)

**The fix loop never pauses for user confirmation.** Every valid finding is fixed and re-reviewed automatically — the goal is complete spec compliance. A loop that stops to ask, or that exits with a valid finding unfixed, has broken this. Never use the plain-text numbered prompt in this loop.

**Committed code changes land before every re-review.** A re-review dispatched with no change since the last verdict has broken this — the reviewer just returns NEEDS_WORK again.

**MAX ITERATIONS**: Limit fix+re-review cycles to
**${MAX_REVIEW_ITERATIONS:-8}** iterations (default 8, configurable in Ralph's
config.env). The `review-rounds increment` gate (step 6 below and Phase 3)
enforces this deterministically across fresh invocations — completion reviews
share the spec-scoped plan counter, so plan + completion rounds cannot each
spend a full cap. When a delivered `NEEDS_WORK` consumes the final round,
continue immediately to SKILL.md Step 3, write terminal `needs_work` exactly
once, then emit `ESCALATE:` and exit 4. Do not attempt another increment first.
An entry-time cap refusal with no delivered completion verdict remains
non-terminal: surface it and stop without a status write (Ralph:
`NEEDS_HUMAN`).

If verdict is NEEDS_WORK:

1. **Parse issues** - Extract ALL gaps (missing requirements, partial implementations) from the response-file Read
2. **Snapshot the pre-fix state** (BEFORE touching any file — literal paths per the path-persistence rule):
 ```bash
 git status --porcelain > "${TMPDIR:-/tmp}/flow-completion-review-snap-pre-<spec-id>-<suffix>.txt"
 ```
3. **Fix the code** - Implement missing functionality
4. **Run tests/lints** - Verify fixes don't break anything
5. **Commit fixes with snapshot-scoped staging** (required before re-review — a blanket `git add --all` has broken this):

 **Pre-dirty collision rule:** if a path you edited during the fix already appears in the PRE snapshot, do NOT stage it — path-level staging cannot separate pre-existing hunks from fix hunks. Surface the collision, defer/escalate that finding (report it in the re-review request or final summary), and never sweep pre-existing changes into a review-fix commit.

 ```bash
 SNAP_PRE="${TMPDIR:-/tmp}/flow-completion-review-snap-pre-<spec-id>-<suffix>.txt" # same literal path from step 2
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

 **Files already in the selection are never re-added.** RepoPrompt auto-refreshes
 file contents on every message. Only use `select-add` for NEW files created during fixes:
 ```bash
 # Only if fixes created new files not in original selection
 if [[ "$RP_MODE" == "classic" && -n "$NEW_FILES" ]]; then
 $FLOWCTL rp select-add --window "$W" --tab "$T" $NEW_FILES
 fi
 ```

 Then send re-review request (NO --new-chat, stay in same chat).

 **The re-review request carries no summary of the fixes.** RP auto-refreshes file contents - reviewer sees your changes automatically. Just request re-review. Any summary wastes tokens and duplicates what reviewer already sees.

 Redirect the re-review response to the SAME literal response file from Phase 3 (overwrite), then Read it once — the single-entry rule applies to every round.

 **fn-90 R5 cap gate first** — increment before EVERY re-review dispatch.
 A delivered final-round `NEEDS_WORK` has already continued through the shared
 status write and exited, so this command is never used to discover that
 terminal one round late. Exit 4 here means no completion verdict was
 delivered in this run: do NOT dispatch or write completion status; surface
 the ESCALATE message and stop (never retry):

 Recompute the post-fix snapshot **first**, in this same block: the fence must
 hash the fixed tree, never the pre-fix HEAD.

 ```bash
 # Post-fix snapshot recompute — ABOVE the hash fence.
 DIFF_BASE="main"
 git rev-parse --verify main >/dev/null 2>&1 || DIFF_BASE="master"
 git rev-parse --verify "$DIFF_BASE" >/dev/null 2>&1 \
 || { echo "cannot resolve diff base; not reserving a round" >&2; exit 1; }
 REVIEW_SNAPSHOT_FILE="${TMPDIR:-/tmp}/flow-completion-review-snapshot-<spec-id>-<suffix>.env"
 REVIEW_HEAD_SHA="$(git rev-parse HEAD)" || exit 1
 REVIEW_BASE_SHA="$(git merge-base "$DIFF_BASE" "$REVIEW_HEAD_SHA")" || exit 1
 [[ -n "$REVIEW_HEAD_SHA" && -n "$REVIEW_BASE_SHA" ]] \
 || { echo "unbound review snapshot; refusing to hash" >&2; exit 1; }
 printf 'REVIEW_HEAD_SHA=%q\nREVIEW_BASE_SHA=%q\n' \
 "$REVIEW_HEAD_SHA" "$REVIEW_BASE_SHA" > "$REVIEW_SNAPSHOT_FILE"

 # Compose the re-review prompt first, then bind the exact final diff.
 DIFF_FILE="${TMPDIR:-/tmp}/flow-completion-review-rereview-<spec-id>-<suffix>.diff"
 ARTIFACT_FILE="${TMPDIR:-/tmp}/flow-completion-review-rereview-<spec-id>-<suffix>.blob"
 RESERVATION_FILE="${TMPDIR:-/tmp}/flow-completion-review-reservation-<spec-id>-<suffix>.json"
 git diff "$REVIEW_BASE_SHA..$REVIEW_HEAD_SHA" > "$DIFF_FILE" \
 || { echo "git diff failed; not reserving a round" >&2; exit 1; }
 [[ -s "$DIFF_FILE" || "$REVIEW_BASE_SHA" == "$REVIEW_HEAD_SHA" ]] \
 || { echo "empty diff over a non-empty range; not reserving a round" >&2; exit 1; }
 $FLOWCTL review-artifact completion "$SPEC_ID" --diff-file "$DIFF_FILE" --output "$ARTIFACT_FILE" --json
 ROUND_JSON="$($FLOWCTL review-rounds increment "$SPEC_ID" --kind plan \
 --review-type completion --artifact-file "$ARTIFACT_FILE" --json)"
 ROUND_EXIT=$?
 if [[ "$ROUND_EXIT" -ne 0 ]]; then
 printf '%s\n' "$ROUND_JSON"
 exit "$ROUND_EXIT"
 fi
 if [[ "$(printf '%s' "$ROUND_JSON" | jq -r '.replayed // false')" == "true" ]]; then
 # Prior delivery replay: terminal precedence, no second dispatch.
 printf '%s\n' "$ROUND_JSON"
 # A superseded replay never votes (a concurrent SHIP reset the counter).
 if [[ "$(printf '%s' "$ROUND_JSON" | jq -r '[.replays[]? | select(.superseded != true) | .verdict] | if index("NEEDS_HUMAN") then "NEEDS_HUMAN" else "" end')" == "NEEDS_HUMAN" ]]; then
 echo "ESCALATE: reviewer requested human review" >&2
 exit 4
 fi
 exit 0
 fi
 printf '%s' "$ROUND_JSON" > "$RESERVATION_FILE"
 REVIEW_ROUND="$(printf '%s' "$ROUND_JSON" | jq -r '.round')"
 REVIEW_CAP="$(printf '%s' "$ROUND_JSON" | jq -r '.cap')"
 ```

 ```bash
 cat > "${TMPDIR:-/tmp}/flow-completion-review-rereview-<spec-id>-<suffix>.md" << 'EOF'
 Gaps addressed. Please re-review for spec compliance.

 **REQUIRED**: End with `<verdict>SHIP</verdict>` or `<verdict>NEEDS_WORK</verdict>` or `<verdict>NEEDS_HUMAN</verdict>`
 EOF

 SETUP_FILE="${TMPDIR:-/tmp}/flow-completion-review-setup-<spec-id>-<suffix>.env"
 source "$SETUP_FILE"
 if [[ "$RP_MODE" == "ce" ]]; then
 $FLOWCTL rp chat-send --window "$W" --context-id "$T" \
 --chat-id "$CHAT_ID" --mode review \
 --message-file "${TMPDIR:-/tmp}/flow-completion-review-rereview-<spec-id>-<suffix>.md" \
 > "${TMPDIR:-/tmp}/flow-completion-review-response-<spec-id>-<suffix>.md"
 else
 $FLOWCTL rp chat-send --window "$W" --tab "$T" \
 --message-file "${TMPDIR:-/tmp}/flow-completion-review-rereview-<spec-id>-<suffix>.md" \
 > "${TMPDIR:-/tmp}/flow-completion-review-response-<spec-id>-<suffix>.md"
 fi
 ```

 Re-extract the verdict from the response file (same grep as Phase 3), then
 run Phase 4's finalize fence verbatim: assemble the receipt inputs FIRST,
 pass them to the same
 `review-rounds record ... --review-type completion --status-target completion`
 command with the captured `rp chat-send` exit code, capture and check
 `RECORD_EXIT`, and publish by reservation id. Then Read the file once for
 the next round's gaps.
 A nonzero recorder exit stops that round immediately; never echo a verdict
 or continue to the shared status owner afterward.
7. **Repeat** until SHIP

**Anti-pattern**: Re-adding already-selected files before re-review. RP auto-refreshes; re-adding can cause issues.

---

## Anti-patterns (RP backend)

- **Calling builder directly** - Must use `setup-review` which wraps it
- **Skipping setup-review** - window selection happens only through this command
- **Hard-coding window IDs** - Never write `--window 1`
- **Missing task specs** - Add ALL task specs to selection
- **Blanket staging (`git add --all`) in the fix loop** - Sweeps pre-existing dirty paths into review-fix commits; use the snapshot-scoped staging
- **Re-typing command output into heredocs** - Handoff/spec/response content moves by redirection (`>`/`>>`) only; echoing a captured response is a duplicate emission
