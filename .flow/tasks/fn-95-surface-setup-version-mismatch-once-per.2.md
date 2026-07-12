---
satisfies: [R4, R7]
---

## Description
Loud, durable mismatch signal in AUTONOMOUS skills + mirror regen + CHANGELOG.

**Size:** S | **Files:** pilot + land SKILL/workflow files (SETUP_STALE line immediately before PILOT_VERDICT / LAND_VERDICT emission), codex mirror (regen via scripts/sync-codex.sh), CHANGELOG.md (Unreleased)

## Approach
- Emit `SETUP_STALE: local vX, plugin vY, run /flow-next:setup` adjacent to the terminal verdict line on mismatch - UNSUPPRESSED by version_ack (per spec R4: loud in logs regardless of interactive acks); grep-able fixed prefix.
- Regenerate the codex mirror; run the full unittest suite + sync validation.
- CHANGELOG entry under Unreleased (no version bump, batched releases).

## Acceptance
- [ ] SETUP_STALE line emitted before both verdicts on mismatch, never blocks, not suppressed by ack
- [ ] Mirror regenerated + validation green; unittest suite green
- [ ] CHANGELOG Unreleased entry present

## Done summary
Added a grep-able SETUP_STALE line to /flow-next:pilot and /flow-next:land: on a setup-version mismatch the pre-check stashes `SETUP_STALE: local vX, plugin vY, run /flow-next:setup` and emits it immediately before the terminal PILOT_VERDICT / LAND_VERDICT line at every emission site (including hard-guard exits), unsuppressed by version_ack, fail-open, never blocking. Regenerated the codex mirror (lines carry verbatim; sync validation green) and added a CHANGELOG Unreleased entry covering the whole fn-95 spec.
## Evidence
- Commits: d22c466cc04c773937f9312893d6c74ef5d8d702
- Tests: python3 -m unittest discover plugins/flow-next/tests (1581 tests, OK, exit 0; baseline green), bash scripts/sync-codex.sh (all validators green)
- PRs: