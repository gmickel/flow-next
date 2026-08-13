# Plan tracker-first spec mint (Route B)

Load this reference only when the Step 5 Route B allocator gate printed its
sentinel — `tracker.specIds=tracker` and the bridge is active (or the probe
errored, in which case re-check below and degrade silently). Flow-first repos
never reach this file.

**Tracker-first is the recommended team default** when a tracker is configured
(`tracker.specIds=tracker`): the tracker is the distributed allocator, so
parallel agents stop colliding on `fn-N`. Explicit user override in the
invocation always wins. If re-checking shows the bridge inactive, no transport,
or `specIds` not `tracker`, do nothing here — fall through to the inline
flow-first post-check in steps.md, silently.

Run inside the same Step 5 creation block, using the SAME `$PLAN_FILE` literal:

```bash
# Named existing issue in the request → mint from that key, THEN attach + seed:
#   $FLOWCTL spec create --tracker-first --tracker-identifier "<KEY|#N|project#iid>" --title "<Short title>" --plan-file "$PLAN_FILE" --json
#   Minting stores the identifier but NOT the durable tracker.id, so this
#   branch MUST also run the fetch/attach/seed ceremony (tracker-sync
#   steps.md Phase 2b). Skipping it leaves the spec effectively unlinked and
#   a later touchpoint creates a SECOND remote issue instead of linking.
# Fresh idea → create-first first (tracker-sync steps.md Phase 2d), then mint + attach + seed:
#   skill: flow-next-tracker-sync (operation: create-first, title: "<Short title>", body: "<seed body>")
#   → {id, identifier, url}; on noop / no transport → SILENT fall-through to flow-first
#   $FLOWCTL spec create --tracker-first --tracker-identifier "$IDENTIFIER" --title "<Short title>" --plan-file "$PLAN_FILE" --json
#   then attach + seed merge base per tracker-sync steps.md Phase 2d "Enabled caller sequence"
# Network cost (honest, conditional): when tracker.perEvent.plan is already active,
# tracker-first REORDERS that existing remote write; when the leaf is off (default — a
# bridge-active repo can have every lifecycle event disabled), tracker-first adds an
# EARLIER remote write that flow-first would not have made.
# Assign the result to SPEC_OUTPUT on every path that succeeds here.
:
```

Then return to steps.md Step 5: the unconditional post-check there is the only
flow-first creation site, and its orphan GUARD (create-first recorded an issue
but the mint failed → surface identifier + url + retryKey and STOP) still binds.
Do **not** add a runtime advisory/nag about the id scheme at this mint site
(withdrawn R10) — setup owns the one-time question.
