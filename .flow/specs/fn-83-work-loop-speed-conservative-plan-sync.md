# fn-83 Work-loop speed: conservative plan-sync gate + worker anchor bundle (zero quality loss)

## Goal & Context

`/flow-next:work` is the hottest loop in flow-next and its wall-clock is dominated by serial machinery around the worker, not by the worker's re-anchor. Measured on the fn-81/fn-82 runs (2026-07-02): plan-sync was spawned unconditionally after every task and returned "no drift, no edits" **3/3 times** at ~70-90k subagent tokens and several minutes each; the worker assembles its anchor through many separate flowctl calls + file reads (round-trip latency, not information value).

**Hard constraint (user-set): ZERO quality loss.** Re-anchoring is a core flow-next tenet — fresh worker context puts exactly the relevant state in the smart zone of the context window. This spec must NOT reduce what the worker knows, and must NOT skip any plan-sync that could have found drift. Speed comes from (a) not dispatching a judgment agent when a deterministic probe can PROVE there is no judgment to make, and (b) delivering the same anchor information in fewer round-trips.

Explicitly deferred to a future spec: parallel disjoint-task execution, review pipelining (structural, higher risk).

## Architecture & Data Models

**1. Conservative plan-sync gate (flowctl plumbing + skill gating).**

New deterministic probe, `flowctl plan-sync-probe <completed-task-id> --json` → `{decision: "spawn"|"skip", facts: {...}}`. flowctl owns facts; the skill owns nothing here — the probe's decision is mechanical:

- **Overlap fact (over-approximate by design):** files touched by the completed task (union of: `git diff --name-only` across the task's evidence commits, and the worker-reported files-changed list) intersected against every DOWNSTREAM todo task's referenced paths — its `**Files:**` list, `## Investigation targets` paths, and any path-shaped token in its body (regex over path-like strings; basename AND path-prefix matches both count as overlap). When `planSync.crossSpec=true`, downstream set = todo tasks of ALL open specs, not just the current one.
- **Deviation fact:** the worker gains a mandatory terminal `PLAN_DEVIATION: yes|no` line (yes = implementation deviated from the task spec's stated approach/files in ANY way the worker judges notable; worker.md instructs "when unsure, yes"). Missing line ⇒ treated as `yes`.
- **Decision rule (fail-open lattice):** `skip` ONLY when (no path overlap) AND (`PLAN_DEVIATION: no`) AND (probe executed without error). Any overlap, any deviation, any probe error, any unparsable input ⇒ `spawn`. Skipping requires proof; spawning never does.

Config: `planSync.gate = off | shadow | on` (default **shadow** on ship; flipping to `on` is the user's explicit act after shadow evidence).
- `off` — today's behavior, always spawn (probe not even run).
- `shadow` — probe runs and its decision is LOGGED (receipt/summary line `plan-sync gate (shadow): would-skip|would-spawn`), plan-sync still ALWAYS spawns. Zero behavior change; collects the evidence that would-skip predictions are always no-drift.
- `on` — skip when the probe proves skip; spawn otherwise. Work's summary reports `plan-sync: spawned (reason)|skipped (proof)` per task — a skipped sync is always visible, never silent.

**2. Worker anchor bundle (flowctl plumbing).**

`flowctl anchor <task-id> [--json|--md]` emits ONE deterministic payload: full task spec body; parent spec sections filtered to the task's `satisfies` R-IDs plus always-included `## Goal & Context` and `## Boundaries`; dependency tasks' ids/titles/done-summaries; current branch + `git status --porcelain` summary; spec/task status fields. worker.md Phase 1 replaces its N discrete anchor reads with one `flowctl anchor` call.

**Superset guarantee (the zero-loss mechanism):** the bundle must contain, verbatim or strictly-richer, everything worker.md's current Phase 1 instructs the worker to read; and the bundle is a FLOOR, not a ceiling — worker.md keeps its freedom (and existing prompts) to Read any additional file it judges relevant. Anchor content is never summarized by the bundle (no paraphrase — verbatim sections).

## API Contracts

- `flowctl plan-sync-probe <task-id> --json` → `{"decision": "spawn"|"skip", "facts": {"touched": [...], "overlaps": [{"task": id, "path": p, "match": "exact|basename|prefix"}], "deviation": "yes"|"no"|"missing", "cross_spec": bool}, "mode": "off|shadow|on"}`. Exit 0 always when readable; any internal error exits nonzero AND the skill treats nonzero as `spawn`.
- Worker terminal line grammar addition: `PLAN_DEVIATION: yes|no` (host parses; missing ⇒ yes). Additive — no existing terminal line changes.
- `flowctl anchor <task-id> --json|--md` → deterministic bundle as above; `--md` is the worker-facing render, `--json` machine form. Pure read — never mutates state.
- Config key `planSync.gate` (default `shadow`); `flowctl config get/set` as usual; schema default documented.

## Edge Cases & Constraints

- **Recall=1 requirement:** a fixture corpus of KNOWN-DRIFT scenarios (real drift shapes: renamed API consumed downstream, changed acceptance semantics, file the downstream task lists, deviation-only drift with zero file overlap) — the probe must return `spawn` on every one. Any false `skip` on the fixtures fails the build. Precision is best-effort (false spawns are just today's behavior).
- Deviation-only drift (worker changed approach but touched only its own files) is caught by the `PLAN_DEVIATION` flag — this is WHY the flag is mandatory and defaults to yes when missing.
- Renames/deletes count as touches on BOTH old and new paths.
- Free-text path matching must tolerate backticks, line-suffixes (`path:12-40`), and relative/absolute forms; when a downstream task has NO parseable path references at all, treat as overlap-unknown ⇒ `spawn` (a task with no Files list can't be proven disjoint).
- Cross-spec: with `planSync.crossSpec=true`, skip requires disjointness across all open specs' todo tasks; if enumeration fails, `spawn`.
- Anchor bundle on huge specs: no truncation — if the filtered sections exceed a sane size, emit everything anyway (zero-loss beats tidy); worker context is fresh and can afford it.
- Ralph/autonomous: identical behavior; gate decisions ride receipts, never prompts.
- Codex mirror: sync-codex regenerates worker/work skill changes; flowctl is shared.

## Acceptance Criteria

- **R1:** `flowctl plan-sync-probe` implemented with the fail-open decision lattice; unit tests cover every lattice arm (overlap/deviation/error/missing-line/cross-spec/no-parseable-refs ⇒ spawn; provably-disjoint + no-deviation ⇒ skip).
- **R2:** Drift-fixture corpus (≥6 scenarios incl. deviation-only and rename drift) — probe returns `spawn` on ALL (recall=1); corpus committed under tests.
- **R3:** `planSync.gate` config with `off|shadow|on`, default `shadow`; `shadow` logs would-skip/would-spawn while always spawning (behavior byte-equivalent to today); `on` skips only on probe-proof; work's final summary carries a per-task `plan-sync:` slot in all modes.
- **R4:** worker emits mandatory `PLAN_DEVIATION: yes|no`; host treats missing as yes; worker.md instructs "unsure ⇒ yes".
- **R5:** `flowctl anchor <task-id>` implemented; superset test proves the bundle contains every artifact worker.md Phase 1 currently reads (fixture spec/task); worker.md Phase 1 uses the single anchor call and explicitly retains read-more freedom.
- **R6:** No reduction of anchor content anywhere — verbatim sections, no summarization (asserted in the superset test).
- **R7:** Measured evidence in the PR: anchor round-trips before/after (call count), and shadow-mode gate log from at least one real multi-task work run on this repo.
- **R8:** Mirror regenerated; smoke (non-repo cwd) + full pytest green; CHANGELOG under `## Unreleased`; no version bump (batched).
- **R9:** Docs: `docs/flowctl.md` (two new commands + config key), work skill docs notes; `planSync.gate` explained with the shadow→on adoption path.

## Boundaries

- NO parallel task execution, NO review pipelining, NO changes to review backends (future spec).
- NO reduction of what plan-sync itself does when it runs (its prompt/behavior untouched here — Tier B prose is fn-85).
- NO summarizing/paraphrasing of anchor content; the re-anchor tenet is inviolable.
- Default stays `shadow` — flipping to `on` is a user decision after evidence, never automatic.

## Decision Context

Probe-not-agent chosen per the repo's own architecture doctrine (flowctl owns deterministic facts; agents own judgment): dispatching plan-sync to conclude "no drift" 3/3 times is paying judgment prices for a set-intersection question. Shadow-default chosen over on-default because the user set a hard zero-quality-loss bar: shadow produces the falsifiable evidence (would-skip vs actual no-drift agreement) before any behavior changes. The deviation flag exists because file-disjointness alone cannot prove no-drift (approach changes are invisible to path intersection) — the worker is the only cheap observer of its own deviation, and fail-open on a missing flag keeps forgetting safe. Anchor bundle is latency/round-trip work only — the information set is deliberately a superset, because the tenet under protection is precision-in-the-smart-zone, not token minimalism.
