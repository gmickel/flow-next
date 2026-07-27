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

### The exact call flow (one path, no ambiguity)

Ownership was previously split in a way that read as a contradiction - the skill "keeps comment synthesis" while callers "call the facade directly". The single flow is:

1. **Caller gate** (retained): bridge-active + `perEvent` value.
2. **Caller-owned content synthesis**: the calling skill renders the comment text or body - that is its judgment.
3. **Secure temp input file**: content is written to a `0600` file under `${TMPDIR}`, never argv; the caller deletes it after the call.
4. **Inline tracker-sync skill wrapper**: the caller invokes the tracker-sync skill, which makes **one** facade call. The wrapper is where the skill's retained surfaces live.
5. **Centralized recovery in that wrapper**: `class: conflict` and `external_action_required` are handled **once, in the skill**, not duplicated as recovery prose across fourteen callers. MCP continuations resolve there too.

So callers own *what to say*; the skill owns *what to do when flowctl says no*. Receipt ownership is unchanged: the facade writes exactly one.

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
- **R3:** Lifecycle touchpoints call the **fn-140 lifecycle facade** `flowctl tracker sync <spec-id> --op <op> --event <key>`, not the granular verbs. The granular verbs cannot preserve behavior on their own - create-if-unlinked, comment markers, dedup and receipts are orchestration, and pushing that into each caller as prose is the problem this batch removes. **C is gated on fn-140 R19 passing conformance.** The `tracker-runner` agent and `references/tracker-dispatch.md` are then removed.
- **R4:** The caller-side gate is **retained**; only transport-ladder and dispatch prose is removed. The `perEvent` to verb mapping is explicitly enumerated, and comment content synthesis is reassigned by name to each calling skill.
- **R5:** Zero dangling references to the deleted agent, across an **enumerated** sweep: every canonical calling skill named individually; `scripts/sync-codex.sh` (measured at 19 matching lines / 29 tokens at time of writing - but the **inventory is an explicit path/token list asserted by test**, never a prose count, because the count is pattern-dependent and goes stale: an earlier draft of this spec said 18 using a narrower pattern); runner-specific tests; the generated mirror's agent TOML; and `docs/platforms.md`. Asserted by test over the named inventory, not a single grep that a narrow scope could pass while dead transforms survive.
- **R5b:** The **pre-teardown oracle is captured before any caller edit**, hash-addressed and pinned to the post-fn-140 / pre-C commit. Capturing it after rewiring (the earlier ordering) cannot prove preservation, because the thing being compared has already changed. It records config reads, argv, imports, stdout and stderr per caller.
- **R6:** The **bridge-inactive path is byte-for-byte unchanged** after rewiring: one config read, no adapter import, no new output. Verified here rather than in A, because C is what changes the final inactive path.
- **R7b:** An **authoritative matrix** exists, naming for every caller: its file path, its event key, the legal configured values, the resolved facade `--op`, any **unconditional** behavior, the required content input, the expected receipt, and stream behavior. The semantics are not reconstructible from "enumerate the legal values" because several callers deviate: **QA coerces every non-`off` value to `comment`**; **make-pr and land have unconditional paths** (land's merge->Done rides bridge-active alone, not its leaf); **work events use fixed operations regardless of the configured verb**. The matrix is asserted by test against the real caller inventory.
- **R7:** Every configured `perEvent` value is tested end to end: the enum is `off | pull | push | reconcile | comment` - an earlier draft omitted **`pull`**. Every event key and its legal values are enumerated by name, including QA's comment-only rule and land's unconditional status rule. Each caller is instrumented with a **fake flowctl** asserting config reads, argv, imports, stdout and stderr against a **pre-teardown captured oracle** - "byte-for-byte" names the streams compared and what it compares them to.
- **R8:** fn-57's R3 supersession is recorded at all three assertion sites, with a pointer to this batch so a future reader finds the decision rather than a contradiction.
- **R9:** `docs/tracker-sync.md` is rewritten: the Transport ladder section becomes flowctl-owned, the `tracker.resolved` schema and capability degradation are documented, and the "flowctl has no tracker transport" line is corrected.
- **R10:** `docs/flowctl.md` gains a complete `## flowctl tracker` section modelled on the existing `## flowctl sync`, documenting every verb, the result envelope, the `class` enum and the numeric exit codes.
- **R11:** The Jira `apiVersion` default is corrected to **2** in docs, matching the measured behavior that v2 round-trips plain strings byte-exact.
- **R12:** No doc still teaches a reader or agent to reason about a runtime transport ladder. Includes the doc-index rows in `README.md`, `docs/README.md`, `docs/teams.md` and `CLAUDE.md`.
- **R13:** `agent_docs/optimizing-skills.md`'s always-loaded weight classification for tracker-sync is re-measured and updated.
- **R14:** fn-130's **B1 baselines are NOT re-frozen** - `freeze_b1()` refuses a non-empty destination because B1 is write-once and hash-addressed, and editing it would destroy the provenance the delta is measured against. fn-134 updated **candidate** evidence, not B1, and this follows that precedent: record the reduction as a **candidate delta** naming all affected tracker fixtures explicitly. If a new baseline is genuinely wanted, that is a deliberate **B2** with its own commit/tag, inventory constant, validator, lineage and migration rationale - not an in-place overwrite.
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

Full gate once at completion: `python3 scripts/run_tests_parallel.py` plus `uvx ruff@0.16.0 check .` (pinned lint gate, landed post-spec-A in #244/#245 - both must be green before a PR).

Post-#245 invariants (see CLAUDE.md): any `flowctl.py`/`flowctl_tracker/` change needs the propagation chain (copy to `.flow/bin/`, `python3 scripts/gen_tracker_manifest.py`, `./scripts/sync-codex.sh` twice); `tests/test_prompt_text_pinned.py` pins embedded prompt constants by SHA-256 - a deliberate prompt change updates the hash in the same commit with the rationale in the commit message.
Docs site: `cd ~/work/flow-next.dev && pnpm build`
