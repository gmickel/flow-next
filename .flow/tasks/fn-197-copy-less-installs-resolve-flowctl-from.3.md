# fn-197-copy-less-installs-resolve-flowctl-from.3 Retire the copy plumbing in flowctl and replace plan's drift check with the migration nudge

## Description
**What:** Retire the copy plumbing inside flowctl (delete `setup-mode`, the launcher self-heal, the dual-write), replace `/flow-next:plan`'s drift check with the delete-me nudge, and give flow-next-tui install-location resolution — regenerated artifacts in the same commit.

**Execution checklist — `plugins/flow-next/scripts/flowctl.py` (line numbers @ origin/main 71e80932):**
1. Delete `LAUNCHER_SH` / `LAUNCHER_CMD` constants + their comment (~L19952-20089) and `_stamp_flow_bin_launchers` (~L20091-20136) — sole consumer of the constants; ralph-init copies from `$PLUGIN_ROOT/scripts/` directly (verified, no dependency).
2. Delete the `cmd_init` call site (~L20146-20151, `actions.extend(_stamp_flow_bin_launchers(...))`). Note: `init --json` `actions[]` loses the two `"stamped bin/…"` values — a documented output-shape change.
3. Delete the `setup-mode` subcommand: `cmd_setup_mode_set` (~L20386-20496) and its argparse registration (~L51058-51076). Old `setup_mode`/`setup_version` fields in `.flow/meta.json` become inert metadata — tolerated on read everywhere, never written, never enforced.
4. Reconcile `PLUGIN_MODE_COPY_ARTIFACTS` (~L20353-20361): ADD `.flow/bin/flowctl_tracker/` (pre-existing hole vs setup's own table), RENAME to reflect its new job (the residue-detection list feeding setup's cleanup offer, task .2), keep it exported/documented as the single machine-readable manifest of legacy copy artifacts.
5. KEEP verbatim (settled): `cmd_usage`'s `.flow/usage.md` fallback (~L20320-20345) and `_memory_template_path` tier 2 (~L22133-22152) as inert legacy grace; `PROTECTED_ARTIFACTS_BLOCK` (~L9265-9269) including `.flow/bin/*`; gate rules (`GATE_FORCE_FULL_PREFIXES` ~L44508, `_gate_ignored_worktree_path` ~L44651, `_classify_gate_path` ~L44829) and their test pins.
6. `_EXPORT_DEFAULT_DERIVED_PATHS` (~L32361-32378): remove the default `dualCopy` entry (`.flow/bin/flowctl.py` ← `scripts/flowctl.py`); KEEP the `dual-copy` kind supported for user-configured `makePr.derivedPaths`.
7. Reword the ×7 tracker-package-missing error strings (~L39783-40043) "re-run /flow-next:setup (or reinstall) to get the tracker verbs" → "update/reinstall the flow-next plugin"; same for ~L8069 and the `.flow/usage.md` route-there strings at ~L1789/1840 (→ `flowctl usage`).
8. `flowctl_tracker/__init__.py` L5-9 docstring: drop the "copy-mode setup writes a fixed list into `.flow/bin/`" clause (Ralph clause stays).
9. Regenerate `scripts/flowctl-help.txt` (generated, byte-pinned by `test_startup_bootstrap::test_tracked_root_help_matches_argparse_byte_for_byte`) — `setup-mode` disappears from lines 2/7/65.
10. `plugins/flow-next/scripts/flowctl_bootstrap.py`: `_usage_fast_path` (~L78-95) keeps its `.flow/usage.md` rung (lockstep with decision 5); reword only the error string at ~L28-30 if the cmd_usage one changes.
11. `plugins/flow-next/scripts/smoke_test.sh` ~L129-169: delete the whole three-assertion self-heal block (shell twin of the deleted tests).

**`skills/flow-next-plan/SKILL.md` (canonical; mirror regenerates):**
12. Delete `## Copy-mode version drift` (L28-30) — the `setup_version`-vs-manifest comparison, the Refresh AskUserQuestion, all of it. Replace with the migration nudge: leftover copy artifacts present (same residue list as step 4) → one short line that they're no longer needed and can be deleted (or cleaned by `/flow-next:setup`); absent → silent. Never read/write `version_ack`/`snippet_ack`/`setup_version`.
13. Drop `ui_version_check` from `skills/flow-next-ralph-init/templates/ralph.sh` (~L286-299) — its "run setup to refresh local scripts" advice is now wrong.

**flow-next-tui (independent resolver — a copy-less USER repo has no `.flow/bin`, no `plugins/` dir, and usually no PATH flowctl; today's resolver would fail):**
14. `flow-next-tui/src/lib/flowctl.ts` `getFlowctlPath` (~L163-240): keep existing rungs (legacy grace) and ADD install-location rungs after them: `~/.claude/plugins/marketplaces/flow-next/plugins/flow-next/scripts/flowctl` (+ the versioned cache glob), `~/.codex/scripts/flowctl`, `~/.cursor/plugins/local/flow-next/scripts/flowctl` (+ cache glob). Update the doc comment and `flow-next-tui/README.md:185` resolution-order list.

**sync-codex + tests:**
15. Run `./scripts/sync-codex.sh` twice; commit the regenerated mirror (plan SKILL.md mirror changes; check the ~L1936-1944 plan-drift guard didn't survive .2 — if it did, delete here).
16. Test pins (named; grep for more): DELETE `tests/test_setup_mode_stamp.py` (whole file, 13 tests) and `tests/test_init_stamp_launchers.py` (whole file — constants + self-heal die together); `test_startup_bootstrap.py` — delete `test_dogfood_bootstrap_is_byte_identical` only in .4 (dogfood still present here), delete `test_copy_launcher_uses_local_usage_and_preserves_help`'s `setup-mode set copy` assertions (L222-229) here, keep `test_usage_fast_path_copy_fallback_and_missing_error` (fallback stays); `test_precheck_mode_contract.py` — drift-contract tests die with the plan section, keep+generalize the template negative assertion (coordinated with .2); `test_export_traceability.py:129-153` — retarget the three dual-copy tests to a user-configured `makePr.derivedPaths` fixture; `test_pr_cognitive_aid.py:86` fixture path; `test_flowctl_surface.py:166` (`setup-mode set` literal — delete; L474-481 removed-surface regex: ADD `setup-mode`); `test_cmd_usage.py` keeps its fallback test; `test_removed_delegate_config_advisory.py:8` docstring reword. CI workflow step ~L468-476 ("Runtime, launcher, usage, and setup-mode contracts") loses `test_setup_mode_stamp` + `test_init_stamp_launchers` from its list — edit the step here or coordinate with .4's workflow edits.

**Touches:** plugins/flow-next/scripts/flowctl.py, plugins/flow-next/scripts/flowctl_bootstrap.py, plugins/flow-next/scripts/flowctl-help.txt (regenerated), plugins/flow-next/scripts/flowctl_tracker/__init__.py, plugins/flow-next/scripts/smoke_test.sh, plugins/flow-next/skills/flow-next-plan/**, plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh, flow-next-tui/src/lib/flowctl.ts, flow-next-tui/README.md, plugins/flow-next/codex/** (regenerated), .github/workflows/test-flow-next.yml (test-list step), plugins/flow-next/tests/**
## Acceptance
- [ ] `setup-mode` gone from CLI, argparse, and regenerated `flowctl-help.txt` (byte-parity test green); old meta stamps read without error anywhere.
- [ ] `_stamp_flow_bin_launchers` + LAUNCHER_* constants + cmd_init call gone; `flowctl init` in any repo creates no bin files; smoke_test block removed.
- [ ] Residue list reconciled (includes `flowctl_tracker/`) and renamed to its detection role; kept rungs (usage fallback, memory-template tier 2, protected paths, gate rules) verbatim with their tests green.
- [ ] Default dualCopy derivedPaths entry removed; user-configured dual-copy still classifies (retargeted tests prove it).
- [ ] Plan skill: no version comparison, no version_ack/snippet_ack/setup_version reads; nudge fires only on residue, delete-oriented; ralph.sh ui_version_check gone; mirror regenerated (sync twice).
- [ ] Tracker-missing error strings say update/reinstall the plugin, not re-run setup.
- [ ] flow-next-tui resolves flowctl in a copy-less user repo via the new install-location rungs; README order updated.
- [ ] test_setup_mode_stamp + test_init_stamp_launchers deleted; other named pins retargeted; CI test-list step updated; suite green.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
