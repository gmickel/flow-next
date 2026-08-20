---
satisfies: [R5, R6]
---
# fn-201-opencode-install-path-from-canonical.3 Manifest-driven uninstall plus deterministic OpenCode installer tests

## Description
Add --uninstall to scripts/install-opencode.sh: remove exactly the paths listed in the task-1 ownership manifest (skills dirs, generated agents/flow-next-*.md, generated commands/flow-next-*.md, support dirs scripts/, templates/, references/, docs/) plus the manifest itself — reading the MANIFEST, never the current source tree, so a skill renamed upstream between install and uninstall still gets cleaned. Leave user content in the same config dir untouched. A re-install after uninstall must be byte-identical to a fresh install into an empty dest (guaranteed by the deterministic manifest — no timestamps).

Add pure-stdlib unittest coverage under plugins/flow-next/tests/ that runs in CI with no OpenCode binary, driving the installer via --dest into temp dirs (pattern: test_install_codex_legacy_cleanup.py). Cover: generator fixtures (happy-path canonical-shaped agent -> expected pinned-schema frontmatter; ALL THREE fail-closed cases from task 2; command-stub generation incl. the uninstall-verbatim and setup-excluded cases); an invariant test that fails when a canonical agents/*.md carries a disallowedTools token the generator has no mapping for (style: test_cursor_agent_frontmatter.py); the plugin-root READ-SURFACE PIN per the spec's precise derivation rule (grep-derived top-level segments MINUS the named exclusion list == installed support dirs; the test fails when a NEW segment appears in neither set - never a naive equality over the raw grep, which matches host manifests, the codex/ mirror, and non-path noise); installer path-ownership (no writes outside manifest paths; pre-flight collision abort on an unclaimed existing support dir; --force override); the R2 layout invariant (two-levels-up flowctl executable + manifest-verified, templates/spec.md present; NOTE these tests are self-referential on the pinned directory names - host discovery is the R2 MANUAL item, never asserted here); --uninstall scope; reinstall-after-uninstall byte-identity; tracker verifier invoked (extend test_tracker_distribution.test_every_installer_invokes_the_shared_verifier to include scripts/install-opencode.sh). Skip live bash installer execution on native Windows. Do not assert live skill prose (G2).

Touches: scripts/install-opencode.sh, plugins/flow-next/tests/test_install_opencode.py, plugins/flow-next/tests/test_opencode_agent_frontmatter.py, plugins/flow-next/tests/fixtures/opencode-install/, plugins/flow-next/tests/test_tracker_distribution.py, plugins/flow-next/scripts/lib/opencode*.py, .github/workflows/test-flow-next.yml
Files:
- scripts/install-opencode.sh (--uninstall)
- plugins/flow-next/tests/test_install_opencode.py
- plugins/flow-next/tests/test_opencode_agent_frontmatter.py
- plugins/flow-next/tests/fixtures/opencode-install/
- plugins/flow-next/tests/test_tracker_distribution.py
- plugins/flow-next/scripts/lib/opencode*.py (only if tests require a seam)
- .github/workflows/test-flow-next.yml (only if an install smoke is added beside the Cursor one)

## Acceptance
R5: --uninstall deletes only manifest-listed paths plus the manifest and leaves sibling user files; installing into a clean dest vs uninstall-then-reinstall produces byte-identical trees. R6: cd plugins/flow-next/tests && python3 -m unittest test_install_opencode test_opencode_agent_frontmatter test_tracker_distribution -q is green without OpenCode installed; fixtures cover the pinned-schema frontmatter and all three fail-closed cases; the unmapped-token invariant test exists and fails on an unmapped canonical token; the read-surface pin test implements derived - exclusions == installed and fails on a new unhandled segment; command-stub tests cover description + $ARGUMENTS + installed path + uninstall-verbatim + setup-excluded; path-ownership tests fail if the installer writes outside manifest paths or deletes an unclaimed pre-existing dir; test_every_installer_invokes_the_shared_verifier includes install-opencode.sh.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
