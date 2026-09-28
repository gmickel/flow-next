---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-276-refine-is-one-interview-scope-is-a.1 Implement Refine is one interview; scope is a filter

## Description
Collapse refine into one interview. `--scope=<anything>` becomes an optional free-text lens (business, technical, qa, security, ...) that the agent interprets; `--biz` / `--tech` stay as aliases; no scope question up front; `--scope=research` keeps its no-questions research mode.

Delete the machinery the one interview no longer needs, with its tests: the scope question, the `flowctl scope` subcommands (resolve, bank, write-policy), the per-scope write policies, the pass-driven Decision Context Motivation / Implementation Tradeoffs split, the two-phase `both` run, the per-scope pass references and question-bank files (their check notes fold into one short list), and the template's scope-owner markers that only served the write policy. No replacement mechanism: the read-back names every section the session changed (R5). Specs written under the old layout still load and refine without being rewritten.

Capture, plan and chart change only where they referenced the removed behaviour. Docs (plugin docs, conduct checklist, flowctl reference, glossary, changelog) and the flow-next.dev refine/scope pages match.

**Review focus (maintainer steering):** overengineering, slop and YAGNI. Reject any replacement mechanism for the deleted write policies, any new flag, verb, field or check, and prose that restates rather than decides. Flag leftover references to the removed passes, write policy, scope question, or `flowctl scope`.
## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Refine now runs one interview: `--scope=<anything>` is a free-text lens (`--biz` / `--tech` aliases, `--scope=research` unchanged), with no scope question, and each answer lands in the section it belongs in; the read-back names every changed section (R5). Deleted the `flowctl scope` group (resolve, bank, write-policy) with its argv rewrite and tests, the pass references and the three question-bank files (check-list folded into SKILL.md), the two-phase both run, and the template's scope-owner markers and FLAT/SUBSTRUCTURED Decision Context comment (SPEC.md re-copied, prompt pin bumped deliberately). Old-layout specs still load unchanged: `test_r22_invariant.TestOldLayoutSpecLoadsUnchanged` pins the round trip (R4). Capture and flow's plan-vs-no-plan change wording only. Docs, conduct checklist, glossary, codex mirror, help fixture + HELP_SHA256, manifest and the CHANGELOG Unreleased entry are updated. The flow-next.dev pages are committed locally, not pushed, at /home/gordon/work/flow-next.dev-fn-276 (branch fn-276-refine-is-one-interview-scope-is-a, e7ca567). That branch is based on origin/main, so the release walk combines it with the unmerged fn-275 site branch.

Follow-up notes: the site's refine.mdx still carries fn-275-era wording ("NFR probes always qualify") that belongs to the fn-275 site branch; the frozen `tests/fixtures/interview_source_tags` fixtures still say "business pass", which is historical and left as is.

Tier: session - explicit override: implementer opus 5.5 (actual_model: claude-opus-5-5)

stage: impl-review - ran (codex gpt-6-astra high, 3-draw fan-out, round 1 SHIP, 0 findings)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 4bc10d2f0676113f61aa6c97dd5f9eb068f9ffd0
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check, baseline: green (python3 scripts/run_tests_parallel.py, 5215 tests pre-edit)
- PRs: