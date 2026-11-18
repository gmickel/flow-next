---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14, R15, R16, R17]
---
# fn-334-fixes-from-the-reviewer-study-idea.1 Implement Fixes from the reviewer study: idea intake, parent at creation, redaction

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Fixed the reviewer-study defects in idea intake, parent at creation, and redaction (R1-R17).

- Idea parent: a created parent carries `flow-next-idea-<key>`; with nothing linked, the settle step searches for it (all pages) before creating, so a rerun after a failed link links it. No Labels on the create screen refuses before creating.
- Jira `wire read` takes a key or URL alone; idea writes check the key Jira returns (moved issues refused), unready and question refuse an idea key before any request, relations read current keys with an idea source; idea read/parent/link refuse a key now outside the discovery projects.
- Spec link refusal is case-blind; set-tracker-id needs --identifier with an idea source.
- Colour tags removed only outside code and noformat blocks; failure envelope carries subtype.
- GitLab: numeric epic set only when the response carries it (retry replays the same), ASCII digits only; create-first claim and failure details carry the parent.
- Redaction covers GITLAB_ACCESS_TOKEN, OAUTH_TOKEN, GLAB_CONFIG_DIR and every glab host when unknown; attachment download rejections carry the reason; a licence marker on glab stderr stays capability; token command checks exit status before strict UTF-8 decode; deep reason bodies keep the bare message.
- Docs: idea-intake reference, flow routing phrase and row (R15, +45 bytes always-loaded), tracker-sync and flowctl references, capture tracker reference, changelog.

stage: impl-review - ran (codex; round 1 three-reviewer panel NEEDS_WORK, 3 findings fixed; round 2 SHIP) (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: b08f2e993bce5cb1ca91f6cbd35b2d6752ab28df, fc348f747341fe752d7adcc382043980e902fb92, cf772bc2d3811660600f5f13b373cfd5ed156aec, 0eb208ebf9848f80758e393718a5afd07953e739, b2b65f5f67710e1f857c7b4eaaac37b02bcf20f2, 4a37ffc5d262bef25ad13d24e48303050a769ceb, aed314878dda4cd02c891faf06904260be18f587, e44e3c9264f7ccde58b8d1d4597dcc6ba4dee5cf, 5b429bc8b249788866b0327009c15037fdb8fdd3, 3f596034cd56e44ec3f3b59ac9bdd5d7124436c2, 423e474b48b4bb8a0a016fa37c8c37b7554ba830
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check .
- PRs: