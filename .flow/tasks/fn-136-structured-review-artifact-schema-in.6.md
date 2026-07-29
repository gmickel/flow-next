---
satisfies: [R6, R7, R8]
---
# fn-136-structured-review-artifact-schema-in.6 Structured PR cognitive-aid artifact + GitHub Markdown walkthrough

## Description
Implement the shared versioned PR cognitive-aid contract and deterministic GitHub Markdown approximation.

**Size:** L

**Files:** make-pr canonical skill/workflow and mirror; flowctl validation/write/currentness plumbing; cognitive-aid export; focused fixtures/tests.

### Approach
- Implement `pr_cognitive_aid` identity, schema version, base/head binding, supersedes chain and source table. The existing host agent owns thesis, logical grouping, source references and order; flowctl only validates and persists.
- Require group/file provenance references. Preserve file-level R-ID/task evidence without inheriting group claims. Separate Git `changeType` from `attentionClass`.
- Enforce all path/URL/string/count/payload bounds and reject invalid/unsafe/ungrounded artifacts without truncation. Current selection must not mix stale or legacy fields.
- Render the full GitHub walkthrough only at `humanReviewLines >= 200` or `canonicalFileCount >= 6`; otherwise use the deterministic compact form.
- Render the complete legend, proof table, 1-7 evidenced steps, file tables and diff links. Keep generated/mechanical files collapsed, raw diffs excluded and the risk-ranked Review plan intact.
- Benchmark validation plus rendering at 50 ms p95 over 30 warm fixture runs; no model/network I/O.
## Acceptance
- [ ] Artifact identity/currentness, provenance, file-level evidence and separate change/attention dimensions validate and persist with no extra model call (R6).
- [ ] Markdown follows deterministic compact/full rules and complete legend while preserving Review plan and raw-diff privacy (R7).
- [ ] Bounds, rejection, stale/non-mixing selection and 50 ms p95 benchmark are fixture-tested (R8).
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
