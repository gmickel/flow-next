---
title: GitHub rulesets need an admin bypass or spec-only commits stall
date: "2026-09-11"
track: knowledge
category: workflow
module: ci
tags: [github, rulesets, ci, flow-state]
applies_when: GitHub rulesets need an admin bypass or spec-only commits stall
---

## Problem
The fn-225 CI-pruning pass (2026-09-05) created a "Required CI" ruleset on the default branch of flow-next, flow-swarm, gno, and gno.sh with an empty bypass list. Every push to main then required the CI status, including `.flow/` spec-only commits that CI does not exercise. Direct flow-close and capture commits, which had landed on main for months, silently became impossible; fn-237's close needed a PR, and the fn-238 capture was refused at push.

## What was chosen
Add the repository admin role (RepositoryRole id 5, bypass mode always) as a bypass actor on each Required CI ruleset. Branch PRs still run CI; only direct admin pushes skip the check. The Copilot review and deletion/force-push rulesets were left untouched. Applied 2026-09-11 to flow-next, gno, gno.sh; flow-swarm already carried a user bypass; dettivo-linux has no push-blocking rule.

## Why
Spec and flow-state commits are the maintainer's own bookkeeping and carry no code. Forcing them through a PR adds a CI run and a merge for nothing, and a ruleset with no bypass blocks the admin as well.

## How to apply
When adding or changing a ruleset with required status checks or pull-request requirements, include the admin bypass in the same change and record it in the spec. Check with:

    gh api repos/<owner>/<repo>/rulesets/<id> --jq '.bypass_actors'

An empty list on a required-checks ruleset is the symptom.

## Considered alternatives
- Route every spec commit through a PR (rejected: ceremony with no verification value, and it changed the repo's landing convention without a decision).
- Path-exclude `.flow/` from the ruleset (rejected: rulesets condition on refs, not paths).
