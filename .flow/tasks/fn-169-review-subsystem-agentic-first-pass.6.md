---
satisfies: [R6, R7]
---
# fn-169-review-subsystem-agentic-first-pass.6 Enforcement (strategy + planning trip-wires + executable ratchet), docs, CHANGELOG, full gate

## Description
Make the decision stick this time, then document and gate.

**Size:** M
**Files:** `STRATEGY.md`, `CLAUDE.md`, `plugins/flow-next/tests/` (no-embed ratchet test), `plugins/flow-next/docs/orchestration.md`, `docs/flowctl.md`, `docs/review-findings.md`, the three `workflow-host.md` files, `CHANGELOG.md`

### Approach
- **Three layers, because prose alone already failed twice.** fn-74 made this exact decision, eval-validated it, deleted the code, and wrote it in a CHANGELOG — and it was reversed by fn-90 and fn-159, each with a good local reason.
  1. `STRATEGY.md` — the principle: pass identities, not payloads; the reviewer is an agent with a shell and a checkout. Use `/flow-next:strategy` to edit.
  2. `CLAUDE.md`'s **"How to spot a mistake"** list — the planning-time trip-wire agents actually read before designing a feature. Add: *embedding content the reviewer could fetch itself*; *writing a fitter/truncator for a prompt payload*; *adding a budget constant to a prompt path*. This is the layer that would have caught fn-90 and fn-159, because both were planning decisions.
  3. An **executable test**: the built review prompt (non-`export`) contains no diff body, no spec body, and no rendered prior items. Name the offending tag in the failure message so a future regression is self-explaining.
- Docs: `orchestration.md`, `flowctl.md`, `review-findings.md`, and the three `workflow-host.md` files state fetch-not-embed, the resumed-vs-injected split, and the host exception. Regenerate the codex mirror (`sync-codex.sh` twice, no second-run diff).
- CHANGELOG `## Unreleased`, outcome-first per `agent_docs/releasing.md` (unheaded user-outcome paragraph required — the value spans several bullets). Lead with what stops happening to the human and to the bill.
- **No release until fn-168 AND fn-169 have both landed.** Both entries ship together; no version bump inside either spec.
- Full gate: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .` + propagation (`cp` flowctl.py, `sync-codex.sh` twice) + `test_prompt_text_pinned` green.

### Investigation targets
**Required:**
- `CLAUDE.md` "Architecture: agentic vs deterministic" + its "How to spot a mistake" symptom list — the insertion point
- `agent_docs/releasing.md` — CHANGELOG ordering rules and the mandatory outcome paragraph
- `STRATEGY.md` — current tracks, and the `/flow-next:strategy` skill that owns edits
- `plugins/flow-next/docs/orchestration.md`, `docs/flowctl.md`, `docs/review-findings.md`

**Optional:**
- 2.5.0 CHANGELOG — what fn-74 wrote, and why writing it there was not enough

### Key context
- Deps `.5`: do not claim the outcome in docs or CHANGELOG before the eval gate passes.
- The no-embed test is the artifact fn-74 omitted. A CHANGELOG entry is not a constraint; a failing test is.
- Host and `export` exceptions must be documented as deliberate and tested, or they read as oversights to the next reader.

## Acceptance
- [ ] `STRATEGY.md` records the identities-not-payloads principle
- [ ] `CLAUDE.md`'s "How to spot a mistake" list gains the three planning-time trip-wires
- [ ] An executable test asserts the non-`export` review prompt carries no diff body, no spec body, and no rendered prior items, and names the offending tag on failure
- [ ] Host and `export` exceptions documented as deliberate, with tests
- [ ] `orchestration.md`, `flowctl.md`, `review-findings.md`, and the three `workflow-host.md` files updated; codex mirror regenerated twice with no second-run diff
- [ ] CHANGELOG `## Unreleased`, outcome-first, with the mandatory unheaded user-outcome paragraph; no version bump
- [ ] Release note recorded: no release until fn-168 and fn-169 have both landed
- [ ] Full gate green: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`; `test_prompt_text_pinned` green; propagation verified

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
