---
satisfies: [R2, R4]
---
# fn-163-ceremony-fast-path-one-shot-spec.1 One-shot spec authoring: spec create --plan-file / --plan -

## Description
Add one-shot spec authoring to flowctl: `spec create --plan-file <path>` and `spec create --plan -` (stdin) perform create + set-plan in a single invocation, producing byte-identical .flow state to the two-call granular sequence.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (cmd_spec_create ~:25704, _add_spec_subparsers ~:47206-47223), `plugins/flow-next/tests/test_spec_create_plan_file.py` (new)

### Approach
- Add `--plan-file` / `--plan` (value `-` = stdin) to the spec-create parser; mutually exclusive with each other.
- Validate and fully read plan content BEFORE id allocation (pre-write validation ordering per `tests/test_task_create_files.py` `test_missing_*_errors_before_write` precedent). Missing/unreadable file → error, zero writes, no id consumed.
- Widened rollback boundary (explicit handled-failure semantics): after id alloc + `atomic_create` json+md (~:25789-25860), apply the plan via a factored RAISING core helper shared with `cmd_spec_set_plan` (~:28822). Note: today set-plan replaces md then json as two INDEPENDENT writes — not a rollback unit; granular set-plan keeps that behavior unchanged. The one-shot path tracks every created path (spec .json + .md) and removes ALL of them on any plan-stage failure (plan-md write OR updated_at json write) — never leave a plan-less skeleton or plan-md-with-stale-json.
- Failure-injection tests at each publication point separately: initial json, initial md, plan md, timestamp json.
- Tracker-first flags (`--tracker-first`, `--tracker-identifier`) compose with `--plan-file` unchanged.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:25704-25870` — cmd_spec_create: lock, alloc, atomic_create, rollback shape
- `plugins/flow-next/scripts/flowctl.py:28822-28900` — cmd_spec_set_plan: what exactly it writes (md body, json updated_at)
- `plugins/flow-next/tests/test_task_create_files.py` — pre-write ordering, byte-compat, rollback test patterns to mirror

**Optional**:
- `plugins/flow-next/scripts/flowctl.py:47206-47223` — parser registration
- `plugins/flow-next/tests/test_anchor_bundle.py:51-62` — importlib module-load fixture pattern

### Key context
- R2 byte-identity: two-call flow's final `updated_at` comes from the set-plan call. Freeze time in the test (monkeypatch `now_iso`) and compare full `.json` + `.md` bytes between one-shot and granular flows.
- Drive tests through the production CLI dispatch (two-token wire form), not parallel constructions (memory: test-production-path-not-parallel-construction).
- fn-166 extracts a different flowctl.py region (~9300-11500) — no collision, but rebase line anchors if it lands first.

### Acceptance
- [ ] `spec create --title T --plan-file p.md` yields spec .json+.md byte-identical (frozen time) to `spec create` then `spec set-plan`
- [ ] `--plan -` stdin form passes the same equivalence test
- [ ] Missing/unreadable plan file errors before id allocation; `.flow/specs/` unchanged (asserted)
- [ ] Failure injection at each of the four publication points (initial json, initial md, plan md, timestamp json) leaves `.flow/specs/` empty of the new spec — no skeleton, no stale-json pairing
- [ ] `done` / receipt / evidence code untouched (no diff outside spec-create/set-plan region + parser)
- [ ] Focused suite green: `python3 -m unittest test_spec_create_plan_file test_task_create_files -q`
## Acceptance
- `spec create --plan-file` and `--plan -` produce byte-identical .flow state to the granular two-call sequence under frozen time (R2)
- Plan-file validation errors occur before id allocation with zero writes (R2)
- New fixture suite `test_spec_create_plan_file.py` covers equivalence, stdin form, pre-write error ordering, rollback (R6 subset)
- No change to receipts/evidence/start/done (R4)
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
