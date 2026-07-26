# Tracker determinism C: prose teardown, docs, baselines

## Goal & Context
<!-- scope: business -->

**Spec C of a three-spec batch** (A foundation, B verb surface, C teardown). Depends on **fn-140**. The batch releases together; C is the last one in and the one that makes the win visible.

A and B build and prove the replacement. **C removes what it replaced.** Until C lands, the repo carries both a deterministic implementation and 476,883 characters of prose describing the same operations - which is strictly worse than either alone, because they can drift.

C is deliberately last and gated on B's conformance matrix passing. **The prose is not deleted until the replacement is proven.**

C also carries the honesty work: a prior spec's acceptance criterion is being reversed, frozen optimization baselines are invalidated by design, and a user-facing behavior change needs the docs site updated in the same workstream.

## Architecture & Data Models
<!-- scope: technical -->

### What the skill keeps

After teardown the tracker-sync skill retains **exactly five judgment surfaces**, each named in `SKILL.md` with why it cannot be deterministic:

1. **The MCP rung** - host-agent-visible tools with no shell command; flowctl cannot reach it.
2. **The discovery ceremony** - choosing a project/team is ambiguous, one-time, interactive.
3. **3-way body-merge conflict adjudication** - semantic. Memory `plan-sync-skip-gate-not-viable` records a deterministic gate for a *less* semantic problem that was built, evaluated and killed by its own eval.
4. **Comment content synthesis** - what a lifecycle comment should say.
5. **Recovery routing from a structured flowctl error** - deciding what to do about a `class: conflict` is judgment.

The earlier draft of this batch claimed "exactly four" while its own architecture table listed recovery as agentic. Five is the honest count.

### What the callers keep

**The caller-side gate is retained.** Only transport-ladder and dispatch prose is removed. This is not cosmetic: every flowctl command emits JSON and `inactive` is an error class, so routing a bridge-inactive repo into flowctl would replace silence with output and an extra process, breaking the invariant that a non-tracker repo sees nothing.

One centralized snapshot gate stays per caller. The `perEvent` value to verb mapping (`push` / `reconcile` / `comment`) is **explicitly enumerated**, not deleted along with the dispatch prose. Comment content synthesis is reassigned by name to each calling skill rather than orphaned when `tracker-runner` is deleted.

### What is superseded

**fn-57 R3** states: "flowctl gains **no tracker-mutation code** - all status / comment / link mutations stay agent-driven through the tracker-sync skill on every transport."

This batch reverses it deliberately. Three places assert the old rule in code and prose and must be updated so nothing ships contradicting a live criterion:

- `flowctl.py` `cmd_sync_check` docstring: "NO tracker-mutation code lives here or anywhere in flowctl (R3)"
- `flowctl.py` `list-dep-relations` transport-blind docstring
- `docs/tracker-sync.md`: "flowctl has no tracker transport"

**fn-130's reached-path B1 baselines** for the tracker cluster are invalidated by the prose reduction. That is by design, not a regression, and they are re-frozen with a recorded delta.

## Edge Cases & Constraints
<!-- scope: technical -->

- The codex mirror is generated. Never hand-edit; run `./scripts/sync-codex.sh` **twice** (idempotency) and commit the mirror diff with the canonical change.
- Removing `tracker-runner` touches fourteen calling skills plus the mirror plus `docs/platforms.md`'s Tier-B dispatch text. A dangling reference to a deleted agent is a silent breakage.
- `docs/tracker-sync.md:238` currently states "flowctl has no tracker transport" - a direct future-contradiction, not merely stale phrasing.
- `docs/platforms.md:120` and `:300` describe the `tracker-runner` Tier-B dispatch that no longer exists after this spec.
- Doc-index rows in `README.md`, `plugins/flow-next/docs/README.md`, `docs/teams.md` and `CLAUDE.md` all use "transport ladder" as user-facing vocabulary, which stops being something a user or agent reasons about.
- `agent_docs/optimizing-skills.md` classifies tracker-sync by always-loaded weight; that classification is stale once the prose shrinks.
- Per repo convention, docs-only changes do **not** bump the plugin version, and the CHANGELOG entry is staged under `## Unreleased` - the batch bumps once, at release.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The adapter references and `steps.md` shrink to **transport-shape documentation**. Measured mechanically, not by eye: a test asserts **zero** matches for an executable-invocation pattern (`gh api`, `glab api`, `curl -sS`, `POST /rest/api`) inside bash fences across an enumerated file set, and asserts the summed character count of that set is at least **150,000 below** the baseline recorded in the test itself.
- **R2:** `SKILL.md` names **exactly five** judgment surfaces with the rationale for each.
- **R3:** Lifecycle touchpoints call `flowctl tracker <verb>` directly. The `tracker-runner` agent and `references/tracker-dispatch.md` are removed.
- **R4:** The caller-side gate is **retained**; only transport-ladder and dispatch prose is removed. The `perEvent` to verb mapping is explicitly enumerated, and comment content synthesis is reassigned by name to each calling skill.
- **R5:** Zero dangling references to the deleted agent across all fourteen calling skills, the codex mirror, and `docs/platforms.md`. Asserted by test, not by grep-once-and-hope.
- **R6:** The **bridge-inactive path is byte-for-byte unchanged** after rewiring: one config read, no adapter import, no new output. Verified here rather than in A, because C is what changes the final inactive path.
- **R7:** Every configured `perEvent` value is tested end to end, not just the inactive case.
- **R8:** fn-57's R3 supersession is recorded at all three assertion sites, with a pointer to this batch so a future reader finds the decision rather than a contradiction.
- **R9:** `docs/tracker-sync.md` is rewritten: the Transport ladder section becomes flowctl-owned, the `tracker.resolved` schema and capability degradation are documented, and the "flowctl has no tracker transport" line is corrected.
- **R10:** `docs/flowctl.md` gains a complete `## flowctl tracker` section modelled on the existing `## flowctl sync`, documenting every verb, the result envelope, the `class` enum and the numeric exit codes.
- **R11:** The Jira `apiVersion` default is corrected to **2** in docs, matching the measured behavior that v2 round-trips plain strings byte-exact.
- **R12:** No doc still teaches a reader or agent to reason about a runtime transport ladder. Includes the doc-index rows in `README.md`, `docs/README.md`, `docs/teams.md` and `CLAUDE.md`.
- **R13:** `agent_docs/optimizing-skills.md`'s always-loaded weight classification for tracker-sync is re-measured and updated.
- **R14:** fn-130's tracker-cluster B1 baselines are re-frozen, **enumerating every affected fixture by name** under `optimization/reached-path/fixtures/b1/tracker` rather than treating it as a blanket refresh, with a before/after delta recorded as an artifact in the honest form fn-134 used.
- **R15:** `./scripts/sync-codex.sh` runs twice with the mirror diff committed alongside the canonical change.
- **R16:** The **flow-next.dev docs site is updated in the same workstream**, committed separately in that repo, with `pnpm build` green. This is a user-facing command and behavior change, so in-repo docs alone are insufficient.
- **R17:** A CHANGELOG entry is staged under `## Unreleased`. **No version bump** - the batch bumps once at release, per the repo's batched-release rule.

## Boundaries
<!-- scope: business -->

**In scope:** prose reduction, dispatch removal and caller rewiring, the fn-57 supersession, repo docs, baseline re-freeze, docs site.

**Out of scope:**
- Any behavior change. C removes and documents; it does not alter what the verbs do. If C needs a behavior change, that is a defect in A or B.
- The live Jira Data Center smoke - externally blocked, tracked separately.
- Cutting the release. The batch releases together once A, B and C are all done.

## Decision Context
<!-- scope: both -->

### Why teardown is last and separately gated

Deleting the prose before the replacement is proven would leave no fallback and no reference. C depends on B, and B's conformance matrix is the gate. The cost of carrying both for one spec's duration is drift risk over a short window; the cost of deleting early is an unrecoverable position if the deterministic path has a hole.

### Why the caller gate survives a "remove the dispatch machinery" spec

It looks like machinery to delete, and deleting it was the original plan. But every flowctl command emits JSON and `inactive` is an error class, so a bridge-inactive repo routed into flowctl gets output and a process where it previously got silence and one config read. The gate is what preserves the invariant that non-tracker users see nothing, which is the single most load-bearing promise of this batch.

### Why the supersession is written down

fn-57 R3 is a live acceptance criterion asserted in two code docstrings and one doc line. Shipping code that contradicts it without recording the reversal leaves a future reader with a contradiction and no decision trail. The cost of recording it is three edits.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_tracker_sync_mirror_parity test_reached_path_harness -q
```

Full gate once at completion: `python3 scripts/run_tests_parallel.py`
Docs site: `cd ~/work/flow-next.dev && pnpm build`
