---
satisfies: [R3, R6]
---

## Description
Correctness/freshness pass on the documentation cohort untouched since 2026-05-20 plus the two oldest `agent_docs/` files, and fix the phantom skill reference. Verify each doc against current behavior and correct anything stale — but preserve intentional historical records (legacy `flow`-plugin removal notes, epic-alias deprecation provenance) as-is.

Specific known fix: `plugins/flow-next/docs/glossary.md:6` references `plugins/flow-next/skills/flow-next-glossary/` — a skill that does not exist. Replace with the real mechanism: `flowctl glossary` subcommands, consumed by `/flow-next:interview`, `/flow-next:audit`, `/flow-next:sync` (the same doc already describes these correctly at ~lines 43-48).

**Size:** M
**Files:** `plugins/flow-next/docs/glossary.md`, `plugins/flow-next/docs/memory-schema.md`, `plugins/flow-next/docs/strategy.md`, `plugins/flow-next/docs/spec-template.md`, `plugins/flow-next/docs/sync-codex.md`, `agent_docs/adding-skills.md`, `agent_docs/releasing.md`.

## Approach
- For each file, read it and spot-check its claims against the current code/CLI/skill surface (`flowctl --help`, the actual skill dirs, the actual template at `templates/spec.md`).
- Apply known memory-learned corrections where they touch these files (e.g. string-enum activation idiom — memory `docs-activation-command-for-string-enum`; codex-mirror composed-transform docs — memory `codex-mirror-smoke-docs-miss-composed`).
- Do NOT rewrite for style — fix only factual drift. Preserve legacy/epic historical notes.
- Pure docs → no version bump. Run `./scripts/sync-codex.sh` only if an edited file is synced (these are docs/ + agent_docs/ — verify whether any are mirrored).

## Investigation targets
**Required** (read before coding):
- `plugins/flow-next/docs/glossary.md` — phantom `flow-next-glossary` ref at line 6
- `plugins/flow-next/docs/spec-template.md` — verify against canonical `plugins/flow-next/templates/spec.md`
- `plugins/flow-next/docs/sync-codex.md` — verify against current `scripts/sync-codex.sh`
- `plugins/flow-next/docs/memory-schema.md` — verify against current `.flow/memory/` schema
- `agent_docs/adding-skills.md`, `agent_docs/releasing.md` — verify against current skill/release process

**Optional** (reference as needed):
- `plugins/flow-next/docs/strategy.md` — verify against root `STRATEGY.md` shape
- `scripts/ci_test.sh` — the gate that must stay green

## Acceptance
- [ ] `docs/glossary.md` no longer references `flow-next-glossary`; it points to `flowctl glossary` + interview/audit/sync.
- [ ] Each file in the 2026-05-20 cohort + `agent_docs/adding-skills.md` + `releasing.md` is verified against current behavior; factual drift corrected.
- [ ] No doc describes removed/renamed behavior as current; legacy `flow`-plugin and epic-alias historical records are preserved.
- [ ] `bash scripts/ci_test.sh` passes; no version bump.

## Done summary
Landed via PR #175 (commit 669fba2) — GitHub docs overhaul. Spec/task scaffold was never committed; deliverables shipped without flow bookkeeping. Closing retroactively.
## Evidence
- Commits:
- Tests:
- PRs: