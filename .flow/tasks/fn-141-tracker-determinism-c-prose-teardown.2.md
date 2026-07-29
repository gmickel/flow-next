---
satisfies: [R3, R4, R5]
---
# fn-141-tracker-determinism-c-prose-teardown.2 Remove tracker-runner; rewire callers; RETAIN the caller gate

## Description
Touchpoints call the **fn-140 lifecycle facade** `flowctl tracker sync <spec-id> --op push|pull|reconcile|comment --event <key>` - NOT the granular verbs, which cannot preserve behavior alone (create-if-unlinked, comment markers, dedup and receipts are orchestration). **Gated on fn-140 R19 conformance.** Then remove the `tracker-runner` agent and `references/tracker-dispatch.md`.

**Retain the caller-side gate** - only transport-ladder and dispatch prose is removed. Every flowctl command emits JSON and `inactive` is an error class, so routing a bridge-inactive repo into flowctl would replace silence with output and an extra process. The gate is what preserves the invariant that non-tracker users see nothing.

Explicitly enumerate the `perEvent` to verb mapping (`push`/`reconcile`/`comment`) rather than deleting it with the dispatch prose, and reassign comment content synthesis by name to each calling skill so it is not orphaned.

Sweep is **enumerated, not a single grep**: every canonical calling skill by name; `scripts/sync-codex.sh` (**19 matching lines / 29 runner-token occurrences**, including transforms and guards); runner-specific tests; the generated mirror's agent TOML; `docs/platforms.md`. Use the explicit path/token inventory in `test_tracker_caller_oracle.py`, asserted against the pinned pre-teardown tree; do not substitute a prose count. <!-- Updated by plan-sync: fn-141-tracker-determinism-c-prose-teardown.7 used an explicit 19-line/29-token inventory, not the planned 18-reference count -->

## Acceptance
- [ ] tracker-runner agent + dispatch reference removed
- [ ] Caller-side gate retained; perEvent->op mapping enumerated for ALL values incl. `pull`
- [ ] Comment synthesis reassigned by name to each calling skill
- [ ] Zero dangling references across the ENUMERATED inventory incl. sync-codex.sh transforms/guards, runner tests, mirror TOML (asserted by test over the named list)
- [ ] sync-codex.sh run twice, mirror committed

## Done summary
Rewired every tracker lifecycle caller to the fn-140 facade while retaining the silent caller gate, full perEvent mapping including pull, QA coercion, unconditional make-pr and land paths, fixed Work operations, and caller-owned comment synthesis. Removed the tracker runner and dispatch reference, deleted Codex-specific runner machinery, regenerated the mirror twice, and added oracle guards for the full teardown inventory and bounded retro-fire paths.
## Evidence
- Commits: 231d724a84045d6c3267130a96c578593bd97fe8, 5a72d35e9725d2869abd1905571797301cba0ae6, 1e318ecb4b96edc23df9c9b8b883f06b19c807db
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_caller_oracle test_tracker_sync_prose_teardown test_cursor_agent_frontmatter test_prompt_text_pinned -q, cd plugins/flow-next/tests && python3 -m unittest test_tracker_sync_mirror_parity test_reached_path_harness -q, ./scripts/sync-codex.sh (twice, repeated after review fix), Codex impl-review: SHIP (gpt-5.6-sol, medium)
- PRs: