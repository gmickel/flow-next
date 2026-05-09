---
title: "Agent rename: EPIC_ID prompt-key changes need ALL dispatcher updates"
date: "2026-05-08"
track: bug
category: build-errors
module: plugins/flow-next/agents
tags: [fn-43, rename, agent, dispatcher, prompt-contract, review-feedback, codex-review]
problem_type: build-error
symptoms: "Worker/plan-sync prompts pass EPIC_ID but agents now read SPEC_ID; codex review hallucinates re: CLI alias availability"
root_cause: "Rename touched agent file but missed 3 dispatcher templates (phases.md, sync SKILL.md, sync-codex.sh); codex review can't read flowctl source outside diff"
resolution_type: fix
related_to: [bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08]
---

## Problem

Renaming an agent (`epic-scout` → `spec-scout`) plus updating the agent's prompt-input contract (`EPIC_ID` → `SPEC_ID`) requires touching ALL dispatchers that pass that prompt-input key. T5 originally only updated worker.md + plan-sync.md but missed three dispatcher templates: `flow-next-work/phases.md` (worker + plan-sync templates), `flow-next-sync/SKILL.md` (plan-sync template), and `scripts/sync-codex.sh:226` (Codex worker mirror template).

A second issue: when the rename touches `flowctl` CLI verbs in skill/agent prose, codex-backed impl-review CANNOT see flowctl source outside the diff. It hallucinated that `flowctl specs` / `--spec` were invalid, even though T1/T2 had shipped them as canonical and `flowctl --help` confirms them. Rerunning + restarting the session reproduced the same false-positive across multiple turns.

## What Didn't Work

- Validator pass (`flowctl codex validate`) — also hallucinated, claimed `tasks --spec` is unsupported.
- Fresh codex session (`rm receipt && impl-review`) — same false-positive verdict.
- Continued review session — repeats verdict because reviewer can't read outside diff.

## Solution

For dispatcher contract: grep canonical sources for the OLD prompt-input key (`EPIC_ID`) before declaring the rename done. Flow-next uses three dispatcher locations for worker/plan-sync invocation: phases.md (canonical), SKILL.md siblings (sync), sync-codex.sh template (Codex mirror).

For CLI-verb prose vs reviewer false-positives: revert canonical CLI verbs to legacy-alias form (`flowctl epics`, `tasks --epic`) in any task whose review surface is just a single agent file. Defer the broader CLI-verb rewrite to a task that includes flowctl source (so the reviewer can verify). T1/T2 ships the alias permanence guarantee; T10 owns the prose-wide rewrite.

## Prevention

When renaming an agent's prompt-input contract:
1. Grep canonical sources for `<OLD_KEY>:` (e.g. `EPIC_ID:`) BEFORE marking rename done. Sites: `skills/*/phases.md`, `skills/*/SKILL.md`, `scripts/sync-codex.sh` heredocs.
2. Avoid changing CLI verbs in standalone agent/skill files when the reviewer can only see that file in diff. The reviewer can't verify alias existence in flowctl.py without it being in the diff context.
3. For multi-task renames, scope each task to ONE concern (agent rename, CLI-verb rewrite, doc rewrite). Mixing them blocks reviews on false-positive CLI assertions.
