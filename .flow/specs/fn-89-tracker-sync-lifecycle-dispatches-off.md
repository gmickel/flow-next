# fn-89-tracker-sync-lifecycle-dispatches-off Tracker-sync lifecycle dispatches off the critical path (background subagents)

## Goal & Context

Every tracker touchpoint today runs INLINE in the host skill: the work loop waits on Linear/GitHub API round-trips between tasks, and — worse for context — the tracker machinery pollutes the host's window. Evidence from the fn-88 run (2026-07-05): each MCP `save_issue` echoed the entire issue body (~10k tokens) back into the HOST context, twice; a body reconcile loads ~13–17k tokens of merge-doctrine refs into the host. The wall-clock cost is seconds per touchpoint; the context cost is the real tax.

The fix is NOT "parallelize everything" — it is **off-the-critical-path + context-isolated**: lifecycle event dispatches execute in a background tracker-runner subagent (own context absorbs the skill refs and MCP echoes; host gets one line back), overlapping the long-pole work (worker runs are minutes; tracker calls are seconds). Two hazards shape the design: per-spec sync-state races (merge-base/lastSyncedAt snapshots must not interleave) and the Phase-5/end-of-run `sync check` audit racing an in-flight dispatch (false MISSING → duplicate retro-fire).

**Scope split:** ceremonies and interactive genuine-conflict resolution STAY inline (they need `AskUserQuestion`; subagents can't block on questions — the documented reason tracker-sync is an inline skill today). Only the event-tagged lifecycle dispatches (capture/interview/plan reconcile, work.firstClaim push, work.done/resolvePr/completionReview/qa comments, makePr reconcile) become forkable — they never ask under the autonomy policy anyway (genuine conflicts queue via `sync defer`).

## Overview & Approach

1. **Tracker-runner dispatch shape.** The calling skill's touchpoint gate (unchanged, deterministic, host-side leaf check) dispatches `skill: flow-next-tracker-sync (operation: <verb> <id>, event: <key>)` to a subagent (Claude `Task`; Codex `spawn_agent`; serial-inline fallback on hosts without subagent dispatch — Copilot/Droid degrade to today's behavior). The subagent runs the tracker-sync skill body for that ONE op: transport calls, receipts, state writes, queueing. It returns a one-line outcome (`pushed|merged|noop|queued|errored + note`).
2. **Two dispatch classes:**
   - **Comment-shaped** (`work.done`, `resolvePr`, `completionReview`, `qa` — append-only, marker-deduped, body/status untouched): **fire-and-forget background**. The loop continues immediately.
   - **State-shaped** (reconcile/push — touches body merge-base, status, links: `capture`, `interview`, `plan`, `work.firstClaim`, `makePr`): **subagent-isolated but AWAITED at the touchpoint** (or per-spec-serialized if a later phase wants overlap) — merge-base snapshot integrity beats latency here.
3. **Per-spec serialization.** At most ONE in-flight tracker op per spec id. The host keeps a tiny in-context ledger of outstanding dispatches (spec id → agent handle); a new dispatch for a spec with an outstanding one AWAITS it first. Ops on different specs parallelize freely. No flowctl locking machinery — the host loop is the serializer (single conductor), matching the "skill owns judgment, flowctl owns plumbing" split.
4. **Pre-audit join.** Before ANY end-of-run `sync check` (work Phase 5, make-pr §5.7), the host awaits ALL outstanding tracker dispatches for the audited spec. The check then reads settled receipts — no false MISSING, no duplicate retro-fire. Retro-fire itself stays exactly one cycle, unchanged.
5. **Autonomy/Ralph unchanged in policy:** the runner inherits the marker family via prompt flags; "ask the human" resolves to `sync defer` (already the rule under RALPH — now uniform for all forked dispatches, interactive included: a forked dispatch that hits a genuine conflict queues + surfaces in the host summary; the HUMAN path to interactive conflict resolution remains a manual `/flow-next:tracker-sync reconcile <id>` run, which stays inline and may ask).
6. **Config leaf (one, opt-out):** `tracker.dispatch` = `async` (default) | `inline`. `inline` restores today's behavior wholesale (support/debug hatch). The leaf gates dispatch MODE only — gating predicates, ops, receipts, event tags, audit are byte-identical in both modes.

## API Contracts

- No flowctl transport changes; no new receipt fields. Receipts/`sync defer`/`sync check` behave identically — only WHERE the tracker-sync body executes changes.
- New config leaf `tracker.dispatch` (`async` default | `inline`), schema default `async`, documented in flowctl.md config table.
- The runner subagent is the EXISTING `flow-next-tracker-sync` skill body driven in fork context with the op/event/spec inputs; no second implementation. Canonical dispatch grammar unchanged: `operation: <verb> <id>, event: <key>`.
- Caller-visible contract: comment-shaped touchpoint gates return immediately after dispatch (outcome line arrives asynchronously and is reported in the host summary); state-shaped gates return after the awaited outcome line.

