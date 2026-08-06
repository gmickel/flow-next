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
- Gate injection on the resume outcome from `.1`: resumed => no injection; resume failed or unavailable => inject, deliberately and visibly.
- **Host always injects** — no session by design (`session_id: null`, "Every re-review is a fresh subagent"), and `workflow-host.md:165` states the receipt's `review` field is REQUIRED for exactly this. Make it an explicit, tested exception so a later "simplification" cannot silently break host convergence.
- The re-review prompt for the resumed path is ALREADY WRITTEN — `build_rereview_preamble` emits "This is a RE-REVIEW... **Updated files:** {files_list}... Re-read these files from the repository - do NOT rely on cached content." Keep that; drop only the prepended ratchet. Do NOT adopt RP's "reviewer sees your changes automatically" wording: that is an RP-specific auto-refresh property and false for CLI backends, which fetch on demand.
- Validated shape (measured): resumed session + zero injection + the grammar instruction produced `Prior finding #1: fixed / #2: not-fixed / #3: fixed`, scored exactly by the production parser.
- This is what removes the PR #295 false-SHIP class at the root: a resumed reviewer saw the full prior set, so its aggregate all-clear is trustworthy and the interim cursor sweep gate can be **deleted** in this task.
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
- [ ] fn-168's interim cursor sweep gate is DELETED, and the aggregate sweep is sound without it on a resumed round
- [ ] `build_rereview_preamble`'s minimal core is preserved; RP's auto-refresh wording is NOT propagated to CLI backends
- [ ] Focused suites green; propagation done

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
