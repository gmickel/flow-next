# Implementation Review Workflow — RepoPrompt Backend

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
REVIEW_SNAPSHOT_FILE="${TMPDIR:-/tmp}/flow-impl-review-snapshot-<task-id-or-branch-slug>-<suffix>.env"
REVIEW_HEAD_SHA="$(git rev-parse HEAD)"
REVIEW_BASE_SHA="$(git merge-base "$DIFF_BASE" "$REVIEW_HEAD_SHA")"
printf 'REVIEW_HEAD_SHA=%q\nREVIEW_BASE_SHA=%q\n' \
  "$REVIEW_HEAD_SHA" "$REVIEW_BASE_SHA" > "$REVIEW_SNAPSHOT_FILE"

git log ${DIFF_BASE}..HEAD --oneline
CHANGED_FILES="$(git diff ${DIFF_BASE}..HEAD --name-only)"
git diff ${DIFF_BASE}..HEAD --stat
```

Save:
- Branch name
- Changed files list
- Commit summary
- DIFF_BASE (for reference in review prompt)

Compose a 1-2 sentence summary in agent context from these results.

---

### Atomic Setup Block

**Only run ONCE. Type the Phase 1 summary into this block.**

```bash
# Self-contained: fill the bracketed Phase 1 facts inline. CE returns the review
# from this one call, so this file carries the complete substantive contract.
REVIEW_INSTRUCTIONS_FILE="${TMPDIR:-/tmp}/flow-impl-review-instructions-<task-id-or-branch-slug>-<suffix>.md"
RESPONSE_FILE="${TMPDIR:-/tmp}/flow-impl-review-response-<task-id-or-branch-slug>-<suffix>.md"
SETUP_FILE="${TMPDIR:-/tmp}/flow-impl-review-setup-<task-id-or-branch-slug>-<suffix>.env"
cat > "$REVIEW_INSTRUCTIONS_FILE" << 'EOF'
Review the actual implementation diff [DIFF_BASE]..HEAD on branch [BRANCH].
Changed files: [CHANGED_FILES]. Commits: [COMMIT_SUMMARY].

Read the task/spec and changed code. Judge correctness, simplicity, DRY,
architecture, edge cases, tests, security, and canonical vocabulary. Explore
happy, invalid, boundary, concurrent, network, exhaustion, attack, corruption,
and cascading-failure scenarios only where applicable to changed code.

For specs with R-IDs, emit a met/partial/not-addressed/deferred coverage table
and `Unaddressed R-IDs: [...]`; a non-deferred not-addressed R-ID blocks.
Confidence must be exactly 0/25/50/75/100. Suppress below 75 except P0 at 50+.
Classify every finding introduced or pre_existing; only introduced findings
block. Never recommend deleting protected `.flow/*`, generated plugin mirrors,
spec/task records, review receipts, or Ralph artifacts.

For each surviving introduced finding emit Severity (P0-P3), Confidence,
Classification, File:Line, Problem, and Suggestion. List pre-existing findings
separately. Emit suppression/classification/protected-path tallies when
applicable. End with exactly one tag: <verdict>SHIP</verdict>,
<verdict>NEEDS_WORK</verdict>, or <verdict>MAJOR_RETHINK</verdict>.
EOF
[[ -n "$TASK_ID" ]] && $FLOWCTL show "$TASK_ID" >> "$REVIEW_INSTRUCTIONS_FILE"

if [[ -n "$TASK_ID" ]]; then
  ROUND_JSON="$($FLOWCTL review-rounds increment "${TASK_ID%.*}" --kind impl --task "$TASK_ID" --json)"
  ROUND_EXIT=$?
  if [[ "$ROUND_EXIT" -ne 0 ]]; then
    printf '%s\n' "$ROUND_JSON"
    exit "$ROUND_EXIT"
  fi
fi

# CE: one context_builder review result, written directly to RESPONSE_FILE.
# Classic: RP_MODE=classic and the old tab selection/chat flow continues below.
$FLOWCTL rp setup-review --repo-root "$REPO_ROOT" \
  --summary-file "$REVIEW_INSTRUCTIONS_FILE" --response-type review \
  --response-file "$RESPONSE_FILE" --create > "$SETUP_FILE"
SETUP_EXIT=$?
if [[ "$SETUP_EXIT" -ne 0 ]]; then
  : > "$RESPONSE_FILE"
  if [[ -n "$TASK_ID" ]]; then
    RECORD_JSON="$($FLOWCTL review-rounds record "${TASK_ID%.*}" --kind impl \
      --review-type impl --task "$TASK_ID" --backend rp \
      --output-file "$RESPONSE_FILE" --exit-code "$SETUP_EXIT" --json)"
    RECORD_EXIT=$?
    printf '%s\n' "$RECORD_JSON"
    if [[ "$RECORD_EXIT" -ne 0 ]]; then
      exit "$RECORD_EXIT"
    fi
  fi
  exit "$SETUP_EXIT"
fi
source "$SETUP_FILE"

# Both paths retain numeric window/context identity; CE also returns the chat.
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

CE already returned the terminal review and MUST skip this phase. Classic alone
uses its published-tab selection:

```bash
SETUP_FILE="${TMPDIR:-/tmp}/flow-impl-review-setup-<task-id-or-branch-slug>-<suffix>.env"
source "$SETUP_FILE"
if [[ "$RP_MODE" == "classic" ]]; then
  $FLOWCTL rp select-get --window "$W" --tab "$T"
  for f in $CHANGED_FILES; do
    $FLOWCTL rp select-add --window "$W" --tab "$T" "$f"
  done
  $FLOWCTL rp select-add --window "$W" --tab "$T" .flow/specs/<task-id>.md
fi
```

**Why this matters:** Chat only sees selected files.

---

## Phase 3: Execute Review (RP)

### Build combined prompt (file composition — no content re-typing)

**Path-persistence rule:** bash vars do NOT survive across tool calls. Compose these literal unique paths in agent context and type them verbatim in EVERY block that references them (`mktemp` is reserved for paths created and consumed within a single bash block):

- Prompt file: `${TMPDIR:-/tmp}/flow-impl-review-prompt-<task-id-or-branch-slug>-<agent-chosen 4-char suffix>.md`
- Response file: `${TMPDIR:-/tmp}/flow-impl-review-response-<task-id-or-branch-slug>-<suffix>.md`

Build the prompt by deterministic composition — redirect command output into the file, never paste it into a heredoc. Only cheap **scalar** slots (branch, file list, commit summary, focus areas — values you already hold from Phase 1) are filled inline while typing the quoted heredocs below; multi-line command output is always appended via redirection.

```bash
SETUP_FILE="${TMPDIR:-/tmp}/flow-impl-review-setup-<task-id-or-branch-slug>-<suffix>.env"
source "$SETUP_FILE"
PROMPT_FILE="${TMPDIR:-/tmp}/flow-impl-review-prompt-<task-id-or-branch-slug>-<suffix>.md"   # literal path
if [[ "$RP_MODE" == "classic" ]]; then

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
fi
```

### Send to RepoPrompt (single-entry response)

The deterministic review-round cap was reserved immediately before the
single CE builder/review call (or before Classic setup). At the cap, stop
without invoking RepoPrompt.

Redirect the review response to the literal response file — it must enter context exactly ONCE, via a single Read of that file (command substitution + `echo` would be the second copy; redirection keeps stdout out of context entirely):

