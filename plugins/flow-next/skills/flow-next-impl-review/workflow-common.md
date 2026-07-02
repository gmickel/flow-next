# Implementation Review Workflow — Common

## Philosophy

The reviewer model only sees selected files. RepoPrompt's Builder discovers context you'd miss (rp backend). Codex, Copilot, and Cursor use context hints from flowctl (codex/copilot/cursor backends).

---

## Phase 0: Backend Detection

**Run this first. Do not skip.**

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# RepoPrompt is macOS-only (rp-cli bridges the GUI). Only offer the rp path
# when it can actually run: on macOS, or when rp-cli is already on PATH.
if [ "$(uname 2>/dev/null)" = "Darwin" ] || command -v rp-cli >/dev/null 2>&1; then
  RP_ELIGIBLE=1
else
  RP_ELIGIBLE=0
fi

# Priority: --review flag > per-task/spec `review` override > env > config (flag parsed in SKILL.md).
# FIRST resolve the review-target id from $ARGUMENTS — the `fn-N.M` task / `fn-N` spec being
# reviewed. This is BEFORE the later `TASK_ID` parse (Workflow Step 0), so extract it HERE (do
# NOT rely on `$TASK_ID`, which is still unset at Phase 0); leave empty for a standalone no-spec
# diff review. Passing it lets a per-task `review: <backend>:...` override route to the RIGHT
# backend before dispatch, even when it differs from the project default. Empty → env/config
# unchanged (no regression).
REVIEW_ID="${1:-}"   # the review-target positional arg (fn-N.M task / fn-N spec); empty for a standalone diff
# Text output is bare backend name for back-compat grep. The same command in --json mode returns
# {backend, spec, model, effort, source} — use that if you need the model / effort resolved.
BACKEND=$($FLOWCTL review-backend "$REVIEW_ID")

if [[ "$BACKEND" == "ASK" ]]; then
  echo "Error: No review backend configured."
  if [ "$RP_ELIGIBLE" = 1 ]; then
    echo "Run /flow-next:setup to configure, or pass --review=rp|codex|copilot|cursor|none"
  else
    echo "Run /flow-next:setup to configure, or pass --review=codex|copilot|cursor|none"
  fi
  exit 1
fi

if [ "$RP_ELIGIBLE" = 1 ]; then
  echo "Review backend: $BACKEND (override: --review=rp|codex|copilot|cursor|none)"
else
  echo "Review backend: $BACKEND (override: --review=codex|copilot|cursor|none)"
fi
```

**Spec-form env var (optional):** `FLOW_REVIEW_BACKEND` accepts bare or full spec:

```bash
# Bare backend (back-compat)
FLOW_REVIEW_BACKEND=codex $FLOWCTL codex impl-review "$TASK_ID" --receipt "$RECEIPT_PATH"

# Full spec — model + effort resolved automatically
FLOW_REVIEW_BACKEND=codex:gpt-5.5:xhigh $FLOWCTL codex impl-review "$TASK_ID" --receipt "$RECEIPT_PATH"
FLOW_REVIEW_BACKEND=copilot:claude-opus-4.5 $FLOWCTL copilot impl-review "$TASK_ID" --receipt "$RECEIPT_PATH"
# Cursor folds effort into the model name (no :<effort>):
FLOW_REVIEW_BACKEND=cursor:gpt-5.5-high $FLOWCTL cursor impl-review "$TASK_ID" --base "$DIFF_BASE" --receipt "$RECEIPT_PATH"

# Or pass spec directly (preferred for one-offs, avoids env pollution):
$FLOWCTL codex impl-review "$TASK_ID" --spec "codex:gpt-5.5:xhigh" --receipt "$RECEIPT_PATH"
```

Per-task `review` (set via `flowctl task set-backend`) overrides env.

**If backend is "none"**: Skip review, inform user, and exit cleanly (no error).

**Then branch to the backend-specific workflow file:**

| `$BACKEND` | Read |
|------------|------|
| `codex`    | [workflow-codex.md](workflow-codex.md) |
| `copilot`  | [workflow-copilot.md](workflow-copilot.md) |
| `cursor`   | [workflow-cursor.md](workflow-cursor.md) |
| `rp`       | [workflow-rp.md](workflow-rp.md) |

Only the file for the active backend should enter context. Do not read the other backend files.

**Foreground rule — review CLI calls are blocking.** Run every `flowctl <backend> …` review command (`impl-review` / `plan-review` / `completion-review` / `validate` / `deep-pass`) as a single **foreground** Bash call with a generous timeout (10 minutes; verdicts typically land in 1–7). **Never** launch one with `run_in_background` + a monitor/poll — a background completion does not reliably resume a subagent context (observed in the fn-78 dogfood: a worker idled on an already-finished cursor review until manually poked), and the call is bounded, so blocking is safe and simpler. (The one sanctioned background launch stays codex-delegation's `codex exec` implementation offload — a different pattern that polls a result file in foreground calls; it is not a review command.)

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
| Any `.flow/specs/*.md` / `.flow/specs/*.json` / `.flow/tasks/*.md` / legacy `.flow/epics/*.json` | REVIEW |
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
    cursor)
      $FLOWCTL cursor deep-pass \
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

The primary review output uses the shared format from the per-backend
workflow (Severity / Confidence / File:Line / Problem / Suggestion per
finding). Map each entry to a line in `/tmp/review-findings.jsonl` — use
the finding's index-in-report (`f1`, `f2`, ...) as the id when the reviewer
didn't supply one. Example:

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
  cursor)
    VALIDATOR_JSON="$($FLOWCTL cursor validate \
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
rewrites to a plain-text numbered prompt in the Codex mirror); flowctl provides
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

## Anti-patterns (all backends)

- **Reviewing yourself** - You coordinate; the backend reviews
- **No receipt** - If REVIEW_RECEIPT_PATH is set, you MUST write receipt
- **Ignoring verdict** - Must extract and act on verdict tag
- **Mixing backends** - Stick to one backend for the entire review session
- **Backgrounding the review CLI** - Never `run_in_background` + monitor/poll a `flowctl <backend>` review call; run it as one blocking foreground Bash call with a long timeout (Foreground rule, Phase 0)

Backend-specific anti-patterns live in each `workflow-<backend>.md` file.
