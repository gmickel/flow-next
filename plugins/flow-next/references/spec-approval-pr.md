# Spec approval by pull request

Read when flowctl reports `spec.approval is pr` for a spec that is not approved yet. In this
project a spec is ready for implementation only after its own pull request merges with at least
one approving review. The forge decides who may approve (branch protection, an agent identity
separate from the people who approve); flowctl reads and records the approval and enforces nothing
else.

When the spec is written (after capture, plan or refine), open the spec as a pull request instead
of marking it ready:

- Branch `spec/<spec-id>` from the default branch. flowctl finds the spec PR by that head branch,
  so use exactly that name.
- Commit the spec's files under `.flow/` (the spec, its sidecar, and its tasks when planned) on
  that branch, push it, and open the PR against the default branch with the spec title and a
  short summary of its acceptance criteria.
- Stop there. Do not run `flowctl spec ready`, start a task, or begin implementation; report the
  PR link as the step that is the person's.

After the PR merges with an approving review, the next `flow --auto` selection or `flowctl start`
finds it, records the approvers, the merge identity and the times on the spec, and marks it ready.
Nobody needs to mark it ready by hand.

If flowctl reports the PR closed without merge, merged without an approving review, or the forge
unreachable, the spec stays not ready. Report the reason; never work around it.
