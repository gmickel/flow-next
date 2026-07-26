---
satisfies: [R11, R12]
---
# fn-139-tracker-sync-determinism-flowctl-owns.7 Skill teardown: prose to transport-shape docs, five judgment surfaces

## Description
Reduce the adapter references and `steps.md` to transport-shape documentation. Remove executable invocations; the skill calls `flowctl tracker <verb>`.

`SKILL.md` names the **five** judgment surfaces and why each cannot be deterministic: MCP rung, discovery ceremony, body-merge conflict adjudication, comment content synthesis, recovery routing from a structured error.

Measurement is mechanical (R11): a test asserts zero executable-invocation matches inside bash fences across an enumerated file set, and that the summed character count is >=150,000 below the baseline recorded in the test.

## Acceptance
- [ ] Zero `gh api` / `glab api` / `curl -sS` / `POST /rest/api` matches in bash fences across the enumerated set
- [ ] Summed char count >=150,000 below the recorded baseline
- [ ] SKILL.md names exactly five judgment surfaces with rationale
- [ ] sync-codex.sh run twice, mirror committed

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
