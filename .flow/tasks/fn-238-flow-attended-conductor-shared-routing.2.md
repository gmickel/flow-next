---
satisfies: [R15, R16, R17, R18]
---
# fn-238-flow-attended-conductor-shared-routing.2 Refine rename with alias stub, research scope, why-scout

## Description
TBD

## Acceptance
R15 to R18 in the parent spec are satisfied; judge this task against those criteria directly.

## Done summary
Renamed the interview skill to `/flow-next:refine` with a one-release forwarding alias (skill stub + command shim, non-triggering, Codex catalog flag off), added `refine --scope=research` (docs, practice, docs-gap, memory scouts; github when gated) writing one `## Resolved via Research` section with plan's research step applying the same skip in reverse, added the read-only `why-scout` agent with direct/supported/inferred/unknown tiers, and put the read-first signal and the why-scout into the route matrix's ready-spec and investigation rows. Every canonical call site, the sync-codex roster, tests, docs, README, GLOSSARY, STRATEGY, conduct pages, and the spec template say refine; a new contract test (`test_refine_rename.py`) pins the alias, the research plumbing and symmetric skip, the why-scout's tool-enforced read-only frontmatter, and pointer resolution.

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)

### Gates

- baseline: red (python3 scripts/run_tests_parallel.py failed pre-edit: 3 test_gate_receipt failures from git 2.55 error text, inherited); ruff green.
- final: full suite rc=1 with only those same 3 inherited failures; ruff green; sync-codex twice rc=0, no second-run diff; install suites for Cursor, Codex, OpenCode green.
- templates/spec.md pin bumped deliberately (task acceptance names the auxiliary-section comments; new hash recorded in test_prompt_text_pinned.py with a comment).

### Downstream (R18), reported separately from source completion

- AI x SDLC guide: source-complete, commits ddca046 and 5ed48c2 on `flow-next-fn-238-flow` in ~/work/AI-x-SDLC-Starter-Kit; unpublished (not pushed). `ruby scripts/check-navigation.rb` passed.
- Vault: Skills Catalog, Vocabulary & Concepts, Messaging Library, log.md edited in place; `gno index projects` run; `gno search "Resolved via Research" --collection projects` hits Catalog and Vocabulary. The vault is not a git repo, so nothing to commit.
- flow-next.dev: untouched (R14, deferred).

### Decisions recorded

- `tracker.perEvent.interview` stays the storage key; refine reads it (no schema regeneration, no silent config rename). Tracker caller ids and the immutable oracle fixture keep `interview` as the event name; the spec-id routing test's pure labels moved to `refine`.
- Legacy-cleanup rows for the alias are NOT added this release: the installer would retire the live stub it just copied. The removal release adds the retire rows for `flow-next-interview` (skill + prompt) alongside deleting the stub, shim, and sync-roster rows (R15's "removed the release after").
- Registry manifests count the alias stub, shim, and why-scout (21 subagents / 29 commands / 33 skills); published phrases stay 32 skills / 27 slash-command (same carve-out as the experimental tier).
- The `flow` DIET description was already over the 200-char catalog cap after task .1's description commit (sync-codex was red on HEAD); trimmed it with the refine entry because the required no-diff double sync depends on it.
- `optimization/` baselines, `tests/fixtures/tracker_callers/oracle-*.json`, the oracle-commit path in test_tracker_caller_oracle.py, agent_docs/archive, CHANGELOG history, and release-history entries keep the old name as frozen evidence.

### Open items

- Legacy-cleanup rows and the alias removal are the release-after task (see above); nobody is tracking it beyond the changelog line and the sync-codex comment.
- No conduct page was written for the research pass beyond two rows on conduct/refine.md; a why-scout conduct page was added (agent_docs/conduct/why-scout.md).
- The vault's Lifecycle & Handover Objects note still spells `interview`; left for a separate vault pass (subagent flagged it).
- flowctl.py line 220 keeps `interview` as a chart decision type (not the skill); unchanged by design.

stage: impl-review - ran(codex gpt-6-astra, axis: overengineered/non-agentic; round 1 NEEDS_WORK 5 findings fixed in 35f3d962, round 2 one open fixed in 0e74643e, round 3 SHIP)
stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 681f31228c9ac5d7c225761d6fbd3c8d068be5ad, 35f3d962, 0e74643e, 63983a4c
- Tests: baseline: red (python3 scripts/run_tests_parallel.py: 3 inherited test_gate_receipt failures from git 2.55 error text, pre-edit); uvx ruff@0.16.0 check . green pre-edit, python3 scripts/run_tests_parallel.py (final: suite_rc=1; only the 3 inherited test_gate_receipt failures remain after the deliberate templates/spec.md pin bump; test_prompt_text_pinned re-run green), python3 -m unittest plugins.flow-next.tests.test_refine_rename test_command_shim_flatten test_chart_docs_inventory test_chart_prompt_scenarios test_chart_skill_contract test_cursor_plugin_surface test_install_opencode (OK), python3 -m unittest plugins.flow-next.tests.test_install_opencode test_install_cursor_parity test_cursor_install_verifier test_install_codex_legacy_cleanup (OK, 40 tests), python3 -m unittest <20 renamed-surface suites: scope flag, r22, source tags, readback, spec-id routing, tracker caller execution/oracle, template canonical, precheck, visual, prospect x3, capture biz routing> (OK, 386 tests after fixes), uvx ruff@0.16.0 check . (All checks passed), ./scripts/sync-codex.sh twice (rc=0 both; no diff after the second run), GATE_RECEIPT_SKIPPED:unittest - full suite not fully green (inherited red baseline), no receipt written, python3 scripts/run_tests_parallel.py (post-review, 35f3d962: 4865 ran, 3 inherited test_gate_receipt failures only), uvx ruff@0.16.0 check . (post-review: green), cd plugins/flow-next/tests && python3 -m unittest test_refine_rename test_prompt_text_pinned test_skill_prose_diet test_flow_routing test_readback_ask_contract -q (post-review: OK), ./scripts/sync-codex.sh (post-review, run twice each commit: idempotent), stage: impl-review - ran(codex exec read-only, gpt-6-astra high, sub2 instance, axis: overengineered/non-agentic): round 1 NEEDS_WORK (1 MUST, 4 SHOULD) -> 35f3d962; round 2 NEEDS_WORK (1 open) -> 0e74643e; round 3 SHIP; receipts .flow/tmp/codex-review/fn-238-t2-review.md, fn-238-t2-rereview.md, fn-238-t2-rereview2.md, stage: plan-sync - skipped(config: planSync.enabled != true)
- PRs: