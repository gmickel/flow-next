---
satisfies: [R1, R8, R9]
---

## Description
The **deterministic flowctl substrate** — pure enumeration + storage, **zero judgment**. Three thin additions:
1. **`pilot.autonomy` config default** in `get_default_config()` as a sibling to `pipeline.qa` — `"pilot": {"autonomy": "ready"}`. Scalar string-enum, STRICT positive read (`== "backlog"`), never bool. The force-gate is a **SIBLING key `pilot.gateClasses: []`** — NOT `pilot.autonomy.gate` (a scalar and an object cannot share the `pilot.autonomy` dot-path; review finding #2). Materializes on `init`.
2. **`flowctl ready --all [--json]`** — NEW **spec-level** eligibility-facts mode (current `cmd_ready` is *task-within-spec* — add a distinct branch, don't conflate). Returns `{id, ready, readySignal, blockedBy, hasSpec}` — `ready` = the **local** fn-58 boolean (flowctl reports only what it sees locally); **`readySignal ∈ {local, none}`** = whether that local flag is set. **flowctl stores NO readiness provenance** — it cannot attribute a *tracker-projected* ready (finding #3); the skill annotates tracker-origin readiness at union time. **No `triageClass`/completeness field.**
3. **Decision-log — FROZEN CLI** (finding #8): `flowctl pilot-log append --id <id> --action <triaged|advanced|asked|blocked|needs-human> --stage <stage|-> [--cost-tokens <n>]` (cost host-reported, null/omitted when unavailable) + `flowctl pilot-log summary --json` → `{tick, id, action, stage, costTokens}` rows. Atomic-write under **`.flow/pilot-runs/`** (sync-runs-style — **NOT** any `receipts/` path ralph-guard validates). Add `pilot-runs/` to the auto-gitignore patterns + test `init` upgrades an existing `.flow/.gitignore` (finding #9). **`pilot-log --id` accepts an arbitrary OPAQUE id** — a flow spec id OR a bare tracker key (tracker-only items have no spec) — normalized into a safe filename (no path / Linear-linkify hazard); it MUST NOT require `resolve_spec_id_arg` (round-3 #2).

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (+ byte-identical `.flow/bin/flowctl.py`), `plugins/flow-next/tests/test_*.py`

## Approach
- Config: mirror `pipeline.qa` (flowctl.py:1256); add `pilot.gateClasses` as a sibling, not a sub-path.
- `ready --all`: new branch in/beside `cmd_ready` (flowctl.py:15247-15365) + `--all` on `p_ready` (flowctl.py:24886-24894); `readySignal` derived from the local flag only.
- `pilot-log`: reuse the atomic-write + status-enum shape of `cmd_sync_receipt` (flowctl.py:20777-20849); sync-runs placement (flowctl.py:19923-19927). Gitignore: find the auto-gitignore pattern list (grep `FLOW_GITIGNORE` / `.gitignore` writer) and add `pilot-runs/`.

## Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl.py:1144-1256` — `get_default_config()` + `pipeline.qa` precedent
- `plugins/flow-next/scripts/flowctl.py:15247-15365` — `cmd_ready` (add spec-level `--all` branch) + `:24886-24894` — `p_ready`
- `plugins/flow-next/scripts/flowctl.py:20777-20849` — `cmd_sync_receipt` (pilot-log row shape) + `:19923-19927` — sync-runs placement
- the auto-gitignore writer / pattern list (grep `gitignore` in flowctl.py) — add `pilot-runs/`

## Key context
Strict-enum reads only (bool `true` must NOT activate). The pilot-log MUST avoid any `receipts/` path or `REVIEW_RECEIPT_PATH` target (ralph-guard validates those). Both flowctl.py copies byte-identical (there's a test).

## Acceptance
- [ ] `get_default_config()` seeds `pilot.autonomy: "ready"` (strict `== "backlog"`, never bool); the force-gate is the **sibling** `pilot.gateClasses` (no `pilot.autonomy.gate` sub-path); gate `ready` → byte-for-byte unchanged.
- [ ] `flowctl ready --all --json` returns `{id, ready, readySignal, blockedBy, hasSpec}` with `ready` = local fn-58 flag and `readySignal ∈ {local, none}`, **no** judgment/`triageClass`; task-level `ready --spec` unchanged.
- [ ] `flowctl pilot-log append`/`summary` with the frozen action enum write `{tick, id, action, stage, costTokens}` rows under `.flow/pilot-runs/` (never a ralph-guard receipts path); `cost-tokens` optional; **`--id` accepts an opaque id (spec id OR tracker key), safe-filename-normalized, never forced to resolve to a flow spec.**
- [ ] `pilot-runs/` added to the auto-gitignore patterns + `init` upgrades an existing `.flow/.gitignore`; pure-stdlib unittest for all four; `py_compile` clean; both flowctl.py copies byte-identical.

## Done summary
Added the deterministic flowctl substrate for pilot backlog mode: pilot.autonomy/pilot.gateClasses config defaults (strict string-enum, materialized on init), a new spec-level `ready --all` eligibility-facts mode ({id, ready, readySignal, blockedBy, hasSpec}, judgment-free, leaving task-level `ready --spec` unchanged), and a frozen `pilot-log append/summary` decision-log CLI writing {tick, id, action, stage, costTokens} rows under guard-safe `.flow/pilot-runs/`. Opaque id normalization blocks path/linkify hazards; per-id tick allocation is flock-serialized; pilot-runs/ added to auto-gitignore. 32-case stdlib unittest; both flowctl.py copies byte-identical. RP impl-review: SHIP (R1/R8/R9 met).
## Evidence
- Commits: e4a3855, 21504ba, bdd8015
- Tests: python3 -m unittest test_pilot_backlog_substrate (32 tests), python3 -m unittest test_lockfile test_flow_gitignore test_cp1252_robustness test_pipeline_qa_config, python3 -m py_compile plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py
- PRs: