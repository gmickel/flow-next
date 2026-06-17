# fn-66-tracker-sync-reserve-linear-done-for.2 Touchpoint re-scoping: completionReview never-terminal / makePr to In Review / land.merged Done-on-merge-evidence

## Description
### Goal
Re-scope the three status-writing touchpoints to the corrected policy: completionReview never terminal, makePr → In Review, land.merged → Done only on merge evidence. Satisfies R2, R3, R4.

### Investigation targets
- **completionReview (the premature-Done site)** — `flow-next-work/phases.md:411-428` (Phase 3g): after `spec set-completion-review-status ... ship` (:412) it fires `tracker-sync (operation: push, event: work.completionReview)` whose prose (:419-420) says "flip the linked issue to Done/verified". Re-scope: post the verdict + R-ID coverage comment and at most ensure `In Review` (open PR) — NEVER terminal. Also the retro-fire path (`:526`) and flow diagram (`:560-561`). Update the perEvent description in `flow-next-tracker-sync/SKILL.md:171` and `flow-next-work/SKILL.md` ("flip Done/verified" → "verdict comment; never Done").
- **makePr → In Review** — `flow-next-make-pr/workflow.md:1669-1693` (dispatch :1680-1681). Currently a non-closing `Ref` link + comment, no status. Add: when an open PR exists for the branch, reconcile the linked issue to `In Review` (R2). Keep the PR-link comment.
- **land.merged → Done** — `flow-next-land/workflow.md:461-475` (LEAF :461, dispatch :472, prose :475 "flips it to the configured terminal state"). Make this the SOLE Done driver, and gate the status write itself on the `MERGED` probe (don't trust the caller). Runs post-merge from a clean base (:422) after spec close (:437).
- **steps.md setStatus guard** — `steps.md:131-139` (push) / `:163-182` (reconcile): before any `setStatus` that would write terminal, assert merge evidence (the policy from fn-66.1).
- **flowctl perEvent** — `flowctl.py:1027` enum `{off,pull,push,reconcile,comment}`; defaults `:1057-1074` (`completionReview` and `land.merged`). Decide + document the default so merge becomes the Done driver and completionReview is non-terminal; add a round-trip test copying `test_qa_tracker_event.py`.
- Lifecycle dispatch grammar must stay `operation: <verb> <id>, event: <key>` verbatim (memory `mirror-regen-exposes-latent-canonical`).

### Notes
Depends on fn-66.1 (the policy/map). This task wires the callers to it. No merge-mechanics change — land still merges; this constrains the status WRITE.
## Acceptance
- [ ] completionReview touchpoint (work phases.md 3g + retro-fire) posts verdict/R-ID-coverage comment and at most ensures `In Review`; never pushes terminal `Done`/`verified` (R4). SKILL prose in tracker-sync + work updated ("flip Done/verified" removed).
- [ ] makePr touchpoint moves the linked issue to `In Review` when an open PR exists for the branch, alongside the PR-link comment (R2).
- [ ] land.merged touchpoint is the sole Done driver and gates the status write on the GitHub `MERGED` probe; no Done without merge evidence (R3).
- [ ] steps.md push/reconcile setStatus guard asserts merge evidence before any terminal write.
- [ ] flowctl perEvent defaults documented/wired so merge drives Done + completionReview is non-terminal; round-trip test added (test_qa_tracker_event.py style); `python3 -m unittest discover -s plugins/flow-next/tests` green.
- [ ] `land.merged` is active by default when the bridge is active (default-on via discovery ceremony OR unconditional-when-active) — decided + implemented here, NOT left `off` (else boards stick at In Review post-merge) (R10).
- [ ] completionReview dispatch is re-scoped from `reconcile` to a `comment`-shaped effect (no status push); verified in flowctl perEvent default + the work caller (R4).
- [ ] make-pr's `In Review` push rides the UNCONDITIONAL PR-link path (active whenever the bridge is active), not gated behind `perEvent.makePr != off` (R2).
- [ ] A manual `/flow-next:tracker-sync` reconcile MAY terminal-write `Done` iff `MERGED` evidence exists (the merge-evidence invariant is per-write, not per-touchpoint) (R10).
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
