---
satisfies: [R13]
---

## Description

Extend `/flow-next:sync` (plan-sync) drift detection to catch glossary-term renames (term in old spec, new term in current code) and implicit decision overrides (current code violates a decision constraint), updating downstream task specs accordingly.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-sync/SKILL.md`, `plugins/flow-next/agents/plan-sync.md`, regenerate Codex mirror

## Approach

- **Sync skill (`flow-next-sync/SKILL.md:97-117`)** — extend Step 5 (Spawn Plan-Sync Agent) to pass two new context types to the agent:
  1. **Glossary state**: `flowctl glossary list --json` output (all defined terms, root + subdirs)
  2. **Decision constraints**: `flowctl memory list --track knowledge --category decisions --json` output (all active decisions with their `Consequences` sections)
- **Plan-sync agent (`agents/plan-sync.md:85-103`)** — extend drift-detection prose:
  - **Glossary-term renames**: when an old task spec or epic spec references a term, but the current code uses a different term (matching one of the old term's `_Avoid_` aliases), flag the spec for update. Update downstream task spec wording to use the canonical term.
  - **Decision overrides**: when current code touches files referenced in an active decision's `Consequences` section in a way that contradicts the decision (e.g. decision says "we use REST not GraphQL" + current code introduces a `/graphql` endpoint), flag the decision id in the sync report. Do NOT auto-supersede; surface for user review.
- Run `scripts/sync-codex.sh` to regenerate `plugins/flow-next/codex/agents/plan-sync.toml`.
- **R17 compliance**: no DDD jargon in skill or agent prose.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-sync/SKILL.md:97-117` — Step 5 (Spawn Plan-Sync Agent) extension point
- `plugins/flow-next/agents/plan-sync.md:85-103` — drift-detection phase prose
- `plugins/flow-next/codex/agents/plan-sync.toml` — Codex mirror (auto-regen)

## Acceptance

- [ ] Sync skill passes glossary-list and decisions-list context to plan-sync agent
- [ ] Plan-sync agent drift-detection detects glossary-term renames (term in old spec, alias in current code) and updates downstream specs
- [ ] Plan-sync agent surfaces decision-override candidates (current code touches files referenced in a decision's `Consequences`) WITHOUT auto-superseding — surface for user review only
- [ ] `scripts/sync-codex.sh` regenerates Codex mirror cleanly
- [ ] No DDD jargon in prose (R17)
- [ ] Manual smoke: run `/flow-next:sync` on a branch with a glossary-term rename in code; verify spec updates land. Run on a branch that violates a decision constraint; verify the decision id surfaces in the report.

## Done summary

## Evidence
