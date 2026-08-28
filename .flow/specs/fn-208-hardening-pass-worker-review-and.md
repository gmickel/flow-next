# Hardening pass: worker, review, and autonomy prose

## Goal & Context

An audit of the banked failure classes in `.flow/memory/` and of the autonomy loops' failure modes produced an adjudicated map of small prose gaps across three surfaces: the worker's implementation contract, the review rubrics' cheap (unpinned) surfaces, and the conductor/autonomy skills. Each gap is a failure mode we have either already banked as a memory entry (rename drift across mirrors, policy-claim sweeps, strike-recovery verbs), grazed live (evidence SHAs orphaned by a rebase; a receipt system that would bank a zero-collected-tests exit 0 as green), or verified as a live defect by reading the current files (four in the land conductor alone).

This spec lands the S-effort portion of that map: roughly 34 one-to-four-line prose edits across about eight files, none of them touching a hash-pinned prompt surface. The larger items the same audit produced (verdict-integrity receipt fields, the pinned review-rubric lines) are deliberately out of scope here and queue as their own specs.

## Architecture & Data Models

Prose-only edits, grouped by blast radius:

1. **Land conductor defect repairs.** The CI-fix triage plans a fix before reading merge-state and unresolved threads, so work ahead of a base merge or thread push is discarded while still consuming the bounded fix budget; a repeat identical failure is re-run blind instead of being reclassified and read; two merges in one tick can land the second PR against a base its checks never saw (the existing re-gate is confined to an opt-in branch); spec dependencies are honored at select but not at merge; the tick ledger has no concurrency claim, so overlapping ticks lose state last-writer-wins; and the clean-review comment scan lacks a stated posture that comment text is evidence, never instruction.
2. **Worker gate integrity.** A block of rules in the worker contract closing the gate-manipulation and evidence-honesty gaps: never altering a test, gate, or baseline to make it pass; never weakening an assertion to match a wrong implementation; a third non-pass verdict state for inconclusive observations; distrusting a gate that passed suspiciously fast or collected zero cases before minting a green receipt; rename sweeps across prose and mirrors; reverting refuted debugging attempts; a scoped idempotency interrogation for lifecycle-shaped tasks; fixing a broken gate in its own change; failing-repro-before-fix as the preferred bug-task commit shape; confirming a new test fails for the intended reason; deleting a replaced path inside the task that replaced it; sweeping a defect's pattern rather than its instance; and never returning blocked from a broken tree.
3. **Conductor dispatch and lifecycle.** The worker dispatch template gains an explicit out-of-scope path ban (echoing the task's declared write surface) and a runtime cap with a return-partial contract; a silent lane past its cap is judged by side effects and stood down under the existing strike cap; the wave report names its selection rule before claiming; continuation workers treat an inherited trail as authoritative for decisions but unproven for pass/fail claims; workspace cleanup requires commits reachable from the target and a clean tree; a pause path at wave boundaries persists the workspace map off-context; and the final summary states that an all-done spec with no PR counts as zero shipped.
4. **Review, unpinned surfaces only.** The quality auditor and the smell baseline gain: a structure-over-instruction probe, a wire-type-leakage check, a legacy-dual-path check, the shallow-module smell with its falsifiable sign, a mechanical file-size-crossing check at Should-Fix severity, a reader-load probe, and the pass-through smell added to the baseline block that currently lacks it while the auditor has it.
5. **Scattered one-liners.** Pilot/land: probe idle agents read-only and re-read the skill file at tick start. Interview/plan: an empirically answerable fork gets a throwaway probe, not a question; wildly divergent independent opinions mean the framing was underspecified, so reframe and re-run rather than average. Review vocabulary gains a named evidence scale (claimed / cited / walked / executed / reproduced) without any receipt-schema change. Memory intake gains three acceptance filters (a mechanizable lesson routes to a gate proposal, not prose; a lesson must route to something actually used in the transcript; a rule that existed but did not fire gets a retrieval fix, not a rewrite). The worker gains the comment-as-alibi block (a comment justifying a workaround is a finding; a constraint stated in a comment wants encoding then deletion). Plan's task-shape guidance gains an equivalence-harness sentence for refactor-shaped tasks, and the conductor side of gate integrity gains: a caught gate manipulation strengthens the gate, never just reverts the edit.

## Quick commands

```bash
./scripts/sync-codex.sh && ./scripts/sync-codex.sh   # twice - idempotency + guards
cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_chart_docs_inventory -q
```

Full gate at the end (per repo rules): `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`

## Edge Cases & Constraints

- Every target surface must be verified unpinned at implementation time (`test_prompt_text_pinned.py`); an edit that strays into a pinned constant updates the pin in the same commit with rationale.
- G1 binds every line: each added rule must name the failure class it closes; restatements of existing worker/conductor rules are rejected at review.
- Semantic preservation is a review criterion: each added rule must keep the full force of the failure class it closes - a softened or hedged rule is a finding, not a style choice.
- The codex mirror regenerates via `sync-codex.sh` run twice; conduct checklists for every touched skill (land, work, interview, plan, audit) are verified against the diff.
- Autonomy-behavior changes (land triage ordering, silent-lane stand-down, pause path) are conservative by construction: they refund or preserve bounded budgets, never widen them, and bind to explicit signals only.
- Downstream: the flow-next.dev docs restructure is in flight and not landed; any docs-site propagation from this spec must first check the new structure rather than assuming the current page layout.

## Acceptance Criteria

- **R1:** The land conductor carries the six defect repairs (triage ordering with no strike on a stale base, post-merge sibling re-gate on all repos, a fresh tick concurrency claim, repeat-failure reclassification, dependency contiguity before merge, comment-text-as-evidence posture). Errors: a held tick claim yields a terminal no-work verdict, never a second writer; a stale claim clears by age; all budget changes are refunds or holds, never widenings.
- **R2:** The worker contract carries the gate-integrity block (the thirteen rules in Architecture item 2), and the dispatch template carries the path ban and runtime cap with the silent-lane stand-down bound by the existing strike cap. Errors: a stood-down healthy-but-slow lane costs one bounded retry, never correctness; the runtime cap returns partial findings, never an empty abort.
- **R3:** The quality auditor and smell baseline carry the seven unpinned review additions, with the file-size check mechanical and capped at Should-Fix, and the shallow-module smell only present with its falsifiable sign. Errors: no addition raises the standards axis above its severity ceiling; no addition fires on pre-existing code (introduced-only discipline unchanged).
- **R4:** The scattered one-liners land at their named surfaces (pilot/land liveness pair, interview/plan probe-and-divergence pair, evidence-scale vocabulary, three memory intake filters, worker comment-as-alibi block, refactor equivalence-harness sentence, conductor gate-hardening clause, pause path, cleanup gate, selection-rule line, continuation-worker posture, zero-shipped accounting line, plus one memory entry routing state-before-code debugging guidance). Errors: the pause path binds to explicit pause or compaction signals only - an autonomous "keep going" instruction never triggers it.
- **R5:** Distribution and gates stay green: `sync-codex.sh` twice idempotent with all guards passing, conduct checklists for touched skills verified, the full suite and lint green, and one CHANGELOG entry staged under `## Unreleased` with no version bump. Errors: a guard failure is load-bearing - fix content or extend the transform, never relax the guard.

## Boundaries

- The pinned review-rubric lines (duplication-tolerance filter, traced-call-chain requirement, named-input-path security precondition, real-thing-not-proxy, covered-means-reached, re-entry scenario, serialization-test rewrite) are a separate future spec with a single hash-move pass and a before/after eval - explicitly not here.
- Verdict-integrity receipt fields (head SHA and patch identity on receipts, the non-boolean verdict vocabulary) are a separate future spec - not here.
- No new mechanisms, no schema changes, no flowctl code, no new skills, no enforcement machinery, no version bump.
- `fn-149-land-hardening-survive-stacked-pr-auto` (stacked-PR retarget survival) is a different defect set in the same file; this spec's land edits share no lines with it and neither blocks the other.
- The persisted feature-map idea from the same audit stays parked pending an explicit decision.

## Decision Context

Direct-batch over per-item specs: the 34 edits are individually reviewed-and-adjudicated one-liners; the cost of a spec each would exceed the work. Grouped into two implementation waves inside one spec (land defect repairs first, everything else second) so the defect repair gets its own reviewed diff. The land edits ship as conservative repairs (refund-or-hold budget semantics) because misworded autonomy prose fails quietly - burning budgets or stalling loops - rather than loudly. The pinned review lines are excluded because their edit ceremony (hash moves across four surfaces plus an eval) deserves a single dedicated pass rather than riding a 34-item batch.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Land conductor defect repairs | fn-208-hardening-pass-worker-review-and.1 | - |
| R2 | Worker gate integrity + dispatch template | fn-208-hardening-pass-worker-review-and.2 | - |
| R3 | Unpinned review additions | fn-208-hardening-pass-worker-review-and.2 | - |
| R4 | Scattered one-liners | fn-208-hardening-pass-worker-review-and.2 | - |
| R5 | Distribution + gates green | fn-208-hardening-pass-worker-review-and.2 | - |
