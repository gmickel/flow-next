# Spec-count rule (routing reference 2 of 6)

**Decision record**

- Source: capture's split-proposal reference, §2.5 spec-count heuristic, moved here unchanged; refine applies the same rule at its write-back.
- Trigger: a capture, a refine write-back, or a flow run from intent has drafted acceptance criteria and must decide whether one intent is 1..n specs.
- Purpose: one counting rule and one partition rule, so the split proposal capture prints and the split flow recommends cannot differ.
- Evidence: one spec is one PR and one completion review judging every R-ID; oversized specs degrade review quality, and padded splits degrade handover.
- Disposition: keep. The user still decides the split; nothing here auto-splits.

## Tripwire (when to compute)

8+ acceptance criteria, OR the criteria visibly serve more than one independently shippable outcome. Below the tripwire, skip this rule entirely.

## Counting rule

Count business and technical requirements only. Standing criteria (G-IDs from `.flow/criteria.md`) and process requirements (tests green, docs updated, mirror synced) never count; they ride along with any spec. Excluded-but-user-stated process items are still honored: carry them in the spec body's prose or Quick commands, not as counted R-IDs.

## Split criterion: independence, not size

The count trips the check; the partition comes from shippability:

- Would a stakeholder accept this cluster of criteria on its own?
- Do the clusters touch disjoint surfaces?
- Does one cluster depend on infrastructure another builds? A dependency seam is a natural spec boundary.

A large-but-cohesive set (12 criteria, one subsystem, one outcome) is ONE spec: say so in the read-back note and move on. Never pad N to look thorough.

## When the partition yields N>1

Compute the proposal: per proposed spec a short title, the criteria allocated to it, and the dependency edges between the proposed specs (`B depends on A`). Each proposed spec must be self-contained and independently reviewable.

The proposal surfaces at the read-back (allocation printed in full, one-line note in the ask). The skill never auto-splits; the user decides. Capture's own split machinery (the `split-as-proposed` option, the per-spec body composition, the split footer) stays in capture's `references/split-proposal.md`.
