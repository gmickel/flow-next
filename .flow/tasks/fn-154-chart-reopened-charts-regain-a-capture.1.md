---
satisfies: [R1, R2, R4, R5, R6]
---
# fn-154-chart-reopened-charts-regain-a-capture.1 Fingerprint the reopen epoch; never echo a stale briefing

## Description
Make briefing identity honest about reopens, and refuse to hand back a stale briefing as an idempotent answer.

Two changes in `plugins/flow-next/scripts/flowctl.py`:

1. **Reopen epoch in the briefing fingerprint.** `_briefing_fingerprint` (14263-14278) gains the chart's `reopened_at` as a fourth blob component. The key is **omitted entirely when the chart carries no reopen**, so every chart already on disk hashes byte-identically and its stored B-IDs keep matching an identical retry. Add a comment at the site explaining why `reopened_at` and not `chart.status`: status changes on the final-briefing -> done transition too, and the existing exclusion comment at 14246 exists to keep that retry idempotent.

   **Do NOT put the epoch in `chart_decision_revision`.** It is shared: it supplies `revision=` to `_maybe_project_chart` on every chart command (`10229`, `23381`), so an epoch there would shift the tracker projection revision and marker digest for charts unrelated to briefing. `_briefing_fingerprint` has exactly one caller (`14895`) inside `emit_chart_briefing` - the scope the defect lives in.
2. **Defensive stale guard.** The idempotent-return branch (14899-14913) must never return a briefing whose `status` is `stale`. With the epoch in the fingerprint this is unreachable through the CLI, but a sidecar written by a pre-fix binary or edited by hand can still present one. Fall through to the ordinary emission path (or raise a `ChartError` naming the fingerprint idempotence and the remedy) rather than echoing it.

Post-reopen re-briefs then reach the existing emission path unchanged, which already mints `B(n+1)`, recomputes draft-vs-final, rewrites the convenience copies, and runs inside `run_chart_transaction` under the single `cross_process_lock` acquisition. Do not add a second lock scope or a detect-then-act split.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_chart_briefing.py`, plus the propagation targets (`.flow/bin/flowctl.py`, `.flow/bin/flowctl_tracker/`, the generated `plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json` and its distribution copy `.flow/bin/flowctl_tracker/MANIFEST.json`, `plugins/flow-next/codex/`)

### Approach

- Follow the existing blob-construction style in `chart_decision_revision` (`flowctl.py:14212-14260`) - sorted keys, `json.dumps(..., sort_keys=True, separators=(",",":"))`, sha256 hex.
- Raise errors with `ChartError(<class>, <code>, <message>, details={...})` as every other chart path does; classes are `CHART_ERROR_CLASSES` at `flowctl.py:195-205`.
- New tests go in `plugins/flow-next/tests/test_chart_briefing.py` and drive the REAL CLI via the existing `_run_flowctl` subprocess helper (`62-78`) and the `_brief` / `_create_chart` / `_resolve` helpers - that is the established pattern in this file, no new harness.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:14212-14310` - `_briefing_fingerprint` (the change site), `chart_decision_revision` (shared - read it to see why it is NOT the change site), `_briefing_evidence_digest`, `_next_briefing_id`
- `plugins/flow-next/scripts/flowctl.py:10229` and `:23381` - the two `_maybe_project_chart(revision=chart_decision_revision(...))` call sites that make that function off-limits here
- `plugins/flow-next/scripts/flowctl.py:14843-15086` - `emit_chart_briefing`, especially the match loop at 14899-14913 and the done/abandoned guard at 14915-14922
- `plugins/flow-next/scripts/flowctl.py:15089-15196` - `reopen_chart`, which fields it writes (`reopened_at` at 15122)
- `plugins/flow-next/tests/test_chart_briefing.py:337-408` - `TestFingerprintVersioning.test_b1_idempotent_and_b2_on_change`, the nearest existing pin

**Optional** (reference as needed):
- `plugins/flow-next/scripts/flowctl.py:10950-10988` - `run_chart_transaction`
- `plugins/flow-next/tests/test_chart_briefing.py:1358-1436` - the failpoint test the new path must survive

### Key context

Do NOT add `chart.status` to the fingerprint - the exclusion at `flowctl.py:14246` is deliberate and protects the final-briefing -> done retry.

The conditional-omission rule in change 1 is the whole of R5: an unconditional key (even one hashing to null) changes the blob for every existing chart and silently breaks stored B-ID matching after the upgrade. Prove it with a pre-fix golden fixture, not a same-version round trip - the latter passes even when both sides use a newly incompatible hash.

`flowctl.py` edits require the propagation chain or `test_tracker_distribution` fails: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py` (never overwrite the bash launcher `.flow/bin/flowctl`), `rsync -a --delete --exclude __pycache__ plugins/flow-next/scripts/flowctl_tracker/ .flow/bin/flowctl_tracker/`, `python3 scripts/gen_tracker_manifest.py`, then `./scripts/sync-codex.sh` twice.

### Acceptance
- [ ] `_briefing_fingerprint` includes the reopen epoch, and omits the key entirely when the chart has never been reopened; `chart_decision_revision` is untouched
- [ ] A comment at the site records why `reopened_at` is the right epoch marker and `chart.status` is not
- [ ] The idempotent-return branch never returns a briefing whose status is `stale`; it falls through to a fresh emission or raises a `ChartError` naming the remedy
- [ ] Real-CLI test: create -> resolve -> brief (final, chart done) -> reopen -> brief with the SAME proposal file and an unchanged ledger -> a `final` briefing exists; the test asserts the decision ledger is byte-identical between reopen and re-brief (R1)
- [ ] Golden-fixture test (R5a): a checked-in chart sidecar whose briefing fingerprint was produced by the PRE-FIX algorithm still matches under the updated real CLI - original B-ID, `noop`. A same-version emit-then-retry does NOT prove this and is not a substitute
- [ ] Same-version retry kept as an ordinary regression test (R5b)
- [ ] Real-CLI test: a planted stale-but-fingerprint-matching briefing is never echoed back (R6)
- [ ] `TestFingerprintVersioning`, `TestEvidenceFingerprint`, `TestVersionedBriefingPaths`, `TestDoneAndMutations`, `TestForcedDraft`, `TestBriefingFailpoint` all still pass unmodified (R4)
- [ ] Propagation chain run; `cd plugins/flow-next/tests && python3 -m unittest test_chart_briefing -q` green
## Acceptance
- [ ] Reopen epoch folded into `_briefing_fingerprint` (NOT `chart_decision_revision`), key omitted when the chart has never been reopened
- [ ] Site comment explains why `reopened_at` and not `chart.status`
- [ ] Stale briefings are never returned as an idempotent answer
- [ ] R1 repro passes against the real CLI with an asserted-unchanged ledger
- [ ] R5a golden pre-fix fixture matches under the updated CLI; R5b same-version retry regression also passes
- [ ] R6 planted-stale-match test passes
- [ ] All pre-existing chart briefing tests pass unmodified
- [ ] Propagation chain run and focused suite green
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
