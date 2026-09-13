## Goal & Context

Superseded on 2026-09-13. This spec described the `flow --auto` integration for stacked PRs as a third slice behind a config gate. The redesign removed the gate and folded the integration into the two remaining specs:

- Selection, branch-from-parent, the make-pr base rung, stack linking, and the verdict prefix are fn-152 (chain authoring).
- Frontier-only merge, patch-id verdict carry-over, the bounded retarget, and the branch janitor are fn-149 (chain landing).

Nothing from this spec remains unowned. It is closed with no tasks so that it drops out of selection; the Linear issue FLOW-84 should be cancelled by the tracker projection rather than marked done.

## Acceptance Criteria

- **R1:** No behaviour is owned here; see fn-152 and fn-149. No error surface.

## Boundaries

- Do not implement from this spec.

## Decision Context

Three specs became two because the make-pr slice on its own was inert (its parent-base rung only fires when work branched from the parent, which was this spec's change) and because the config gate was dropped: chains are the default shape for a dependent spec and the GitHub stack is an automatic enhancement.
