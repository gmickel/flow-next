# fn-111-flowctl-dead-surface-removal-sweep-docs.2 Epic-alias surface + config-alias machinery removal

## Description
Remove the epic/epics alias surface end to end (maintainer resolution: remove ALL; flow-swarm migrates separately) plus the empty config-alias machinery.

**Size:** M
**Files:** both flowctl.py copies, tests, plugins/flow-next/scripts/alias_smoke.sh, .github/workflows/test-flow-next.yml (alias_smoke step)

### Approach

- Read fn-101 plan section 2 table first. Remove: `epic`/`epics` command aliases, every `--epic*` flag alias (keep canonical --spec forms), the R31 dual-emit JSON keys on hot reads (list/show/export emit spec keys ONLY), `depends_on_epics`... CAREFUL: `depends_on_epics` is the CANONICAL on-disk spec field, NOT an alias - do not touch it. Only remove ALIAS surfaces the fn-101 table lists.
- Empty config-alias machinery (~110 LOC + triple config parse): remove the alias map + resolver; config parses once. If a minimal resolver seam is trivially separable, keep the seam function with an empty map and a one-line comment (future renames); otherwise remove fully.
- Test fallout: delete alias_smoke.sh + its CI step; delete test_read_compat.py; delete test_config_alias.py no-op cases (keep any case that pins still-live behavior - verify each against current code before deletion; if the whole file is no-op after the machinery removal, delete the file). Each deletion names its dead behavior in the summary.
- BREAKING note for the CHANGELOG rider in task 4: flow-swarm reads the `epics` key + forwards --epic flags; maintainer migrates flow-swarm before consuming this release.
- Dual-copy mirrored; sync-codex x2. NO git commands.

### Acceptance

- [ ] No epic/epics command or --epic* flag parses; hot-read JSON emits canonical keys only (no dual-emit)
- [ ] Config parses once; alias machinery gone (or empty-map seam with comment)
- [ ] alias_smoke.sh + CI step + test_read_compat.py deleted; test_config_alias.py no-op cases gone, live cases (if any) kept
- [ ] Focused suites green: --pattern "test_config*.py", --pattern "test_hot_path*.py", --pattern "test_export*.py"
- [ ] Both flowctl.py copies byte-identical; sync-codex idempotent

## Acceptance
- [ ] TBD

## Done summary
Epic-alias surface removed end to end: epic/epics commands, all --epic* flag aliases, R31 dual-emit JSON keys (epics/epic/epic_id/epic_title/epic_count/epic_blocked_by/legacy_reason/current_epic/blocked_epics), _emit_rename_deprecation + callers, cmd_epic_* Python aliases; config-alias triple-parse gone (empty-map resolver seam kept with comment). depends_on_epics stays - canonical on-disk field. alias_smoke.sh + CI step deleted; test_config_alias no-op cases (3) and test_config_snapshot alias-injection cases (6) deleted, live cases kept. BREAKING rider for task 4 CHANGELOG: flow-swarm reads the epics JSON key + forwards --epic flags; maintainer migrates flow-swarm before consuming. Host review: (1) restored task create --title (delegate dropped it while collapsing the spec/epic/title argparse block - real canonical-surface regression, caught by the full-corpus gate, one-line fix + dual-copy sync); (2) pruned 3 stale alias-pinning tests the delegate missed (test_spec_ready handler-identity, test_backend_spec cmd_epic_set_backend x2). Full parallel suite green: 83 files, 1841 tests, 0 failures, 79.3s; sync-codex x2 idempotent.
## Evidence
- Commits: 5d95eec909a8c15cc5e035127090a78bd082801d
- Tests: python3 scripts/run_tests_parallel.py (83 files, 1841 tests, 0 failures, 79.3s), focused: test_config*.py 33 OK / test_hot_path*.py 18 OK / test_export*.py 31 OK / test_backend_spec.py 138 OK / test_spec_ready.py 13 OK / test_normalize_section_content.py 26 OK
- PRs: