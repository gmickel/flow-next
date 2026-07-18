---
satisfies: [R7, R9, R11]
---

## Description

Foundations for the background tracker-runner: the shared discipline reference, the runner agent, and the sync-codex plumbing.

**Size:** M
**Files:** plugins/flow-next/references/tracker-dispatch.md (NEW), plugins/flow-next/agents/tracker-runner.md (NEW), plugins/flow-next/skills/flow-next-tracker-sync/steps.md (RALPH gate one-liner), scripts/sync-codex.sh (sandbox_for + role rewrite + guard), codex mirror (regen)

1. Write references/tracker-dispatch.md per the spec's Approach item 1 - the five-sentence discipline, both MUST invariants, join mechanics (notification-driven; TaskOutput(block=true) on agent tasks FORBIDDEN), host gate, degradation, recovery. Hard cap 50 lines.
2. Write agents/tracker-runner.md per Approach item 2: model sonnet, disallowedTools: Task, contract inputs, executes the existing tracker-sync skill body for ONE op, TERMINAL line `TRACKER_RUNNER=<status> spec=<id> note="..."` (full receipt enum). State plainly: hosts parse the LAST line.
3. tracker-sync steps.md RALPH gate: add `|| "${DISPATCH:-}" == "forked"` (one line, current gate at steps.md:21-26).
4. sync-codex.sh: sandbox_for gains `tracker-runner) echo "workspace-write"`; global `Task flow-next:tracker-runner` -> `tracker_runner` role rewrite + hard-fail guard (fn-100 transform+guard pattern); regen twice, idempotent, guards green; verify codex/agents/tracker-runner.toml generated with workspace-write.
5. Proof point (R9): dispatch one real runner (comment op, linked spec, dedup-safe) and parse the terminal line from its LAST line; record in evidence.
6. Tier B regression re-verify (R8): the 2026-07-18 probe PASSED (codex-cli 0.144.1, exec surface, sol spawn -> parent read CHILD_SAID=PROBE_OK_74192 verbatim, 15.7k tok). Re-run the same one-shot echo probe on the then-current CLI before shipping; a regression demotes Codex to Tier C in the ladder prose with the probe output recorded.

## Acceptance
- [ ] R11: reference exists, <=50 lines, sole statement of the rules
- [ ] R9: terminal-line contract written + live-parsed once
- [ ] R7: RALPH gate one-liner; runner prose points at the existing skill body (no second implementation)
- [ ] sync-codex: toml generated (workspace-write), rewrite + guard green, idempotent

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
