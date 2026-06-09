---
satisfies: [R10]
---

## Description

Add a glossary-bootstrap step to `/flow-next:prime`: when GLOSSARY.md is absent or a husk, scan the repo for the load-bearing nouns/flows/distinctions, propose terms with file-ref evidence, read-back, and seed via `flowctl glossary add`. Prompting only — zero new flowctl.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-prime/` (SKILL.md + workflow files)

## Approach

- Gate on husk-aware detection: `flowctl glossary list --json` → `total_terms == 0` (NOT `[[ -f GLOSSARY.md ]]` — `glossary remove` leaves an H1 husk; same R18 invariant interview uses at `flow-next-interview/SKILL.md:170-193`).
- Bootstrap flow: host agent scans the repo (README, docs, module names, domain nouns recurring across specs/code) → proposes ~10-20 candidate terms, each with a one-line definition + file-ref evidence + `_Avoid_` aliases where naming drift is visible → **read-back before any write** (consent-gated; mirror capture's read-back discipline) → writes accepted terms via `flowctl glossary add` (format: H2-per-term, see `docs/glossary.md`).
- On a POPULATED glossary: report term-coverage as a readiness signal (e.g. "GLOSSARY.md: 12 terms, N referenced in code") — never rewrite, never re-propose existing terms. Pruning belongs to audit, not prime.
- Respect prime's existing report structure — bootstrap is one new pillar/step in the readiness scan, not a separate mode. Follow prime's existing fix-vs-report split (prime fixes agent-readiness items; glossary seeding IS an agent-readiness fix).
- Cross-platform: canonical Claude tool names; AskUserQuestion for the read-back (sync-codex.sh rewrites for the mirror).

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-prime/SKILL.md` — current pillar/step structure + where the bootstrap slots in
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:160-193` — husk-aware autodetect to mirror
- `docs/glossary.md` (plugins/flow-next/docs/) — term format, `_Avoid_`/`_Relates to_` conventions, ancestor resolution
- `GLOSSARY.md` (repo root) — exemplar of the target output quality

**Optional:**
- `plugins/flow-next/skills/flow-next-audit/workflow.md` (glossary scan §0.5) — what pruning already covers, to avoid overlap

## Acceptance

- [ ] Prime on a glossary-less (or husk) repo proposes evidence-backed terms and writes them only after read-back approval, via `flowctl glossary add`
- [ ] Prime on a populated glossary reports coverage and changes nothing
- [ ] Gating uses `total_terms == 0`, never file presence
- [ ] No new flowctl code; no new skill; bootstrap is a step inside prime
- [ ] Codex-mirror-compatible (canonical tool names; no new sync-codex special cases needed)

## Done summary
_(to be filled at completion)_

## Evidence
_(to be filled at completion)_
