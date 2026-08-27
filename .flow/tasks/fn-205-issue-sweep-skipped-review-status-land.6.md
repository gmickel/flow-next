# fn-205-issue-sweep-skipped-review-status-land.6 Finalize the sweep: docs, conduct checklists, CHANGELOG entry, mirror regen, full gate

## Description
One finalization task for all four workstreams: the docs surfaces that enumerate the status members or the review roster, the conduct checklists that act as review criteria for the edited skills, the `## Unreleased` CHANGELOG entry crediting the four reporters, and the single authoritative mirror regen plus the full gate. Deliberately not split per artifact.

**Size:** M
**Files:** `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/ralph.md`, `plugins/flow-next/docs/architecture.md`, `plugins/flow-next/docs/teams.md`, `plugins/flow-next/docs/tracker-sync.md`, `plugins/flow-next/docs/platforms.md`, `agent_docs/conduct/work.md`, `agent_docs/conduct/land.md`, `agent_docs/conduct/spec-completion-review.md`, `agent_docs/conduct/pilot.md`, `CHANGELOG.md`, `plugins/flow-next/codex/**` (regenerated)
**Touches:** [plugins/flow-next/docs/**, agent_docs/conduct/**, CHANGELOG.md, scripts/sync-codex.sh, plugins/flow-next/codex/**]

### Approach
- Status-member surfaces: `docs/flowctl.md:243` (the `set-completion-review-status` value list) and `:796` (the `next` predicate sentence, currently `completion_review_status != ship`); `docs/ralph.md:362-368` (the gate box literally spelling `!= ship`); `docs/architecture.md:124,135,185,191` (field prose, write-ordering, setter list); `docs/teams.md:209` ("blocks spec-close until completion review returns SHIP" — there is now a documented excused path); `docs/tracker-sync.md:207` if it restates the projection row. Replace the stale predicate rather than appending exceptions (G1).
- Roster surface: confirm no docs page advertises `--review=export` for work; the published config schema and GLOSSARY already omit it, so no regeneration is expected there. If a config key was somehow introduced upstream in this spec, the schema table and its committed artifact move in the same change — but the spec puts that out of scope.
- Host-form surface: `docs/platforms.md:364` currently makes the reader do the colon-to-flat mapping. With closers emitting the right form, that line understates behavior — it is the canonical home for the statement.
- Conduct checklists are the review rubric for skill-prose changes: add items for the excused-member write (spec-completion-review), the fail-closed export rejection (work), the sidecar-commit invariant plus the #368 note if it landed (land), and — load-bearing, since R7 assigns pilot's prose-gate coverage HERE instead of to a banned prose pin — pilot: routing and advancement decide through the `{ship, not_required}` satisfying set, and unknown/unrecognized members satisfy nothing.
- CHANGELOG: there is no `## Unreleased` section today — create it above the newest release heading. Four user-visible fixes, written user-outcome-first with machinery last per `agent_docs/releasing.md`, each referencing its issue. Credit rule: thank @sn-furali on #371 and #367; #366 and #364 are maintainer-reported (@gmickel) — reference the issue, no thanks-credit (repo convention). Do NOT run `scripts/bump.sh` and do not touch version manifests — the release is batched separately.
- Routed from .5's host review (P2, in-scope here because this task owns the final sync + guard-green acceptance): the closer-roster guard in `scripts/sync-codex.sh` checks only ABSENCE of the colon-form literal — add the positive half: a third tab-separated roster column carrying the expected rewritten string, with `grep -qF` required to SUCCEED on it (a reword that breaks the sed anchor then fails the sync instead of staling the mirror at exit 0). Keep the forbidden-anchor check as the complement.
- Mirror + manifest: run `./scripts/sync-codex.sh` twice (idempotent, guards green) and commit the mirror diff; re-run `python3 scripts/gen_tracker_manifest.py` (or its `--check`) to confirm the manifest matches the shipped tracker members.
- Final gate, once, here: `python3 scripts/run_tests_parallel.py` (serial fallback `--serial`) plus `uvx ruff@0.16.0 check .`. The docs-only classifier tier does not license skipping it — this repo pins docs and conduct content in the unit suite.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/docs/flowctl.md:240-250` and `:790-800` — the member list and the `next` predicate
- `plugins/flow-next/docs/ralph.md:355-375` — the gate box with the stale comparison
- `CHANGELOG.md:1-12` — current head, to place a new `## Unreleased`
- `agent_docs/releasing.md` — changelog ordering rules and the hard rejection test

**Optional** (reference as needed):
- `plugins/flow-next/docs/platforms.md:360-370` — the OpenCode mapping sentence
- `agent_docs/conduct/README.md` — how checklist items are phrased

### Key context
- No version bump anywhere: stage under `## Unreleased` only (repo CLAUDE.md/AGENTS.md batched-release rule).
- The docs site at flow-next.dev is a separate repo; note what it needs, do not edit it from here.

### Acceptance
- [ ] Every docs page that enumerated the completion-review members or the `!= ship` predicate is accurate for the excused member, with stale predicates replaced rather than annotated
- [ ] `docs/platforms.md` states the OpenCode command-form behavior now that closers emit it
- [ ] Conduct checklists carry the new invariants for work, land, spec-completion-review, and pilot (satisfying-set routing/advancement — the R7 prose-gate coverage)
- [ ] `## Unreleased` exists with four user-outcome-first entries crediting reporters of #371, #367, #366, #364; no version bump, no `bump.sh`, no manifest version edits
- [ ] Roster guard extended with the positive expected-output column (routed .5 P2); a removed sed AND a broken anchor both fail the sync
- [ ] `./scripts/sync-codex.sh` run twice with identical results and guards green; mirror diff committed
- [ ] `python3 scripts/gen_tracker_manifest.py` reports no drift
- [ ] `python3 scripts/run_tests_parallel.py` green
- [ ] `uvx ruff@0.16.0 check .` clean

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
