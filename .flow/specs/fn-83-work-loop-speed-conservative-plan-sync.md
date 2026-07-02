# fn-83 Work-loop speed: conservative plan-sync gate + worker anchor bundle (zero quality loss, eval-proven)

## Goal & Context

`/flow-next:work` is the hottest loop in flow-next and its wall-clock is dominated by serial machinery around the worker, not by the worker's re-anchor. Measured on the fn-81/fn-82 runs (2026-07-02): plan-sync was spawned unconditionally after every task and returned "no drift, no edits" **3/3 times** at ~70-90k subagent tokens and several minutes each; the worker assembles its anchor through many separate flowctl calls + file reads (round-trip latency, not information value).

**Hard constraint (user-set): ZERO quality loss, PROVEN by an eval set before ship — not asserted, not gathered-in-production-later.** Re-anchoring is a core flow-next tenet — fresh worker context puts exactly the relevant state in the smart zone of the context window. This spec must NOT reduce what the worker knows, and must NOT skip any plan-sync that could have found drift. Speed comes from (a) not dispatching a judgment agent when a deterministic probe can PROVE there is no judgment to make, and (b) delivering the same anchor information in fewer round-trips. Both changes ship ONLY behind their eval proof (methodology: `agent_docs/optimizing-skills.md` — ground-truth corpus, baseline-first, keep-iff-held).

Explicitly deferred to a future spec: parallel disjoint-task execution, review pipelining (structural, higher risk).

## Architecture & Data Models

**1. Gate eval harness — the centerpiece (`optimization/plan-sync-gate/`).**

Ground truth is the REAL plan-sync agent's verdict, not our intuition. The harness holds a frozen corpus of completed-task scenarios, each a reproducible repo state (fixture repo or pinned git state of this repo) with: parent spec, completed task + its diff/evidence, downstream todo tasks. Two populations:

- **Drift-POSITIVE scenarios (constructed, ≥6):** every drift shape we can name — (a) API/function rename consumed by a downstream task's Investigation targets; (b) **deviation-only drift**: implementation changed approach with ZERO downstream file overlap (only catchable via the worker deviation flag); (c) acceptance-semantics staleness (implementation makes a downstream acceptance criterion wrong); (d) file rename/move that a downstream `**Files:**` lists; (e) cross-spec drift (`planSync.crossSpec=true`, other spec's task references the changed API); (f) shared-contract change referenced only in downstream prose, not Files lists.
- **Drift-NEGATIVE scenarios (replayed from real history, ≥6):** the actual fn-81.1/.2/.3 and fn-82.1/.2/.3 post-task states reconstructed from this repo's git history — runs where the real plan-sync verifiably returned no-drift.

**Ground-truth pass:** run the REAL plan-sync agent (frozen prompt, model held constant, per optimizing-skills.md "subagent-reads-prompt" mechanic) on every scenario; record edit/no-edit verdict per scenario (N≥2 runs on any scenario where the verdict wobbles; a wobbling drift-negative gets reclassified positive — ambiguity counts as drift). This table IS the answer key, committed to the harness.

**Probe eval (the merge gate):** run `flowctl plan-sync-probe` (deterministic, 1 run) on every scenario. Required result: **false-skip count == 0** (probe says skip on a scenario where ground truth is edit) across the ENTIRE corpus — a single false skip fails the build and the probe design iterates (tighten the lattice) until zero. Secondary metric (efficiency evidence, no gate): skip-rate on the drift-negative population — target ≥80%, report actual. `results.tsv` rows per the standard ratchet format; probe iterations logged kept/discarded.

**2. Conservative plan-sync gate (flowctl plumbing + skill gating).**

`flowctl plan-sync-probe <completed-task-id> --json` → `{decision: "spawn"|"skip", facts: {...}}`, purely mechanical:
- **Overlap fact (over-approximate):** files touched by the completed task (union of `git diff --name-only` across evidence commits + worker-reported files) ∩ every downstream todo task's referenced paths (its `**Files:**` list, `## Investigation targets` paths, any path-shaped token in its body; basename AND path-prefix matches count). `planSync.crossSpec=true` ⇒ downstream = todo tasks of ALL open specs.
- **Deviation fact:** mandatory worker terminal line `PLAN_DEVIATION: yes|no` (yes = any notable deviation from the task spec's approach/files; worker.md instructs "unsure ⇒ yes"). Missing ⇒ yes.
- **Decision lattice (fail-open):** `skip` ONLY when (no overlap) AND (`PLAN_DEVIATION: no`) AND (probe ran clean) AND (every downstream task had parseable path refs — a task with none cannot be proven disjoint ⇒ spawn). Anything else ⇒ spawn. Probes contain NO pipelines (capture rc-checked, parse separately — fn-82 gate-skeleton rule).

Config `planSync.gate = off | shadow | on`. **Default `on` — justified by the eval proof landing in the same PR** (see Decision Context). `shadow` retained as an observability mode (probe logs would-skip/would-spawn, always spawns) for users who want local evidence on their own repos; `off` = pre-fn-83 behavior. In ALL modes work's final summary carries a per-task `plan-sync:` slot (`spawned (reason) | skipped (proof) | shadow: would-…`) — a skipped sync is always visible, never silent.

**3. Worker anchor bundle + its eval.**

`flowctl anchor <task-id> [--json|--md]` emits ONE deterministic payload: full task spec body; parent spec sections filtered to the task's `satisfies` R-IDs plus always-included `## Goal & Context` and `## Boundaries`; dependency tasks' ids/titles/done-summaries; branch + `git status --porcelain` summary; status fields. Verbatim sections — the bundle never summarizes.

Two-part proof, both merge gates:
- **Deterministic superset check:** on fixture specs/tasks, every artifact worker.md Phase 1 currently instructs reading is present verbatim (or strictly richer) in the bundle. Committed test.
- **Comprehension-equivalence eval (`optimization/worker-anchor/`):** on ≥3 frozen real tasks (varied size), a read-only subagent answers K binary anchor-comprehension questions (state the acceptance criteria ids; name the files to touch; state the boundaries; state dep status; name the relevant R-IDs' requirements) twice — once given ONLY the bundle, once given ONLY the status-quo anchor reads. Required: bundle score ≥ status-quo score on every question set. Any miss ⇒ bundle content iterates until equivalence.

worker.md Phase 1 then uses the single anchor call and explicitly retains read-more freedom (bundle is a floor, not a ceiling).

## API Contracts

- `flowctl plan-sync-probe <task-id> --json` → `{"decision": "spawn"|"skip", "facts": {"touched": [...], "overlaps": [{"task": id, "path": p, "match": "exact|basename|prefix"}], "deviation": "yes"|"no"|"missing", "unparseable_downstream": [ids], "cross_spec": bool}, "mode": "off|shadow|on"}`. Nonzero exit on any internal error; the skill treats nonzero as `spawn`.
- Worker terminal-line grammar addition: `PLAN_DEVIATION: yes|no` (host parses; missing ⇒ yes). Additive.
- `flowctl anchor <task-id> --json|--md` — pure read, deterministic, never mutates.
- Config key `planSync.gate` (default `on`); documented adoption note for cautious users: set `shadow` to observe first.
- Harnesses: `optimization/plan-sync-gate/` and `optimization/worker-anchor/` follow the standard layout (README, answer key/evals, scenarios, results.tsv).

## Edge Cases & Constraints

- Ground-truth ambiguity: any scenario where the real plan-sync agent's verdict is unstable across runs is classified drift-POSITIVE (ambiguity = drift for gating purposes).
- Renames/deletes count as touches on BOTH old and new paths. Path matching tolerates backticks, `path:12-40` suffixes, relative/absolute forms.
- Cross-spec enumeration failure ⇒ spawn. `.flow` unreadable ⇒ spawn. Everything degrades to today's behavior, never past it.
- Anchor bundle on huge specs: no truncation — zero-loss beats tidy; worker context is fresh.
- Ralph/autonomous: identical behavior; gate decisions ride receipts, never prompts.
- Corpus realism: drift-negative scenarios are REAL history replays, not synthetic look-alikes; drift-positive constructions each map to a named real-world drift shape.
- Codex mirror regenerated (worker/work skill edits); flowctl shared.

## Acceptance Criteria

- **R1:** `optimization/plan-sync-gate/` harness committed: ≥6 constructed drift-positive + ≥6 history-replayed drift-negative scenarios, real-agent ground-truth answer key (wobble rule applied), README documenting reproduction.
- **R2:** Probe achieves **zero false skips** on the full corpus (hard merge gate); results.tsv records every probe iteration (kept/discarded lattice changes).
- **R3:** Skip-rate on the drift-negative population reported (target ≥80%; actual number in the PR — a lower number ships with rationale, a false skip never ships).
- **R4:** `flowctl plan-sync-probe` implements the fail-open lattice; unit tests cover every lattice arm (overlap / deviation / missing-line / probe-error / unparseable-downstream / cross-spec-failure ⇒ spawn; proven-disjoint + no-deviation + clean-run ⇒ skip); no pipelines in probe blocks.
- **R5:** Worker emits mandatory `PLAN_DEVIATION: yes|no` (missing ⇒ yes; "unsure ⇒ yes" instruction); host bridges it into the probe.
- **R6:** `planSync.gate` config (`off|shadow|on`, default `on`); per-task `plan-sync:` summary slot present in all modes; shadow mode logs would-decisions while always spawning.
- **R7:** `flowctl anchor` implemented; deterministic superset test green; comprehension-equivalence eval green (bundle ≥ status-quo on every question set, ≥3 real frozen tasks) — both committed under `optimization/worker-anchor/` + tests.
- **R8:** worker.md Phase 1 uses the single anchor call, retains read-more freedom, and no anchor content is summarized anywhere (asserted by the superset test).
- **R9:** Measured evidence in the PR: anchor round-trip count before/after; gate corpus results table (false-skips=0, skip-rate); at least one real multi-task work run on this repo with the gate `on`, its `plan-sync:` slots shown.
- **R10:** Mirror regenerated; smoke (non-repo cwd) + full pytest green; CHANGELOG under `## Unreleased`; no version bump (batched).
- **R11:** Docs: `docs/flowctl.md` (both commands + config key), architecture note on the gate's eval-proof requirement; `optimizing-skills.md` gains a pointer to the two new harnesses.

## Boundaries

- NO parallel task execution, NO review pipelining, NO review-backend changes (future spec).
- NO changes to plan-sync's own prompt/behavior when it runs (that is fn-85 Tier B).
- NO summarizing/paraphrasing of anchor content; the re-anchor tenet is inviolable.
- The gate may never ship (even behind config) without R2's zero-false-skip proof — if the corpus defeats the probe design, the outcome is "gate not shippable, evidence attached", not a weakened corpus.

## Decision Context

User rejected the earlier shadow-first design ("prove there is no quality loss with an eval set") — production shadow logging is evidence-later; the ratchet methodology demands evidence-first. So the eval harness moved from validation garnish to the centerpiece and merge gate: ground truth = the real plan-sync agent's verdicts on a frozen corpus (the same real-backend-in-the-loop pattern as the fn-74 review-prompt harness), and the probe iterates under a hard zero-false-skip requirement. With that proof in the PR, defaulting to `on` is justified (shipping default-shadow would discard the proof we just paid for); `shadow` stays for per-repo observability since our corpus proves the probe on THIS repo's shapes while the fail-open lattice provides the structural guarantee everywhere else. Deviation-only drift (scenario b) is the reason the worker flag exists and the reason file-intersection alone was never sufficient; ambiguity-counts-as-drift keeps the answer key honest. The anchor bundle gets the same treatment (comprehension-equivalence eval, not just a file diff) because "same files present" does not prove "worker equally informed" — the eval does.
