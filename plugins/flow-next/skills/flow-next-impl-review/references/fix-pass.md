# CLI path: NEEDS_WORK fix pass (gated reference)

> Read from SKILL.md step 4 only when the verdict of SKILL.md's CLI review is `NEEDS_WORK`, or an
> unattended `NEEDS_HUMAN` over a call that does not block the rest of the work.

- `NEEDS_WORK`: one fix pass, then one re-review. Fix only the findings working-rules says to
  fix; list the rest as follow-ups. Never ask the person which to fix. Run focused tests for the
  fixes and commit only the files you changed, with one `Declined #<n>: <reason>` line in the
  commit message for each finding you listed as a follow-up (the re-review reads them). Then
  re-review once, with one reviewer, in the foreground:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REVIEW_ID="<literal or empty>"; DIFF_BASE="<literal>"; BACKEND="<literal>"
ROUTE="$("$FLOWCTL" review-route ${REVIEW_ID:+"$REVIEW_ID"} --json)"
TASK_ID="$(jq -r '.task_id // empty' <<<"$ROUTE")"; RECEIPT_PATH="$(jq -r '.receipt_path' <<<"$ROUTE")"
"$FLOWCTL" "$BACKEND" impl-review ${TASK_ID:+"$TASK_ID"} --base "$DIFF_BASE" --receipt "$RECEIPT_PATH"
```

  The re-review resumes the reviewer's session and its verdict is terminal: report surviving
  findings, never start a second fix pass, unless working-rules.md's review loop applies (an
  unattended run, or a request to review until SHIP). In that loop, fix and re-review the same
  way until SHIP or an `ESCALATE:` (round cap or stall). When the reviewer keeps only findings
  you declined under working-rules.md's rule, all below Major, end the loop and print
  `OVERRIDDEN: <n> declined findings` with each finding and both sides' reasons after
  `VERDICT=NEEDS_WORK`; the caller completes the task on it.
