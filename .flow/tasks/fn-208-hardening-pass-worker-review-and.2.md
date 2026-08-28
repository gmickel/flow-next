---
satisfies: [R2, R3, R4, R5]
---
# fn-208-hardening-pass-worker-review-and.2 Worker gate integrity, review additions, scattered one-liners

## Description
The remaining ~28 prose edits (R2, R3, R4) plus distribution and gates (R5). Depends on task 1 (both touch land's workflow and the mirror).

**Size:** M
**Files:** `plugins/flow-next/agents/worker.md`, `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/skills/flow-next-work/references/wave-join.md`, `plugins/flow-next/agents/quality-auditor.md`, `plugins/flow-next/scripts/flowctl.py` (SMELL_BASELINE_BLOCK only), `plugins/flow-next/skills/flow-next-pilot/**`, `plugins/flow-next/skills/flow-next-land/workflow.md`, `plugins/flow-next/skills/flow-next-interview/**`, `plugins/flow-next/skills/flow-next-plan/steps.md`, `plugins/flow-next/skills/flow-next-plan/examples.md`, `plugins/flow-next/skills/flow-next-audit/phases.md`, `CHANGELOG.md`, `plugins/flow-next/codex/**` (regenerated), one `.flow/memory/` entry
**Touches:** [plugins/flow-next/agents/worker.md, plugins/flow-next/skills/flow-next-work/**, plugins/flow-next/agents/quality-auditor.md, plugins/flow-next/scripts/flowctl.py, plugins/flow-next/skills/flow-next-pilot/**, plugins/flow-next/skills/flow-next-land/workflow.md, plugins/flow-next/skills/flow-next-interview/**, plugins/flow-next/skills/flow-next-plan/**, plugins/flow-next/skills/flow-next-audit/**, CHANGELOG.md, plugins/flow-next/codex/**, .flow/memory/**]

### Approach
Verify every target section fresh. Each rule is one to four lines; each must name the failure class it closes (G1) and keep its full force (a hedged rule is a review finding).

**worker.md (R2), Phase 2 Rules unless noted:**
1. Never edit a test, gate, or baseline to make it pass; a wrong gate is `BLOCKED: TOOLING_FAILURE`.
2. Never weaken an existing assertion to match a wrong implementation (place beside the test-mass discipline: that rule bounds volume, this bounds strength).
3. Phase 5 Verify: INCONCLUSIVE (errored/timed-out/wrong-surface observation) is a third state, never a pass - recorded verbatim in evidence, never as green.
4. Phase 5, beside suite-output capture: a gate that passed suspiciously fast or collected zero cases is not green - check the observation before writing a receipt (protects green-receipt reuse).
5. Rename edits: spot-check every rename against strings, prose, mirrors, and back-references (the repo's highest-frequency banked failure class).
6. Debugging: a refuted hypothesis ships as a revert - belt-and-suspenders that might help does not ship; the smallest evidence-justified change does.
7. For tasks adding or changing a CLI verb, lifecycle step, or loop iteration, interrogate: runs twice? crashed at any point? converges? An it-depends-on-leftover-state answer means a reconciliation step is missing (interrogate the design - never add unrequested machinery).
8. TOOLING_FAILURE category: a broken gate is fixed in its own change, never silently worked around inside the task diff.
9. Phase 3 Commit, bug-shaped tasks: a failing-repro commit before the fix is allowed and preferred, never required.
10. Beside the AC-error-case rule: confirm a new test fails for the intended reason before fixing.
11. Replacing an API/verb/key: deletion of the replaced path is inside the task, not a follow-up.
12. Phase 1.5 grep: sweep the defect's pattern, not just the instance - bounded to the surface the ACs cover.
13. Typed escalation: never return BLOCKED from a broken tree - commit a coherent partial or revert to base, and state which.
Plus the comment-as-alibi block (R4): a comment justifying a workaround is a finding - fix the code; a constraint stated in a comment (do-not-remove, ordering-matters) wants the cheapest encoding (assert, test, lint) and then deletion; keep-list: license headers, external-constraint notes, lint suppressions with reasons, public API contracts, issue links.

**phases.md / wave-join.md (R2+R4):**
- 3c dispatch template: add `FORBIDDEN: <paths outside this task's declared Touches>; no force-push; no rebase of the target` and `TIMEBOX: <cap> - on expiry write the handover with partial findings and return, never run on`.
- 3d: progress is side effects only (commits in the workspace, a moved task status, handover files on disk); a lane past its TIMEBOX with none is stuck - diagnose in its workspace, stand down, count against the existing 2-strike cap. (Known risk: a slow-but-healthy lane can be stood down; the cap bounds the cost.)
- 3a report: one `Selection rule:` line naming why this subset of the frontier, printed before claiming.
- 3d continuation worker: the inherited trail is authoritative for what was decided and written - never redo it; its pass/fail claims are unproven - re-verify on the real artifact before done.
- Between 3f and 3g: a pause path - only at a wave boundary, only on an explicit pause or imminent-compaction signal (an autonomous keep-going never triggers it); wip: commit with a broken-tree note if needed; write the workspace/handover map to /tmp/<spec-id>-resume.md because in-context state does not survive summarization.
- wave-join cleanup: tear down a workspace only when the task's commits are reachable from the target HEAD and the tree is clean; uncommitted work pauses cleanup and is reported, never deleted.
- Phase 5 summary: an all-done spec with no PR counts as zero shipped; the Next: line is the remaining work.
- Conductor side of gate integrity: a caught gate manipulation strengthens the gate in its own change, never just reverts the edit.

**quality-auditor.md + SMELL_BASELINE_BLOCK (R3):**
- Standards axis: if a finding's fix is a comment or a convention someone must remember, ask for the structural constraint (type, lint, runtime check) instead.
- Correctness/architecture: public re-exports of wire/storage/transport types are leakage - parse external data into domain types behind the boundary.
- A change that adds a new API while keeping the old alive with no external consumers: migrate callers and delete in the same wave (the settled-plan rule already excuses recorded phased migrations).
- Smell baseline: shallow module, ONLY with its sign - learning the interface does not save the caller from learning the implementation.
- Standards, mechanical: a file crossing the 1000-line threshold in this diff is a Should-Fix finding (crossing only - never for files already past it; numstat is already in hand).
- Standards naming widened to naming-and-traceability: can a new reader answer where X comes from and what can change X in under 30 seconds?
- SMELL_BASELINE_BLOCK (flowctl.py ~:8981): add the pass-through/middle-man smell (forwards the same arguments to another method of the same shape - a layer hiding nothing). This constant IS pinned (test_prompt_text_pinned.py ~:103) - update the hash in the same commit with the rationale: baseline gains the one smell the auditor already carries but impl-review is blind to.

**Scattered (R4):**
- pilot + land: probe an idle agent read-only (a resume restarts it); re-read the skill file at tick start so a long loop never runs a stale copy.
- interview + plan question discipline: an empirically answerable fork (behavior, timing, output) gets a throwaway probe, not a user question - the ask is the slow path.
- Multi-opinion sites (plan-review/impl-review disagreement handling): wildly divergent independent opinions mean the framing was underspecified - reframe and re-run; never average, never quietly pick-best.
- Review vocabulary (unpinned surfaces): the evidence scale claimed / cited / walked / executed / reproduced; a safety claim that cannot reach executed is stated as such.
- audit phases.md intake filters: a mechanizable lesson routes to a gate proposal, not a memory entry; accept only lessons that route to something actually used in the transcript; a rule that existed but did not fire gets a retrieval (description/placement) fix, not a rewrite.
- plan examples.md/steps.md task-shape guidance: refactor-shaped tasks name an equivalence harness (a script diffing old-vs-new outputs, or a recorded baseline replayed against the new code) as the behavior pin.
- One memory entry (knowledge/best-practices): failures-after-restart suspect persistent state before code - config files, caches, locks, serialized state; if clearing state restores behavior, state validation is the fix. (This repo is unusually disk-stateful.)

**Distribution (R5):** sync-codex twice, mirror committed; conduct checklists for land, work, interview, plan, audit verified against the diff; CHANGELOG entry under a fresh `## Unreleased` (user-outcome first, no em dashes); full gate.

### Investigation targets
**Required:**
- `plugins/flow-next/agents/worker.md` - full read (Rules, Phase 2/3/5, escalation block)
- `plugins/flow-next/skills/flow-next-work/phases.md` + `references/wave-join.md` - 3a/3c/3d/3f-3g, Phase 5
- `plugins/flow-next/agents/quality-auditor.md` - both axes + smell baseline + severity ceiling
- `plugins/flow-next/tests/test_prompt_text_pinned.py` - confirm which targets are pinned TODAY (only SMELL_BASELINE_BLOCK among these expected)

**Optional:**
- `agent_docs/conduct/` checklists for the five touched skills
- `.flow/memory/bug/build-errors/` rename-drift entries (the failure classes several rules encode)

### Key context
- G1 binds every line; a restatement of an existing rule is a review finding.
- Autonomy edits are conservative: refund/hold budgets, explicit-signal binding only.
- Full gate before handoff: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`.

### Acceptance
- [ ] All worker rules and the comment-as-alibi block present; each names its failure class; none restates an existing rule
- [ ] Dispatch template carries FORBIDDEN + TIMEBOX; silent-lane stand-down bound to the existing 2-strike cap; pause path binds to explicit signals only
- [ ] Seven review additions present on unpinned surfaces; SMELL_BASELINE_BLOCK pin updated in the same commit with rationale; standards ceiling and introduced-only discipline unchanged
- [ ] Scattered one-liners at their named surfaces; memory entry written via flowctl
- [ ] sync-codex twice green, conduct checklists verified, CHANGELOG under ## Unreleased, no version bump, full gate green

## Acceptance
- [ ] All worker rules and the comment-as-alibi block present; each names its failure class; none restates an existing rule
- [ ] Dispatch template carries FORBIDDEN + TIMEBOX; silent-lane stand-down bound to the existing 2-strike cap; pause path binds to explicit signals only
- [ ] Seven review additions present on unpinned surfaces; SMELL_BASELINE_BLOCK pin updated in the same commit with rationale; standards ceiling and introduced-only discipline unchanged
- [ ] Scattered one-liners at their named surfaces; memory entry written via flowctl
- [ ] sync-codex twice green, conduct checklists verified, CHANGELOG under ## Unreleased, no version bump, full gate green

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
