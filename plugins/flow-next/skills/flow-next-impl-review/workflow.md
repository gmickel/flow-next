# Implementation Review Workflow

## Philosophy

The reviewer model only sees selected files. RepoPrompt's Builder discovers context you'd miss (rp backend). Codex and Copilot use context hints from flowctl (codex/copilot backends).

---

## Phase 0: Backend Detection

**Run this first. Do not skip.**

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Priority: --review flag > env > config (flag parsed in SKILL.md)
# Text output is bare backend name for back-compat grep. The same command in
# --json mode returns {backend, spec, model, effort, source} — use that if you
# need the model / effort resolved from a spec-form env value.
BACKEND=$($FLOWCTL review-backend)

if [[ "$BACKEND" == "ASK" ]]; then
  echo "Error: No review backend configured."
  echo "Run /flow-next:setup to configure, or pass --review=rp|codex|copilot|none"
  exit 1
fi

echo "Review backend: $BACKEND (override: --review=rp|codex|copilot|none)"
```

**Spec-form env var (optional):** `FLOW_REVIEW_BACKEND` accepts bare or full spec:

```bash
# Bare backend (back-compat)
FLOW_REVIEW_BACKEND=codex $FLOWCTL codex impl-review "$TASK_ID" --receipt "$RECEIPT_PATH"

# Full spec — model + effort resolved automatically
FLOW_REVIEW_BACKEND=codex:gpt-5.5:xhigh $FLOWCTL codex impl-review "$TASK_ID" --receipt "$RECEIPT_PATH"
FLOW_REVIEW_BACKEND=copilot:claude-opus-4.5 $FLOWCTL copilot impl-review "$TASK_ID" --receipt "$RECEIPT_PATH"

# Or pass spec directly (preferred for one-offs, avoids env pollution):
$FLOWCTL codex impl-review "$TASK_ID" --spec "codex:gpt-5.5:xhigh" --receipt "$RECEIPT_PATH"
```

Per-task `review` (set via `flowctl task set-backend`) overrides env.

**If backend is "none"**: Skip review, inform user, and exit cleanly (no error).

**Then branch to backend-specific workflow below.**

---

## Phase 0.5: Trivial-diff triage (fn-29.6)

A cheap pre-check that short-circuits lockfile-only, docs-only, release-chore,
and generated-file diffs. Runs before the configured backend — when it returns
SKIP, the receipt is written with `mode: "triage_skip"` / `verdict: "SHIP"`
and no expensive backend review is invoked.

**Default behavior:** deterministic whitelist only (no LLM call). Ambiguous
diffs default to REVIEW. Opt-in to LLM judge with `FLOW_TRIAGE_LLM=1`.

**Opt-out:**
- `--no-triage` argument on the skill
- `FLOW_RALPH_NO_TRIAGE=1` env var (Ralph runs)

**Invocation (from SKILL.md):**

```bash
if [[ -z "${TRIAGE_DISABLED:-}" && -z "${FLOW_RALPH_NO_TRIAGE:-}" ]]; then
  RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt.json}"
  TRIAGE_ARGS=(triage-skip --receipt "$RECEIPT_PATH" --json)
  [[ -n "$BASE_COMMIT" ]] && TRIAGE_ARGS+=(--base "$BASE_COMMIT")
  [[ -n "$TASK_ID" ]] && TRIAGE_ARGS+=(--task "$TASK_ID")
  [[ -z "${FLOW_TRIAGE_LLM:-}" ]] && TRIAGE_ARGS+=(--no-llm)

  if TRIAGE_OUT=$($FLOWCTL "${TRIAGE_ARGS[@]}" 2>/dev/null); then
    SKIP_REASON=$(echo "$TRIAGE_OUT" | jq -r '.reason // "trivial diff"' 2>/dev/null)
    echo "Triage-skip: $SKIP_REASON"
    echo "VERDICT=SHIP"
    exit 0
  fi
fi
```

**Exit codes:**
- `0` → SKIP (verdict=SHIP, receipt written, skill exits early)
- `1` → proceed to full review (normal fallthrough to backend)
- `>=2` → error (falls through to full review — never fail closed)

**Receipt shape on SKIP:**

```json
{
  "type": "impl_review",
  "id": "fn-29.6",
  "mode": "triage_skip",
  "base": "main",
  "verdict": "SHIP",
  "reason": "lockfile-only (bun.lock)",
  "source": "deterministic",
  "changed_file_count": 1,
  "timestamp": "2026-04-24T10:00:00Z"
}
```

Ralph reads `verdict` — `SHIP` satisfies the gate regardless of `mode`. No
Ralph-script changes required.

**Triage rules (deterministic layer):**

| Shape | Action |
|-------|--------|
| Any code file (`.py`, `.ts`, `.go`, `.sh`, ...) present | REVIEW (AC9) |
| Any `.flow/specs/*.md` / `.flow/tasks/*.md` / `.flow/epics/*.json` | REVIEW |
| All files are lockfiles (`package-lock.json`, `bun.lock`, ...) | SKIP |
| All files are docs (`.md`, `.mdx`, `.txt`, `.rst`, `.adoc`) | SKIP |
| All files are under generated paths (`codex/`, `vendor/`, `node_modules/`, ...) | SKIP |
| Release-chore: `plugin.json` / `package.json` / `Cargo.toml` / `pyproject.toml` + optional `CHANGELOG.md` | SKIP |
| Lockfile + manifest combo | SKIP |
| Anything else | REVIEW (conservative fallthrough) |

When `FLOW_TRIAGE_LLM=1`, ambiguous diffs get a one-shot fast-model call
(`gpt-5-mini` for codex backend, `claude-haiku-4.5` for copilot backend).
Malformed LLM output falls through to REVIEW.

---

## Codex Backend Workflow

Use when `BACKEND="codex"`.

### Step 1: Identify Task and Diff Base

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
```

### Step 2: Execute Review

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt.json}"

$FLOWCTL codex impl-review "$TASK_ID" --base "$DIFF_BASE" --receipt "$RECEIPT_PATH"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK`.**

### Step 3: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix code and run tests
3. Commit fixes
4. Re-run step 2 (receipt enables session continuity)
5. Repeat until SHIP

### Step 4: Receipt

Receipt is written automatically by `flowctl codex impl-review` when `--receipt` provided.
Format: `{"mode":"codex","task":"<id>","verdict":"<verdict>","session_id":"<thread_id>","timestamp":"..."}`

---

## Copilot Backend Workflow

Use when `BACKEND="copilot"`.

### Step 1: Identify Task and Diff Base

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
```

### Step 2: Execute Review

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt.json}"

# Runtime config:
#   --spec <spec>           full spec (backend:model:effort), highest priority
#   FLOW_REVIEW_BACKEND     env (spec-form ok: copilot:claude-opus-4.5:xhigh)
#   FLOW_COPILOT_MODEL      env (fills missing model only; default gpt-5.2)
#   FLOW_COPILOT_EFFORT     env (fills missing effort only; default high)
#   per-task stored review  via `flowctl task set-backend` (highest if set)

$FLOWCTL copilot impl-review "$TASK_ID" --base "$DIFF_BASE" --receipt "$RECEIPT_PATH"
```

**Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK`.**

### Step 3: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from output
2. Fix code and run tests
3. Commit fixes
4. Re-run step 2 (receipt enables session continuity when `mode == "copilot"`)
5. Repeat until SHIP

### Step 4: Receipt

Receipt is written automatically by `flowctl copilot impl-review` when `--receipt` provided.
Format: `{"type":"impl_review","id":"<id>","mode":"copilot","verdict":"<verdict>","session_id":"<uuid>","model":"<model>","effort":"<effort>","spec":"copilot:<model>:<effort>","timestamp":"..."}`

The `spec` field is the canonical round-trippable form (added in fn-28.3). `model` + `effort` remain for backward compatibility.

Session resume guard: re-review only resumes the copilot session when the existing receipt at `$RECEIPT_PATH` has `mode == "copilot"`. A cross-backend switch (e.g., codex receipt at the same path) starts a fresh session.

---

## RepoPrompt Backend Workflow

Use when `BACKEND="rp"`.

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

## Requirements coverage (if spec has R-IDs)

If the task spec references an epic spec with numbered acceptance criteria like
`- **R1:** ...`, `- **R2:** ...`, produce a per-R-ID coverage table. Read the
epic spec's `## Acceptance` section (or the legacy `## Acceptance criteria`
heading — reviewer MUST tolerate both). If no R-IDs are present anywhere, skip
this block entirely — the rest of the review is unchanged.

For each R-ID, classify status:

| Status | Meaning |
|--------|---------|
| met | Diff clearly implements the requirement with appropriate tests/evidence |
| partial | Diff advances the requirement but leaves gaps (missing tests, missing edge case, missing integration point) |
| not-addressed | Diff does not advance this requirement at all |
| deferred | Spec explicitly defers this requirement to a later task/PR |

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
line entirely — both forms are valid. Deferred R-IDs are never listed here.

**Verdict gate:** any `not-addressed` R-ID that is NOT marked `deferred` in the
spec MUST flip the verdict to `NEEDS_WORK`. A clean coverage table (all `met`
or `deferred`) does not by itself force SHIP — the other review gates still
apply.

## Confidence calibration

Rate each finding on exactly one of these 5 discrete anchors. Do not use interpolated values (no 33, 80, 90).

| Anchor | Meaning |
|--------|---------|
| 100 | Verifiable from the code alone, zero interpretation. A definitive logic error (off-by-one in a tested algorithm, wrong return type, swapped arguments, clear type error). The bug is mechanical. |
| 75 | Full execution path traced: "input X enters here, takes this branch, reaches line Z, produces wrong result." Reproducible from the code alone. A normal caller will hit it. |
| 50 | Depends on conditions visible but not fully confirmable from this diff — e.g., whether a value can actually be null depends on callers not in the diff. Surfaces only as P0-escape or via soft-bucket routing. |
| 25 | Requires runtime conditions with no direct evidence — specific timing, specific input shapes, specific external state. |
| 0 | Speculative. Not worth filing. |

## Suppression gate

After all findings are collected:
1. Suppress findings below anchor 75.
2. **Exception:** P0 severity findings at anchor 50+ survive the gate. Critical-but-uncertain issues must not be silently dropped.
3. Report the suppressed count by anchor in a `Suppressed findings` section of the review output.

Example:

> Suppressed findings: 3 at anchor 50, 7 at anchor 25, 2 at anchor 0.

## Introduced vs pre-existing classification

For each finding, classify whether this branch's diff caused it:

- **introduced** — this branch caused the issue (new code, or a pre-existing bug that this diff amplified/exposed in a way that now matters)
- **pre_existing** — the issue was already present on the base branch; this diff did not touch it

Evidence methods (use whatever is cheapest):
- `git blame <file> <line>` to see when the line was last touched
- Read the base-branch version of the file directly
- Infer from diff context: a finding on an unchanged line in an unchanged file is `pre_existing` by default

**Verdict gate:** only `introduced` findings affect the verdict. A review whose sole surviving findings are all `pre_existing` MUST ship.

Report pre-existing findings in a dedicated non-blocking section:

```
## Pre-existing issues (not blocking this verdict)

- [P1, confidence 75, introduced=false] src/legacy.ts:102 — null dereference on empty array
- ...
```

Never delete pre-existing findings from the report — they stay visible for future prioritization.

## Protected artifacts

The following paths are flow-next / project-pipeline artifacts. Any finding recommending their deletion, gitignore, or removal MUST be discarded during synthesis. Do not flag these paths for cleanup under any circumstances:

- `.flow/*` — flow-next state, specs, tasks, epics, runtime
- `.flow/bin/*` — bundled flowctl
- `.flow/memory/*` — learnings store (pitfalls, conventions, decisions)
- `.flow/specs/*.md` — epic specs (decision artifacts)
- `.flow/tasks/*.md` — task specs (decision artifacts)
- `docs/plans/*` — plan artifacts (if project uses this convention)
- `docs/solutions/*` — solutions artifacts (if project uses this convention)
- `scripts/ralph/*` — Ralph harness (when present)

These files are intentionally committed. They are the pipeline's state, not clutter. An agent that deletes them destroys the project's planning trail and breaks Ralph autonomous runs.

If you notice genuine issues with content INSIDE these files (e.g., a spec that contradicts itself, a stale runtime value, a memory entry that's wrong), flag the content — not the file's existence.

**Protected-path filter.** Before emitting findings, scan each for recommendations to delete, gitignore, or `rm -rf` any path matching the protected list above. Drop those findings. If you drop any, report the drop count in a `Protected-path filter:` line in the review output (e.g. `Protected-path filter: dropped 2 findings`). Omit the line when nothing was dropped.

## Output Format

For each surviving `introduced` finding:
- **Severity**: Critical / Major / Minor / Nitpick (P0 / P1 / P2 / P3 accepted)
- **Confidence**: 0 / 25 / 50 / 75 / 100 (one of the five discrete anchors)
- **Classification**: introduced
- **File:Line**: Exact location
- **Problem**: What's wrong
- **Suggestion**: How to fix

Then list each `pre_existing` finding under a separate `## Pre-existing issues (not blocking this verdict)` heading using the compact form `[severity, confidence N, introduced=false] file:line — summary`.

After the findings list, emit:
- The `## Requirements coverage` table and `Unaddressed R-IDs:` line (only when the spec uses R-IDs; otherwise skip).
- A `Suppressed findings:` line tallying anchors dropped by the gate (omit when nothing was suppressed).
- A `Classification counts:` line tallying `introduced` vs `pre_existing` survivors, e.g. `Classification counts: 2 introduced, 4 pre_existing.`.
- A `Protected-path filter:` line tallying findings dropped by the protected-path filter (omit when nothing was dropped).

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
- **Missing changed files** - Add ALL changed files to selection

**Codex backend only:**
- **Using `--last` flag** - Conflicts with parallel usage; use `--receipt` instead
- **Direct codex calls** - Must use `flowctl codex` wrappers

**Copilot backend only:**
- **Direct copilot calls** - Must use `flowctl copilot` wrappers
- **Inventing `--model`/`--effort` CLI flags** - Use `--spec` for a full backend:model:effort value, or `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars to fill individual fields
- **Using `--continue`** - Conflicts with parallel usage; session resume uses `--resume=<uuid>` under the hood via `--receipt`
- **Assuming cross-backend session continuity** - Resume only works when prior receipt has `mode == "copilot"`
