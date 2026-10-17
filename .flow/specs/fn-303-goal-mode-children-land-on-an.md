# Goal mode: children land on an integration branch

## Goal & Context
<!-- scope: business -->

Goal mode as merged lands each child spec on the default branch, one reviewed change at a time, and measures the bar there. Most goals cannot show the default branch a half-finished state: a migration or port where half-moved code cannot ship, a version upgrade where the default branch has to keep building on the old version until the switch, a release bar that only means something as a whole. So by default the children land on an integration branch and the goal reaches the default branch through one final pull request. A goal whose every step is safe to ship on its own (for example, a PRD worked down feature by feature) opts out with one sentence and lands each child on the default branch. Daniel Killenberger raised it while reviewing goal mode. [paraphrase]

Target user: anyone running `flow --goal`. [inferred]

## Architecture & Data Models
<!-- scope: technical -->

- **On by default; opt out in words.** Every goal run uses an integration branch unless the goal spec or the invocation's prompt says children land on the default branch directly, for example under Boundaries: "land each child on main". The run reads that sentence like any other part of the goal. No flag, field or config key. [paraphrase]
- **The goal spec's `branch_name` is the integration branch.** Every spec already carries one. The run creates that branch from the default branch's remote head once, pushes it, and records it in the goal log. [paraphrase]
- **Children build on it.** Each child's work branches from the integration branch and its pull request targets it, so each child stays one reviewed change against the integration branch. Work gains a `--base=<ref>` argument that sets the base its branch fence already reads (`DEFAULT_BASE`); the goal run passes it, and make-pr gets the matching `--base`. Land merges into whatever base the pull request has, unchanged. [inferred]
- **Measure on it.** Goal mode's measure step uses the integration branch's remote head instead of the default branch's. [paraphrase]
- **Keep it current.** Before each measurement the run merges the default branch's remote head into the integration branch and pushes the merge (never a rebase or force-push). A conflict it cannot resolve within the goal's Boundaries is an open question for the person. [paraphrase]
- **The final pull request.** At `GOAL_MET` the run opens one pull request from the integration branch to the default branch and gives it a full implementation review of the whole diff. Its body is built from the goal log. It lands only with merge consent on the current invocation, as any other pull request does. Whether it opens through make-pr for the goal spec or directly is the implementer's call, decided by what make-pr already supports for a spec with no tasks. [inferred]
- **Unchecked children are not green.** When pull requests into the default branch report checks and a child's pull request into the integration branch reports none, the run stops `NEEDS_HUMAN`, naming the likely cause: the repository's CI triggers only on pull requests into the default branch. [paraphrase]
- **Docs.** The goal-mode page gains an "Integration branch" section: when to use it, the sentence to put in the goal spec, and that the repository's CI must run on pull requests into that branch (for GitHub Actions, the branch or a pattern such as `goal/**` under `pull_request: branches`, and in branch protection if the checks should block merges). [paraphrase]
- **Parity.** Skill and reference prose plus work's one argument, through the existing mirrors; no flowctl change. [inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

- With the opt-out sentence in the goal spec or the prompt, children land on the default branch and the run measures there, as goal mode does before this spec; no integration branch and no final pull request. [paraphrase]
- The integration branch already exists (a resumed goal): the run uses it and does not recreate it. It exists but was not created by this goal, per the goal log: `NEEDS_HUMAN`. [inferred]
- The default branch cannot be merged in cleanly and the conflict touches a Boundary or a product choice: open question; the run keeps working on gaps that do not depend on it only when the integration branch still builds. [inferred]
- The final pull request is closed without merge: `NEEDS_HUMAN`; the run never reopens or replaces it. [inferred]
- `--until=merge` lands children into the integration branch and, only with that same invocation's consent, the final pull request. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** By default the run creates the integration branch from the goal spec's `branch_name` (once), builds every child from it, opens every child's pull request against it, and measures on its remote head. A goal spec or prompt that says children land on the default branch gets the direct behaviour instead: no integration branch, children land on the default branch, measurement on its remote head. Errors: an existing branch the goal log does not record as the goal's → `NEEDS_HUMAN`.
- **R2:** Work accepts `--base=<ref>`, which sets the base its branch fence uses; without it the base resolves as today. Errors: an unknown or unfetchable ref → `BLOCKED` before any branch is created.
- **R3:** Before each measurement on an integration branch, the run merges the default branch's remote head into it and pushes the merge, never rebasing or force-pushing. Errors: an unresolvable conflict → open question in the goal log.
- **R4:** At `GOAL_MET` on an integration branch, the run opens one pull request from it to the default branch with a body built from the goal log, runs a full implementation review on it, and lands it only under the invocation's merge consent. Errors: the pull request is closed unmerged → `NEEDS_HUMAN`.
- **R5:** When pull requests into the default branch report checks and a child's pull request into the integration branch reports none, the run stops `NEEDS_HUMAN` naming the CI trigger as the likely cause. No error surface beyond that stop.
- **R6:** The goal-mode docs page has an "Integration branch" section covering the default, the opt-out sentence and when to use it, and the CI and branch-protection configuration the default needs; the page's run steps, `--until=merge` text and goal-log example describe the integration branch as the default; the plugin's skills reference names work's `--base`. No error surface.

## Boundaries
<!-- scope: business -->

- No flowctl verb, spec field or config key. [paraphrase]
- No change to the opted-out behaviour: it stays goal mode as merged in #561. [paraphrase]
- No rebase, force-push or history rewrite of the integration branch or any child branch. [paraphrase]
- No CI configuration changes in the user's repository; the run reports, the person configures. [inferred]

## Decision Context
<!-- scope: both -->

Goal mode's main uses (migrations, ports, version upgrades, release bars) have intermediate states that must not reach the default branch, so the integration branch is the default. It costs drift (handled by merging the default branch in before each measurement), one large final review, and CI that must run on pull requests into the integration branch (R5 catches a repository where it does not). Landing each child on the default branch keeps changes small and checked by the default branch's own CI; a goal that wants that opts out in one sentence. A question at the start of a goal run was rejected because goal runs are unattended; the person states the choice in the goal spec or the prompt instead. The goal spec's `branch_name` serves as the integration branch so no new field is needed, and the final pull request answers #559's open question of whether a goal gets a pull request of its own: by default it does. [paraphrase]

Credit: suggested by @DanielKillenberger while reviewing goal mode (#559). Delivery: before 9.0.0, so goal mode ships with it. [paraphrase]

## Strategy Alignment

Serves the autonomy track; follows Agent first (the opt-out is one sentence in the goal spec or prompt, no new field or flag beyond work's base argument, which names the unattended failure it prevents: children built from the wrong base while their pull requests target the integration branch) and Consent comes from a person (the person can opt out in the goal spec or prompt; the final merge still needs merge consent on the invocation). [inferred]

## Strategy Conflicts

None found. [inferred]
