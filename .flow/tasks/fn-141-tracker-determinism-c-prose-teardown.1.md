---
satisfies: [R1, R2]
---
# fn-141-tracker-determinism-c-prose-teardown.1 Prose reduction to transport-shape docs; five judgment surfaces

## Description
Reduce the adapter references and `steps.md` to transport-shape documentation. The skill calls `flowctl tracker <verb>`; it no longer contains invocations to execute.

`SKILL.md` names **exactly five** judgment surfaces with rationale: MCP rung, discovery ceremony, body-merge conflict adjudication, comment content synthesis, and recovery routing from a structured error. The earlier draft claimed four while its own table listed recovery as agentic.

Measurement is mechanical, not by eye: a test asserts zero executable-invocation matches (`gh api`, `glab api`, `curl -sS`, `POST /rest/api`) inside bash fences across an enumerated file set, and that the summed character count is >=150,000 below the baseline recorded in the test.

## Acceptance
- [ ] Zero executable-invocation matches in bash fences across the enumerated set
- [ ] Summed char count >=150,000 below the recorded baseline
- [ ] SKILL.md names exactly five surfaces with rationale for each
- [ ] Body-merge adjudication explicitly retained as agentic

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
