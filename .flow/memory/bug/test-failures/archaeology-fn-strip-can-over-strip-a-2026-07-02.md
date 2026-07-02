---
title: Archaeology fn-strip can over-strip a test-pinned canonical breadcrumb
date: "2026-07-02"
track: bug
category: test-failures
module: plugins/flow-next/skills/flow-next-tracker-sync/steps.md
tags: [fn-82, archaeology, fn-strip, sync-codex, mirror, test-pinned, allowlist, final-gate]
problem_type: test-failure
symptoms: full pytest 1 fail (test_pilot_backlog_mirror_safety) after fn-NN provenance strip; smoke stayed green
root_cause: strip allowlist omitted fn-tags that a mirror-safety test pins as canonical invariants
resolution_type: fix
---

## Problem
fn-82.2's tracker-sync archaeology sweep (strip build-time `fn-N`/`fn-N.M` provenance from always-loaded prose) rewrote a breadcrumb in `flow-next-tracker-sync/steps.md` from "Codex mirror is regenerated in **fn-68.5** (a SEPARATE task)…" to "Codex mirror regen is a **SEPARATE task**…", dropping the `fn-68.5` token. That token is pinned by a test: `test_pilot_backlog_mirror_safety.py::test_maintainer_breadcrumb_stripped_from_mirror` asserts the CANONICAL steps.md still contains `Codex mirror is regenerated in **fn-68.5**` (the human-useful breadcrumb) while sync-codex.sh strips it from the MIRROR. The strip broke the canonical assertion — full pytest went 1392 pass / 1 fail, invisible to the per-task smoke test.

## What Didn't Work
The fn-82 strip/keep allowlist only enumerated `R\d+` ids, `S-[A-Z]` fixtures, and version numbers as strip-exempt. A bare `fn-NN` breadcrumb that a mirror-safety test keys on was NOT on the allowlist, so it was swept.

## Solution
Restored the canonical breadcrumb verbatim to the test-pinned string, regenerated the mirror (idempotent x2, parity green — the mirror still strips "Codex mirror is regenerated" as the test's mirror-side assertion requires). One-line canonical fix, not a test edit — the string is a load-bearing oracle, not free provenance. Fixed at plugins/flow-next/skills/flow-next-tracker-sync/steps.md:631.

## Prevention
1. Treat any fn-tag that a test pins as strip-EXEMPT (same class as R-IDs / S-fixtures) — grep the test suite for a candidate string before stripping it in an archaeology pass.
2. The final gate MUST run the FULL pytest suite (`python3 -m pytest plugins/flow-next/tests/`), not just smoke_test.sh — mirror-safety / canonical-invariant tests live only in pytest and catch exactly this class of over-strip. smoke covers CLI behavior, not doc-string invariants.
