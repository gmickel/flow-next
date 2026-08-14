---
satisfies: [R2, R3, R6]
---
# fn-195-orchestration-by-intent-named-tiers-per.3 Delete the shipped model identifiers and the pin machinery they fed

## Description
Remove the model identifiers from shipped prose - the count at planning time was 179 mentions across 64 canonical files - and delete the role map and staleness machinery they existed to feed. Two declared exceptions survive: the single tier-guidance page and the review-backend configuration grammar.

**Size:** L (mechanical breadth, low per-edit risk)
**Files:** every canonical file naming a model identifier (docs tree, skills, templates, references) plus `plugins/flow-next/scripts/flowctl.py` (`models.roles` storage, validation, staleness math, the resolve verb) and the schema entry; also `plugins/flow-next/commands/uninstall.md` and `plugins/flow-next/skills/flow-next-setup/workflow.md` (two staleness items `.2` left unowned — see below)
**Touches:** [plugins/flow-next/docs/**, plugins/flow-next/skills/**, plugins/flow-next/templates/**, plugins/flow-next/references/**, plugins/flow-next/scripts/flowctl.py, plugins/flow-next/schema/flow-config.schema.json, scripts/gen_flow_config_schema.py, .flow/bin/flowctl.py, plugins/flow-next/commands/uninstall.md]

### Approach
- Enumerate mechanically first and keep the list: grep the identifier patterns across canonical files, then classify each hit as delete, replace-with-a-tier-name, or declared exception. Do not free-hand the sweep.
- Any identifier that cannot be removed without losing a load-bearing contract is recorded as an exception WITH its reason. A silent survivor is the failure this criterion exists to catch.
- `models.roles` goes entirely: storage, write validation, the staleness stamp and nudge, and the resolve verb. The delegate role is already gone by then; this removes the rest of a surface nothing reads.
- The review backend's own grammar and its receipts are out of scope. Do not touch them.
- Agent definitions keep their model fields - they are the floor, and removing them would change behavior on the primary host.
- Deleted config keys report once and never block, matching the pattern the delegation removal established.

### Investigation targets
**Required** (read before coding):
- the enumerated grep output from this task's first step - the working list
- `plugins/flow-next/scripts/flowctl.py` role-map storage, validation and resolve paths - the deletion boundary
- the tests that currently pin the `models.roles` pin-ceremony machinery being deleted (storage, validation, staleness stamp, resolve verb) - `plugins/flow-next/tests/test_model_pin_ceremony_prose.py` no longer exists in the tree as of `.2`'s landing; locate its replacement/successor (or confirm no test currently covers this surface) before deleting the machinery, so removal doesn't leave a dangling red test elsewhere <!-- Updated by plan-sync: fn-195-orchestration-by-intent-named-tiers-per.2 - the named investigation-target file is stale, it does not exist on disk -->
- `plugins/flow-next/skills/flow-next-impl-review/workflow-host.md` (the "How to pin" table, ~lines 129-135) - PRE-EXISTING, flagged by .1's plan-sync note as unowned: it carries a concrete model identifier (`grok-4.6`) in scope for R2, and it enumerates spawn primitives per host (Claude native subagent `model` param, Codex `spawn_agent`, etc.) in violation of R3 ("no skill names a spawn primitive"). This task is the natural owner (Touches already includes `skills/**`) - move the per-host mechanism content into the reach pages `.1` wrote under `plugins/flow-next/docs/reach/` and leave the table referring to a tier + "see the reach page for this host," not a spawn call. <!-- Updated by plan-sync: fn-195-orchestration-by-intent-named-tiers-per.1 flagged this pre-existing R3 gap with no downstream owner -->
- `plugins/flow-next/commands/uninstall.md` line ~70 - stale description: it still says the model-routing scaffold block "contains a markdown table," but `.2` changed the block to a fully commented HTML-comment example (no table). Correct the parenthetical to describe the actual shape. <!-- Updated by plan-sync: fn-195-orchestration-by-intent-named-tiers-per.2 explicitly handed this staleness item downstream, no test currently pins the wording -->
- `plugins/flow-next/skills/flow-next-setup/workflow.md` Review question for `PLATFORM=grok` (~lines 548-563) - still names the concrete slug `grok-4.5` twice ("Grok's only native model family is grok-4.5", "single-native-family (grok-4.5)"). This is not one of R2's two declared exceptions (the tier-guidance page, the review-backend grammar) - it is prose in the setup skill describing family-detection logic, not a review-backend config string. Replace with tier/family language that names no concrete slug, or add it explicitly as a declared exception with its reason if the family-detection logic cannot be stated without the literal. <!-- Updated by plan-sync: fn-195-orchestration-by-intent-named-tiers-per.2 explicitly handed this staleness item downstream, MODEL_SLUG_RE in test_model_routing_scaffold.py only scans the template file so this slug is currently unpinned -->

### Key context
- This is the task where prose pins bite: every literal removed must be checked against the test corpus and the mirror generator first, with retargets landing in the same commit.

### Acceptance
- [ ] Enumerated hit list recorded with a per-hit disposition; end state is the two declared exceptions and nothing else
- [ ] `models.roles` storage, validation, staleness machinery and resolve verb removed; schema regenerated; drift test green
- [ ] Deleted keys report once, never block; agent model fields untouched
- [ ] Review-backend grammar and receipts untouched
- [ ] Every moved or deleted literal checked against the test corpus and the mirror generator, with retargets in the same commit
- [ ] `flow-next-impl-review/workflow-host.md`'s host-pin table: `grok-4.6` identifier removed, spawn-primitive-per-host content moved to the `.1`-authored reach pages (R3)
- [ ] `commands/uninstall.md`'s "contains a markdown table" description corrected to match the commented-block shape `.2` shipped
- [ ] `flow-next-setup/workflow.md`'s Grok review-menu option no longer names the `grok-4.5` slug (or the identifier is recorded as a declared exception with its reason)

## Acceptance
- [ ] TBD

## Done summary
Deleted the shipped model identifiers and the pin machinery they fed: `models.roles` storage, write validation, the 90-day staleness stamp/nudge and the `models resolve` verb are gone (schema regenerated, drift test green), and concrete model identifiers are swept out of the docs tree, skills, templates and references, leaving the two declared exceptions.

### Enumerated hit list, with dispositions

Enumeration: `grep -rInE 'opus|sonnet|haiku|fable|gpt-5|grok-[0-9]|composer-[0-9]|claude-[0-9a-z]+-[0-9]|gemini|o3-mini'` over `plugins/flow-next` (excluding `codex/`, `tests/`) plus the `models.roles|verifiedAt|models resolve` symbol grep over `flowctl.py`, `gen_flow_config_schema.py`, `sync-codex.sh`.

**Deleted / replaced with tier or placeholder language:**
- `docs/orchestration.md` — role-map section removed whole; the "proven default pipeline" table rewritten as tiers (no models, no eval numbers, no speed claims, per the spec's no-rankings boundary); the "model table in CLAUDE.md" section rewritten as the routing block `.2` actually ships (it described a scores table that no longer exists); agent-defaults table, review-backend reach list, bridge recipes, chaining example all de-slugged. **Now contains zero model identifiers.**
- `docs/flowctl.md` — `models resolve` section and the three `models.*` config rows deleted; `spec/task set-backend` examples genericized (they carried retired `gemini:`/`agent:` ids); cursor reviewer-model enumeration replaced with "ask `--list-models`".
- `docs/platforms.md` — Codex model-mapping table now names the env vars, not slugs; sync example placeholders; Grok single-family sentence and Cursor alias/slug lines de-slugged.
- `docs/troubleshooting.md`, `docs/ralph.md`, `docs/spec-template.md` — ladder sample output, `FLOW_RALPH_CLAUDE_MODEL` example, triage LLM layer.
- `skills/flow-next-prime/{SKILL,workflow}.md`, `skills/flow-next-interview/references/fact-scouts.md` — scout tiers restated in the fn-195 tier vocabulary (fast scout / thinking scout / session model).
- `skills/flow-next-impl-review/{references/backend-specs.md,references/triage-rules.md,workflow-cursor.md,workflow-copilot.md}` and the matching `flow-next-spec-completion-review/*` — backend model *enumerations* and "default `<slug>`" claims replaced by the registry pointer / `--list-models`; the `backend[:model[:effort]]` grammar examples are kept (exception B).
- `skills/flow-next-ralph-init/SKILL.md` — cursor reviewer slug.
- `scripts/sync-codex.sh` — the `models.roles` scout-pin read deleted (precedence is now env > baseline). Not in the task's declared Touches, but it was a live consumer of a key this task deletes; leaving it would have left a dangling read.

**Task-file-named items, all three done:**
- `skills/flow-next-impl-review/workflow-host.md` (and the identical table in `flow-next-spec-completion-review/workflow-host.md`) — the "How to pin" table is gone: `grok-4.6` removed, per-host spawn primitives (`spawn_agent`, native `model` param) removed, replaced by the reviewer-tier precedence sentence + a link to the `.1` reach pages, with the read-only-by-TOOLS invariant kept in the skill (it is a security contract, not reach). `host:opus` anti-pattern → `host:<model>`.
- `commands/uninstall.md` — "the block contains a markdown table" corrected to the commented-example shape `.2` shipped.
- `skills/flow-next-setup/workflow.md` — both `grok-4.5` occurrences replaced with single-native-family language; the fail-closed logic is unchanged and does not need the literal.

### Declared exceptions (identifiers that survive, with reasons)

1. **The review-backend configuration grammar** (spec's exception). Concrete ids remain only inside `backend[:model[:effort]]` examples and the registry that backs them: `flowctl.md` (`review.backend` row, spec-grammar line, ranking defaults, `triage-skip` / `codex`/`copilot`/`cursor` command examples), `schema/flow-config.schema.json` `review.backend` description, the two review skills' SKILL/workflow-common/backend-reference spec examples, the ralph-init prompt templates' `spec form, e.g. …` lines, `setup/workflow.md` power-user spec examples. Reason: the grammar's shape is the contract being taught; a placeholder-only example stops demonstrating that the middle segment is a model id.
2. **`flowctl.py` `BACKEND_REGISTRY` + `FAST_JUDGE_BASELINE`** — same exception, code side. The registry ranking is the review backend's own configuration (and the ladder's data); the fast-judge baselines are per-backend triage defaults in that subsystem. Both explicitly out of scope per the spec's Boundaries ("the review backend stays … untouched here").
3. **The tier-guidance page exception went unused** — `orchestration.md` ended with zero model identifiers, so the end state is exception 1/2 only.
4. **`agents/*.md` model fields untouched** (spec: they are the floor). The `orchestration.md` agent-defaults table no longer restates the aliases; the frontmatter is the single source.

### Machinery removed (R6)

`MODEL_ROLES`, `MODEL_ROLE_BACKENDS`, `MODELS_STALE_DAYS`, `_parse_role_pin`, `get_role_map_pin`, `resolve_role_model`, `resolve_models_role`, `cmd_models_resolve`, `parse_models_verified_at`, `models_pin_nudge_message`, `_validate_models_config_key`, `_validate_models_roles_tree`, the `models` default-config block, the `models` argparse subparser, the `flowctl status` staleness line, the role-map rung in `BackendSpec.resolve`, and the schema generator's `models*` entries. `resolve_fast_judge_model` survives as explicit-else-baseline (triage still needs a model). Deleted keys (`models.roles`, `models.verifiedAt`, `models.verifiedWith`) joined the flow-98 advisory tuple, renamed `REMOVED_CONFIG_KEYS` / `removed_config_keys_*` since it is no longer delegation-only — one stderr line per invocation, never blocking.

### Test-corpus retargets (same commit)

`test_model_resolution.py` (role-map/staleness/resolve classes replaced by a removal-contract class + a review-precedence class; the role-pin cache-intent test rebuilt on a carried non-explicit spec), `test_flowctl_surface.py` (`models resolve` leaf), `test_removed_delegate_config_advisory.py` (renamed symbols, models fixture), `test_host_review_backend.py` (`MODEL_ROLE_BACKENDS` import → host has no model axis), `test_flow_config_schema_drift.py` (models fixtures now invalid-by-schema). No test file deleted; `test_model_pin_ceremony_prose.py` was already gone from `.2`.

### Deferred / notes for the conductor

- **Mirror regen (`codex/**`) NOT run** — `.5` owns it, as planned. The mirror is stale against this commit by design.
- **`templates/usage.md` + `.flow/usage.md` untouched** — both are `.5`'s Touches and `test_cursor_host_docs` pins them byte-identical. They still carry bridge-recipe slugs (`grok-4.6`, `gpt-5.6-terra`, cursor slugs); `.5` owns that pair, and editing one copy here would have gone red on the parity test.
- **Root `CLAUDE.md` model table untouched** — `.5`'s Touches, per the conductor's note.
- **Dogfood propagation DONE here** (`.flow/bin/flowctl.py`, `flowctl_tracker` rsync, `gen_tracker_manifest.py`) because `.flow/bin/flowctl.py` is in this task's Touches and `test_tracker_distribution` would otherwise be red. Only `sync-codex.sh` remains for `.5`.
- Pre-existing untracked `.flow/artifacts/flow-98-…/` was deliberately NOT staged (877d953d untracked it on purpose); staging used `git add -A -- . ':(exclude).flow/artifacts'`.

baseline: green (full suite + ruff verified on this branch head before edits, per conductor)

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
stage: delegation - skipped(config: delegation off)


Review fixes cfdf0b2b: --help snapshot + HELP_SHA256 regenerated (P1), space-form identifier sweep (P2, 5 sites), set-backend argparse placeholderized (P3), manifest regen.

stage: impl-review - ran (host backend, fresh fable-5 reviewers; r1 NEEDS_WORK -> fixes cfdf0b2b -> r2 SHIP)stage: plan-sync - ran (drift: yes; .5 approach corrected - propagation already done by .3, only sync-codex x2 remains, deferred slug files named; .4 clean; cross-spec deferred to conductor)

## Evidence
- Commits: cb0388f7d7789303d8af9bd3dcff5e3501be23bb, cfdf0b2b587dfa428f586ab79596a781d53a2fb5
- Tests: python3 scripts/run_tests_parallel.py (191 files, 4381 tests, 0 failures, 0 errors, suite_rc=0), uvx ruff@0.16.0 check . (All checks passed), cd plugins/flow-next/tests && python3 -m unittest test_model_resolution test_flowctl_surface test_removed_delegate_config_advisory test_host_review_backend test_backend_spec test_model_routing_scaffold test_cursor_host_docs test_cursor_docs_contract test_ralph_docs_truth test_skill_prose_diet test_flow_config_schema_drift -q, post-fix full gate: python3 scripts/run_tests_parallel.py (191 files, 4381 tests, 0F 0E) + uvx ruff@0.16.0 check . (clean), impl-review: host backend r1 NEEDS_WORK (P1 help snapshot, P2 space-form slugs, P3 argparse literals), r2 SHIP (reviewer claude-fable-5, fresh subagents; receipt /tmp/impl-review-receipt-fn-195-orchestration-by-intent-named-tiers-per.3.json)
- PRs: