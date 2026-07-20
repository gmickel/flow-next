## Description

Repo-specific verification conventions + corpus hygiene. MAINTAINER DIRECTIVE: no cross-model review; self-verifying via the suite itself.

**Size:** M
**Files:** CLAUDE.md (spec-authoring rule in the Flow-Next section; AGENTS.md is a symlink), .flow/templates/spec.md (Quick-commands scaffold comment), .flow/usage.md, plugins/flow-next/tests/ (stale removals + top-2 slow-file diet)

## Approach

- CLAUDE.md: short spec-authoring rule - Quick commands list FOCUSED suites for the feature's files; the FULL suite (parallel entrypoint from .1) runs once at the final gate; name the entrypoint. Mirror one line into .flow/templates/spec.md's Quick-commands comment + usage.md.
- Stale-test sweep: remove ONLY tests pinning gone behavior - verify each candidate against current code before deletion; known candidates: test_config_alias no-op-path cases (verify vs the alias machinery still present until fn-111 - if machinery still exists, DEFER those to fn-111 and remove nothing there), any pre-1.0 migration-path tests NOT owned by fn-111's list (cross-check fn-111's test-fallout list first - no double-delete). Every removal names what made it stale in the commit message.
- Slow-file diet, top 2 only: profile test_prime_eval + test_gate_receipt per-test; convert per-test git/tmpdir fixtures to setUpClass where isolation allows; stop at these two files.
- Full parallel suite green after all changes; serial spot-check on the two dieted files.

## Acceptance

- [ ] CLAUDE.md + template + usage.md carry the focused-vs-full convention
- [ ] Stale removals: each names its dead behavior; zero overlap with fn-111's fallout list (checked + noted)
- [ ] test_prime_eval + test_gate_receipt wall time halved or better, same test count, green
- [ ] Full parallel suite green; evidence records timings

## Done summary
fn-119.2: scoped verification convention + slow-file diet (+ stale sweep deferred to fn-111).

Docs: CLAUDE.md focused-vs-full Quick commands rule; .flow/templates/spec.md comment; .flow/usage.md Verification section; CHANGELOG Unreleased note.

Diet: test_prime_eval template copytree + SchemaShape setUpClass cache + substance-fast classify (skip axes git probes; stub docs-freshness except SubstanceDocsFreshnessTestCase). test_gate_receipt module template copytree + in-process cmd_gate_* (subprocess only for PATH shims) + batched gate-id validation + shorter TTL race sleep.

Stale sweep: cross-checked fn-111 fallout (test_migrate_rename, test_banner, test_lockfile, alias_smoke, test_read_compat, test_config_alias no-ops, set-deps/show-backend/scope-suggest, pre-1.0 migrate). Machinery still present; DEFERRED all known candidates to fn-111. Zero deletions (zero overlap).

Timings (same counts): prime 189 tests 109.6s -> 53.7s; gate 49 tests 52.3s -> 17.0s.
## Evidence
- Commits:
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_prime_eval -q  # 189 in 53.7s (was 109.6s), cd plugins/flow-next/tests && python3 -m unittest test_gate_receipt -q  # 49 in 17.0s (was 52.3s)
- PRs: