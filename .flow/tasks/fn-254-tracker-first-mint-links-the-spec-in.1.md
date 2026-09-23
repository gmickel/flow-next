---
satisfies: [R1, R2, R4, R5]
---
# fn-254-tracker-first-mint-links-the-spec-in.1 Implement Tracker-first mint links the spec in the same call

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
`spec create --tracker-first` now takes `--tracker-id` and `--tracker-url`. It publishes `tracker.id`, `identifier`, `url` and `linkState: linked` in the same atomic mint write. A durable id that another spec already holds is refused before anything is written. The collision check (`_tracker_id_owner`, extracted from and shared with `sync set-tracker-id`) and the publication both run under the config writer lock. The five mint-site references and their Codex mirrors now read or create the issue first and pass its identity at mint. The stale Phase 2b/2d pointers are gone. The identity reference, `docs/flowctl.md`, `docs/tracker-sync.md` and the Unreleased changelog document the new arguments.

Tests: R1 `test_linked_mint_publishes_linked_and_skips_remote_create` drives `create_if_unlinked` and asserts no transport call. `test_linked_mint_argument_errors_write_nothing` covers every enumerated argument error. R2 `test_linked_mint_refuses_durable_id_owned_by_another_spec` and `test_linked_mint_checks_and_publishes_under_writer_lock`. R4 `TrackerFirstMintIsLinked` in test_spec_id_routing_prose.py replaces the old attach pin. R5 identifier-only assertions added to `test_tracker_first_canonical_id_and_shape`. Each new test was run red against the base first.

stage: impl-review - ran (codex gpt-6-astra: round 1 fan-out NEEDS_WORK with 1 finding, a substring match of --tracker-id inside --tracker-identifier, fixed in eeb001b9; round 2 SHIP)
## Evidence
- Commits: 1ce4a35d594df692012672b03671359f60638adb, eeb001b9008a64bc39fcc0e6e0ecfd776208ec93, 93f8ae280168530c367f49e36c36e598b04cb8b8
- Tests: baseline: green (python3 scripts/run_tests_parallel.py pre-edit, ran=5040), python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., python3 -m unittest plugins/flow-next/tests/test_tracker_id_generator.py plugins/flow-next/tests/test_spec_id_routing_prose.py
- PRs: