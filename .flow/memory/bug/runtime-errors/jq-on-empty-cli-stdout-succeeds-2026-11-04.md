---
title: jq on empty CLI stdout succeeds silently; a blank glab answer read as no MR
date: "2026-11-04"
track: bug
category: runtime-errors
module: plugins/flow-next/scripts/make-pr-gitlab.sh
tags: [jq, glab, probe-failure, make-pr]
problem_type: runtime-error
symptoms: Successful glab call with empty or non-JSON stdout became an empty MR listing
root_cause: "jq runs no filter on zero inputs and exits 0, so the in-filter type check never fired"
resolution_type: fix
related_to: [bug/runtime-errors/cli-login-probe-a-nonzero-exit-is-not-2026-11-04, bug/runtime-errors/skill-fences-that-degrade-only-without-2026-09-13]
---

## Problem
make-pr's GitLab read helper (`plugins/flow-next/scripts/make-pr-gitlab.sh`) validated each `glab api` page with `jq 'if type == "array" then length else error end'`. A `glab` call that exited 0 with empty, whitespace-only or warning-only stdout gave jq no input, so jq printed nothing and exited 0. The accumulated listing stayed `[]` and the preflight read it as "no merge request". The existing-MR check then proceeded to close the spec, and the parent lookup treated the parent as having no MR. All three review lenses reproduced it.

## What Didn't Work
A type check inside the jq filter. jq never runs the filter on zero inputs, and `null` added to an array leaves it unchanged, so the check never fails.

## Solution
Slurp each page and require exactly one array document: `jq -s 'if length == 1 and (.[0] | type) == "array" then .[0] | length else error("not a listing") end'`. Empty, scalar, HTML and multi-document stdout now fail the read. Regression cases replay a recorded success with blank and HTML stdout through the helper, the existing-MR check and the parent lookup.

## Prevention
When shell code validates CLI JSON with jq, test the zero-input case: an empty stdout from a successful exit is not a JSON document. Use `jq -s` with a document-count check, or `jq -e` so an empty result is a failure, never `jq '<filter>'` alone.
