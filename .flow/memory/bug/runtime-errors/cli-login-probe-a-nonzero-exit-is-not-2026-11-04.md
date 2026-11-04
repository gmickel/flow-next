---
title: "CLI login probe: a nonzero exit is not 'logged out'; .get() misses absent keys"
date: "2026-11-04"
track: bug
category: runtime-errors
module: plugins/flow-next/scripts/flowctl.py
tags: [forge, glab, probe-failure, validation]
problem_type: runtime-error
symptoms: Offline GitLab host classified as GitHub under an enterprise gh token; malformed MR rows raised KeyError
root_cause: Exit code read as a boolean ownership answer; optional-null fields validated with .get() so absent keys passed
resolution_type: fix
related_to: [bug/runtime-errors/empty-value-semantics-leak-null-in-2026-07-20, bug/runtime-errors/flowctl-bootstrap-only-fronts-usage-2026-10-12, bug/runtime-errors/forced-color-git-grep-output-defeats-2026-07-19, bug/runtime-errors/glob-walk-file-loads-need-lstat-screen-2026-07-19, bug/runtime-errors/same-owner-alias-re-registration-must-2026-08-02, bug/runtime-errors/section-input-computed-outside-anchors-2026-09-26, bug/runtime-errors/structured-review-parsers-must-2026-07-30]
---

## Problem
The forge rule asked each CLI whether it owned the origin host and read any nonzero `glab auth status` exit as "not mine". An offline but logged-in GitLab host also exits 1 (an API call fails), so with `GH_ENTERPRISE_TOKEN` set the rule fell through to `gh`, which claims every host, and classified a GitLab origin as GitHub. Separately, the MR row validator checked `isinstance(mr.get("sha"), (str, None))`, which passes when the key is absent, and the mapper then indexed `mr["sha"]` and raised `KeyError`. A list-valued `state` raised `TypeError` on the dict membership test. Both escaped the "a failed read is a probe failure" contract.

## What Didn't Work
Treating the CLI exit code as a boolean, and validating optional-null fields with `.get()`.

## Solution
`_gitlab_owns_host` (plugins/flow-next/scripts/flowctl.py) returns False only on glab's recorded logged-out answer ("has not been authenticated", matched on whitespace-collapsed stderr because glab wraps it); any other failure returns None, which ends detection as unknown. `_gitlab_mr_row` requires `"sha" in mr and "merged_at" in mr` and `isinstance(state, str)` before mapping.

## Prevention
For a CLI probe, record its negative answer and its failure answer live and test both: a probe that cannot tell "no" from "could not ask" must read the latter as unknown. When a validator allows None, check key presence separately from type, and fuzz recorded fixtures by deleting each mapped key.
