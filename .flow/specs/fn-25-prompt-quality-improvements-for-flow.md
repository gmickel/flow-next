# Prompt-quality improvements for flow-next agents

## Overview

Improve flow-next planning, implementation, and review quality through prompt-only changes to skill .md and agent .md files. Inspired by structured development workflow patterns (investigation targets, traceability, bidirectional coverage, typed escalation, confidence gating, test budget awareness).

**All changes are prose/prompt modifications. Zero changes to flowctl, .flow/ JSON schema, hooks, or runtime behavior.**

## Constraints (CRITICAL)

- Only modify files in `plugins/flow-next/skills/` and `plugins/flow-next/agents/`
- Zero flowctl CLI changes
- Zero .flow/ JSON schema changes
- Zero hook changes
- Ralph mode must work identically (same commands, same hooks, same flowctl calls)
- MergeFoundry compatibility: .flow/specs/*.md and .flow/tasks/*.md prose additions are additive — MergeFoundry layers runtime state on top, no conflicts
- No new dependencies
- Run `scripts/sync-codex.sh` after all changes to regenerate codex/ directory
- Version bump via `scripts/bump.sh patch flow-next` (prompt changes warrant patch, not minor)

## Approach

Eight prompt improvements grouped into 6 implementation tasks + 1 documentation task:

**Tier 1 (high value):**
1. Investigation targets in task specs — plan writes them, worker reads them
2. Requirement coverage traceability table in epic specs — plan writes, plan-sync maintains
3. Bidirectional coverage in epic-review — add code→spec reverse check
4. Early proof point in epic specs — plan identifies approach-validating task

**Tier 2 (good value):**
5. Typed escalation in worker blocks — structured block messages with category
6. Similar functionality search before implementation — worker greps before coding

**Tier 3 (nice-to-have):**
7. Confidence gating in scout outputs — Verified vs Inferred qualifiers
8. Test budget awareness in quality-auditor — flag disproportionate test generation

## File change map

| File | Changes |
|------|---------|
| `plugins/flow-next/skills/flow-next-plan/steps.md` | Investigation targets in task template, traceability table + early proof point in epic template |
| `plugins/flow-next/skills/flow-next-plan/examples.md` | Good/bad examples for investigation targets, traceability table |
| `plugins/flow-next/agents/worker.md` | Pre-implementation investigation phase, similar functionality search, typed escalation |
| `plugins/flow-next/skills/flow-next-epic-review/workflow.md` | Code→spec reverse coverage check |
| `plugins/flow-next/agents/plan-sync.md` | Traceability table maintenance on drift |
| `plugins/flow-next/agents/repo-scout.md` | Verified/Inferred confidence qualifiers in output |
| `plugins/flow-next/agents/context-scout.md` | Verified/Inferred confidence qualifiers in output |
| `plugins/flow-next/agents/quality-auditor.md` | Test budget ratio check (advisory) |
| `plugins/flow-next/README.md` | Document new features in Features section |
| `README.md` | Add row to "Why It Works" table |
| `CHANGELOG.md` | [flow-next 0.27.1] entry |

## Quick commands

```bash
# Verify no schema/hook changes were introduced
git diff --name-only | grep -v -E '(skills/|agents/|codex/|\.codex-plugin|\.claude-plugin|CHANGELOG|scripts/sync|README)' && echo "UNEXPECTED FILES CHANGED" || echo "OK: only expected files"

# Smoke test
plugins/flow-next/scripts/smoke_test.sh

# Sync codex after all changes
scripts/sync-codex.sh
```

## Acceptance

- [ ] Investigation targets section added to task spec template in steps.md
- [ ] Traceability table added to epic spec template in steps.md
- [ ] Early proof point added to epic spec template in steps.md
- [ ] examples.md updated with good/bad examples for new sections
- [ ] Worker reads investigation targets before implementing
- [ ] Worker searches for similar functionality before implementing
- [ ] Worker uses typed escalation categories when blocking
- [ ] Epic-review checks code→spec direction (not just spec→code)
- [ ] Plan-sync updates traceability table when drift detected
- [ ] Scouts output Verified/Inferred confidence qualifiers
- [ ] Quality-auditor flags disproportionate test generation (advisory only)
- [ ] `scripts/sync-codex.sh` runs clean — codex/ regenerated
- [ ] `plugins/flow-next/scripts/smoke_test.sh` passes
- [ ] No changes to flowctl, .flow/ JSON, or hooks
- [ ] Ralph mode unaffected (no new commands, no changed hook patterns)
- [ ] Flow-next README Features section documents new behaviors
- [ ] Root README "Why It Works" table updated
- [ ] CHANGELOG has [flow-next 0.27.1] entry
- [ ] Version bumped via `scripts/bump.sh patch flow-next`

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Investigation targets in task specs | .1 (plan), .2 (worker) | — |
| R2 | Requirement coverage traceability table | .1 (plan), .4 (plan-sync) | — |
| R3 | Bidirectional epic-review | .3 | — |
| R4 | Early proof point in epic specs | .1 | — |
| R5 | Typed escalation in worker | .2 | — |
| R6 | Similar functionality search | .2 | — |
| R7 | Confidence gating in scouts | .5 | — |
| R8 | Test budget awareness | .6 | — |
| R9 | Documentation updates | .7 | — |
| R10 | Version bump + codex sync | .7 | — |

## Early proof point
Task .1 validates the core format (investigation targets + traceability table in plan output). If the plan skill changes feel too heavy or the output format is awkward, simplify before proceeding to worker/review tasks.
