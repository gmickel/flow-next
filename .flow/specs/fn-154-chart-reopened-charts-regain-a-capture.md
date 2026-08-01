# chart: reopened charts regain a capture door (briefing re-finalize after reopen)

## Goal & Context
<!-- scope: business -->

Found while dogfooding chart (3.13.0) as a downstream consumer: MergeFoundry's cockpit built a chart decision-map surface whose capture handoff renders ONLY from a `final` briefing (draft/stale never - their reviewer treated anything else as a stale-masquerade class). Driving the real binary through lifecycle edges surfaced one state where the CLI strands the operator:

**Repro (verified against the released 3.13.0 binary):**
1. `chart create` → `add-decision` → `resolve` → `briefing` - briefing B1 goes `final`, chart → `done`.
2. `chart reopen --reason "more work needed"` - chart → `open`, B1 correctly staled.
3. Nothing else. `reopen` stales briefings and `produced_specs` but does **not** re-open decisions (`flowctl.py:15120`), so the chart is `briefable: true` again the instant it reopens. Settling or adding anything here would move the fingerprint and mask the bug.
4. Run `chart briefing` with the **same proposal over the unchanged ledger** → the command is idempotent on the fingerprint and returns the existing **stale** B1 (`status: "stale"`, `chart_status: "open"`, `noop: true`). It does not re-finalize, does not mint B2, and prints no hint that a changed proposal is required. The early return at `flowctl.py:14899` fires *before* the `done|abandoned` guard that would otherwise have named the remedy.

Result: a `briefable: true` chart with **no capture-ready briefing and no path to one** short of the operator guessing that the proposal content must differ. Downstream surfaces that (correctly) gate capture on `final` render this honestly as inactive-with-no-door - but the door itself is upstream's to restore. The fingerprint idempotence is right for the normal case (double-invocation must not mint duplicate briefings); it is wrong when every briefing the fingerprint matches is stale.

## Scope
<!-- scope: technical -->

1. **Re-finalize on stale-only match.** When `chart briefing` finds an existing briefing by fingerprint AND that briefing's status is `stale` AND the chart is currently `briefable`, the match must produce a capture-ready outcome instead of a silent stale echo. Decide the mechanism at plan time - three candidates:
   - (a) restore the matched briefing to `final` (and chart → `done`), on the argument that an unchanged proposal over an unchanged ledger is the same conclusion re-reached; or
   - (b) mint the next briefing id (`B(n+1)`) as `final` with the same content, preserving the staled one as history; or
   - (c) make the fingerprint honest instead of special-casing the return branch: `reopen` already persists `reopened_at` (`flowctl.py:15122`), so folding it into the fingerprint blob changes identity on reopen but **not** on the final-briefing → done transition, which is the exact property the current exclusion protects (see Decision Context). Post-reopen re-briefs then mint `B(n+1)` naturally and identical retries *within* one reopen epoch stay idempotent.
   Either way the invariant becomes: **`briefing` on a briefable chart always ends with a final briefing** (or a hard error naming why not). Note that (a) is weaker than it looks: a `final → stale → final` round trip erases the reopen from the ledger, which contradicts fn-135's standing rule that reversals are preserved rather than deleted.
2. **Honest message on the idempotent path.** Whatever mechanism lands, the non-JSON output and the `--json` envelope must say what happened (`refinalized` / `superseded_stale` / equivalent), never silently return a stale object as if it were the requested outcome.
3. **Downstream-visible signal.** `chart show --json` already carries per-briefing `status`; ensure whatever new state transitions exist keep that field authoritative so read-only consumers need no new logic.
4. **Docs**: the chart skill's reopen section documents the re-finalize behavior; the `--force` draft path is untouched (drafts remain "never capture-ready").

## Boundaries
<!-- scope: business -->

- No change to fingerprint idempotence for the normal case (matching a `final` or `draft` briefing keeps today's behavior).
- No change to `reopen` staling semantics - staling on reopen is correct and is what made the downstream honesty rendering possible.
- No new flags required; this is the existing command doing the right thing on an edge.

## Decision Context
<!-- scope: both -->

**The root cause is a deliberate exclusion, not an oversight.** `chart_decision_revision` hashes id, outcome, title, decisions and parked questions, and **excludes `chart.status` on purpose** - the comment at `flowctl.py:14246` records why: so that a final-briefing → `done` transition does not break identical-fingerprint retries. `reopen` changes status, `reopened_at`, `reopen_reason` and the briefing/link `status` fields, and touches nothing else the fingerprint hashes, which is exactly how the stale echo happens. The obvious fix - add `chart.status` to the fingerprint - breaks the retry case that comment exists to protect. Any mechanism chosen at plan time must keep the final → done retry working, and should say so in its own comment rather than leaving the next reader to rediscover this.

**Why the fingerprint is the more interesting place to fix it.** Options (a) and (b) special-case one branch: a stale match. Option (c) makes the identity function tell the truth about what a reopen is, which closes the whole class (any future state change that should invalidate a briefing identity gets the same treatment) rather than the one instance found by dogfooding. That is a plan-time call, not a decision this spec forces, but the class-versus-instance difference is the thing worth weighing.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The repro above ends with a capture-ready (`final`) briefing: `reopen` → `briefing` **with the decision ledger untouched** (the only path on which the fingerprint still matches) yields a final briefing, restored or minted per the plan-time decision, with chart status consistent with it. Tested against the real CLI, and the test must assert the ledger is unchanged between reopen and re-brief - a test that settles anything in between moves the fingerprint and passes without exercising the defect.
- **R2:** The stale-echo path is gone: no invocation of `briefing` on a `briefable` chart can return only stale briefings without either producing a final one or erroring with a message that names the fingerprint idempotence and the remedy.
- **R3:** `--json` envelopes for the new path carry an explicit outcome discriminator; per-briefing `status` in `chart show --json` remains the single source of truth for capture-readiness (no consumer-side inference needed).
- **R4:** Draft (`--force`) semantics and normal idempotence are byte-unchanged (regression-tested); reopen staling untouched; docs updated in the same change.
