---
name: flow-next-impl-review
description: Carmack-level implementation review of changes via the configured backend. Use when asked to review code or a diff in a flow-next repo.
user-invocable: false
---

# Implementation review

You coordinate; the configured backend reviews. Never author a verdict yourself, and use one
backend for the whole review. Read [working-rules.md](../../references/working-rules.md) first:
its Review section decides which findings you fix.

Arguments: `[task id] [--base <commit>] [--review=<backend>] [--deep[=passes]]
[--validate] [--interactive] [--no-triage] [focus areas]`. Without `--base` the whole branch is
reviewed against main. A spec or branch review passes no id.

## 1. Setup

One Bash call; fill the three literals from the arguments.

```bash
set -e
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REVIEW_ID="<task id, or empty for a spec or branch review>"
BACKEND="<value of --review, or empty>"
DIFF_BASE="<value of --base, or empty>"
[ -n "$BACKEND" ] || BACKEND=$("$FLOWCTL" review-backend "$REVIEW_ID")
[ -n "$DIFF_BASE" ] || { DIFF_BASE=main; git rev-parse -q --verify main >/dev/null || DIFF_BASE=master; }
echo "FLOWCTL=$FLOWCTL BACKEND=$BACKEND DIFF_BASE=$DIFF_BASE"
git diff --shortstat "$DIFF_BASE"...HEAD
```

- `ASK`: stop; no backend is configured (`/flow-next:setup`, or pass `--review=<backend>`).
- `none`: no review; say so.
- `rp` or `export`: removed; tell the user in one line "RepoPrompt review (rp, export) was removed
  in flow-next 8.0.0; review backends: claude, codex, copilot, cursor, host." and stop as for `ASK`.
- Any other backend than `codex`, any of `--deep`, `--validate`, `--interactive`, `--no-triage`,
  `FLOW_VALIDATE_REVIEW=1` or `FLOW_REVIEW_DEEP=1` in the environment, or an instruction about
  the reviewers ("one reviewer", "three model families"): read [other-paths.md](other-paths.md)
  and follow it and the backend's workflow file to the end. That file owns the verdict, fix and
  re-review handling; of step 4, only the `OVERRIDDEN:` line ending an unattended loop applies,
  never its fix pass or codex re-review.

Shell state does not survive between Bash calls: each block below resolves `FLOWCTL` again and
takes `REVIEW_ID` and `DIFF_BASE` as literals.

## 2. Codex review

Run each review command as one blocking foreground Bash call with a 600-second timeout. Never
run it in the background: its completion would not resume you.

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REVIEW_ID="<literal or empty>"; DIFF_BASE="<literal>"
ROUTE="$("$FLOWCTL" review-route ${REVIEW_ID:+"$REVIEW_ID"} --rotate-stale --json)" || { printf '%s\n' "$ROUTE" >&2; exit 1; }
ACTION="$(jq -r '.action' <<<"$ROUTE")"; TASK_ID="$(jq -r '.task_id // empty' <<<"$ROUTE")"
RECEIPT_PATH="$(jq -r '.receipt_path' <<<"$ROUTE")"
echo "TASK_ID=$TASK_ID RECEIPT_PATH=$RECEIPT_PATH"
case "$ACTION" in
  stop) jq -r '.message' <<<"$ROUTE" >&2; exit 1 ;;
  fix-then-rereview) echo "RESUMED: the receipt holds findings still to fix; go to step 4"; exit 0 ;;
esac
TRIAGE=(--receipt "$RECEIPT_PATH" --base "$DIFF_BASE" --no-llm); [ -n "$TASK_ID" ] && TRIAGE+=(--task "$TASK_ID")
if OUT=$("$FLOWCTL" triage-skip --json "${TRIAGE[@]}" 2>/dev/null); then
  echo "Triage-skip: $(jq -r '.reason // "trivial diff"' <<<"$OUT")"; echo "VERDICT=SHIP"; exit 0
fi
args=(); [ -n "$TASK_ID" ] && args+=("$TASK_ID")
args+=(--base "$DIFF_BASE" --receipt "$RECEIPT_PATH" --json)
# The default is three reviewers. For a small diff in one area (one module or feature, not spread
# across subsystems) that touches no persisted or shared state, concurrency, security or data layout, set ONE_REVIEWER=1 for a single reviewer.
ONE_REVIEWER=0
[ "$ONE_REVIEWER" = 1 ] && args+=(--draw correctness)
"$FLOWCTL" codex impl-review-fanout "${args[@]}"
```

A branch review (no task) passes the caller's focus areas with `--focus "<areas>"`. Triage
passing means lockfile, docs, release or generated files only: the review is done.

## 3. Merge and finalize

The fan-out JSON lists each draw's `<axis>.review.md`, its `rid`, and the finalize command. Read
each review and write a merge plan to a file: `{"keep":["correctness:1"],"collapse":{"contracts:2":"correctness:1"}}`,
where references are `<axis>:<finding number>`. Collapse findings that describe the same defect
onto the one with the strongest evidence; leave out findings with no concrete failing scenario in
the change. Then, in the foreground:

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
"$FLOWCTL" codex impl-review-fanout-finalize --rid "<rid>" --merge-plan "<plan path>" --json
```

flowctl computes the verdict (the worst draw wins; failed draws do not vote) and writes the
receipt. Report `VERDICT=<verdict>` with the kept findings; your own reading never changes it.
Finalize before you change or commit anything: a commit moves HEAD past the reviewed head,
flowctl refuses the round, and the retry is a full fresh review instead of the scoped re-review.

## 4. Act on the verdict (every backend)

- `SHIP`: done. Report the verdict and any follow-ups.
- `MAJOR_RETHINK`: the approach is wrong. Stop with `BLOCKED: DESIGN_CONFLICT` and the
  reviewer's rationale; do not patch finding by finding.
- `NEEDS_HUMAN` (flowctl reports it as `ESCALATE: reviewer requested human review`): stop and hand
  the reviewer's question to the person. Unattended, when that question is a human call that does
  not block the rest of the work (working-rules-unattended.md), run the `NEEDS_WORK` fix pass below
  instead, declining the call itself with `Declined #<n>: open item for the person`; when that loop
  ends, print `OPEN_ITEM: <the question>` after the verdict. The caller completes the task on it and
  the pull request opens as a draft.
- `NEEDS_WORK`: on the codex path, read [references/codex-fix-pass.md](references/codex-fix-pass.md)
  and run its one fix pass and re-review; other backends run their workflow file's fix loop.

On any backend, when an unattended loop ends with the reviewer keeping only findings you declined
under working-rules.md's rule, all below Major, print `OVERRIDDEN: <n> declined findings` with
each finding and both sides' reasons after `VERDICT=NEEDS_WORK`; the caller completes the task on it.

If a review command ends without a verdict (a transport error), retry it once. `ESCALATE:` (other
than the `NEEDS_HUMAN` case above), `TRANSPORT_UNHEALTHY`, `NOT_RETRYABLE:` and other refusals end this review: report the message
as printed and stop. Never widen the reviewer's sandbox, call `codex` directly, or reset review
state to get past one.
