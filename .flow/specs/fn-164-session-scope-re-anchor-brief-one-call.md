# Session-scope re-anchor brief: one call, token-bounded

## Goal & Context
<!-- scope: business -->

Benchmark evidence (SlopCodeBench lite-opus5, 2026-08-03, gmickel/scb-flow-next; vault: "flow-next - SlopCodeBench Experiment"): a fresh agent session re-anchoring on `.flow/` state costs ~5+ tool calls (`flowctl list`, then reading spec bodies, receipts, memory files) and drags full spec markdown into context every session. Measured: 3.81x cache-read tokens vs a no-flow control across 16 checkpoints — the carried `.flow/` context is the biggest cost multiplier after ceremony call count, and it recurs every session in every flow-next repo.

`flowctl anchor` (landed post-3.13.3) already solves this for TASK scope: one deterministic call bundling the worker's Phase-1 reads. The gap is SESSION scope: an agent arriving cold (benchmark checkpoint, fresh pilot tick, new chat session) has no task id yet and today reconstructs the workspace picture by hand.

Goal: one flowctl call that gives a cold session everything it needs to orient — token-bounded, deterministic, teachable as THE re-anchor step in the always-loaded block.

## Architecture & Data Models
<!-- scope: technical -->

New verb (name for planner: `flowctl brief` / `flowctl anchor --session`), pure read, no LLM:

- **Contents**: open specs (id, title, status, one-line goal), ready/in-progress tasks with claim state, last N done-receipts (id + summary line + evidence presence), memory index (entry names + one-liners, not bodies), active locks/runs, and pointers ("read fn-N full via `flowctl cat`").
- **Budget**: default output <= ~2k tokens-equivalent (chars/4). Deterministic truncation order when over budget (oldest receipts first, then memory one-liners) with an explicit `[truncated: ...]` marker. `--full` escape hatch; `--json` machine form.
- **Derivation**: reuses anchor's section builders where they are task-agnostic; no new state, no writes.

## Edge Cases & Constraints
<!-- scope: technical -->

- Empty/fresh `.flow/` must produce a useful short brief, not an error (the benchmark's checkpoint-1 case).
- Large repos (100+ specs): the budget must hold; closed/superseded specs excluded by default.
- Output must be stable across runs given identical state (agents diff it; tests pin it).
- The always-loaded setup block and worker/skill docs must teach brief-first re-anchor, replacing the `list`+read-everything pattern — otherwise the calls and tokens stay (same lesson as fn-99: guidance placement determines behavior).
- Coordinate with in-flight flowctl work (PR #290 area); second lander rebases.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** One flowctl invocation yields the session brief; fixture test pins content and section order for a populated repo and an empty repo.
- **R2:** Default output <= 2k tokens-equivalent on a fixture with 20 specs / 50 tasks / 30 memory entries; truncation marker appears and is deterministic.
- **R3:** `--json` form carries the same data machine-readably.
- **R4:** Setup block + relevant skills teach brief-first re-anchor as the default cold-session step.
- **R5:** No writes: brief leaves `.flow/` byte-identical (test asserts).
- **R6:** CHANGELOG entry; docs-site staged per downstream conventions.

## Boundaries
<!-- scope: business -->

- NOT changing task-scope `anchor` semantics.
- NOT summarizing via LLM — deterministic extraction only.
- NOT the ceremony/write-path work (separate spec).
- Benchmark prompt adoption happens in gmickel/scb-flow-next after revendor, not here.
