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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
