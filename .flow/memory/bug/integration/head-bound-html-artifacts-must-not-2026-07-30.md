---
title: Head-bound HTML artifacts must not stale their own input
date: "2026-07-30"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-make-pr/html-lens.md
tags: [fn-136, make-pr, html, currentness, semantic-carrier, impl-review]
problem_type: integration
symptoms: Committed PR lens advanced HEAD beyond the cognitive aid it presented as current
root_cause: A head-bound derived artifact was committed to the same branch after selecting its input
resolution_type: fix
related_to: [bug/integration/adding-a-tracker-to-tracker-sync-sweep-2026-06-28, bug/integration/caller-fakes-must-enforce-lifecycle-2026-07-29, bug/integration/caller-oracle-must-preserve-historical-2026-07-29, bug/integration/rp-builder-file-slices-cause-false-2026-06-10, bug/integration/tracker-ownership-rewrites-require-2026-07-29]
---

## Problem

The optional HTML lens selected a head-bound current cognitive-aid object and then committed `pr.html` to the same reviewed branch. That commit advanced `HEAD`, immediately making the embedded object stale. The initial parity test also only round-tripped JSON and searched prose, so it did not exercise an HTML-consumable representation.

## What Didn't Work

Documentation that HTML consumes the same object was not executable proof. Ordering HTML before structured generation could not satisfy both exact-object parity and final-head currentness; a self-describing committed artifact creates a head-reference cycle.

## Solution

Generate and persist the structured cognitive aid before optional HTML. Emit a deterministic script-safe semantic carrier with `flowctl pr-cognitive-aid html-input`, embed it verbatim, and keep current-v1 HTML local-only so `HEAD` remains equal to `headSha`. Tests parse the carrier, recover exact object equality and all 500 ordered file rows, reject script termination, and assert the current branch contains no artifact commit.

## Prevention

For any head-bound derived artifact, test the full event order and assert publication does not mutate the identity it claims. Cross-render parity needs an executable lossless carrier or projector; prose and synthetic object copies are insufficient.
