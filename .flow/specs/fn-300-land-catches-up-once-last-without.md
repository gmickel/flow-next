# Land catches up once, last, without restarting patience

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 0% [user], 55% [paraphrase], 45% [inferred] -->

Land brings a pull request up to date with its base (a server-side branch update) as the first thing it does whenever the PR is behind, before it knows whether review, threads, CI and patience would let the PR merge. Two costs follow on a busy repository: [paraphrase]

- **Early catch-ups are wasted.** Land catches up, then waits on a review, a thread or the patience window; meanwhile the base moves again and the PR is behind again, so the next tick catches up again. Each catch-up is a new head and a full CI cycle, and only the last one before the merge ever mattered. [paraphrase]
- **Every catch-up restarts patience.** On an unattended merge, land waits a patience window after the last push so review bots can post. A catch-up is a push, so it restarts the window, although it adds no code the PR's author wrote and the bots already had their window on the actual change. [paraphrase]

Land also needs to know when the repository requires up-to-date branches. That requirement can live in a ruleset rather than classic branch protection; a repository whose only strict rule is in a ruleset reads as unprotected through the classic protection read. [paraphrase]

What gets merged does not change: a PR on a repository that requires up-to-date branches is still caught up and tested before merging, as today. [paraphrase]

Target user: maintainers whose PRs wait on land, and anyone running `flow --auto --until=merge` on an active repository. [inferred]

## Architecture & Data Models
<!-- scope: technical -->

Scope: PRs whose base is the repository's trunk. Stack layers whose base is a parent branch keep today's behaviour toward that parent. [inferred]

- **Conflicts first, catch-up last.** Land still reads mergeability first and stops `BLOCKED` on a conflict, naming the branch that needs a rebase. It then evaluates threads, CI, review decision and patience. It catches up only when being behind the base is the only thing between the PR and a merge it is otherwise allowed to make: after patience, before the merge-verdict command, so the verdict command only ever judges a head that will not be replaced. A refused catch-up still stops `BLOCKED`. [paraphrase]
- **The catch-up is pinned to the gated head.** The update passes the head land just gated as the expected head (the forge's update-branch `expected_head_sha`), so a push that lands between the gate read and the update is never merged in silently; a mismatch returns `RESOLVING`. [inferred]
- **After a catch-up, every gate runs again on the next tick** on the new head: CI, threads, the review decision (a repository that dismisses stale approvals on push sends the PR back to `AWAITING_REVIEW`, which is correct) and the verdict command. [inferred]
- **What counts as a catch-up.** A merge commit whose second parent comes from the base and whose committer is the forge's web-flow identity. A person clicking the forge's "Update branch" produces the same commit and counts the same; a base merge the author made locally is an authored push. Land finds them by walking first parents from the gated head, reading each commit's parents and committer from the forge's commit API, until the first commit that is not a catch-up (at most a few reads: the run it needs is two long). A read that fails or returns incomplete data is never taken as an authored commit: land stops `RESOLVING` for that tick, and patience falls back to the head's own push, as today. [inferred]
- **Patience counts from the last authored push.** The patience window counts from the newest push that changed the PR's own diff; catch-up commits on top of it do not restart it. The existing fallbacks (no push date: the earliest check suite, then the committer date) are read from that authored commit, never from the catch-up head. [paraphrase]
- **Red CI on a catch-up-only head is not a fix attempt.** When the only commits since the last green head are catch-ups and CI turns red, the PR's own code did not change: land stops `BLOCKED` naming the base move, instead of spending its one CI repair. [inferred]
- **Two consecutive catch-ups, then a person.** Counting the run of catch-up commits at the head of the PR's history: with two already there and the base moved again, land does not catch up a third time and stops `NEEDS_HUMAN` naming the moving base, so a person decides (a merge queue, a quieter window, or merging by hand). [inferred]
- **Behind, independent of strictness.** Whether the PR is missing base commits comes from the forge's compare of base and head (`behind_by`), never from the merge state: the forge reports a behind state only when the base requires up-to-date branches, so a PR on a repository without strict rules can be behind while its merge state reads clean. Land catches up a behind PR (last) whether or not the base requires it, so no strictness read is needed. A compare that cannot be read is `RESOLVING`. [inferred]
- **Merge queues.** Before any catch-up, land checks whether the base branch requires a merge queue, from the same effective rules for the base branch, independently of how strictness was learned. A queue-required base is not caught up: the queue tests the merge result, and land's existing queued handling is unchanged. When that read fails, land treats the base as having no queue and catches up as today, which costs a CI cycle but merges nothing untested. [inferred]
- **Behind base where the rules allow it:** land still catches up before merging, as today, only now last; it never merges a PR it observed behind its base. On a repository without strict rules or a merge queue, the base can still move between land's last read and the merge, and the repository's rules allow that merge, as they do today; freshness enforced at the merge itself belongs to strict rules or a merge queue, which land honours. [paraphrase]
- **Visible.** The verdict reason says when land deferred a catch-up to the end, when it caught up, and when it stopped on a moving base. A dry run reports the catch-up it would make last. [inferred]
- **Size.** This reorders land's existing steps and re-anchors one timer; it adds no reference file, flowctl verb or state file, and land's instruction text does not grow on net. [paraphrase]

## Examples
<!-- scope: both -->

**Busy base, strict rules.** Today: tick 1 catches up (CI 12 min), tick 2 waits 10 min of patience from that catch-up, the base moves twice meanwhile, tick 3 catches up again, and so on. With this change: tick 1 sees review pending and does not catch up; tick 2 sees review approved, CI green on the authored head and patience elapsed since the author's last push, catches up once against the gated head, and returns while CI runs; tick 3 re-checks every gate on the caught-up head and merges. One CI cycle for the base instead of one per tick. [inferred]

**Stale approvals dismissed on push.** Same as above, but the repository dismisses approvals on any push: tick 3 reads `AWAITING_REVIEW` on the caught-up head and waits for a fresh approval, as the repository asks. [inferred]

**Moving base.** After two catch-ups in a row the base moves again during CI:

```text
LAND_VERDICT=NEEDS_HUMAN pr=812 reason="base moved after two consecutive catch-ups; merge by hand, use a merge queue, or retry in a quieter window"
```

[inferred]

**Strict rule in a ruleset.** A repository has no classic branch protection, and its "Required CI" ruleset enforces strict status checks. Land reads the effective rules for the base branch, knows up-to-date branches are required, and catches up last instead of trying a merge that the forge would refuse. [inferred]

**Patience anchor.** The author's last push was 14:02; land's catch-up pushed at 14:20. At 14:21 the patience window (10 min) has elapsed, measured from 14:02, so the only wait is the CI run on the caught-up head. [inferred]

**Red after catch-up.** CI was green on the author's head; the catch-up merges a base change that breaks the PR's tests. Land stops `BLOCKED` naming the base commits merged in, rather than trying a fix on code the author did not change. [inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

- A catch-up that brings a conflict: `BLOCKED` naming the branch, as today. [paraphrase]
- A push by the PR's author after a catch-up is an authored push: it restarts patience and ends the run of consecutive catch-ups. [inferred]
- A human's current merge authorization still waives patience, unchanged; the catch-up is still last relative to threads, CI and review. [paraphrase]
- No push date for the authored commit: the earliest check suite for that commit, then its committer date; a fallback that reads the catch-up head is wrong. [inferred]
- The rules read needs repository permissions the token may lack; a failed read is treated as up-to-date required, never as permission to merge behind. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** On a trunk-based PR, land reads mergeability first and catches up a behind PR only when every other gate it applies (threads, CI, review decision, patience) would otherwise allow the merge, after patience and before the merge-verdict command; stack layers keep today's behaviour. Errors: conflict or refused catch-up → `BLOCKED` naming the branch, unchanged. [paraphrase]
- **R2:** The patience window counts from the newest push that changed the PR's own diff; catch-up commits do not restart it, and the no-push-date fallbacks read that authored commit. Errors: push evidence unavailable → the existing fallbacks on the authored commit. [paraphrase]
- **R3:** A catch-up is a web-flow merge commit from the base (a person's Update-branch click counts the same), found by walking first parents from the gated head with parents and committer read per commit; with two consecutive catch-ups at the head and the base moved again, land does not catch up a third time and stops `NEEDS_HUMAN` naming the moving base. Errors: a failed or incomplete history read → `RESOLVING` for that tick, never counted as authored. [paraphrase]
- **R4:** Land learns whether a PR is behind from the forge's compare of base and head, independent of whether the base requires up-to-date branches, and catches it up last either way; before counting catch-ups it reads whether the base requires a merge queue, and a queue-required base is not caught up. Errors: compare unreadable → `RESOLVING`; queue requirement unreadable → treated as no queue, catching up as today. [paraphrase]
- **R5:** Land's instruction text gains no new step, reference file, flowctl verb or state file, and does not grow on net. No error surface. [paraphrase]
- **R6:** On a scratch repository with strict rules on (in a ruleset) and off, land defers the catch-up to the last gate, pins it to the gated head, counts catch-ups as R3 defines, never merges a PR it observed behind its base, and never merges a different code head than it gated; with strict rules on, a base that moves after the catch-up is caught by the forge's own freshness check, and with them off the merge proceeds as the repository's rules allow. Observed ticks on this project's own PRs show no more catch-ups per merged PR than before. No error surface beyond the observation. [inferred]
- **R7:** The catch-up passes the gated head as the expected head, and a head that moved meanwhile returns `RESOLVING` without merging. No error surface. [inferred]
- **R8:** Red CI on a head whose only new commits since the last green head are catch-ups stops `BLOCKED` naming the base move, and uses no CI repair. No error surface. [inferred]

## Boundaries
<!-- scope: business -->

- Land still never rebases, force-pushes or merges without current authorization; every other gate is unchanged. [paraphrase]
- No merging behind the base on the agent's judgment that base changes are unrelated; a repository that wants freshness enforced at merge time turns on strict checks or a merge queue, and land honours it. [paraphrase]
- Carrying review verdicts across rebases by patch identity, removed by fn-250, stays removed. [paraphrase]
- No forge other than GitHub in this change; the GitLab parity stub absorbs the equivalent when it is planned. [inferred]

## Early proof point

Task fn-300-land-catches-up-once-last-without.1 validates the core approach (whether the forge's behind state already encodes strictness, and the reordered catch-up on a scratch repository). If the behind state does not encode strictness and the effective-rules read is unavailable to an ordinary token, re-evaluate R4 before relying on it.

## Strategy Alignment

Active tracks served by this plan:
- **Autonomous mode** — unattended landing spends less time on repeated catch-ups and restarted patience, with no change to what merges.

Follows the **Agent first** design principle: no new mechanism, a reorder of existing steps; the catch-up decisions are the agent's, recorded in the verdict reason.

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

The first version of this spec let land merge behind the base when the agent judged the base changes unrelated. The maintainer rejected that on 2026-10-15: it adds an unattended judgment that can break the base branch (a base change that adds a new caller of code the PR changes is easy to miss), it helps only repositories that already allow behind merges, and it does nothing on a repository like this one, whose strict rule makes every catch-up mandatory. Ordering the catch-up last and anchoring patience on the author's push remove most of the waiting without changing what gets merged. [paraphrase]

Planning (2026-10-15) added: the catch-up's place relative to the verdict command, pinning it to the gated head, a definition of a catch-up that needs no state file, patience fallbacks read from the authored commit, red CI on a catch-up-only head, a `NEEDS_HUMAN` stop for a base that will not stop moving (an endless `RESOLVING` loop was the alternative), merge queues, stack scoping, and "no net growth" in place of a line budget the land text already exceeds. [inferred]

The plan route came from a detector that read "stacked PR" in the edge cases as staged delivery; the work is one cohesive task. [inferred]

## Memory findings

No relevant entries in project memory.

## Quick commands

```bash
uv run --with pytest python -m pytest -q plugins/flow-next/tests/test_land_named_pr.py plugins/flow-next/tests/test_land_config.py plugins/flow-next/tests/test_skill_prose_diet.py
./scripts/sync-codex.sh --check
```

## Strategy Conflicts

None found.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
| --- | --- | --- | --- |
| R1 | On a trunk-based PR, land reads mergeability first and catches up a behind PR only when every other gate it applies (threads, CI, review decision, patience) would otherwise allow the merge, after patience and before the merge-verdict command; stack layers keep today's behaviour. Errors: conflict or refused catch-up → `BLOCKED` naming the branch, unchanged. | fn-300-land-catches-up-once-last-without.1 | — |
| R2 | The patience window counts from the newest push that changed the PR's own diff; catch-up commits do not restart it, and the no-push-date fallbacks read that authored commit. Errors: push evidence unavailable → the existing fallbacks on the authored commit. | fn-300-land-catches-up-once-last-without.1 | — |
| R3 | A catch-up is a web-flow merge commit from the base (a person's Update-branch click counts the same), found by walking first parents from the gated head with parents and committer read per commit; with two consecutive catch-ups at the head and the base moved again, land does not catch up a third time and stops `NEEDS_HUMAN` naming the moving base. Errors: a failed or incomplete history read → `RESOLVING` for that tick, never counted as authored. | fn-300-land-catches-up-once-last-without.1 | — |
| R4 | Land learns whether a PR is behind from the forge's compare of base and head, independent of whether the base requires up-to-date branches, and catches it up last either way; before counting catch-ups it reads whether the base requires a merge queue, and a queue-required base is not caught up. Errors: compare unreadable → `RESOLVING`; queue requirement unreadable → treated as no queue, catching up as today. | fn-300-land-catches-up-once-last-without.1 | — |
| R5 | Land's instruction text gains no new step, reference file, flowctl verb or state file, and does not grow on net. No error surface. | fn-300-land-catches-up-once-last-without.1 | — |
| R6 | On a scratch repository with strict rules on (in a ruleset) and off, land defers the catch-up to the last gate, pins it to the gated head, counts catch-ups as R3 defines, never merges a PR it observed behind its base, and never merges a different code head than it gated; with strict rules on, a base that moves after the catch-up is caught by the forge's own freshness check, and with them off the merge proceeds as the repository's rules allow. Observed ticks on this project's own PRs show no more catch-ups per merged PR than before. No error surface beyond the observation. | fn-300-land-catches-up-once-last-without.1 | — |
| R7 | The catch-up passes the gated head as the expected head, and a head that moved meanwhile returns `RESOLVING` without merging. No error surface. | fn-300-land-catches-up-once-last-without.1 | — |
| R8 | Red CI on a head whose only new commits since the last green head are catch-ups stops `BLOCKED` naming the base move, and uses no CI repair. No error surface. | fn-300-land-catches-up-once-last-without.1 | — |

