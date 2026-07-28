## Conversation Evidence

> user: "hard task but we noticed the same halting behavior in opus 5, figure out how this all applies to flow-next and if we could do a couple of simple tweaks that would improve behaviour without negatively affecting other models"
> user: "ok so break down which changes we would make"
> user: "ok, do it (all 3). we have another branch open, so we will do it on this worktree and then get it merged after testing and our normal landing procedure and then downstream updates."
> user: "Then we'll create a prompt for the other agent to tell them what changed on main so it can decide whether and how to rebase etc"

## Goal & Context
<!-- scope: business -->

Opus 5 at medium effort is a strong flow-next conductor, but literal stop and
handoff language can make it end an autonomous turn at an inline skill seam.
Apply three narrow, cross-model-safe prompt changes: replace false stop/return
boundaries with explicit continuation, make every autonomous Work route
question-free at delegation consent, and keep host-review mechanics cold until
the host backend is selected.

This is a surgical retune, not a Compound-style corpus rewrite. Preserve
machine-readable markers, required stages, deterministic safety gates, real
subagent/process boundaries, and Pilot/Land single-tick terminal contracts.

## Architecture & Data Models
<!-- scope: technical -->

The change stays in skill prose, prose-contract tests, reached-path fixtures,
the generated Codex mirror, changelog/docs truth surfaces, and downstream
flow-next.dev documentation. No flowctl runtime, CLI, schema, receipt shape,
configuration key, or plugin-version manifest changes are expected.

Canonical Claude skill files remain the source of truth. `scripts/sync-codex.sh`
generates the Codex mirror and must run twice to prove idempotence.

## API Contracts
<!-- scope: technical -->

No public command, flag, configuration key, receipt field, verdict enum, or
runtime API changes.

The prose contracts become:

- A conditional reference load says to read/execute the reference and continue
  to the named phase; it never labels the inline transition as `STOP`.
- An active backend workflow carries its verdict into the shared fix loop and
  continues immediately; it does not "return" to a fictional caller.
- Work treats `FLOW_AUTONOMOUS=1` and parsed `mode:autonomous` as headless at
  delegation consent. Without persisted consent, delegation stays off and the
  standard in-session Work path continues.
- Root review skills retain host recognition, bare-only `host` grammar, a
  concise fresh/read-only invariant, shared fix-loop logic, and shared status
  ownership. Host-specific mechanics live only in selected `workflow-host.md`.

## Edge Cases & Constraints
<!-- scope: technical -->

- Keep terminal `NEEDS_HUMAN`, retry-cap, Pilot, Land, and Ralph boundaries.
- Keep real worker/subagent returns and subprocess receipt boundaries.
- Keep exact verdict tags, field names, output paths, sentinel values, and
  prompt templates unless a deliberate continuation wording change requires a
  pinned-hash rationale.
- Autonomous consent suppression must not persist consent, widen sandbox
  authority, or alter interactive consent behavior.
- Host routing must fail closed when no cross-family pin exists.
- Completion-review status must be written exactly once through the existing
  shared owner.
- Do not relax Plan's SHORT scout floor in this workstream.
- Preserve unrelated changes in other worktrees and the concurrent fn-140
  branch.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Every inline forced-reference site in Pilot and Work replaces
  `GATE ACTIVE — STOP` / `STOP and read` framing with an explicit
  read-execute-continue instruction, while the default-off path and fail-open
  activation behavior remain unchanged.
- **R2:** Review backend workflow seams replace "return verdict/control to
  caller/shared loop" framing with explicit continuation into the existing
  shared fix loop; genuine terminal/runtime boundaries remain unchanged.
- **R3:** Work delegation consent classifies Ralph, receipt, `FLOW_AUTONOMOUS=1`,
  and parsed `mode:autonomous` as headless; absent persisted consent disables
  delegation and continues standard Work without asking.
- **R4:** Interactive Work delegation consent remains unchanged and accepted
  consent retains the existing persisted sandbox/config behavior.
- **R5:** Impl-review and completion-review root `SKILL.md` files contain only
  the minimal host routing/invariant surface; selected `workflow-host.md` files
  remain self-contained for cross-family selection, read-only dispatch,
  receipts, re-review, and fail-closed behavior.
- **R6:** Host completion-review status ownership is unambiguous and writes
  terminal status exactly once through the existing shared status step.
- **R7:** Prose-contract and reached-path tests prove host selection loads only
  `workflow-host.md`, other backends keep it cold, autonomous consent never
  asks, and forbidden false-seam phrases do not regress at inline transitions.
- **R8:** Canonical and generated Codex skill trees remain semantically aligned;
  `scripts/sync-codex.sh` is idempotent across two consecutive runs.
- **R9:** Focused suites, the full parallel test gate, pinned Ruff 0.16.0, and
  relevant smoke/reached-path checks pass.
- **R10:** Repo `CHANGELOG.md` and flow-next.dev user-facing truth surfaces are
  updated under Unreleased without a plugin version bump.
- **R11:** After merge, provide a self-contained prompt to the agent on the
  concurrent branch describing the new main commit, overlapping paths,
  verification performed, and instructions to inspect/rebase rather than
  blindly overwrite.

## Boundaries
<!-- scope: business -->

- No broad prompt-corpus deletion.
- No model-specific fork or feature flag.
- No Plan scout-floor reduction.
- No runtime Python change unless implementation proves a prose-only contract
  cannot be enforced; stop and report before expanding scope.
- No release/version bump.

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
<!-- scope: business -->

The observed Opus 5 behavior and upstream Compound Engineering evidence point
to false control-transfer language, not an inability to execute the underlying
work. Small wording changes remove that ambiguity without reducing workflow
coverage for other models.

### Implementation Tradeoffs
<!-- scope: technical -->

Choose explicit forward-motion wording over deleting stages or guards. Choose
selected-reference routing over another copy of host-backend rules. Treat the
autonomous consent mismatch as a contract bug and preserve interactive consent.
Behavior claims require existing reached-path and test evidence; do not infer a
percentage improvement from one clean run.

## Strategy Alignment

- Ralph/autonomous mode: removes question and false-halt paths while preserving
  typed terminal outcomes.
- Cross-platform parity: canonical changes regenerate and validate the Codex
  mirror; Cursor/Droid/Grok continue consuming canonical prose.
- Self-improving through normal work: adds regression coverage and records the
  prompt-retune rationale under Unreleased.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest -q \
  test_codex_delegation_gates test_skill_prose_diet \
  test_work_reached_path_routes test_host_review_backend \
  test_pilot_backlog_mirror_safety test_prompt_text_pinned

./scripts/sync-codex.sh
./scripts/sync-codex.sh

python3 scripts/run_tests_parallel.py
uvx ruff@0.16.0 check .
```

## Requirement coverage

| Requirement | Task |
|---|---|
| R1, R2, R7-R9 | TBD via `/flow-next:plan` |
| R3, R4, R7-R9 | TBD via `/flow-next:plan` |
| R5-R9 | TBD via `/flow-next:plan` |
| R10, R11 | TBD via `/flow-next:plan` |
