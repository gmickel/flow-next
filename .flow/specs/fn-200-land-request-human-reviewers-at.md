# land: request human reviewers at convergence (`land.requestReviewers`)

## Overview

`/flow-next:land` models the human reviewer as an event it waits for, never as someone it can ask. It can summon a bot (`land.reviewTrigger`, a one-shot issue comment keyed to the head SHA in the land ledger), bound the wait (`land.patienceMinutes`), and define what counts as a clean review (`land.reviewSignal`) — but it never populates the PR's requested-reviewers field. On a repo whose ruleset requires a code-owner review (sharpest when the PR author is a GitHub App, which cannot be a code owner), a converged PR sits idle until a human happens to notice it. GitHub issue #359 (part 1), reported by @sn-furali.

This spec adds one opt-in config key, `land.requestReviewers`. When set, land requests the listed humans (or lets GitHub resolve CODEOWNERS) exactly at the moment a human review is the only thing standing between the PR and a merge, flips the PR from draft to ready at that same moment so "ready" keeps meaning "a human may review this now", and records the request one-shot per PR per head SHA in the existing land ledger. Default empty — today's gates, actions, and ledger writes are unchanged (the evidence line gains one additive `reviewers=off` field). Part 2 of the issue (`land.draftOnChangesRequested`) is out of scope.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_land_config test_flow_config_schema_drift test_skill_prose_diet -q
uvx ruff@0.16.0 check .
```

## Goal & Context

Reporter's daily cost: land reaches convergence, reports `AWAITING_REVIEW`/`NEEDS_HUMAN`, and the one person who can satisfy the gate was never told it is their turn. The fix belongs inside land because only land knows "converged" (recomputing it consumer-side duplicates the gate tree) and `isDraft` is already land's state to write. `/loop` cadence does not help: more ticks never ask a human.

## Architecture & Data Models

- **Config:** `land.requestReviewers` — csv string (same shape as `land.automatedReviewers`): GitHub logins and/or `org/team` slugs, and/or the literal token `codeowners`. Default `""`. `null` / `""` mean OFF. Read through the single Phase 0 `lcfg` capture (no second `config get`).
- **Ledger:** a new per-PR field `reviewRequestSha` in the existing land ledger (`$(git rev-parse --git-common-dir)/flow-next/land-strikes.json`), written atomically (jq + mv) exactly like `triggerSha`; removed with the whole PR entry on the existing post-merge `del(.[$pr])`.
- **Gate-tree placement (Phase 2 stays read-only):** a new `§2.6b — Human reviewer request` immediately after §2.6's signal evaluation and before §2.7 computes the predicate below and, when a request is due, sets `PLANNED_ACTION=request-reviewers` with provisional verdict `AWAITING_REVIEW` (inside the patience window) / `NEEDS_HUMAN` (beyond it). It mutates nothing — no `gh` write, no ledger write — and falls through like every other gate (§2.7 still runs). The mutations live in a new Phase 3 action class `§3.x — request-reviewers` (one action class per PR per tick, same as `ci-fix`/`resolve`/`catch-up`), so `--dry-run`'s zero-mutation stop before Phase 3 covers it by construction. The existing draft-PR *bot* trigger in §2.6 is left exactly as it is.
- **Predicate ("human-review-pending"):** `REQUEST_REVIEWERS` non-empty AND CI green AND `UNRESOLVED == 0` AND one of:
  - `reviewSignal ∈ {approve, <login>}` and the signal is unsatisfied with `REVIEW_DECISION != CHANGES_REQUESTED` (no review yet, or a stale/dismissed one);
  - `reviewSignal == silence` and the signal is satisfied but `REVIEW_DECISION == REVIEW_REQUIRED` (the repo requires a human review that is missing — today this becomes a merge attempt GitHub refuses).
  Predicate true AND ledger `reviewRequestSha != HEAD_OID` AND no claim dir for `(PR, HEAD_OID)` → `PLANNED_ACTION=request-reviewers`. Predicate true AND already recorded or claimed for this head → `PLANNED_ACTION=none`, verdict per window, `reviewers=already:<sha8>`. Under `silence` the predicate replaces the planned `merge` with the above (a merge GitHub would refuse anyway). Predicate false → §2.6b is a no-op and nothing downstream changes.
- **`request-reviewers` action (Phase 3):** (0) atomic claim via `mkdir` of the `(PR, HEAD_OID)` claim dir — failure → `reviewers=already:<sha8>`, stop; (1) if `IS_DRAFT`, `gh pr ready` (idempotent); (2) request the reviewer list minus the PR author via `gh pr edit --add-reviewer <csv>` — the PR author login comes from the existing `PR_STATE` capture, whose `gh pr view --json` field list gains `author`; the `codeowners` token is dropped from the explicit list (GitHub auto-requests code owners on the ready flip); (3) write `reviewRequestSha = HEAD_OID` (atomic jq+mv) whatever the outcome of 1-2; (4) verdict `AWAITING_REVIEW`. A list that is empty after removing the author (or `codeowners` alone) takes the ready-flip-only path when the PR is a draft; on an already-ready PR that same list is a no-op — report `reviewers=skipped:already-ready, no explicit logins`, record the sha, and never report `requested` without a request-producing action.
- **Report:** Phase 4 evidence block gains one field on the `signal=` line: `reviewers=<requested|would-request|already:<sha8>|skipped:<reason>|failed:<one-line>|off>`, and the `action=` vocabulary gains `request-reviewers`. `--dry-run` reports `action=request-reviewers reviewers=would-request` (plus `would-ready` when the PR is a draft) and writes nothing.
- **Failure handling:** a failing `gh pr ready` or `gh pr edit --add-reviewer` (unknown login, no access, partial-batch rejection, empty author login) still writes `reviewRequestSha` — one attempt per head, never a retry loop — and surfaces `reviewers=failed:<reason>`; the verdict is whatever the window says (`AWAITING_REVIEW` / `NEEDS_HUMAN`), never `BLOCKED` (reserved for server-side merge refusals).
- **Concurrency (exact-once claim):** before any remote call, the action atomically claims `(PR, HEAD_OID)` with a single `mkdir` of `$LEDGER_DIR/review-request-claims/<pr-number>-<HEAD_OID>` (mkdir is atomic on every POSIX filesystem; the parent is created first). A failed `mkdir` means another tick already holds this head → no request, `reviewers=already:<sha8>`. §2.6b treats an existing claim dir exactly like a recorded `reviewRequestSha`. The claim persists through gh failure (one attempt per head, same as the ledger sha) and the PR's claim dirs are removed in the same post-merge step that deletes its ledger entry. The ledger `reviewRequestSha` remains the human-readable record; the claim dir is the mutual-exclusion primitive, so a lost ledger update under overlapping ticks cannot cause a duplicate request.

## API Contracts

- `flowctl config get land.requestReviewers` → `""` by default; `config set` round-trips any string; published schema: `{"type": ["string","null"]}` with a description naming the csv grammar and the `codeowners` token.
- Ledger entry shape (additive): `{"...existing fields...", "triggerSha": "<sha|absent>", "reviewRequestSha": "<sha|absent>"}`.
- Evidence line (additive only): `signal=<...> decision=<...> reviewers=<requested|would-request|already:<sha8>|skipped:<reason>|failed:<reason>|off>`; `action=` gains the value `request-reviewers`.

## Edge Cases & Constraints

- PR author is in the list → filtered out before the call (GitHub 422s a self-request). Team slugs contain `/` and are compared as whole tokens, never substring-matched against the author.
- Re-requesting an already-requested or already-reviewed login is GitHub's "re-request review" — the intended semantic for a new head; a reviewer whose approval still stands on the current head is never re-asked because the predicate is false.
- A land-authored CI-fix/catch-up push moves `HEAD_OID`, so the one-shot re-arms: a re-request fires only if the human's review is again missing for the new head (dismissed under `dismiss_stale_reviews_on_push`) — that is a genuine re-ask, not spam.
- The ready flip happens on a draft only; `ready_for_review` is not a push and does not dismiss approvals, so §2.7's stale-approval detector is unaffected. Bots that auto-review on ready (Codex) may post a review after the flip; that only ever adds evidence.
- Re-entry (`resume-tail`) and durable-label (`2.1`) paths never reach §2.6b; a stale `reviewRequestSha` on such a PR is inert and leaves with the PR's ledger entry.
- `silence` with no ruleset (`REVIEW_DECISION` empty): unchanged — land merges; `requestReviewers` never gates a merge, `reviewSignal` does. A team that wants a human look on every PR sets `reviewSignal: approve` (documented next to the key).
- App-authored PRs: any write-access identity can request reviewers on them; the ready flip makes GitHub auto-request code owners regardless of author.
- Dry-run zero-mutation promise holds by construction: the action class lives in Phase 3, which `--dry-run` never enters.
- Coordinate, not depend: fn-149 (stacked-PR hardening) edits the §2.8/§3.3/§3.5 region; §2.6b is a new section above it — leave a one-line cross-reference in fn-149's spec if both are in flight.

## Acceptance Criteria

- **R1:** `land.requestReviewers` exists as a seeded config key with default `""`, round-trips through `flowctl config get/set` without clobbering sibling `land.*` keys, and is present in the generated `flow-config.schema.json` with the csv-or-`codeowners` grammar in its description. Errors: an unset/`null`/`""` value means OFF; no validation of login names at config time (GitHub is the validator; no error surface beyond R4).
- **R2:** With `requestReviewers` non-empty, §2.6b plans the `request-reviewers` action exactly when the human-review-pending predicate holds (CI green, zero unresolved threads, and a human review is the only missing merge input per `reviewSignal`) and neither the ledger's `reviewRequestSha` nor a claim dir marks this head; the Phase 3 action first takes the atomic `mkdir` claim for `(PR, HEAD_OID)`, then flips a draft PR to ready, requests the configured reviewers minus the PR author (author read from the `PR_STATE` capture, which gains the `author` field), and records `reviewRequestSha` — exactly once per PR per head SHA even under overlapping ticks. Phase 2 performs no mutation. Errors: predicate false (CI not green, threads open, signal satisfied with no required review, `CHANGES_REQUESTED`) → no action, no flip, no ledger write; same head already recorded or claimed (including a lost `mkdir` race) → `action=none`/no remote call, `reviewers=already:<sha8>`, no second call on any later tick; empty/null author login → treated as a failed request (R4), never a self-request.
- **R3:** With `requestReviewers` empty (the default), every gate decision, planned action, verdict, `gh` call, and ledger write is unchanged from today; the only observable difference is the additive `reviewers=off` field on the evidence line. Errors: no error surface beyond R1.
- **R4:** A failing request or ready flip writes `reviewRequestSha` anyway, surfaces `reviewers=failed:<one-line reason>` in the evidence block, and yields the window-bounded verdict (`AWAITING_REVIEW` / `NEEDS_HUMAN`), never `BLOCKED` and never a retry on the next tick for the same head. Errors: list empty after removing the PR author, or `codeowners` alone → on a draft PR the ready-flip-only path (reported `requested`: the flip is the request-producing action, GitHub resolves owners); on an already-ready PR → no request-producing action exists → `reviewers=skipped:already-ready, no explicit logins`, sha recorded, never reported `requested`.
- **R5:** `--dry-run` reports `action=request-reviewers reviewers=would-request` (plus `would-ready` for a draft) from Phase 2 alone and performs zero mutations — no `gh pr ready`, no `--add-reviewer`, no ledger write — because the mutating action class lives in Phase 3. Errors: no error surface beyond R4.
- **R6:** Under `reviewSignal: silence` with `requestReviewers` set and `reviewDecision == REVIEW_REQUIRED`, land plans `none` with `AWAITING_REVIEW` (inside the window) instead of a merge GitHub would refuse; once the decision becomes `APPROVED` the existing merge path runs. Errors: `reviewDecision` empty (no review policy) → merge as today, no request.
- **R7:** Docs carry the key: land SKILL.md gate bullet, `docs/flowctl.md` `land.*` table row, `docs/README.md` what's-new bullet, `agent_docs/conduct/land.md` checklist row, a `## Unreleased` CHANGELOG entry crediting @sn-furali (#359), codex mirror regenerated twice. Errors: no error surface beyond the existing docs tests.

## Boundaries

- `land.draftOnChangesRequested` (issue #359 part 2) — not built; reassess after part 1 ships.
- No local CODEOWNERS parsing or owner-resolution logic: the `codeowners` token relies on GitHub's own auto-request on ready-for-review.
- No re-anchoring of the patience window to the request time; the window stays anchored to the last push.
- No per-signal override of `requestReviewers`; one key, one predicate.
- No flow-next.dev docs-site change in this spec (maintainer's private downstream chain handles it at release).

## Strategy Alignment

Active tracks served by this plan:
- **Ralph autonomous mode** — land is the shipping half of the pilot+land assembly line; this closes the last un-asked human handoff in its gate tree without weakening "never merge unreviewed" or "surface-don't-force".

## Decision Context

- **Predicate, not "at convergence":** the issue says "request at convergence beside the ready flip", but under `approve`/`<login>` convergence *is* the human's approval, so that would deadlock; and under `silence` without a ruleset it would notify a human about a PR that merges in the same tick. The predicate "a human review is the only missing merge input" fires in both real cases and never in the rubber-stamp case — structural elimination of the race, no extra state.
- **Flip ready at request time:** `gh pr ready` currently runs only at merge (§3.5). GitHub auto-requests code owners only on ready-for-review and many orgs ignore drafts; requesting a human on a draft is the "ready once" semantic the reporter calls out. Flipping at request time keeps "ready" = "a human may review now", gives the `codeowners` token a zero-code implementation, and costs nothing on approval (ready is not a push; nothing is dismissed).
- **One-shot keyed to head SHA, not per-PR-lifetime:** the predicate already guarantees a request fires only when the human's review is missing for the current head, so a per-head key re-asks exactly when a re-review is genuinely needed (approval dismissed by a CI-fix push) and never otherwise. Rejected per-PR-until-reviewed as extra ledger state that duplicates what `reviewDecision` already says.
- **csv string, not JSON list:** matches `land.automatedReviewers`, is `flowctl config set`-friendly, and needs no new schema shape. Rejected a list type as inconsistent with the sibling key.
- **Record the sha on failure too:** mirrors the bot trigger's one-attempt-per-head; a retry loop against a 422 is worse than a surfaced `failed:` reason.
- **Phase 3 action class, not a gate-phase side effect:** the bot trigger mutates inside §2.6, but Phase 2 is documented read-only and `--dry-run` stops before Phase 3; putting the human request (and the ready flip) in a `request-reviewers` action class keeps one-action-per-PR-per-tick bookkeeping honest and makes the dry-run promise structural instead of guarded. The bot trigger's placement is left alone (out of scope).
- **Test shape (honest harness limitation):** the gate tree is host-executed bash prose; like every other land gate it is pinned by static token assertions plus a dogfood tick, not a stubbed-`gh` harness (none exists, and G2 forbids prose pins). The deterministic halves — config key, schema, round-trip — get behavioral tests. A flowctl helper that evaluates the predicate from explicit inputs would make it unit-testable but is extra CLI surface for one predicate; revisit if §2.6b grows.
- Rejected "reuse `land.reviewTrigger` for humans" (an issue comment is not a review request and does not satisfy a ruleset) and "open PRs ready instead of draft" (draft is load-bearing for the bot trigger and the CI-fix cycle) — both per the issue's own alternatives.

## Early proof point

Task fn-200-land-request-human-reviewers-at.2 validates the core approach (the §2.6b predicate + one-shot + ready flip, pinned by the static workflow assertions and a dogfood `--dry-run` tick). If the predicate cannot be expressed from the gate state already captured in §2.4-§2.6 without a new GitHub read, re-evaluate the placement before the docs task.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | config key + schema + round-trip | fn-200-land-request-human-reviewers-at.1 | — |
| R2 | predicate, one-shot ledger, ready flip | fn-200-land-request-human-reviewers-at.2 | — |
| R3 | default unchanged | fn-200-land-request-human-reviewers-at.1, fn-200-land-request-human-reviewers-at.2 | — |
| R4 | failure handling | fn-200-land-request-human-reviewers-at.2 | — |
| R5 | dry-run zero-mutation | fn-200-land-request-human-reviewers-at.2 | — |
| R6 | silence + REVIEW_REQUIRED plans none | fn-200-land-request-human-reviewers-at.2 | — |
| R7 | docs + changelog + mirror | fn-200-land-request-human-reviewers-at.3 | — |
