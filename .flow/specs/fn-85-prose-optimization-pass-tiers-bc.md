# fn-85 Prose optimization pass, Tiers B+C: scenario-guarded conductor trims + time-boxed small-skill sweep

## Goal & Context

Companion to fn-84 (Tier A artifact skills). The remaining fleet splits into two honest classes where a per-mutation eval loop would be theater:

- **Tier B — behavior-trace skills** (`pilot`, `land`, `work`, `tracker-sync`, `resolve-pr`): their "output" is a trace of gates fired, verdict lines, receipts, and state transitions — not a judged artifact. The meaningful guard is a SCENARIO/STATE-MATRIX fixture (the fn-82 pattern: execute the gate blocks across default/on/probe-error/parse-error states in a scratch repo) plus conservative in-place trims. Frozen-input prose evals cannot see what matters here.
- **Tier C - small skills** (<~6k always-loaded: `deps`, `sync`, `map`, `memory-migrate`, `setup`, `ralph-init`, `drive`, `export-context`, `rp-explorer`, `worktree-kit`, `flow-next` core): loop overhead exceeds any possible win. One time-boxed manual pass each, reviewed, no harness. **`prime` dropped from Tier C (fn-92 resolution 16):** fn-92 rebuilt prime into a large multi-reference skill (SKILL.md + four reference files + `pillars.md`), so it is no longer a sub-6k small skill; this spec depends on fn-92 (`depends_on_epics`) and prime is out of the Tier-C sweep - any prime prose work belongs to fn-92 / a dedicated pass, not here.

**Hard constraint (user-set): zero quality loss.** For Tier B that means: machine-parsed grammars frozen, every trimmed workflow proven behavior-equivalent on its scenario matrix, and anything ambiguous left untouched. For Tier C: trim only what is provably dead or redundant; when in doubt, skip.

## Architecture & Data Models

**Tier B per-skill shape:**
1. Inventory the skill's CONTRACTS: terminal-line grammars (PILOT_VERDICT, PLAN_DEVIATION, receipts), gate conditions, mandatory summary slots, state files. These are frozen surfaces.
2. Build/extend a scenario matrix: for each gate/branch, a scratch-repo execution proving the branch fires (or stays silent) exactly as before the trim — extending the gate-state tests fn-82 established (pilot qa gate, work bridge gate). land + tracker-sync matrices cover their who-wins/merge-evidence/defer arms via existing fixtures (status-sync S-A…S-G oracles are already host-exercisable — reuse, never rewrite).
3. Conservative trims only: verbose rationale collapse, duplicate-explanation removal, dead-branch prose; imperatives and tables stay put (proximity + repetition rules from fn-84 bind here too).
4. Gate: scenario matrix green pre/post + smoke + pytest + rp impl-review per task.

**Sequencing dependency:** `work`/`worker` prose changes land in fn-83 (gate slot, PLAN_DEVIATION line, anchor call) — Tier B's work task MUST run after fn-83 merges (dep recorded), or it trims a moving target.

**Tier C shape:** one task sweeping all small skills; per skill a time-boxed pass (dead prose, stale refs, verbose rationale) with an explicit "skipped — nothing provably safe" outcome allowed; single rp review over the combined diff.

**Shared closeout:** `agent_docs/optimizing-skills.md` gains the tier taxonomy (A: artifact-eval loop / B: scenario-guarded / C: time-boxed manual) as the standing method for future prose work; `optimization-log.md` rows for every Tier B trim (kept/discarded) and a single Tier C summary row.

## API Contracts

Skill-markdown-only. FROZEN surfaces (any experiment touching one is invalid): pilot verdict grammar + strike ledger lines; work's 4-state `Tracker sync:` slot + `PLAN_DEVIATION` + worker/plan-sync dispatch prompts' field names; land's ledger/receipt fields + merge command shape; tracker-sync receipts/defer + who-wins rule ids (R-IDs, S-fixtures); resolve-pr's GraphQL reply/resolve flow + 2-cycle escalation bound. sync-codex mirror regenerated once per landed task.

## Edge Cases & Constraints

- land is deliberately verbose in places as an autonomous-merger safety contract (its Forbidden list, gate tree) — those blocks are quality-load-bearing; trims there need explicit reviewer sign-off, default keep.
- tracker-sync adapter references are on-demand (not always-loaded) — lowest priority; only always-loaded SKILL/steps prose is in scope.
- resolve-pr was surveyed clean twice — expect small/no wins; a near-empty diff with "nothing safe to trim" is a valid outcome (zero-loss beats forced savings).
- Any Tier B skill whose scenario matrix cannot be made trustworthy in budget: leave the skill untrimmed and log it — same no-weak-guard rule as fn-84.
- Ralph/autonomous paths must be exercised in the matrices (the trace differs from interactive).

## Acceptance Criteria

- **R1:** Scenario matrices exist (new or extended) for all five Tier B skills, executed green BEFORE and AFTER each trim; committed where the fn-82 gate tests live.
- **R2:** Zero changes to frozen surfaces (grep + review audit against the API-contract list).
- **R3:** Tier B trims are behavior-equivalent by matrix proof; every kept/discarded trim logged in optimization-log.md.
- **R4:** work-task ordering: executed only after fn-83 is merged (dep recorded on the task).
- **R5:** Tier C sweep completed within its time-box; per-skill outcome recorded (trimmed N tok | skipped-with-reason); combined diff rp-reviewed.
- **R6:** optimizing-skills.md documents the A/B/C tier taxonomy as standing method.
- **R7:** Net effect table in the PR (per skill: always-loaded tokens before/after or "unchanged").
- **R8:** Mirror regenerated; smoke + full pytest green; CHANGELOG under `## Unreleased`; no version bump (batched).

## Boundaries

- Tier A skills OUT (fn-84); review skills OUT (fn-74 harness owns their rubrics).
- No structural moves, no new gates/references (fn-82 territory), no flowctl changes beyond none.
- No trims to land's safety contracts or tracker-sync rule tables without explicit review sign-off — default keep.
- Adapter reference deep-dives OUT (on-demand files; negligible per-run cost).

## Decision Context

The tier split exists because eval fidelity, not ambition, is the binding constraint: pretending a frozen-input prose eval can guard pilot's strike ledger would launder regressions as "passed" — the opposite of the zero-loss mandate. Scenario matrices are the guard that actually observes what these skills DO; fn-82 already proved the pattern (gate-state tests caught nothing because the moves were safe — and that "nothing" was the proof). Tier C's time-box + skip-allowed rule encodes that on sub-6k skills the downside of a bad trim exceeds the upside of any trim; forced savings are how quality leaks. Sequencing after fn-83 for the work task avoids baselining prose that fn-83 is about to rewrite.
