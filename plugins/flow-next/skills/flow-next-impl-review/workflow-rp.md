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

### Build combined prompt

Get builder's handoff:
```bash
HANDOFF="$($FLOWCTL rp prompt-get --window "$W" --tab "$T")"
```

Write combined prompt:
```bash
cat > /tmp/review-prompt.md << 'EOF'
[PASTE HANDOFF HERE]

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
[PASTE flowctl show OUTPUT if known]

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

### Send to RepoPrompt

```bash
REVIEW_RESPONSE="$($FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file /tmp/review-prompt.md --new-chat --chat-name "Impl Review: $BRANCH")"
echo "$REVIEW_RESPONSE"

VERDICT="$(echo "$REVIEW_RESPONSE" \
  | tr -d '\r' \
  | grep -oE '<verdict>(SHIP|NEEDS_WORK|MAJOR_RETHINK)</verdict>' \
  | tail -n 1 \
  | sed -E 's#</?verdict>##g')"

if [[ -z "$VERDICT" ]]; then
  echo "No verdict tag found in response"
  echo "<promise>RETRY</promise>"
  exit 0
fi
```

**WAIT** for response. Takes 1-5+ minutes.

---

## Phase 4: Receipt + Status (RP)

### Write receipt (if REVIEW_RECEIPT_PATH set)

```bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mkdir -p "$(dirname "$REVIEW_RECEIPT_PATH")"

  # Optional: capture suppression-gate tally (fn-29.3).
  # Reviewer emits a line like "Suppressed findings: 3 at anchor 50, 7 at anchor 25, 2 at anchor 0."
  SUPPRESSED_JSON="$(printf '%s' "$REVIEW_RESPONSE" \
    | grep -iE '^[>*_` ]*suppressed findings[ *_`]*:' \
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
  CLASSIFICATION_LINE="$(printf '%s' "$REVIEW_RESPONSE" \
    | grep -iE '^[>*_` ]*classification counts[ *_`]*:' \
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
  UNADDRESSED_LINE="$(printf '%s' "$REVIEW_RESPONSE" \
    | grep -iE '^[>*_` ]*unaddressed([[:space:]]+r[-_ ]?ids?)?[ *_`]*:' \
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

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is production-grade world-class software and architecture. Never use AskUserQuestion in this loop.**

**CRITICAL: You MUST fix the code BEFORE re-reviewing. Never re-review without making changes.**

**MAX ITERATIONS**: Limit fix+re-review cycles to **${MAX_REVIEW_ITERATIONS:-3}** iterations (default 3, configurable in Ralph's config.env). If still NEEDS_WORK after max rounds, output `<promise>RETRY</promise>` and stop — let the next Ralph iteration start fresh.

If verdict is NEEDS_WORK:

1. **Parse issues** - Extract ALL issues by severity (Critical → Major → Minor)
2. **Fix the code** - Address each issue in order
3. **Run tests/lints** - Verify fixes don't break anything
4. **Commit fixes** (MANDATORY before re-review):
   ```bash
   git add -A
   git commit -m "fix: address review feedback"
   ```
   **If you skip this and re-review without committing changes, reviewer will return NEEDS_WORK again.**

5. **Request re-review** (only AFTER step 4):

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

   ```bash
   cat > /tmp/re-review.md << 'EOF'
   Issues addressed. Please re-review.

   **REQUIRED**: End with `<verdict>SHIP</verdict>` or `<verdict>NEEDS_WORK</verdict>` or `<verdict>MAJOR_RETHINK</verdict>`
   EOF

   $FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file /tmp/re-review.md
   ```
6. **Repeat** until Ship

**Anti-pattern**: Re-adding already-selected files before re-review. RP auto-refreshes; re-adding can cause issues.

---

## Anti-patterns (RP backend)

- **Calling builder directly** - Must use `setup-review` which wraps it
- **Skipping setup-review** - Window selection MUST happen via this command
- **Hard-coding window IDs** - Never write `--window 1`
- **Missing changed files** - Add ALL changed files to selection
