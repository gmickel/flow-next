---
satisfies: [R7, R9, R24, R26, R34, R35]
---

## Description

Detect pre-1.0 `.flow/` layout on every flowctl invocation. Print a one-time-per-process loud banner naming the rename, the flow-swarm carrot, and two migration paths. Banner acknowledgement (`.flow/.banner-acknowledged`) is written ONLY on explicit user action -- `migrate-rename --dry-run` (the user inspected the plan), or the `/flow-next:setup` interactive defer choice. Bare `flowctl <verb>` invocations DO NOT write the ack file -- they show the banner once-per-process and continue. Suppress under Ralph, `FLOW_NO_AUTO_MIGRATE=1`, post-migration sentinel, or after explicit ack within 7 days. Forward-compat downgrade safety.

**Size:** S
**Files:** `plugins/flow-next/scripts/flowctl.py`

## Approach

- New helper `_check_migration_banner(flow_dir, *, allow_ack_write=False)`: called once per `flowctl` invocation early in `main()`.
  - Detects pre-1.0: `.flow/epics/` exists, `.flow/.flow_version` does NOT exist.
  - Detects future-version: `.flow/.flow_version` exists with version > 1.x; emits one-line stderr warning ("`.flow/` was migrated by a newer flow-next; some features may be unavailable"); helper returns. Subcommand's normal exit code is preserved.
  - Suppresses on any of: `FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH`, `FLOW_NO_AUTO_MIGRATE=1`, `.flow/.flow_version` exists at <= 1.x, `.flow/.banner-acknowledged` exists with timestamp within 7 days.
  - Otherwise emits the 6-line banner block to stderr. **Does NOT write `.flow/.banner-acknowledged` from this path** -- a process-level dedup flag (set in module state on first emit) prevents re-emit within the same invocation; multi-process invocations DO re-emit (per process) but only once each. The 7-day suppression file is written ONLY by explicit user action below.
- `flowctl migrate-rename --dry-run` (T3) and the `/flow-next:setup` interactive defer choice (T9 / `.10`) ARE the explicit ack actions: each writes `.flow/.banner-acknowledged` with the current timestamp. Subsequent bare `flowctl` invocations within 7 days suppress the banner (the user has actively engaged with the migration UX).
- Banner copy (~6 lines, stderr verbatim):
  - Line 1: "flow-next 1.0 renamed `flowctl epic` -> `flowctl spec`."
  - Line 2: "Your `.flow/epics/` directory is from 0.x; alias mode keeps everything working."
  - Line 3: "Migrate to unlock future flow-swarm compatibility:"
  - Line 4: "  Interactive:  /flow-next:setup"
  - Line 5: "  Deterministic: flowctl migrate-rename --yes"
  - Line 6: "Suppress this banner: FLOW_NO_AUTO_MIGRATE=1 (alias keeps working)"

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py` -- main `if __name__ == "__main__"` block / argparse dispatch entrypoint.

## Key context

- Banner is informational only; never blocks, never affects exit code, never affects stdout.
- The `.banner-acknowledged` file is the explicit-consent marker; not written by passive banner display.
- 7-day re-nudge cadence applies after explicit ack. Bare invocations show the banner every process boot until ack.

## Acceptance

- [ ] Pre-1.0 `.flow/`: first `flowctl <anything>` invocation prints the 6-line banner to stderr; `.flow/.banner-acknowledged` is NOT written.
- [ ] Subsequent invocations: banner re-emits each time (one banner per process), until either the user runs `flowctl migrate-rename --dry-run` OR migration completes OR `FLOW_NO_AUTO_MIGRATE=1` is set.
- [ ] `flowctl migrate-rename --dry-run` writes `.flow/.banner-acknowledged` with current timestamp.
- [ ] After `.flow/.banner-acknowledged` is written: subsequent `flowctl` invocations within 7 days do NOT emit the banner.
- [ ] After 7 days: banner re-emits once on next invocation; the `.banner-acknowledged` timestamp is NOT auto-updated -- user must run `migrate-rename --dry-run` again or migrate.
- [ ] `FLOW_NO_AUTO_MIGRATE=1 flowctl <anything>`: banner suppressed.
- [ ] `FLOW_RALPH=1 flowctl <anything>`: banner suppressed.
- [ ] `REVIEW_RECEIPT_PATH=/tmp/x flowctl <anything>`: banner suppressed.
- [ ] Post-migration (`.flow/.flow_version` at "1.0.0"): banner suppressed.
- [ ] Future version (`.flow/.flow_version` = "2.0.0"): one-line warning to stderr; subcommand still runs; final exit code is the subcommand's normal exit code.
- [ ] Banner stderr does not pollute `--json` stdout: top-level `flowctl show fn-X --json | jq .id` parses cleanly.

## Done summary

## Evidence
- Commits:
- Tests:
- PRs:
