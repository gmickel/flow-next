---
satisfies: [R14, R15, R29]
---
# fn-139-tracker-sync-determinism-flowctl-owns.8 Remove tracker-runner dispatch; rewire callers; verify inactive path

## Description
Remove the `tracker-runner` agent and `references/tracker-dispatch.md`; lifecycle touchpoints call `flowctl tracker <verb>` directly, since a subprocess needs no subagent dispatch.

Sweep all fourteen calling skills plus the codex mirror and `docs/platforms.md` Tier-B text so no dangling reference to the deleted agent remains (fn-89 teardown, R29).

**R14 verification belongs here**, after rewiring, because .8 is what changes the final inactive path: assert via the reached-path harness that a bridge-inactive run is byte-for-byte unchanged.

## Acceptance
- [ ] tracker-runner agent + dispatch reference removed
- [ ] Zero dangling references across skills, codex mirror, docs/platforms.md
- [ ] All touchpoints call flowctl directly
- [ ] Bridge-inactive path byte-for-byte unchanged (reached-path harness)
- [ ] sync-codex.sh run twice, mirror committed

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
