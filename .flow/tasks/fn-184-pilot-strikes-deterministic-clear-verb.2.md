---
satisfies: [R3, R4]
---
# fn-184-pilot-strikes-deterministic-clear-verb.2 Pilot skill prose + repo docs truth-sweep

## Description
Spec fn-184 items 2-3 (#325). Pilot workflow.md: the Phase 1 item 3 armed-readyState escape clause names `flowctl pilot strikes clear <spec-id>` as THE recognized human clear; the strike-2/2 BLOCKED terminal reason names the verb (transcript carries its own recovery); the ledger-ownership sentence ('skill-owned scratch; no flowctl plumbing') updates to the shared contract; null-readyState clear-on-ready path behaviorally byte-identical. Repo docs: tracker-sync.md Pilot-interplay paragraph corrected to the fn-87 rule + verb recovery; troubleshooting.md gains a strikes-ledger entry (location, what a strikeout looks like, list/clear recovery). SWEEP, not spot-fix: grep the whole repo for surfaces asserting projection-clears-strikes (R4 says no repo surface remains). backlog-mode.md reference likely needs the same escape-clause naming. Fixtures follow the pin-shape rule (content + reachability, smallest distinctive tokens - NO sentence pins). Conduct checklist: agent_docs/conduct/pilot.md. sync-codex twice.

**Files:** plugins/flow-next/skills/flow-next-pilot/workflow.md + references/backlog-mode.md; plugins/flow-next/docs/tracker-sync.md; plugins/flow-next/docs/troubleshooting.md; codex mirror regen; prose-contract fixtures

## Acceptance
R3, R4 of the spec. Escape clause + terminal reason name the verb; no repo surface asserts pre-fn-87 behavior; conduct checklist pass/fail reported.

## Done summary
Prose sweep per fn-184 R3-R4 (#325). workflow.md Phase 1 item 3 escape clause rewritten: flowctl pilot strikes clear <spec-id> is THE recognized human clear under armed readyState, with the honest statement that no board state can serve (deliberate re-ready and echo byte-identical in every durable artifact); strike-2/2 BLOCKED terminal reason carries "clear with: flowctl pilot strikes clear <id>" so the transcript names its own recovery; Phase 0 ledger-ownership sentence updated to the shared contract (flowctl reads+clears, skill records). backlog-mode.md 1g same correction. tracker-sync.md Pilot-interplay paragraph corrected (projection-set ready never clears a strike; recovery is the verb, not the board; board stays the readiness control plane); troubleshooting.md strikes-ledger entry; flowctl.md pilot strikes section (in-scope extension - the anchor both docs link). Sweep enumerated: 3 assertion sites corrected, 14 surfaces checked clean, historical CHANGELOG/spec records deliberately left frozen. Conduct checklist pilot.md 6/6 pass. New reachability-shaped fixture suite, no sentence pins.
## Evidence
- Commits: ea767749
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_pilot_strikes_prose test_pilot_strikes test_ralph_docs_truth test_flowctl_surface test_review_findings_docs -q (44 OK), test_prompt_text_pinned test_skill_prose_diet (29 OK), python3 scripts/run_tests_parallel.py (4458 OK)
- PRs: