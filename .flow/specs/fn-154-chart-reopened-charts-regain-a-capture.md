# chart: reopened charts regain a capture door (briefing re-finalize after reopen)

## Goal & Context
<!-- scope: business -->

Found while dogfooding chart (3.13.0) as a downstream consumer: MergeFoundry's cockpit built a chart decision-map surface whose capture handoff renders ONLY from a `final` briefing (draft/stale never — their reviewer treated anything else as a stale-masquerade class). Driving the real binary through lifecycle edges surfaced one state where the CLI strands the operator:

**Repro (verified against the released 3.13.0 binary):**
1. `chart create` → `add-decision` → `resolve` → `briefing` — briefing B1 goes `final`, chart → `done`.
2. `chart reopen --reason "more work needed"` — chart → `open`, B1 correctly staled.
3. Settle the remaining decisions so the chart is `briefable: true` again.
4. Run `chart briefing` with an **unchanged proposal fingerprint** → the command is idempotent on the fingerprint and returns the existing **stale** B1 (`status: "stale"`, `chart_status: "open"`). It does not re-finalize, does not mint B2, and prints no hint that a changed proposal is required.

Result: a `briefable: true` chart with **no capture-ready briefing and no path to one** short of the operator guessing that the proposal content must differ. Downstream surfaces that (correctly) gate capture on `final` render this honestly as inactive-with-no-door — but the door itself is upstream's to restore. The fingerprint idempotence is right for the normal case (double-invocation must not mint duplicate briefings); it is wrong when every briefing the fingerprint matches is stale.

## Scope
<!-- scope: technical -->

1. **Re-finalize on stale-only match.** When `chart briefing` finds an existing briefing by fingerprint AND that briefing's status is `stale` AND the chart is currently `briefable`, the match must produce a capture-ready outcome instead of a silent stale echo. Decide the mechanism at plan time — the two candidates:
   - (a) restore the matched briefing to `final` (and chart → `done`), on the argument that an unchanged proposal over a re-settled ledger is the same conclusion re-reached; or
   - (b) mint the next briefing id (`B(n+1)`) as `final` with the same content, preserving the staled one as history.
   Either way the invariant becomes: **`briefing` on a briefable chart always ends with a final briefing** (or a hard error naming why not).
2. **Honest message on the idempotent path.** Whatever mechanism lands, the non-JSON output and the `--json` envelope must say what happened (`refinalized` / `superseded_stale` / equivalent), never silently return a stale object as if it were the requested outcome.
3. **Downstream-visible signal.** `chart show --json` already carries per-briefing `status`; ensure whatever new state transitions exist keep that field authoritative so read-only consumers need no new logic.
4. **Docs**: the chart skill's reopen section documents the re-finalize behavior; the `--force` draft path is untouched (drafts remain "never capture-ready").

## Boundaries / non-goals

- No change to fingerprint idempotence for the normal case (matching a `final` or `draft` briefing keeps today's behavior).
- No change to `reopen` staling semantics — staling on reopen is correct and is what made the downstream honesty rendering possible.
- No new flags required; this is the existing command doing the right thing on an edge.

## Acceptance Criteria

- **R1:** The repro above ends with a capture-ready (`final`) briefing: reopen → re-settle → `briefing` with an unchanged proposal yields a final briefing (restored or minted per the plan-time decision), chart status consistent with it (tested against the real CLI).
- **R2:** The stale-echo path is gone: no invocation of `briefing` on a `briefable` chart can return only stale briefings without either producing a final one or erroring with a message that names the fingerprint idempotence and the remedy.
- **R3:** `--json` envelopes for the new path carry an explicit outcome discriminator; per-briefing `status` in `chart show --json` remains the single source of truth for capture-readiness (no consumer-side inference needed).
- **R4:** Draft (`--force`) semantics and normal idempotence are byte-unchanged (regression-tested); reopen staling untouched; docs updated in the same change.
