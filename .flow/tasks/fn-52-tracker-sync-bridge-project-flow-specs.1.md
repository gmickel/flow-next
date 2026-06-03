---
satisfies: [R1, R4, R5, R11, R12]
---

## Description

Deterministic flowctl plumbing — the foundation every other task builds on. Adds the sync config block, per-spec sync state (incl. merge-base snapshot), enumerate-only helpers, the sync receipt, and the Ralph-safe deferral path. All in the flowctl monolith; the skill (later tasks) calls these helpers. No tracker API calls here.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`; tests `plugins/flow-next/tests/test_tracker_config.py`, `test_tracker_sync_state.py`, `test_tracker_receipts.py`

**Three up-front design decisions this task MUST settle (tasks .4 and .5 block on these):**
1. **State location** — sync state lives in the existing `.flow/specs/<id>.json` sidecar (not spec frontmatter; merge-base body copies would bloat the markdown).
2. **Merge-base format** — store BOTH a flow-form body snapshot AND a tracker-form rendered snapshot at last sync, plus content hashes for the echo-fence. 3-way merge needs the base in a form comparable to each side.
3. **Receipt state enum** — one enum spanning all three sync layers: `pushed | pulled | merged | updated | diverged | queued | errored | noop`. Design it against tasks .4 AND .5 outputs, not just body.

## Approach

- New `sync` command group following the `config`-group pattern at `flowctl.py:21477` (parent parser + nested `add_subparsers` + leaf `.set_defaults(func=cmd_sync_*)`). Every handler early-guards `ensure_flow_exists()` and honors `args.json`.
- **Config block** in `get_default_config` (`flowctl.py:1018`): a `tracker` key — `{version, enabled, type, provenance, perEvent, perTracker, staleAfterHours, conflictTiebreak}`:
  - **`enabled`** — bool, default `false`. **`type`** — default `null`. **`provenance`** — default `null` (set by the discovery ceremony to who/what confirmed). Because `load_flow_config` always merges this default block in, **activation is explicit AND value-checked**: active iff raw `tracker.enabled == true` OR raw `tracker.type ∈ {"linear","github"}`; absent / `null` / `""` / unknown ⇒ inactive (a default `type: null` persisted by an unrelated `set_config` write must NOT activate). Provide a single activation predicate helper (raw-config-aware via `cmd_config_get --raw`, `flowctl.py:4758`) that .6 calls — do not let each skill re-derive the rule.
  - `perEvent` — keys **nested to stay dot-path-safe** for `get_config`/`set_config` (which split on `.`): `{capture, interview, plan, work: {firstClaim, done}, makePr, resolvePr, completionReview}`, each leaf an enum `off | pull | push | reconcile | comment`, **all defaulting to `off`**. Lifecycle hooks (.6) read `tracker.perEvent.work.firstClaim`, `tracker.perEvent.work.done`, `tracker.perEvent.capture`, etc. Do NOT use a flat literal key `"work.firstClaim"` — it is unreadable via the dotted-path API.
  - `perTracker` — `{teamId/projectId, label map, priority map}`.
  - `staleAfterHours` — integer threshold (document the default, e.g. 24) consumed by `list-stale`.
  - `conflictTiebreak` — `flow-wins | tracker-wins | always-ask`.
  - `deep_merge` (`:1036`) **preserves** unknown keys (it does NOT drop them) ⇒ forward-compat (R1): unset keys fall back to defaults, unknown keys round-trip untouched. Get/set via existing `get_config`/`set_config`.
- **Sync-state fields** added to the spec sidecar schema in `cmd_spec_create` (`flowctl.py:11059-11071`): `tracker {id(UUID dedupe key), identifier, url, lastSyncedAt, baseHashFlow, baseHashTracker, mergeBaseFlow, mergeBaseTracker}`. Setters copy the `cmd_spec_set_branch` idiom (`flowctl.py:11827`: resolve → mutate one field → stamp `updated_at` → `atomic_write_json` `:1658`).
- **Enumerate helpers:** `sync list-unsynced` (no tracker id); `sync list-stale` with a concrete threshold — `--older-than-hours N` flag defaulting to `tracker.staleAfterHours` (missing `lastSyncedAt` always counts as stale); plus a dup-tracker-id collision check (two specs → one issue).
- **Setters/getters:** `set-tracker-id`, `set-last-synced`, `set-merge-base`, `get-state`, `clear` (unlink → wipe tracker state atomically).
- **Receipt:** additive-write idiom from `cmd_review_walkthrough_record` (`flowctl.py:18773`); give it a distinct `type: "sync"` and a distinct path (NOT under `REVIEW_RECEIPT_PATH`) so the review-receipt validator in `hooks/ralph-guard.py:121-153` (verdict enum SHIP/NEEDS_WORK/MAJOR_RETHINK) does not reject it. Record every body merge for rollback.
- **Ralph deferral:** reuse `append_deferred_findings` (`flowctl.py:18670`) → genuine sync conflicts append to the deferred-decisions sink, never block. Config validation: `always-ask` is a legal tiebreak; document that in autonomous mode it resolves to *queue* (not prompt) — surface-dependent, mirrors fn-51.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:21477` — config command-group pattern (template for `sync` group)
- `plugins/flow-next/scripts/flowctl.py:1018` — `get_default_config` (add `tracker` block)
- `plugins/flow-next/scripts/flowctl.py:11059-11071` — spec sidecar schema (add sync-state fields)
- `plugins/flow-next/scripts/flowctl.py:11827` — `cmd_spec_set_branch` (field-setter idiom)
- `plugins/flow-next/scripts/flowctl.py:1636,1658` — `atomic_write` / `atomic_write_json`
- `plugins/flow-next/scripts/flowctl.py:18773` — `cmd_review_walkthrough_record` (receipt additive write)
- `plugins/flow-next/scripts/flowctl.py:18670` — `append_deferred_findings` (Ralph-safe sink)

**Optional:**
- `plugins/flow-next/scripts/flowctl.py:4859` — `cmd_review_backend` (env>config>ASK shape, reused by .2)
- `plugins/flow-next/scripts/hooks/ralph-guard.py:121-153` — receipt validation (why the sync receipt needs a distinct type/path)
- `plugins/flow-next/tests/test_review_receipt_schema.py` — schema-test pattern to mirror for `test_tracker_receipts.py`
- `plugins/flow-next/tests/test_config_alias.py` — config-test pattern to mirror for `test_tracker_config.py`

## Acceptance

- [ ] `flowctl config get tracker --json` returns the default block (version + `enabled:false` + `type:null` + `provenance:null` + nested `perEvent` {capture,interview,plan, work:{firstClaim,done}, makePr,resolvePr,completionReview} each leaf defaulting `off` + perTracker + staleAfterHours + conflictTiebreak); `config get tracker.perEvent.work.firstClaim` resolves via the dotted-path API; an unknown key under `tracker` survives a get/set round-trip (preserved, not dropped) [R1]
- [ ] Activation predicate is value-checked: active iff raw `tracker.enabled == true` OR raw `tracker.type ∈ {linear,github}`; absent / `null` / `""` / unknown ⇒ inactive. Regression test: a persisted `tracker.type: null` (+ some perEvent set) reads as INACTIVE, not adapter dispatch [R1]
- [ ] `sync list-stale --older-than-hours N` honors the flag and defaults to `tracker.staleAfterHours`; missing `lastSyncedAt` always counts stale [R5]
- [ ] Pytest coverage added under `plugins/flow-next/tests/`: config defaults + forward-compat + **absent-raw-config ⇒ inactive** (`test_tracker_config.py`), sync-state setters + dup-id detection (`test_tracker_sync_state.py`), receipt schema (`test_tracker_receipts.py`); all green via the repo's test runner
- [ ] Spec sidecar carries tracker sync state (id, identifier, url, lastSyncedAt, merge-base in flow-form + tracker-form, content hashes); all writes atomic; setters follow the set-branch idiom [R4]
- [ ] Merge-base format (flow-form + tracker-form snapshot + echo-fence hash) is the documented schema decision [R4]
- [ ] `flowctl sync list-unsynced` and `list-stale` enumerate correctly; collision check flags two specs sharing one tracker id [R5]
- [ ] Sync receipt writes with `type: "sync"` + status enum {pushed,pulled,merged,updated,diverged,queued,errored,noop}, records each body merge for rollback, at a path the review-receipt guard does NOT reject [R12]
- [ ] Genuine conflict appends to the deferred-decisions sink (never blocks); `always-ask` validates as legal and is documented to queue (not prompt) in autonomous mode [R11]
- [ ] Every new `cmd_sync_*` supports both text and `--json` output and guards `ensure_flow_exists()`

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
