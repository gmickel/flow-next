# fn-66 tracker-sync: reserve Linear Done for merged PRs; In Review after make-pr

> **Origin:** Linear issue [FLOW-15](https://linear.app/gmickel/issue/FLOW-15) (team Flow Next, project Development, `Bug`, High), filed 2026-06-17 after a SapienXT incident. Grabbed via `/flow-next:tracker-sync`; this spec is the canonical source of truth and FLOW-15 is its co-editable mirror.

## Goal & Context

tracker-sync can push a projected tracker issue to **`Done`** when a Flow spec is locally complete (all tasks `done` + `completion_review_status == ship`) **even though no PR exists or the PR has not merged**. The repo convention (SapienXT incident, 2026-06-17) is unambiguous: **Linear `Done` means *merged*.** Local Flow completion means implementation + review are done, NOT that the change shipped.

**Observed failure:** SapienXT `fn-29` / `WOR-27` reached all-tasks-done + completion-review `SHIP`; closeout/tracker-sync pushed `WOR-27` → `Done` with **no GitHub PR** and **unmerged commits**; a human had to drag it back to `In Progress`.

**Goal:** make the tracker-sync status policy lifecycle-accurate — `Done` is reserved for *merge-confirmed* state, and an open PR maps to `In Review` — so the board never claims "shipped" for work that isn't.

## Architecture & Data Models

The status projection lives in the tracker-sync **status who-wins** layer (`skills/flow-next-tracker-sync/references/status-sync.md`) plus the per-event touchpoints the host skills fire (the `tracker.perEvent.*` table in `flow-next-tracker-sync/SKILL.md`; current seeded values: `work.firstClaim=push`, `work.done=comment`, `makePr=comment`, `completionReview=reconcile`, `land.merged=off`). The fix is a **status mapping policy** keyed off lifecycle phase + **PR/merge evidence**, applied consistently at every touchpoint that can write status.

**The canonical lifecycle → tracker-state map** (this is the spec's core contract):

| Flow lifecycle phase | Evidence | Tracker state |
|---|---|---|
| Task first-claimed / work underway | task `in_progress` | `In Progress` |
| make-pr created/found an **open** PR | open PR exists for `branch_name` | `In Review` |
| PR **merged** | GitHub reports the linked PR `MERGED` | `Done` (terminal) |
| All tasks done + completion `ship`, **no merged PR** | no PR / open PR / closed-unmerged | **NEVER `Done`** — stay `In Review` (open PR) or non-terminal + a comment; ambiguous → `NEEDS_HUMAN` |

- **Merge-evidence gate (the central rule).** The flow→normalized mapping becomes a function of **`(spec status, completion_review_status, PR-merge-evidence)`** — `flowToNormalized(spec, prEvidence)` — NOT of spec state alone. No write path (automatic touchpoint OR a manual `/flow-next:tracker-sync` reconcile) may set the terminal `Done`/completed state without **GitHub-confirmed `MERGED`** evidence for the spec's `branch_name` (`gh pr list --head <branch> --state all` → `MERGED`). Flow `done` + completion `ship` is necessary, never sufficient. The gate is an **invariant on the outbound terminal write**, not a property of one touchpoint — so a manual merge-evidenced reconcile is the legitimate recovery path (it MAY terminal-write when `MERGED` exists), while any local-completion-only write may not.
- **No-PR all-done — exact state.** All tasks done + completion `ship` + **no PR at all**: tracker-sync makes **no status advance** — the issue stays at its current non-terminal state (typically `In Progress`); it is NOT moved to `In Review` (nothing is in review) and NOT to `Done`. Optionally a one-line comment notes "locally complete, no PR yet." Pilot (below) is what then drives `make-pr`.
- **make-pr → `In Review` (on the unconditional PR-link path).** make-pr's PR↔issue link is **unconditional whenever the bridge is active** (not perEvent-gated — it powers Linear Diffs). The `In Review` status push rides that same unconditional path: when make-pr creates/finds an **open** PR, reconcile the linked issue to `In Review` (the existing Flow Next `type: started` state) alongside the PR-link comment — so In Review is not gated behind `perEvent.makePr` being non-`off`.
- **completionReview → not terminal (dispatch becomes `comment`-shaped).** The `completionReview` touchpoint stops pushing status: re-scope its dispatch from `reconcile` (which implies status+body) to a **`comment`-shaped** effect (verdict + R-ID coverage), and at most leave the issue at `In Review` if an open PR exists. Never `Done`.
- **merge/land → `Done` (the automatic driver, active by default).** `land.merged` is the **automatic** Done driver, gated on the `MERGED` probe. To avoid boards sticking at `In Review` after a real merge, `land.merged` must be **active by default when the bridge is active** (resolve in T2: default-on via the discovery ceremony, or unconditional-when-bridge-active — NOT left `off`, which would never project Done at all). The merge-evidence invariant means even this write self-checks `MERGED` rather than trusting the caller.
- **GitHub adapter parity.** The same `flowToNormalized(spec, prEvidence)` gate applies on the GitHub adapter (`references/github.md` terminal/closed mapping): its reduced-fidelity `setStatus(done|verified)` path must also require `MERGED` evidence, or it regresses the bug via the back door. Note the transport-blind invariant in `references/adapter-interface.md` (terminal outbound writes require merge evidence).
- **pilot classification gap.** Pilot must not return terminal `NO_WORK` for an all-done / completion-`ship` spec that has **no open and no merged PR** — that state means make-pr never ran (or its PR was lost). Pilot already has an all-done PR-probe branch (classifies `make-pr` when no PR exists); this spec hardens it so the no-PR all-done case dispatches `make-pr` or reports `NEEDS_HUMAN`, never silently `NO_WORK`.

## API Contracts

- **status-sync policy** (`references/status-sync.md`): add the lifecycle→state map + the merge-evidence gate to the who-wins ladder. The mapping is **transport-blind** (Linear state names / GitHub labels resolved per adapter); `Done`/closed terminal is gated on merge evidence regardless of adapter.
- **perEvent semantics** unchanged as keys, but their *status effect* is re-specified: `makePr` may push `In Review` (open-PR evidence); `completionReview` never pushes terminal; a merge touchpoint pushes `Done` (merge evidence). No new config key required unless a `tracker.statePolicy` knob proves necessary during planning — default behavior is the corrected map.
- **Merge probe** (shared): `gh pr list --head "$BRANCH_NAME" --state all --json state` → `MERGED` present ⇒ merge evidence; `OPEN` ⇒ In Review; `CLOSED` (unmerged) / none ⇒ non-terminal + NEEDS_HUMAN/comment. Reuse land's existing probe shape.
- **pilot**: the all-done classification branch returns `make-pr` (no PR) or `NEEDS_HUMAN` (closed-unmerged / merged-but-open-spec inconsistency) — never `NO_WORK` for an all-done spec lacking a merged PR.

## Edge Cases & Constraints

- **No PR at all** (the FLOW-15 incident): all-done + completion-ship, no PR → tracker stays non-terminal; pilot dispatches make-pr; never `Done`.
- **Open PR:** → `In Review`; not `Done` until merged.
- **Merged PR:** → `Done` (terminal) — the only path to Done.
- **Closed-unmerged PR / missing branch / ambiguous PR state:** do NOT mark `Done`; emit `NEEDS_HUMAN` or leave non-terminal with an explanatory comment.
- **GitHub adapter parity:** the same merge-evidence rule applies — `Done`/closed label only on a merged PR; the GitHub adapter's reduced-fidelity status must still gate terminal on merge.
- **Idempotency / re-entry:** re-running a touchpoint must not thrash status (In Review → In Review is a no-op; a merged spec re-synced stays Done).
- **Backward-safety:** a spec already at `Done` from a real merge is untouched; the change only prevents *premature* Done.
- **Who-wins interaction:** a human manually moving the issue must still win per the existing tiebreak — the merge-evidence gate constrains tracker-sync's *own* writes, not human edits.

## Acceptance Criteria

- **R1:** tracker-sync status policy never maps Flow `done` + completion-review `ship` directly to tracker `Done` unless **merged-PR evidence** exists (the GitHub `MERGED` probe for the spec's `branch_name`).
- **R2:** The make-pr lifecycle touchpoint moves the linked issue to `In Review` when an open PR exists for the branch (in addition to the existing PR-link comment).
- **R3:** The merge/land reconciliation moves the linked issue to `Done` only when GitHub reports the linked PR `MERGED`.
- **R4:** completion-review (`SHIP`) never pushes a terminal `Done`; it posts its verdict/evidence and at most ensures `In Review`.
- **R5:** Pilot never returns terminal `NO_WORK` for an all-done / completion-`ship` spec with no open and no merged PR — it dispatches `make-pr` or returns `NEEDS_HUMAN`.
- **R6:** Closed-unmerged PR, missing branch, or ambiguous PR state never produces `Done` — `NEEDS_HUMAN` or non-terminal + comment.
- **R7:** Regression coverage exercises the full matrix: **no PR, open PR, merged PR, closed-unmerged PR** (and the pilot all-done-no-PR case), asserting the resulting tracker state / verdict for each.
- **R8:** GitHub adapter honors the same merge-evidence gate for its terminal state.
- **R9:** Docs updated — `references/status-sync.md`, `references/github.md` (terminal mapping), `references/adapter-interface.md` (transport-blind merge-evidence note), the `perEvent` status semantics in `flow-next-tracker-sync/SKILL.md` + `docs/tracker-sync.md` (incl. inverting the `:131` "spec-completion-review owns Done" claim) + `docs/teams.md` (Linear Diffs paragraph), the make-pr / completion-review / land touchpoint prose, the pilot classification note; Codex mirror regenerated; flow-next.dev tracker-sync / land pages updated in the same workstream.
- **R10:** `land.merged` is active by default when the bridge is active (so a real merge actually projects `Done`), and the terminal-write merge-evidence invariant holds on **every** path — automatic touchpoints AND a manual `/flow-next:tracker-sync` reconcile (which may terminal-write iff `MERGED` evidence exists). The flow→normalized mapping is `flowToNormalized(spec, prEvidence)`.

## Boundaries

- **No new lifecycle phases** — only the state *mapping* + the merge-evidence gate change; the touchpoints themselves (firstClaim / makePr / work.done / completionReview / merged) stay where they are.
- **No change to merge mechanics** — land still owns merging; this constrains the *status write* to require merge evidence, it doesn't move the merge.
- **No override of human edits** — the existing who-wins tiebreak for human status changes is preserved.
- **Not dependency projection** — distinct from FLOW-14 / fn-64 (explicitly noted in FLOW-15).
- **Tracker stays a projection** — flow remains the source of truth; this only corrects what state the projection writes.

## Decision Context

`Done` is a *claim about reality* ("this shipped"), and the board is read by people who don't see the repo — so a premature `Done` is a correctness bug, not a cosmetic one (the SapienXT human had to manually undo it). The repo already has the exact primitive needed: land's `gh pr list --head <branch> --state all` MERGED probe. The fix is to make **every** terminal-status write depend on that evidence instead of trusting local Flow completion, and to give the open-PR state its own honest rung (`In Review`).

Reserving `Done` for merge evidence also closes the pilot gap symmetrically: an all-done spec with no merged PR is *unfinished from the board's perspective*, so pilot must keep driving it (make-pr) or surface it (`NEEDS_HUMAN`) rather than declaring `NO_WORK`. The lifecycle is only consistent if "done locally," "in review," and "shipped" are three distinct, evidence-backed states end to end.

## Requirement coverage

| R-ID | Task |
|---|---|
| R1, R6, R7, R8 | fn-66.1 — status-sync policy: `flowToNormalized(spec, prEvidence)` merge-evidence gate + `In Review` rung + worked-fixture matrix (S-G..S-J, exact states) + linear-ladder + github.md + adapter-interface sync |
| R2, R3, R4, R10 | fn-66.2 — touchpoint re-scoping: completionReview (dispatch→`comment`, never terminal) / makePr (→ In Review on the unconditional PR-link path) / land.merged (→ Done on MERGED evidence, **active-by-default when bridge active**) + manual merge-evidenced recovery + flowctl perEvent default/test |
| R5, R6 | fn-66.3 — pilot all-done hardening: never NO_WORK for an all-done spec lacking a merged PR (make-pr / defer-to-land / NEEDS_HUMAN) |
| R9 | fn-66.4 — docs (tracker-sync.md, SKILL prose, decision-record note) + CHANGELOG + version bump + Codex mirror regen + flow-next.dev (tracker-sync + land) |
