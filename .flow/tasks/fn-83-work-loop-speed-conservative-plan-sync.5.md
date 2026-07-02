---
satisfies: [R4, R11, R12, R13]
---

## Description

Final gate: live-run evidence, the honesty statements in the PR, repo docs + docs-site edits, single mirror regen + commit, CHANGELOG. Depends on all prior tasks.

**Size:** M
**Files:** `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/architecture.md`, `agent_docs/optimizing-skills.md`, `agent_docs/optimization-log.md`, `GLOSSARY.md`, `CHANGELOG.md`, `plugins/flow-next/codex/` (single regen+commit), `~/work/flow-next.dev` (separate repo, same workstream)

## Approach

- **Live evidence (R11):** run a real multi-task `/flow-next:work` on this repo with gate `on` (a small maintenance spec or fixture spec); capture per-task `plan-sync:` slots + `.flow/plansync-gate.jsonl` excerpt; count worker anchor round-trips before (worker.md old read list) vs after (one call) — table into the PR body.
- **Honesty block in the PR (R4):** the rule-of-three bound with actual N; skip-rate on negatives; the deviation-only/plain-word residual stated verbatim with its mitigations (unsure⇒yes, 1-in-5 audit, append-only corpus).
- **Repo docs (R12):** flowctl.md — `plan-sync-probe` + `anchor` command sections (usage → JSON shape → exit/edge bullets, per the sync/prospect house style) + `planSync.gate` config-table row beside crossSpec (adoption note: cautious users set shadow first) + disambiguation note (plan-sync-probe ≠ /flow-next:sync); architecture.md — short paragraph on the fail-open lattice + zero-false-skip merge-gate discipline; optimizing-skills.md — pointers to both new harnesses beside the fn-74 real-backend section; GLOSSARY — light refresh of `Re-anchoring` + `Worker subagent` (single-call bundle, same information); optimization-log.md rows (gate corpus outcome, anchor eval outcome); CHANGELOG `## Unreleased` (create — top is released 2.6.1).
- **Docs-site (same workstream, separate commit in ~/work/flow-next.dev):** skills/work.mdx plan-sync section + mermaid `Sync` node (now probe-gated); flowctl/configuration.mdx new `planSync.gate` section (sibling/format of crossSpec section); subagents/execution.mdx + overview.mdx gate footnotes; `pnpm build` green; NO FLOW_NEXT_VERSION bump (batched).
- **Mirror:** idempotency verification re-run of `sync-codex.sh` (fn-83.4 already committed the regenerated mirror; this run must produce a no-op diff — any delta is a finding); drop any stray validation stashes.
- Full gates: smoke (non-repo cwd) + full pytest; no version bump.

## Investigation targets

**Required:**
- `plugins/flow-next/docs/flowctl.md:577-640` (config table) + `:749-800` (command-section style)
- `agent_docs/releasing.md` — batched-release + docs-site changelog conventions (entry only at release)
- `~/work/flow-next.dev/src/content/docs/flowctl/configuration.mdx:55-80` (crossSpec section = template)

## Acceptance

- [ ] Live-run evidence + round-trip table + honesty block staged for the PR body
- [ ] All repo docs updated per Approach; CHANGELOG Unreleased created; optimization-log rows present
- [ ] Docs-site edits committed in flow-next.dev with green `pnpm build`; no version refs bumped
- [ ] Mirror regenerated once (×2 idempotent, parity green) + committed; stashes dropped
- [ ] smoke + full pytest green; no version bump

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
