---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-328-bitbucket-and-jira-field-report-follow.1 Implement Bitbucket and Jira field-report follow-ups (#602, #611)

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Implemented all seven field-report follow-ups (#602, #611):

- R1: `tracker.perTracker.tokenCommand` (argv, no shell) supplies the Linear key, Jira API token or Jira PAT when the env var is unset; once per process, 10 s timeout, output never logged; failures surface as AUTH/resolve with the cause. Schema, drift allowlist and tracker-sync docs updated; a Linear tracker with a token command is no longer on the MCP rung.
- R2: land's shared workflow stops BLOCKED without a commit when the only green fix removes the PR's purpose.
- R3: briefing links use the hosting forge's path (GitHub blob, GitLab -/blob for nested groups, Bitbucket src); an origin no forge claims gets plain paths.
- R4: land's Bitbucket and GitLab references name `.selected.pr.open.readiness`.
- R5: Bitbucket and GitLab gh stand-ins answer exactly the requested --json keys, add isDraft and body (GitLab also headRefOid), and refuse unknown keys; the Bitbucket create guard and the preflight parent read now request the keys they use.
- R6/R7: make-pr's briefing follows the head over a task summary; repository-required trailer lines may follow the rendered body.

Live check: Bitbucket stand-in against flownextnew/flownext returned exactly the requested keys; flowctl tracker resolve with a failing token command reported "token command exited 3" without its output.

stage: impl-review - ran (NEEDS_WORK: unclaimed origins got GitHub links; fixed; re-review SHIP) (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: b39a51fabb612062bbc00a68703d2e4e3c47d0cf, 4df24ec2f1dbc7731ec290f0884efb422c915749, 6dcd72d5a5b43490c6cab698276a06642eca5d04, b0608594bf1a9100902853fe378205be37955e6d, d6715887de93751a5be58e051b957b4c81053084, e981cf3ca08be4c09b857d16368f6f2ee6eb2a99, 28ce2e49e099bbb3d19c356c49fcb576a90dcc3e, 1a61a8b9858d5eb59ee515b5b48658340d4cc396, 6fbe5a0bb733bca356d4e43fb928eed87b6c3997, d97f96851422766c0565fc217d40510ac7a28aef, bc3df7f5619272000c62ec70d0b165d72cfdde4c, ce33d49bbab7fff3f5e718f8d585b00ed696db62, a84707cad163fefea8335936eb25dbb09b732d1c
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check .
- PRs: