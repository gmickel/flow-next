---
satisfies: [R1, R2]
---
# fn-125-cursor-scout-pin-wiring-consume-the.2 Wire Plan + Prime scout fan-outs to the shared contract

## Description
Wire the Plan + Prime scout fan-outs to the shared contract (CONSUME path; skip/adapt if DROP chosen in task 1). Update flow-next-plan/steps.md, flow-next-prime/SKILL.md + workflow.md; add test_cursor_scout_routing.py. Resolve the Cursor scout pin ONCE before each fan-out and pass it as the caller-side model to: every selected Plan scout across both repo-scout/context-scout branches + all depth tiers + optional memory/GitHub scouts + flow-gap-analyst; all nine Prime Phase-1 scouts + Prime's one-time per-scout retry. Every pinned dispatch keeps tool-enforced read-only. Claude Code unchanged (no agents/*.md edits - native frontmatter aliases still drive tiering there).

## Acceptance
- Plan applies the resolved pin across both scout branches, every depth tier, optional memory/GitHub scouts, and flow-gap-analyst.
- Prime applies it to all nine Phase-1 scouts + preserves it on the existing retry.
- Host review / quality review / implementation / generic investigation NEVER consume SCOUT_PIN.
- No agents/*.md changes; Claude Code frontmatter tiering intact.
- Contract test inventories named scout dispatches and FAILS when a new Plan/Prime scout call site omits the shared reference.
- test_cursor_scout_routing / test_cursor_agent_frontmatter / test_prime_eval green.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
