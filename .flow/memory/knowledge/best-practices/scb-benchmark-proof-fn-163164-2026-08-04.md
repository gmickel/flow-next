---
title: "SCB benchmark proof: fn-163/164 eliminated ceremony as a cost factor"
date: "2026-08-04"
track: knowledge
category: best-practices
tags: [fn-163, fn-164, fn-165, slopcodebench, benchmark]
applies_when: "SCB benchmark proof: fn-163/164 eliminated ceremony as a cost factor"
---

SlopCodeBench gated run (2026-08-04, opus-5, circuit_eval, gmickel/scb-flow-next; full data in vault 'flow-next - SlopCodeBench Experiment'): per-checkpoint stage timing shows flowctl wall-time 0.1-0.2 min and spec+plan authoring 1.6 min of a ~47-min checkpoint - ceremony went from the #1 measured overhead pre-3.15.0 (18 calls, dominant cost) to statistical noise after fn-163 (one-shot spec+bulk tasks) and fn-164 (brief). Same run: plan-review stage (4.2 min) caught a spec-interpretation defect that two plain-lite runs shipped bit-identically (missing-required-key defaulting); impl-review stage (8.1 min + 8.0 fix) was an ad-hoc benchmark reviewer that re-ran full suites + improvised mutation testing and still missed a semantic edge (X-width) 4 checkpoints running - supports the shipped quality-auditor design (readonly, diff-scoped, evidence-table; no suite re-runs). Caveat: benchmark reviewers are prompt-defined stand-ins, not the packaged skills.
