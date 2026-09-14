---
title: "Plan-review criteria edits must also sweep workflow-rp.md (CE summary + Classic "
date: "2026-09-14"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md
tags: [plan-review, repoprompt, prompt-pins, codex-review]
problem_type: integration
symptoms: rp plan reviews never saw the new criterion or verdict block; codex fan-out flagged the gap
root_cause: rp builds its own instructions and rubric; pin/fixture parity tests cover only template + fallback
resolution_type: fix
related_to: [bug/integration/forwarded-license-carried-the-wrong-2026-09-14, bug/integration/spec-named-config-keys-must-be-checked-2026-07-15]
---

## Problem
A plan-review criteria edit (fn-142 Maintainability item + `maintainability:` verdict block) was swept through the four hash-pinned copies the fn-174 pattern names (skill template, flowctl fallback constant, both parity fixtures) and the codex mirror, but not through `workflow-rp.md`. The RepoPrompt backend does not consume the template: CE builds its own instructions summary in Phase 2 and Classic carries an inline rubric in Phase 3. The codex review fan-out (contracts draw) flagged it: rp reviews could never emit the block the new Decision Context write-back consumes.

## What Didn't Work
Following the prior commit's file list (fn-174.1 also touched workflow-rp.md, but the pin/fixture parity tests only cover the template and fallback, so nothing red pointed at the rp copies).

## Solution
Added the criterion to both rp paths in `plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md` (the CE `REVIEW_INSTRUCTIONS_FILE` heredoc summary and the Classic `## Review Criteria` list + `## Output Format`), then regenerated the mirror. Commit 47c218f6.

## Prevention
Treat a plan-review or impl-review criteria edit as a six-copy sweep: template, flowctl fallback, two fixtures, `workflow-rp.md` (CE summary AND Classic rubric), then `sync-codex.sh`. No parity test pins the rp copies; grep the criterion's name across `skills/flow-next-plan-review/` before committing.
