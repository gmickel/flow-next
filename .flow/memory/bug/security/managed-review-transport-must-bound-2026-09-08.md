---
title: Managed review transport must bound time and protect scoped credentials
date: "2026-09-08"
track: bug
category: security
module: plugins/flow-next/scripts/flowctl.py
tags: [managed-review, transport, credentials]
problem_type: security
symptoms: Provider error text leaked scoped tokens and incomplete or trickled HTTP responses bypassed transport contracts
root_cause: Valid error envelopes escaped sanitization and sized reads plus socket timeouts were mistaken for complete bounded HTTP exchange
resolution_type: fix
related_to: [bug/security/rollback-path-sanitizer-must-not-2026-06-05]
---

## Problem
A valid local review provider failure could echo its scoped credential through ordinary CLI diagnostics. Sized HTTP reads could accept complete JSON despite premature EOF, and socket-operation timeouts allowed trickled responses to exceed the review execution deadline.

## What Didn't Work
Sanitizing only exceptions left valid error envelopes unprotected. Injecting IncompleteRead into tests missed HTTPResponse.read(amount)'s early-EOF behavior. urllib's timeout bounded socket operations rather than elapsed request time.

## Solution
The managed review hook uses a direct HTTPConnection with a monotonic deadline and socket shutdown timer, verifies remaining Content-Length, and returns generic failure diagnostics. Successful text masks the scoped token and credential-bearing session handles are refused. Ordinary CLI adapters remain unchanged. See plugins/flow-next/scripts/flowctl.py, _read_review_execution_response and execute_review.

## Prevention
Drive actual HTTPResponse framing with an in-memory stream, test a loopback response that trickles bytes below the socket timeout, and drive secret-bearing failures through the public CLI and receipt path. Keep no-socket parser regressions runnable in read-only review sandboxes.
