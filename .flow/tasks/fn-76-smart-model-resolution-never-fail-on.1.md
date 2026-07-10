## Description

Implement fn-76 v3.1 exactly as the epic spec defines (R1-R5). The epic spec IS the design — re-read it fully before coding. Size: M. All changes in flowctl.py (dual-copied to .flow/bin/flowctl.py) + tests + docs + mirror.

## Approach

1. **R1 ranking:** the registry `models` value is currently a Python `set` — an ORDERED ranking needs an ordered type. Change the per-backend `models` to a LIST (strongest first; keep every current entry), and adapt the (few) membership checks + `test_backend_spec.py` catalog assertions. `BackendSpec.parse` becomes warn-and-accept for unknown models (stderr one-liner); effort axis stays strict. Registry `default_model` stays and MUST equal the ranking's first entry (add a unit test asserting that invariant).
2. **R2 optimistic happy path:** unconfigured resolution returns the ranking top — assert in tests that the built exec argv is byte-identical to today's hardcoded-default argv and that NO extra subprocess (no --list-models) runs on the happy path.
3. **R3 fallback ladder:** wrap the exec call sites (codex/copilot/cursor review paths) with a fallback: iff the failure matches the backend's distinctive model-unavailable signature, retry per spec (cursor: consult `cursor-agent --list-models` ∩ ranking; codex/copilot: next ranking entry, max 2 steps; then floor: codex omit --model, copilot/cursor `auto`). Signatures (fixtures, captured live 2026-07-10): codex `"The '<m>' model requires a newer version of Codex"` and model-not-available 400s; copilot `Model "<m>" from --model flag is not available`. Cursor's signature is UNCAPTURED — capture it live during implementation by dispatching a fake model id (`cursor-agent -p --mode ask --model definitely-not-a-model-xyz "OK"`) and pin it as a fixture. Ladder retries happen BELOW the fn-90 review-round cap (one logical dispatch = one cap increment — do NOT call enforce_and_increment_review_cap again on retry). Any non-signature failure propagates unchanged.
4. **R4 cache:** `.flow/.cache/model-resolution.json`, atomic write, keyed `(backend, cli_version)`; explicit models bypass; distinctive-signature failure of a cached entry invalidates + re-resolves; corrupt/missing = cold start. Ensure `.flow/.cache/` is gitignored (check .flow/.gitignore or root .gitignore — sync-runs handling is precedent).
5. **R5 hygiene:** floor omits effort; receipts record actual model else "auto"/"default"; one stderr warning on downgrade/floor naming tried→used; docs (flowctl.md resolution section + troubleshooting entry); CHANGELOG `## Unreleased` entry (no version bump — batched); sync-codex regen + guard green.

## Acceptance

- [ ] All five epic R-IDs implemented as specified; explicit-pin paths byte-identical (regression-tested).
- [ ] Happy-path argv assertions per backend (no probe subprocess, ranking-top model present).
- [ ] Ladder unit tests from the captured signature fixtures (incl. cursor's, captured during this task); non-signature errors propagate; max-2-steps + floor covered.
- [ ] Cache round-trip + invalidation + corrupt-file tests; `.flow/.cache/` ignored by git.
- [ ] default_model == ranking[0] invariant test; full unittest suite + smoke_test.sh (from outside repo) green; dual-copy parity; mirror regenerated.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
