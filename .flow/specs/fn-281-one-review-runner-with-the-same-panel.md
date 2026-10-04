# One review runner with the same panel on every backend

## Goal & Context

Every review backend should work the same. [paraphrase] Today it does not: the first round of an implementation review runs a risk-sized panel (one reviewer for a small, safe diff, three otherwise) only on the Codex path; host always runs three, and the claude, copilot and cursor backends always run one. [paraphrase] The split came from fn-215's R15, which scoped the three-reviewer fan-out to codex and host at capture time without a maintainer decision. [paraphrase]

8.0.0 keeps the deterministic flowctl review path and `review.backend` (agentic dispatch, fn-279, is parked) and fixes the inconsistency by collapsing the per-backend review dispatch into one generic runner: the same rule, the same steps and the same receipt for every CLI reviewer, whichever harness flow-next runs in, with host review applying the identical rule through its own subagents. [paraphrase] Two low-risk review improvements from fn-279 ride along on the existing path: the single-task route checks the project's standing criteria, and the stall check reviews a new fix before it gives up. [paraphrase]

This is the second 8.0.0 spec; it builds after RepoPrompt is removed (fn-280), so the runner covers five reviewer paths that all work the same way. It supersedes fn-196, which proposed the generic runner and was deferred. [paraphrase]

<!-- Source: 50% user / 40% [paraphrase] / 10% [inferred] -->

## Architecture & Data Models

- **One rule, two transports.** CLI reviewers (codex, claude, copilot, cursor) run through one flowctl runner whichever harness flow-next runs in, so flow-next in Codex with the claude backend and flow-next in Claude Code with the codex backend take the same steps. Host review cannot go through flowctl because its reviewers are the harness's own subagents; it applies the identical rule in its workflow and records through the same flowctl commands, so its receipt has the same shape. [paraphrase]
- **The risk call stays with the agent.** The agent judges whether the diff is small, in one area and free of persisted or shared state, concurrency, security and data layout, and tells the runner one or three reviewers; flowctl owns the mechanics (concurrency, merge, receipt, round count). [paraphrase]
- **Where the rule lives.** The panel rule is stated once in the shared review rules and referenced by every backend's workflow, so it cannot drift per backend again. [paraphrase]
- **The substrate is untouched.** Unchanged-artifact refusal, round counting and ratchet, attempt provenance, failure classification and merge-gate head binding behave exactly as today. [paraphrase]
- **Receipts keep their format**, so every reader of review receipts keeps working. [paraphrase]
- **Standing criteria on the default route.** The single-task inline path hands the repository's standing criteria (`.flow/criteria.md`) to the reviewer it already runs; no extra review is added. [paraphrase]

## API Contracts

- The runner takes the reviewer count (one or three) from the agent; three reviewers use the existing three axis lenses (correctness, contracts, integration); one reviewer uses the correctness lens. [paraphrase]
- The merged first round counts as one round against the round cap, as it does today on codex and host. [paraphrase]
- `review.backend`, per-spec and per-task review selection, and the `--review` flag keep their current meaning. [paraphrase]

## Edge Cases & Constraints

- A host that cannot dispatch three reviewers in one message runs them back to back and says so. [paraphrase]
- A reviewer CLI that rejects three simultaneous calls (subscription limits on copilot or cursor) runs its three reviewers back to back and says so; a quick concurrency probe of copilot and cursor comes before the build. [paraphrase]
- Claude reviewers in a three-reviewer round must receive the diff the same way a single claude review does today; today's fan-out never passes it, which is likely why claude was left out. [paraphrase]
- Host review reads the model-routing block from whichever instruction file holds it (CLAUDE.md on Claude Code and Droid, AGENTS.md elsewhere); today it always names AGENTS.md. [paraphrase]
- Cross-family reviewing stays reachable and the family rule stays documented. [paraphrase]
- Plan review and completion review keep one reviewer on every backend. [paraphrase]

## Acceptance Criteria

- **R1:** The first round of an implementation review runs one or three reviewers by the same risk rule on every reviewer path (codex, claude, copilot, cursor, host), on every harness, and the re-review after fixes is one reviewer on every path. Errors: a reviewer that fails does not vote; all reviewers failing → the review reports the failure and records no verdict; a host or CLI that cannot run three at once runs them back to back and says so. [paraphrase]
- **R2:** The CLI reviewer paths share one runner with no per-backend fan-out gating (no codex-only commands, registry flag, primary-must-be-codex check or hard-coded codex receipt mode), and the flowctl review code shrinks rather than grows. Errors: no error surface beyond today's backend errors. [paraphrase]
- **R3:** Any harness can use any CLI reviewer through the runner (for example flow-next in Codex with the claude backend), and every reviewer in a three-reviewer round reviews the same diff, including claude. Errors: a reviewer CLI that is not installed → today's named error and the review fails closed, never a substitute reviewer. [paraphrase]
- **R4:** For each reviewer path (codex, claude, copilot, cursor, host), one draw of a small bug produces a one-reviewer round and one draw of a larger change produces a three-reviewer round, and both reach a verdict. Errors: a path that picks the wrong panel size or cannot complete the round blocks the change. [paraphrase]
- **R5:** The substrate behaves identically (unchanged-artifact refusal, round counting and ratchet, attempt provenance, failure classification, merge-gate head binding), proven by the existing tests without weakening them, and receipts keep their current format. Errors: no error surface beyond today's. [paraphrase]
- **R6:** On the single-task inline route, the reviewer that already runs also judges the repository's standing criteria, and a violated criterion is a finding like any other; no additional review dispatch is added. Errors: no standing-criteria file → the review runs as before with no note. [paraphrase]
- **R7:** The stall check reviews a new fix before it escalates: it stops only after the reviewer marks the same finding `not-fixed` in three consecutive rounds, and never refuses a round whose committed fix has not yet been reviewed. Errors: no error surface beyond the existing round cap. [paraphrase]
- **R8:** Parity fixes: host review reads the routing block from the instruction file that holds it on each harness; no doc claims a panel rule the code does not apply; the fix loop's re-review list includes every backend. Errors: no error surface. [paraphrase]
- **R9:** The 8.0.0 changelog states that `review.backend` stays, reversing 7.1.0's deprecation note, and downstream notes that announced its removal are corrected at release. Errors: no error surface. [paraphrase]
- **R10:** Measured with the fn-271 harness against 7.1.2 on cases 2 and 4, attended and `--auto`, at least 3 draws each: no hidden check that passes on every 7.1.2 draw fails, and wall-clock, cost and judge score are no worse; R6 measured on a single-task case carrying a standing criterion. Errors: a regression blocks the change until explained or fixed. [paraphrase]

## Boundaries

- No agentic review dispatch; fn-279 stays parked. [paraphrase]
- `review.backend` is not retired and needs no migration. [paraphrase]
- No author override for unattended plan and completion review (fn-279's R5). [paraphrase]
- Plan and completion review panels are not changed. [paraphrase]
- No change to the review prompt templates or axis lenses. [paraphrase]

## Decision Context

- **Maintainer, 2026-10-04:** "each backend should work the same"; 8.0.0 keeps everything the same except RepoPrompt removal, the same review on every backend through one generic runner, and the cheap wins that are not dangerous. [paraphrase]
- Agentic dispatch (fn-279) was parked because moving the CLI handling flowctl encodes (stdin hangs, resume flags, model pinning, trust prompts, Windows sandboxing) into prose risks being slower and less reliable across six harnesses, and it breaks a lot; the uniform panel does not need it. [paraphrase]
- Of fn-279's cheap wins, standing criteria on the single-task route and the stall-check fix are low risk; the unattended author override for plan and completion review changes autonomy behaviour and is left out. [paraphrase]
- Keeping the receipt format means existing readers, including MergeFoundry, keep working. [paraphrase]

## Strategy Alignment

- Serves "Cross-platform parity": the same review on every harness and backend. [strategy:Cross-platform parity]
- Keeps the "Autonomous mode" invariant "multi-model review at every handover" with convergence-aware, bounded rounds enforced by flowctl. [strategy:Autonomous mode]

## Strategy Conflicts

None.
