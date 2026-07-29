---
satisfies: [R6, R7, R8]
---
# fn-136-structured-review-artifact-schema-in.6 Structured PR cognitive-aid artifact + GitHub Markdown walkthrough

## Description
Implement the shared versioned PR cognitive-aid contract and deterministic GitHub Markdown approximation.

**Size:** L

**Files:** make-pr canonical skill/workflow and mirror; flowctl validation/write/currentness plumbing; cognitive-aid export; focused fixtures/tests.

### Approach
- Implement `pr_cognitive_aid` identity, schema version, base/head binding, supersedes chain and source table. The existing host agent owns thesis, logical grouping, source references and order; flowctl only validates and persists one JSON per generation at `.flow/artifacts/<spec-id>/pr-cognitive-aid/<artifactId>.json` (the contract home; see spec section 2).
- Require non-empty proof/group/file provenance references and exact same-record source coverage for every group/file R-ID or task claim. Preserve file-level evidence without inheriting group claims. Separate Git `changeType` from `attentionClass`.
- Enforce all path/URL/string/count/payload and per-kind cardinality bounds, including exactly 1-7 `step` groups; reject invalid/unsafe/ungrounded artifacts without truncation. Current selection must not mix stale or legacy fields.
- Compose, validate and persist the cognitive-aid artifact before final PR-body creation, then render the supported current artifact into that body. Keep PR creation as the boundary that produces `$PR_URL`; tracker projection remains after that boundary and must not become an artifact-generation dependency.
- Preserve the current make-pr tracker facade end to end: the PR-body tracker reference, explicit `--pr-url`, body-preserving reconcile to In Review, provider-native link or deduplicated fallback, optional breadcrumb, receipt-backed audit and single bounded retro-fire. Do not restore the retired tracker-runner dispatch or bypass the deterministic facade.
- Add regression coverage proving cognitive-aid generation and Markdown rendering neither alter nor skip the `makePr` tracker call, its PR URL/linkage inputs, status reconciliation, audit or retro-fire behavior.
- Render the full GitHub walkthrough only at `humanReviewLines >= 200` or `canonicalFileCount >= 6`; otherwise use the deterministic compact form.
- Render the complete legend, proof table, 1-7 evidenced steps, file tables and diff links. Keep generated/mechanical rows collapsed inside their upstream groups, never regroup files, keep raw diffs excluded and preserve the risk-ranked Review plan.
- Benchmark validation plus rendering at 50 ms p95 over 30 warm fixture runs; no model/network I/O.
## Acceptance
- [ ] Artifact identity/currentness, provenance, file-level evidence and separate change/attention dimensions validate and persist with no extra model call (R6).
- [ ] Cognitive-aid generation precedes final PR-body creation while the existing post-creation `makePr` tracker facade remains behaviorally compatible at its linkage, In Review, audit and retro-fire boundaries (R6).
- [ ] Focused regressions prove walkthrough rendering cannot alter, bypass or resurrect retired machinery around the deterministic tracker facade (R6).
- [ ] Markdown follows deterministic compact/full rules and complete legend while preserving Review plan and raw-diff privacy (R7).
- [ ] Bounds, rejection, stale/non-mixing selection and 50 ms p95 benchmark are fixture-tested (R8).
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
