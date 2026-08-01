# chart: reopened charts regain a capture door (briefing re-finalize after reopen)

## Overview

`flowctl chart briefing` is idempotent on a content fingerprint so a double invocation cannot mint duplicate briefings. `chart reopen` stales the existing briefing but changes nothing the fingerprint hashes, so re-running `briefing` on the reopened chart matches the old fingerprint and echoes the **stale** briefing back with `noop: true`. The operator is left holding a `briefable: true` chart with no capture-ready briefing and no path to one.

The fix makes the identity function honest rather than special-casing the echo: a reopen is a new epoch, so a briefing emitted after it is a different briefing. Post-reopen re-briefs then take the **ordinary emission path** - which already mints `B(n+1)`, recomputes draft-vs-final from the live chart, rewrites the convenience copies, runs inside the existing WAL transaction and lock, and projects to the tracker. Every edge the analysis surfaced dissolves there instead of needing its own branch.

## Quick commands

Focused suites for this change:

```bash
cd plugins/flow-next/tests && python3 -m unittest test_chart_briefing test_capture_chart_handoff test_chart_tracker_projection -q
```

Manual end-to-end repro (the R1 path), against the real CLI:

```bash
.flow/bin/flowctl chart briefing <chart-id> --proposal-file p.json --json   # final, chart -> done
.flow/bin/flowctl chart reopen <chart-id> --reason "more work" --json       # open, B1 stale
.flow/bin/flowctl chart briefing <chart-id> --proposal-file p.json --json   # SAME file: must end final
```

Final gate, once:

```bash
python3 scripts/run_tests_parallel.py
uvx ruff@0.16.0 check .
```

`flowctl.py` changes require the propagation chain before the gate:

```bash
cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py
rsync -a --delete --exclude __pycache__ plugins/flow-next/scripts/flowctl_tracker/ .flow/bin/flowctl_tracker/
python3 scripts/gen_tracker_manifest.py
./scripts/sync-codex.sh
./scripts/sync-codex.sh
```

## Goal & Context
<!-- scope: business -->

Found while dogfooding chart (3.13.0) as a downstream consumer: MergeFoundry's cockpit built a chart decision-map surface whose capture handoff renders ONLY from a `final` briefing (draft/stale never - their reviewer treated anything else as a stale-masquerade class). Driving the real binary through lifecycle edges surfaced one state where the CLI strands the operator:

**Repro (verified against the released 3.13.0 binary):**
1. `chart create` -> `add-decision` -> `resolve` -> `briefing` - briefing B1 goes `final`, chart -> `done`.
2. `chart reopen --reason "more work needed"` - chart -> `open`, B1 correctly staled.
3. Nothing else. `reopen` stales briefings and `produced_specs` but does **not** re-open decisions (`flowctl.py:15120`), so the chart is `briefable: true` again the instant it reopens. Settling or adding anything here would move the fingerprint and mask the bug.
4. Run `chart briefing` with the **same proposal over the unchanged ledger** -> the command is idempotent on the fingerprint and returns the existing **stale** B1 (`status: "stale"`, `chart_status: "open"`, `noop: true`). It does not re-finalize, does not mint B2, and prints no hint that a changed proposal is required. The early return at `flowctl.py:14899` fires *before* the `done|abandoned` guard that would otherwise have named the remedy.

Result: a `briefable: true` chart with **no capture-ready briefing and no path to one** short of the operator guessing that the proposal content must differ. Downstream surfaces that (correctly) gate capture on `final` render this honestly as inactive-with-no-door - but the door itself is upstream's to restore. The fingerprint idempotence is right for the normal case (double-invocation must not mint duplicate briefings); it is wrong when every briefing the fingerprint matches is stale.

## Architecture & Data Models
<!-- scope: technical -->

**Chosen mechanism: fold the reopen epoch into the fingerprint (candidate (c)).** `reopen_chart` already persists `reopened_at` (`flowctl.py:15122`). Adding it to the fingerprint blob changes briefing identity on reopen but **not** on the final-briefing -> `done` transition, which is the exact property the deliberate `chart.status` exclusion protects (`flowctl.py:14246`).

Three sites:

1. **`_briefing_fingerprint`** (`flowctl.py:14263-14278`) - the blob gains the chart's reopen epoch as a fourth component. **The key is omitted entirely when the chart has never been reopened**, so every chart on disk today hashes byte-identically and its stored B-IDs keep matching. This is what keeps R4's "normal idempotence byte-unchanged" true across the upgrade rather than only for charts created after it.

   **Not `chart_decision_revision`.** That function looks like the natural home, but it is *shared*: it supplies `revision=` to `_maybe_project_chart` on every chart command (`flowctl.py:10229`, `23381`), so an epoch added there would change the tracker projection revision and marker digest for charts that have nothing to do with briefing. `_briefing_fingerprint` has exactly one caller (`14895`), inside `emit_chart_briefing`, which is the scope the defect actually lives in.
2. **The idempotent-return branch** (`flowctl.py:14899-14913`) - gains a defensive guard: a fingerprint match whose `status` is `stale` is never returned as an idempotent answer. With the epoch in the fingerprint this should be unreachable through the CLI, but a chart written by a pre-fix binary or a hand-edited sidecar can still present one, and a stale briefing has no valid reading as "the requested outcome."
3. **The result payload and the non-JSON print branch** (`flowctl.py:15059-15086`, `24248-24259`) - a fresh emission that supersedes stale predecessors says so, in both the envelope and the human line. The human branch today can only print `status=<val> (noop)`, which is exactly the misleading output the report describes.

**The discriminator contract (fixed here, not at implementation time).** The `--json` result of a fresh emission carries:

| | |
|---|---|
| **Field** | `supersedes_stale` |
| **Type** | array of strings (B-IDs, e.g. `["B1"]`), in sidecar order |
| **Presence** | **only** on a fresh emission (`noop: false`) that follows at least one `stale` briefing, and only when the array is non-empty. Absent from every idempotent-retry result, every first-emission result, and every error envelope. |
| **Human line** | the non-JSON branch prints the minted B-ID and the superseded ones on the same line |

Presence *is* the discriminator: a consumer keys on the field existing. Absence keeps every envelope that exists today byte-identical, which is what makes R4 true rather than merely intended.

`Outcome` is a load-bearing chart term already (the map's stated goal, the `## Outcome` heading, `chart create --outcome`), which is why the field is **not** named `outcome` - a second meaning in the same envelope family would make the docs self-contradictory.

**What this mechanism buys, versus a guarded stale-match branch.** Post-reopen re-briefs reach the *existing* emission path, so: draft-vs-final is recomputed fresh from `briefable` + this invocation's `--force` (a stale-that-was-a-draft can never silently regain `final`); the convenience copies `<id>-briefing.md` / `-briefing-<k>.md` are rewritten in step with the sidecar; multi-cluster proposals work unchanged; a second reopen mints again; a reopen sourced from `abandoned` behaves like one sourced from `done`; the write happens inside the existing `run_chart_transaction` under the single `cross_process_lock` acquisition, so no detect-then-act TOCTOU window is introduced and WAL recovery is unchanged; and the tracker projection fires as it does for any ordinary emission.

## Boundaries
<!-- scope: business -->

- No change to fingerprint idempotence for the normal case (matching a `final` or `draft` briefing on a chart that was never reopened keeps today's behavior, byte for byte).
- No change to `reopen` staling semantics - staling on reopen is correct and is what made the downstream honesty rendering possible.
- No new flags required; this is the existing command doing the right thing on an edge.
- **`produced_specs[]` links staled by a reopen stay stale.** A new final briefing does not un-stale spec links: those specs were built from the earlier briefing and a human decides whether they still hold. Out of scope here, deliberately.
- **`chart link-spec` stays ungated.** It never reads briefing `status` today; capture's draft/stale fail-closed admission is a skill-level contract. Adding enforcement there is a separate decision, not this fix.
- **No new lifecycle command and no `unstale` verb.** The only new behavior is what an ordinary `briefing` invocation does after a reopen.

## Decision Context
<!-- scope: both -->

**The root cause is a deliberate exclusion, not an oversight.** `chart_decision_revision` hashes id, outcome, title, decisions and parked questions, and **excludes `chart.status` on purpose** - the comment at `flowctl.py:14246` records why: so that a final-briefing -> `done` transition does not break identical-fingerprint retries. `reopen` changes status, `reopened_at`, `reopen_reason` and the briefing/link `status` fields, and touches nothing else the fingerprint hashes, which is exactly how the stale echo happens. The obvious fix - add `chart.status` to the fingerprint - breaks the retry case that comment exists to protect. `reopened_at` is the field that changes on reopen and *not* on the done transition, which is why it is the right epoch marker; the fix must say so in a comment at the site rather than leaving the next reader to rediscover it.

**Why the fingerprint and not a guarded branch.** Options (a) restore-in-place and (b) mint-at-the-stale-match both special-case one branch. Making the identity function truthful closes the class: any post-reopen re-brief becomes an ordinary emission, and the five edge cases the gap analysis surfaced (draft flattening, first-match-wins over an older stale entry, convenience-copy drift, second reopen, abandoned-sourced reopen) stop needing individual handling because none of them reach a special branch.

**Why (a) was rejected outright.** A stale-match return performs no file writes, but `<id>-briefing.md` is rewritten on *every* emission. Restoring an older stale briefing's status in place would leave the sidecar claiming `final` while the on-disk convenience copy holds a later, different briefing's content - the exact stale-masquerade class the downstream consumer refuses. It also contradicts fn-135 R41 (briefings are immutable and versioned) and R45 (a changed proposal or chart revision allocates the next B-ID): a `final -> stale -> final` round trip erases the reopen from the ledger.

**Why the defensive guard stays even though the epoch makes it unreachable.** Charts written by a pre-fix binary carry fingerprints computed without the epoch; a hand-edited or externally-produced sidecar can carry anything. "Never hand back a stale briefing as the answer" is the invariant the downstream consumer actually depends on, so it is enforced where it is read, not only where it is written.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The repro above ends with a capture-ready (`final`) briefing: `reopen` -> `briefing` **with the decision ledger untouched** (the only path on which the fingerprint still matches) yields a final briefing, restored or minted per the plan-time decision, with chart status consistent with it. Tested against the real CLI, and the test must assert the ledger is unchanged between reopen and re-brief - a test that settles anything in between moves the fingerprint and passes without exercising the defect.
- **R2:** The stale-echo path is gone: no invocation of `briefing` on a `briefable` chart can return only stale briefings without either producing a final one or erroring with a message that names the fingerprint idempotence and the remedy.
- **R3:** `--json` envelopes for the new path carry an explicit outcome discriminator; per-briefing `status` in `chart show --json` remains the single source of truth for capture-readiness (no consumer-side inference needed).
- **R4:** Draft (`--force`) semantics and normal idempotence are byte-unchanged (regression-tested); reopen staling untouched; docs updated in the same change.
- **R5:** Charts that have never been reopened keep byte-identical briefing fingerprints across this change - the epoch key is absent from the hashed blob when the chart carries no reopen, so a B-ID minted by a **pre-fix** binary still matches an identical retry after the upgrade. Proven by **two** tests, because same-version emit-then-retry only demonstrates ordinary idempotence and would pass even if both sides used a newly incompatible hash: (a) a **golden fixture** - a chart sidecar whose stored briefing fingerprint was produced by the pre-fix algorithm, checked in as test data, against which the updated real CLI returns the original B-ID with `noop`; and (b) a same-version retry kept as an ordinary regression test.
- **R6:** A briefing whose status is `stale` is never returned as an idempotent answer, even when its fingerprint matches - the defensive guard holds for sidecars written by a pre-fix binary or edited by hand. Proven by a test that plants a stale-but-matching briefing and asserts the command mints a final one (or errors naming the remedy) rather than echoing it.
- **R7:** Draft-vs-final is recomputed per invocation from the live chart, never inherited from a stale predecessor: a chart whose only briefing is a staled `--force` draft cannot produce a `final` briefing unless the chart is genuinely briefable, and a `--force` retry after reopen still yields a draft. Proven by a test - reopen flattens `draft` and `final` alike to `stale`, so status alone cannot distinguish them.
- **R8:** The fix is state-source-agnostic and repeatable, proven by two **exactly specified** sequences (a loose "behaves identically" test is vacuous here: `abandon` is legal only from `open`, so an abandoned chart can carry no briefing at all, and reopen-then-brief would simply mint B1 without ever touching stale-fingerprint handling):
  - **abandoned source:** open chart with an unresolved decision -> `briefing --force` mints **draft** B1, chart stays open -> `abandon` -> `reopen` -> `briefing --force` with the **identical** proposal -> B1 is `stale` and a new **draft** B2 is minted. It must NOT become final: the chart is still unbriefable.
  - **second round trip:** the R1 done-sourced path continued - after final B2 and chart `done`, `reopen` again -> `briefing` with the identical proposal -> final B3, chart `done`. A second reopen must mint again rather than re-match B2.
- **R9:** The `supersedes_stale` field ships exactly as specified in Architecture & Data Models - name, array-of-B-ID type, and presence-only-on-a-superseding-fresh-emission rule - and is **not** named `outcome`. It is documented in `docs/flowctl.md` alongside the envelope error classes and pinned by an assertion in `test_chart_docs_inventory.py`, so the doc cannot silently drift from the code. A test asserts the field is **absent** from a first-emission and from an idempotent-retry envelope, which is what makes R4's byte-unchanged claim checkable rather than assumed.

## Early proof point

Task fn-154-chart-reopened-charts-regain-a-capture.1 validates the core approach: that folding the reopen epoch into `_briefing_fingerprint` fixes the repro **while keeping every existing idempotence pin green** (`TestFingerprintVersioning`, `TestEvidenceFingerprint`, `TestVersionedBriefingPaths`, `TestDoneAndMutations`, `TestForcedDraft`, `TestBriefingFailpoint`).

If it fails - if the epoch cannot be added without breaking existing fingerprint pins, or the conditional-omission compatibility rule proves unworkable - fall back to mechanism (b): mint `B(n+1)` from a guarded stale-match branch inside the same transaction, and carry the draft-recompute and convenience-copy rewrite explicitly rather than inheriting them from the ordinary path.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Repro ends with a final briefing (real CLI, ledger unchanged) | .1, .2 | - |
| R2 | Stale-echo path gone | .1 | - |
| R3 | `--json` discriminator; `chart show` status stays authoritative | .2 | - |
| R4 | `--force` and normal idempotence byte-unchanged | .1, .2, .3 | - |
| R5 | Never-reopened charts keep byte-identical fingerprints | .1 | - |
| R6 | A stale briefing is never an idempotent answer | .1 | - |
| R7 | Draft-vs-final recomputed per invocation | .2 | - |
| R8 | Abandoned-sourced reopen + second round trip | .2 | - |
| R9 | `supersedes_stale` ships to contract; documented and pinned | .2, .3 | - |

## References

- Bug site: `plugins/flow-next/scripts/flowctl.py:14899-14913` (idempotent-return branch), `14915-14922` (done/abandoned guard)
- Fingerprint: `_briefing_fingerprint` `14263-14278` (single caller, `14895` - the change site); `chart_decision_revision` `14212-14260` (SHARED - also feeds `_maybe_project_chart(revision=...)` at `10229` and `23381`; do not touch); `_briefing_evidence_digest` `14281-14295`
- Emission: `emit_chart_briefing` `14843-15086`; convenience-copy rewrite `14945-14948`, `14974-14990`; `_next_briefing_id` `14298-14307`
- Reopen: `reopen_chart` `15089-15196` (`reopened_at` at `15122`; staling loop `15130-15139`; `produced_specs` `15144-15160`)
- Transactions: `run_chart_transaction` `10950-10988`, `_chart_failpoint` `10419-10428`, lock `charts_resource_lock_path` `10056`
- Envelope: `chart_json_success` `10103`, `chart_fail` `10151`, `CHART_ERROR_CLASSES` `195-205`
- Handlers: `cmd_chart_briefing` `24203-24260` (non-JSON print `24248-24259`), `cmd_chart_reopen` `24262-24301`
- Tracker projection: `flowctl_tracker/facade/chart_projection.py:47`, `90-110`
- Tests: `plugins/flow-next/tests/test_chart_briefing.py` (real-CLI via `_run_flowctl` `62-78`); `TestFingerprintVersioning` `337-408`, `TestForcedDraft` `302-334`, `TestBriefingFailpoint` `1358-1436`, `TestReopenFromAbandoned` `1438-1466`
- fn-135 constraints: R41 (briefings are immutable and versioned), R45 (identical fingerprint reuses a B-ID; a changed proposal or chart revision allocates the next). R23 governs D-ID allocation, NOT briefings - do not cite it here.
