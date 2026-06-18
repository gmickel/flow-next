# fn-66-tracker-sync-reserve-linear-done-for.4 Docs + CHANGELOG + version bump + Codex mirror + flow-next.dev

## Description
### Goal
Land the docs across both repos, the CHANGELOG + version bump, and regenerate the Codex mirror. Satisfies R9.

### Investigation targets
- `plugins/flow-next/docs/tracker-sync.md` — perEvent table (`:100-107`) + lifecycle sync points (`:96-125`): document `In Review` at make-pr and Done-only-on-merge. **`:131` currently states the OPPOSITE** ("does not auto-complete on merge — spec-completion-review owns the Done transition") — invert it: land.merged owns Done.
- `flow-next-tracker-sync/SKILL.md` + `flow-next-work/SKILL.md` (`:171`) — the completionReview "flip Done/verified" prose (also fixed in fn-66.2; ensure docs match).
- `flow-next-land/workflow.md:32` — state land.merged is the only Done path.
- Decision record `.flow/memory/knowledge/decisions/tracker-sync-is-projection-not-2026-06-01.md:37` (Consequences) — note fn-66 made `In Review` actively projected + Done gated on MERGED. (Committed decision record — edit the Consequences section only.)
- `CHANGELOG.md` — new entry (Fixed/Changed; status policy + pilot NO_WORK fix). Run `scripts/bump.sh <patch|minor> flow-next` (current 2.1.1; behavior fix → bump).
- Codex mirror: `bash scripts/sync-codex.sh` after all canonical edits (status-sync.md, steps.md, SKILL.md, phases.md, pilot+land workflow.md) + commit `plugins/flow-next/codex/`. Pre-audit canonical (mirror regen exposes latent gaps — memory `mirror-regen-exposes-latent-canonical`).
- flow-next.dev: `teams/tracker-sync.mdx:132` (invert the "spec-completion-review owns Done" sentence) + `autonomous/land.mdx:32` (Done-only-on-merge) + changelog + `src/lib/site.ts` FLOW_NEXT_VERSION + package.json; `pnpm build`; commit separately.

### Notes
Docs-last; depends on fn-66.1/.2/.3 settling so prose matches reality. GLOSSARY: only add "In Review" if the implementation hardcodes the literal string (low priority; it's a Linear state name).
## Acceptance
- [ ] tracker-sync.md (perEvent + lifecycle) updated incl. inverting the `:131` "spec-completion-review owns Done" claim → land.merged owns Done; In Review documented.
- [ ] tracker-sync + work SKILL prose + land workflow.md prose state Done-only-on-merge; decision-record Consequences note added.
- [ ] CHANGELOG entry + version bump via scripts/bump.sh across all manifests.
- [ ] Codex mirror regenerated + committed; `bash plugins/flow-next/tests/ci_test.sh` green.
- [ ] flow-next.dev tracker-sync.mdx + land.mdx corrected, changelog + FLOW_NEXT_VERSION + package.json bumped, `pnpm build` green, committed separately.
- [ ] `plugins/flow-next/docs/teams.md` Linear Diffs paragraph updated — "spec-completion-review owns Done" → "land/merged evidence owns Done".
- [ ] `references/github.md` + `adapter-interface.md` doc notes shipped (terminal-requires-merge-evidence).
## Done summary
fn-66.4 docs/release pass: audited that fn-66.1/.2/.3 fully inverted the tracker-sync.md/teams.md/status-sync.md "completion-review owns Done" prose to "land.merged owns Done" + In Review (no fix needed); added the decision-record Consequences note, the CHANGELOG 2.1.2 entry, and bumped flow-next 2.1.1→2.1.2 across all manifests + README + Codex/Cursor mirrors. RepoPrompt impl-review SHIP (2 rounds; the one NEEDS_WORK was a stale installed-copy artifact outside the repo/diff, not a real defect).
## Evidence
- Commits: 8decd4a6ba4df1752e014cc650972acaa64d39d6
- Tests: bash plugins/flow-next/scripts/ci_test.sh (67 passed), python3 -m unittest discover -s tests (1110 passed, 2 skipped)
- PRs: