---
satisfies: [R7]
---
# fn-200-land-request-human-reviewers-at.3 docs + CHANGELOG + codex mirror for land.requestReviewers

## Description
User-facing docs for the new key, the `## Unreleased` CHANGELOG entry crediting the reporter, and the codex mirror regen; then the full gate.

**Size:** S
**Files:** plugins/flow-next/docs/flowctl.md, plugins/flow-next/docs/README.md, CHANGELOG.md, plugins/flow-next/codex/** (regenerated)
**Touches:** [plugins/flow-next/docs/flowctl.md, plugins/flow-next/docs/README.md, CHANGELOG.md, plugins/flow-next/codex/**]

### Approach
- `docs/flowctl.md` land.* table (~l.964-971): one row after `land.mergeVerdictCommand`, same column style: type string, default `""`, description = grammar (csv logins / `org/team` / `codeowners`), when it fires (human review is the sole missing merge input), one-shot per head SHA, flips draft→ready, never gates a merge (`reviewSignal` does), dry-run would-request.
- `docs/README.md`: a what's-new bullet in the `land.mergeVerdictCommand` style (~l.78) with a `flowctl config set land.requestReviewers "alice,org/platform"` example; extend the doc-index blurb (~l.54) only if it already enumerates land keys.
- `CHANGELOG.md`: insert `## Unreleased` above the 4.1.0 entry (none exists yet); `### Added` entry written user-outcome-first per `agent_docs/releasing.md` (what the human now experiences; machinery last), credit `thanks @sn-furali (#359)`, note part 2 (`draftOnChangesRequested`) is deferred. No version bump.
- `./scripts/sync-codex.sh` twice (idempotent), commit the mirror diff.
- Final gate: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`.

### Investigation targets
**Required:**
- `plugins/flow-next/docs/flowctl.md:960-972` — land.* table rows
- `plugins/flow-next/docs/README.md:50-80` — index blurb + what's-new bullets
- `agent_docs/releasing.md` — changelog ordering + rejection test
- `CHANGELOG.md:1-12` — current top entry

**Optional:**
- `CHANGELOG.md` fn-188 / fn-65.1 entries — precedent shape for a land config addition

### Acceptance
- [ ] flowctl.md row, README bullet, Unreleased CHANGELOG entry (credits @sn-furali, #359) present
- [ ] `./scripts/sync-codex.sh` run twice, second run a no-op, mirror diff committed
- [ ] `python3 scripts/run_tests_parallel.py` and `uvx ruff@0.16.0 check .` green

## Acceptance
- [ ] TBD

## Done summary
R7 docs for `land.requestReviewers`: `docs/flowctl.md` land.* table row (grammar, sole-missing-input predicate, one-shot per head, ready flip, never gates a merge, dry-run, `reviewers=` vocabulary), `docs/README.md` what's-new bullet + land index blurb, `## Unreleased` CHANGELOG entry written user-outcome-first (thanks @sn-furali, #359; part 2 `draftOnChangesRequested` deferred), codex mirror regenerated twice (second run no-op). Review fix: `reviewers=off` is now reserved for an unset key — a configured-but-not-due PR reports `skipped:not-due` (workflow initializer + SKILL/docs/CHANGELOG + test pin). Baseline green; full suite 4400 tests green, ruff clean.

stage: impl-review - ran (codex gpt-5.6-sol high: NEEDS_WORK x1 -> SHIP; finding fixed in fe624d8a)
## Evidence
- Commits: 6c14d152a7bbd3e91d365e39447cce2a4b258b8f, fe624d8ad5e84f9793c4c83d87df122db42b80d7
- Tests: baseline: green (cd plugins/flow-next/tests && python3 -m unittest test_land_config test_flow_config_schema_drift test_skill_prose_diet -q; uvx ruff@0.16.0 check .), cd plugins/flow-next/tests && python3 -m unittest test_land_config test_flow_config_schema_drift test_skill_prose_diet -q, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh x2 (second run no-op)
- PRs: