---
title: Structured review parsers must distinguish invalid from absent
date: "2026-07-30"
track: bug
category: runtime-errors
module: plugins/flow-next/scripts/flowctl.py
tags: [fn-136, review-findings, fail-closed, parser, impl-review]
problem_type: runtime-error
symptoms: Malformed structured review evidence plus explicit-empty SHIP emitted an empty findings container
root_cause: "Canonical parsing was reused as presence detection, collapsing invalid records into absence"
resolution_type: fix
---

## Problem
A deterministic review parser could emit an authoritative empty findings container when explicit-empty SHIP prose appeared beside malformed structured evidence, including unknown prior statuses or incomplete host tables.

## What Didn't Work
Canonical parsers doubled as presence detectors. Unknown status values and partially recognizable tables therefore looked absent, while broad candidate bounds were enforced only after materialization.

## Solution
Detect line-level prior records independently from canonical status parsing, treat recognized malformed and strongly indicative partial tables as invalid, and count broad candidates incrementally before the 200-item limit. Regression coverage lives in `plugins/flow-next/tests/test_review_findings_parser.py`.

## Prevention
For additive structured parsers, separate presence detection from canonical parsing: recognized-but-invalid input must select the invalid sentinel, never the absent sentinel. Enforce candidate limits during discovery and combine every corruption regression with explicit-empty prose.
