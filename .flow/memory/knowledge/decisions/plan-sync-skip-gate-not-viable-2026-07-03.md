---
title: A deterministic plan-sync skip-gate is not viable — do not re-attempt
date: "2026-07-03"
track: knowledge
category: decisions
module: plugins/flow-next/skills/flow-next-work/phases.md
tags: [plan-sync, work-loop, gate, eval, fn-83, drift, determinism, shelved]
applies_when: considering any deterministic/cheap probe to skip the plan-sync agent after a work task
---

## Problem

`/flow-next:work` spawns the plan-sync agent (opus, ~70-90k tokens, minutes) after every completed task to check whether the implementation drifted from the plan and edit downstream task specs. On the fn-81/fn-82 runs it returned "no drift, no edits" 3/3 times — apparently wasted spawns. fn-83 set out to gate plan-sync behind a cheap **deterministic** probe: prove "this task cannot have affected any downstream task" (file-path intersection + morphological symbol-token intersection between the task's diff and downstream task/spec bodies, plus a worker `PLAN_DEVIATION` flag), and skip the spawn when proven disjoint; fail open otherwise. Hard constraint: zero quality loss, eval-proven before ship.

## What Didn't Work

**The deterministic skip-gate. It was built, fully tested, and killed by its own eval.** Two independent, fundamental failures (not tuning problems):

1. **It is not safe — drift is semantic, and a deterministic probe cannot see it.** Cross-repo validation (fn-83.6) replayed 27 real completed-task scenarios from three external flow-managed repos (`~/work/DocIQ-Sphere`, `~/work/gno`, `~/work/transcribe`), with frozen ground-truth answer keys from the REAL plan-sync agent (`claude-opus-4-8`, N=3 majority, wobble⇒drift; 82 runs). The probe produced a **genuine false skip**: `transcribe fn-25.3` changed a downstream task's *meaning* while touching no file and no symbol that task referenced — the real plan-sync agent flagged drift, and transcribe's own production history confirms plan-sync materially edited the downstream task at that exact state (commit `8f3565b2`). No path/token signal existed to catch it. You cannot stoplist or morphology-match your way to catching semantic drift.

2. **It would not pay even if it were safe.** Aggregate skip-rate on true-negative (real no-drift) scenarios was **1/15 = 6.7%** (design threshold ≥50%). On flow-next itself (fn-83.2 corpus) it was 0% with 0/14 false skips — safe but useless. The "monolith repo vs feature-sliced repo" hypothesis was explicitly tested and **disproven**: feature-sliced DocIQ-Sphere also scored 0% skips. Real tasks touch shared scope (shared modules, skill dirs, common symbols) pervasively enough that a disjointness proof almost never fires. The spawn-reason histogram (path-overlap 21/27, token-overlap 2, unparseable-refs 2, skip 2) shows dropping the entire directory-prefix arm would flip zero scenarios — every skip candidate also has real token overlap.

**Root cause:** whether a completed task invalidates a downstream plan is a *semantic* question about meaning and intent. The only reliable oracle is an LLM reading the actual code — i.e. plan-sync itself. Any deterministic proxy is either unsafe (misses semantic drift) or so conservative it never skips. A semantic proxy would just be a second LLM call, defeating the cost saving.

## Solution

**Abandon the skip-gate. Ship only the parts of fn-83 that are independently proven and valuable; remove the gate machinery from the shipped CLI; keep the experiment as archived evidence.**

Shipped (fn-83, streamlined):
- **`flowctl anchor <task-id>`** — the single-call worker anchor bundle (fn-83.3). Proven zero-loss: a byte-for-byte superset test vs the worker's current Phase-1 reads, plus a comprehension-equivalence eval (a worker answered anchor questions 7/7 from the bundle vs 7/7 from the old ~8 discrete reads). This is a pure round-trip reduction; it works because the bundle is assembled by invoking the same production `cmd_*` functions the worker already uses and concatenating their verbatim output.
- **CROSS_SPEC caller fix** — the plan-sync spawn prompt never passed the `CROSS_SPEC` flag its own contract (`plan-sync.md:19`) documents; an independent latent-bug fix that makes the *existing* unconditional plan-sync correct in cross-spec mode.

Removed from the shipped plugin (`plugins/flow-next/scripts/flowctl.py`): `plan-sync-probe` command + probe-specific `_psp_*` helpers, `planSync.gate` config enum, the `plansync-gate.jsonl` ledger, and their unit/corpus tests. (The one shared helper `_psp_run_git` is retained/relocated because `flowctl anchor` reuses it.) No `PLAN_DEVIATION` worker line, no `base_commit` evidence change — both existed only to feed the probe.

Kept as archived evidence (dev assets under `optimization/`, never shipped in the plugin): `optimization/plan-sync-gate/` (this-repo corpus + frozen answer key + cross-repo verdict) and `optimization/worker-anchor/` (the passing comprehension eval).

**Plan-sync continues to spawn unconditionally after every task, exactly as before fn-83.** The speedup we chased on the plan-sync axis does not exist and is not recoverable with a deterministic gate.

## Prevention

- **Do NOT re-attempt a deterministic plan-sync skip-gate.** The failure is fundamental (semantic drift is invisible to path/symbol analysis), not a corpus/threshold/predicate that needs improvement. Any future attempt must start from the `transcribe fn-25.3` false-skip exhibit in `optimization/plan-sync-gate/cross-repo/` and explain how it catches semantic drift a deterministic probe cannot — which almost certainly requires a second LLM, defeating the purpose.
- If plan-sync cost is worth attacking again, attack it a different way: make plan-sync itself cheaper/faster (smaller prompt, cheaper model, tighter scope), or reduce how often *work* produces genuinely disjoint downstream tasks — not a gate that predicts drift.
- General lesson (reinforces the repo's agentic-vs-deterministic doctrine, CLAUDE.md): "did this change semantically affect that plan?" is a judgment question. Building a deterministic proxy for a judgment question is the anti-pattern the doctrine warns about; the eval harness earned its cost by killing the plausible-but-wrong optimization before it shipped and cost quality.
- Scope note: fn-102's hash/path-only gate diet is outside this ban - predicates are commit-hash equality + path membership + receipt age, no semantic proxies (see the fn-102 spec Decision Context).

## References

- Spec: `fn-83-work-loop-speed-conservative-plan-sync` (streamlined 2026-07-03 to ship only `flowctl anchor` + the CROSS_SPEC fix)
- Ship-gate verdict + methodology: `optimization/plan-sync-gate/cross-repo/README.md`
- This-repo safety corpus: `optimization/plan-sync-gate/README.md` (0/14 false skips, 0% skip-rate)
- Anchor-bundle proof: `optimization/worker-anchor/` (comprehension eval, bundle ≥ status-quo)
- False-skip exhibit: `transcribe fn-25.3`, production drift at commit `8f3565b2`
- Probe/harness commits (removed from shipped CLI, preserved in history): `5993c446` (probe), `e89f1beb` (cross-repo)
- Linear: FLOW-29
