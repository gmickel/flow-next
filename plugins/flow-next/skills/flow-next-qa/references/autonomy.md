# Tracker verdict post

Read when the `workflow.md` §6.5 gate prints its sentinel: `tracker.perEvent.qa` is not `off`, or
the probe failed. The receipt is already written; this step never changes it.

## Tracker verdict post

The leaf accepts `off | comment` (default `off`). A verdict is a report, so the only operation is a
comment: `pull`, `push` and `reconcile` are treated as `comment`, never as a body or status
update, and an unrecognised value posts nothing. It
runs only when the tracker bridge is active; the gating matches the other lifecycle events
([tracker-touchpoints.md](../../flow-next-work/references/tracker-touchpoints.md#bridge-overview) "Shared gating predicate").

```bash
case "$QA_LEAF" in
  pull|push|reconcile|comment) QA_OP="comment" ;;
  off|null)                    QA_OP="off" ;;
  *)                           QA_OP="off" ;; # malformed config stays silent
esac
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
   && [ "$QA_OP" != "off" ]; then
  # QA synthesizes the comment content by name: verdict, qa_outcome, open P0/P1
  # findings, and R-ID coverage. Its FIRST line is
  # `evidence=<tested-head-sha>`. Write it to a mode 0600 temporary body file,
  # never argv. The inline flow-next-tracker-sync wrapper makes exactly one
  # facade call and deletes the file:
  #   "$FLOWCTL" tracker sync "$SPEC_ID" --op comment --event qa --body-file "$BODY_FILE"
  # pull, push, reconcile, and comment all coerce to comment. Best-effort.
  : # never blocks
fi
```

Transport, comment dedup and the sync receipt belong to flow-next-tracker-sync; QA only gates and
hands over the body. With no linked issue the call is a clean no-op. A tracker failure (no
transport, missing issue, rate limit) never blocks or rolls back the verdict.
