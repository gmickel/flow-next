---
satisfies: [R16]
---

## Description

Update the deep-detail flow-next docs surfaces under `plugins/flow-next/docs/` for spec vocabulary. These are read by users who want depth (per the README's "Read the full docs" callout): the teams + spec-driven-development guide (38 refs), Ralph deep-dive (39 refs), and the canonical flowctl CLI reference (83 refs).

**Size:** M
**Files:**
- `plugins/flow-next/docs/teams.md`
- `plugins/flow-next/docs/ralph.md`
- `plugins/flow-next/docs/flowctl.md`

## Approach

- `docs/teams.md`: rewrite handover-objects framing from "epic" -> "spec" throughout. Note: the doc's central insight (spec-driven development) is already correct conceptually -- this rewrite finishes what teams.md started. The sixth handover object (`epic-review` -> `spec-completion-review`) needs renaming. CLI verb examples and `.flow/epics/` path references update.
- `docs/ralph.md`: CLI verb update throughout (`flowctl epic set-plan-review-status`, `flowctl epic set-completion-review-status`, `flowctl epic close` -> `flowctl spec *`); filesystem path update `.flow/epics/*.json` -> `.flow/specs/*.json`. Include a brief subsection on Ralph + the `EPICS_FILE` -> `SPECS_FILE` rename (T8 covers the template; this doc references it).
- `docs/flowctl.md`: full CLI reference update -- every `flowctl epic *` subcommand documented under its new spec name; the alias section (NEW) lists the deprecated forms with their canonical equivalents and suppression env var. Add `flowctl migrate-rename` and `flowctl migrate-rollback` documentation (NEW subcommands from T3). The migrate-rename docs cover: `--dry-run` (default; ALSO writes `.flow/.banner-acknowledged`), `--yes` (commit), `--json`, the 4-case crash-recovery decision tree (no-backup / partial-backup / complete-no-manifest / mid-migration), the `.flow/.migrating` lockfile semantics with cross-platform PID-liveness reclaim, and the SHA256 task-drift detection. The migrate-rollback docs cover: `--yes`, `--force-overwrite-post-migration-changes`, the manifest-safety contract (refuses on post-migration writes or SHA256 drift), and the rollback-deletes-manifest invariant for repeatable migrate->rollback cycles. <!-- Updated by plan-sync: T3 ships richer surface than original spec captured -->. Document the read-only-fs ordering (idempotency check runs BEFORE the read-only refusal — already-migrated repos on read-only fs are no-ops, NOT failures). <!-- Updated by plan-sync: T3 ships idempotency-before-readonly ordering -->. Add a NEW "Migration banner" subsection documenting T4's stderr banner: 6-line copy verbatim, suppression env vars (`FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH`, `FLOW_NO_AUTO_MIGRATE=1`), the `.flow/.banner-acknowledged` lifecycle (written ONLY by `migrate-rename --dry-run` or `/flow-next:setup` defer; bare `flowctl <verb>` invocations DO NOT write it), the 7-day re-nudge cadence with no auto-refresh, process-level dedup (one banner per `flowctl` invocation), and the future-version downgrade-safety warning (sentinel major >= 2). <!-- Updated by plan-sync: T4 ships banner subsystem with public-facing env vars + ack-file lifecycle that needs canonical doc surface -->

## Investigation targets

**Required:**
- `plugins/flow-next/docs/teams.md` (38 refs).
- `plugins/flow-next/docs/ralph.md` (39 refs).
- `plugins/flow-next/docs/flowctl.md` (83 refs -- canonical CLI reference, highest precision).

## Key context

- docs/flowctl.md is the highest-precision doc surface (readers copy-paste from here). Get the rename right; add the deprecation aliases as a dedicated section.
- docs/teams.md was just shipped (commit 011bc48) and explicitly frames the spec-driven workflow. The rename completes its thesis.

## Acceptance

- [ ] All three docs rewritten; zero `flowctl epic` references in canonical prose (alias-context exempted in flowctl.md's deprecation section).
- [ ] docs/flowctl.md has a "Deprecated aliases" section listing every `epic` -> `spec` mapping plus `FLOW_NO_DEPRECATION=1`.
- [ ] docs/flowctl.md documents `flowctl migrate-rename` (with `--dry-run`/`--yes`/`--json` flags, the 4-case crash-recovery decision tree, the cross-platform lockfile + PID-liveness reclaim, SHA256 task-drift detection, and idempotency-before-readonly ordering) and `flowctl migrate-rollback` (with `--yes`/`--force-overwrite-post-migration-changes`, manifest-safety contract, and rollback-deletes-manifest invariant). <!-- Updated by plan-sync: T3 ships richer surface than original spec captured -->
- [ ] docs/flowctl.md has a "Migration banner" subsection covering T4's banner: 6-line stderr copy, suppression env vars (`FLOW_RALPH`, `REVIEW_RECEIPT_PATH`, `FLOW_NO_AUTO_MIGRATE=1`), the `.flow/.banner-acknowledged` lifecycle and 7-day re-nudge cadence (no auto-refresh), and the future-version (major >= 2) downgrade-safety warning. <!-- Updated by plan-sync: T4 ships user-facing banner surface that needs canonical doc -->
- [ ] docs/ralph.md mentions the `EPICS_FILE` -> `SPECS_FILE` rename and the alias.
- [ ] docs/teams.md updated to reflect spec-completion-review handover object name.

## Done summary

## Evidence
- Commits:
- Tests:
- PRs:
