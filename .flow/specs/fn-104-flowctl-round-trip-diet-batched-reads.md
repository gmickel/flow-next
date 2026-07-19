# fn-104 flowctl round-trip diet: batched reads and writes for hot skills

> STUB from the fn-101 audit (2026-07-19). Each skill Bash fence costs an agent round-trip plus ~0.4s flowctl startup; hot skills spend 10-20 per run. Interview/plan before building (flag design decisions below).

## Goal & Context

fn-101's round-trip census (full table in the fn-101 plan, section 4): land Phase 0 makes 7 sequential `config get` startups (land/workflow.md:53-72); plan scatters ~8 config/state reads across its run; pilot makes 3 config reads plus a Phase-4 snapshot that re-runs Phase 1's exact `show`/`tasks` reads (pilot/workflow.md:390-396 vs 142-149); plan pays 1+2N follow-up write calls per spec (set-branch after create, set-spec per task); every review round pays 1-2 follow-up status-write calls.

## Approach (four flowctl features + skill callsite updates)

1. Multi-key config read: `flowctl config get land --json` returns the whole `land.*` subtree (or `--keys a,b,c`). Update land/plan/pilot callsites.
2. Write-path flags: `spec create --branch <name>`; `task create --description-file/--acceptance-file` (or accept full task markdown on stdin). Update plan steps.md callsites.
3. Review handlers self-write status: `<backend> plan-review` sets `plan_review_status` from its own verdict; rp path folds `review-rounds increment/reset` into dispatch plumbing. Update plan-review/impl-review callsites (workflow.md:87-92, 453-458).
4. Skill-prose fence consolidation (no flowctl change): make-pr delete the validation-only `show >/dev/null` (workflow.md:131-135) and collapse Phase 0's 8 read fences to 2-3; pilot single select/classify bundle call for its tick reads (anchor-pattern precedent) killing the Phase-4 re-reads and per-dep show loops; plan-review deduplicate the per-backend block that exists verbatim in both SKILL.md and workflow.md (3 backends x 2 copies); impl-review merge its 3 arg-parse fences into 1; pilot deduplicate hard guards (SKILL.md:51-63 = workflow.md:27-46).

## Acceptance

- land Phase 0 config reads: 7 flowctl startups -> 1.
- plan happy path (4 tasks): flowctl invocations reduced by >= 40% (count before/after in a scripted dry run).
- pilot ADVANCED tick: no repeated `show` of the same id within one tick.
- sync-codex.sh run twice, mirror committed; smoke tests green.

## Boundaries

- Worker/work-skill handover fences are OUT (parallel workstream owns them).
- Keep single-emission discipline (fn-81) - no new post-write re-fetches.
- New flags must degrade gracefully on older .flow/bin copies (probe or version-gate per existing patterns).
