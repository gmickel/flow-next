# Tracker retro-fire (gated reference)

> **Loaded only when phases.md Phase 5's end-of-run `flowctl sync check` reported a
> non-empty `.missing`** (or its own output could not be parsed — fail open). A run
> with an inactive bridge, or a check that came back clean, never reads this file.
> The `sync check` itself and the mandatory four-state `Tracker sync:` summary slot
> stay inline in phases.md Phase 5 and run on every run.

**Retro-fire on MISSING — exactly ONE cycle, never blocking:**

1. Record the retro-fire start anchor and echo it (the re-check needs it as `--since`): `date -u +%Y-%m-%dT%H:%M:%SZ`
2. For each MISSING event, invoke the **inline flow-next-tracker-sync wrapper directly**. It prepares the same approved inputs as the missed touchpoint and makes exactly one facade call with the event tag. **The check block itself is never invoked as the wrapper** — doing so has broken this:
 - `work.firstClaim` → `flowctl tracker sync <spec-id> --op push --status-only --event work.firstClaim <legal file flags>`
 - `work.done` → Work re-synthesizes the task done summary plus tests, commits, and PR evidence; the 0600 body starts with the same stable per-task `evidence=<task-id>@<final-evidence-commit-sha>` (or task-evidence fingerprint) required by the primary touchpoint, then Work calls `flowctl tracker sync <spec-id> --op comment --event work.done --body-file <0600-file>`
 - completion review: Work re-synthesizes the verdict plus R-ID coverage; the 0600 body starts with `evidence=<reviewed-head-sha>`, then Work calls `flowctl tracker sync <spec-id> --op comment --event completionReview --body-file <0600-file>`. This is comment-shaped and NEVER terminal (fn-66). Event key is the TOP-LEVEL `completionReview` (matches the `tracker.perEvent.completionReview` leaf; a `work.`-prefixed tag resolves no leaf and the audit can never clear or miss it)
3. Re-check the missed events only, `--since` = the step-1 anchor:
 `"$FLOWCTL" sync check "$SPEC_ID" --events "<missed-csv>" --since "<retro-fire-start>" --json`
4. Record the final state in the summary slot. Still MISSING after the one cycle is a recorded, visible outcome — never a second retro-fire, never a block (the work is already done; a tracker hiccup must not become a hard stop). Recovery guidance lives in the receipt note + `docs/tracker-sync.md`.