## Edge Cases & Constraints

- Subagent MCP availability: interactively-authed MCP servers may be absent in headless runs — the runner inherits the same transport-ladder degradation (MCP → GraphQL/env-token → no-op + receipt) the inline path has; no new failure mode.
- A fire-and-forget dispatch that dies (agent error) = an unwritten receipt = caught by the pre-join `sync check` → retro-fire once (the existing backstop becomes the retry path). Comments are marker-deduped so a duplicate retro-fire is harmless.
- Ordering: firstClaim (state-shaped, awaited) always lands before the first done-comment can dispatch — natural ordering preserved without extra machinery.
- The host ledger must survive context compaction: on resume, treat outstanding handles as unknown → run the pre-audit join via `sync check` semantics (receipts on disk are the truth, not the ledger).
- Hosts without background dispatch (Copilot/Droid serial loops): gates detect no-subagent capability and run inline — zero behavior change there.
- Never fork the discovery ceremony, link/unlink ceremonies, or `--dry-run`/manual runs — user-facing interaction lives host-side.

## Quick commands

```bash
# Gate
uvx pytest plugins/flow-next/tests -q
bash plugins/flow-next/scripts/smoke_test.sh   # from OUTSIDE the repo
./scripts/sync-codex.sh

# Config hatch
.flow/bin/flowctl config get tracker.dispatch --json
.flow/bin/flowctl config set tracker.dispatch inline
```

## Strategy Alignment

Active tracks served by this plan:
- **Ralph autonomous mode** — pilot/backlog ticks reconcile every tick; isolating reconcile refs + MCP echoes from the conductor's context directly lowers per-tick token cost (the factory-efficiency readout).
- **Cross-platform parity** — dispatch capability is feature-detected per host; Codex uses spawn_agent, no-subagent hosts degrade to inline.

## Acceptance Criteria

- **R1:** Comment-shaped touchpoints (`work.done`, `resolvePr`, `completionReview`, `qa`) dispatch to a background tracker-runner subagent and the calling loop continues without awaiting the API round-trip; the outcome line is surfaced in the host's end-of-run summary.
- **R2:** State-shaped touchpoints (`capture`/`interview`/`plan` reconcile, `work.firstClaim` push, `makePr` reconcile) run subagent-isolated and are awaited at the touchpoint.
- **R3:** Per-spec serialization: at most one in-flight tracker op per spec id; a second dispatch for the same spec awaits the first. Different specs may run concurrently.
- **R4:** Pre-audit join: every end-of-run `sync check` call site (work Phase 5, make-pr §5.7) awaits outstanding dispatches for the audited spec first; no duplicate retro-fire from in-flight ops (verified by a receipt-timeline assertion in tests where feasible, else prose-contract).
- **R5:** `tracker.dispatch` config leaf (`async` default | `inline`); `inline` restores current behavior byte-for-byte at every touchpoint; documented in flowctl.md.
- **R6:** Ceremonies (discovery, link/unlink), manual runs, `--dry-run`, and interactive genuine-conflict resolution remain inline — never forked; forked dispatches resolve conflicts by queueing (`sync defer`) in BOTH interactive and autonomous modes, surfaced in the host summary.
- **R7:** The runner is the existing tracker-sync skill body (no duplicate implementation); host summary gains outstanding-dispatch reporting; receipts/event tags unchanged; `sync check` semantics unchanged.
- **R8:** No-subagent hosts degrade to inline automatically; Codex mirror renders the dispatch via spawn_agent (sync-codex validation green); smoke + full pytest green; CHANGELOG under `## Unreleased`; no version bump (batched).

## Boundaries

Out of scope: no flowctl tracker transport (flowctl never grows API calls); no changes to body-merge/status/comment semantics; no receipts schema changes; no parallelizing MULTIPLE ops for the SAME spec; no forking of plan-sync (different subsystem, already a subagent); no queue persistence beyond receipts (the disk receipts are the durable truth); no changes to pilot/land verdict grammars.

## Decision Context

"Parallelize everything" was rejected: per-spec sync-state (merge-base pairs, lastSyncedAt) has interleaving hazards, and the measured win isn't concurrency between tracker calls — it's (a) getting seconds of API latency off the work loop's critical path and (b) keeping ~10–17k-token tracker payloads/refs out of the conductor's context (both observed in the fn-88 run, 2026-07-05). Fire-and-forget is confined to append-only marker-deduped comment ops where the existing `sync check` + retro-fire backstop doubles as the retry path; state-shaped ops keep await semantics because a torn merge-base snapshot costs more than the seconds saved. The host-as-serializer (in-context ledger + join points) was chosen over flowctl-side locking: the conductor is already the single dispatcher, and receipts-on-disk remain the recovery truth after compaction. The `inline` hatch exists because background failures are harder to debug live; flipping one leaf reproduces today's behavior exactly.
