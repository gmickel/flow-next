---
satisfies: [R5, R7]
---
# fn-163-ceremony-fast-path-one-shot-spec.3 Teach fast path as default: docs, snippets, CHANGELOG, propagation

## Description
Teach the fast path as the default everywhere the granular ceremony is currently taught, update CLI reference docs, stage CHANGELOG + docs-site entries, and run the full propagation chain.

**Size:** M
**Files:** `plugins/flow-next/docs/flowctl.md` (spec create ~:184-203, task create ~:392-407, bulk JSON schema next to evidence-json schema), `plugins/flow-next/templates/usage.md:27-39`, `plugins/flow-next/agents/worker.md`, `plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md`, `claude-md-snippet-plugin.md`, `agents-md-snippet.md`, root `CLAUDE.md` Flow-Next block, `CHANGELOG.md`, codex mirror (regenerated), `.flow/bin/*` (propagated), `.flow/usage.md`

### Approach
- Rewrite the ceremony teaching: `spec create --title --plan-file` + `task create --from-json` (or full-field single calls) as THE default; granular verbs stay documented as the editing path. Keep snippets INSIDE the `test_token_budgets.py` budgets (tighten, don't append — replace the granular lines rather than adding to them).
- Document the bulk JSON schema in `docs/flowctl.md` adjacent to the evidence-json schema.
- Add repo `## Unreleased` CHANGELOG entry (header currently absent; no version bump — batched releases). Docs-site (`~/work/flow-next.dev`): update the live CLI-reference/usage pages for the new flags NOW, verify with the site's `pnpm build`. The site's CHANGELOG entry and all version fields (FLOW_NEXT_VERSION, package.json, versioned `### X.Y.Z`) are DEFERRED to the batched release — the site's changelog is versioned-only; do not invent an unreleased format.
- Downstream walk (same workstream, not deferred): follow `~/work/agent-instructions/downstream-properties.md` — assess docs-site, microsite, AIxSDLC guide, and vault; update what the feature makes stale; record per-property assess/update evidence in the done summary and PR body.
- Propagation (final gate): `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py`; rsync flowctl_tracker; `python3 scripts/gen_tracker_manifest.py`; `./scripts/sync-codex.sh` twice; commit mirror diff.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/templates/usage.md:27-39` — the granular sequence to replace
- `plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md` (+plugin/agents variants) — setup block lines ~7-17
- `plugins/flow-next/tests/test_token_budgets.py` — the budgets the rewrite must stay inside

**Optional**:
- `plugins/flow-next/agents/worker.md` — confirm where (if anywhere) it teaches create ceremony; workers mostly consume existing tasks
- `agent_docs/releasing.md` — changelog entry style (user-outcome-first)

### Key context
- fn-164 and fn-160 touch the same snippets/usage.md — second lander rebases against the other's landed text, not just main.
- sync-codex.sh validation guards must stay green; new Claude-only phrases may need a transform + guard.

### Acceptance
- [ ] usage.md, setup snippets (x3), worker.md (if it teaches ceremony), root CLAUDE.md block teach fast path as default; granular verbs still documented (R5)
- [ ] `test_token_budgets.py` green (R5)
- [ ] docs/flowctl.md documents --plan-file/--plan -, inline variants, --from-json + JSON schema
- [ ] Repo CHANGELOG `## Unreleased` entry, user-outcome-first; docs-site live reference pages updated + `pnpm build` green; site changelog/version fields untouched (deferred to batched release) (R7)
- [ ] Downstream walk executed with per-property assess/update evidence (docs-site, microsite, AIxSDLC guide, vault) (R7)
- [ ] Propagation complete: .flow/bin sync, tracker manifest, sync-codex.sh x2 idempotent; `test_tracker_distribution` green
## Acceptance
- All teaching surfaces default to the fast path with granular verbs still documented; token-budget tests pass (R5)
- CLI reference documents all new flags + bulk JSON schema
- Repo CHANGELOG Unreleased entry; docs-site live reference pages updated (build green), site changelog/version fields deferred to batched release; downstream walk evidence recorded (R7)
- Full propagation chain run; distribution and mirror guards green
## Done summary
Fast path taught as default everywhere the granular ceremony was taught: templates/usage.md Common Commands (spec create --plan-file + task create --from-json with example; granular verbs one editing line), the three setup snippets, root CLAUDE.md Flow-Next block, docs/flowctl.md (spec create one-shot flags + full --from-json schema with rejection semantics and ordered output, placed next to the evidence-json schema). Token budgets green (usage.md 2942/2950). Repo CHANGELOG Unreleased entry (user-outcome-first). Propagation complete: .flow/bin/flowctl.py + flowctl_tracker synced, tracker manifest regenerated, sync-codex.sh idempotent. Docs-site: cli-reference.mdx updated with fast-path commands + contract paragraph (host; commit follows spec landing). Downstream walk: docs-site UPDATED; microsite NO-CHANGE (no CLI-surface content); AIxSDLC guide NO-CHANGE (methodology level, revisit at release); vault NO-CHANGE (SlopCodeBench experiment note already captures the driver). Site changelog + version fields deferred to batched release. Implemented by grok-4.5 bridge; host wrote CHANGELOG/CLAUDE.md/docs-site and verified.
## Evidence
- Commits: 8dddf5e76fbef17a303694a257a92a6c8fb63077
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_token_budgets test_prompt_text_pinned -q
- PRs: