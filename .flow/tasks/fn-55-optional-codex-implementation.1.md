---
satisfies: [R1, R2]
---

## Description
Lay the config foundation so delegation defaults are "the law, defined once" and the activation resolution chain (arg > config > default off) has a deterministic backend. No delegation mechanics yet — just the knobs + how they resolve.

Add a `work` block to flowctl's `get_default_config()` so `flowctl config get work.delegate*` returns the spec defaults (NOT `null`): `work.delegate=false`, `work.delegateModel=gpt-5.5`, `work.delegateEffort=medium`, `work.delegateSandbox=yolo`, `work.delegateConsent=false`, `work.delegateDecision=auto`. Document the resolution chain — arg token `delegate:codex` / `delegate:local` > `work.delegate` config > hard default off. **The generic fuzzy "use codex" is NOT a delegation trigger** — it already means "review with Codex"; only `delegate:codex` / `delegate:local` (and the config) resolve here.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (`get_default_config()` ~L1106), `plugins/flow-next/tests/` (new test for defaults + resolution)

## Approach
- Add the `work` namespace to the defaults dict at `flowctl.py:1106` (`get_default_config()`). Confirm coexistence with the existing `work.*` / `tracker.perEvent.work.*` perEvent keys read in `phases.md:94-101` — the new `work.delegate*` keys must not clash with the tracker-sync `work.*` namespace.
- `set_config` (`flowctl.py:1267`) already takes arbitrary nested dot-paths + auto-coerces `true|false|digits`, so `config set work.delegate codex` works with no new flowctl command — the only change is the defaults block so `config get` (non-`--raw`) returns the spec defaults.
- Effort enum is `none|low|medium|high|xhigh` (gpt-5.5 supports `none`, NOT `minimal` — corrected per plan research / OpenAI gpt-5.5 model docs).
- `work.delegateDecision` default `auto`; its `auto|ask` *behavior* is implemented in fn-55.2 — this task only sets the default + documents the enum.
- This task implements the config-default half + a pure unit test of the resolution precedence (no skill wiring).

## Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:1106` — `get_default_config()` defaults dict (where the `work` block goes)
- `plugins/flow-next/scripts/flowctl.py:1267` — `set_config` (confirms arbitrary dot-path writes, no whitelist)
- `plugins/flow-next/scripts/flowctl.py:5299` `cmd_config_get` + `:5376` `cmd_config_set` — get merges defaults, `--raw` bypasses
- `plugins/flow-next/skills/flow-next-work/phases.md:94-101` — existing `work.*` / `tracker.perEvent.work.*` reads (namespace-coexistence check)

**Optional** (reference as needed):
- `plugins/flow-next/tests/` — existing flowctl config test patterns to mirror

## Acceptance
- [ ] `flowctl config get work.delegate --json` returns `false` on a fresh repo (default); `work.delegateModel` → `gpt-5.5`, `work.delegateEffort` → `medium`, `work.delegateSandbox` → `yolo`, `work.delegateConsent` → `false`, `work.delegateDecision` → `auto` — all WITHOUT any prior `config set`.
- [ ] `flowctl config set work.delegate codex` then `config get work.delegate` returns `codex`; an unrelated `config get tracker.perEvent.work.firstClaim` still resolves (no namespace clash).
- [ ] A deterministic unit test asserts the resolution precedence (arg `delegate:codex` beats config `false`; `delegate:local` beats config `codex`; absent arg falls to config; absent config falls to default off) and that a bare/generic "use codex" string does NOT resolve as a delegation trigger.
- [ ] Effort enum documented as `none|low|medium|high|xhigh` (no `minimal`); `medium` is the floor default.
- [ ] flowctl test suite green.

## Done summary
Added the work.delegate* Codex-delegation config defaults to flowctl's get_default_config() (delegate=false, model=gpt-5.5, effort=medium, sandbox=yolo, consent=false, decision=auto), mirrored the identical block into the dogfood .flow/bin/flowctl.py, documented the activation resolution chain (arg delegate:codex/delegate:local > config > default off; generic "use codex" stays the review backend), and added a 19-case unit test (defaults + precedence) wired into CI. impl-review (rp): SHIP, zero findings.
## Evidence
- Commits: 0962514c7c4cedd7a583b2454219a645c976e020
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' (816 tests OK, 2 skipped), python3 -m unittest tests.test_work_delegate_config -v (19 tests OK), live: flowctl config get work.delegate* on fresh repo returns spec defaults; config set work.delegate codex round-trips; tracker.perEvent.work.firstClaim still resolves
- PRs: