---
satisfies: [R8]
---
# fn-195-orchestration-by-intent-named-tiers-per.5 Docs sweep, dictionary, CHANGELOG, and the full gate

## Description
Close out: the big-picture docs sweep across every page the change touches, the dictionary terms, the major-release CHANGELOG entry, mirror regeneration, and the full gate.

**Size:** M
**Files:** `plugins/flow-next/docs/README.md` (notable updates + index rows), `platforms.md`, `orchestration.md`, `teams.md`, `troubleshooting.md`, `glossary.md`, `plugins/flow-next/README.md`, root `CLAUDE.md` where it describes routing, `CHANGELOG.md`
**Touches:** [plugins/flow-next/skills/flow-next-work/phases.md, plugins/flow-next/skills/flow-next-pilot/workflow.md, plugins/flow-next/docs/README.md, plugins/flow-next/docs/platforms.md, plugins/flow-next/docs/teams.md, plugins/flow-next/docs/troubleshooting.md, plugins/flow-next/templates/usage.md, .flow/usage.md, .flow/bin/**, plugins/flow-next/README.md, CLAUDE.md, CHANGELOG.md]

### Approach
- Sweep by asking which other pages the change touches, not just the obvious ones: the platform pages carried per-host tier tables, teams carried routing advice, troubleshooting carried pin failures, and the notable-updates list needs one line.
- The CHANGELOG entry ships in the same major release as the delegation removal and reads as one story: routing became a preference you write instead of a subsystem you configure. Name the removed keys, the replacement, and the one-line migration. No benchmark tables, no speed claims, no model identifiers beyond the declared exceptions.
- Mirror regenerated twice for idempotency; verify the generator's transforms actually fired on the changed files rather than assuming.
- **Dogfood propagation is already done — `.3` completed it** (`.flow/bin/flowctl.py` copy, `flowctl_tracker` rsync, `gen_tracker_manifest.py`), because `.flow/bin/flowctl.py` was already in `.3`'s Touches and `test_tracker_distribution` would otherwise have gone red there. This task's only remaining propagation step is `sync-codex.sh` run twice — do not redo the dogfood copy from scratch; `.flow/bin/**` in this task's Touches is verification (confirm it's still current after the docs sweep), not first-time propagation. <!-- Updated by plan-sync: fn-195-orchestration-by-intent-named-tiers-per.3 completed dogfood propagation; only mirror regen was deferred -->
- `templates/usage.md` + `.flow/usage.md` (byte-identical pair per `test_cursor_host_docs`) and the root `CLAUDE.md` model table were explicitly left untouched by `.3` and still carry bridge-recipe slugs (`grok-4.6`, `gpt-5.6-terra`, cursor slugs) — this task owns de-slugging both, keeping the usage.md pair byte-identical after the edit. <!-- Updated by plan-sync: fn-195-orchestration-by-intent-named-tiers-per.3 deferred templates/usage.md, .flow/usage.md and root CLAUDE.md to this task -->
- Full gate: the parallel suite with the exit code captured directly, plus the pinned linter. Docs trees here are test-pinned and the local classifier calls them docs-only, so the full suite runs regardless of tier.
- **Codex mirror content-pin gap (flagged during .2/.3):** `test_model_routing_scaffold.py`'s canonical assertions (`WorkflowProseContract`, `TemplateShape`) run against the canonical `plugins/flow-next/skills/flow-next-setup/workflow.md` and its template only — nothing re-pins the equivalent *mirror* content at `plugins/flow-next/codex/**` after `sync-codex.sh` regenerates it (deliberately dropped: the mirror is a generated rewrite, and `sync-codex.sh`'s own validation guards police the transform, not the prose). After the mirror regen in this task, either (a) add a mirror-side content pin equivalent to the canonical `WorkflowProseContract`/`TemplateShape` checks (routing-block markers, no model slug, pin-ceremony vocabulary absent) scoped to the Codex-rewritten paths, or (b) explicitly record the accepted gap - which surface asserts the mirror stayed in sync with the routing prose, and why a content pin was decided against - in this task's Done summary and in the docs sweep. Silence is not an acceptable outcome for this item. <!-- Updated by plan-sync: fn-195-orchestration-by-intent-named-tiers-per.2 flagged that mirror-content pins were deliberately dropped and no downstream task re-added or recorded the gap -->

### Investigation targets
**Required** (read before writing):
- `agent_docs/releasing.md` - the changelog register and what a major requires
- `plugins/flow-next/docs/README.md` notable-updates format

- **Emitter for the R7 stage-line model annotation (from .4's review):** the parser for a trailing `(model: <what ran>)` on stage-outcome lines landed in .4 with zero producers. Teach the two stage-line grammar sites — `skills/flow-next-work/phases.md` (stage-outcome block) and `skills/flow-next-pilot/workflow.md` — to append the annotation when the orchestrator knows what ran (record-only, absent means unknown). Without this, R7's non-review half ships permanently dead.

### Acceptance
- [ ] Every page the change touches is updated, not only the routing page; notable-updates line added
- [ ] Four tier terms present in the dictionary with synonym bans (already added by `.1` - verify they survived `.3`'s sweep rather than re-adding) <!-- Updated by plan-sync: fn-195-orchestration-by-intent-named-tiers-per.1 already added Tier/Reach + the four tier terms to the dictionary; this task verifies, does not author -->
- [ ] `## Unreleased` CHANGELOG entry framed for the major release, one story with the delegation removal, migration line included; no version bump
- [ ] Mirror regenerated twice with transforms verified on the changed files
- [ ] Mirror routing-prose content is either re-pinned by a new test or the accepted gap is explicitly recorded (Done summary + docs sweep) — not silently left unpinned
- [ ] Full suite + linter green with exit codes captured directly; OS matrix green in CI

## Acceptance
- [ ] TBD

## Done summary
Closed out fn-195: swept every page the routing change touches (docs README index + reach row + notable-updates line, platforms.md, teams.md, troubleshooting.md, sync-codex.md, review-findings.md, root README, root CLAUDE.md, the byte-identical usage.md pair), taught the two stage-line grammar sites to emit the R7 `(model: <what ran>)` annotation, closed the mirror content-pin gap with a real test, and staged the major-release CHANGELOG entry under `## Unreleased` with no version bump.

Decisions and evidence for review:

- **Mirror content-pin gap: closed with option (a), not recorded as accepted.** `MirrorRoutingProse` in `plugins/flow-next/tests/test_model_routing_scaffold.py` pins the regenerated mirror's routing block (markers, four tier names, zero model identifier) and asserts the retired ceremony references (`references/model-*.md`) are actually gone from the mirror — an incomplete regen leaves them loadable while the canonical assertions stay green. Recorded in the docs sweep too: `docs/sync-codex.md` now states that the sync guards police the transform, not the prose, and names the test as where mirrored user-facing contracts get pinned.
- **`test_cursor_host_docs` was asserting the opposite of R2** — it required a concrete Cursor slug in `usage.md`. Inverted: it now asserts no shipped identifier plus a `<model>` placeholder. This was pinning the machinery the spec deletes, not catching drift.
- **Root `CLAUDE.md` routing block rewritten into the shipped shape** (tier lines + precedence + preferences prose). Removed: the model ranking/score table, the probe-marked "live only if installed" lines, role-pin/registry-rung vocabulary, and benchmark claims. The concrete model names stay — this file is the consumer's own instruction file, which is exactly where the spec says identifiers belong.
- **R2 residue is only the declared exceptions.** Final scan over shipped prose (plugin tree, excluding the mirror and tests) returns review-backend grammar surfaces only (`codex:<model>:<effort>`, `cursor:<model>-<effort>`, ralph-init prompt templates showing spec form) — the exception .3 declared and the conductor said not to re-litigate. `orchestration.md`, the other declared exception, currently names no identifier at all.
- **Glossary verified, not re-authored:** 18 terms, including Tier, Reach, and the four tier terms with their `avoid` lists — all survived .3's sweep.
- **Mirror regen:** `./scripts/sync-codex.sh` run three times total (twice consecutively with an identical 63-file working tree, then once more after the `sync-codex.md` edit) — idempotent, exit 0 each time, and the transforms verified as fired on the changed files (mirror `usage.md`, `phases.md`, `pilot/workflow.md`, routing snippet) rather than assumed. The regen also deleted seven stale `flow-next-setup/references/model-*.md` mirror files left over from the deleted ceremony.
- **Version:** no bump, no `bump.sh`, no manifest touch — CHANGELOG lands under `## Unreleased` for the 4.0.0 batch with flow-98. The docs-site changelog is a release-time downstream step, not done here.
- **Baseline:** green (full suite exit 0 before any edit).

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
stage: delegation - skipped(config: delegation off)


Review fixes c327e766 (mirror floors restored via corrected generator baselines + MirrorAgentFloors pin; terra sentence; reviewer-tier rejection hints; MODEL_SLUG_RE cursor scan; shared gone-list) + bf3003dd (test-hygiene nits).

stage: impl-review - ran (host backend, fresh fable-5 reviewers; r1 NEEDS_WORK (P1 mirror floors) -> fixes -> r2 SHIP)
stage: plan-sync - skipped(empty: no downstream todo tasks)
## Evidence
- Commits: e2517bdc2ef8d1658302378b269d3ebdd96a545f, c327e766885a62c8084e5a6f6163bcedddcdb5f9, bf3003dd
- Tests: python3 scripts/run_tests_parallel.py (files=192 ran=4396 failures=0 errors=0 skipped=8, exit 0), uvx ruff@0.16.0 check . (All checks passed), cd plugins/flow-next/tests && python3 -m unittest test_model_routing_scaffold test_cursor_host_docs -q (33 tests, OK), ./scripts/sync-codex.sh x2 (idempotent, exit 0), post-fix full gate: python3 scripts/run_tests_parallel.py (192 files, 4397 tests, 0F 0E; receipt c327e766-unittest) + ruff clean; sync-codex.sh idempotent across consecutive runs, impl-review: host backend r1 NEEDS_WORK (P1 mirror agent floors + 4 lower), r2 SHIP (reviewer claude-fable-5, fresh subagents; receipt /tmp/impl-review-receipt-fn-195-orchestration-by-intent-named-tiers-per.5.json)
- PRs: