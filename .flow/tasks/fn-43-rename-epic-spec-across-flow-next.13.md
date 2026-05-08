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
- `docs/flowctl.md`: full CLI reference update -- every `flowctl epic *` subcommand documented under its new spec name; the alias section (NEW) lists the deprecated forms with their canonical equivalents and suppression env var. Add `flowctl migrate-rename` and `flowctl migrate-rollback` documentation (NEW subcommands from T3).

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
- [ ] docs/flowctl.md documents `flowctl migrate-rename` and `flowctl migrate-rollback`.
- [ ] docs/ralph.md mentions the `EPICS_FILE` -> `SPECS_FILE` rename and the alias.
- [ ] docs/teams.md updated to reflect spec-completion-review handover object name.

## Done summary

## Evidence
- Commits:
- Tests:
- PRs:
