---
satisfies: [R8]
---
# fn-195-orchestration-by-intent-named-tiers-per.5 Docs sweep, dictionary, CHANGELOG, and the full gate

## Description
Close out: the big-picture docs sweep across every page the change touches, the dictionary terms, the major-release CHANGELOG entry, mirror regeneration, and the full gate.

**Size:** M
**Files:** `plugins/flow-next/docs/README.md` (notable updates + index rows), `platforms.md`, `orchestration.md`, `teams.md`, `troubleshooting.md`, `glossary.md`, `plugins/flow-next/README.md`, root `CLAUDE.md` where it describes routing, `CHANGELOG.md`
**Touches:** [plugins/flow-next/docs/README.md, plugins/flow-next/docs/platforms.md, plugins/flow-next/docs/teams.md, plugins/flow-next/docs/troubleshooting.md, plugins/flow-next/templates/usage.md, .flow/usage.md, .flow/bin/**, plugins/flow-next/README.md, CLAUDE.md, CHANGELOG.md]

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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
