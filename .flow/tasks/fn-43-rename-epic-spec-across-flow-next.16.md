---
satisfies: [R25, R29]
---

## Description

Maintainer-only post-merge updates to two external repos. **This task does NOT gate fn-43 epic close.** Per spec R25 ("tracked but not blocking the release") and R29 ("maintainer-only; external repo"), task acceptance is "drafts pushed and PR links recorded in `done_summary`"; merges happen on Gordon's timing. Mark `done` once drafts are up. (a) `~/work/mickel.tech` flow-next page (rename + add explicit "spec-driven development" framing per R25); (b) `~/work/AI-x-SDLC-Starter-Kit` methodology guide cross-reference.

**Size:** M
**Files (external repos, NOT this marketplace):**
- `~/work/mickel.tech/app/apps/flow-next/page.tsx` (29 epic refs + framing addition)
- `~/work/AI-x-SDLC-Starter-Kit/guides/methodology.md` (line 546)

## Approach

### mickel.tech page (R25) -- TWO things, not just rename

1. **Vocabulary rename.** Every CLI reference, artefact path, command name, prose mention. Hot spots per docs-gap-scout: lines 102, 105, 107, 132, 149, 169, 351, 466, 475, 485, 493, 500, 509, 529, 584, 597, 672, 676, 686, 697, 931, 979, 1156, 1276.
2. **Spec-driven development framing.** Lede / hero / metadata description / FAQ copy explicitly frames flow-next as a spec-driven development system. Includes:
   - Hero subtitle update.
   - Metadata description add "spec-driven development" phrase.
   - One new FAQ entry: "What does 'spec-driven development' mean for flow-next?" (3-4 sentences).
   - Existing FAQ entry for `/flow-next:epic-review` reframed as `/flow-next:spec-completion-review`.

### AI-x-SDLC-Starter-Kit (R29)

`guides/methodology.md:546` -- the [8] PR-AS-COGNITIVE-AID callout. Two specific edits:
1. `"epic spec with R-IDs"` -> `"spec with R-IDs"`.
2. `flowctl epic export-cognitive-aid` -> `flowctl spec export-cognitive-aid`.

Other guides reference flow-next via slash-command names (which do NOT change). The `coding-assistants.md:100` "read the parent epic" example uses generic Agile vocabulary -- explicitly out of scope per spec Boundaries.

## Investigation targets

**Required:**
- `~/work/mickel.tech/app/apps/flow-next/page.tsx` -- enumerated lines.
- `~/work/AI-x-SDLC-Starter-Kit/guides/methodology.md:546`.

## Key context

- This task is **maintainer-only**. External contributors skip; Gordon handles post-merge.
- Two separate PRs: one to mickel.tech, one to AI-x-SDLC-Starter-Kit.
- mickel.tech CLAUDE.md design rules: Atelier shell, no em-dashes in body, "Agentic PDLC" not "agentic SDLC".
- **Acceptance is "drafts pushed", NOT "merged".** External-repo merges are not on the fn-43 epic close gate -- this task records the work was done and provides PR links, but doesn't block fn-43 close on external review timing.

## Acceptance

- [ ] mickel.tech `/apps/flow-next` page draft PR pushed; PR URL recorded in `done_summary`.
- [ ] mickel.tech page draft has zero `flowctl epic` references in user-visible copy.
- [ ] mickel.tech page draft has explicit "spec-driven development" framing in lede / hero / metadata / FAQ.
- [ ] mickel.tech page draft passes biome lint + tsc + build (verified locally before pushing).
- [ ] AI-x-SDLC-Starter-Kit draft PR pushed; PR URL recorded in `done_summary`. The `methodology.md:546` updated for both prose phrasing and CLI verb.
- [ ] PR URLs for both drafts recorded; merge timing is on Gordon's separate cadence (not gating this task).

## Done summary
External T16 maintainer-only task: drafted both PRs for the post-merge external repo updates.

mickel.tech: rebranded the public flow-next product page for 1.0 -- collapsed `epic` vocabulary to `spec` across hero, FAQ, scouts, phases, features, commands, Ralph + storage sections; renamed `/flow-next:epic-review` -> `/flow-next:spec-completion-review` and `epic-scout` -> `spec-scout`; corrected the `.flow/` directory tree (spec markdown + JSON sidecar colocate under `.flow/specs/`); added a new "What does spec-driven development mean for flow-next?" FAQ; reframed hero subtitle, metadata title/description, OpenGraph + Twitter to lead with spec-driven development; bumped page version 0.40.0 -> 1.0.0; verified clean via biome + tsc + `bun run build`.

AI-x-SDLC-Starter-Kit: targeted edit at `guides/methodology.md:546` (the [8] PR-AS-COGNITIVE-AID callout) -- "epic spec with R-IDs" -> "spec with R-IDs" and `flowctl epic export-cognitive-aid` -> `flowctl spec export-cognitive-aid`. Other guides (slash-command references) intentionally not touched per fn-43 boundaries.

Both PRs are DRAFT per the task acceptance ("drafts pushed, NOT merged"). Merge timing on Gordon's separate cadence -- this task does NOT gate fn-43 epic close.

Drafts:
- mickel.tech: https://github.com/gmickel/mickel.tech/pull/5
- AI-x-SDLC-Starter-Kit: https://github.com/gmickel/AI-x-SDLC-Starter-Kit/pull/3
## Evidence
- Commits: mickel.tech@1e241db: feat(flow-next): rename to spec-driven vocabulary + 1.0 framing, AI-x-SDLC-Starter-Kit@c5537c2: docs(methodology): rename flow-next epic refs to spec for 1.0
- Tests: mickel.tech: bun x biome check app/apps/flow-next/page.tsx -- clean, mickel.tech: bun x tsc --noEmit -- clean, mickel.tech: bun run build -- compiled successfully, AI-x-SDLC-Starter-Kit: grep -n 'flowctl epic\|epic spec with R-IDs' guides/methodology.md -- no matches
- PRs: https://github.com/gmickel/mickel.tech/pull/5 (draft), https://github.com/gmickel/AI-x-SDLC-Starter-Kit/pull/3 (draft)