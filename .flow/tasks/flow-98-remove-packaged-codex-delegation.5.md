---
satisfies: [R4, R7, R10]
---
# flow-98-remove-packaged-codex-delegation.5 Docs sweep, CHANGELOG breaking-change entry, and the final gate

## Description
Point every doc that described packaged delegation at the prose route, confirm the per-spec backend fields survive untouched, and stage the breaking-change entry for the major release this ships in.

**Size:** M
**Files:** `plugins/flow-next/docs/orchestration.md`, `ralph.md`, `teams.md`, `flowctl.md`, `skills.md`, `docs/README.md`, repo `CLAUDE.md` (the delegation carve-out prose), `CHANGELOG.md`, `agent_docs/local-dev.md` (the fn-55.3 codex delegation early-proof smoke section and its `references/codex-delegation.md` pointer), `plugins/flow-next/skills/flow-next-impl-review/workflow-common.md` (dangling `references/codex-delegation.md` pointer at the foreground-rule note), `plugins/flow-next/skills/flow-next-qa/workflow.md` (same dangling pointer at the never-subtract note), `plugins/flow-next/skills/flow-next-setup/workflow.md` + its `references/model-routing-question-{cursor,grok,bridge}.md` (the `Scaffold + enable codex delegation` option and `HAVE_CODEX`-gated delegation wiring), `plugins/flow-next/tests/test_model_routing_scaffold.py` (frozen-option-string pin over the setup workflow prose — must move with the prose it pins), `plugins/flow-next/scripts/flowctl.py` (orphaned `codex classify-result` / `codex rollback-plan` subcommands — the classify-judge CLI surface .2 didn't own)
**Touches:** [plugins/flow-next/docs/orchestration.md, plugins/flow-next/docs/ralph.md, plugins/flow-next/docs/teams.md, plugins/flow-next/docs/flowctl.md, plugins/flow-next/docs/skills.md, plugins/flow-next/docs/README.md, CLAUDE.md, CHANGELOG.md, agent_docs/local-dev.md, .flow/usage.md, .flow/bin/**, plugins/flow-next/skills/flow-next-impl-review/workflow-common.md, plugins/flow-next/skills/flow-next-qa/workflow.md, plugins/flow-next/skills/flow-next-setup/**, plugins/flow-next/tests/test_model_routing_scaffold.py, plugins/flow-next/scripts/flowctl.py]

<!-- Updated by plan-sync: fn-98.2 done-summary review surfaced 4 dangling references the earlier Files/Touches list didn't name — added here rather than left implicit under "sweep by grep" -->
<!-- Updated by plan-sync: fn-98.4 done-summary handover note added agent_docs/local-dev.md's fn-55.3 smoke section (never named in an earlier task's Touches) and test_model_routing_scaffold.py (pins the setup workflow prose this task edits, must move with it) -->


### Approach
- Sweep by grep, not by memory: find every mention of the removed vocabulary across canonical docs and the repo instruction file, and either delete it or repoint it at the bridge recipe plus the routing preference. This sweep is not docs-tree-only: two skill workflow files carry a dangling pointer at `references/codex-delegation.md` (deleted in .2) — `flow-next-impl-review/workflow-common.md`'s foreground-rule note and `flow-next-qa/workflow.md`'s never-subtract note — reword both, do not just drop the dead link.
- `flow-next-setup/workflow.md` Step 6d still offers `Scaffold + enable codex delegation` as a Model Routing option (gated on `HAVE_CODEX=1`), and its `references/model-routing-question-{cursor,grok,bridge}.md` wire the same option through. Remove the delegation branch from the frozen option set and from each reference; the remaining options (`Scaffold` / `Skip`) are unaffected. `test_model_routing_scaffold.py` pins the frozen option strings and the never-pre-set-`work.delegateConsent` prose contract (group d) — update the pin in the same commit as the workflow.md edit, not before or after.
- `agent_docs/local-dev.md`'s "Codex delegation early-proof smoke (fn-55.3)" section still documents the manual `FLOW_DELEGATE_CODEX=1 codex exec …` verification procedure and points at the deleted `references/codex-delegation.md`. Delete the section (the packaged path it verified is gone) or repoint it if any part still applies to prose-routed bridges; state which in the summary.
- `flowctl.py` still carries the `codex classify-result` / `codex rollback-plan` subcommands that backed the classify judge's CLI surface — .2 removed the skill-prose caller (Phase 1.5) but not this implementation. Zero callers remain after .2; delete them here as part of the full-gate propagation pass, and check the schema/help text for matching entries.
- The repo's own instruction file carries a sanctioned-carve-out paragraph naming delegation as the one licensed second-LLM spawn. That paragraph must be rewritten, not deleted: the carve-out list still has members (review dispatch, the triage-skip judge), and the sentence that names them is doctrine.
- Confirm and state that `spec set-backend`'s per-spec impl/review/sync fields are untouched - they are data carriage for other control planes, not delegation.
- CHANGELOG under `## Unreleased`, outcome-first, framed as a breaking change for the next major: what disappears, what replaces it, and the one-line migration. Say plainly that routing became a preference you write rather than a subsystem you configure. No benchmark tables, no speed claims.
- **This task owns ALL propagation for the spec** (the earlier tasks deliberately skip it so they can wave): copy the module to the dogfood bin, regenerate the manifest, sync the mirror twice, and confirm the tree is clean.
- Full gate: the parallel suite with the exit code captured directly, plus the pinned linter.

### Investigation targets
**Required** (read before coding):
- repo `CLAUDE.md` sanctioned-carve-out paragraph - rewrite target, not a delete target
- `plugins/flow-next/docs/orchestration.md` delegation sections - the largest doc surface
- `agent_docs/releasing.md` - the changelog register and the breaking-change requirement for a major
- `plugins/flow-next/skills/flow-next-impl-review/workflow-common.md` ~line 96 and `plugins/flow-next/skills/flow-next-qa/workflow.md` ~line 208 - dangling `codex-delegation.md` pointers (fn-98.2 done-summary review)
- `plugins/flow-next/skills/flow-next-setup/workflow.md` Step 6d + `references/model-routing-question-{cursor,grok,bridge}.md` - the `Scaffold + enable codex delegation` option
- `plugins/flow-next/tests/test_model_routing_scaffold.py` - the frozen-option-string pin over the setup workflow prose above; must move with it
- `agent_docs/local-dev.md` ~lines 109-155 - the fn-55.3 codex delegation early-proof smoke section (fn-98.4 done-summary handover)
- `plugins/flow-next/scripts/flowctl.py` `codex classify-result` / `codex rollback-plan` - orphaned CLI surface, zero callers since .2

### Acceptance
- [ ] No canonical doc or repo instruction file describes packaged delegation as available; each mention deleted or repointed
- [ ] `workflow-common.md`'s and `flow-next-qa/workflow.md`'s dangling `codex-delegation.md` pointers reworded, not just unlinked
- [ ] `flow-next-setup`'s Model Routing question and its per-platform references carry no `Scaffold + enable codex delegation` option; `test_model_routing_scaffold.py`'s frozen-option-string pin updated to match
- [ ] `agent_docs/local-dev.md`'s fn-55.3 codex delegation smoke section deleted or repointed
- [ ] `flowctl.py`'s `codex classify-result` / `codex rollback-plan` subcommands removed (zero callers since .2); help text and schema checked for matching entries
- [ ] The sanctioned-carve-out paragraph rewritten with its remaining members, not removed
- [ ] `spec set-backend` fields verified untouched and stated as such in the summary
- [ ] `## Unreleased` CHANGELOG entry, outcome-first, marked breaking, with the migration line; no version bump
- [ ] Mirror regenerated twice (idempotent); full suite + linter green with exit codes captured directly

## Acceptance
- [ ] TBD

## Done summary
Swept every remaining description of packaged codex delegation out of the canonical docs, the setup ceremony, the repo instruction file, and flowctl's CLI surface; pointed each mention at the prose bridge route (setup model-routing scaffold + `flowctl usage` recipes); staged the `## Unreleased` breaking-change entry; and ran the spec's full propagation (dogfood bin copy, tracker manifest, codex mirror x3 idempotent) plus the final gate.

What changed, by acceptance item:

- **Canonical docs.** `orchestration.md`'s "Implementation delegation — `work` → `codex exec`" section is replaced by "Implementation offload — the bridge route", which states the offload is a routing decision you write rather than a subsystem you configure, and carries both R9 survivors explicitly: the bridged child writes code while the host keeps git, judgment, and the verdict; and the value-tier-matches-strong-tier-at-two-thirds-the-wall advice, with no benchmark table. Every downstream mention was repointed, not just unlinked: `flowctl.md` (config table rows, `models resolve` role list and example, the two removed subcommand sections), `ralph.md` (delegation section deleted, guard-table row for the `FLOW_DELEGATE_CODEX` allowlist removed — the guard itself lost that carve-out in .4), `running-lean.md` (the deprecated-layer entry became "Implementation offload (no layer to enable)" and the layer table row is gone), `skills.md`, `docs/README.md` (the deleted reference's row removed, anchors retargeted), `teams.md` (the `DELEGATION_*` control-signal example dropped — those lines no longer exist).
- **Dangling pointers reworded.** `flow-next-impl-review/workflow-common.md`'s foreground-rule note no longer names codex-delegation as "the one sanctioned background launch"; it now states the rule binds review commands and that a file-polled ad-hoc bridge is a different pattern. `flow-next-qa/workflow.md`'s never-subtract note now rejects any worker or bridged-child self-report as the gate rather than citing the deleted file.
- **Setup ceremony.** The `Scaffold + enable codex delegation` option is gone from `workflow.md`'s frozen option set (now `Scaffold` / `Skip`) and from all three `references/model-routing-question-*.md`; the delegation opt-in blocks are removed from `model-routing-{bridge,cursor,grok}.md`; the `delegate` row left `references/model-pins.md`; the completion report lost the `Codex delegation:` line and the `delegate` role-map key. `test_model_routing_scaffold.py`'s pin moved in the same commit and now asserts **non-regrowth** (`assertNotIn "Scaffold + enable codex delegation"`, `assertNotIn "work.delegate"`) instead of the retired consent contract; `smoke_test.sh` check 3 was converted the same way.
- **`agent_docs/local-dev.md`.** The "Codex delegation early-proof smoke (fn-55.3)" section was **deleted**, not repointed: everything it verified (the `--output-schema` result contract, the `FLOW_DELEGATE_CODEX` guard shape, the scratch-dir result poll) belonged to the packaged path. The MCP-isolation observation it contained is a property of `codex exec --ignore-user-config`, not of the deleted subsystem, and is not a flow-next gate — no part of the procedure still applies to prose-routed bridges.
- **flowctl.** `codex classify-result` and `codex rollback-plan` removed with their helpers (`classify_delegation_result`, `_result_is_valid_schema`, `rollback_plan`, `sanitize_rollback_path`, `_read_nul_delimited`, `_rollback_reject_reason`), their argparse wiring, and the stale "NOT classify-result/rollback-plan" comment on the cursor parser. Help text verified (`flowctl codex --help` now lists only the five review subcommands); `tests/test_flowctl_surface.py`'s command inventory updated; both `docs/flowctl.md` subsections deleted. The `work.delegate*`-era comment in `cmd_models_resolve`'s docstring was already clean from .1 — no change needed there.
- **Carve-out rewritten, not removed.** Repo `CLAUDE.md`'s narrow carve-out paragraph now says implementation offload is prose-routed and host-orchestrated (child writes code, host keeps git/judgment/verdict), and the "Sanctioned carve-out (subprocess LLM judgment)" sentence keeps its remaining members — review-backend dispatch and the triage-skip judge.
- **R7 verified untouched.** `flowctl spec set-backend --impl/--review/--sync` is byte-unchanged (the flowctl diff is deletions only, none of them in the backend surface; `--help` verified live). It stays data carriage for flow-swarm and other control planes.
- **Migration route dogfooded.** This repo's own `.flow/config.json` lost the six `work.delegate*` keys and `models.roles.delegate`; the advisory that fired on every flowctl call here is now silent. That is the exact route the CHANGELOG tells users to take.
- **CHANGELOG.** `## Unreleased` breaking-change entry, outcome-first, naming what disappears, the one-step migration (`/flow-next:setup` scaffold + `flowctl usage` bridge recipes), the inert-leftover-keys advisory, and both surviving rules. No version bump, no `bump.sh`, no manifest touch. The flow-next.dev docs-site changelog is handled downstream at release time (per `agent_docs/releasing.md`) — not written here.
- **Propagation + gate.** `cp` of `flowctl.py` to `.flow/bin/flowctl.py` (bash launcher untouched), `rsync` of `flowctl_tracker/`, `gen_tracker_manifest.py`, then `sync-codex.sh` run three times with an identical worktree hash after the second and third (idempotent). Baseline before any edit was RED (8 files) purely from the propagation the earlier tasks deliberately deferred to this one; it is green now.

Follow-ups noted, not built: `plugins/flow-next/docs/README.md`'s historical "Notable updates" bullet still narrates the 3.x deprecation (a past-release ledger entry, deliberately left as history with only its dangling anchor retargeted).

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)

stage: impl-review - ran (host backend, fresh fable-5 reviewer, SHIP round 1)
stage: plan-sync - skipped(empty: no downstream todo tasks)
## Evidence
- Commits: d960d6f51351197393ca18c6a3ded8d721cba87f
- Tests: python3 scripts/run_tests_parallel.py (files=192 ran=4407 failures=0 errors=0 skipped=8, suite_rc=0), uvx ruff@0.16.0 check . (All checks passed), ./scripts/sync-codex.sh x3 (idempotent: identical worktree state), plugins/flow-next/scripts/smoke_test.sh (not runnable in the plugin repo by design: 'refusing to run from main plugin repo'), impl-review: host backend SHIP round 1 (reviewer claude-fable-5, fresh read-only subagent; independently re-ran full gate green; receipt /tmp/impl-review-receipt-flow-98-remove-packaged-codex-delegation.5.json)
- PRs: