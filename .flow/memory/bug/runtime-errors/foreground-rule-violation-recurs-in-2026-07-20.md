---
title: Foreground-rule violation recurs in long worker runs
date: "2026-07-20"
track: bug
category: runtime-errors
problem_type: runtime-error
symptoms: worker backgrounded review; silent codex death; no resume; task stalled in_progress
root_cause: context decay + adjacent legit background pattern + harness habit; rule is prose far from the fence
resolution_type: workaround
---

## Symptom
fn-110.1 worker (52min, 61 tool calls) backgrounded its codex impl-review + armed a monitor despite worker.md:313 forbidding exactly that; the background codex died silently (no receipt, no process), the monitor never resumed the subagent, task stalled in_progress. Recovered via SendMessage resume with explicit foreground instruction.

## Root cause
Instruction decay at end of long context + the adjacent codex-delegation pattern (worker.md:157-175) that LEGITIMATELY backgrounds codex exec + ambient "background long jobs" harness habit. The review-specific prohibition is a prose paragraph far from the command fence.

## Fix that held
SendMessage resume: rerun review as one blocking foreground call.

## Durable fix candidate
Embed the Foreground rule as a comment INSIDE the fenced review command block (the fn-116 suite-capture treatment) in worker.md + impl-review/plan-review skills - fence-embedded rules survive context decay; prose paragraphs above do not. Recurrence of the fn-78 stall class (rule added 2.5.3).
