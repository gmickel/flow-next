---
satisfies: [R1, R6]
---
# fn-168-review-convergence-lost-ratchet-prompt.1 Ratchet prompt states the line grammar + aggregate record (incl. host wording, drift guard)

## Description
State the machine grammar in the ratchet prompt (per-ordinal lines + the dedicated aggregate record), mirror the same wording into the 3 host workflow files, and add the drift guard that keeps the prompt's example and the parser's regexes from ever diverging.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (`build_convergence_ratchet_block` rule 1 + example), `plugins/flow-next/skills/flow-next-impl-review/workflow-host.md`, `plugins/flow-next/skills/flow-next-plan-review/workflow-host.md`, `plugins/flow-next/skills/flow-next-spec-completion-review/workflow-host.md`, `plugins/flow-next/codex/skills/*/workflow-host.md` (regenerated, never hand-edited), `plugins/flow-next/tests/test_review_convergence_cap.py`, `.flow/bin/flowctl.py` (propagation)

### Approach
- **This task OWNS the parser vocabulary for every token it advertises (plan-review round 2 — the earlier "coordinate with .2" ordering was impossible, since .2 depends on this task).** Verified live: `Prior finding #2: not-fixed` fails `_FINDINGS_PRIOR_RE` (which spells the negative with whitespace/underscore, no hyphen) while matching the broad `_FINDINGS_PRIOR_RECORD_RE` → RECORD/PRIOR count mismatch → `None` → the whole round's findings container is dropped. `Prior findings: all fixed` has the same defect. So this task widens the canonical pattern (hyphen) + adds the `not-fixed` alias, and makes the aggregate line **recognized** by the counting logic so a compliant aggregate-only response produces no mismatch. Recognition ONLY — the aggregate's sweep semantics, scoping, and corpus tests belong to .2.
- Rewrite rule 1 of the shrink-only contract to state the exact format and show it: one line per prior finding, line-start, `Prior finding #N: fixed` / `not-fixed` / `withdrawn`, echoing **the literal number rendered before each item** (not a reinvented 1..N scheme). Prose and tables stay welcome; the lines are mandatory.
- Add the aggregate record to the same block: `Prior findings: all fixed` — usable only when every prior is fixed, and explicitly overridden by any per-ordinal line. Include the one-sentence warning that `unaddressed: []` does NOT vouch for prior findings.
- Do NOT imply ordinals are always mandatory: the parser special-cases a single prior item with no ordinal (~`flowctl.py:5171`) — keep the example compatible with that shape.
- The builder is shared by all 5 codex/copilot/cursor call sites, so one edit covers them; the 3 `workflow-host.md` files need the same wording added by hand (they currently list render fields only, no reply grammar).
- **R6 drift guard** in `test_review_convergence_cap.py` (`TestConvergenceRatchet`): extract EVERY status token and example line the emitted block advertises (parse them out of the production builder's output — never hand-copy one `fixed` case) and assert each is accepted by `_FINDINGS_PRIOR_RE`, recognized by `_FINDINGS_PRIOR_RECORD_RE` without creating a RECORD/PRIOR count mismatch, and normalized by `_FINDINGS_STATUS_ALIASES`. This guard is what would have caught the hyphen bug.
- Check whether promoting the prefix/suffix to module-level constants (bringing them under `test_prompt_text_pinned`) is a genuine one-liner; if it churns hashes or shapes, leave R6's assertion as the guard and note the decision.
- Propagation: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py`; `./scripts/sync-codex.sh` TWICE (second run must produce no diff).

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py` — `build_convergence_ratchet_block` (~:11807-11911; rule 1 ~:11861) and how it renders each prior item's ordinal
- `plugins/flow-next/scripts/flowctl.py` — `_FINDINGS_PRIOR_RE`, `_FINDINGS_PRIOR_RECORD_RE`, `_FINDINGS_STATUS_ALIASES` (~:4577-4648): the example MUST parse under these
- `plugins/flow-next/tests/test_review_convergence_cap.py` — `TestConvergenceRatchet` (~:86) for the assertion's home and style
- `plugins/flow-next/skills/flow-next-impl-review/workflow-host.md` (~113-118) — the host contract wording to extend (siblings follow the same shape)

**Optional** (reference as needed):
- `plugins/flow-next/tests/test_prompt_text_pinned.py` (~:89 `PROMPT_HASHES`) — only if promoting the strings to pinned constants
- `plugins/flow-next/scripts/flowctl.py` ~:5171 — the single-item no-ordinal special case

### Key context
- These prompt strings are function-local, so no hash currently pins them — the edit is unblocked, and R6 is what stops future silent drift.
- Do NOT touch `REVIEW_JSON_TALLY_BLOCK` (~:8893): it is pinned, and its `unaddressed` key keeps its existing R-ID meaning.
- Memory (`audit-sync-codexsh-during-planning-for-2026-04-30`): skill-markdown edits need sync-codex run twice with validation green.
## Acceptance
- [ ] Rule 1 states the per-ordinal line grammar with an example that echoes the rendered ordinal; single-item no-ordinal shape not excluded
- [ ] The aggregate record `Prior findings: all fixed` is stated, with explicit-per-ordinal-wins and the `unaddressed: []` non-vouching warning
- [ ] Same wording present in all 3 canonical `workflow-host.md` files; codex mirror regenerated via sync-codex.sh run twice (no diff on the second run), never hand-edited
- [ ] R6 guard: EVERY advertised token/example is extracted from the production builder's output and asserted accepted by `_FINDINGS_PRIOR_RE` + `_FINDINGS_STATUS_ALIASES` with no RECORD/PRIOR count mismatch
- [ ] Every token this prompt advertises is parser-accepted AT THE END OF THIS TASK: hyphenated `not-fixed` accepted by `_FINDINGS_PRIOR_RE` + normalized by `_FINDINGS_STATUS_ALIASES`; aggregate line recognized with no RECORD/PRIOR count mismatch (aggregate sweep semantics deliberately NOT implemented here)
- [ ] Pinned-constant promotion either done (with same-commit hash update + rationale) or explicitly declined with a one-line reason in the task summary
- [ ] Focused suites green: `python3 -m unittest test_review_convergence_cap test_prompt_text_pinned test_review_findings_parser -q`
- [ ] Propagation done (cp flowctl.py to .flow/bin)
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
