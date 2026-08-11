# Overview

Issue #325 (sn-furali): the documentation and the pilot skill give opposite answers about whether a Linear board move clears a `/flow-next:pilot` two-strike strikeout - and the reporter's three-phase measurement shows the skill's own escape clause has nothing to key on. The docs sentence ("re-readying the spec, which pilot reads as a human re-bless and clears strikes") describes pre-fn-87 behavior; fn-87 R7 (2026-07-04, a060afb6) deliberately made a `count >= 2` strike survive a projection-set ready because a board echo re-grants readiness with no human involvement (reporter phase A confirms). But the skill's stated recovery - "an explicit re-ready made after the failure is understood (not a projection echo)" - is unimplementable: a deliberate out-and-back board move is byte-identical to an echo in every durable artifact (phase C; flowctl stores no readiness provenance). Under armed `tracker.readyState`, a struck spec reads ready everywhere a human looks while staying permanently invisible to pilot; the only escape is hand-editing an undocumented ledger under `.git/`.

**Evidence standing: reporter-measured three-phase experiment (echo / deliberate re-bless / receipt diff) at 3.15.0, contradiction re-verified at 3.23.0; timeline confirmed from git history this session. No new evals.**

## Goal & Context

Give the human signal a real observable - a deterministic `flowctl pilot strikes` verb family (the recovery the skill's escape clause promises but cannot detect) - and sweep every surface still asserting the pre-fn-87 behavior. Strikes are pilot state, not readiness state, so a CLI clear does not dent the board-is-the-readiness-control-plane doctrine.

## Architecture & Data Models

1. **`flowctl pilot strikes` verb family (new plumbing over existing state):** `flowctl pilot strikes list [--json]` (render the ledger; missing file = empty), `flowctl pilot strikes clear <spec-id> [--json]` (remove one entry; unknown spec-id is a distinct not-found, not silent success), `flowctl pilot strikes clear --all [--json]`. Ledger location and schema are the skill's existing contract verbatim: `$(git rev-parse --git-common-dir)/flow-next/pilot-strikes.json`, `{"<spec-id>": {count, stage, reason, ts}}`. Writes are atomic (tmp + rename), tolerate a missing/empty file, and never touch other entries. flowctl becomes the shared read/clear plumbing; the skill keeps its own jq write sites for recording strikes.
2. **Pilot skill prose:** the Phase 1 item 3 exception's escape clause names the verb as THE recognized human clear under armed `tracker.readyState` ("the human answering the surfaced failure runs `flowctl pilot strikes clear <spec-id>`"); the `BLOCKED ... strike 2/2` terminal reason names the verb so the transcript carries its own recovery; the "skill-owned scratch; no flowctl plumbing" sentence updates to the shared contract. The null-`readyState` clear-on-ready path is unchanged.
3. **Docs truth-sweep (repo):** `docs/tracker-sync.md` Pilot-interplay paragraph corrected to the fn-87 rule + the verb as the armed-repo recovery; `docs/troubleshooting.md` gains a strikes-ledger entry (where it lives, what a strikeout looks like, how to list/clear). Site pages (`teams/tracker-sync.mdx`, `skills/pilot.mdx` on flow-next.dev) carry the same correction - they ride the release downstream walk, not this repo's diff.
4. **Decision record:** the board-native alternative (an observed-out-of-ready-since-strike ledger bit) is recorded as considered-and-deferred with the tick-granularity caveat, so it is not re-proposed cold.

## Edge Cases & Constraints

- `clear` on a spec with `count < 2` still clears (the ledger entry is the thing being managed; no magic threshold).
- Not a git repo / no common dir: `list` reports empty with a note, `clear` errors cleanly; never a traceback.
- Concurrent pilot tick vs clear: last atomic write wins; acceptable (same discipline as the skill's own write sites; no new lock).
- The verb must NOT touch spec `ready` state - clearing a strike does not re-ready an unreadied spec on a null-`readyState` repo; the two signals stay orthogonal and the docs say so.
- Worktrees: the git-common-dir resolution must match the skill's (shared across worktrees); a worktree-local `.git` file resolves through to the common dir.
- The reporter's "not requested" list is binding: no change to projection direction, the two-strike guard, or `spec ready`/`unready` semantics.

## Acceptance Criteria

- **R1:** `flowctl pilot strikes list` renders the ledger (empty-safe, `--json` machine shape); `clear <spec-id>` removes exactly one entry atomically with a distinct not-found for unknown ids; `clear --all` empties the ledger. Errors: non-repo contexts fail cleanly, never a traceback.
- **R2:** Clearing a strike never mutates spec readiness, pinned by test.
- **R3:** The pilot skill's armed-`readyState` escape clause and the strike-2/2 terminal reason name the verb; the ledger-ownership sentence reflects the shared contract; the null-`readyState` clear-on-ready path is byte-identical in behavior.
- **R4:** `docs/tracker-sync.md` no longer claims projection clears strikes; it states the fn-87 rule and the verb recovery. `docs/troubleshooting.md` documents the ledger and recovery. No repo surface still asserts the pre-fn-87 behavior (sweep, not spot-fix).
- **R5:** The board-native alternative is recorded as a deferred decision with rationale.
- **R6:** Mirrors, dual flowctl copies, CHANGELOG Unreleased crediting @sn-furali (#325); the #325 answer is postable by link. Errors: parity red blocks merge.

## Boundaries

- No board-native transition detection (deferred, recorded - R5).
- No change to projection direction, the two-strike guard, or `spec ready`/`unready`.
- No strike-recording move into flowctl - the skill keeps its write sites.
- Site-page corrections ride the release downstream walk, not this diff.
- Version bump deferred to the batched release.

## Decision Context

Verb over board-native: the verb is an unambiguous human signal with no missed-transition window, testable, and consistent with the flowctl-owns-set-this-field split; the board-native bit preserves the board doctrine for armed repos but silently misses a fast out-and-back between ticks and adds observation semantics to a ledger that is otherwise a plain counter. Strikes are pilot state, not readiness state, so the doctrine sentence in tracker-sync.md survives intact. The docs error is a fn-87 sweep miss - the same every-surface-in-one-edit failure class as #306 and the PR #327 paraphrase tail; the sweep here is deliberately exhaustive (R4 says "no repo surface", not a file list).
