---
satisfies: [R5, R6, R7, R8, R9, R10]
---

## Description

Add doc-aware mode to `/flow-next:interview`: autodetect on `GLOSSARY.md` or `knowledge/decisions/` presence, `--docs` / `--no-docs` flags, four layered behaviors (glossary scan, fuzzy-term sharpening, code/spec contradiction surfacing, inline writes with three-criteria gate + read-back). Pure prose changes (no flowctl plumbing in this task).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-interview/SKILL.md`, `plugins/flow-next/skills/flow-next-interview/questions.md`, `plugins/flow-next/commands/flow-next/interview.md`, regenerate Codex mirror via `scripts/sync-codex.sh`

## Approach

- **Autodetect bash** in `SKILL.md` Setup section (after line ~58): check `[[ -f GLOSSARY.md ]]` AND `flowctl memory list --track knowledge --category decisions --json | jq '.entries | length > 0'`. Set `DOC_AWARE=1` if either fires.
- **Flag parsing** (pattern from `audit/SKILL.md:30-40` `mode:autofix` token): `--docs` forces `DOC_AWARE=1` (and lazy-creates root `GLOSSARY.md` on first term resolution); `--no-docs` forces `DOC_AWARE=0`.
- **Behavior (a) — Phase-zero glossary scan**: when `DOC_AWARE=1`, before drafting the first question batch, run `flowctl glossary list --json` and intersect terms with the user's request. For each defined term in the request, evaluate: is the term load-bearing for the spec's behavior? If yes AND user wording conflicts with canonical, surface as the first interview question via `AskUserQuestion`. **Throttle** (R7 + Constraints): casual passing mention → no question; behavior-defining mention → question.
- **Behavior (b) — Fuzzy-term sharpening**: when overloaded language emerges across the conversation, propose canonical via `AskUserQuestion` (lead-with-rec + confidence tier). On user-pick, build the resolved definition and call `flowctl glossary add <term> --definition-file -` (pipe stdin) before next question. The next question can re-read glossary; cache freshness handled by re-read on every glossary-aware turn (no in-memory cache).
- **Behavior (c) — Code/spec contradiction**: extend `## Investigate Codebase Before Asking` (SKILL.md:135-142). When grep reveals code disagrees with a user assertion, escalate from silent `## Resolved via Codebase` log to an `AskUserQuestion`. Body: "Code shows X (file:line); you said Y. Which?" Confidence: `[high]` when grep evidence is unambiguous.
- **Behavior (d) — Decision write**: when interview surfaces an architectural decision, evaluate three-criteria gate (hard-to-reverse + surprising-without-context + real-trade-off). If all three hold, draft entry (title + 1-3 sentence body + optional `Considered Options` + optional `Consequences`) and show via `AskUserQuestion` (capture/audit pattern). On `approve`, call `flowctl memory add --track knowledge --category decisions ...`. Never write silently.
- **questions.md (Pre-Question Taxonomy at lines 5-21)**: add glossary-lookup as a third axis. Codebase-answerable + glossary-lookup-answerable → resolved silently in `## Resolved via Codebase` (or `## Glossary Conflicts` for behavior-a hits). User-judgment-required → `AskUserQuestion`.
- **interview.md (slash command)**: document `--docs` / `--no-docs` flags in the args section.
- **R17 enforcement**: skill prose must NOT use "ubiquitous language", "bounded context", "domain expert", "aggregate root", or equivalent DDD vocabulary. T7 ships the automated grep guard; manual review on this task's first ship.
- **Run `scripts/sync-codex.sh`** after prose changes; validation block (`scripts/sync-codex.sh:760-770`) must pass: no `AskUserQuestion` literals leak into Codex mirror, no DDD jargon, all required `openai.yaml` files present.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:55-75` — Setup + Detect Input Type (autodetect insertion point)
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:135-142` — Investigate Codebase Before Asking (extension point for behavior c)
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:178-191` — `## Resolved via Codebase` convention
- `plugins/flow-next/skills/flow-next-interview/questions.md:5-21` — Pre-Question Taxonomy
- `plugins/flow-next/skills/flow-next-audit/SKILL.md:30-40` — `mode:autofix` token parsing template
- `plugins/flow-next/commands/flow-next/interview.md` — slash command entry
- `scripts/sync-codex.sh:485-491, 760-770` — rewrite + validation rules

**Optional:**
- `plugins/flow-next/skills/flow-next-capture/workflow.md` — read-back pattern reference for decision write

## Acceptance

- [ ] Interview autodetects doc-aware mode when `GLOSSARY.md` exists OR `.flow/memory/knowledge/decisions/` has any entry; off when neither (R5)
- [ ] `--docs` flag forces doc-aware on (lazy-creates root `GLOSSARY.md` on first term resolution); `--no-docs` forces off (R6)
- [ ] When user wording conflicts with canonical glossary term AND term is load-bearing for current spec, conflict surfaces as `AskUserQuestion` (R7); passing mention does NOT trigger
- [ ] When fuzzy term resolves, definition is written to nearest-ancestor `GLOSSARY.md` via `flowctl glossary add --definition-file -` before next question (R8)
- [ ] When grep reveals code-vs-assertion contradiction, surfaced as `AskUserQuestion` (not silently resolved) (R9)
- [ ] Decision entries write only when three-criteria gate passes; agent shows draft via `AskUserQuestion` before write (R10)
- [ ] questions.md Pre-Question Taxonomy gains glossary-lookup as a third axis
- [ ] interview.md documents `--docs` / `--no-docs` flags
- [ ] `scripts/sync-codex.sh` runs clean (no `AskUserQuestion` / `Task` literals in Codex mirror, no DDD jargon, no missing `openai.yaml`)
- [ ] Manual smoke: invoke `/flow-next:interview` in a project with sample `GLOSSARY.md` containing a known canonical term + conflicting user wording; verify behavior (a) question fires

## Done summary

## Evidence
