---
satisfies: [R3, R5]
---
# fn-194-land-merge-identity-seam-server-side.3 Post-merge tail reorder: close -> release -> tracker -> persist-push

## Description
R3 in the land skill. Reorder §3.5's post-merge tail (~:580-673): 1 spec close (local commit, no push); 2 release-follow (precondition: clean non-.flow tree - holds, the close is committed); 3 tracker touchpoint (already gated on the fresh MERGED probe ~:632-644, NOT on the close being pushed - state that inline); 4 persist: push the close commit AND the ~:673 tracker-sync-state commit together, with rollback-on-refusal isolated to THIS step - a refused push no longer skips release-follow or the tracker touchpoint; the residue is the per-spec NEEDS_HUMAN 'spec close not pushed' bookkeeping note. State the dedupe reasoning inline (verdict comments key on the merge-commit identity ~:652; release-follow has its idempotency probe ~:614) so a re-tick after a failed persist is visibly safe. Update §3.6 re-entry prose to match the new order. Add one tail line to agent_docs/conduct/land.md (release and tracker precede the persist-push; a refused persist affects bookkeeping only). Static ordering tests in test_land_config.py: close before release-follow before tracker before push (index assertions on section tokens); the rollback scoped to the persist step. sync-codex x2. Gate BARE: test_land_config + test_skill_prose_diet.

## Acceptance
R3 met; ordering pinned; conduct line added; a persist refusal demonstrably (by prose + pins) cannot skip release/tracker; sync-codex idempotent.

## Done summary
Post-merge tail reordered: close (local commit) -> release-follow -> tracker touchpoint -> one persist-push carrying both .flow commits, rollback scoped to the persist via the recorded pre-tail base tip - a refused push yields only the bookkeeping NEEDS_HUMAN; merge/release/tracker stand. Re-tick safety stated inline (MERGED probe, comment dedupe, release idempotency). §3.6 + SKILL summary (which was already stale) + conduct line updated. 8 ordering pins, 96 tests green.
## Evidence
- Commits: 2d3f4a0e
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_land_config test_skill_prose_diet -q
- PRs: