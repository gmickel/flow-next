---
satisfies: [R6, R9]
---

## Description

The core bet: the agentic 3-way body merge + scoped-conflict surfacing, behind the .2 orchestration, validated over a real .3 Linear round-trip. **This is the spec's early proof point** — if it over-surfaces false conflicts or loses data, re-evaluate the merge-base format + translation approach before building .6/.7.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-tracker-sync/references/body-merge.md` (+ a steps hook in .2's orchestration).

## Approach

- **3-way merge:** base (`lastSyncedAt` snapshot from .1) vs flow-side vs tracker-side. **Deterministic pre-reduction first** (only one side changed → auto-apply; both byte-identical → no conflict) so the agent only judges genuine both-diverged cases — kills false-conflict over-surfacing. **Structural verification gate** before write-back: no section silently dropped; non-conflicting additions from both sides present.
- **Format translation flow↔tracker (R6):** structured spec / R-IDs ↔ free-form issue body; idempotent for unchanged content (flow→tracker→flow = no churn). tracker→flow folds free text into the right flow sections and **never invents R-IDs / source-tags** (a PM literally typing "R17:" in Linear = prose, not promoted).
- **First-sync / no-base bootstrap (R6):** flow-first push with no base → fast-forward projection, never conflict, snapshot after. Tracker-first link → seed base from the current tracker body, first pass pull-only, then snapshot.
- **Echo-loop fence (R6):** post-push tracker content hash recorded (.1); on next pull a hash match = flow's own echo → no-op, not a phantom conflict.
- **Scoped conflict (R9):** only a genuine contradiction (both sides rewrote the same content to mean different things) surfaces — scoped to the section, never the whole body, never a silent overwrite. Interactive: show merged body for confirmation before write. Autonomous: confident merges proceed; genuine conflict (incl. `always-ask` tiebreak) queues to the .1 deferred sink (R11), never blocks.
- **No state advance on failure:** state (`lastSyncedAt`, merge-base) is written ONLY after a fully successful reconcile + write-back. A failed/errored fetch or write (404, transport error, partial batch) leaves prior state intact and emits an `errored`/`queued` receipt — never a half-advanced base. Batch sync is item-level: one item's failure doesn't block or corrupt the others.
- This is a direct application of CLAUDE.md "agentic vs deterministic": the agent owns the merge judgment; flowctl owns the deterministic snapshot/enumerate/receipt. Do NOT build a deterministic fallback merge engine.

## Investigation targets

**Required:**
- the .1 merge-base schema + deferred sink + sync receipt
- the .2 orchestration skeleton + adapter interface
- the .3 Linear transport (round-trip already proven)
- `CLAUDE.md` — "Architecture: agentic vs deterministic" rule + anti-pattern list

## Acceptance

- [ ] 3-way merge over a real Linear round-trip: non-conflicting two-sided edits both survive (PM goal edit in Linear + dev AC edit in flow → both preserved) [R6]
- [ ] Format translation idempotent for unchanged content; tracker free-text folds into correct flow sections; no invented R-IDs / source-tags [R6]
- [ ] No-base bootstrap: flow-first → fast-forward, never conflict; tracker-first link → base seeded from issue, first pass pull-only [R6]
- [ ] Echo-loop fence: a push immediately followed by a pull is a no-op, not a phantom conflict [R6]
- [ ] Structural verification gate runs before any write-back (no dropped section; both sides' non-conflicting additions present) [R6]
- [ ] State (`lastSyncedAt`/merge-base) advances ONLY on a fully successful reconcile; a failed/errored/404 sync leaves prior state intact + emits an `errored` receipt; batch failures are item-level [R6]
- [ ] Genuine conflict surfaces scoped to one section — fixture proves a one-section contradiction does NOT surface a whole-body diff; interactive confirm before write-back [R9]
- [ ] Autonomous mode: confident merges proceed; genuine conflict (incl. `always-ask`) queues to the deferred sink; never blocks [R9]

## Done summary
Implemented the agentic 3-way body reconciliation for the flow-next-tracker-sync skill (R6/R9): a new references/body-merge.md with deterministic pre-reduction (echo/byte-identical/one-side-changed auto-cases), an agentic both-sides-diverged merge, flow-structured<->tracker free-form format translation (idempotent; never invents R-IDs/source-tags on a tracker->flow fold), a structural verification gate before write-back, scoped genuine-conflict surfacing (one section, never whole-body — interactive confirm vs Ralph queue), no-base bootstrap, an echo fence, and state-advances-only-on-success with item-level batch failure. steps.md Phase 3/4 + SKILL.md now delegate the reconcile body hooks to it (no lingering [stub -> fn-52.4]). Four worked fixtures (A-D) serve as runnable oracles; the strictly-live Linear round-trip is deferred to the post-PR smoke phase. impl-review (rp): SHIP first pass, 0 introduced findings.
## Evidence
- Commits: faa3748f24ad6a9d2f82fbee1216e883031372b6
- Tests: bash plugins/flow-next/scripts/ci_test.sh (58 passed / 0 failed), python3 -m unittest discover -s plugins/flow-next/tests (788 passed, 2 skipped), flowctl validate --spec fn-52-tracker-sync-bridge-project-flow-specs (valid: True), markdown fence-balance + cross-ref link resolution (0 broken), impl-review rp backend: SHIP (first pass, 0 introduced findings; R6 + R9 covered)
- PRs: