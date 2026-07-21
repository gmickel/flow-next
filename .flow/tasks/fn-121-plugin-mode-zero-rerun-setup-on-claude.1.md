---
satisfies: [R1, R2, R3]
---
# fn-121-plugin-mode-zero-rerun-setup-on-claude.1 flowctl mechanism: bin launcher, usage subcommand, canonical usage.md move

## Description
Formalize the two mechanism prototypes already on this branch and land the canonical usage.md move with every reference site updated. Size: M.

**Context**: Prototypes exist: `plugins/flow-next/bin/flowctl` (launcher) and `cmd_usage` in `plugins/flow-next/scripts/flowctl.py` (3.0.0: cmd_usage ~L7996; registration near the `cat` subparser). Probe evidence in session scratchpad binlab/FINDINGS.md. Read spec Architecture + Edge Cases first.

**Work**:
1. `bin/flowctl`: keep in lockstep with `scripts/flowctl` (fn-77 probe semantics: PYTHON_BIN, `py -3`, python3, python; intentional diff ONLY the exec target `$SCRIPT_DIR/../scripts/flowctl.py`). Follow the comment structure of the `LAUNCHER_SH` constant (flowctl.py ~L7788, 3.0.0).
2. `git mv plugins/flow-next/skills/flow-next-setup/templates/usage.md plugins/flow-next/templates/usage.md`.
3. `cmd_usage`: drop the transitional middle candidate (old skills path); final chain = `../templates/usage.md` then `.flow/usage.md`; error hint must read correctly in both modes (do not tell plugin-mode users to look for `.flow/usage.md`).
4. Update every old-path reference (grep gate, list is a floor): `skills/flow-next-setup/workflow.md:174-186` (read path + prompt-body path), `scripts/sync-codex.sh` transform (~L426) + guard (~L1707-1716), `plugins/flow-next/tests/test_dogfood_template_parity.py`, `test_token_budgets.py:22` (TEMPLATES dir - keep asserting usage.md budget from the NEW location; other setup snippets stay at the old dir), `plugins/flow-next/scripts/ralph_e2e_rp_test.sh:197`, `ralph_e2e_short_rp_test.sh:96`, `flow-next-capture/workflow.md`, `flow-next-make-pr/workflow.md`, `agent_docs/local-dev.md`, `agent_docs/guidance-eval/` (verify each hit; docs prose refs to `.flow/usage.md` runtime copies are NOT the template path - only rewrite template-location refs here; mode-qualifying prose claims is task .2).
5. New tests (pattern: `test_init_stamp_launchers.py`, importlib + tempdir style): `test_bin_launcher_parity.py` (byte-compare bin/flowctl vs scripts/flowctl modulo the exec-path line) and `test_cmd_usage.py` (bundled hit; `.flow/usage.md` fallback hit; neither = exit 1 + hint).
6. Dual-copy refresh for this dogfooding repo: `.flow/bin/flowctl.py` re-copied from `scripts/flowctl.py` (deliberate commit). NOTE: `scripts/ralph/` no longer exists here post-fn-114 (ralph is opt-in, zero-install) - the launcher trio in `.flow/bin/` is the only dual-copy set; a `scripts/ralph/flowctl.py` exists only in repos that ran ralph-init.
7. Run `./scripts/sync-codex.sh` TWICE; commit mirror diff with the change.

**Files**: plugins/flow-next/bin/flowctl, plugins/flow-next/scripts/flowctl.py, plugins/flow-next/templates/usage.md (new location), plugins/flow-next/skills/flow-next-setup/workflow.md (path literals only), scripts/sync-codex.sh (path literals only), plugins/flow-next/tests/{test_bin_launcher_parity.py (new), test_cmd_usage.py (new), test_dogfood_template_parity.py, test_token_budgets.py}, plugins/flow-next/scripts/{ralph_e2e_rp_test.sh, ralph_e2e_short_rp_test.sh}, .flow/bin/flowctl.py, plugins/flow-next/codex/** (regenerated), skills workflow refs listed above.
## Acceptance
- R1: `plugins/flow-next/bin/flowctl usage | head -3` prints the guide header; parity test green; `claude plugin validate plugins/flow-next` passes.
- R2: `test_cmd_usage.py` covers bundled hit / `.flow` fallback / neither (exit 1 + mode-appropriate hint); old-path candidate removed from cmd_usage.
- R3: `grep -rn "flow-next-setup/templates/usage.md" --exclude-dir=codex --exclude-dir=.flow --exclude-dir=.git .` returns ZERO hits (gate scoped to active sources - historical `.flow/specs|tasks|memory` records stay untouched); canonical file lives at `plugins/flow-next/templates/usage.md`.
- Dual copy refreshed (`.flow/bin/flowctl.py` byte-identical to `scripts/flowctl.py`; no `scripts/ralph/` in this repo post-fn-114).
- `./scripts/sync-codex.sh` run twice: second run produces no diff; all existing guards green.
- Focused suites green: `cd plugins/flow-next/tests && python3 -m unittest test_init_stamp_launchers test_bin_launcher_parity test_cmd_usage test_dogfood_template_parity test_token_budgets -q`.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
