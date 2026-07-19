# fn-105 flowctl dead-surface removal sweep + docs drift

> STUB from the fn-101 audit (2026-07-19). ~2.7k LOC with zero fleet callers, plus 11 docs-drift items. Interview/plan before building (a few keep-or-kill calls need the maintainer).

## Goal & Context

fn-101 verified zero skill/agent/hook/template callers (codex mirror excluded, docs mentions not counted) for every surface below. Full table with line refs in the fn-101 plan, section 2.

## Removal list (each with risk note in fn-101)

- `epic`/`epics` aliases + `--epic*` flags + R31 dual-emit JSON keys on hot reads. PRECONDITION: check flow-swarm for alias-key reads before dropping dual-emit.
- **Pre-1.0 migration machinery, removed NOW not at 3.0** (maintainer decision 2026-07-19): `migrate-rename` + `migrate-rollback` + banner hook + `migrate-state` (~1.46k LOC, flowctl.py:18325-19782 + main-hook 33779), the setup-workflow migration arm, and the legacy-epics scan clauses in capture/make-pr prose. REPLACEMENT: a short prose entry in the setup-managed usage.md template (and a line in troubleshooting.md) telling the agent how to port a pre-1.0 repo by hand: rename `.flow/epics/` to `.flow/specs/`, rename `epic-*.json` keys per the mapping, run `flowctl validate` - an agent with Read/Write can do the whole migration from three sentences. Orphans test_migrate_rename.py (24 tests), test_banner.py (26), test_lockfile.py (12).
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

- Every removal needs: sync-codex.sh regen x2, CHANGELOG Unreleased entry, docs-site changelog note at release. The migration removal is a breaking change for pre-1.0 repos - CHANGELOG entry must point at the usage.md porting prose.
