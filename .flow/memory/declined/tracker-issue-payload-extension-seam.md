# Generic tracker issue-payload extension seam

**Decision:** Not building a generic payload-extension seam for tracker providers.

A named field flow-next understands (`tracker.projectId` / `tracker.projectMilestoneId`)
beats an open payload seam that outsources semantics to every integrator: the seam
would need per-provider validation, reconcile semantics, and a compatibility contract
for keys flow-next cannot interpret. Extensibility sprawl for a need that named fields
cover as they arise.

## Prior requests
- 2026-08-08 - issue #315 option 2 (sn-furali); declined at fn-182 capture in favor of the per-spec named fields (option 1).
