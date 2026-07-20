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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
