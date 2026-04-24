# /flow-next:prospect — upstream-of-plan idea generation with ranked candidates

## Overview

New user-triggered skill that fills the "what should I build?" gap above `/flow-next:interview` and `/flow-next:plan`. Given a codebase and an optional focus hint, `prospect` generates many candidate ideas grounded in the repo, critiques every one with explicit rejection reasons, and surfaces only the survivors. Output is a ranked artifact under `.flow/prospects/<slug>-<date>.md` that feeds directly into `interview` or `plan` via a promote command.

Current flow-next upstream-of-work pipeline assumes a formed target: `interview` refines a known spec/epic, `plan` breaks a known spec into tasks. Neither handles the phase where the user is asking the system to propose directions. `prospect` closes that gap without forcing users to pre-invent candidates.

## Constraints (CRITICAL)

- Zero-dep: bash + Python stdlib + flowctl only. No new runtime deps.
- Cross-backend: works on Claude Code, Codex, Copilot, Droid. The interactive single-question loop uses each platform's blocking tool (`AskUserQuestion` / `request_user_input` / etc.); numbered-options fallback when no blocking tool available.
- Ralph-out: autonomous loops must not decide "what to build next". `/flow-next:prospect` hard-errors with exit 2 when `REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1` is set, same pattern as `--interactive` in impl-review.
- Artifact-first: output is a markdown file under `.flow/prospects/`, not chat prose that vanishes. Resumable, queryable, promotable.
- Additive to existing lifecycle: does not replace `interview` or `plan`. Users with clear targets skip `prospect` and go straight to interview/plan as today.

## Approach

### Skill: `/flow-next:prospect [focus hint]`

Single skill invocation per ideation session. The optional argument is a freeform focus hint that scopes the ideation:

- **Concept:** `DX improvements`, `review-skill polish`, `test-suite health`
- **Path:** `plugins/flow-next/skills/` (ideate inside a subtree)
- **Constraint:** `quick wins under 200 LOC`, `minor-bump only`, `no new deps`
- **Volume hint:** `top 3`, `50 ideas`, `raise the bar`

If no hint, ideation is open-ended — the skill picks its own coverage targets from repo structure.

### Phase order

1. **Phase 0 — Resume check.** If `.flow/prospects/*.md` contains an artifact <30 days old, list them and ask whether to extend or start fresh. Prevents short-horizon churn where users re-generate the same ideas weekly.
2. **Phase 1 — Ground.** Scan the repo:
   - Recently-modified files (git log, last 30 days).
   - Open `.flow/epics/*.json` with `status: open` (what's already being thought about).
   - `.flow/memory/knowledge/*/` entries tagged with the focus hint (if any).
   - `CHANGELOG.md` top N entries (what shipped recently — don't re-propose those).
3. **Phase 2 — Generate.** Produce a candidate list. Volume default: 15-25 ideas if no hint; respect `top N` / `N ideas` hints when given. Each candidate has: `title`, `one-line summary`, `affected area(s)`, `estimated scope (XS/S/M/L/XL)`, `risk notes`.
4. **Phase 3 — Critique every candidate.** For each idea: explicit "why not" assessment against one or more of: duplicates existing open epic, out-of-scope for repo, insufficient signal, too large without decomposition, prevents backward compatibility. Rejected candidates get a one-line reason and are dropped from the final report.
5. **Phase 4 — Rank survivors.** Survivors only are ranked by: leverage (small-diff, large-impact wins top), fit-with-open-epics, solo-doable. No quantitative score — prose reasoning wins over numbers here.
6. **Phase 5 — Write artifact.** Emit `.flow/prospects/<slug>-<date>.md` with YAML frontmatter (`title`, `date`, `focus_hint`, `volume`, `survivor_count`, `rejected_count`, `artifact_id`) plus body sections:
   - `## Focus`
   - `## Grounding snapshot` (what the skill scanned)
   - `## Survivors` (ranked; each with title, summary, leverage reasoning, suggested size, suggested next step)
   - `## Rejected` (one line per rejected candidate with a reason)
7. **Phase 6 — Offer handoff.** After writing, prompt: "Promote one of the survivors to an epic now? (idea number / skip / interview instead)". Route the user to `flowctl prospect promote <artifact_id> --idea <N>` or `/flow-next:interview`.

### Promote command

New flowctl subcommand `flowctl prospect promote`:

```bash
flowctl prospect promote <artifact-id> --idea <N> [--epic-title "..."] [--json]
```

- Reads the artifact, extracts survivor #N's title/summary/reasoning.
- Creates a new epic with the extracted title (or `--epic-title` override).
- Pre-fills the epic spec skeleton with: original idea summary, leverage reasoning, suggested size, a `## Source` section linking back to the prospect artifact (`source: .flow/prospects/<artifact-id>.md#idea-N`).
- Returns the new epic ID; user then runs `/flow-next:interview <epic-id>` or `/flow-next:plan <epic-id>` to refine.

### Additional flowctl subcommands

- `flowctl prospect list [--json]` — list prospect artifacts with survivor/rejected counts and date.
- `flowctl prospect read <artifact-id>` — print the artifact body (parallels `flowctl memory read`).
- `flowctl prospect archive <artifact-id>` — move to `.flow/prospects/_archive/` (keeps history, removes from default listings).

## Artifact schema

```yaml
---
title: "DX improvements for flow-next"
date: 2026-04-24
focus_hint: "DX improvements"
volume: 22
survivor_count: 6
rejected_count: 16
artifact_id: dx-improvements-2026-04-24
---

## Focus
<focus_hint expanded>

## Grounding snapshot
- Scanned: 34 recently-modified files across plugins/flow-next/
- Open epics: fn-14, fn-18, fn-21 (considered for overlap)
- Recent ship: fn-29/30/31/32 (0.32.1 → 0.35.1)

## Survivors

### 1. <title>
**Summary:** <one line>
**Leverage:** <why this has big impact for small effort>
**Suggested size:** S
**Next step:** /flow-next:interview or /flow-next:plan

### 2. ...

## Rejected

- <title> — <one-line reason (duplicates fn-X / out of scope / too large / low signal / backward-incompatible)>
- ...
```

## Acceptance criteria

- **R1:** `/flow-next:prospect [hint]` scans repo (recent files + open epics + recent CHANGELOG + memory) before generating candidates; "Grounding snapshot" section lists exactly what was scanned.
- **R2:** Volume default 15-25 when no hint; `top N` / `N ideas` hints respected; `raise the bar` biases toward fewer, higher-leverage survivors.
- **R3:** Every candidate gets an explicit critique; rejected candidates surface only in "Rejected" section with a one-line reason; survivors only get prose in "Survivors".
- **R4:** Artifact writes to `.flow/prospects/<slug>-<date>.md` with YAML frontmatter matching the schema (title, date, focus_hint, volume, survivor_count, rejected_count, artifact_id).
- **R5:** Resume check on Phase 0 — artifacts <30 days old list and ask whether to extend or start fresh; extending appends a new section to the existing artifact with a dated header.
- **R6:** `flowctl prospect promote <id> --idea <N>` creates an epic with pre-filled skeleton (title, summary, leverage reasoning, `## Source` link) and returns the new epic ID via stdout / `--json`.
- **R7:** `flowctl prospect list / read / archive` implemented with `--json` support.
- **R8:** Ralph-blocked: `/flow-next:prospect` exits 2 when `REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1` is set. No env-var opt-in (no `FLOW_PROSPECT_*` variable).
- **R9:** Handoff prompt at end of Phase 6 offers promote / interview / skip; numbered-option fallback when no blocking question tool available.
- **R10:** Smoke test covers: generate-with-hint, generate-no-hint, resume of <30-day artifact, promote-to-epic, list/read/archive, Ralph-block exit 2.
- **R11:** Docs updated: CHANGELOG entry, plugins/flow-next/README.md (new "Prospecting" section before Planning), CLAUDE.md command list entry.

## Testing strategy

- Unit: YAML frontmatter round-trip, grounding-snapshot collector, rejection-critique parser (survivor-vs-rejected split), promote command skeleton generation.
- Smoke (synthetic repo): full end-to-end — generate artifact, list, read, promote to epic, verify epic pre-filled with `## Source` link. Second run reuses resume path.
- Ralph regression: `/flow-next:prospect` invoked with `FLOW_RALPH=1` must exit 2 without writing any artifact.

## Boundaries

- Not replacing `interview` or `plan`. Prospect is only for the "I don't know yet" phase.
- Not a multi-persona parallel dispatch. Single-chat, sequential: generate → critique → rank → write.
- Not inventing a ranking algorithm. Prose reasoning wins over quantitative scores.
- Not committing the artifact. Artifacts are under `.flow/prospects/`, which (like `.flow/epics` and `.flow/tasks`) users decide whether to commit. Default `.gitignore` behaviour: up to the user's project conventions.

## Decision context

**Why "prospect" and not "ideate"?** "Ideate" is too generic and common across plugins; "prospect" reads as engineering-adjacent (prospecting for leads / opportunities) and matches flow-next's action-verb vocabulary (plan, work, interview, resolve-pr, prime).

**Why artifact-first, not chat-first?** Chat prose vanishes. Artifacts are resumable (Phase 0), queryable (list / read), promotable (promote → epic). The whole point of adding this skill is to stop half-formed ideas evaporating between sessions.

**Why generate-many-critique-all rather than rank directly?** Explicit rejection forces sharper selection than optimistic ranking. A reviewer who has to say "this one is not worth keeping, because X" produces survivors with real leverage; a reviewer who just sorts 10 candidates gives you the best-looking 10, not the best 3.

**Why no Ralph opt-in?** Prospect is exploratory. An autonomous loop has no business deciding what a repo should tackle next; that's a human-in-the-loop judgement call.

## Risks

| Risk | Mitigation |
|---|---|
| Artifact sprawl (users run prospect weekly, accumulate stale artifacts) | Resume check in Phase 0 extends recent artifacts instead of creating new ones; `archive` subcommand for deliberate cleanup |
| Survivor list drifts into bikeshedding (2-line ideas, no leverage) | Critique pass requires explicit "why this leverage" for survivors; rejection pass filters noise before ranking |
| Promote creates half-formed epics | Promote explicitly routes the user to `/flow-next:interview` as the next step; epic skeleton has `## Source` link so interview has context |
| Users confuse prospect with interview | Docs + hint prompts explicitly state: prospect = "many candidates, rank them"; interview = "one candidate, go deep"; plan = "one spec, break into tasks" |

## Follow-ups (not in this epic)

- Cross-project prospecting (scan multiple repos simultaneously)
- LLM-powered survivor-scoring (currently prose-only ranking)
- Scheduled weekly prospect via `/schedule` remote agent

## Tasks

Planned task breakdown (epic-review will finalize):

1. Skill + command + workflow.md (phases 0-6, backend-agnostic prose, artifact writer)
2. `flowctl prospect promote` subcommand + artifact parser + epic skeleton generator
3. `flowctl prospect list / read / archive` subcommands
4. Resume / extend logic (Phase 0) + artifact frontmatter schema
5. Smoke test + Ralph-block verification
6. Docs, website, codex mirror, version bump (minor: 0.35.1 → 0.36.0)
