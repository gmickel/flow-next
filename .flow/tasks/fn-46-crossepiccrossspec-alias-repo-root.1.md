---
satisfies: [R1, R2]
---

## Description

Add `planSync.crossSpec` as the canonical config key with `planSync.crossEpic` as a read-only legacy alias. `get` prefers `crossSpec`; falls back to `crossEpic` only when `crossSpec` is **absent from the raw JSON file** (not merely default-valued). `set` writes `crossSpec` only. Legacy reads emit a one-line stderr deprecation via the fn-43 `_emit_rename_deprecation` helper (suppressed via `FLOW_NO_DEPRECATION=1`). Update `flow-next-setup` workflow (5 sites) and `agents/plan-sync.md` env-var doc to reference the new key as canonical.

**Size:** M

**Files:**
- `plugins/flow-next/scripts/flowctl.py`
- `plugins/flow-next/agents/plan-sync.md`
- `plugins/flow-next/skills/flow-next-setup/workflow.md`
- `plugins/flow-next/codex/**` (regenerated mirror via sync-codex.sh)

## Approach

- **Alias resolution must read raw file state, not merged config.** `load_flow_config()` at `flowctl.py:1039-1051` deep-merges defaults — if `crossSpec` is added to defaults, `get_config("planSync.crossSpec")` returns the default `False` and never falls back to `crossEpic`. Fix: alias logic reads the JSON file directly (or strips defaults for the aliased key). Simplest: at `cmd_config_get` / `set_config` entry, consult `_CONFIG_KEY_ALIASES = {"planSync.crossEpic": "planSync.crossSpec"}`, and for the legacy-fallback path probe the raw file via a small `_get_config_from_file(key)` helper that does NOT apply defaults.
- **Default switches to canonical only.** Drop `"crossEpic": False` from `get_default_config()` at `flowctl.py:1018-1025`; add `"crossSpec": False` instead. Legacy presence in the file then means "user explicitly set legacy" (distinguishable from "unset").
- **Reuse `_emit_rename_deprecation`** at `flowctl.py:3865-3888` verbatim. Per-process dedup is already there. To include "Removed in 2.0." suffix per the spec wording, extend the helper with an optional `extra: str = ""` parameter and append; or accept the slight wording divergence with existing fn-43 deprecation lines (the existing prose is `Warning: {legacy} is deprecated; use {canonical}. (Suppress with FLOW_NO_DEPRECATION=1.)`). **Recommend the extra param** — it keeps wording consistent across future deprecations.
- **5 `flow-next-setup/workflow.md` sites** (lines 237-239, 268, 309-320, 415-417, 497): write `crossSpec` on new configs; read both with new winning. Display text uses "Plan-Sync cross-spec" canonical wording. Legacy mention moves to a footnote (not inline in question / display).
- **`agents/plan-sync.md:19`** env-var doc updated: `CROSS_SPEC` reads from `planSync.crossSpec` (with `planSync.crossEpic` as legacy alias documented in a footnote).
- Run `./scripts/sync-codex.sh` after canonical changes; verify all sync validation guards pass.

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:1018-1096` — config defaults, get/set, load_flow_config deep-merge (the gotcha source)
- `plugins/flow-next/scripts/flowctl.py:3865-3888` — `_emit_rename_deprecation` helper to reuse
- `plugins/flow-next/scripts/flowctl.py:4574-4606` — `cmd_config_get` / `cmd_config_set` handlers (extend with alias lookup)
- `plugins/flow-next/skills/flow-next-setup/workflow.md:237-320,415-497` — 5 sites with crossEpic
- `plugins/flow-next/agents/plan-sync.md:19` — env-var doc

**Optional**:
- `plugins/flow-next/scripts/flowctl.py:3836-3862` — `resolve_spec_arg` (fn-43 alias pattern at argparse layer; NOT directly reusable but shows the convention)
- `.flow/memory/bug/build-errors/agent-rename-epic-id-prompt-key-changes-2026-05-08.md` — dispatcher-sweep discipline lesson from fn-43

## Key context

- **Critical correctness gotcha:** `load_flow_config()` deep-merges defaults BEFORE `get_config()` reads. If `crossSpec` default is `False`, `get_config("planSync.crossSpec")` always returns `False` (not `None`). Solution: when checking "is `crossSpec` set?", probe the raw JSON file, not the merged config. Practice-scout flagged this explicitly.
- **`get` warns only when canonical absent AND legacy present.** Don't warn on default-value reads (no user-set anywhere). Don't warn when canonical is present.
- **`set` never mutates legacy.** Writing `crossSpec` doesn't delete `crossEpic` — the legacy key just becomes "wins-on-fallback-only" until 2.0 removes it. Document that the canonical wins on next read.
- **Per-process dedup** in `_RENAME_DEPRECATION_EMITTED: set[str]` (existing). Setup reading the legacy key 3 times in a single invocation will only warn once.
- **Legacy key absence from defaults** is load-bearing. With `crossEpic: False` removed from `get_default_config()`, an unset file shows `None`/`missing` for `crossEpic` — distinguishable from "user explicitly set legacy to false". This is what enables the "raw file probe" semantic.
- **flow-next-setup display wording:** keep the user-facing label "Plan-Sync cross-spec" (already used in the existing display text). What changes is the underlying config key written / read — the label stays.
- **Codex mirror regeneration:** `./scripts/sync-codex.sh` rewrites canonical → mirror. The Codex mirror copy of `flow-next-setup/workflow.md` and `plan-sync.md` will pick up the new key wording automatically. Verify the rui_refs guard from fn-45 still passes (no new `request_user_input` introduced).

## Acceptance

- [ ] `planSync.crossSpec` is the canonical key; `get_default_config()` returns `{"crossSpec": False}` (no `crossEpic` entry).
- [ ] `flowctl config get planSync.crossSpec` returns the canonical value; `flowctl config set planSync.crossSpec <bool>` writes only the canonical key.
- [ ] `flowctl config get planSync.crossEpic` returns the legacy value if present in the file AND `crossSpec` is absent from the file; emits one-line stderr `Warning: planSync.crossEpic is deprecated; use planSync.crossSpec. (Suppress with FLOW_NO_DEPRECATION=1.) Removed in 2.0.` (or close wording per `_emit_rename_deprecation` extension).
- [ ] `FLOW_NO_DEPRECATION=1 flowctl config get planSync.crossEpic` suppresses the warning.
- [ ] Per-process dedup verified: 3 consecutive `get` calls in one process emit the warning exactly once.
- [ ] Setting `crossSpec` does NOT delete `crossEpic` from the file (legacy preserved as-is until 2.0).
- [ ] `flow-next-setup/workflow.md` 5 sites updated: writes only `crossSpec`; reads both with `crossSpec` winning; display text uses canonical wording.
- [ ] `agents/plan-sync.md:19` references `planSync.crossSpec` as source-of-truth with legacy alias in a footnote.
- [ ] `./scripts/sync-codex.sh` runs cleanly; all sync validation guards pass; mirror regenerated.
- [ ] Smoke green: `cd /tmp && bash /Users/gordon/work/gmickel-claude-marketplace/plugins/flow-next/scripts/smoke_test.sh` reports 130/130 pass.
- [ ] Sync idempotency confirmed: re-running `./scripts/sync-codex.sh` produces byte-identical mirror.

## Done summary
flowctl `planSync.crossSpec` is now canonical; `planSync.crossEpic` is a read-only legacy alias with one-line stderr deprecation (per-process deduped, `FLOW_NO_DEPRECATION=1` suppresses, removed in 2.0). Alias resolution probes the raw `.flow/config.json` to dodge the `load_flow_config()` deep-merge gotcha. flow-next-setup workflow (4 key-bearing sites + display label retained) and `agents/plan-sync.md` env-var doc now reference the canonical key with legacy footnote. Codex mirror regenerated; sync is idempotent. 14 new unit tests cover defaults, raw-file probe, both-directions read resolution, write redirection, dedup, and env suppression.
## Evidence
- Commits: 5ef184cde0b437bae3a4be3cb7609b9ff7063454
- Tests: python3 -m unittest plugins.flow-next.tests.test_config_alias -v (14/14 passed), python3 -m unittest discover -s plugins/flow-next/tests (601/601 passed), cd /tmp && bash plugins/flow-next/scripts/smoke_test.sh (130/130 passed), ./scripts/sync-codex.sh — clean run + idempotent re-run (byte-identical mirror), manual acceptance T1-T12: defaults, canonical wins, legacy fallback, FLOW_NO_DEPRECATION=1 suppress, per-process dedup (single warn across 3 calls)
- PRs: