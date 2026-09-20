# Worker never returns with its own commands still running

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 20% [paraphrase], 80% [inferred] -->

A worker returned "done" three times on one task while its own test suite was still running. It had started an eleven-minute test run in the background and ended its turn. The conductor received a completion notice with the task still in progress and the suite still executing, so the result it was asked to accept did not exist yet.

The work skill tells the conductor to diagnose a return that is not done. It does not tell the worker never to end a turn while a command it started is still running, and it does not tell the conductor to look for live child processes before accepting a return. Once one instruction to that effect was added to each dispatch in the affected run, the next four workers behaved. On the last of them the gate exceeded the host's foreground time limit and was moved to the background by the host; the worker blocked on it and read its exit code before returning.

A related slip from the same run: a worker used `git stash` to look at another tree state where a temporary worktree was the right tool.

## Edge Cases & Constraints
<!-- scope: technical -->

- Some hosts move a long foreground command to the background after a time limit. The worker still owns that command and must wait for it. [inferred]
- How a conductor sees a worker's live children differs by host: a background task list on some, the process table on others. The rule is stated as behavior, not as one host's command. [inferred]
- The rules apply on both scheduling routes, rolling and wave, since both accept worker returns. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The worker instructions state that a worker does not return while any command it started is still running: it runs its gate in the foreground, or blocks on the command and reads its exit code, before returning. Errors: when the host moves the command to the background, the worker waits on it and reports the exit code it read; when the worker cannot wait out the command inside its runtime cap, it returns partial under the existing contract and names the command still running. [inferred]
- **R2:** Before accepting a worker return, the conductor checks the task's status and whether the worker left commands running. A return with the task still in progress and a live command is handled by waiting for that command and resuming the same worker, and it does not count as a failed attempt. Errors: a task still in progress with nothing running follows the existing not-done diagnosis; a command that never finishes is bounded by the existing runtime cap. [inferred]
- **R3:** The worker instructions name a temporary worktree as the tool for inspecting another tree state and rule out `git stash`. Errors: no error surface beyond the existing workspace-teardown rules. [inferred]
- **R4:** Each rule is one or two sentences, the conduct checklists for the touched skills cover them, and the generated mirrors are regenerated. Errors: no error surface beyond R1. [inferred]

## Boundaries
<!-- scope: business -->

- Prose rules on the worker and the conductor only. No process supervisor, no new flowctl command, no change to task state. [paraphrase]
- No change to the runtime cap, the strike rules, or scheduling. [inferred]
- The land redesign is a separate spec. [inferred]

## Decision Context
<!-- scope: both — conditionally substructured -->

- The fix is prose on both sides because the defect is a missing sentence, and one added sentence per dispatch already corrected the behavior in four consecutive runs. [inferred]
- The conductor check exists as well as the worker rule because a return is the only moment the conductor can catch the case cheaply: task status and a live command are facts on hand, and no judgment about the worker's intent is needed. [inferred]
- Rejected: a classifier that judges whether a worker is deferring a required step. On the observed returns, task status and the live command decided every case. [inferred]

## Strategy Alignment

- Design principle "Remember the bitter lesson": the bar is stated in one general sentence before any mechanism is considered, and no mechanism is added.
- Design principle "The owner holds the license": the worker owns the commands it starts through to their exit code.
