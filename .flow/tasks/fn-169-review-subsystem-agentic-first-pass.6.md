---
satisfies: [R5, R6, R7]
---
# fn-169-review-subsystem-agentic-first-pass.6 Enforcement (strategy + planning trip-wires + executable ratchet), docs, CHANGELOG, full gate

## Description
Make the decision stick this time, then document and gate.

**Size:** M
**Files:** `STRATEGY.md`, `CLAUDE.md`, `plugins/flow-next/tests/` (no-embed ratchet test), `plugins/flow-next/docs/orchestration.md`, `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/review-findings.md`, the three `workflow-host.md` files, `CHANGELOG.md`

### Approach
- **Three layers, because prose alone already failed twice.** fn-74 made this exact decision, eval-validated it, deleted the code, and wrote it in a CHANGELOG — and it was reversed by fn-90 and fn-159, each with a good local reason.
  1. `STRATEGY.md` + the `CLAUDE.md` trip-wires — **already landed in `.1`** so review rounds could read them. Verify they are present and still accurate; do not duplicate.
  2. `CLAUDE.md`'s **"How to spot a mistake"** list — the planning-time trip-wire agents actually read before designing a feature. Add: *embedding content the reviewer could fetch itself*; *writing a fitter/truncator for a prompt payload*; *adding a budget constant to a prompt path*. This is the layer that would have caught fn-90 and fn-159, because both were planning decisions.
  3. An **executable test**: the built review prompt (non-`export`) contains no diff body, no spec body, and no rendered prior items. Name the offending tag in the failure message so a future regression is self-explaining.
- Docs (canonical paths — all three live under `plugins/flow-next/docs/`, there is no repo-root `docs/`): `plugins/flow-next/docs/orchestration.md`, `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/review-findings.md`, and the three `workflow-host.md` files state fetch-not-embed, the resumed-vs-injected split, and the host exception. Regenerate the codex mirror (`sync-codex.sh` twice, no second-run diff).
- CHANGELOG `## Unreleased`, outcome-first per `agent_docs/releasing.md` (unheaded user-outcome paragraph required — the value spans several bullets). Lead with what stops happening to the human and to the bill.
- **No release until fn-168 AND fn-169 have both landed.** Both entries ship together; no version bump inside either spec.
- Full gate: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .` + propagation (`cp` flowctl.py, `sync-codex.sh` twice) + `test_prompt_text_pinned` green.

### Investigation targets
**Required:**
- `CLAUDE.md` "Architecture: agentic vs deterministic" + its "How to spot a mistake" symptom list — the insertion point
- `agent_docs/releasing.md` — CHANGELOG ordering rules and the mandatory outcome paragraph
- `STRATEGY.md` — current tracks, and the `/flow-next:strategy` skill that owns edits
- `plugins/flow-next/docs/orchestration.md`, `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/review-findings.md`

**Optional:**
- 2.5.0 CHANGELOG — what fn-74 wrote, and why writing it there was not enough

### Key context
- Deps `.4` (the eval tasks `.2`/`.5` were removed — see the spec's no-eval decision). Do not claim an outcome in docs or CHANGELOG that this spec's own PR review has not demonstrated.
- The no-embed test is the artifact fn-74 omitted. A CHANGELOG entry is not a constraint; a failing test is.
- Host and `export` exceptions must be documented as deliberate and tested, or they read as oversights to the next reader.

## Acceptance
- [ ] `STRATEGY.md` records the identities-not-payloads principle
- [ ] `CLAUDE.md`'s "How to spot a mistake" list gains the three planning-time trip-wires
- [ ] An executable test asserts the non-`export` review prompt carries no diff body, no spec body, and no rendered prior items, and names the offending tag on failure
- [ ] Host and `export` exceptions documented as deliberate, with tests
- [ ] `plugins/flow-next/docs/{orchestration,flowctl,review-findings}.md` and the three `workflow-host.md` files updated; codex mirror regenerated twice with no second-run diff
- [ ] CHANGELOG `## Unreleased`, outcome-first, with the mandatory unheaded user-outcome paragraph; no version bump
- [ ] Release note recorded: no release until fn-168 and fn-169 have both landed
- [ ] **Dogfood evidence recorded**: this spec's own PR was reviewed through the new fetch-not-embed path — verdict delivered, findings citing resolvable paths, and the prompt-token delta taken from the review receipts against the known baseline (impl-reviews 544k-1.12M, completion review 3.45M input tokens)
- [ ] Full gate green: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`; `test_prompt_text_pinned` green; propagation verified

## Done summary
Three layers of enforcement, docs, and a CHANGELOG that no longer claims more than the evidence supports.

**Why three layers.** fn-74 made this exact decision, validated it with an eval, deleted the embedding code, and wrote it in a CHANGELOG. fn-90 re-added the diff body; fn-159 re-added it with a fitter. Each had a good local reason, and nothing failed when they did. A CHANGELOG entry is not a constraint.

1. **STRATEGY.md + CLAUDE.md** (landed in `.1` so the review rounds could read them): the "identities, not payloads" principle, and three planning-time trip-wires in "How to spot a mistake" — embedding fetchable content, writing a payload fitter/truncator/budget, and enumerating ways-to-do-it-wrong.
2. **An executable ratchet.** First attempt was vacuous, and the reviewer caught it: it asserted sentinels absent that were never fed in, so re-adding a `diff_content=` parameter would have left it green. Now it drives `cmd_backend_review` with the git reads and task spec mocked to return sentinel-bearing content, intercepts the dispatch, and inspects the prompt that would have crossed the process boundary — **verified by simulating the regression and watching it go red**. Alongside it, the old `files_embedded`/`embedded_files` name screen became an exact signature PIN, because a name list is a race against the next spelling: those two were banned and fn-90 walked straight past them with `diff_content`.
3. **Docs**: `orchestration.md` gains the identity contract, the transport-vs-content distinction, and the per-backend resume matrix; `flowctl.md` documents the prompt slots per review kind and the loud-failure behavior; `review-findings.md` records why nothing shortens a prompt any more and why prior findings are the one payload with no identity to pass instead. All three `workflow-host.md` files state the host always-inject exception — and their dispatch steps were rewritten too, since the reviewer found they still said "the final diff" directly below the new paragraph forbidding it.

**The CHANGELOG got corrected, not framed.** The acceptance criterion asks for receipt-derived telemetry, so I pulled per-round `usage` from all ten dispatches — and it contradicted what I had written. Input tokens ran 3.49M–5.55M, *above* the 544k–1.12M recorded for fn-168's pre-identity reviews, because a fetching reviewer moves cost off the prompt and onto conversation turns (91–96% cached, so billable cost does not track the raw number — but a saving is not demonstrated, and the comparison is confounded by diff size and round count anyway). Wall-clock is worse too: three dispatches hit the fixed 600s bound. So the entry no longer opens with "gets cheaper", no longer says "you pay for a much smaller prompt", and no longer claims removing the payload "deletes overhead rather than adding latency". It states what *is* demonstrated — complete evidence instead of ~10%, an 83% smaller prompt, a resolvable scope map — and sets the cost and latency expectation honestly, pointing at the evidence file.

**Also landed here:** the exec bound raised 600 → 1800s and made env-overridable (`FLOW_REVIEW_EXEC_TIMEOUT`), because the fetch model made the old number kill working reviewers. The comment and the follow-up capture (`.flow/tmp/fn-170-idle-liveness-CAPTURE.md`) both record that this raises the number without fixing the shape: the right bound is an idle deadline over the event stream codex already emits.

**Release note:** fn-168 (#295) is on `origin/main` as `1300e433`, so the "no release until both land" constraint is satisfied once this spec lands. No version bump — manifests untouched.
## Evidence
- Commits: faa3979f, 5c3e8d9b, 6be85422, 5dc024fe
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., cd plugins/flow-next/tests && python3 -m unittest test_review_prompt_no_embed_ratchet test_eval_harness_prompt_api test_prompt_text_pinned test_review_prompt_template_parity -v
- PRs: https://github.com/gmickel/flow-next/pull/296