---
satisfies: [R1, R2, R3, R4]
---
# fn-297-defect-route-legitimate-state-fixes-and.1 Implement Defect route: legitimate-state fixes and the reported surface

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Defect route (plugins/flow-next/skills/flow-next-work/references/defect-route.md): diagnosis step 2 makes persisted state (config files, caches, lock files, serialized records, migrations) the first candidate when a failure appears only after a restart, reload or second run, eliminated with evidence before code is suspected. Before designing the fix, diagnosis decides whether the triggering state may legitimately occur; when it should never exist, the fix goes where the state was produced, and a fix shaped as a guard, retry, swallowed error, clamped value or discarded state says why the state is legitimate (undecidable: asked attended, evidence-backed default recorded unattended). Step 4 runs base and head observations through the surface the report came from (command, request, call or app); a unit test of the changed branch is supporting evidence only, and a report with no named surface uses the one a user meets first, recorded on the base line. pipeline-variations.md, CHANGELOG Unreleased and the Codex mirror updated.

Timing (R4): same-time A/B on the comparison harness's two defect cases at head 4d349f5d, 3 draws per arm: median first hand-back 149 -> 129 s on the small defect and 263 -> 176 s on the hard defect; judge no worse; all hidden checks pass. Hard-case wall time was higher on B (698 -> 945 s median), driven by one draw's long contended-core benchmark during reproduction and a base-versus-head full-suite comparison during proof; both arms' walls roughly doubled against the previous round.

Decisions:
- The always-on signal line (one record line naming the log line, check or metric that would have shown a hard-to-find cause) was built, measured over five rounds and dropped. Its payoff falls on a later defect the comparison cannot measure, agents wrote it in under half the cases it targeted, and the wordings that raised uptake slowed the first hand-back (+23..+35 s on the small defect when mandatory). The spec's acceptance is now R1-R4.
- flow-next.dev "Bug or defect" steps 2 and 4 updated on local site branch docs/fn-297-defect-route (33e662b), not pushed: held for the release, like the other specs in this set.

stage: impl-review - ran [round 1 NEEDS_WORK (timing criterion only), re-review NEEDS_WORK (timing), re-review at 4d349f5d SHIP] (model: codex gpt-6-astra high)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 45625d9efafbd79ccbe9bd36c6c759d4cb5f9235, 710228fd4ed891dda31285579591cb10b0ec996e, 3bec86976c3e69801596da20cf5e964a2df7ccbc, d914cb693ad170306a5622f573331424b74516c4, 1fdbf302af5982e94fb4883a2eab82f9ec9f18f6, 8be3653f561e72dc5a505dca8ac856126db73776, 4d349f5d2dcc2e8b79b72f4223829f4360ed4314
- Tests: uv run --with pytest python -m pytest -q test_flow_routing.py test_shipped_links.py test_sync_codex_check.py test_reference_encoding_guard.py test_skill_prose_flowctl_surface.py test_skill_prose_diet.py test_pr_cognitive_aid*.py test_export_cognitive_aid.py (plugins/flow-next/tests), uvx ruff check .
- PRs: