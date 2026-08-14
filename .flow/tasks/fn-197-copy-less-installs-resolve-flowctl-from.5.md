# fn-197-copy-less-installs-resolve-flowctl-from.5 Docs sweep: retire the dual-mode story from every in-repo doc

## Description
**What:** In-repo docs sweep — the dual-mode story disappears everywhere; the documented world is: install the plugin once, `/flow-next:setup` once per repo (snippet + config), re-run only on snippet-schema bump; old copies can simply be deleted.

**Execution checklist — `plugins/flow-next/docs/`:**
1. `platforms.md` (partial restructure, not whole-file): DELETE the `## Setup modes: plugin vs copy (fn-121)` section (L37-47 incl. the 5-row table) → replace with a 3-5 line "What setup does"; DELETE the "Why other hosts can't have plugin mode" paragraph (L67); rewrite L7 (intro copy-mode clause), L31 (Grok matrix cell), L56+L60-65 (flowctl_tracker verification story — installers only now), L193-218 Codex per-project fence (delete the optional `.flow/bin` copy block L212-216 + bullet L197), Grok claims (L232, 254, 263, 273), Cursor claims (L289, 298, 322, 332-333), Windows section (L352 "Both live under `.flow/bin/`…" → plugin `bin/`; L354 alias-stub recovery path). ANCHOR TRAP: `#setup-modes-plugin-vs-copy-fn-121` has 3 inbound links — fix `docs/architecture.md:261`, `docs/flowctl.md:136`, `docs/troubleshooting.md:14` in this task.
2. `troubleshooting.md`: replace the whole "Just updated the plugin? Re-run setup" section (L5-14) with "Updated the plugin — do I re-run setup? **No**, unless the snippet schema bumped (setup tells you)"; L18 porting pointer → `flowctl usage`; L167 Windows re-run advice → "update the plugin"; L179-187 broken-launcher recovery → keep, explicitly labeled as legacy-copy recovery; ADD a short "I have `.flow/bin/` from an old install" → delete it, nothing depends on it.
3. `flowctl.md`: L5 (`.flow/usage.md` → `flowctl usage`), L65 (init re-stamps launchers — dead after .3, delete), L67, L123 (usage resolution → bundled, one-line legacy note), DELETE L129-136 (`setup-mode` command reference + check TOC/anchors), L182-188 (setup-block CI recipe: drop the `setup_mode: copy` framing, recipe survives — `.flow/templates/claude-block.md` there is USER-owned, not a setup copy), L416 (derivedPaths default — dual-copy example gone), L1787 (prime emitter dual-copy prose), L1946+L1957 (gate cleanliness/FORCE-FULL: keep the rules — settled — but reword the rationale as legacy-path handling), L2174 (drop the setup half).
4. `architecture.md`: L110 pointer; L261 rewrite to the single resolution story (its cross-link target died in step 1).
5. `spec-template.md`: L18-27 retitle `## 3-tier discovery cascade`, delete tier 3, renumber; L37 strip the copy-mode comment; L298 protected-artifacts bullet — keep the `.flow/bin/*` protection, strike only the mode clause.
6. `orchestration.md` L149, L241, L323: strip the "`.flow/usage.md` in copy-mode repos" alternatives → `flowctl usage` only.
7. `memory-schema.md` L192: rewrite the mitigation rationale (single source now, no lockstep-copies premise).
8. `ralph.md` L816: relabel the `.flow/bin` launcher example as a legacy spelling the guard still recognizes.
9. `docs/README.md`: verify no broken links post-restructure.
10. `ci-workflow-example.yml` L28-30: delete the commented Option-1 `.flow/bin` block; the curl path becomes the only option.
11. `running-lean.md`: verify its one mention (grep) and fix.

**Repo-level + agent_docs:**
12. Root `README.md`: replace the `### After every update` trio (L175-181) with one paragraph — "Nothing is copied into your repo. Plugin updates land silently. Re-run `/flow-next:setup` only when the snippet schema bumps, or to change configuration."; L479 reword.
13. `STRATEGY.md:53`: light rewrite of the copy-mode clause.
14. Repo-root `SPEC.md:51`: cascade tier line (regenerate from the new template or hand-fix).
15. `agent_docs/setup-modes.md`: wholesale rewrite (or rename to `agent_docs/setup.md`): keep invariants 1-3 (consent, block-id markers + sentinel, per-(path,id) hashes) and "Where things live" minus the mode pairs; delete the taxonomy, resolution-chain table's copy column, drift section, state machine. MUST state the new rule explicitly (the old invariant 6 — "bare `flowctl` never in skill prose" — is inverted by fn-197; without a stated replacement the next contributor re-adds `.flow/bin` fallbacks). Fix inbound links: root `CLAUDE.md:87`/`143` (done in .4 — verify), `docs/platforms.md:67` (done in step 1 — verify).
16. `agent_docs/local-dev.md`: L117-121 fence → bare `flowctl`; L127, 130, 146, 149, 152 spellings; L161/188 cascade prose; L228 contributing-scope clause.
17. `agent_docs/conduct/setup.md`: L8 drop `.flow/usage.md` from user-owned files; L10 delete the mode-stamp bullet; ADD: "Nothing is copied into `.flow/`; a run that writes `.flow/bin/` has broken this."
18. `agent_docs/releasing.md`: no setup-refresh step exists (verified) — keep the installer re-run note (L140-151); ADD one checklist line: "if `SNIPPET_SCHEMA_VERSION` bumped, say so in the changelog upgrade-actions block".
19. Install scripts' user-facing text: `scripts/install-cursor.sh` L27 + L113-114 and `scripts/install-cursor.ps1` L29 + L146-147 (the only Windows-spelling `.flow\bin` hits in the repo) — setup no longer writes `.flow/bin`; describe snippet + config. `install-codex.sh` needs nothing (verified). `plugins/flow-next/scripts/lib/verify_tracker_manifest.py:4` docstring drops "copy-mode".
20. CHANGELOG: add the Unreleased entry (register gate) — behavioral, user-visible: copies retired, delete-safe migration, one-mode setup, setup re-run story. No benchmark numbers, no speed claims, no external attribution. Never edit historical entries.

**Exit criterion (run it):** `git grep -n "\.flow/bin\|\.flow\\\\bin" -- ':!.flow' ':!CHANGELOG.md' ':!optimization' ':!agent_docs/archive' ':!agent_docs/guidance-eval' ':!agent_docs/optimization-log.md'` returns only: the rung-3 preamble lines, migration/leftover-cleanup prose, protected-path lists, gate-rule code + pins, ralph-guard legacy-recognition fixtures/prose, explicitly-labeled legacy/history notes. Anything else is a miss.

**Touches:** plugins/flow-next/docs/**, README.md, STRATEGY.md, SPEC.md, agent_docs/setup-modes.md, agent_docs/local-dev.md, agent_docs/conduct/setup.md, agent_docs/releasing.md, scripts/install-cursor.sh, scripts/install-cursor.ps1, plugins/flow-next/scripts/lib/verify_tracker_manifest.py, CHANGELOG.md, plugins/flow-next/codex/** (regenerated if any canonical skill text moved), plugins/flow-next/tests/** (docs-pinning tests)
## Acceptance
- [ ] The grep exit criterion in the checklist passes: every remaining `.flow/bin` (or `.flow\bin`) hit is a rung-3 line, migration prose, protected-path list, gate-rule residue, ralph-guard legacy recognition, or a labeled legacy/history note.
- [ ] platforms.md has no mode section or mode table; all three inbound anchors fixed; Codex/Grok/Cursor/Windows host sections tell the chain story.
- [ ] troubleshooting leads with "plugin updates need no setup re-run"; legacy-copy recovery + delete-your-old-copies sections present and labeled.
- [ ] flowctl.md has no setup-mode reference; cascade documented as 3 tiers everywhere (spec-template.md, references walker already done in .2 — verify).
- [ ] Root README After-every-update is one copy-free paragraph; STRATEGY.md and repo SPEC.md updated.
- [ ] agent_docs: setup-modes rewritten to one mode with the new contributor rule stated explicitly; local-dev bare `flowctl`; conduct/setup has the "a run that writes `.flow/bin/` has broken this" line; releasing gains the snippet-bump checklist line.
- [ ] Installer text (sh + ps1) matches the new setup behavior; CHANGELOG Unreleased entry present; register/format gates pass; no speed claims or attribution.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
