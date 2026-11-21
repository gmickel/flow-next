# Tracker linkage and audit after create (gated reference)

> Read from create-and-finalize.md unless `flowctl sync active --json` reads `active: false`.

When the bridge is active, invoke the inline tracker-sync wrapper with the prepared snapshots and optional
private breadcrumb, making one lifecycle call:
```bash
TRK_ACTIVE="${TRK_ACTIVE:-$("$FLOWCTL" sync active --json 2>/dev/null | jq -r 'if .active == null then "" else (.active | tostring) end')}"
if [[ -n "$PR_URL" ]] && [ "$TRK_ACTIVE" = "true" ]; then
  # "$FLOWCTL" tracker sync "$SPEC_ID" --op reconcile --event makePr --pr-url "$PR_URL" <other legal file flags>
  :
fi
```
`off|pull|push|reconcile|comment` all use `reconcile` for PR linkage and In Review. It preserves the issue
body unless `tracker.specWins: true`, where flowctl itself sends the rendered spec as the final body;
`tracker.perEvent.makePr` gates only the optional breadcrumb, which Make PR synthesizes from the URL and
opened-PR context. Create-if-unlinked first; unreachable transport is a no-op. Use provider-native links or
URL-deduplicated fallback; never edit issue prose yourself or mark Done. Failures warn without changing PR
success.

Audit `sync check "$SPEC_ID" --events makePr --since <PR-createdAt> --json` independently of dispatch. If
MISSING, record a UTC start, Retro-fire the same wrapper once with explicit `--pr-url`, then recheck since
that start. Never loop.

The tracker call writes sync state, and the link for a spec it just linked, into the spec's JSON after the
pull request was pushed. Commit that file alone and push it to the pull request branch, so it reaches the
default branch with the merge:
```bash
# fence:make-pr-sync-state
TOP="$(git rev-parse --show-toplevel)"
SYNC_JSON="$TOP/.flow/specs/$SPEC_ID.json"
if [ -f "$SYNC_JSON" ] && ! git -C "$TOP" diff --quiet -- "$SYNC_JSON"; then
  git -C "$TOP" commit -q --only -m "chore(flow): tracker sync state for $SPEC_ID" -- "$SYNC_JSON" \
    && { git -C "$TOP" push -q origin HEAD || echo "Warning: tracker sync state for $SPEC_ID not pushed" >&2; }
fi
```
