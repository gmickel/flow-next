---
satisfies: [R6, R7, R9]
---

## Description

Final gate: streamlined docs + CHANGELOG for the shipping surface (anchor bundle + CROSS_SPEC fix), the honest "skip-gate shelved" note pointing at the decision record, docs-site edits, mirror idempotency check. Depends on all prior tasks.

**Size:** M
**Files:** `plugins/flow-next/docs/flowctl.md`, `agent_docs/optimizing-skills.md`, `agent_docs/optimization-log.md`, `GLOSSARY.md`, `CHANGELOG.md`, `~/work/flow-next.dev` (separate repo, same workstream)

## Approach

- **Repo docs (R6):** flowctl.md — new `anchor` command section (usage → JSON shape → exit/edge bullets, per the `sync`/`prospect` house style). **No `plan-sync-probe` section, no `planSync.gate` config-table row** (both removed). GLOSSARY — light refresh of `Re-anchoring` + `Worker subagent` to reflect the single-call bundle (same information, one call). optimizing-skills.md — a pointer to `optimization/worker-anchor/` (comprehension-equivalence eval — a new proof shape worth a short callout beside the fn-74 real-backend section). optimization-log.md — two rows: anchor eval = PASS/shipped; plan-sync skip-gate = FAIL/shelved (link the decision record). CHANGELOG `## Unreleased` (create — top is released 2.6.1): entry ships `flowctl anchor` (worker anchors in one call, proven zero-loss) + the CROSS_SPEC caller fix; one sentence records the skip-gate as proven non-viable + shelved with the decision-record path — NOT sold as a feature.
- **Honest note (R8 PR half):** the PR body carries the anchor round-trip before/after table (worker.md old ~8 reads → one `flowctl anchor` call) and one paragraph: the skip-gate was proven non-viable on cross-repo evidence (1 false skip, 6.7% skip-rate) and shelved; pointer to `.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03.md`. Do not present any gate/audit/shadow mechanism as shipped.
- **Docs-site (R7, separate commit in ~/work/flow-next.dev):** plan-sync stays documented as UNCONDITIONAL (skills/work.mdx section + mermaid `Sync` node UNCHANGED); NO `planSync.gate` configuration.mdx section, NO gate footnotes. The only documentable change is the anchor round-trip win (mention in work.mdx if it fits naturally). `pnpm build` green; NO FLOW_NEXT_VERSION bump (batched).
- **Mirror (R9):** idempotency verification re-run of `sync-codex.sh` (fn-83.4 already committed the regenerated mirror; this run must be a no-op diff — any delta is a finding).
- Gates: smoke (non-repo cwd) + full unittest; no version bump.

## Investigation targets

**Required:**
- `plugins/flow-next/docs/flowctl.md` — `sync`/`prospect` command-section style + config table (confirm no planSync.gate row was ever added to the doc)
- `agent_docs/releasing.md` — batched-release + docs-site changelog conventions (entry only at release)
- `~/work/flow-next.dev/src/content/docs/skills/work.mdx` — plan-sync section (stays unconditional)

## Key context

This is a smaller PR than the original spec implied — the gate died, so there is no gate config/shadow/mermaid/footnote surface to document. Keep the docs honest and minimal: one new command, one bug fix, one shelved-experiment pointer.

## Acceptance

- [ ] flowctl.md `anchor` section added; zero `plan-sync-probe`/`planSync.gate` doc surface; GLOSSARY refreshed; optimizing-skills.md pointer; optimization-log.md rows (anchor PASS, gate FAIL/shelved)
- [ ] CHANGELOG `## Unreleased` created — anchor + CROSS_SPEC fix; skip-gate recorded as shelved w/ decision-record pointer; no version bump
- [ ] PR body: anchor round-trip table + honest shelved-gate paragraph
- [ ] docs-site: plan-sync stays unconditional (no gate surface); `pnpm build` green; no version refs bumped
- [ ] mirror sync-codex re-run is a no-op; smoke + full unittest green

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
