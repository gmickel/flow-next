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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
