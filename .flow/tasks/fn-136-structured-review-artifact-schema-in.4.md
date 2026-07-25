---
satisfies: [R3]
---
# fn-136-structured-review-artifact-schema-in.4 Prompt-template tightening + no-new-LLM guards

## Description
Tighten the flowctl Output Format blocks so parsing is reliable; prove the constraints.

**Size:** S

**Files:** flowctl.py review prompt templates; sync-codex run; a constraint-guard test.

### Approach
- Tighten ONLY where the .1 survey found ambiguity (e.g. mandate File:Line even for repo-wide findings via "File:Line: -", standardize R-ID mention form); templates live in flowctl python so most backends need zero skill-prose change; if rp/host skill prose needs a line, measure token delta <= 0.
- Guard test: the diff introduces no new subprocess/LLM invocation sites (grep-based assertion over flowctl.py's invocation inventory - document the mechanism).
- Run scripts/sync-codex.sh twice (idempotency) if any skill prose touched.

## Acceptance
- [ ] Template tightening per survey; token-delta <= 0 for any prose touch; sync-codex idempotent (R3).
- [ ] No-new-LLM guard in place (R3).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
