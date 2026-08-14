---
title: Ralph guard reverts its delegation amendment; bridge safety is prose-only
date: "2026-08-14"
track: knowledge
category: decisions
module: plugins/flow-next/scripts/hooks/ralph-guard.py
tags: [flow-98, ralph-guard, codex-delegation, safety, deprecation]
applies_when: "Editing ralph-guard.py, or wondering why prose-routed bridges have no hook-level git guard"
decision_status: accepted
alternatives_considered: ['Widen the guard to recognize prose-routed bridge invocations (rejected: Ralph is deprecated and bridge command shapes are agent-authored, so an allowlist would be a race against the next spelling)']
related_to: [knowledge/decisions/composed-brief-deleted-path-handoff-2026-07-19]
---

## Decision

The Ralph guard's codex-delegation amendment reverts with the packaged
delegation subsystem (flow-98, R8). Deleted from
`plugins/flow-next/scripts/hooks/ralph-guard.py`: the
`is_canonical_codex_delegation` recognizer, `_scratch_dir_of`, the
`_SCRATCH_BASENAMES` map, the `_DELEGATE_YOLO_FLAG` / `-s workspace-write`
sandbox allowlist, and the codex-section early-pass that let the canonical
`FLOW_DELEGATE_CODEX=1 codex exec …` shape through. The guard is back to its
pre-fn-55 behavior: every direct `codex exec` / `codex review` blocks, only
`flowctl codex …` wrappers pass, and `--last` blocks even through a wrapper.

Deliberately NOT widened to cover prose-routed bridges (`codex exec`,
`cursor-agent`, `grok` invoked from the model-routing prose).

## Rationale

The amendment existed to bound exactly ONE machine-generated command shape.
With that generator deleted, the allowlist has no producer, and an allowlist
with no producer is only attack surface plus maintenance.

Ralph is already deprecated - the documented route for an unattended loop is a
shell script around the pipeline primitives - so building new hook enforcement
for a harness we steer people away from buys nothing. Ralph worked before the
packaged path existed and returns to that behavior.

## Accepted trade (stated, not hidden)

For prose-routed bridges the rule "the bridge child writes code; the host keeps
git and judgment" now lives in PROSE ONLY (`.flow/usage.md` bridge recipes,
flow-98 R9b) - not in a deterministic hook. That is weaker than a mechanical
guard. It is the accepted cost of deleting a subsystem whose enforcement only
ever covered one generated command shape.

## Where the surviving invariants are tested

`plugins/flow-next/tests/test_ralph_guard.py::CodexSectionGuardTestCase` -
direct exec/review blocked, wrapper allowed, `--last` blocked through the
wrapper, copilot blocked, non-codex allowed, plus two regrowth guards: the old
canonical delegation shape now BLOCKS, and the guard module carries no
`is_canonical_codex_delegation` / `_scratch_dir_of` / `FLOW_DELEGATE_CODEX`.
