---
title: Review backend adapters move diagnostics between output and stderr
date: "2026-10-05"
track: bug
category: integration
module: plugins/flow-next/scripts/flowctl.py
tags: [fn-283, review, backend-adapters, failure-message]
problem_type: integration
symptoms: Claude no-verdict failure recorded no CLI message; sandbox line omitted it
root_cause: Extractor read only the output slot; claude adapter moves error results to stderr
resolution_type: fix
related_to: [bug/integration/a-new-terminal-status-needs-every-2026-10-05, bug/integration/bundled-snapshot-pr-listing-truncation-2026-09-26]
---

## Problem
fn-283 (#515) added the CLI's last error text to no-verdict review attempts, read from each backend's returned output. Review found the claude adapter (`run_claude_exec`) moves an `is_error` result into stderr and returns empty output, so a Claude spend-limit failure recorded no message and the skills' limit rule could not apply. The sandbox refusal branch in `_finish_backend_exec` also exited before the new suffix was added.

## What Didn't Work
Reading only the output slot because the spec said "last non-empty output line". The test fed plain output straight into the shared runner, so it never exercised what an adapter actually returns.

## Solution
`_review_failure_message(backend, output, stderr)` falls back to the last non-empty stderr line when the output names nothing; the sandbox `error_exit` ends with `_failure_message_suffix` like the other no-verdict lines (plugins/flow-next/scripts/flowctl.py).

## Prevention
Before reading a field off the shared review runner's `(output, sid, rc, stderr)` tuple, read each backend's `run_*_exec` return paths: they move diagnostics between output and stderr differently (claude moves error results to stderr, cursor keeps them in output, timeouts return flowctl's own text in stderr). Test with the tuple the adapter returns, not with idealized output, and list every `error_exit` branch after the new value is computed.
