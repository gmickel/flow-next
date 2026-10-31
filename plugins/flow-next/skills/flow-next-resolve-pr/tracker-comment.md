# Phase 9.5: tracker resolution comment (gated reference)

> Read from [workflow.md](workflow.md) Phase 9.5 unless `flowctl sync active --json` reads
> `active: false`.

**Optional. Runs only when the tracker bridge is active AND `resolvePr` is opted in, after the resolution pass settles (Phase 9 found nothing left to loop on, or only `needs-human` threads remain). With no tracker configured this is a no-op.** Posts an optional resolution comment to the linked tracker issue summarizing what was addressed on the PR — append-only, conflict-free.

The linked spec id comes from the PR's spec association (the same `SPEC_ID` make-pr used; resolve `flowctl show <spec-id>` from the branch as elsewhere in this skill).

```bash
LEAF="$($FLOWCTL config get tracker.perEvent.resolvePr --json | jq -r '.value')"   # read the leaf ONCE (shared gating predicate — work references/tracker-touchpoints.md)
case "$LEAF" in
  pull|push|reconcile|comment) OP="comment" ;;
  off|null)                    OP="off" ;;
  *)                           OP="off" ;; # malformed config stays silent
esac
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
   && [ "$OP" != "off" ]; then
  # Resolve PR synthesizes the comment content by name: "Addressed N of M
  # review items on PR #<NUMBER>" plus the terminal resolution counts. Its
  # FIRST line is `evidence=<post-resolution-pr-head-sha>`. Write it to a mode
  # 0600 temporary body file, never argv. The inline
  # flow-next-tracker-sync wrapper makes exactly one facade call and deletes it:
  #   "$FLOWCTL" tracker sync "$SPEC_ID" --op comment --event resolvePr --body-file "$BODY_FILE"
  # Unlinked specs create and link inside the facade. Best-effort; never blocks
  # the resolve-pr summary.
  :
fi
```

The facade emits one receipt tagged `--event resolvePr`. Structured errors are
routed by the inline wrapper and remain best-effort.
