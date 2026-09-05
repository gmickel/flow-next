---
title: Backend special-case in a shared helper is an enumeration site too
date: "2026-09-05"
track: bug
category: integration
module: plugins/flow-next/scripts/flowctl.py
tags: [review-backend, claude, enumeration-sweep, fn-221, tracker-manifest]
problem_type: integration
symptoms: claude validate/deep-pass accepted a foreign --spec and resumed with a foreign model; manifest stale after a post-regen edit
root_cause: _resolve_session_pass_spec strict check was a backend == cursor special case the tuple sweep never lists; manifest regenerated before the final flowctl.py edit
resolution_type: fix
---

## Problem
Adding the `flowctl claude` review subcommands (fn-221.2), the primary commands rejected a foreign `--spec` through `_resolve_claude_review_spec`, but `validate` and `deep-pass` route through the shared `_resolve_session_pass_spec`, whose strict own-backend check was a `backend == "cursor"` special case. `flowctl claude deep-pass --spec codex:gpt-5.4:high` resumed the claude session with `--model gpt-5.4`. Two of three fan-out draws reproduced it through the real CLI entry.

## What Didn't Work
Treating the enumeration sweep as "every `{codex,copilot,cursor}` tuple/dict" - the sweep found the parser dicts, the guard set and the schema prose, but a single-backend `if backend == "cursor"` branch inside a shared helper is the same enumeration site written as a special case, and grep for the tuple never lists it.

## Solution
`_resolve_session_pass_spec` (flowctl.py) keys the strict grammar on a small `{backend: grammar}` map covering every backend whose model ids do not cross over (`cursor`, `claude`), with a message naming the backend; `test_claude_review_commands.py::test_session_passes_reject_foreign_spec_before_spawn` drives both passes through the real CLI and asserts exit 2 with zero spawns. A second round caught the tracker manifest going stale because `flowctl.py` was edited after `gen_tracker_manifest.py` had run - regenerate LAST, after the final code edit.

## Prevention
When adding a backend, grep for `== "<newest-backend>"` / `!= "<newest-backend>"` in flowctl.py as well as for the backend tuples: a per-backend special case in a shared helper is an enumeration site. Run `python3 scripts/gen_tracker_manifest.py` (and the schema generator) as the last step before each commit that touches `flowctl.py`, never before a review fix.
