---
satisfies: [R2, R10, R12]
---
# fn-130-reached-path-skill-prompt-optimization.11 Gate Make PR HTML and creation branches

## Description
Apply one conservative Make PR cold-branch extraction: keep HTML artifact-lens material cold when disabled or inapplicable while preserving dry-run, body rendering, create/finalize, existing-PR, push/retry, and autonomous refusal behavior.

**Size:** S
**Files:** `plugins/flow-next/skills/flow-next-make-pr/**`; existing Make PR optimization assets/tests; `optimization/reached-path/make-pr-*`; corresponding Codex mirror.

### Approach
- Verify task input hashes match `V1/B1`; compare candidates only against `B1`.
- Load the HTML lens only when artifacts are enabled and the reached mode needs it.
- Keep body safety, push/retry, existing-PR handling, and finalization instructions at their consuming phases.
- Score routing independently from any other cluster; retain discarded candidates.
- Recheck dormant fn-73 before edits; its forge semantics take precedence.

### Frozen fixtures
- dry-run HTML off; dry-run HTML on; create/finalize; existing PR; rich/risky/sparse payloads; push retry; push failure; autonomous incomplete-spec refusal.

### Investigation targets
**Required**
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md:317-375` — HTML lens surface.
- `optimization/make-pr/fixtures/{payload-rich,payload-risky,payload-sparse}.json` — frozen rendering corpora.
- Existing Make PR smoke/prose/mirror tests.

**Optional**
- fn-73 forge spec for overlapping files/semantics.

## Acceptance
- [ ] Task input hashes match `V1/B1`; Make PR has an independent `B1`/candidate ledger and every candidate can be kept or discarded without affecting Strategy or Pilot.
- [ ] HTML material remains cold when disabled/inapplicable and loads only on the selected enabled path.
- [ ] Dry-run, ordinary body rendering, create/finalize, existing-PR, push/retry/failure, autonomous refusal, and rich/risky/sparse outputs match `B1`.
- [ ] Existing and new route assertions pass on canonical and Codex mirror; fn-73 status is rechecked.
- [ ] Reached-path improvement and every discard reason are recorded without claiming unmeasured wall-time gains.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
