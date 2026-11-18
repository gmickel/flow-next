# Machine-local tracker token command

## Goal & Context

<!-- Source: 20% user / 50% [paraphrase] / 30% [inferred] -->

MergeFoundry stores a tracker credential per machine and serves it through an argv such as `["/path/to/mergefoundryd", "tracker-token", "linear", "/home/me/.mergefoundry"]`. Today flowctl reads the token command only from the tracked `.flow/config.json` (`tracker.perTracker.tokenCommand`), so using it means committing a machine-specific path to the shared repository. A collaborator without the token variable then gets `token command not found`, a committed command switches off Linear's MCP create route for everyone, and a worktree started from `origin` sees the command only once it is committed. [paraphrase]

The ask (MergeFoundry coordinator, approved by Gordon 2026-11-18): take the token command from an untracked, machine-local source checked before the tracked config. The variable form is enough for MergeFoundry, because its daemon exports environment to every session it starts. [paraphrase]

This settles the parked unknown in fn-328 ("an environment-variable form of the token command next to the committed config value"). fn-328's objection to a per-developer variable was the manual setup step; here a daemon sets it, so nobody does it by hand. [inferred]

## Architecture & Data Models

- The machine-local command lives in one environment variable per tracker that consumes a token command: `FLOW_TRACKER_TOKEN_COMMAND_LINEAR` and `FLOW_TRACKER_TOKEN_COMMAND_JIRA` (Jira Cloud token and Data Center PAT alike). [inferred]
- The configured executor (the single place every credentialed tracker call is built, including 9.13.0's upstream-idea reads) picks the command for the configured `tracker.type`: the variable when set, otherwise the tracked `tracker.perTracker.tokenCommand`. Credential resolution and the run-once cache stay as they are. [inferred]
- Linear's MCP-route check treats the variable like the tracked key. [inferred]

## API Contracts

- `FLOW_TRACKER_TOKEN_COMMAND_LINEAR` / `FLOW_TRACKER_TOKEN_COMMAND_JIRA`: a JSON array of non-empty strings, run as argv without a shell, exactly like `tracker.perTracker.tokenCommand`. [paraphrase]
- Order for a credential: the token variable (`LINEAR_API_KEY`, `JIRA_API_TOKEN`, `JIRA_PAT`) → the machine-local command → the tracked `tokenCommand` → Linear's MCP route. [paraphrase]

## Edge Cases & Constraints

- A machine-local command that fails stops there with the same `auth` error the tracked command gives; flowctl never falls back to the tracked command after it, so a misconfigured machine is visible and only one secret store runs. [inferred]
- An empty variable counts as unset. [inferred]
- Neither the variable's value nor the command's output appears in any error, log, receipt or `.flow/` file. [paraphrase]

## Acceptance Criteria

- **R1:** With `FLOW_TRACKER_TOKEN_COMMAND_<TRACKER>` set for the configured tracker (Linear or Jira) and the token variable unset, every credentialed tracker call takes the credential from that command; the tracked `tokenCommand` is not run. The token variable still wins over both. [paraphrase]
  Errors: a value that is not a JSON array of non-empty strings fails as `auth` naming the variable, without echoing the value; a command that exits non-zero, times out, is not found or prints nothing fails exactly as the tracked command does, and the tracked command is not tried afterwards.
- **R2:** The machine-local command keeps the tracked command's guarantees: argv without a shell, at most one run per process under concurrent requests, a 10-second timeout, and its output is never written anywhere. [paraphrase]
  Errors: no error surface beyond R1.
- **R3:** A Linear tracker with `FLOW_TRACKER_TOKEN_COMMAND_LINEAR` set does not take the MCP create route, as with the tracked key. [inferred]
  Errors: no error surface beyond R1.
- **R4:** The tracker-sync documentation, the config schema's `tokenCommand` description and the tracker-sync skill name the variable and the order. [inferred]
  Errors: no error surface beyond documentation.

## Boundaries

- No machine-local command for GitHub or GitLab: they authenticate through `gh`/`glab` or `GH_TOKEN`/`GITLAB_TOKEN`. [inferred]
- No user-level config file (for example `$XDG_CONFIG_HOME/flow-next/config.json`) in this change; the variable covers the stated need. [inferred]
- No fallback from a failed machine-local command to the tracked one. [inferred]

## Decision Context

- Per-tracker variables rather than one: one daemon environment can serve repositories with different trackers. [inferred]
- The user-level file was offered as an alternative in the ask and is parked: a second source means a second precedence rule, a file format and location to document and test, for no need stated today. [inferred]

## Parked unknowns

- A user-level config file, if a host without a daemon that exports environment needs a machine-local command.
