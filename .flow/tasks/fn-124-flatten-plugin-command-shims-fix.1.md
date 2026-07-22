---
satisfies: [R1, R2, R3, R4]
---

## Description

Flatten the Claude Code command shims and de-prefix their frontmatter so the slash menu renders `/flow-next:qa`; update EVERY live path consumer (Cursor manifest, Cursor + Codex installers, CI verifier, CI gate, tests, sync-codex) in lockstep; remove the dead epic-review alias on all platforms; prove the fix in a live Claude Code session; add a regression test.

**Size:** M
**Files:** `plugins/flow-next/commands/flow-next/*.md` (24 -> 23 moved + 1 deleted), `plugins/flow-next/.cursor-plugin/plugin.json`, `scripts/install-cursor.sh`, `scripts/install-cursor.ps1`, `scripts/install-codex.sh`, `scripts/ci/verify_cursor_install.py`, `plugins/flow-next/scripts/ci_test.sh`, `plugins/flow-next/tests/test_no_default_hooks.py`, `plugins/flow-next/tests/test_model_routing_scaffold.py`, `plugins/flow-next/tests/test_cursor_plugin_surface.py` (NEW), `scripts/sync-codex.sh`, `plugins/flow-next/codex/` (regen), `plugins/flow-next/scripts/{prospect_smoke_test.sh,smoke_test.sh,resolve-pr_smoke_test.sh,map_smoke_test.sh,strategy_smoke_test.sh}`

## Approach

Work through the spec's "Live path-consumer inventory" table - it is the complete verified list; every row is in scope for this task except the two docs rows (task .2).

- `git mv plugins/flow-next/commands/flow-next/<name>.md plugins/flow-next/commands/` for 23 shims; `git rm plugins/flow-next/commands/flow-next/epic-review.md`. Confirm dir gone.
- Frontmatter: remove `name:` entirely OR set bare `name: <cmd>` - uniform choice; verify against current docs (v2.1.216+ last-segment semantics) and Cursor name derivation; state choice + reasoning in commit message (R2).
- `scripts/install-codex.sh:252`: loop `"$PLUGIN_DIR/commands/$PLUGIN/"*.md` -> `"$PLUGIN_DIR/commands/"*.md` (+ comment :20). Without this Codex installs get ZERO prompts.
- `scripts/install-codex.sh` upgrade cleanup: existing installs keep stale artifacts (skills loop only replaces skills still in source; prompts loop only copies current files). Add exact-target removal of `~/.codex/skills/flow-next-epic-review/` and `~/.codex/prompts/epic-review.md` (`$CODEX_DIR`-relative, exact paths only - never glob user skills/prompts), plus a test proving stale aliases are removed while unrelated entries survive.
- Smoke tests -> flat path: `prospect_smoke_test.sh:217`, `smoke_test.sh:1979,1997`, `resolve-pr_smoke_test.sh:26,140`, `map_smoke_test.sh:132`, `strategy_smoke_test.sh:535,542,549,565` (this one BUILDS a nested fixture dir - flatten the fixture layout too).
- `plugins/flow-next/scripts/ci_test.sh:440`: `commands/flow-next/strategy.md` -> `commands/strategy.md`.
- `plugins/flow-next/tests/test_no_default_hooks.py:25` and `test_model_routing_scaffold.py:24,45`: UNINSTALL path -> flat.
- `.cursor-plugin/plugin.json:19` -> `"./commands"`; `install-cursor.sh:21-23,87` + `install-cursor.ps1` -> flat globs.
- `scripts/ci/verify_cursor_install.py:41` -> `root / "commands"`; run it against a FRESH temp-HOME install (installer dest override), never the user's live ~/.cursor.
- `scripts/sync-codex.sh`: update comment :1487; REMOVE the `generate_redirect_skill "flow-next-epic-review" ...` line (:1519); run twice - second run byte-identical; commit mirror diff (epic-review redirect skill removal).
- NEW `plugins/flow-next/tests/test_cursor_plugin_surface.py`: assert (a) no `commands/flow-next/` dir, (b) >=23 `commands/*.md` shims, (c) `.cursor-plugin/plugin.json` commands == `./commands`, (d) no shim frontmatter `name:` contains a colon, (e) `epic-review.md` absent.
- **Live-menu proof (R1):** fresh Claude Code session with the modified plugin (`claude --plugin-dir plugins/flow-next` or reinstalled local marketplace): capture menu//help inventory showing `/flow-next:qa` and no duplicated prefixes; one typed invocation reaches `flow-next-qa` skill. Also run `claude plugin validate plugins/flow-next` (schema only). Save captured output as evidence.
- Final sweep (live trees only): `grep -rn "commands/flow-next" plugins/flow-next/commands plugins/flow-next/skills plugins/flow-next/docs plugins/flow-next/tests plugins/flow-next/scripts scripts agent_docs README.md docs 2>/dev/null` -> zero hits (docs rows fixed in .2, so at this task's end only the two docs-row files may still hit; note them for .2).

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/commands/flow-next/qa.md` - canonical shim shape
- `scripts/install-codex.sh:240-270` - prompts copy loop
- `scripts/ci/verify_cursor_install.py:30-115` - assertions + install-dir handling
- `scripts/sync-codex.sh:1480-1530` - comment + epic-review generator
- `scripts/install-cursor.sh` - rsync excludes + count checks

**Optional:**
- `plugins/flow-next/tests/test_install_cursor_parity.py`, `test_cursor_clean_tree.py` - test patterns to mirror in the new test
- Claude Code docs: skills "How a skill gets its command name" (v2.1.216+ semantics)

## Key context

- `.claude-plugin/plugin.json` has NO `commands` key - Claude Code auto-discovers `commands/`; no manifest edit needed on the Claude side (manifest description counts are task .2).
- Codex mirror skills don't consume the shims, but `install-codex.sh` copies them as PROMPTS - that loop is load-bearing.
- fn-123 (Cursor first-class) already landed; its installer excludes (codex/ + tests/) must not regress.

## Acceptance

- [ ] 23 shims flat at `plugins/flow-next/commands/*.md`; `commands/flow-next/` gone; `epic-review.md` deleted; sync-codex generator line removed so the Codex mirror sheds `flow-next-epic-review` (alias removed on ALL platforms)
- [ ] No shim frontmatter contains `name: flow-next:...`; treatment uniform; choice justified in commit message (R2)
- [ ] Every consumer in the spec inventory table updated: cursor manifest + installers, `install-codex.sh:252` loop, `ci_test.sh:440`, `test_no_default_hooks.py`, `test_model_routing_scaffold.py`, `verify_cursor_install.py`, all five smoke tests (prospect/smoke/resolve-pr/map/strategy incl. its fixture layout)
- [ ] `install-codex.sh` removes stale `flow-next-epic-review` skill dir + `epic-review.md` prompt on upgrade (exact targets only); test proves unrelated user skills/prompts untouched; affected smoke tests pass
- [ ] NEW `test_cursor_plugin_surface.py` green with the five assertions listed in Approach
- [ ] Focused suites green: `cd plugins/flow-next/tests && python3 -m unittest test_install_cursor_parity test_cursor_review_commands test_cursor_clean_tree test_model_routing_scaffold test_no_default_hooks test_cursor_plugin_surface -q`
- [ ] `verify_cursor_install.py` passes against a fresh temp-HOME install
- [ ] Live-menu evidence captured: fresh-session inventory shows `/flow-next:qa`, no duplicated prefixes; typed invocation reaches the skill; `claude plugin validate` passes
- [ ] `./scripts/sync-codex.sh` twice: second run byte-identical; mirror diff committed
- [ ] Live-tree grep sweep clean (only task-.2 docs rows may remain, explicitly listed in the task summary)

## Done summary
Flattened the 23 command shims to plugins/flow-next/commands/*.md (deleted the dead epic-review alias on all platforms incl. the Codex mirror redirect skill), and updated every live path consumer in lockstep (Cursor manifest + installers + CI verifier, Codex prompts loop + exact-target stale-alias upgrade cleanup, ci_test.sh, 2 unit tests, 5 smoke tests, sync-codex).

**Frontmatter `name:` — FINAL implementation (revised after rebase onto fn-123 + GPT-5.6-sol review):** each shim carries a BARE, colon-free `name: <cmd>` (e.g. `name: qa`), NOT a removed name. An earlier iteration removed `name:` entirely (basename governs), but fn-123 R11 / Cursor's marketplace review checklist require `name` + `description` on every command, so the field stays — just de-prefixed. Bare name fixes Claude Code's tripled prefix (v2.1.216+ prepends the plugin prefix to the last segment; a colon renders literally) while keeping the Cursor contract.

**Live-menu evidence — re-captured on the bare-name head (2026-07-22):** fresh headless `claude --plugin-dir plugins/flow-next -p` inventory rendered all 23 as clean `/flow-next:<cmd>` (no duplicated prefixes, no epic-review), and a typed `/flow-next:qa` dispatched the skill; `claude plugin validate plugins/flow-next` passes. (The originally-recorded proof below was captured against the earlier name-removed commit d057f689; the bare-name variant was independently re-verified on the current head and by a GPT-5.6-sol regression review.)

Live-menu raw capture (fresh headless `claude --plugin-dir plugins/flow-next -p`, 2026-07-22; relevant command-shim lines from the unfiltered live inventory):

```text
/flow-next:audit
/flow-next:capture
/flow-next:impl-review
/flow-next:interview
/flow-next:land
/flow-next:make-pr
/flow-next:map
/flow-next:memory-migrate
/flow-next:pilot
/flow-next:plan
/flow-next:plan-review
/flow-next:prime
/flow-next:prospect
/flow-next:qa
/flow-next:ralph-init
/flow-next:resolve-pr
/flow-next:setup
/flow-next:spec-completion-review
/flow-next:strategy
/flow-next:sync
/flow-next:tracker-sync
/flow-next:uninstall
/flow-next:work
```

The same live inventory contained zero tripled command names and no `epic-review` entry. Inherent plugin-prefixed skill entries such as `/flow-next:flow-next-qa` remain separate from these command shims.

Typed invocation probe:

```text
$ claude --plugin-dir plugins/flow-next -p "/flow-next:qa fn-124-flatten-plugin-command-shims-fix -- probe dispatch only; stop after loading the skill" --model haiku --output-format stream-json --verbose --tools Skill
{"type":"tool_use","name":"Skill","input":{"skill":"flow-next:qa","args":"fn-124-flatten-plugin-command-shims-fix -- probe dispatch only; stop after loading the skill"}}
```

Remaining old-path references, deliberately left for task .2 (docs rows): plugins/flow-next/docs/platforms.md:208,237; plugins/flow-next/docs/strategy.md:58; agent_docs/adding-skills.md:7. Codex impl-review: SHIP (first pass; one non-blocking Minor: raw capture now embedded here).
## Evidence
- Commits: d057f6891b59095f3fe963cd3659fb94ca95ad4c
- Tests: baseline: green (focused suite pre-edit, 67 tests OK), cd plugins/flow-next/tests && python3 -m unittest test_install_cursor_parity test_cursor_review_commands test_cursor_clean_tree test_model_routing_scaffold test_no_default_hooks test_cursor_plugin_surface test_install_codex_legacy_cleanup -q (73 tests OK), HOME=<tmp> ./scripts/install-cursor.sh && python3 scripts/ci/verify_cursor_install.py --dest <tmp>/.cursor/plugins/local/flow-next (OK: skills=28 commands=23 agents=22), claude plugin validate plugins/flow-next (Validation passed), ./scripts/sync-codex.sh x2 (second run byte-identical), live-menu proof: claude --plugin-dir ... -p rendered all 23 as /flow-next:<cmd> (no tripled prefixes, no epic-review); typed /flow-next:qa dispatched Skill flow-next:qa, python3 scripts/run_tests_parallel.py (SUMMARY files=108 ran=2069 failures=0 errors=0 skipped=3; OK), exact live-tree grep from the spec (zero hits)
- PRs:
