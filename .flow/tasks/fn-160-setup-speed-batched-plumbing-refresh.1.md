---
satisfies: [R1, R2]
---
# fn-160-setup-speed-batched-plumbing-refresh.1 flowctl plumbing: setup detect --json + batched config set

## Description
Add a `setup` command group to flowctl with `setup detect --json` (one-call replacement for workflow.md Step 6a's piecemeal probes) and extend `config set` to accept multiple `key=value` pairs in one invocation.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_setup_detect.py` (new), `plugins/flow-next/tests/test_config_set_batch.py` (new), `plugins/flow-next/docs/flowctl.md`

### Approach
- Register `setup` as a new top-level group beside `setup-block`/`setup-mode` (parser registration pattern at `flowctl.py:42209-42843`).
- `setup detect --json` wraps the existing keyless-root ConfigSnapshot read (`cmd_config_get`, `flowctl.py:17307-17386`) — do NOT re-read config per key. Output one JSON object: raw (`--raw` semantics) values for every key Step 6a probes (review.backend, memory.enabled, planSync.enabled, planSync.crossSpec, scouts.github, artifacts.html.enabled, tracker.specIds, models + models.verifiedAt), plus `tracker_active` (reuse the `sync active` predicate), `criteria_exists` (-e||-L semantics from workflow.md:351), and CLI detection (`have_rp` incl. the RepoPrompt CE path probes, `have_codex`, `have_copilot`, `have_cursor`, `have_grok`, derived `bridge_detected`). Platform classification stays in skill prose (env-var visibility belongs to the host shell) — detect returns tool/file facts only.
- Failure contract: an individual probe error yields a null/error-marked field, never a non-zero exit for the whole call.
- Batched `config set`: repeated `key=value` positionals (keep single-key form working). Validate ALL keys through the existing per-key validators (`cmd_config_set`, `flowctl.py:17388+`) before writing anything; one atomic write; any invalid key → no write, itemized error.
- Memory lesson (id-grammar sweep): grep every consumer of `cmd_config_set` args and the flowctl.md config table for surface drift.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:17307-17386` — keyless root config read to wrap
- `plugins/flow-next/scripts/flowctl.py:17388-17472` — per-key validation to preserve under batching
- `plugins/flow-next/skills/flow-next-setup/workflow.md:299-372` — exact Step 6a probe semantics to reproduce (incl. `--raw` null-vs-false jq subtlety)
- `plugins/flow-next/scripts/flowctl.py:42209-42843` — parser registration pattern

**Optional:**
- `plugins/flow-next/skills/flow-next-plan/steps.md:74-87` — the config-snapshot-once prior art
- `plugins/flow-next/docs/flowctl.md` — `### setup-mode` / `### setup-block` sections as doc format template

### Key context
- The `--raw` distinction is load-bearing: merged reads return defaults for unset keys and would break the "only ask unset questions" gate (PR #135 cycle 2). detect must expose raw (absent = null) values.
- No new config keys → `gen_flow_config_schema.py` untouched. If implementation ends up needing one, it must go through the fn-138 TABLE + drift test in the same commit.
- Final gate when flowctl.py changes: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py` + tracker rsync + `gen_tracker_manifest.py` + `./scripts/sync-codex.sh` twice (per project CLAUDE.md).

### Acceptance
- [ ] `flowctl setup detect --json` returns every Step 6a datum in one call; per-field degradation on probe failure
- [ ] `flowctl config set a.b=1 c.d=true --json` validates all keys before writing; single atomic write; single-key form unchanged
- [ ] New focused tests green; `docs/flowctl.md` gains `### setup` + batched-set docs
- [ ] `uvx ruff@0.16.0 check .` green; propagation + sync-codex ×2 clean

## Acceptance
- [ ] R1: one-call detect replaces per-key probe fences (semantics identical incl. --raw null handling)
- [ ] R2: batched config set, validate-all-then-write-all, per-key validators preserved


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
