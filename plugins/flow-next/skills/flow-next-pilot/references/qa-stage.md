# QA stage — freshness probe (gated reference)

> **Loaded only when Phase 2's QA gate prints its `GATE ACTIVE — STOP` sentinel**
> (`pipeline.qa == "on"`, or the gate's probe/parse errored — fail open). A default
> tick (`pipeline.qa` off/unset) never reads this file. Contract: this file states
> how to compute `QA_FRESH` (and resolve `BRANCH_NAME`); the **consumption stays
> inline in `workflow.md`** — the Phase 2 classification rows and the all-done PR
> probe's no-PR branch read `QA_STAGE_ENABLED` / `QA_FRESH` there, unchanged, and
> the Phase 5 post-dispatch verify keeps its own receipt re-read.

## QA-stage freshness probe (R1b — only when `QA_STAGE_ENABLED=1`)

When the QA gate is on, the all-done juncture classifies `qa` **only when no *fresh* `qa_verdict` receipt exists** for the spec. Pilot is single-tick: without this idempotence gate it would re-classify `qa` forever and never reach make-pr. The receipt lives at the committed path `.flow/review-receipts/qa-<spec-id>.json` (the QA skill's default; task .1 added the `head_sha` field). A receipt is **fresh** iff all three hold:

1. `receipt.id == <spec-id>` (the receipt's existing spec-id field is `id`, not `spec`).
2. `receipt.head_sha` matches the spec **branch** head **with the `chore(flow): {qa verdict, pr artifact}` bookkeeping commits peeled off** — the receipt records the CODE head, but pilot commits the receipt (and make-pr the pr.html artifact) ABOVE it, so a raw `rev-parse "$BRANCH_NAME"` would never match and QA would re-run forever. Compute against the branch, not `HEAD` (a resumed/manual tick may sit on another branch); the post-dispatch verify (pre-receipt-commit) still uses `HEAD` directly.
3. `receipt.qa_outcome` is a valid terminal value (`SHIP`, `NEEDS_WORK`, `NA`, or `BLOCKED`).

Resolve `BRANCH_NAME` + `QA_FRESH` here; the `qa` decision itself is made in the all-done PR probe's **no-PR** branch below, so an existing PR always takes priority. Read the receipt with a single `jq` so a missing/malformed file degrades to never-fresh:

```bash
[[ -n "${BRANCH_NAME:-}" ]] || BRANCH_NAME="$(printf '%s\n' "$SPEC_JSON" | jq -r '.branch_name // empty')"
QA_RECEIPT="$REPO_ROOT/.flow/review-receipts/qa-$SELECTED_SPEC.json"
QA_FRESH=0
if [ -f "$QA_RECEIPT" ] && [ -n "$BRANCH_NAME" ]; then
  R_ID="$(jq -r '.id // ""' "$QA_RECEIPT" 2>/dev/null)"
  R_SHA="$(jq -r '.head_sha // ""' "$QA_RECEIPT" 2>/dev/null)"
  R_OUT="$(jq -r '.qa_outcome // ""' "$QA_RECEIPT" 2>/dev/null)"
  case "$R_OUT" in SHIP|NEEDS_WORK|NA|BLOCKED) : ;; *) R_SHA="" ;; esac   # invalid outcome → never fresh
  # The receipt's head_sha is the CODE head; pilot's own `chore(flow): qa verdict` commit
  # (and a later `pr artifact` commit) sit ABOVE it on the branch, so the branch tip is not
  # the code head. Walk from the tip peeling those bookkeeping commits and accept a match
  # anywhere in the chain — else a successful QA pass reads as never-fresh and re-runs forever.
  if [ "$R_ID" = "$SELECTED_SPEC" ] && [ -n "$R_SHA" ]; then
    _s="$(git -C "$REPO_ROOT" rev-parse --verify --quiet "$BRANCH_NAME" 2>/dev/null || echo "")"
    while [ -n "$_s" ]; do
      [ "$_s" = "$R_SHA" ] && { QA_FRESH=1; break; }
      git -C "$REPO_ROOT" log -1 --format='%s' "$_s" 2>/dev/null \
        | grep -qE '^chore\(flow\): (qa verdict|pr artifact) ' || break
      _s="$(git -C "$REPO_ROOT" rev-parse "$_s^" 2>/dev/null || echo "")"
    done
  fi
fi
```

`QA_FRESH` feeds the **no-PR branch** of the all-done PR probe below — the `qa` decision is made *there*, not before it. Classify `qa` only when that probe finds **no PR** AND `QA_STAGE_ENABLED=1` AND `QA_FRESH=0`. Any existing PR takes priority over (re-)running QA (open → defer-to-land; closed/merged/probe-failed → `NEEDS_HUMAN`), and the probe **fails closed** on a `gh` error — so a transient API failure never misroutes to `qa`. A fresh receipt (`QA_FRESH=1`) or the gate off ⇒ `make-pr`. (Echo `qa_gate=<on|off> qa_fresh=<0|1>` in the classification report so a transcript-only driver sees why the juncture chose `qa` vs `make-pr`.)
