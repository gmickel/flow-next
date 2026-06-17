# fn-66-tracker-sync-reserve-linear-done-for.1 status-sync policy: merge-evidence gate for Done + In Review rung + fixture matrix + linear-ladder sync

## Description
### Goal
Fix the status policy at its root: reserve terminal `Done`/`verified` for merge-confirmed PRs, add an `In Review` rung for open PRs, and prove it with worked fixtures. Satisfies R1, R6, R7, R8.

### Investigation targets
- `references/status-sync.md:51-54` — the flow→normalized map. **Lines 52-53 are the bug**: `spec done + completion_review_status == ship → verified` and `spec done, no review → done`, both terminal, pushed with NO merge check. Insert: open PR (unmerged) → `in-review`; terminal (`done`/`verified`) ONLY when a merged-PR probe returns `MERGED`. Local completion is necessary, not sufficient.
- **Do NOT disturb** the who-wins ladder / deadlock-first ordering (`status-sync.md:61-130`, collision-before-single-field per memory `who-wins-ladder-must-check-collision-first`). The fix is upstream in the flow→normalized mapping, before who-wins runs.
- `references/linear-ladder.md:105-117` — the DUPLICATE normalized-status map (`completed → done/verified`); edit in lockstep or it drifts.
- Merge-evidence probe (reuse verbatim): `gh pr list --head "$BRANCH_NAME" --state all --json url,state,number,isDraft` → jq `select(.state=="MERGED")` (land `workflow.md:99-104`, pilot `:126-132`). Bare `gh pr view` returns rc 0 for CLOSED/MERGED — always filter `.state` via jq. Use `-F` not `-f` for numeric gh-api fields (memory `gh-api-f-stringifies`).
- Worked fixtures are the oracle (`status-sync.md:352-433`, S-A..S-F). Add **S-G..S-J**: no-PR (all-done, completion-ship) → non-terminal; open-PR → in-review; merged-PR → done; closed-unmerged → non-terminal/NEEDS_HUMAN. Assert the projected state per case.
- New normalized status values must match what flowctl actually emits (memory `skill-prose-must-match-real-flowctl`); `in-review` maps to Linear `state.type: started` / GitHub label per `status-sync.md:200-212`.
- Linear GraphQL `workflowStates { nodes }` (for resolving the In Review state) needs `first:` (memory `linear-graphql-every-nodes-connection`).

### Notes
This task is the POLICY core; the touchpoints (fn-66.2) and pilot (fn-66.3) enforce it. Transport-blind: the merge-evidence gate applies on BOTH Linear and GitHub adapters (R8).
## Acceptance
- [ ] status-sync.md flow→normalized map: terminal `done`/`verified` is gated on a `MERGED` merge-evidence probe for the spec branch; `spec done + completion ship` with no merged PR NEVER maps to terminal (R1).
- [ ] Open (unmerged) PR maps to an `in-review` normalized rung → Linear `In Review` / GitHub equivalent (R-supports R2).
- [ ] Closed-unmerged / missing-branch / ambiguous PR state never maps to terminal — non-terminal + warning / NEEDS_HUMAN (R6).
- [ ] GitHub adapter honors the same merge-evidence gate for its terminal/closed state (R8).
- [ ] linear-ladder.md normalized map updated in lockstep (no drift).
- [ ] Worked fixtures S-G..S-J added (no-PR / open-PR / merged-PR / closed-unmerged) asserting the projected state for each (R7).
- [ ] who-wins / deadlock ordering untouched; merge-evidence is upstream of the ladder.
- [ ] The flow→normalized map is `flowToNormalized(spec, prEvidence)` — takes PR-merge evidence as input, not spec state alone.
- [ ] `references/github.md` terminal/closed mapping requires `MERGED` evidence; `references/adapter-interface.md` notes the transport-blind "terminal outbound write requires merge evidence" invariant.
- [ ] Fixtures S-G..S-J assert EXACT states (not "non-terminal"): no-PR all-done → stays `In Progress` (no advance); open-PR → `In Review`; merged-PR → `Done`; closed-unmerged → `In Progress`/non-terminal + NEEDS_HUMAN.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
