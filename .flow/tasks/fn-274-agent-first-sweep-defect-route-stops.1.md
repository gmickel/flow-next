---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-274-agent-first-sweep-defect-route-stops.1 Implement Agent-first sweep: defect route stops and feature-map plumbing

## Description
Delete agent-first ceremony from two shipped surfaces (STRATEGY.md "Agent first", `.flow/criteria.md` G4). This is deletion, not replacement.

- Defect route (`skills/flow-next-work/references/defect-route.md`, route-matrix defect row, flowctl judge presentation text): the prior-fix step records open PRs touching the area and continues, stopping only when one fixes the bug or a person visibly owns a fix in progress (R1); reproduction asks for one that fires reliably, no fixed count (R2). Judge classification criteria text stays unchanged.
- Resolved-feature plumbing: remove the record, `flowctl done --resolved-feature`, the QA receipt field, the first-current-record precedence rule, the defect-intake verbatim-confirmation step, and the make-pr "Resolved feature" proof cell, with their tests (R3). Live-app stages read the feature map and match the feature themselves. Old receipts/task files carrying `resolved_feature` still load (R4).
- Docs, codex mirror, CHANGELOG Unreleased, flow-next.dev pages match; full suite green (R5).

Review focus: overengineering, slop and YAGNI. Reject any replacement mechanism, compat scaffolding beyond what R4 needs, or leftover references to the removed record.
## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
The defect route no longer stops when other open PRs touch the area: it records them and continues, and it stops only for an existing fix or a fix a person visibly owns (R1). Step 2 now asks for a reproduction that fires reliably, with no fixed count (R2). The route matrix and pipeline-variations follow. The judge's defect text never said "twice", so flowctl's routing text and the routing-accuracy study are untouched.

The resolved-feature record is gone (R3). Removed: `flowctl done --resolved-feature` and its validator, receipt line and export field, the QA receipt field, the contract's "Resolved-feature record" section and first-current-record precedence step, the defect-intake record and verbatim-confirmation step, the worker's record line, the make-pr `Resolved feature` cell, the slowness row's "record the match in the spec" (the review finding), and test_resolved_feature_evidence.py plus the QA record test. Live-app stages now run check existence, match the target (index plus one file), then drive.

On compatibility, passing `--resolved-feature` now fails as an unrecognized argument, a clear error with no accept-and-ignore shim, per the no-compat-scaffolding policy. Evidence JSON or QA payloads that carry `resolved_feature` still load and the key is ignored (R4). This is covered by test_resolved_feature_legacy.py and test_artifact_writers `test_qa_receipt_ignores_a_legacy_resolved_feature`, both confirmed red against the base.

Docs are updated: architecture.md, flowctl.md, the codex mirror and a CHANGELOG Unreleased entry (R5). The flow-next.dev pages are committed locally in ~/work/flow-next.dev-fn-274 (1cae146, not pushed), and the site build and link check pass. Conduct checklists needed no change.

Follow-up (parked unknown): prototype-before-ask.md's judge fork-gate fence was not folded in. It gates asking a person a question, not acting, and removing it touches a judge preset in flowctl, the route's shared fork subdecision, test_judge/test_judge_consumers and judge.md. That removal is not small, so it is left for a separate spec.

Tier: session - explicit override: implementer opus 5.5 (actual_model: claude-opus-5-5)

stage: impl-review - ran (codex gpt-6-astra high; round 1 fan-out NEEDS_WORK 1 finding, round 2 SHIP)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 50dc350949d8f813510f34f236b46333ec1fefe5, 078ddba86b7817083591d90739597e5251f9a1fa, 8ebe2f7c47848d6179540957ca011244bd1d98b8
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check, flow-next.dev: pnpm build && pnpm check:links
- PRs: