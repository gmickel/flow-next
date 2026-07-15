---
title: Spec-named config keys must be checked against shipped surface; cross-family is 
date: "2026-07-15"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-setup/workflow.md
tags: [fn-97, config-contract, spec-amendment, cross-family-review, codex-review, review-feedback]
problem_type: integration
symptoms: R1 named snake_case keys that never shipped; codex review recommended as cross-family on GPT-writer hosts
root_cause: Spec authored without checking get_default_config(); cross-family framed host-relative instead of writer-relative
resolution_type: fix
related_to: [bug/integration/byte-for-byte-spec-contract-branch-2026-07-01, bug/integration/rp-builder-file-slices-cause-false-2026-06-10]
---

## Problem
fn-97 R1 specified "new" snake_case config keys (`work.delegate_model` / `work.delegate_effort`) with omit-flag-when-unset semantics - but fn-55 had already shipped the same surface as camelCase `work.delegateModel` / `work.delegateEffort` with deliberately ALWAYS-explicit `-m` / `-c` flags (`--ignore-user-config` isolation). Implementing the spec verbatim would have created duplicate alias keys and re-introduced a defer-to-user-codex-config path fn-55 deliberately closed. Separately, the spec's "cross-family review = codex" framing was host-blind: on a Codex host the mirror worker is GPT (terra), so recommending/switching to codex review is SAME-family and re-correlates blind spots.

## What Didn't Work
Treating the spec's key names as authoritative without checking `get_default_config()`; and claiming R1 satisfied by the pre-existing keys without amending the spec - the codex reviewer correctly held NEEDS_WORK at confidence 100 until spec, task body, and implementation all named the same contract.

## Solution
- Amended spec R1 + API Contracts + Boundaries and the TASK body to the as-shipped fn-55 contract (flowctl spec set-plan + direct task-md edit), keeping the real delta: default flip gpt-5.6-sol -> gpt-5.6-terra.
- Made every codex-review recommendation writer-family-aware: setup's Recommended label and the step-8 switch offer are skipped when PLATFORM=codex; orchestration.md table/footnote states cross-family is measured from the WRITER, not the host (plugins/flow-next/skills/flow-next-setup/workflow.md, docs/orchestration.md).

## Prevention
- Before implementing a spec that "adds" config keys, grep `get_default_config()` + flowctl.md config table for the surface under any casing; a naming mismatch means amend the spec/task to the shipped contract in the SAME commit as the implementation (reviewer checks all three agree).
- Any "cross-family review" default must name the reference point: cross-family FROM THE WRITER. Audit every recommendation surface (setup questions, snippets, docs tables) for host-blindness when the writer model varies by host.
