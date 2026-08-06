---
satisfies: [R2]
---
# fn-169-review-subsystem-agentic-first-pass.3 Inject prior findings only when the session did not resume

## Description
Make session resume the primary continuity mechanism and injection the fallback it was always meant to be.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (`_dispatch_backend_review` resume/injection branches ~:40583, ~:41085, ~:41350, ~:41400; `build_rereview_preamble`), `plugins/flow-next/tests/`, `.flow/bin/flowctl.py`

### Approach
- Today the cursor branch **resumes the session AND builds the ratchet with `prior_findings` + `prior_items` embedded** into the argv-budgeted prompt (~:40583). Both mechanisms, same dispatch — so on the one backend with a hard cap we re-ship bytes the resumed chat already has, then truncate them.
- **Two-phase dispatch — the resume outcome is not known in time for a single prompt build (plan-review r1, P1).** `run_codex_exec` builds the prompt, tries `codex exec resume`, and on `CalledProcessError` falls through to a fresh session **reusing the same prompt string**. So simply stripping priors would leave that fresh fallback BLIND, and `resolution_out["resume_failed"]` arrives after the dispatch that needed it. Restructure instead:
  1. attempt resume with the **lean** prompt (no injection);
  2. on resume failure, **rebuild** the prompt WITH injection and dispatch fresh.
  The runner therefore needs a prompt **factory** (a callable) rather than a fixed string, or the caller owns both phases explicitly. A fixed string cannot express this contract — that is the whole finding.
- Apply the same contract to copilot and cursor, or exclude them explicitly with a stated reason (cursor is resume-only with `require_nonempty_sid`; copilot is create-or-resume via marker).
- **Host always injects** — no session by design (`session_id: null`, "Every re-review is a fresh subagent"), and `workflow-host.md:165` states the receipt's `review` field is REQUIRED for exactly this. Make it an explicit, tested exception so a later "simplification" cannot silently break host convergence.
- The re-review prompt for the resumed path is ALREADY WRITTEN — `build_rereview_preamble` emits "This is a RE-REVIEW... **Updated files:** {files_list}... Re-read these files from the repository - do NOT rely on cached content." Keep that; drop only the prepended ratchet. Do NOT adopt RP's "reviewer sees your changes automatically" wording: that is an RP-specific auto-refresh property and false for CLI backends, which fetch on demand.
- Validated shape (measured): resumed session + zero injection + the grammar instruction produced `Prior finding #1: fixed / #2: not-fixed / #3: fixed`, scored exactly by the production parser.
- This removes the PR #295 false-SHIP class on the RESUMED path: a resumed reviewer saw the full prior set in its own context, so its aggregate all-clear is trustworthy there.
- **Do NOT delete fn-168's interim cursor sweep gate in this task** (corrected during implementation). On the resume-FAILURE path cursor still receives rendered prior items, and those can still be truncated by the argv fitter — so the hazard survives until `.4` removes truncation itself. The gate is deleted in `.4`, together with the fitters that make it necessary.
- Propagation: `cp` to `.flow/bin/flowctl.py`.

### Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl.py` ~:40583 — the cursor branch that resumes and injects together; the three sibling dispatch sites
- `build_rereview_preamble` (~:11934) — the minimal prompt already present; the `ratchet` variable it prepends
- `plugins/flow-next/skills/flow-next-impl-review/workflow-host.md` ~:11, ~:165 — host's no-session contract
- fn-168's interim cursor sweep gate — deleted here

**Optional:**
- `workflow-rp.md` ~:636 — the do-not-summarize principle (spirit, not the RP-specific justification)

### Key context
- **The target shape is already proven** (spec § Already established): a resumed session with zero injection produced the exact per-ordinal grammar, scored by the production parser. Implement it; do not re-run a feasibility probe.
- Depends on `.1`: without a trustworthy, loud resume signal this task would silently produce blind re-reviews — fn-90's original runaway.
- If `.1` found resume unreliable for a backend, narrow this task to host plus that backend and record why.
- fn-90's root cause was "every re-review ordered a FRESH blind review." Resume is the actual fix for that; injection was the compensation.

## Acceptance
- [ ] A resumed re-review contains NO rendered prior items; injection fires only on a surfaced resume failure
- [ ] Host always injects, as an explicit tested exception
- [ ] Forced-resume-failure test asserts injection returns and the round still converges
- [ ] A resumed round with zero injection yields correct per-ordinal statuses through the production `_review_finding_prior_items`
- [ ] The aggregate sweep is sound on a RESUMED round without the interim gate; the gate itself stays until `.4` (resume-failure rounds on cursor still carry truncatable rendered items)
- [ ] `build_rereview_preamble`'s minimal core is preserved; RP's auto-refresh wording is NOT propagated to CLI backends
- [ ] Focused suites green; propagation done

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
