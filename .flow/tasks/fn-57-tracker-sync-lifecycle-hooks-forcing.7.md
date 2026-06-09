---
satisfies: [R11, R12]
---

## Description

Complete the glossary compounding loop: capture joins interview as a writer, and the read path widens to plan scouts, the work worker's re-anchor, and review prompts. Prompting only.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-capture/workflow.md` + `phases.md`, `plugins/flow-next/agents/` (repo-scout + context-scout definitions), `plugins/flow-next/skills/flow-next-work/phases.md` (worker prompt), review skill prompts (impl-review / plan-review — light touch)

## Approach

- **capture writes (R11):** capture already detects vocabulary conflicts (`## Glossary Conflicts` section). Add the offer-to-add path: during Phase 4 read-back, when the conversation surfaced genuinely NEW project vocabulary (term used repeatedly, absent from `glossary list`), include a "add N terms to GLOSSARY.md?" option — on approval, write via `flowctl glossary add` after the spec write (Phase 5). Same husk-aware autodetect gating as interview's doc-aware mode; in autofix mode, never write terms (print suggestions only).
- **read path (R12):** 
  - repo-scout / context-scout agent definitions: when `glossary list --json` has terms, match terms against the request text and include ONLY the matching entries (term + definition + aliases) in the research payload. Budget-capped — never the whole file.
  - work worker re-anchor (phases.md worker prompt ~3c): add task-relevant glossary terms to the re-anchor reads, same relevance matching.
  - review prompts (impl-review / plan-review): one line — "canonical vocabulary in GLOSSARY.md; flag implementations that contradict defined terms" — only when populated.
- NOTE: this task edits `capture/workflow.md` and `work/phases.md` AFTER tasks .3/.4 touched them (deps enforce order) — re-anchor on the post-.3/.4 file state before editing.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-capture/workflow.md` Phase 4-5 (read-back + write) + `phases.md` (biz-routing tables, where Glossary Conflicts is specified)
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:434-460` — behaviors (a)-(e), the term-add shape to mirror
- `plugins/flow-next/agents/` — repo-scout / context-scout definitions (find exact files; output-budget sections)
- `plugins/flow-next/skills/flow-next-work/phases.md` §3c — worker spawn prompt (post-.3 state)

**Optional:**
- `plugins/flow-next/skills/flow-next-impl-review/` + `flow-next-plan-review/` — where a one-line vocabulary nudge fits

## Acceptance

- [ ] capture offers consent-gated term-adds at read-back when new vocabulary surfaced; autofix prints suggestions, never writes
- [ ] repo-scout + context-scout include task-relevant glossary terms (matched, capped) in research payloads when the glossary is populated; silent when husk/absent
- [ ] worker re-anchor includes task-relevant terms; review prompts reference the glossary when populated
- [ ] Zero behavior change when no glossary exists (husk-aware gates everywhere)
- [ ] No whole-glossary dumps anywhere — relevance-matched terms only

## Done summary
_(to be filled at completion)_

## Evidence
_(to be filled at completion)_
