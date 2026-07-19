# fn-105 flowctl dead-surface removal sweep + docs drift

> STUB from the fn-101 audit (2026-07-19). ~2.7k LOC with zero fleet callers, plus 11 docs-drift items. Interview/plan before building (a few keep-or-kill calls need the maintainer).

## Goal & Context

fn-101 verified zero skill/agent/hook/template callers (codex mirror excluded, docs mentions not counted) for every surface below. Full table with line refs in the fn-101 plan, section 2.

## Removal list (each with risk note in fn-101)

- `epic`/`epics` aliases + `--epic*` flags + R31 dual-emit JSON keys on hot reads. PRECONDITION: check flow-swarm for alias-key reads before dropping dual-emit.
- `rp windows/pick-window/ensure-workspace/builder`, `prep-chat` (superseded by `rp setup-review`/`rp chat-send`).
- rp pick-window state-file write (flowctl.py:20389) - writer with zero readers + stale docstring at 20287 + ci_test.sh:716 cleanup.
- `memory discoverability-patch` (~357 LOC, fn-30.6 relic).
- `task show-backend` (~180), `task set-deps` (~80, third copy of dep logic - extract shared helper for the two survivors).
- Empty config-alias machinery (~110 + 19 no-op tests + triple config parse; keep a minimal resolver seam only if future renames expected).
- `sync clear-dep-relation`, `strategy list`, `repo-map show`, `repo-map since-ref`, `prospect list`, `prospect read`, `checkpoint delete`, `state-path`. MAINTAINER CALL: `pilot-log summary` (keep if the fn-102 post-land measurement will consume it); backend `check` triplet (keep if troubleshooting docs direct users to it).
- Always-empty `review_receipts` export field + dead `--section` export filter.
- `scope suggest` moves to fn-107 (judgment eviction), not here.
- Test fallout: delete alias_smoke.sh, test_read_compat.py, test_config_alias.py no-op cases; prune set-deps/show-backend/scope-suggest cases listed in fn-101 section 7.

## Docs drift (fold in, same sweep)

flowctl.md: document setup-block, scope, strategy section, spec skeleton, codex classify-result/rollback-plan, rp ensure-workspace, done --summary/--evidence; add pilot-log + review-rounds to Available Commands; fix File Structure tree. architecture.md: complete the .flow/ layout. ralph.md/flowctl.md: fix the state.json claim (PAUSE/STOP sentinels + progress.txt); guard-rules table completeness. (The "zero overhead" claim is fixed by fn-108's debug-log gating, not here.)

## Boundaries

- NOT in scope: the 3.0 retirement basket (migrate-rename/rollback/state ~1.46k LOC) - recorded in fn-101, decide at 3.0.
- Every removal needs: sync-codex.sh regen x2, CHANGELOG Unreleased entry, docs-site changelog note at release.
