# fn-197-copy-less-installs-resolve-flowctl-from.1 Add the plugin-root derivation rung to every flowctl preamble, fix the hardcoded sites, rewrite the Cursor rail

## Description
**What:** Add the probe-proven plugin-root derivation rung (rung 2) to every canonical FLOWCTL preamble, fix the hardcoded and broken sites, rewrite the Cursor rail, and make sync-codex + ralph-guard rung-2-aware — all in one commit so mirror parity and sync guards never go red.

**The new canonical preamble (exact wording, proven live on Cursor CLI + Cursor app + Grok, 2026-08-14):**
```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**Execution checklist:**
1. **Bulk preamble edit — 49 standard sites** (one 2-line pair each, mechanically identical; insert rung 2 between the pair): `agents/quality-auditor.md` (NOTE: line ~208 uses a single-line `; `-joined form — convert it to the 3-line form), `agents/repo-scout.md` (2 pairs), and the 46 skill-file sites under `plugins/flow-next/skills/` (flow-next-audit, -capture ×3, -chart ×6, -deps, -export-context, -guide, -impl-review, -interview ×3, -land ×2, -make-pr ×2, -map ×2, -memory-migrate ×2, -pilot ×2, -plan, -plan-review, -prime/workflow.md ×3-in-one-file, -prospect ×2, -qa ×2, -resolve-pr ×2, -spec-completion-review, -strategy, -sync, -tracker-sync, -visual, -work ×3, flow-next/SKILL.md).
2. **Fix the nonstandard/broken sites:**
   - `agents/worker.md:283` — carries rung 1 with NO fallback at all (latent bug); give it the full 3-rung chain.
   - `skills/flow-next-tracker-sync/references/status-sync.md:57` — hardcodes `.flow/bin/flowctl` for BRANCH_NAME; use `$FLOWCTL`.
   - `agents/docs-gap-scout.md:47` — hardcodes `.flow/bin/flowctl` then silently degrades to `find`; give it the chain.
3. **Rewrite `rules/flow-next.mdc`** (Cursor rail, lines 8-14): replace the five `.flow/bin/flowctl` invocations and the "if `.flow/bin/flowctl` is not found run `/flow-next:setup`" remedy with the chain + "If `flowctl` is not found: run `/flow-next:setup`".
4. **scripts/sync-codex.sh — make the mirror rung-2-aware (three sub-edits):**
   - Fallback injector #1 (skill files, ~L272-304: equality test L287, trigger L292, inject L295) and injector #2 (agent bodies, ~L1785-1823: equality L1798, trigger L1802, inject L1812) both key on exact next-line equality with the OLD fallback string — with rung 2 inserted they inject a DUPLICATE `.flow/bin` rung into every mirrored file. Either make them scan the following block for the fallback literal, or delete them (the canonical text now carries rungs 2+3 which flow through the line-1 sed untouched). Verify by regenerating and grepping the mirror for duplicate fallback lines.
   - The line-1 sed (env vars → `${CODEX_HOME:-$HOME/.codex}/scripts/flowctl`) is unchanged; the mirror ships CODEX_HOME rung 1 + the same rung-2/rung-3 tail.
   - Run `./scripts/sync-codex.sh` TWICE (idempotence) in the same commit; commit the regenerated `plugins/flow-next/codex/**` including `codex/agents/*.toml` (they have `.flow/bin` baked in at worker.toml:418, repo-scout.toml:30,45, quality-auditor.toml:208, docs-gap-scout.toml:47).
5. **`plugins/flow-next/scripts/hooks/ralph-guard.py` ~L798-802**: the composition screen exempts the exact current preamble as "the standard preamble … NOT composition". Add rung 2 to that exemption or Ralph fails closed on every skill invocation. Its other `.flow/bin` mentions (docstrings/examples at 737, 752, 802, 1028, 1284, 1643) stay — the guard must keep recognizing legacy spellings.
6. **`agent_docs/adding-skills.md` ~L102-131**: this is the preamble's contributor spec. Update the pattern to the 3-rung chain, rewrite L111's copy-mode caveat, and update L131's description of the sync-codex fallback interplay to match whatever step 4 did.
7. **Explicitly unchanged:** `plugins/flow-next/bin/flowctl` (the plugin's own Claude Code PATH-injection launcher) and the review-prompt protected-path lists.

**Test pins to retarget in the same commit (named; grep for more):**
- `tests/test_guide_routing.py:130,134-138` — asserts BOTH preamble lines (line 1 split across two Python string literals — a naive sed won't match); add rung 2 to the assertion.
- `tests/test_cursor_plugin_surface.py:249-253` `test_flowctl_resolved_via_flow_bin` — asserts `.flow/bin/flowctl` in flow-next.mdc; retarget to the new rail text (rename the test to match its new meaning).
- `plugins/flow-next/scripts/map_smoke_test.sh:166` — asserts preamble line 1 only; verify still passes.
- `tests/test_ralph_guard.py:1027` — composed-token fixture embedding line 1; verify against the step-5 exemption change.
- Full suite green; capture exit codes directly (no piping to tail).

**Live probe before done:** tmp repo with `.flow/` data and no `.flow/bin`; `cursor-agent -p "list my flow tasks"` resolves the installed plugin's flowctl and succeeds.

**Touches:** plugins/flow-next/skills/**, plugins/flow-next/agents/**, plugins/flow-next/rules/**, plugins/flow-next/codex/** (regenerated), scripts/sync-codex.sh, plugins/flow-next/scripts/hooks/ralph-guard.py, agent_docs/adding-skills.md, plugins/flow-next/scripts/map_smoke_test.sh, plugins/flow-next/tests/**
## Acceptance
- [ ] All 49 standard sites + worker.md + quality-auditor's one-line form carry the three-rung chain, byte-identical rung-2 wording everywhere.
- [ ] status-sync.md:57 and docs-gap-scout.md:47 use the chain; no bare `.flow/bin/flowctl` invocation remains outside protected-path lists and gate rules.
- [ ] `rules/flow-next.mdc` teaches the chain; `test_cursor_plugin_surface` retargeted.
- [ ] `./scripts/sync-codex.sh` runs clean TWICE; regenerated mirror greps show exactly one `.flow/bin` fallback line per preamble (no injector duplicates); codex/agents/*.toml regenerated.
- [ ] ralph-guard's standard-preamble exemption covers the new rung (test_ralph_guard green, incl. the L1027 fixture).
- [ ] `agent_docs/adding-skills.md` shows the new pattern + updated sync interplay.
- [ ] test_guide_routing + map_smoke_test.sh pins retargeted; full suite green (exit codes captured directly).
- [ ] Live probe: bin-less tmp repo, `cursor-agent -p "list my flow tasks"` resolves the installed plugin's flowctl.
## Done summary
Added the derived-plugin-root rung (rung 2) to every canonical FLOWCTL preamble (52 sites, byte-identical wording), fixed the three nonstandard/hardcoded sites (worker.md had no fallback at all, quality-auditor's one-line form, docs-gap-scout + tracker-sync status-sync hardcoding `.flow/bin`), rewrote the Cursor rail to teach the chain, deleted sync-codex's two fallback-injector awks (they would have duplicated the `.flow/bin` rung) in favor of a mirror chain-integrity validation guard, regenerated the Codex mirror, and retargeted the affected test pins + contributor docs.

Live probe (acceptance): a bin-less tmp repo with `.flow/` data; `cursor-agent -p --trust --force` resolved and EXECUTED `/Users/gordon/.cursor/plugins/local/flow-next/scripts/flowctl` and returned the real task list. Note: the probe required refreshing the maintainer's local Cursor install from this working tree via `scripts/install-cursor.sh` — that install now points at unreleased working-tree prose until re-run after a pull.

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
stage: delegation - skipped(config: delegation off)


stage: impl-review - ran (host backend, fresh fable-5 reviewer, SHIP round 1; 3 P3 FYIs carried to .2/.5)
## Evidence
- Commits: 9fedadd96fca2592ddee40c49458f2acf2d70657
- Tests: python3 scripts/run_tests_parallel.py (files=192 ran=4397 failures=0 errors=0 skipped=8, exit 0), uvx ruff@0.16.0 check . (exit 0), bash plugins/flow-next/scripts/map_smoke_test.sh (75/75, exit 0), ./scripts/sync-codex.sh x2 (exit 0, idempotent), live probe: cursor-agent -p --trust --force in bin-less /tmp repo executed /Users/gordon/.cursor/plugins/local/flow-next/scripts/flowctl, impl-review: host backend SHIP round 1 (reviewer claude-fable-5, fresh read-only subagent; receipt /tmp/impl-review-receipt-fn-197-copy-less-installs-resolve-flowctl-from.1.json)
- PRs: