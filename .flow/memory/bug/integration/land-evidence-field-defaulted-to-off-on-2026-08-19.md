---
title: land evidence field defaulted to 'off' on configured-but-not-due paths
date: "2026-08-19"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-land/workflow.md
tags: [land, evidence, report-vocabulary]
problem_type: integration
symptoms: reviewers=off reported while land.requestReviewers was configured (red CI / satisfied signal)
root_cause: initializer used the disabled token unconditionally; only the firing branch overwrote it
resolution_type: fix
---

## Problem
The land workflow initialized the per-PR evidence field `REVIEWERS_STATE=off` unconditionally and only overwrote it inside the §2.6b predicate branch. The Phase 4 vocabulary defines `off` as "land.requestReviewers is unset/null/empty", so every configured-but-not-due tick (red CI, open threads, signal already satisfied, CHANGES_REQUESTED, any early-exit gate) falsely reported the feature as disabled. Surfaced by codex impl-review on fn-200.3 (P2).

## Solution
Initialize from the config value at the PR_STATE capture: `REVIEWERS_STATE=off; [[ -n "$REQUEST_REVIEWERS" ]] && REVIEWERS_STATE="skipped:not-due"`, reserve `off` for the unset case, and pin the initializer in `test_land_config.py` (`plugins/flow-next/skills/flow-next-land/workflow.md` ~l.205).

## Prevention
When a report field has a value that means "feature disabled", the initializer must branch on the config value, not default to the disabled token — every non-firing path otherwise inherits a lie. Pin the initializer, not just the vocabulary string.
