---
title: Scout fallback prose drifted from spec's decision-lock command shape
date: "2026-05-26"
track: bug
category: build-errors
module: plugins/flow-next/agents/context-scout.md
tags: [fn-50, clawpatch, scouts, decision-lock-in, flag-drift, codex-review]
problem_type: build-error
symptoms: "Fallback section documented --count where spec decision lock-in required --json (single shape, centralized schema check)"
root_cause: Wrote prose by local optimization (count is simpler) instead of mirroring the spec's decision lock-in
resolution_type: fix
related_to: [bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18, bug/build-errors/fn-44-review-cycle-lessons-2026-05-21, bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26]
---

## Problem

Wrote agent fallback prose using `flowctl repo-map list --count` (the
flag prime's DE7 detection uses for a fast scalar count) inside a scout
agent's `Fallback: Standard Tools` section — but the spec decision
lock-in explicitly says **scouts call `--json`** so the schema-version
check + parse-skip diagnostics stay centralized in one shape.

The drift created two documented command paths (`--count` for fallback,
`--json` for Step 0) where the spec required one. Codex impl-review
caught it as a Minor introduced finding before merge.

## What Didn't Work

Picking the flag based on local context ("we just want to know if it's
zero, so `--count` is simpler") instead of mirroring the decision
lock-in. The fallback section's job is to echo Step 0's idiom, not
optimize for the local read.

## Solution

Replace `--count` with `--json` + `count: 0` JSON-field check in the
fallback section so the two documented paths converge on the same
command shape. The scout still gets the count it needs (from the `count`
field in the JSON envelope) without introducing a second command path
the tests would have to cover separately.

Fix in `plugins/flow-next/agents/context-scout.md` line 406: change
`flowctl repo-map list --count` returns `0`
→ `flowctl repo-map list --json` returns `count: 0`.

## Prevention

When a spec carries a "Decision lock-in" / "decision lock-ins" section
specifying a single command shape (here: "Scouts call `flowctl repo-map
list --json`, not direct JSON parse. Centralizes schema-version
check."), grep the entire authored output for the alternative flags
**before commit** — even in prose sections that look orthogonal.

Static prose-contract tests caught the schema fields and enum values
(per the test_scout_fallback_contract.py assertions), but did NOT lock
the command-flag shape. Future tests of this kind should add an
assertion like:

```python
self.assertNotIn("repo-map list --count", agent_text)
```

when the spec decision lock-in says `--json` is the only documented
scout path.
