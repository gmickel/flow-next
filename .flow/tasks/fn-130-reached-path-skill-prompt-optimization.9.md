---
satisfies: [R2, R10, R12]
---
# fn-130-reached-path-skill-prompt-optimization.9 Gate Strategy first-run and update branches

## Description
Apply one conservative Strategy cold-branch extraction: route absent/husk first-run versus generated update behavior without broad prose trimming. Make PR and Pilot are separate tasks 130.11 and 130.12.

**Size:** S
**Files:** `plugins/flow-next/skills/flow-next-strategy/**`; existing Strategy optimization assets/tests; `optimization/reached-path/strategy-*`; corresponding Codex mirror.

### Approach
- Verify task input hashes match `V1/B1`; compare candidates only against `B1`.
- Select absent/husk first-run or generated update path while preserving foreign/user-authored non-clobber and confirmation behavior.
- Keep shared strategy vocabulary and write safety at the consuming action sites.
- Score and log each mutation separately; retain discards.

### Frozen fixtures
- missing STRATEGY.md; husk; foreign file Keep; foreign file abort; generated first-run; generated update with preserved custom content; malformed/unknown classification.

### Investigation targets
**Required**
- `plugins/flow-next/skills/flow-next-strategy/SKILL.md` — route classification and mutually exclusive phases.
- Existing Strategy tests and optimization artifacts.

**Optional**
- fn-84/fn-85 optimization constraints.

## Acceptance
- [ ] Task input hashes match `V1/B1`; Strategy has an independent `B1`/candidate ledger and every candidate can be kept or discarded without affecting Make PR or Pilot.
- [ ] First-run/update routing preserves husk/foreign/generated classification, user-content non-clobber, questions, writes, and summary.
- [ ] Unknown/malformed state fails open toward the safe classification path.
- [ ] Existing and new route assertions pass on canonical and Codex mirror.
- [ ] Reached-path improvement and every discard reason are recorded without claiming unmeasured wall-time gains.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
