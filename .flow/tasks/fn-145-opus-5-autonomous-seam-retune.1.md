---
satisfies: [R1, R2, R7, R9]
---
# fn-145-opus-5-autonomous-seam-retune.1 Replace false inline control-transfer seams

## Description
Replace false same-session `STOP` and fictional return-to-caller wording with
explicit read/execute/continue instructions at the reached Pilot, Work, and
plan-review seams. Preserve every genuine terminal boundary and default-off
gate.

**Size:** M

**Files:**
- `plugins/flow-next/skills/flow-next-pilot/SKILL.md`
- `plugins/flow-next/skills/flow-next-pilot/workflow.md`
- `plugins/flow-next/skills/flow-next-work/phases.md`
- `plugins/flow-next/skills/flow-next-plan-review/references/workflow-*.md`
- focused prose/reached-path tests under `plugins/flow-next/tests/`

### Approach

- Change only inline transition language; keep sentinels, activation probes,
  stage actions, verdict tags, and last-line contracts intact.
- Carry selected review verdicts directly into the existing shared fix loop.
- Add narrow canonical-and-mirror assertions that distinguish false seams from
  real worker, subprocess, retry-cap, Ralph, Pilot, and Land terminals.

### Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-work/phases.md:126-133,222-226,415-419,529-534`
- `plugins/flow-next/skills/flow-next-pilot/SKILL.md:105-120`
- `plugins/flow-next/skills/flow-next-pilot/workflow.md:303-318`
- `plugins/flow-next/skills/flow-next-plan-review/SKILL.md`
- `plugins/flow-next/skills/flow-next-plan-review/references/workflow-common.md`

**Optional:**
- `.flow/specs/fn-130-reached-path-skill-prompt-optimization.md`
- `plugins/flow-next/tests/test_pilot_backlog_mirror_safety.py`
- `plugins/flow-next/tests/test_skill_prose_diet.py`

### Key context

This is a prompt-seam clarification, not a stage deletion. Do not weaken typed
terminal outcomes or broaden the wording sweep into machine-readable contracts.

## Acceptance
- [ ] All targeted Pilot/Work forced-reference sites instruct the host to read,
  execute, and continue to the named next phase without `STOP` framing.
- [ ] Plan-review backend workflows continue directly into the shared fix loop
  without fictional return-to-caller wording.
- [ ] Default-off probes and activated actions are unchanged.
- [ ] Tests reject false-seam phrases while preserving genuine terminal
  contracts in canonical and generated skill trees.
- [ ] Focused Pilot, prose-diet, reached-path, and prompt-pin tests pass.


## Done summary
Replaced false same-session control-transfer wording in Pilot, Work, and Plan
Review with explicit read, execute, and continue instructions. Preserved
default-off/fail-open gates and genuine terminal verdicts. Added canonical and
Codex mirror prose/reached-path regression coverage.
## Evidence
- Commits: d58e69f0
- Tests: cd plugins/flow-next/tests && python3 -m unittest -q test_pilot_backlog_mirror_safety test_skill_prose_diet test_work_reached_path_routes test_prompt_text_pinned (98 passed, worker), fresh read-only host quality review (SHIP; 57 focused tests passed)
- PRs: