---
satisfies: [R2, R4, R12]
---
# fn-130-reached-path-skill-prompt-optimization.3 Route Setup host and optional branches on demand

## Description
Refactor the 112 KB Setup workflow into a compact common path plus direct references for genuinely optional or mutually exclusive host/model/Ralph branches. Preserve all first-install, refresh, marker-safe, configuration, model-pin, and setup-mode behavior.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-setup/SKILL.md`, `workflow.md`, new or reorganized `references/*.md`, setup templates only if routing requires no semantic content change, `plugins/flow-next/tests/test_setup_*.py`, `test_model_routing_scaffold.py`, `test_model_pin_ceremony_prose.py`, `test_setup_snippet_lockstep.py`, corresponding Codex mirror, `optimization/reached-path/setup-*`.

### Approach
- Keep common path detection, initialization, copy/stamp, ordinary config questions/processing, and summary coherent.
- Gate model-routing question/scaffold, model-pin refresh, selected Cursor/Grok/bridge implementation, and Ralph question/processing by explicit branch state.
- Use one-level direct references and a forcing instruction; unknown state loads the safe/common material.
- Preserve variables in the same shell fence that consumes them, ask-between-fences behavior, replace-not-append fallbacks, `$TMPDIR` scratch, and every-terminal cleanup.
- Treat exact marker/byte comparison, template twins, shim handling, autonomous silence, and platform defaults as frozen.

### Frozen fixtures
- Clean first copy install; pristine copy refresh; plugin mode; customized snippet Keep/Overwrite/Skip; missing marker/hash; malformed metadata.
- Interactive and autonomous runs; model-pin write/stamp/skip; routing scaffold accepted/kept/customized; Ralph yes/no/unsupported.
- Claude, Codex, Droid, Cursor, and Grok host routes; installed bridge present/absent; unavailable model enumeration.

### Investigation targets
**Required**
- `plugins/flow-next/skills/flow-next-setup/workflow.md:5-313` — common install/setup-mode/config foundation.
- `plugins/flow-next/skills/flow-next-setup/workflow.md:511-785` — optional routing/Ralph/model-pin question branches.
- `plugins/flow-next/skills/flow-next-setup/workflow.md:895-1071` — host-specific scaffold and Ralph processing.
- `plugins/flow-next/tests/test_model_routing_scaffold.py:132-405` — canonical/mirror/probe contracts.
- `.flow/specs/fn-99-setup-block-diet-evidence-schema-inline.md` — template and evidence locks.

**Optional**
- `plugins/flow-next/tests/test_setup_cursor_host.py` and `test_setup_grok_host.py` — host-native path assertions.

## Acceptance
- [ ] Task input prompt hashes match version-adjusted `V1/B1`; every structural candidate compares against `B1`, never original `B0`.
- [ ] Baseline traces exist before mutation for every Setup fixture family and all five host selectors.
- [ ] Autonomous/default runs avoid all cold model-pin/scaffold/Ralph branches; interactive runs load only the selected host implementation plus applicable questions.
- [ ] First install, refresh, copy/plugin mode, customized marker replacement, config writes, model pins, Ralph, stamp-last, and summaries match baseline observables.
- [ ] Malformed/unknown state fails open; no required safety branch is silently skipped.
- [ ] Existing setup/model-routing/template tests and new route-read assertions pass on canonical and mirror.
- [ ] Candidate records a measured reached-path improvement; if zero-loss cannot be demonstrated, revert the router and retain the fixture evidence as a discard.
## Done summary
Refactored Setup into a 69,591-character common path plus one-level, state-gated model-pin, host-routing, and Ralph references. Added canonical route-read contracts and frozen V1/B1 candidate evidence showing 27.81%–32.88% reached-path reduction across all 16 Setup fixtures; generated Codex mirror regeneration remains deferred to the conductor.

Verification:
- `python3 optimization/reached-path/run_eval.py --check-b1-input setup` — green before mutation.
- `python3 optimization/reached-path/run_eval.py --validate-b1` — 117 manifests valid.
- Parent focused structural suite — 545 tests green.
- Setup router/model/template suite — 72 tests green.
- Authenticated Claude reached-path eval not run: this parallel-wave task explicitly required Codex-only execution.
## Evidence
- Commits: 0a4400f7, ed9b6206, 63e9942e, 3e4e92ee, f3d1ff79, f7c85984, e901aa00, 1ab5bb3b, 0f08c608, c00dc797, c0142c0d, 97e9793a
- Tests: ./scripts/sync-codex.sh twice: 28 skills, 22 agents, idempotent, python3 scripts/run_tests_parallel.py: 2,286 run, 3 skipped, 0 failures/errors, bash plugins/flow-next/scripts/smoke_test.sh from /tmp: 136 passed, 0 failed, flow-next.dev build: Astro check 0 errors/warnings/hints; 74 pages built, git diff --check and changed-reference existence audit: passed, Prime authenticated Claude baseline and candidate: 7/7 each; 6/6 synthetic plus negative control
- PRs:
