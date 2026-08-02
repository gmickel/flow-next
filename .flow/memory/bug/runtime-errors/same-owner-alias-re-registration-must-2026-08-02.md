---
title: "Same-owner alias re-registration must harden a weak claim, not no-op"
date: "2026-08-02"
track: bug
category: runtime-errors
module: plugins/flow-next/scripts/flowctl.py
tags: [chart, aliases, two-pass-validation, flowctl]
problem_type: runtime-error
symptoms: Genuine initial-map alias collision surfaced as invalid_graph/self_edge instead of validation/alias_collision
root_cause: "Same-owner idempotent branch returned early, leaving a provisional weak claim displaceable by another decision's strong claim"
resolution_type: fix
related_to: [bug/runtime-errors/empty-value-semantics-leak-null-in-2026-07-20, bug/runtime-errors/flowctl-on-disk-per-key-counter-count-2026-06-27, bug/runtime-errors/forced-color-git-grep-output-defeats-2026-07-19, bug/runtime-errors/glob-walk-file-loads-need-lstat-screen-2026-07-19, bug/runtime-errors/structured-review-parsers-must-2026-07-30]
---

## Problem
`validate_and_build_initial_map` runs twice per `chart create --initial-map-file`: a provisional pass under a sentinel chart id (`fn-999999999`) and a real pass after allocation. The new owner-aware alias registrar marks chart-id-dependent full-D-ID claims as `weak` during the provisional pass so the sentinel cannot manufacture a false collision. A decision that explicitly claims the alias its OWN provisional full D-ID already holds hit the same-owner idempotent branch and returned early, leaving the claim weak. A second decision's identical explicit claim then displaced the weak incumbent, and its edge resolved to itself - so a genuine caller/caller collision surfaced as `invalid_graph` / `self_edge` from the provisional graph check instead of the contracted `validation` / `alias_collision` with claimant details.

## What Didn't Work
Treating same-owner re-registration as a pure no-op. It is idempotent for OWNERSHIP but not for CLAIM STRENGTH: an explicit `id` is chart-id independent, so it must not inherit the displaceability of a chart-id-dependent generated alias.

## Solution
`_InitialMapAliasRegistrar.register` (`plugins/flow-next/scripts/flowctl.py`) now hardens on the same-owner path: when the incumbent is weak and the incoming claim is strong, clear the weak flag before returning. Regression pinned in `plugins/flow-next/tests/test_chart_graph_claims.py::TestInitialMapAliasCollisions::test_provisional_sentinel_makes_no_false_collision_and_resolves`.

## Prevention
Whenever a registry carries BOTH an owner and a strength/priority attribute, the idempotent same-owner path must still reconcile the attribute - test the case where one owner registers the same key twice at different strengths. For two-pass validators generally: any suppression keyed on "this pass is provisional" needs a test proving the genuine case in the same shape still raises the contracted error.
