---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10]
---
# fn-296-four-new-attended-routes-and-a-visual.1 Implement Four new attended routes and a visual-parity pin

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Four attended intake rows in flow's matrix (captured artifact to diagnose, repeated agent mistake, prompt or skill change to measure, diff risk to prove), each with a gated procedure reference; the refactor row pins UI parity with screenshots and a pixel diff. One shared hardening ladder (plugins/flow-next/references/hardening-ladder.md) read by the new repeated-mistake row and by audit's Harden path; Harden now writes only lint or CI gates in existing surfaces, proves them on a named past occurrence, and recommends the route for code-level fixes instead of writing instruction-file rules. Prime's ranked-actions catalog gains the repeated-mistake recommendation. Flow's description (canonical and Codex diet line) names the new starting states. CHANGELOG Unreleased entries added. flow-next.dev route, flow and audit pages updated on local site branch docs/fn-296-intake-routes (commit a2ec213), not pushed; held for the release.

Open items for the person: R9 routing-accuracy study and R8 trigger probe need authorized paid model draws; run before release or defer R9 explicitly.

Decisions:
- Harden no longer writes new instruction-file gates for checkable lessons (code-level or no-surface cases go to the repeated-mistake route); earlier instruction-file gates keep their liveness check. Basis: spec R3 and the ladder's "instruction text last, judgment only" rule; audit never writes product code.
- Site docs committed locally, not pushed: publishing would document an unreleased feature on the live site.

stage: impl-review - ran [round 1 three-axis NEEDS_WORK, fix pass, re-review NEEDS_WORK with only the R9 open item] (model: codex gpt-6-astra high)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 61e3198a8dcf0dbef5d6ce8da8966e00eb3cf214, 6e5bb0aa6a4f74c0152411b364d45118c5363b62
- Tests: pytest test_flow_routing test_codex_flow_dispatch test_shipped_links test_skill_prose_diet test_skill_prose_flowctl_surface test_memory_marks test_reference_encoding_guard: 64 passed, pytest test_memory_audit_bundle test_prime_eval: 130 passed, ./scripts/sync-codex.sh --check: fresh, flow-next.dev astro build (worktree docs/fn-296-intake-routes): 84 pages, complete
- PRs: