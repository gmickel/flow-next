---
satisfies: [R2, R4]
---
# fn-137-global-acceptance-criteria-object.2 Completion-review integration + compliance in receipts

## Description
Completion review applies existing criteria; receipts carry per-criterion compliance.

**Size:** M

**Files:** flowctl.py completion-review prompt builder (`build_completion_review_prompt` + `COMPLETION_REVIEW_PROMPT_FALLBACK`), `plugins/flow-next/skills/flow-next-spec-completion-review/references/completion-review-prompt.md`, receipt write + validation, parser extension (extends the landed fn-136 parser - `parse_review_findings` family, same degrade-to-None public boundary), tests + fixtures.

**Backend coverage (R2 = all six):** audit `workflow-{codex,common,copilot,cursor,host,rp}.md`. Injection point is the shared template/builder wherever the backend flows through it; add per-workflow prose only where a backend bypasses the builder. Add a test/fixture per backend path where feasible.

**Prompt-pin tripwire:** `completion-review-prompt.md` is SHA-256-pinned in `plugins/flow-next/tests/test_prompt_text_pinned.py` and `COMPLETION_REVIEW_PROMPT_FALLBACK` must stay byte-identical to the template (fn-112.3). Update the fallback byte-identical AND refresh the pinned hashes in the SAME commit, with the prompt-change rationale in the commit message. flowctl.py dual-copy checklist applies (scripts/ + .flow/bin/ + sync-codex twice).

### Approach
- Prompt: when criteria exist, inject a compact criteria block (user content) opened by the canonical marker heading `## Global acceptance criteria` (the SAME literal .1's zero-cost-absent test greps for - expose it as a shared flowctl constant so test and injection cannot drift) + an Output Format addition mandating a `## Global criteria` section: per criterion `G<N>: met|violated|n/a - <note>`; violations must ALSO appear as normal findings (severity per reviewer judgment) so the fn-136 findings channel stays the single findings surface.
- Receipt: `criteria: [{id, status, note?}]` parsed deterministically (extend the fn-136 parser); degrade-to-absent.
- Consistency contract: the `criteria:` array is authoritative for compliance status; findings carry the detail; no validation cross-links the two surfaces (a `violated` criterion without a matching finding, or vice versa, is explicitly accepted - downstream renderers treat criteria as the compliance source).
- Token discipline: injection gated on file existence (zero-cost-absent test from .1 goes green); template delta measured.
- Fixtures: real-shaped completion-review outputs with criteria sections.

## Acceptance
- [ ] All completion-review backends apply criteria + receipts carry compliance; degrade-to-absent (R2).
- [ ] Zero-cost-absent proven; template deltas measured; sync-codex idempotent if prose touched (R4).

## Done summary
Completion review now applies `.flow/criteria.md` global acceptance criteria across all six backend surfaces (codex/copilot/cursor via the shared build_completion_review_prompt `{global_criteria_block}` placeholder; rp CE+classic and host via the new `flowctl criteria prompt-block` composition), mandating a `## Global criteria` output section whose `G<N>: met|violated|n/a - note` lines are deterministically projected into the additive completion-review receipt field `criteria: [{id, status, note?}]` (parse_review_criteria, fn-136-style degrade-to-None; attached by both `_write_backend_review_receipt` and `review-findings attach`). Absent-file stays byte-identical zero-cost (fn-137.1's test now load-bearing); template + byte-identical fallback + pinned hashes refreshed in the same commit; dual copies, tracker MANIFEST, and codex mirror (sync-codex x2, idempotent) propagated. Implementation delegated to grok-4.5 via the cursor-agent bridge; prompt wording, skill prose, and review by the orchestrator.
## Evidence
- Commits: c4988fa7, aab272f3
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_criteria test_prompt_text_pinned test_review_prompt_template_parity test_review_findings_parser test_review_findings_receipts test_review_prompt_constraints test_startup_bootstrap test_tracker_distribution -q (164 tests OK), python3 scripts/run_tests_parallel.py (files=165 ran=3474 failures=0 errors=0; GREEN_RECEIPT 9947d982-unittest), uvx ruff@0.16.0 check . (All checks passed), baseline: green (focused suites, 100 tests OK pre-edit), post-review: python3 -m unittest test_criteria test_prompt_text_pinned test_review_prompt_template_parity test_startup_bootstrap test_bin_launcher_parity test_tracker_distribution -q (OK); uvx ruff@0.16.0 check flowctl.py clean
- PRs: