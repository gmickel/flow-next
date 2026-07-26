# Published JSON Schema for .flow/config.json

## Goal & Context
<!-- scope: business -->

`.flow/config.json` has grown a real surface (review.backend spec grammar, pipeline.qa, work.delegate, artifacts.html, tracker settings, ...) documented only in prose. T3 Code ships `t3.json` with a published JSON Schema so editors give completion, validation, and hover docs via `$schema` - the pattern costs little and makes the config self-teaching. This spec does the same for flow-next: a generated, published JSON Schema for `.flow/config.json`, kept honest by tests against the real config reader.

## Scope
<!-- scope: technical -->

- Schema source of truth: a deterministic generator (pure-stdlib python in flowctl/scripts) that emits draft 2020-12 JSON Schema for the full documented config surface (keys, types, enums like backend names, spec-grammar patterns like `backend[:model[:effort]]`, descriptions lifted from the docs) - hand-maintained descriptions in one structured table, never scattered.
- Publication: the schema ships in-repo (e.g. `plugins/flow-next/schema/flow-config.schema.json`) and is published at a stable URL via the docs site (flow-next.dev/schema/... - the docs-site half is the standing downstream-walk item, noted for the release walk, not implemented from this repo); setup writes `$schema` into scaffolded/refreshed config files pointing at the published URL (offline-tolerant: just a string).
- Honesty tests: every key the config READER consumes appears in the schema and vice versa (a drift test that walks the reader's accepted keys against the schema - additions fail the gate until the schema learns them); valid/invalid fixture configs validated in tests (stdlib-only structural validation is acceptable; no new dependency).
- Docs: flowctl.md config section links the schema; CHANGELOG Unreleased entry.

## Boundaries / non-goals

- No config format changes, no new keys, no migration.
- No runtime schema validation in flowctl beyond what exists (editors are the consumer; flowctl keeps its current tolerant reads).
- The docs-site upload/URL wiring happens in the downstream walk (maintainer property), not from this repo's tasks beyond emitting the file.

## Acceptance Criteria

- **R1:** The generator deterministically emits a draft 2020-12 schema covering the full documented config surface with descriptions; byte-stable across runs (committed artifact + regen test).
- **R2:** Drift test: reader-accepted keys and schema keys match in both directions; a new config key without a schema entry fails the suite.
- **R3:** Setup stamps `$schema` on configs it writes (scaffold + refresh paths) pointing at the stable URL; existing configs untouched unless refreshed.
- **R4:** Fixture validation tests (valid + invalid configs incl. the backend spec grammar pattern) pass stdlib-only; no new dependencies.
- **R5:** Docs + Unreleased CHANGELOG updated; the downstream-walk note lists the docs-site publication step.

## Cross-spec dependency (added 2026-07-26)

**Depends on [[fn-139-tracker-sync-determinism-flowctl-owns]].**

fn-139 adds a new top-level config block `tracker.resolved` (a discovery-written destination + capability cache: per-tracker resolved ids, plus `attachments` / `blockedBy` / `subIssues` / `deleteIssue` capability flags). Its shape is settled by fn-139's R2/R19-R23, including that it is atomic, lock-protected, and may be partially absent by design during migration.

Publishing the schema before that block exists would ship a schema that immediately drifts, and fn-138's own honesty test would fail the moment fn-139 lands. Sequence fn-138 after fn-139, or land both in one window with the schema table updated in the same change.
