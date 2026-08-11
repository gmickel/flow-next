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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
