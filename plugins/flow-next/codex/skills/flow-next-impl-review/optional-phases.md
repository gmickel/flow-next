# impl-review — optional phase machinery (loaded on demand)

> Loaded ONLY when the matching opt-in flag resolves true — `DEEP=true` (§Deep-Pass),
> `VALIDATE=true` (§Validator), `INTERACTIVE=true` (§Interactive Walkthrough). All three are
> default-OFF, so the default per-task review never loads any of this (~5.4k tokens saved/review).

**Contents**
- [Phase ordering & flag-combination matrix](#phase-ordering--flag-combination-matrix-fn-324)
- [Deep-Pass Phase (`--deep`)](#deep-pass-phase-fn-322---deep--all-backends)
- [Validator Pass (`--validate`)](#validator-pass-fn-321---validate--all-backends)
- [Interactive Walkthrough Phase (`--interactive`)](#interactive-walkthrough-phase-fn-323---interactive--all-backends)

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

Mode split (fn-113): steps 2-3 mutate the receipt ONLY under autonomy markers
(FLOW_RALPH=1 / REVIEW_RECEIPT_PATH set / FLOW_AUTONOMOUS=1). In an interactive
session deep/validate return raw JSON with host_judges: true and leave the
receipt unchanged - the host judges merge/promotion/survivors from that JSON
instead of re-reading the receipt. Both paths are documented per phase below.

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

| Combo | Phases executed |
|------------------------------------|--------------------------|
| (default, no flags) | 1 → 5 → 6 |
| `--validate` | 1 → 3 → 5 → 6 |
| `--deep` | 1 → 2 → 5 → 6 |
| `--interactive` | 1 → 4 → 5 → 6 |
| `--validate --deep` | 1 → 2 → 3 → 5 → 6 |
| `--validate --interactive` | 1 → 3 → 4 → 5 → 6 |
| `--deep --interactive` | 1 → 2 → 4 → 5 → 6 |
| `--validate --deep --interactive` | 1 → 2 → 3 → 4 → 5 → 6 |

**Receipt composition:** each phase appends its own block to the receipt
without mutating any other block. The receipt schema is additive — old
Ralph scripts read `verdict` / `mode` / `session_id` and ignore unknown
keys.

| Phase | Receipt keys written | Verdict effect |
|-------|----------------------|----------------|
| 1. Primary | `type`, `id`, `mode`, `verdict`, `session_id`, `timestamp`, `model`, `effort`, `spec` | Sets `verdict` |
| 2. Deep | `deep_passes`, `deep_findings_count`, `cross_pass_promotions`, `deep_timestamp`, optional `verdict_before_deep` | SHIP → NEEDS_WORK (upgrade only; never downgrades) |
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

Compute `SELECTED_PASSES` here (the flags `DEEP` / `DEEP_PASSES` and
`BASE_COMMIT` were parsed in SKILL.md Step 0) using `flowctl review-deep-auto`
against the changed-file list. Explicit CSV form
(`--deep=adversarial,security`) overrides auto-enable.

```bash
# If explicit CSV provided, use those passes verbatim.
# Otherwise: adversarial always + security/performance auto-enabled by
# changed-file globs via `flowctl review-deep-auto`.
if [[ -n "$DEEP_PASSES" ]]; then
  SELECTED_PASSES="${DEEP_PASSES//,/ }"
else
  # Determine changed files for auto-enable heuristic
  if [[ -n "$BASE_COMMIT" ]]; then
    CHANGED="$(git diff --name-only "$BASE_COMMIT"..HEAD)"
  else
    DIFF_BASE=main; git rev-parse main >/dev/null 2>&1 || DIFF_BASE=master
    CHANGED="$(git diff --name-only "$DIFF_BASE"..HEAD)"
  fi
  SELECTED_PASSES="$(printf '%s\n' "$CHANGED" | $FLOWCTL review-deep-auto)"
fi
echo "Deep passes selected: $SELECTED_PASSES"
```

See [deep-passes.md](deep-passes.md) for the pass prompt templates, the
auto-enable globs, and merge/promotion rules.

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
ROUTE="$($FLOWCTL review-route ${TASK_ID:+"$TASK_ID"} --json)"   # pure: canonical TASK_ID + receipt path (no rotation, no state change)
TASK_ID="$(jq -r '.task_id // empty' <<<"$ROUTE")"
RECEIPT_PATH="$(jq -r '.receipt_path' <<<"$ROUTE")"
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
      # findings block), send via `rp chat-send` (NO --new-chat). Classic uses
      # --tab "$T"; CE uses --context-id "$T" --chat-id "$CHAT_ID" --mode review,
      # parse findings with the same header regex flowctl uses,
      # merge into receipt manually (or via a shared helper).
      # See deep-passes.md for template markers.
      :
      ;;
    host)
      # fn-123 R5: no flowctl subprocess for host. Dispatch each selected
      # pass as ANOTHER fresh read-only host-native reviewer subagent with
      # the SAME cross-family pin as the primary review (workflow-host.md
      # Step 1). Give it the pass-specific prompt from deep-passes.md plus
      # the primary findings block; parse its findings and merge them into
      # the receipt yourself (deep_findings_count / cross_pass_promotions,
      # same additive fields as D.5). If a fresh subagent cannot be
      # dispatched, do NOT silently skip: interactive -> ask whether to
      # continue without deep passes; autonomous -> NEEDS_HUMAN.
      :
      ;;
  esac
done
```

### Step D.4: Re-compute verdict after merge

Mode split (fn-113): under autonomy markers (`FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH`
set, or `FLOW_AUTONOMOUS=1`) each `deep-pass` call writes the merged receipt in
place and the final verdict is read back from the receipt as below. In an
INTERACTIVE session the call instead returns raw findings with `host_judges: true`
and does NOT mutate the receipt - read the JSON output, judge merge/promotion
yourself, and record your verdict. The read-back applies to the autonomous path:

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
ROUTE="$($FLOWCTL review-route ${TASK_ID:+"$TASK_ID"} --json)"   # pure: canonical TASK_ID + receipt path (no rotation, no state change)
TASK_ID="$(jq -r '.task_id // empty' <<<"$ROUTE")"
RECEIPT_PATH="$(jq -r '.receipt_path' <<<"$ROUTE")"
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
    # Classic uses --tab "$T"; CE uses --context-id "$T" plus chat identity.
    # Parse the response lines with the same regex flowctl uses:
    #   `<id>: validated: <true|false> -- <reason>`
    # Then recompute dropped/kept counts and merge into the receipt by hand
    # (or via a shared helper). See validate-pass.md for the template.
    cat /path/to/validate-pass.md | sed 's|<!-- FINDINGS_BLOCK -->|'"$(cat render_findings.md)"'|' > /tmp/validator.md
    if [[ "$RP_MODE" == "ce" ]]; then
      VALIDATOR_RESPONSE="$($FLOWCTL rp chat-send --window "$W" --context-id "$T" --chat-id "$CHAT_ID" --mode review --message-file /tmp/validator.md)"
    else
      VALIDATOR_RESPONSE="$($FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file /tmp/validator.md)"
    fi
    # Parse lines matching /^[>*_` ]*<id>[\s*_`]*:[\s*_`]*validated[\s*_`]*:[\s*_`]*(true|false)/
    # and update receipt's validator block accordingly.
    ;;
  host)
    # fn-123 R5: no flowctl subprocess for host. Dispatch the validator as a
    # fresh read-only host-native subagent with the SAME cross-family pin as
    # the primary review (workflow-host.md Step 1), prompted from
    # validate-pass.md with the findings block injected. Parse its
    # `<id>: validated: <true|false> -- <reason>` lines yourself, recompute
    # dropped/kept counts, and merge the validator block into the receipt.
    # If a fresh subagent cannot be dispatched, do NOT silently skip:
    # interactive -> ask; autonomous -> NEEDS_HUMAN.
    ;;
esac
```

### Step V.3: Re-compute verdict from validator result

Mode split (fn-113): under autonomy markers the `codex validate` and
`copilot validate` subcommands merge the validator result into the receipt
and upgrade verdict to SHIP if all findings dropped - the read-back below
applies there. In an INTERACTIVE session the call returns raw validator
decisions with `host_judges: true` and does NOT mutate the receipt: read the
JSON output (`.decisions` - an object keyed by finding id, each value `{validated, reason}` - plus `.dropped`/`.kept`), judge which findings
survive yourself, and record your verdict. Autonomous read-back:

```bash
NEW_VERDICT="$(jq -r '.verdict' "$RECEIPT_PATH" 2>/dev/null || echo NEEDS_WORK)"
DROPPED="$(jq -r '.validator.dropped // 0' "$RECEIPT_PATH" 2>/dev/null || echo 0)"
KEPT="$(jq -r '.validator.kept // 0' "$RECEIPT_PATH" 2>/dev/null || echo 0)"

echo "Validator: dropped=$DROPPED kept=$KEPT verdict=$NEW_VERDICT"

if [[ "$NEW_VERDICT" == "SHIP" ]]; then
  # All findings dropped — verdict upgraded. Done, no fix loop. This exit
  # never reaches the backend workflow's final release step, so release the
  # optional-phase lease here (PR #392): OWNING_RID is restated as a LITERAL
  # — the fan-out rid from the codex phase-one JSON, or the host reservation
  # id. 0 phases means nothing was held.
  OWNING_RID="<owning rid>"
  if [ -n "$OPTIONAL_PHASES_COUNT" ] && [ "$OPTIONAL_PHASES_COUNT" != "0" ]; then
    # A failed release (rid mismatch, persistence failure) is not success:
    # the scope would stay fenced until the lease TTL. Escalate instead.
    "$FLOWCTL" review-route ${TASK_ID:+"$TASK_ID"} --receipt "$RECEIPT_PATH" --release-phases --rid "$OWNING_RID" --json || {
      echo "NEEDS_HUMAN: optional-phase lease release failed (rid $OWNING_RID, receipt $RECEIPT_PATH) — the verdict is SHIP but the scope stays fenced until the lease TTL; repair with review-route --release-phases --rid <owning rid>" >&2
      exit 4
    }
  fi
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
loop in [walkthrough.md](walkthrough.md) drives `plain-text numbered prompt`; flowctl provides
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

The skill loops over findings and calls the plain-text numbered prompt (see
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

**Lease renewal while waiting on a human (PR #392).** A walkthrough has no
time bound — it blocks once per finding on a reply — but the optional-phase
lease expires on the liveness bound. When the lease is held (an optional flag
is enabled), renew it before EACH plain-text numbered prompt; a hold for the same
owning rid is a renewal. A refused renewal means another coordinator's live
lease or reservation owns the scope now: stop the walkthrough and re-route
instead of writing over the newer review. Restate the count and the rid as
literals (shell state does not survive across prompt turns).

```bash
OPTIONAL_PHASES_COUNT="<count printed by Step 0>"
OWNING_RID="<owning rid>"
if [ -n "$OPTIONAL_PHASES_COUNT" ] && [ "$OPTIONAL_PHASES_COUNT" != "0" ]; then
  "$FLOWCTL" review-route ${TASK_ID:+"$TASK_ID"} --receipt "$RECEIPT_PATH" --hold-phases "$OPTIONAL_PHASES_COUNT" --rid "$OWNING_RID" --json || {
    echo "NEEDS_HUMAN: optional-phase lease renewal refused (rid $OWNING_RID) — another coordinator owns this scope; walkthrough stopped" >&2
    exit 4
  }
fi
```

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
