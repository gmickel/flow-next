# Delegation diet: replace the composed brief with path-handoff; shrink delegate:codex to rails

## Goal & Context

An 8-run controlled eval (2026-07-19, harness + full results in the spec authoring session's scratchpad `deleval/`; summary below) compared the packaged delegate:codex 8-section composed brief against a minimal fixed path-handoff prompt ("read `.flow/tasks/<id>.md` + `.flow/specs/<id>.md`, implement exactly that task, rails, report schema") on three real replayed tasks (fn-102.1 code-heavy, fn-102.2 prose wiring, fn-89.2 prose gates), gpt-5.6-terra @ medium, true base-commit worktrees, historical briefs verbatim as the control arm.

Result: objective-gate TIES on all fixtures (contract probes, acceptance greps, suites); blind judges (scrambled labels) found ZERO Major defects in path-handoff once orchestrator-owned steps (mirror regen, dual-copy) were adjudicated; exec wall-clock within 1.5x both ways; the one stable gradient (test thoroughness on the code fixture: 26/25 methods vs 11/9) closed completely with ONE general template sentence ("one test per named case - exhaustive, never representative" -> 34 methods). The pre-registered DELETE-THE-BRIEF bar was met.

Conclusion (bitter-lesson framing): the composed brief is scaffolding built for a weaker-model/thinner-spec era. The task/spec files already carry the contract; restating them costs 5-17 min of host composition + ~10x prompt tokens per task and adds nothing the review layer does not already guarantee. The delegation surface reduces to: **strong spec + thin fixed template + deterministic rails**. The rails (result schema, classify-result, circuit breaker, rollback, trust cross-check, consent, ralph-guard canonical shape) exist for UNATTENDED operation and stay; everything model-coddling goes.

## Acceptance criteria

- **R1:** The 8-section composed-brief prescription in `references/codex-delegation.md` is REPLACED by a fixed path-handoff template: read the task file + spec file (paths only), implement exactly that task, allowed-file list lifted verbatim from the task's Files line (minus orchestrator-owned artifacts: codex mirror, `.flow/bin` dual-copies), the existing constraints paragraph (no git, no `.flow/` writes outside own scratch, scope to listed files), the verify clause INCLUDING the eval-validated exhaustive-tests sentence ("Where the task enumerates test cases, edge cases, or a fail-closed matrix, write ONE test per named case - exhaustive, never representative; a named case without a test is an incomplete implementation."), and the unchanged output contract (result-schema.json). NO per-task composed content: no `<patterns>`, no `<approach>`, no restated contract, no line anchors. Assembling the template must be purely mechanical (task id, spec id, file list).
- **R2:** All deterministic rails are byte-preserved (MACHINE-CHECKED: the task hashes the kept rail sections of codex-delegation.md pre/post-edit and carries grep assertions for the load-bearing rail strings - canonical invocation flags, classify-result actions, circuit-breaker counter, trust cross-check field - so "a rail got swept out with the composition prose" is a gate failure, not a reviewer catch): pre-flight gates (platform, recursion, availability, consent, input-kind, clean-baseline), the canonical single-line `codex exec` invocation + ralph-guard allowlist shape, `--output-schema`/`result-batch` plumbing, `classify-result` taxonomy + circuit breaker + rollback, trust cross-check, `evidence.delegation` proof-of-work. Zero flowctl changes.
- **R3:** `references/codex-delegation.md` shrinks accordingly (target: at least half its current size; measure and record). Cut: the template-composition prose, batch-content guidance, and any instruction that restates spec content into the prompt. Keep: gates, invocation, rails, template (now fixed), result handling, failure taxonomy. worker.md's delegation touchpoints update to match (compose = fill 3 slots, nothing else).
- **R4:** Docs reframed honestly: `docs/orchestration.md` + `.flow/usage.md` § Orchestration present the RAW bridge (already documented) as the interactive route and `delegate:codex` as "the same bridge with deterministic rails for unattended loops"; the brief is gone from both. CHANGELOG Unreleased entry.
- **R5:** Spec-density guardrail, both ends. Plan side: one sentence at the plan skill's task-authoring step - task files must carry the full contract (named files, named test cases, named acceptance) because downstream executors receive the task file AS the brief (plan-time knowledge reaches executors through the task file, no other channel). Worker side: one JUDGMENT valve in the delegation decision - if the task file does not name its files and acceptance, do not delegate it; implement in-session (delegation is per-task optional; the host looks at the artifact and decides - no template compensation).
- **R6:** Eval evidence preserved: the results table + design land as a decision-record memory entry (knowledge/decisions) marking the composed brief do-not-rebuild without new evidence; the session scratchpad harness path recorded for reproduction.
- **R7:** Cross-platform checklist walked: sync-codex x2 idempotent + guards green (codex-delegation.md is mirrored); canonical prose host-portable; no version bump (batched releases).

## Approach

Prose-only surgery plus one decision record. Rewrite the template section of codex-delegation.md around the eval-validated fixed template; delete composition guidance; update worker.md Phase-2-delegation touchpoints ("fill the 3 slots, pipe to codex exec"); reframe orchestration docs; add the plan-skill density sentence; write the decision record. No flowctl edits, no config-schema changes (`work.delegate*` keys unchanged - the mode's surface is stable, its interior shrinks).

## Key files / interfaces

- `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md` (the shrink)
- `plugins/flow-next/agents/worker.md` (delegation prompt-composition touchpoints)
- `plugins/flow-next/docs/orchestration.md`, `.flow/usage.md` template source (setup-managed - check `usage.md` generation path), `CHANGELOG.md`
- `plugins/flow-next/skills/flow-next-plan/steps.md` (R5 density sentence at the task-authoring step)
- `.flow/memory/knowledge/decisions/` (R6 record)
- `scripts/sync-codex.sh` (regen only; guards must stay green)

## Decision Context

- Eval: 8 runs, 3 fixtures, historical briefs as control, pre-registered bars, blind scrambled-label judges, rep-confirmed gradient + one-line closure (F1B3: 34 test methods vs brief's 25-26). DELETE bar met.
- Rails stay because they solve a different problem (unattended trust/rollback with an unobservable external CLI), not model weakness. Brief goes because it solved model weakness that no longer exists at current spec density.
- The raw-bridge path (usage.md) is already the documented interactive route; this spec aligns the packaged mode with it instead of duplicating content-composition.
- fn-83's ban (no deterministic proxies for judgment) untouched: the template is fixed boilerplate, not judgment; spec density (R5) is where judgment lives, at plan time, made by the session model.
