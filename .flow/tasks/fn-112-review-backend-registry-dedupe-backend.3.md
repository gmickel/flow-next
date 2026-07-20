# fn-112-review-backend-registry-dedupe-backend.3 Prompt extraction to skill templates

## Description
Embedded review prompts move out of flowctl into visible skill templates.

**Size:** M
**Files:** both flowctl.py copies, new template .md files under plugins/flow-next/skills/ (impl-review/plan-review/spec-completion-review references), scripts/sync-codex.sh (only if a new transform/guard is needed), tests

### Approach

- Move the ~780 LOC of embedded f-string review prompts (fn-112 stub lists flowctl.py:5133-5421, 5586-5804, 21354-21503, 24724-24877 at audit HEAD - re-locate by content) into skill-owned .md template files using the EXISTING load_validator_template / load_deep_pass_template loader + embedded-fallback pattern (template file wins, embedded string is the fallback when the plugin root is unavailable). Keep the embedded fallbacks byte-identical to the templates (pin with a parity test, pattern: test_dogfood_template_parity).
- Placeholder interpolation stays in Python (the loader substitutes); templates carry {placeholder} markers documented at the top of each file.
- sync-codex.sh: the new template files ride the existing skills mirror; check its validation guards still pass and add a transform ONLY if a template carries Claude-only tool names (they should not - they are reviewer prompts).
- fn-90 sentences and any fence content pinned by test_skill_prose_diet / test_foreground_rule_fences must remain byte-preserved wherever they live.
- Dual-copy mirrored; sync-codex x2. NO git commands.

### Acceptance

- [ ] Embedded prompt f-strings replaced by template loads with byte-identical embedded fallbacks (parity test pins template == fallback)
- [ ] Rendered prompts byte-identical to pre-change for a fixed input (fixture test)
- [ ] Focused suites green: test_backend_spec.py, test_skill_prose_diet.py, test_foreground_rule_fences.py, the new parity test
- [ ] Both copies byte-identical; sync-codex idempotent

## Acceptance
- [ ] TBD

## Done summary
Review prompts extracted to 4 skill reference templates (impl-review-prompt / standalone-review-prompt / plan-review-prompt / completion-review-prompt) with documented placeholder contracts; XML wrapping and rubric blocks stay single-source in Python. Embedded fallbacks kept byte-identical to templates - REQUIRED, not optional: setup-installed .flow/bin/flowctl runs without the plugin root, same rationale as the existing load_validator_template pattern - so flowctl LOC does not shrink here (+64; the spec's >=1500 cumulative gate is measured at .4 where the parser shrink lands). test_review_prompt_template_parity pins fallback==template (9 tests) and 8 golden fixtures pin rendered-prompt byte-identity; HOST PROVENANCE CHECK: all 8 goldens re-rendered from the pre-extraction module with the exact test-matched calls - byte-identical, so the goldens are honest (initial mismatch was the host's own call-signature error, documented). Host review also caught via the full-corpus gate: the delegate deleted VALIDATOR_TEMPLATE_FALLBACK while load_validator_template still returned it (NameError landmine on the plugin-less path) - restored verbatim, DEEP_PASSES_FALLBACK verified intact. Full parallel suite 84 files / 1841 tests / 0 failures / 85.8s (new parity file +9); dual-copy identical; sync-codex x2 (mirror ships the templates).
## Evidence
- Commits: 6a929ee5, c9542f332010ddf7e6486cb5faf089425abcf7a7
- Tests: python3 scripts/run_tests_parallel.py (84 files, 1841 tests, 0 failures, 85.8s), test_review_prompt_template_parity.py 9 (parity + 8 goldens), host provenance: 8 goldens re-rendered from pre-extraction module, byte-identical, test_cursor_review_commands.py 32 (fallback path restored)
- PRs: