# Tracker linkage and audit after create (gated reference)

> Read from create-and-finalize.md unless `flowctl sync active --json` reads `active: false`.

When the bridge is active, invoke the inline tracker-sync wrapper with the prepared snapshots and optional
private breadcrumb, making one lifecycle call:
```bash
if [[ -n "$PR_URL" ]] && [ "$("$FLOWCTL" sync active --json | jq -r '.active')" = "true" ]; then
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
