---
satisfies: [R1, R6]
---
# fn-168-review-convergence-lost-ratchet-prompt.1 Prompt states the line grammar + parser vocabulary + host wording + drift guard

## Description
State the machine grammar in the ratchet prompt (per-ordinal lines + the dedicated aggregate record), widen the parser vocabulary so every token the prompt advertises actually parses, mirror the same wording into the 3 host workflow files, and add the drift guard that keeps prompt and parser from ever diverging again.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (`build_convergence_ratchet_block` rule 1 + example; `_FINDINGS_PRIOR_RE` / `_FINDINGS_STATUS_ALIASES` / `_FINDINGS_PRIOR_RECORD_RE`), `plugins/flow-next/skills/flow-next-impl-review/workflow-host.md`, `plugins/flow-next/skills/flow-next-plan-review/workflow-host.md`, `plugins/flow-next/skills/flow-next-spec-completion-review/workflow-host.md`, `plugins/flow-next/codex/skills/*/workflow-host.md` (regenerated, never hand-edited), `plugins/flow-next/tests/test_review_convergence_cap.py`, `plugins/flow-next/tests/test_review_findings_parser.py`, `.flow/bin/flowctl.py` (propagation)

### Approach
- **This task OWNS the parser vocabulary for every token it advertises.** The earlier "coordinate with `.2`" ordering was impossible — `.2` depends on this task. Verified live by running the compiled regexes:

  | line | `_FINDINGS_PRIOR_RE` | `_FINDINGS_PRIOR_RECORD_RE` | result |
  |---|---|---|---|
  | `Prior finding #2: fixed` | 1 | 1 | ok |
  | `Prior finding #2: not fixed` | 1 | 1 | ok |
  | `Prior finding #2: not_fixed` | 1 | 1 | ok |
  | `Prior finding #2: not-fixed` | **0** | 1 | **MISMATCH → whole container `None`** |
  | `Prior findings: all fixed` | **0** | 1 | **MISMATCH → whole container `None`** |

  So this task widens the canonical pattern to accept the hyphen, adds the `not-fixed` alias to `_FINDINGS_STATUS_ALIASES`, and makes the aggregate line **recognized** by the counting logic so a compliant aggregate-only response produces no mismatch. **Recognition ONLY** — the aggregate's sweep semantics, scoping, and corpus tests belong to `.2`.
  - *This is a LIVE bug today, not introduced by the spec: the current prompt's own prose says "state whether it is now **fixed** or **not-fixed**" — it advertises the hyphen the parser rejects.*
- Rewrite rule 1 of the shrink-only contract to state the exact format and show it: one line per prior finding, line-start, `Prior finding #N: fixed` / `not-fixed` / `withdrawn`, echoing **the literal number rendered before each item** (not a reinvented 1..N scheme). `_render_structured_prior_finding` (~`:11780`) emits `{ordinal}. {severity} | {classification} | {status} | {title} | {location}`, and `ordinal` is a stored per-item field (`next_ordinal` ~`:5601-5621`, uniqueness enforced ~`:5404`) — NOT positional, so `#2` cannot re-bind when the prior set shrinks.  Prose and tables stay welcome; the lines are mandatory.
- Add the aggregate record to the same block: `Prior findings: all fixed` — usable only when every prior is fixed, explicitly overridden by any per-ordinal line. Include the one-sentence warning that `unaddressed: []` does NOT vouch for prior findings.
- Do NOT imply ordinals are always mandatory: the parser special-cases a single prior item with no ordinal (~`:5171`) — keep the example compatible with that shape.
- The builder is shared by all 5 codex/copilot/cursor call sites (~`:39562`, `:40433`, `:40920`, `:41185`, `:41235`), so one edit covers them. The 3 `workflow-host.md` files need the same wording added by hand — **host does NOT pass through the builder** (they currently list render fields only, with no reply grammar).
- **R6 drift guard — now load-bearing.** Once `.3` deletes both heuristic classes, `same-not-fixed-lineage` is the ONLY stall class that can fire, and it reads exclusively `not_fixed`, which only an explicit parsed resolution line can write. A prompt/parser divergence therefore no longer degrades a heuristic; it silently removes stall detection entirely. The guard lives in `test_review_convergence_cap.py` (`TestConvergenceRatchet`): extract EVERY status token and example line the emitted block advertises — parse them out of the **production builder's output**, never hand-copy one `fixed` case — and assert each is accepted by `_FINDINGS_PRIOR_RE`, recognized by `_FINDINGS_PRIOR_RECORD_RE` without creating a RECORD/PRIOR count mismatch, and normalized by `_FINDINGS_STATUS_ALIASES`. *This guard is what would have caught the hyphen bug.*
- Check whether promoting the prefix/suffix to module-level constants (bringing them under `test_prompt_text_pinned`) is a genuine one-liner; if it churns hashes or shapes, leave R6's assertion as the guard and note the decision in the done summary.
- Propagation: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py`; `./scripts/sync-codex.sh` TWICE (second run must produce no diff).

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py` — `build_convergence_ratchet_block` (~:11827; rule 1 ~:11880) and `_render_structured_prior_finding` (~:11780) for how each ordinal is rendered
- `plugins/flow-next/scripts/flowctl.py` — `_FINDINGS_STATUS_ALIASES` (~:4577), `_FINDINGS_PRIOR_RE` (~:4625), `_FINDINGS_PRIOR_RECORD_RE` (~:4639): every advertised token MUST parse under these
- `plugins/flow-next/scripts/flowctl.py` — `_review_finding_prior_items` (~:5134-5207) for the count-mismatch → `None` path and its sole call site (~:5476)
- `plugins/flow-next/tests/test_review_convergence_cap.py` — `TestConvergenceRatchet` (~:86) for the assertion's home and style
- `plugins/flow-next/skills/flow-next-impl-review/workflow-host.md` (~113-118) — the host contract wording to extend (siblings follow the same shape)

**Optional** (reference as needed):
- `plugins/flow-next/tests/test_review_findings_parser.py` (grammar accept/reject ~:368-437) — where a hyphen accept-case belongs
- `plugins/flow-next/tests/test_prompt_text_pinned.py` (~:89 `PROMPT_HASHES`) — only if promoting the strings to pinned constants
- `plugins/flow-next/scripts/flowctl.py` ~:5171 — the single-item no-ordinal special case

### Key context
- These prompt strings are **function-local**, so `test_prompt_text_pinned` (which discovers module-level constants + on-disk templates) does NOT pin them — the edit is unblocked, and R6 is the only drift protection.
- Do NOT touch `REVIEW_JSON_TALLY_BLOCK` (~:8893): it IS pinned, and its `unaddressed` key keeps its existing R-ID meaning.
- Widening `_FINDINGS_PRIOR_RE` must not swallow neighbouring text: it ends with `(?![A-Za-z0-9_-])`, so verify a hyphen alternative still rejects `not-fixedish` and never lets a bare `not-` match.
- Memory (`audit-sync-codexsh-during-planning-for-2026-04-30`): skill-markdown edits need sync-codex run twice with validation green.

## Acceptance
- [ ] Rule 1 states the per-ordinal line grammar with an example that echoes the rendered ordinal; the single-item no-ordinal shape is not excluded
- [ ] The aggregate record `Prior findings: all fixed` is stated, with explicit-per-ordinal-wins and the `unaddressed: []` non-vouching warning
- [ ] Every token this prompt advertises is parser-accepted AT THE END OF THIS TASK: hyphenated `not-fixed` accepted by `_FINDINGS_PRIOR_RE` and normalized by `_FINDINGS_STATUS_ALIASES`; the aggregate line recognized with no RECORD/PRIOR count mismatch (aggregate sweep semantics deliberately NOT implemented here)
- [ ] Negative cases still reject: `not-fixedish` and a bare `not-` do not match; an out-of-vocabulary status (`pending`) stays recognized-but-invalid (whole-container `None`), never a silent absence
- [ ] Same wording present in all 3 canonical `workflow-host.md` files; codex mirror regenerated via sync-codex.sh run twice (no diff on the second run), never hand-edited
- [ ] R6 guard: EVERY advertised token/example is extracted from the production builder's output and asserted accepted by `_FINDINGS_PRIOR_RE`, recognized without a RECORD/PRIOR count mismatch, and normalized by `_FINDINGS_STATUS_ALIASES`; the test's docstring states that it protects the only surviving stall terminal
- [ ] Pinned-constant promotion either done (with same-commit hash update + rationale) or explicitly declined with a one-line reason in the done summary
- [ ] Focused suites green: `python3 -m unittest test_review_convergence_cap test_prompt_text_pinned test_review_findings_parser -q`
- [ ] Propagation done (cp flowctl.py to .flow/bin)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