```bash
# Re-declare BOTH literal paths — this may run as a separate tool call from the
# build block, and bash vars do not survive across tool calls (type them verbatim)
PROMPT_FILE="${TMPDIR:-/tmp}/flow-impl-review-prompt-<task-id-or-branch-slug>-<suffix>.md"      # same literal path from the build block
RESPONSE_FILE="${TMPDIR:-/tmp}/flow-impl-review-response-<task-id-or-branch-slug>-<suffix>.md"  # literal path
SETUP_FILE="${TMPDIR:-/tmp}/flow-impl-review-setup-<task-id-or-branch-slug>-<suffix>.env"
source "$SETUP_FILE"

if [[ "$RP_MODE" == "classic" ]]; then
  $FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file "$PROMPT_FILE" --new-chat --chat-name "Impl Review: $BRANCH" > "$RESPONSE_FILE"
  RP_EXIT=$?
else
  # CE's one context_builder call already wrote the terminal response.
  RP_EXIT=0
fi

VERDICT="$(tr -d '\r' < "$RESPONSE_FILE" \
  | grep -oE '<verdict>(SHIP|NEEDS_WORK|MAJOR_RETHINK)</verdict>' \
  | tail -n 1 \
  | sed -E 's#</?verdict>##g')"

if [[ -n "$TASK_ID" ]]; then
  RECORD_JSON="$($FLOWCTL review-rounds record "${TASK_ID%.*}" --kind impl \
    --review-type impl --task "$TASK_ID" --backend rp \
    --output-file "$RESPONSE_FILE" --exit-code "$RP_EXIT" --json)"
  RECORD_EXIT=$?
  printf '%s\n' "$RECORD_JSON"
  if [[ "$RECORD_EXIT" -ne 0 ]]; then
    exit "$RECORD_EXIT"
  fi
fi

if [[ -z "$VERDICT" ]]; then
  echo "No verdict tag found in response"
  echo "<promise>RETRY</promise>"
  exit 0
fi
echo "VERDICT=$VERDICT"
```

**WAIT** for response. Takes 1-5+ minutes.

The `record` call refunds no-verdict reservations and logs the failure. After
more than `${MAX_REVIEW_TRANSPORT_FAILURES:-2}` consecutive failures it exits
5 / `TRANSPORT_UNHEALTHY`: stop for backend repair, never reset the review
counter. A failed task-scoped recorder must terminate this fence; no later
verdict, receipt, status, or fix-loop command may swallow its exit.

**Single-entry rule:** after this block, Read the response file ONCE (Read tool, literal path). That render IS the findings context — it feeds parsing and the fix loop. Do NOT `echo`/`cat` the response; verdict and receipt tallies grep the file directly.

---

## Phase 4: Receipt + Status (RP)

### Reset the cap counter on SHIP (fn-90 R5 convergence)

Immediately after parsing a SHIP verdict (task-scoped reviews only):

```bash
if [[ "$VERDICT" == "SHIP" && -n "$TASK_ID" ]]; then
  $FLOWCTL review-rounds reset "${TASK_ID%.*}" --kind impl --task "$TASK_ID" --json
fi
```

### Write receipt (if REVIEW_RECEIPT_PATH set)

```bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mkdir -p "$(dirname "$REVIEW_RECEIPT_PATH")"
  REVIEW_SNAPSHOT_FILE="${TMPDIR:-/tmp}/flow-impl-review-snapshot-<task-id-or-branch-slug>-<suffix>.env"
  source "$REVIEW_SNAPSHOT_FILE"

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

  RECEIPT_INPUT="$(mktemp "${TMPDIR:-/tmp}/flow-impl-review-receipt.XXXXXX.json")"
  cat > "$RECEIPT_INPUT" <<EOF
{"type":"impl_review","id":"<TASK_ID>","mode":"rp","verdict":"$VERDICT"$EXTRA_FIELDS,"timestamp":"$ts"}
EOF
  # The reviewer response is already local. This deterministic attach reads
  # the prior receipt before atomically replacing it, preserving explicit
  # supersedes lineage without another model/network call.
  if ! "$FLOWCTL" review-findings attach \
    --input "$RECEIPT_INPUT" \
    --receipt "$REVIEW_RECEIPT_PATH" \
    --review-file "$RESPONSE_FILE" \
    --base "$REVIEW_BASE_SHA" \
    --head "$REVIEW_HEAD_SHA" \
    --json >/dev/null; then
    rm -f "$RECEIPT_INPUT"
    echo "<promise>RETRY</promise>"
    exit 0
  fi
  rm -f "$RECEIPT_INPUT"
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

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is production-grade world-class software and architecture. Never use AskUserQuestion in this loop.**

**CRITICAL: You MUST fix the code BEFORE re-reviewing. Never re-review without making changes.**

**MAX ITERATIONS**: Limit fix+re-review cycles to **${MAX_REVIEW_ITERATIONS:-8}** iterations (default 8, configurable in Ralph's config.env). If still NEEDS_WORK after max rounds, output `<promise>RETRY</promise>` and stop — let the next Ralph iteration start fresh. The `review-rounds increment` gate (step 6 below and Phase 3) enforces this deterministically across fresh invocations: at the cap it refuses with an `ESCALATE:` marker + exit 4, which is NOT retryable — surface it and stop (Ralph: NEEDS_HUMAN).

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
   SNAP_PRE="${TMPDIR:-/tmp}/flow-impl-review-snap-pre-<task-id-or-branch-slug>-<suffix>.txt"    # same literal path from step 2
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
   if [[ "$RP_MODE" == "classic" && -n "$NEW_FILES" ]]; then
     $FLOWCTL rp select-add --window "$W" --tab "$T" $NEW_FILES
   fi
   ```

   Then send re-review request (NO --new-chat, stay in same chat).

   **CRITICAL: Do NOT summarize fixes.** RP auto-refreshes file contents - reviewer sees your changes automatically. Just request re-review. Any summary wastes tokens and duplicates what reviewer already sees.

   Redirect the re-review response to the SAME literal response file from Phase 3 (overwrite), then Read it once — the single-entry rule applies to every round.

   **fn-90 R5 cap gate first** — increment before EVERY re-review dispatch (task-scoped only); exit 4 = cap reached → do NOT dispatch, surface the ESCALATE message and stop (never retry):

   ```bash
   if [[ -n "$TASK_ID" ]]; then
     ROUND_JSON="$($FLOWCTL review-rounds increment "${TASK_ID%.*}" --kind impl --task "$TASK_ID" --json)"
     ROUND_EXIT=$?
     if [[ "$ROUND_EXIT" -ne 0 ]]; then
       printf '%s\n' "$ROUND_JSON"
       exit "$ROUND_EXIT"
     fi
   fi
   ```

   ```bash
   cat > "${TMPDIR:-/tmp}/flow-impl-review-rereview-<task-id-or-branch-slug>-<suffix>.md" << 'EOF'
   Issues addressed. Please re-review.

   **REQUIRED**: End with `<verdict>SHIP</verdict>` or `<verdict>NEEDS_WORK</verdict>` or `<verdict>MAJOR_RETHINK</verdict>`
   EOF

   if [[ -z "$BASE_COMMIT" ]]; then
     DIFF_BASE="main"
     git rev-parse main >/dev/null 2>&1 || DIFF_BASE="master"
   else
     DIFF_BASE="$BASE_COMMIT"
   fi
   REVIEW_SNAPSHOT_FILE="${TMPDIR:-/tmp}/flow-impl-review-snapshot-<task-id-or-branch-slug>-<suffix>.env"
   REVIEW_HEAD_SHA="$(git rev-parse HEAD)"
   REVIEW_BASE_SHA="$(git merge-base "$DIFF_BASE" "$REVIEW_HEAD_SHA")"
   printf 'REVIEW_HEAD_SHA=%q\nREVIEW_BASE_SHA=%q\n' \
     "$REVIEW_HEAD_SHA" "$REVIEW_BASE_SHA" > "$REVIEW_SNAPSHOT_FILE"

   SETUP_FILE="${TMPDIR:-/tmp}/flow-impl-review-setup-<task-id-or-branch-slug>-<suffix>.env"
   source "$SETUP_FILE"
   if [[ "$RP_MODE" == "ce" ]]; then
     $FLOWCTL rp chat-send --window "$W" --context-id "$T" \
       --chat-id "$CHAT_ID" --mode review \
       --message-file "${TMPDIR:-/tmp}/flow-impl-review-rereview-<task-id-or-branch-slug>-<suffix>.md" \
       > "${TMPDIR:-/tmp}/flow-impl-review-response-<task-id-or-branch-slug>-<suffix>.md"
   else
     $FLOWCTL rp chat-send --window "$W" --tab "$T" \
       --message-file "${TMPDIR:-/tmp}/flow-impl-review-rereview-<task-id-or-branch-slug>-<suffix>.md" \
       > "${TMPDIR:-/tmp}/flow-impl-review-response-<task-id-or-branch-slug>-<suffix>.md"
   fi
   ```

   Re-extract the verdict from the response file (same grep as Phase 3), call
   the same task-scoped `review-rounds record ... --review-type impl` command
   with the captured `rp chat-send` exit code, capture and check `RECORD_EXIT`
   exactly as in Phase 3, then Read the file once for the next round's findings.
   A nonzero recorder exit stops the round before any verdict/control path.
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
