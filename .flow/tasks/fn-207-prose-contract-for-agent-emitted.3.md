---
satisfies: [R6]
---
# fn-207-prose-contract-for-agent-emitted.3 sync-codex: extend docs-link transform + guard to agents/

## Description
Close the R6 gap: the docs-link namespacing transform and the hard-fail validation guard in scripts/sync-codex.sh scan only the skills surface, so a relative docs link in an agent file mirrors through unrewritten (pointing at a nonexistent mirror path) and no guard catches it. Extend both to the agents surface. Prerequisite for .4's agent-file pointers.

**Size:** S
**Files:** `scripts/sync-codex.sh`
**Touches:** [scripts/sync-codex.sh, plugins/flow-next/codex/**]

### Approach
- Extend the relative-docs-link namespacing transform (the block that rewrites `../docs/<file>.md`-shaped links into the mirror's `docs/flow-next/` namespace for skill files, ~L366-384) to also process the agent `.md` sources before TOML conversion (agents sit one level shallower than skill files: `../docs/x.md` from `agents/*.md`, so the rewrite depth differs from both skill-root and references files — derive it from the actual mirror layout, do not copy the skills sed blindly).
- Extend the validation guard ("bad relative docs links in codex skill prose", ~L2148-2160) to scan the mirrored agents surface (the generated `.toml` bodies or their `.md` intermediates — whichever the guard can reliably see) with the same hard-fail behavior.
- Guard extension only, never relaxation. Verify with a deliberate broken-link dry run locally (add a bogus `../docs/nope.md` to an agent file in a scratch tree or temporarily, confirm the guard fails, remove it) — do not commit the bogus link.
- Run `./scripts/sync-codex.sh` twice (idempotency) — with no agent docs-links existing yet the mirror diff should be empty or transform-neutral.

### Investigation targets
**Required** (read before editing):
- `scripts/sync-codex.sh:366-384` — the skills docs-link namespacing transform (pattern to extend)
- `scripts/sync-codex.sh:2148-2160` — the skills docs-link guard (pattern to extend)
- `scripts/sync-codex.sh:1808-1880` — the agents md→toml conversion (where agent bodies pass through; decide whether to rewrite before or after conversion)
- `plugins/flow-next/codex/docs/flow-next/` — the mirror docs layout the rewritten links must resolve against

**Optional:**
- `.flow/memory/bug/build-errors/codex-home-rewrite-both-spellings-2026-08-02.md` — transform-coverage prior art
- `.flow/memory/bug/integration/installer-must-own-what-it-deletes-2026-08-21.md` — consumer-layout validation lesson

### Key context
- Validate at the CONSUMER's layout (installed mirror), not the repo tree — the recurring lesson.
- No prompt-text pins on sync-codex.sh. Bash script change: ruff does not apply; the sync script's own validation guards + test_tracker_distribution-class tests are the check.

### Acceptance
- [ ] Transform rewrites relative docs links in agent sources into the mirror's docs namespace at the correct depth
- [ ] Guard scans the mirrored agents surface and hard-fails on a dangling docs link (verified with a deliberate local broken-link probe, not committed)
- [ ] `./scripts/sync-codex.sh` run twice: idempotent, all existing guards green
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned -q`

## Acceptance
- [ ] Transform rewrites relative docs links in agent sources into the mirror's docs namespace at the correct depth
- [ ] Guard scans the mirrored agents surface and hard-fails on a dangling docs link (verified with a deliberate local broken-link probe, not committed)
- [ ] `./scripts/sync-codex.sh` run twice: idempotent, all existing guards green
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned -q`

## Done summary
Extended sync-codex.sh docs-link machinery to the agents surface (R6): the agent md->toml conversion loop now rewrites `](../docs/` to `](../docs/flow-next/` in generated TOML bodies (agents' shallower depth vs the skills transform), and the fn-202 hard-fail docs-link guard scans codex/agents/ alongside codex/skills/ with unchanged failure semantics. Verified via deliberate broken-link probe (guard exit 1) and positive probe (valid link rewrites + resolves), both removed before commit; sync twice idempotent; full suite green. Script edits authored via the cursor-agent bridge (cursor-grok-4.6-high) per explicit routing instruction; diff verified line by line by the worker.

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
## Evidence
- Commits: 836177e3c3726257948c2a5984e93150cd9365b8
- Tests: baseline: green (./scripts/sync-codex.sh clean + test_prompt_text_pinned OK pre-edit), ./scripts/sync-codex.sh (twice, idempotent, all guards green), broken-link probe: bogus ../docs/nope.md in agents/build-scout.md -> sync exit 1, guard flags codex/agents/build-scout.toml (not committed), positive probe: ../docs/prose.md rewrites to ../docs/flow-next/prose.md and resolves (not committed), cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned -q, python3 scripts/run_tests_parallel.py (files=192 ran=4505 failures=0 errors=0)
- PRs:
stage: impl-review - ran (model: claude-fable-5, host backend, cross-family from grok-4.6 writer; SHIP round 1)
stage: plan-sync - skipped(config: planSync.enabled != true)
