# fn-111-flowctl-dead-surface-removal-sweep-docs.1 Pre-1.0 migration machinery removal + porting prose

## Description
Remove the pre-1.0 migration machinery entirely (maintainer decision 2026-07-19: now, not at 3.0) and replace it with agent-portable porting prose.

**Size:** L
**Files:** plugins/flow-next/scripts/flowctl.py + .flow/bin/flowctl.py (dual copy), plugins/flow-next/skills/flow-next-setup/workflow.md (migration arm = Step 1b), plugins/flow-next/skills/flow-next-setup/templates/usage.md + .flow/usage.md (porting prose, BYTE-IDENTICAL - test_dogfood_template_parity enforces), plugins/flow-next/docs/troubleshooting.md, plugins/flow-next/skills/flow-next-capture/*, plugins/flow-next/skills/flow-next-make-pr/* (legacy-epics scan clauses), deleted tests

### Approach

- Read fn-101 plan section 2 (.flow/specs/fn-101-flowctl-determinism-audit-what-still.md) for the exact line-ref table: migrate-rename + migrate-rollback + banner hook + migrate-state ~1.46k LOC at flowctl.py:18325-19782 + main-hook 33779 (line refs are from the audit HEAD - re-locate by symbol, do not trust raw offsets).
- Remove: cmd_migrate_* functions, their argparse registrations, the banner hook call in main, migrate-state helpers, the .flow/.banner-acknowledged / .migrating / .migration-manifest handling that only migration wrote (keep .flow/.gitignore patterns - historical repos still have the files).
- Setup skill: delete Step 1b (pre-1.0 detection + AskUserQuestion migration arm) from workflow.md; renumber references to it.
- Capture/make-pr prose: remove the legacy-epics scan clauses (grep for "epics/" and "pre-1.0" in those skills).
- REPLACEMENT prose (three sentences, agent-executable): in the setup-managed usage.md template AND the repo dogfood copy (byte-identical), plus one line in troubleshooting.md: rename .flow/epics/ -> .flow/specs/, rename epic-*.json keys per the mapping, run flowctl validate.
- Delete orphaned tests: test_migrate_rename.py (24), test_banner.py (26), test_lockfile.py (12) - BUT verify first that each file pins ONLY the removed machinery (read every test case; the audit says orphaned, trust but verify). Any case pinning surviving behavior (e.g. a general-purpose lock helper still used by pilot-log/tracker paths) moves to a surviving test file instead of dying - each named in the commit message with what made it stale (machinery deleted). migration_smoke.sh: delete + remove its CI step.
- Dual-copy flowctl mirrored byte-identical; ./scripts/sync-codex.sh x2.
- NO git commands - the host owns git.

### Acceptance

- [ ] flowctl has no migrate-rename/migrate-rollback/migrate-state commands; banner hook gone from main; flowctl --help mentions none of them
- [ ] Setup workflow has no Step 1b migration arm; usage.md template + dogfood copy carry the 3-sentence porting prose byte-identically; troubleshooting.md has the porting line
- [ ] test_migrate_rename.py, test_banner.py, test_lockfile.py, migration_smoke.sh deleted; CI migration_smoke step removed
- [ ] Focused suites green: python3 scripts/run_tests_parallel.py --pattern "test_dogfood_template_parity.py" and --pattern "test_setup*.py" and --pattern "test_flow_gitignore.py"
- [ ] Both flowctl.py copies byte-identical; sync-codex idempotent

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
