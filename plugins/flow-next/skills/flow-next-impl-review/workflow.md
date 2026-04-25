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

## Phase ordering & flag-combination matrix (fn-32.4)

The opt-in flags (`--validate`, `--deep`, `--interactive`) layer on top of the
primary review. When multiple are set, phases run in a fixed order:

```
1. Primary review (always)
2. If --deep:        run deep passes in same session → merge findings into receipt
3. If --validate:    validator re-checks merged findings → drops false positives
4. If --interactive: user walks surviving findings → Apply/Defer/Skip/Acknowledge
5. Verdict           computed over surviving findings (deep may upgrade SHIP→NEEDS_WORK;
                     validate may upgrade NEEDS_WORK→SHIP; walkthrough never flips)
6. Receipt           each phase writes its own additive block without disturbing others
```

**Why this order:**
- Deep runs before validate: deep expands the finding superset; validator
  filters the (larger) merged set in a single pass — cheaper than running
  validator twice (once for primary, once for deep).
- Validate runs before interactive: the user walks only validated findings,
  reducing decision burden and keeping per-finding quality high.
- Interactive is always last: it consumes the fully-merged, fully-validated
  set; it never flips the verdict, only sorts findings into Apply / Defer /
  Skip / Acknowledge buckets.

**Flag combination matrix:**

| Combo                              | Phases executed          |
|------------------------------------|--------------------------|
| (default, no flags)                | 1 → 5 → 6                |
| `--validate`                       | 1 → 3 → 5 → 6            |
| `--deep`                           | 1 → 2 → 5 → 6            |
| `--interactive`                    | 1 → 4 → 5 → 6            |
| `--validate --deep`                | 1 → 2 → 3 → 5 → 6        |
| `--validate --interactive`         | 1 → 3 → 4 → 5 → 6        |
| `--deep --interactive`             | 1 → 2 → 4 → 5 → 6        |
| `--validate --deep --interactive`  | 1 → 2 → 3 → 4 → 5 → 6    |

**Receipt composition:** each phase appends its own block to the receipt
without mutating any other block. The receipt schema is additive — old
Ralph scripts read `verdict` / `mode` / `session_id` and ignore unknown
keys.

| Phase | Receipt keys written | Verdict effect |
|-------|----------------------|----------------|
| 1. Primary   | `type`, `id`, `mode`, `verdict`, `session_id`, `timestamp`, `model`, `effort`, `spec` | Sets `verdict` |
| 2. Deep      | `deep_passes`, `deep_findings_count`, `cross_pass_promotions`, `deep_timestamp`, optional `verdict_before_deep` | SHIP → NEEDS_WORK (upgrade only; never downgrades) |
| 3. Validator | `validator: {dispatched, dropped, kept, reasons}`, `validator_timestamp`, optional `verdict_before_validate` | NEEDS_WORK → SHIP (upgrade only when all drop; never downgrades) |
| 4. Walkthrough | `walkthrough: {applied, deferred, skipped, acknowledged, lfg_rest}`, `walkthrough_timestamp` | None — walkthrough never flips verdict |

**Empty-block invariants:**
- When no `--validate`, the receipt has **no** `validator` key, **no**
  `validator_timestamp`, and **no** `verdict_before_validate`.
- When no `--deep`, the receipt has **no** `deep_passes`, **no**
  `deep_findings_count`, **no** `cross_pass_promotions`, **no**
  `deep_timestamp`, and **no** `verdict_before_deep`.
- When no `--interactive`, the receipt has **no** `walkthrough` and
  **no** `walkthrough_timestamp`.
- When `--validate` ran with zero dispatched findings, an empty validator
  block (`{dispatched: 0, dropped: 0, kept: 0, reasons: []}`) + its
  timestamp are still written — this keeps the receipt shape deterministic
  for consumers.
- `verdict_before_validate` / `verdict_before_deep` are only written when
  their phase actually upgraded the verdict; otherwise absent.

**Ralph compatibility:** the receipt-gate logic reads `verdict`, `mode`,
and `session_id`. All new fields are optional and ignored by older Ralph
scripts. `FLOW_VALIDATE_REVIEW=1` and `FLOW_REVIEW_DEEP=1` are the only
env opt-ins; `--interactive` hard-errors in Ralph mode (see SKILL.md
Step 0).

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

## Deep-Pass Phase (fn-32.2 --deep) — all backends

When `DEEP=true`, run the selected specialized passes after the primary
review completes — regardless of verdict. Each pass continues the primary
backend session (via receipt `session_id`) so the model already has the
diff + primary findings loaded; deep-pass prompts re-use that context to
probe for what the primary framing may have missed.

**Preserved by default:** when `DEEP=false` (or `--deep` not passed and
`FLOW_REVIEW_DEEP` unset), this entire section is skipped — primary
Carmack flow is unchanged.

### Step D.1: Determine which passes to run

The skill layer computes `SELECTED_PASSES` in Step 0 (see SKILL.md) using
`flowctl review-deep-auto` against the changed-file list. Explicit CSV
form (`--deep=adversarial,security`) overrides auto-enable.

Adversarial always runs. Security auto-enables for auth / routes /
middleware / session / token / `.env` / workflow paths. Performance
auto-enables for migrations / SQL / cache / jobs paths. See
[deep-passes.md](deep-passes.md) for the full pattern list.

### Step D.2: Extract primary findings

Parse the primary review output into a JSON-lines file
(`/tmp/primary-findings.jsonl`) using the same format as the validator
pass — one object per line, with at least `id`, plus `severity`,
`confidence`, `classification`, `file`, `line`, `title`, `suggested_fix`.

The deep-pass prompt embeds these as context so the pass avoids
re-flagging issues the primary already caught.

### Step D.3: Dispatch each pass

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt.json}"
PRIMARY_FINDINGS="/tmp/primary-findings.jsonl"

for pass in $SELECTED_PASSES; do
  case "$BACKEND" in
    codex)
      $FLOWCTL codex deep-pass \
        --pass "$pass" \
        --primary-findings "$PRIMARY_FINDINGS" \
        --receipt "$RECEIPT_PATH" \
        --json
      ;;
    copilot)
      $FLOWCTL copilot deep-pass \
        --pass "$pass" \
        --primary-findings "$PRIMARY_FINDINGS" \
        --receipt "$RECEIPT_PATH" \
        --json
      ;;
    rp)
      # RP: same-chat session continuity is automatic. Render the
      # pass-specific prompt from deep-passes.md (inject primary
      # findings block), send via `rp chat-send` (NO --new-chat),
      # parse findings with the same header regex flowctl uses,
      # merge into receipt manually (or via a shared helper).
      # See deep-passes.md for template markers.
      :
      ;;
  esac
done
```

### Step D.4: Re-compute verdict after merge

Each `deep-pass` call writes the merged receipt in place. Final verdict
is read back from the receipt:

```bash
NEW_VERDICT="$(jq -r '.verdict' "$RECEIPT_PATH" 2>/dev/null || echo NEEDS_WORK)"
DEEP_COUNTS="$(jq -c '.deep_findings_count // {}' "$RECEIPT_PATH")"
PROMOTIONS="$(jq -c '.cross_pass_promotions // []' "$RECEIPT_PATH")"

echo "Deep passes: $SELECTED_PASSES"
echo "Deep findings per pass: $DEEP_COUNTS"
echo "Cross-pass promotions: $PROMOTIONS"
echo "VERDICT=$NEW_VERDICT"
```

If the verdict was upgraded (`SHIP → NEEDS_WORK`), the receipt records
`verdict_before_deep` for telemetry. Verdict is **never** downgraded by
deep-pass — that is the validator's job.

### Step D.5: Receipt contract (additive fields)

After deep passes run, the receipt carries:

```json
{
  "type": "impl_review",
  "id": "fn-32.2",
  "mode": "codex",
  "verdict": "NEEDS_WORK",
  "verdict_before_deep": "SHIP",
  "session_id": "019ba...",
  "deep_passes": ["adversarial", "security"],
  "deep_findings_count": {"adversarial": 2, "security": 1},
  "cross_pass_promotions": [
    {"id": "f1", "from": 50, "to": 75, "pass": "adversarial"}
  ],
  "deep_timestamp": "2026-04-24T10:10:00Z"
}
```

All fields are **additive** — existing Ralph scripts and receipt
consumers that don't know about deep-pass read `verdict` as before and
ignore the new keys.

---

## Validator Pass (fn-32.1 --validate) — all backends

When `VALIDATE=true` AND the primary review verdict is `NEEDS_WORK`, run a
validator pass before the fix loop. The validator re-checks each finding
against the current code and drops clear false positives. If all findings
drop, the verdict upgrades to `SHIP` automatically.

**Preserved by default:** when `VALIDATE=false` (or `--validate` not passed
and `FLOW_VALIDATE_REVIEW` unset), this entire section is skipped — the
primary-review Carmack flow is unchanged.

### Step V.1: Extract findings from the primary review

Parse the primary review output into a JSON-lines `findings-file`. Required
key: `id`. Recommended keys: `severity`, `confidence`, `classification`,
`file`, `line`, `title`, `suggested_fix`. One JSON object per line.

The primary review output uses the shared format from earlier in this doc
(Severity / Confidence / File:Line / Problem / Suggestion per finding). Map
each entry to a line in `/tmp/review-findings.jsonl` — use the finding's
index-in-report (`f1`, `f2`, ...) as the id when the reviewer didn't supply
one. Example:

```jsonl
{"id":"f1","severity":"P0","confidence":75,"classification":"introduced","file":"src/auth.ts","line":42,"title":"null deref in middleware","suggested_fix":"guard req.user before use"}
{"id":"f2","severity":"P1","confidence":50,"classification":"introduced","file":"src/db.ts","line":10,"title":"unchecked result","suggested_fix":"await err check"}
```

If the primary review produced zero findings (shouldn't happen on
`NEEDS_WORK` — a sign of a parse miss), skip the validator and treat as a
parse error; fall through to normal fix loop.

### Step V.2: Dispatch the validator pass

```bash
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt.json}"
FINDINGS_FILE="/tmp/review-findings.jsonl"

case "$BACKEND" in
  codex)
    VALIDATOR_JSON="$($FLOWCTL codex validate \
      --findings-file "$FINDINGS_FILE" \
      --receipt "$RECEIPT_PATH" \
      --json 2>&1)"
    ;;
  copilot)
    VALIDATOR_JSON="$($FLOWCTL copilot validate \
      --findings-file "$FINDINGS_FILE" \
      --receipt "$RECEIPT_PATH" \
      --json 2>&1)"
    ;;
  rp)
    # RP: same-chat session continuity is automatic. Build a validator prompt
    # from validate-pass.md and send it via `rp chat-send` (NO --new-chat).
    # Parse the response lines with the same regex flowctl uses:
    #   `<id>: validated: <true|false> -- <reason>`
    # Then recompute dropped/kept counts and merge into the receipt by hand
    # (or via a shared helper). See validate-pass.md for the template.
    cat /path/to/validate-pass.md | sed 's|<!-- FINDINGS_BLOCK -->|'"$(cat render_findings.md)"'|' > /tmp/validator.md
    VALIDATOR_RESPONSE="$($FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file /tmp/validator.md)"
    # Parse lines matching /^[>*_` ]*<id>[\s*_`]*:[\s*_`]*validated[\s*_`]*:[\s*_`]*(true|false)/
    # and update receipt's validator block accordingly.
    ;;
esac
```

### Step V.3: Re-compute verdict from validator result

The `codex validate` and `copilot validate` subcommands already merge the
validator result into the receipt and upgrade verdict to SHIP if all
findings dropped. Read the updated receipt to pick up the new verdict:

```bash
NEW_VERDICT="$(jq -r '.verdict' "$RECEIPT_PATH" 2>/dev/null || echo NEEDS_WORK)"
DROPPED="$(jq -r '.validator.dropped // 0' "$RECEIPT_PATH" 2>/dev/null || echo 0)"
KEPT="$(jq -r '.validator.kept // 0' "$RECEIPT_PATH" 2>/dev/null || echo 0)"

echo "Validator: dropped=$DROPPED kept=$KEPT verdict=$NEW_VERDICT"

if [[ "$NEW_VERDICT" == "SHIP" ]]; then
  # All findings dropped — verdict upgraded. Done, no fix loop.
  exit 0
fi

# NEEDS_WORK remains — surviving findings go into the fix loop below,
# limited to those the validator kept.
```

### Step V.4: Receipt contract (unchanged shape, new fields)

After the validator pass, the receipt carries an additional `validator`
object and (when upgraded) a `verdict_before_validate` field:

```json
{
  "type": "impl_review",
  "id": "fn-32.1",
  "mode": "codex",
  "verdict": "SHIP",
  "verdict_before_validate": "NEEDS_WORK",
  "session_id": "019ba...",
  "validator": {
    "dispatched": 3,
    "dropped": 3,
    "kept": 0,
    "reasons": [
      {"id": "f1", "file": "src/x.ts", "line": 42, "reason": "null check already at line 40"},
      {"id": "f2", "file": "src/y.ts", "line": 10, "reason": "error is propagated via ? operator"},
      {"id": "f3", "file": "src/z.ts", "line": 5,  "reason": "suggested fix misreads TS narrowing"}
    ]
  },
  "validator_timestamp": "2026-04-24T10:05:00Z"
}
```

All fields are **additive** — existing Ralph scripts and receipt consumers
that don't know about `validator` read `verdict` as before and ignore the
new keys. Verdict never downgrades; the validator only drops findings,
never invents them.

---

## Interactive Walkthrough Phase (fn-32.3 --interactive) — all backends

When `INTERACTIVE=true` AND the primary review verdict is `NEEDS_WORK`
(still NEEDS_WORK after validator if `--validate` also set), walk through
each finding with the user before entering the fix loop. The skill-side
loop in [walkthrough.md](walkthrough.md) drives `AskUserQuestion` (sync-codex.sh
rewrites to `request_user_input` in the Codex mirror); flowctl provides
helpers for the defer sink + receipt merge.

**Preserved by default:** when `INTERACTIVE=false`, this entire section is
skipped — the fix loop runs against all surviving findings as before.
**Ralph-incompatible:** SKILL.md hard-errors at entry if
`REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1` is set. No receipt is written in
that error path.

### Step W.1: Extract findings for the walkthrough

Reuse the validator pass extraction (Step V.1) — same JSON-Lines shape,
same `/tmp/walkthrough-findings.jsonl`. If `--validate` already ran, use
the kept set; if `--deep` also ran, use the merged+promoted set.

If zero findings remain (e.g., all validator-dropped), skip the
walkthrough — nothing to ask about. Verdict should already be SHIP.

### Step W.2: Present each finding + record decision

The skill loops over findings and calls the platform blocking tool (see
walkthrough.md for platform mapping). For each finding, collect one of:

- Apply (implement fix)
- Defer (record in sink)
- Skip (ignore)
- Acknowledge (note no action)
- LFG the rest (auto-classify remainder)

Write per-bucket JSONL files for downstream helpers:

```bash
/tmp/walkthrough-apply.jsonl
/tmp/walkthrough-defer.jsonl
/tmp/walkthrough-skip.jsonl
/tmp/walkthrough-ack.jsonl
```

"LFG the rest" auto-classifies: P0/P1 @ confidence ≥ 75 → Apply;
otherwise → Defer.

### Step W.3: Append deferred findings to sink

```bash
DEFER_COUNT=$(wc -l < /tmp/walkthrough-defer.jsonl 2>/dev/null || echo 0)
if [[ "$DEFER_COUNT" -gt 0 ]]; then
  $FLOWCTL review-walkthrough-defer \
    --findings-file /tmp/walkthrough-defer.jsonl \
    --receipt "$RECEIPT_PATH" \
    --json
fi
```

The helper derives the branch slug via `git branch --show-current`,
creates `.flow/review-deferred/` if absent, and appends a timestamped
section to `.flow/review-deferred/<branch-slug>.md`.

### Step W.4: Record walkthrough counts in receipt

```bash
$FLOWCTL review-walkthrough-record \
  --receipt "$RECEIPT_PATH" \
  --applied  "$(wc -l < /tmp/walkthrough-apply.jsonl 2>/dev/null || echo 0)" \
  --deferred "$(wc -l < /tmp/walkthrough-defer.jsonl 2>/dev/null || echo 0)" \
  --skipped  "$(wc -l < /tmp/walkthrough-skip.jsonl  2>/dev/null || echo 0)" \
  --acknowledged "$(wc -l < /tmp/walkthrough-ack.jsonl 2>/dev/null || echo 0)" \
  --lfg-rest "${LFG_USED:-false}" \
  --json
```

Receipt gains:

```json
{
  "walkthrough": {
    "applied": 3,
    "deferred": 2,
    "skipped": 1,
    "acknowledged": 0,
    "lfg_rest": false
  },
  "walkthrough_timestamp": "2026-04-24T18:42:00Z"
}
```

Additive — existing consumers ignore the new key. Walkthrough never
flips the verdict; it only sorts findings.

### Step W.5: Fixer dispatch (Apply list only)

If `/tmp/walkthrough-apply.jsonl` is non-empty, dispatch the worker
agent (or an inline fixer) restricted to those findings. Do **not**
re-run the primary review inside this session — commit fixes and exit.
Re-review is a separate user invocation.

If the Apply list is empty, exit without dispatching — the user chose
to defer / skip / acknowledge everything. The sink captures the
deferred items for later revisit.

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
