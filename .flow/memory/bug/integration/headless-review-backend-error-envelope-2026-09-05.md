---
title: "Headless review backend: error-envelope text must never ride the output slot"
date: "2026-09-05"
track: bug
category: integration
module: plugins/flow-next/scripts/flowctl.py
tags: [review-backend, claude, transport, verdict-channel, fn-221]
problem_type: integration
symptoms: is_error payload text containing a verdict tag was consumed as SHIP; wrong-type JSON parsed as a result
root_cause: "_finish_backend_exec parses the verdict before the exit code, and a shared lenient parser accepted non-result objects"
resolution_type: fix
related_to: [bug/integration/adding-a-review-backend-sweep-all-2026-06-29, bug/integration/drop-receipt-to-break-codex-2026-05-09, bug/integration/set-tracker-id-rejected-github-n-2026-06-03]
---

## Problem
Adding the `claude -p` review backend (fn-221.1), the runner shared cursor's lenient result parser and returned an error envelope's `result` text as reviewer output with only the exit code flipped to 1. Two ways a non-review became a SHIP: a wrong-type / type-less JSON object (or a valid result followed by corruption) parsed as a result, and an `is_error` payload whose text contained `<verdict>SHIP</verdict>` was consumed by `_finish_backend_exec`, which parses the verdict BEFORE it looks at the exit code. All three fan-out draws flagged it.

## What Didn't Work
Forcing `exit_code = 1` on `is_error`. The shared finalizer's order is verdict-first, so a non-zero exit does not protect the verdict channel; and sharing a JSON-lines salvage parser "for tolerance" widened what counts as a result.

## Solution
`_parse_claude_result` (flowctl.py) parses stdout as exactly ONE JSON object and requires `type == "result"`; anything else is `("", None, True, None)`. In `run_claude_exec._dispatch`, an error envelope (or the exit-0 unavailable signature) returns empty reviewer output, moves the envelope text to stderr, and keeps the parsed payload only for the ladder predicate. Regressions in `test_model_resolution.py` (`test_non_result_payloads_are_transport_failures`, `test_error_envelope_text_never_reaches_reviewer_output`, the latter driven through `_finish_backend_exec`).

## Prevention
For any new headless review backend: (1) the output slot of the exec 4-tuple is the VERDICT channel - never put failure-envelope text in it, diagnostics go to stderr; (2) do not reuse another backend's lenient parser - pin the CLI's exact success shape; (3) write the regression through the shared finalizer, not only the runner, because the finalizer's verdict-before-exit-code order is the coupling that bites.
