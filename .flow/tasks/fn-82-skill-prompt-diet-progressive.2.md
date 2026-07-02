---
satisfies: [R5, R6]
---

## Description

Class-1 archaeology: strip dev-time scaffolding from tracker-sync (always-loaded files + adapter refs), qa, map, and memory-migrate. Pure deletion/rewording of dead text — no behavior. CANONICAL FILES ONLY. (audit + prospect archaeology ride with fn-82.3 to avoid file overlap.)

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-tracker-sync/{SKILL.md,steps.md,references/linear-ladder.md,references/github.md,references/gitlab.md}`, `agent_docs/tracker-sync-spikes.md` (new dev archive), `plugins/flow-next/skills/flow-next-qa/{SKILL.md,workflow.md}`, `plugins/flow-next/skills/flow-next-map/SKILL.md`, `plugins/flow-next/skills/flow-next-memory-migrate/{SKILL.md,workflow.md,phases.md}`

## Approach

- **Strip/keep allowlist (spec §Approach — binding):** strip `fn-N`/`fn-N.M` provenance parentheticals where prose carries the rule; a rule whose ONLY carrier is the fn-tag gets the rule rewritten into prose first (e.g. "(fn-66)" → "a real merge is the sole Done driver"). KEEP: `R\d+` ids, `S-[A-Z]` status-sync fixtures, version numbers. Work through tracker-sync SKILL.md + steps.md (~93 occurrences; `grep -n 'fn-[0-9]'` first, classify each).
- Spike harnesses: linear-ladder.md:191-269, github.md:546-642, gitlab.md:862-931 → `agent_docs/tracker-sync-spikes.md` (dev archive outside the plugin tree — never shipped/mirrored; jira.md has none). Breadcrumb where each was: "Round-trip spike: dev archive at agent_docs/tracker-sync-spikes.md — not runtime material."
- qa: delete ownership table workflow.md:9-15, OWNER comments (:268,:332,:374,:441,:583), skeleton/proof-point prose (:335-348), SKILL.md:126 task framing; remove the transient proof-receipt write (workflow.md:352) — §6.3 qa_verdict is the single receipt now (verify nothing reads proof-receipt.json: grep repo).
- map SKILL.md:12,:80 → present tense; memory-migrate phases.md:3 line numbers → names, "Task 2" prose (SKILL.md:14,:82, workflow.md:35) → present tense.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-tracker-sync/SKILL.md` + `steps.md` (full read — classify every fn-tag)
- `plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md` — the S-fixtures + R-ID rules to NOT touch
- `plugins/flow-next/skills/flow-next-qa/workflow.md:1-60,260-360,430-450,570-600`

## Key context

Adapter-ref strips are dead-text cleanup (on-demand files), the SKILL+steps strips are the always-loaded win (~1-2k). Do not reword live rules — deletion/prose-substitution only per the allowlist.

## Acceptance

- [ ] `grep -c 'fn-[0-9]' SKILL.md steps.md` reduced to allowlisted survivors only (list each survivor + reason in summary)
- [ ] Spike harnesses out of runtime refs, consolidated with breadcrumbs; status-sync oracles byte-untouched
- [ ] qa scaffolding + proof-receipt gone; nothing references proof-receipt.json
- [ ] map/memory-migrate present-tense; zero flowctl.py line-number refs in touched files
- [ ] Canonical-only diff; smoke green locally

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
