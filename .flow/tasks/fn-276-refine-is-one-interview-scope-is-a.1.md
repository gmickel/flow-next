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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
