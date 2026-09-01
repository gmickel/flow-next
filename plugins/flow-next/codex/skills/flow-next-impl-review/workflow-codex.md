# Implementation Review Workflow — Codex Backend

Use when `BACKEND="codex"`. Prerequisite: Phase 0 backend detection in [workflow-common.md](workflow-common.md) has resolved `BACKEND`, `FLOWCTL`, and (optionally) `TASK_ID` / `BASE_COMMIT`.

## Critical Rules (codex backend)

1. Use the `$FLOWCTL codex` review commands exclusively — never call `codex` directly
2. **The FIRST review round of a scope is the two-phase fan-out**: `impl-review-fanout` (dispatch), your merge, `impl-review-fanout-finalize` (finalize). Re-review rounds after fixes are a single `impl-review` with `--receipt`
3. Pass `--receipt` throughout — the finalize writes the merged receipt; re-reviews resume from it
4. Parse verdict from command output

## Step 1: Identify Task and Diff Base

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

## Step 2: Fan-out dispatch (phase one — first round only)

The first round fans out **three concurrent reviewer draws** — one per fixed
axis lens (`correctness`, `contracts`, `integration`), each differing from the
base prompt by exactly one added axis line, on the same resolved backend/model
the single dispatch uses. The fan-out is TWO blocking foreground flowctl
invocations with your merge between them; this is the first.

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt${TASK_ID:+-${TASK_ID}}.json}"  # fn-90 R5: task-scoped default (concurrent tasks no longer collide); explicit REVIEW_RECEIPT_PATH still wins

# RESUME GATE (fan-out is first-round only): a fresh invocation resuming a
# scope mid-fix-loop — e.g. after a lost coordinator context — arrives here
# with a receipt whose verdict is still open (NEEDS_WORK / NEEDS_HUMAN). That
# is round 2+: skip Steps 2-4 entirely (dispatch, merge, finalize — they need
# a rid and merged file no skipped phase produced) and go straight to Step
# 5.4's single-dispatch re-review. A receipt whose verdict is closed (SHIP /
# MAJOR_RETHINK) or unreadable is a COMPLETED earlier scope left at this path —
# stale input for a new round, never a resume: rotate it aside so the fresh
# fan-out starts clean instead of bouncing off flowctl's first-round guard or
# injecting stale findings. (Concurrent standalone scopes should set an
# explicit per-scope REVIEW_RECEIPT_PATH — the standalone default path is
# shared.) flowctl's guard remains the no-cost exit-2 backstop.
RESUMED=0
if [ -f "$RECEIPT_PATH" ]; then
  # Identity first (PR #392 r10): only OUR scope's open receipt is a resume —
  # another scope's receipt at a shared path must never inject its session or
  # findings into this review.
  case "$(jq -r --arg s "${TASK_ID:-branch}" 'if (.id // "") == $s then (.verdict // "") else "FOREIGN" end' "$RECEIPT_PATH" 2>/dev/null)" in
    NEEDS_WORK|NEEDS_HUMAN)
      RESUMED=1
      echo "RESUMED SCOPE — receipt carries an active fix loop; skip Steps 2-4, go to Step 5.4 (single-dispatch re-review)" ;;
    *)
      # Closed, unreadable, or another scope's receipt: stale input for this
      # round — rotate aside, start clean.
      mv "$RECEIPT_PATH" "$RECEIPT_PATH.prev" ;;
  esac
fi

# Standalone branch reviews leave TASK_ID empty — OMIT the positional entirely
# (a quoted "" is rejected as an invalid task id; standalone mode needs no task arg).
# Subcommand tokens stay LITERAL on the command line (the Ralph guard blocks
# a variable in either of the two tokens after the launcher).
args=()
[ -n "$TASK_ID" ] && args+=("$TASK_ID")
args+=(--base "$DIFF_BASE" --receipt "$RECEIPT_PATH" --json)
[ "$RESUMED" = "1" ] || $FLOWCTL codex impl-review-fanout "${args[@]}"
```

What the dispatch does (facts you rely on, not steps you take):

- Task mode reserves exactly **ONE** review round for the whole fan-out
  (standalone reserves none; a per-invocation nonce serves as the `rid`).
- The three draws run concurrently, each under its own timeout — a hung draw
  cannot hold the round to the wall-clock bound.
- Per-draw sidecars land at `.flow/review-fanout/<rid>/`: `<axis>.review.md`
  (the extracted reviewer message — what you merge), `<axis>.json` (metadata
  incl. verdict/session), `<axis>.out.txt` (raw), `meta.json`, `progress.log`.
  The JSON output lists the paths, per-draw verdicts, the `rid`, and the exact
  finalize command to run next.
- **First-round guard:** a `--receipt` already carrying prior findings or a
  resumable session is refused — fan-out never runs on round 2+.
- **Partial fan-out fails open:** one draw with a verdict is enough to proceed;
  failed draws are recorded in `failed_draws`, never retried, and never block.
  Only an all-draws-no-verdict dispatch is a transport failure — one refund,
  today's durable semantics (counts toward `MAX_REVIEW_TRANSPORT_FAILURES`,
  never the verdict counter).

### Steering draw topology (prose, never flags-in-config)

**You own the draw topology.** Parse the user's instruction here and pass
explicit `--draw AXIS[=BACKEND[:MODEL[:EFFORT]]]` arguments — flowctl never
reads prose. Worked phrasings:

- "use 1 reviewer instead of 3" → a single draw: `--draw correctness`
- "use three different model families for the review fan-out" → three explicit
  per-draw backend specs, e.g. `--draw correctness=codex:gpt-5.2:medium
  --draw contracts=cursor:sonnet-4.5 --draw integration=copilot:gemini-2.5-pro`
  — three genuinely distinct families; cross-family is three explicit
  dispatch specs, never a config key
- Ambiguous phrasing → default three same-backend draws (say so and proceed)

Enforced constraint (flowctl, not convention): the **primary draw
(`correctness` — or, when `correctness` isn't drawn, the first draw) must run
on `codex`** — the finalize stamps the merged receipt's top-level
session/model from it and round 2+ resumes that session via codex, so a
non-codex primary is refused with exit 2. Secondary draws may name `codex`,
`copilot`, or `cursor` only; no other backend is dispatchable as a draw.

## Step 3: Coordinator merge (judgment — yours)

Read each surviving draw's `<axis>.review.md` and merge them into ONE review
document (write it to a file for the finalize):

- **Same-defect dedupe** is judgment: findings describing the same defect from
  different draws collapse to one entry, keeping the strongest evidence.
- **Evidence bar:** drop findings that fail it and state the dropped counts in
  the standard per-anchor tally grammar — e.g.
  `Suppressed findings: 3 at anchor 50, 2 at anchor 0.` — summing the draws'
  tallies per anchor (or carry the draws' JSON tally blocks through verbatim).
- **Ranked output with an Act-On tier capped at 5 — non-blocking tiers only** —
  plus a published remainder: considered-and-deferred must be distinguishable
  from never-seen, so remainder items stay in the merged document (they enter
  the findings container as deferred lineage across rounds), never silently
  dropped. **Every surviving introduced blocking finding is fixed regardless of
  count** — the cap never trims blockers; the fix-loop contract is unchanged.
- **Axis provenance lives in your prose report** (e.g. "the integration draw
  surfaced #3 and #7"), never as a field on finding items — the v1 findings
  schema's closed allowlist is untouched.
- **Count the NEEDS_WORK-draw survivors while you merge:** you compute this
  count during the same-defect dedupe — the number of actionable findings from
  the NEEDS_WORK draws that survived your evidence
  gate. Pass it to the finalize as `--needs-work-survivors N` — item fields
  carry no draw attribution, so only your merge knows it. When every
  NEEDS_WORK-draw finding was dropped, `--needs-work-survivors 0` triggers
  the wedge escalation even though SHIP-draw remainder items keep the merged
  container non-empty.
- Keep the draws' output format (Severity / Confidence / Classification /
  File:Line / R-IDs per finding, the `## Pre-existing issues` section, coverage
  table and tally lines where present) and end with exactly one verdict tag.
  The finalize computes the verdict mechanically — worst-wins over the draws —
  so your tag can only escalate it (a strictly worse tag wins; a milder tag
  never downgrades and is stamped as a recorded mismatch on the receipt).

## Step 4: Finalize (phase two)

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
# Bash state does NOT survive across prompt turns — re-derive the Step-1/Step-2
# values in THIS block rather than reading stale variables. RID and MERGED_FILE
# are typed as LITERALS: the rid from the phase-one JSON output, the merged-file
# path from your Step-3 merge — never carried shell variables.
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt${TASK_ID:+-${TASK_ID}}.json}"
if [[ -z "$BASE_COMMIT" ]]; then
  DIFF_BASE="main"
  git rev-parse main >/dev/null 2>&1 || DIFF_BASE="master"
else
  DIFF_BASE="$BASE_COMMIT"
fi
args=()
[ -n "$TASK_ID" ] && args+=("$TASK_ID")
args+=(--base "$DIFF_BASE" --rid "<rid from phase-one JSON>" --merged-file "<your merged document path>" --needs-work-survivors "<coordinator count of surviving findings from NEEDS_WORK draws>" --receipt "$RECEIPT_PATH" --json)
$FLOWCTL codex impl-review-fanout-finalize "${args[@]}"
```

The finalizer is deterministic and atomic — only it records or refunds:

- **Verdict = mechanical worst-wins** over the draws' verdict tags
  (`NEEDS_HUMAN > MAJOR_RETHINK > NEEDS_WORK > SHIP`); failed draws do not
  vote. No draw's verdict is judged away.
- **Wedge escalation:** a `NEEDS_WORK` round with zero actionable survivors
  from the NEEDS_WORK draws (your `--needs-work-survivors` count — required
  whenever any draw returned `NEEDS_WORK`) escalates to `NEEDS_HUMAN` rather
  than looping against an unchanged artifact — per NEEDS_WORK draw, so
  SHIP-draw remainder items never mask an all-filtered NEEDS_WORK.
- Records the attempt, the single v1 findings container (ordinals re-assigned
  1..N across the union), the merged receipt, and the ONE round consumption
  atomically. Receipt top-level `session_id`/`model` are the primary
  (correctness) draw's; `draws[]` honestly records each draw's axis, model,
  session_id, verdict, and failed flag.
- Re-invocable with the same merged file (quiet replay) — recoverable after a
  coordinator crash. A run that dies between dispatch and finalize leaves a
  write-ahead refund-intent journal that the next reservation replays as a
  refunded transport failure — never hand-repair it.

## Optional phases (gated by flags)

When `--deep` / `--validate` / `--interactive` fired, run the gated phases from
[optional-phases.md](optional-phases.md) — the dispatch matches the `codex`
case in each phase — **AFTER `impl-review-fanout-finalize`, against the merged
findings it recorded: still exactly ONCE per round, never per draw, and always
before the fix pass.** The ordering is load-bearing, not stylistic: the
deep-pass and validator dispatches resume from the merged receipt, and only the
finalize writes it — run between merge and finalize they hit an absent or
session-less receipt and error out; and the walkthrough's receipt updates must
land after the finalize's rebuild, which would otherwise clobber them. Fold
what survives into the fix pass, never back into the already-finalized merged
document.

See [optional-phases.md](optional-phases.md) "Phase ordering & flag-combination matrix" for the order when multiple flags are set.

## Step 5: Handle Verdict

If `VERDICT=NEEDS_WORK`:
1. Parse issues from the merged output
2. Fix code and run tests
3. Commit fixes
4. **Re-review is a single dispatch** — the fan-out is first-round only:

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
# Bash state does NOT survive across prompt turns (the fix/test/commit steps ran
# between) — re-derive the Step-1 values in THIS block rather than reading
# stale variables; TASK_ID is a literal from the invocation context.
RECEIPT_PATH="${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt${TASK_ID:+-${TASK_ID}}.json}"
if [[ -z "$BASE_COMMIT" ]]; then
  DIFF_BASE="main"
  git rev-parse main >/dev/null 2>&1 || DIFF_BASE="master"
else
  DIFF_BASE="$BASE_COMMIT"
fi
args=()
[ -n "$TASK_ID" ] && args+=("$TASK_ID")
args+=(--base "$DIFF_BASE" --receipt "$RECEIPT_PATH")
$FLOWCTL codex impl-review "${args[@]}"
```

   When the receipt carries `draws[]`, flowctl resumes the primary session but
   **disables lean resume for that one round**: the resumed session did not
   author the other axes' findings, so the FULL merged prior-finding container
   is injected into the dispatch prompt (every merged ordinal present).
   Automatic — no flag.
5. Repeat until SHIP — bounded by the backend-agnostic fix-loop cap in [SKILL.md](SKILL.md) (`MAX_REVIEW_ITERATIONS`, default 8): a merged fan-out round counts as ONE round; count each fix+re-review cycle; at the cap, surface surviving findings and stop instead of looping

**Output includes `VERDICT=SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN`.**

## Step 6: Receipt

The merged receipt is written by `impl-review-fanout-finalize` (and updated by
`impl-review` on re-reviews) when `--receipt` is provided. Format: the existing
top-level shape (`{"mode":"codex","task":"<id>","verdict":"<verdict>","session_id":"<thread_id>","timestamp":"..."}`)
plus the `draws[]` array recording the fan-out honestly. Per-draw raw outputs
persist beside it in the `.flow/review-fanout/<rid>/` sidecar for audit.

---

## Anti-patterns (Codex backend)

- **Using `--last` flag** - Conflicts with parallel usage; use `--receipt` instead
- **Direct codex calls** - Must use `flowctl codex` wrappers
- **Fanning out on round 2+** - First round only; the guard refuses a receipt with prior findings, and re-reviews resume the primary session
- **Axis provenance on finding items** - It lives in your merge prose; the findings schema's allowlist is closed
- **Retrying a failed draw** - Partial fan-out fails open; a failed draw never blocks, retries, or consumes extra rounds
- **Skipping the finalize** - The dispatch records nothing; a merge without `impl-review-fanout-finalize` leaves a charged round that the refund-intent journal will refund as a transport failure
