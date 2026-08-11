---
satisfies: [R5, R6]
---
# fn-182-tracker-create-first-cas-list-open.4 Abandon-path docs, CHANGELOG, manifest + full gate

## Description
Spec fn-182 item 4 (#309). tracker-sync.md paragraph: close/cancel remote first (consumer-owned), then create-first-clear, with the ordering rationale. CHANGELOG Unreleased crediting @sn-furali (#309, #310, #311, #315 with the option-choices noted). Dual copies, gen_tracker_manifest, sync-codex twice, full suite + ruff.

## Acceptance
R5, R6 of the spec. Full gate green; no version bump.

## Done summary
R5-R6 closed out. tracker-sync.md: abandon path with explicit remote-first ordering and consumer-owned close (#309 answerable by link), CAS promotion ceremony (adopt details.recordedSpecId on conflict), Linear list-open refusal semantics (refusal = no-ready-lane, unset stays legitimate), projectId/projectMilestoneId sidecar field table row (absent = unmanaged, never cleared, Linear-only capability). flowctl.md: create-first-put synopsis + CAS contract incl. exit 10 and all four subtypes; wire list-open per-provider caveat. Skill surfaces: linear-ladder + adapter-interface tables, steps.md backlog enumeration teaches fall-back-to-Flow-ready on the refusal. CHANGELOG Unreleased credits @sn-furali (#309 #310 #311 #315). Full gate green; no version bump.
## Evidence
- Commits: d7d5f393
- Tests: python3 scripts/run_tests_parallel.py (4432 OK), uvx ruff@0.16.0 check . (clean), ./scripts/sync-codex.sh x2 (idempotent)
- PRs: