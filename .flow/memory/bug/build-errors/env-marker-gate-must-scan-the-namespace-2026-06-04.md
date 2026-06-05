---
title: "Env-marker gate must scan the namespace, not a fixed var list"
date: "2026-06-04"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-work/references/codex-delegation.md
tags: [fn-55, skill-prose-gate, env-markers, opencode, platform-gate, codex-delegation]
problem_type: build-error
symptoms: Platform gate prose says 'no OPENCODE_* marker' but bash checked only OPENCODE/OPENCODE_BIN — OPENCODE_SESSION etc. passed
root_cause: Fixed two-var env check cannot honor an open-ended 'any X_* marker' exclusion contract
resolution_type: fix
---

## Problem
A SKILL-prose gate predicate said one thing in prose ("exclude OPENCODE / OPENCODE_*") but the shipped bash only checked two fixed vars (`OPENCODE`, `OPENCODE_BIN`). Any other `OPENCODE_*` marker (OPENCODE_SESSION, OPENCODE_ROOT, …) silently passed the gate — a direct prose-vs-code mismatch the impl-review caught.

## What Didn't Work
Enumerating env markers as a fixed `${OPENCODE:-}${OPENCODE_BIN:-}` concatenation. A two-var check can never honor an open-ended "AND no OpenCode marker" contract — it only covers the markers known at write time.

## Solution
Scan the whole namespace: `[ -z "${OPENCODE:-}" ] || return 1` for the bare var, then `env | grep -q '^OPENCODE_' && return 1` for any prefixed marker (plugins/flow-next/skills/flow-next-work/references/codex-delegation.md `platform_gate_ok`). Added a test iterating OPENCODE_SESSION/ROOT/BIN.

## Prevention
When a gate's prose says "any X_* marker" / "no X marker", implement it as a namespace scan (`env | grep '^X_'`), not a fixed list of known vars — and write a test that passes a marker NOT in the original list. The discipline that caught it: extract the shipped bash predicate from the reference and EXECUTE it in the test (brace-match the function out of the fenced block) so prose claims are checked against runnable behavior, not just token presence.
