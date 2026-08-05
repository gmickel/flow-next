---
satisfies: [R4, R5]
---
# fn-168-review-convergence-lost-ratchet-prompt.4 End-to-end two-round proof, docs, CHANGELOG + full final gate

## Description
Prove the whole fix end-to-end on a scripted two-round transcript, land every doc surface, and run the full final gate for the spec.

**Size:** M
**Files:** `plugins/flow-next/tests/` (the e2e transcript test — extend the reservation/cap suite), `plugins/flow-next/docs/review-findings.md`, `plugins/flow-next/docs/README.md` ("Notable updates"), `plugins/flow-next/docs/troubleshooting.md`, `CHANGELOG.md`

### Approach
- **R4 three-round symmetry regression** (plan-review round 2): 6 fresh → 6 carried-unverified + 1 fresh → 7 carried-unverified + 1 fresh; round 3 allowed, and the reservation after it MUST classify the flat 1→1 fresh trajectory as a stall. Production reservation path.
- **R4 e2e**: script a two-round codex-style transcript — round 1 NEEDS_WORK with findings; round 2 NEEDS_WORK that resolves all priors via the stated grammar AND raises one new finding — and assert it reaches round 3 without ESCALATE under the default caps, driving the production reservation path (not a hand-built digest pair). Add the mirror-image case: a genuinely stalling transcript still ESCALATEs.
- **R5 docs**: `docs/review-findings.md` "Identity and lineage" states the literal per-ordinal grammar + the aggregate record + that `unaddressed: []` does not vouch for prior findings (prose-with-inline-code, matching the section's style — no new table). `docs/README.md` "Notable updates" gains a top bullet in the existing format (precedent: the 3.14.0 "Review loops end on convergence evidence" bullet). `docs/troubleshooting.md` (~:83) gains the false-`flat-trajectory` root cause to its list. Check `docs/flowctl.md` (~:2026) — a one-clause mention only if the receipt/back-compat prose is now stale.
- **CHANGELOG**: `## Unreleased`, outcome-first per `agent_docs/releasing.md` — a converging review loop (findings shrinking round over round) no longer falsely escalates at round 2; machinery last. NO version bump (batched releases).
- **FINAL GATE**: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .` + propagation verification (`cp` flowctl.py to `.flow/bin/`, `./scripts/sync-codex.sh` twice with no second-run diff) + `test_prompt_text_pinned` green with any hash change justified in its commit message.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/tests/test_review_convergence_cap.py` — the reservation/cap harness the e2e test must drive
- `plugins/flow-next/docs/review-findings.md` (~:100-121) — the "Identity and lineage" prose to extend
- `plugins/flow-next/docs/README.md` (~:54-70) — the "Notable updates" bullet format + the 3.14.0 precedent
- `CHANGELOG.md` (~:1-40) — entry shape; confirm the current released head before adding `## Unreleased`

**Optional** (reference as needed):
- `agent_docs/releasing.md` — the changelog ordering rules + hard rejection test
- `plugins/flow-next/docs/troubleshooting.md` (~:83) — the review-loop-stall root-cause list

### Key context
- Both changelogs are user-facing release surfaces: user outcome first, machinery last.
- Docs-only edits do not bump the plugin version; this whole spec stages under `## Unreleased`.
- The e2e test is the only place the fix is proven as a system rather than per-function — keep it driving production paths.
## Acceptance
- [ ] R4: two-round transcript reaches round 3 without ESCALATE via the production reservation path; the three-round 6 → 6+1 → 7+1 symmetry regression stalls on the flat 1→1 fresh trajectory; a genuinely stalling transcript still ESCALATEs
- [ ] `docs/review-findings.md` states the per-ordinal grammar, the aggregate record, and the `unaddressed: []` non-vouching note
- [ ] `docs/README.md` "Notable updates" bullet added in the existing format; `docs/troubleshooting.md` root-cause list extended
- [ ] CHANGELOG `## Unreleased` entry, outcome-first; no version bump
- [ ] Full suite green: `python3 scripts/run_tests_parallel.py`; `uvx ruff@0.16.0 check .` clean
- [ ] Propagation verified: flowctl.py copied to `.flow/bin/`; `./scripts/sync-codex.sh` run twice with no diff on the second run
- [ ] `test_prompt_text_pinned` green (any hash change justified in the commit message)
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
