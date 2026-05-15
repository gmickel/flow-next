---
satisfies: [R16, R17]
---

## Description

Internal docs + release prep. `STRATEGY.md` "Our approach" gets a one-sentence anchor stating the single-evolving-spec commitment. `CLAUDE.md` "Creating a spec" embedded heredoc replaced with a pointer to `plugins/flow-next/templates/spec.md`. `CHANGELOG.md` gets `[flow-next 1.1.0]` entry. Ancillary docs that reference spec template structure inline (plan/steps.md, flowctl.md) updated to reference the canonical template path.

**Size:** M
**Files:**
- `STRATEGY.md` (Our approach paragraph; 1 sentence)
- `CLAUDE.md:114-147` (Creating-a-spec section: replace heredoc with template pointer)
- `CHANGELOG.md` (NEW [flow-next 1.1.0] entry)
- `plugins/flow-next/.claude-plugin/plugin.json` (version 1.0.2 → 1.1.0)
- `plugins/flow-next/.codex-plugin/plugin.json` (version 1.0.2 → 1.1.0)
- `.claude-plugin/marketplace.json` (plugins[] flow-next entry version + metadata.version → 1.1.0)
- `.agents/plugins/marketplace.json` (Codex marketplace — version field if present)
- `plugins/flow-next/skills/flow-next-plan/steps.md` (replace inline template refs with path link)
- `plugins/flow-next/docs/flowctl.md` (spec set-plan note: link to template)

## Approach

`STRATEGY.md` "Our approach" gets one-sentence anchor:

> Specs are single durable documents that evolve through layers — `.flow/specs/<id>.md` is the source of truth for goal, architecture, R-IDs, and acceptance, vs alternative split-file approaches (e.g., Kiro's `requirements.md` / `design.md` / `tasks.md`).

`CLAUDE.md:120-147` heredoc replaced with short pointer:

> Spec template: [`plugins/flow-next/templates/spec.md`](plugins/flow-next/templates/spec.md). See it for the canonical section list + scope-owner annotations.

Keep surrounding context (the "Two paths" framing, capture-recommended note).

`CHANGELOG.md` `[flow-next 1.1.0]` entry covers:
- `--scope=business|technical|both` flag for `/flow-next:interview` (default `technical`)
- New `questions-business.md` covering 9 business-context dimensions
- Canonical spec template at `plugins/flow-next/templates/spec.md`
- docs/teams.md + GLOSSARY.md naming fixes (handover #1 / #2 = one evolving spec, not two)
- Capture skill now routes business signals across nine destinations
- Backward-compat: zero-flag invocations of all commands unchanged (R22 invariant)

`plan/steps.md:294,318,490` inline spec template references replaced with template path links.

`flowctl.md` spec set-plan section gets one-line note: "See `plugins/flow-next/templates/spec.md` for the canonical section structure."

## Investigation targets

**Required:**
- `STRATEGY.md` "Our approach" section — find insertion point
- `CLAUDE.md:114-147` — Creating-a-spec heredoc
- `CHANGELOG.md` head — existing 1.0.2 entry as format precedent
- `plugins/flow-next/skills/flow-next-plan/steps.md:294,318,490` — inline template refs
- `plugins/flow-next/docs/flowctl.md:104-130` — spec set-plan documentation

## Acceptance

- [ ] `STRATEGY.md` "Our approach" includes one-sentence single-evolving-spec anchor
- [ ] `CLAUDE.md` "Creating a spec" heredoc replaced with template pointer; surrounding framing preserved
- [ ] `CHANGELOG.md` `[flow-next 1.1.0] - 2026-05-15` entry covers scope flag, biz question bank, template extraction, docs naming fixes, capture routing, R22 backward-compat
- [ ] `plan/steps.md` inline template refs replaced with template path links
- [ ] `flowctl.md` spec set-plan note links to `templates/spec.md`
- [ ] `plugins/flow-next/.claude-plugin/plugin.json` version bumped to 1.1.0
- [ ] `plugins/flow-next/.codex-plugin/plugin.json` version bumped to 1.1.0
- [ ] `.claude-plugin/marketplace.json` plugins[] flow-next entry + metadata.version both at 1.1.0
- [ ] `.agents/plugins/marketplace.json` version aligned to 1.1.0 if the file carries a version field
- [ ] Run `bash scripts/bump.sh minor flow-next` (or manual equivalent) — verify all FIVE manifest surfaces aligned at 1.1.0: `plugins/flow-next/.claude-plugin/plugin.json`, `plugins/flow-next/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `plugins/flow-next/README.md` badge

## Done summary
Bumped flow-next from 1.0.2 to 1.1.0 across all 5 manifest surfaces (plugin.json x2, marketplace.json plugins[] + metadata.version, README badges x2) via scripts/bump.sh. Anchored the single-evolving-spec choice in STRATEGY.md "Our approach", added CHANGELOG.md [flow-next 1.1.0] entry covering --scope flag / business question bank / template extraction / capture biz routing / R22 backward-compat / R26 project-docs, and rewired CLAUDE.md "Creating a spec" + plan/steps.md + docs/flowctl.md to point at the canonical templates/spec.md instead of inline-duplicating the section list. Added a sync-codex.sh sed rewrite so the regenerated Codex mirror gets the correct ../../../templates/spec.md relative path. Captured one bug-track memory entry documenting the three review-cycle patterns (scoped-diff false-positives, prose-form scaffold drift past the R21 guard, Codex mirror relative paths).
## Evidence
- Commits: b1672ab, a56b894, 4f5f347, 4024a77, 8bbd86e
- Tests: bash scripts/sync-codex.sh (passes all 12 validators incl. R21 spec-template duplication guard), bash plugins/flow-next/scripts/ci_test.sh (58 passed, 0 failed), codex impl-review SHIP after 3 NEEDS_WORK -> SHIP cycles (gpt-5.5:high)
- PRs: