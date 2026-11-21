# Efficiency audit 2026-11 wave 3: eval-gated wall-clock and token levers

## Goal & Context

The 2026-11 efficiency audit identified high-leverage wall-clock and token reductions that touch loaded instruction placement, review topology, default model effort, scout dispatch, or always-loaded system-prompt snippets. Earlier studies showed that moving instruction text across files or changing review rules can shift behavior even when every link stays reachable, so none of these changes may ship on code review alone.

This spec defines the pre-registered evaluation queue for the new 2026-11 levers and reconciles the still-open items in `fn-260` (audit wave 6), where two items (`fn-260` R4 and R6) are already shipped at v9.18.0 and two (`fn-260` R2 and R9) have drifted worse since v9.5.0. Each item is evaluated under the maintainer's eval methodology (`METHODOLOGY.md`, `lib/evalkit.py`) with model, harness, and effort held constant, a written `PREREGISTER.md` before any draw, and KEEP, PARK, negative, and INCONCLUSIVE outcomes retained. A change ships only on a KEEP.

## Architecture & Data Models

No product code changes until an individual study records a KEEP. Study harnesses, fixtures, and raw draw artifacts live in the separate eval repository, never in this repository. Each kept change ships in its own small commit or follow-up spec with `./scripts/sync-codex.sh` regenerated. Standing criteria G1, G2, and G4 apply.

## Edge Cases & Constraints

- Silence or omission must never win a cost or wall-clock metric: every study scores correctness, recall, or coverage alongside time, calls, and tokens.
- Wall-clock verdicts run sequentially on an otherwise idle machine with host load recorded per draw.
- Studies of Claude Code skill behavior drive the real terminal UI (not print mode alone) when system prompt or interactive turns are under test.
- Representative external repositories are used for repo-context-sensitive skills, not only `flow-next`.
- Previously falsified or parked directions are out of scope and must not be reopened without a new mechanism: big-bang spec-end review, delta-scoped re-review, deps-closure plan-sync, `.ignore` exclusion for `.flow/`, generic wording-only prose rewrites, and replacing single-task inline work with workers.

## Acceptance Criteria

- **R1:** Pre-registered study on Phase 4 `quality-auditor` overlap with `impl-review`: measure defect escape rate, wall clock, and cost when Phase 4 skips `quality-auditor` (or runs standards-only) on specs where `REVIEW_MODE != none` and every task already passed `impl-review` (cutting 5 reviews to 3 on large single-task specs), keeping full 2x Opus audit for `REVIEW_MODE=none` and multi-task cross-task seams. Errors: any escaped defect caught by baseline `quality-auditor` on reviewed specs blocks shipping.

- **R2:** Pre-registered study on review panel sizing and Claude reviewer default effort:
  - Test anchoring a concrete 1-draw vs 3-draw threshold (diff size/file count outside sensitive paths) on `flow-next-impl-review` against the current prose-only rule.
  - Benchmark `claude` review backend default effort `claude-opus-5-5:medium` against current `high` on the slop testbed and real specs (actionable defect recall, false claims, wall clock).
  Errors: a recall loss beyond the pre-registered bar parks the arm; no knob is added to product config.

- **R3:** Pre-registered study on lean resumed re-review prompts (`two_phase_resume`): test omitting the repeated ~11 KB base prompt on resumed `codex` re-review turns (keeping ratchet, updated range/files, and verdict reminder) and extending `two_phase_resume` to `claude`, scoring verdict-tag compliance, finding format, and convergence parity. Errors: any resume-fallback failure or dropped verdict tag blocks shipping.

- **R4:** Pre-registered study on `gpt-6.2-sol:medium` non-actionable notes: measure whether the ~3.83 non-actionable notes/review observed in `reviewer-model-2026-11` trigger unnecessary extra fix and re-review rounds in live `flow-next`, and if so whether a concise triage rule cuts round count without dropping real fixes. Errors: baseline showing zero extra rounds ends as NO CHANGE (no prose added).

- **R5:** Pre-registered study on Cursor small-defect route literalism: test adding a narrowing sentence in `route-matrix.md` permitting small local defects to take a direct change on Cursor and Claude Code, scoring small-bug wall clock and cost alongside hard-bug verification proof (ensuring hard bugs still run full defect proof). Errors: any hard-bug verification regression parks the change.

- **R6:** Pre-registered studies on proximity-sensitive file splits and gated loading (excluded from Wave 1 for safety):
  - Split `flow-next-refine/SKILL.md` (21.6 KB) into a ~5 KB router plus `interview.md` (-13.5 KB on `--scope=research`).
  - Route bare `host` `impl-review` directly to `workflow-host.md` bypassing `other-paths.md` (-13.5 KB, -2 Reads), and split `optional-phases.md` (22.1 KB) per flag (-25 to -35 KB).
  - Gate `flow-next-features/maintain.md` Phase 6 (-7.2 KB on clean passes), split consumer `feature-entry-contract.md` (-9.8 KB on QA/drive), split `drive/references/cua-sandbox.md` (-10.3 KB on attended native), move 12.5 KB of worked fixtures out of `tracker-sync` runtime refs, gate `audit` `phases.md` and Phase 5-6 (35.8 KB), and collapse `backlog-mode.md` Phase 1/1.5 and 2/1.6.
  Errors: any branch that reaches a moved rule without reading its target file counts as a study failure, not a KEEP.

- **R7:** Pre-registered studies on scout, planning, and rolling-scheduler latency:
  - Remove duplicate `gh search code`/`gh api` sweeps from `practice-scout` (and narrow `docs-scout`), inline `memory search` in `refine --scope=research`, skip `spec-scout` when zero other open/live specs exist, and test backgrounding web scouts so `flow-gap-analyst` runs as soon as local scouts finish.
  - Test opportunistic first-batch non-blocking measurement in `rolling-scheduler.md` against the current 2 throwaway sleep subagents (-10 to -25 s wall on cold rolling runs).
  Errors: plan DISC/FLOOR parity against sealed keys and rolling-scheduler degradation detection on blocking hosts must not regress.

- **R8:** Pre-registered studies on prompt and always-loaded trims:
  - Trim 5.8 KB of redundant HTML comments from `templates/spec.md` / `flowctl spec skeleton`; compress `model-routing-snippet.md` (1,851 B commented HTML paid on every session) to a compact pointer; collapse `completion-review-prompt.md` double R-ID matrices and triple verdict/tally blocks; test dropping `worker.md`'s `docs/prose.md` read (5.8 KB/worker) and hardcoded TS/PY grep; test batching `features/maintain.md` Phase 2 Explore subagents and viewport scoping in `qa/workflow.md`.
  Errors: spec fidelity, review parse/recall parity, worker test quality, and QA defect recall must hold across all tested arms.

- **R9:** Reconcile `fn-260` (audit wave 6) without duplicating work: mark `fn-260` R4 (worker rare branches) and R6 (rolling workers focused-only) satisfied as already shipped at v9.18.0; update `fn-260` R2/R9 baselines (`auto.md` grew to 55.4 KB; `--goal` wastes ~43.5 KB and `--from-issue` refusals waste ~48 KB); prioritize `fn-260` R1 (skill listing descriptions diet, 11.3 KB to ~6.2 KB), R2+R9 (`auto.md` mode/stage split), R7+R11 (`prime` deterministic inventory + conditional stack/setup blocks), and R14 (`flow` redundant `brief`/re-reads/`plan-vs-no-plan`) alongside R1-R8 above. Errors: no error surface beyond `fn-260`'s own pre-registration rules.

## Boundaries

- No product file edits are authorized by this spec itself; each KEEP ships only after its study concludes and is reviewed.
- No new config keys or opt-in knobs are introduced to hedge an eval outcome (keep one topology per `STRATEGY.md`).
- Items covered by Wave 1 (mechanical + zero-loss prose) and Wave 2 (deterministic CLI/orchestration plumbing) are out of scope here.

## Decision Context

Separating eval-gated items from Waves 1 and 2 keeps zero-risk engineering work moving immediately while enforcing empirical evidence on every change that alters what models read, how reviewers judge, or how routes narrow. Keeping this as a sibling wave spec referencing `fn-260` preserves `fn-260`'s R-IDs without renumbering.

## Strategy Alignment

Directly implements `STRATEGY.md` "Remember the bitter lesson" (evaluate compensating scaffolding against its absence with pre-registered bars and delete on evidence) and "Agent first" (delete machinery and prompt bloat that modern models no longer need).
