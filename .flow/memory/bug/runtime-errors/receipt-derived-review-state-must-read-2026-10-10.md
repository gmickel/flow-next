---
title: Receipt-derived review state must read the resolved receipt path
date: "2026-10-10"
track: bug
category: runtime-errors
module: flowctl.py _backend_impl_review
tags: [review, receipt, focus, rereview]
problem_type: runtime-error
symptoms: Re-review via REVIEW_RECEIPT_PATH or default receipt lost its focus
root_cause: Focus read from args.receipt before env/default receipt path resolution
resolution_type: fix
---

## Problem
The single-reviewer impl-review route read the prior round's focus from `args.receipt` before it resolved the effective receipt path (`--receipt`, then `REVIEW_RECEIPT_PATH`, then the route default). A re-review whose receipt came from the environment or the default resumed the right session and findings but dispatched without the focus, then wrote a receipt without it. Tests that always passed `--receipt` explicitly could not see it. All three review draws found it.

## Solution
Read every receipt-derived value (focus, prior findings, session) from the resolved `receipt_path`, after `args.receipt = receipt_path` in `_backend_impl_review`. The regression test runs the re-review with `REVIEW_RECEIPT_PATH` set and no `--receipt`.

## Prevention
When adding a value that a re-review inherits from the receipt, place its read next to `_read_prior_findings(receipt_path)` and test continuity through a receipt that is not passed with `--receipt`.
