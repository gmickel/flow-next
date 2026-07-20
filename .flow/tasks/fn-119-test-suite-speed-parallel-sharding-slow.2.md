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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
