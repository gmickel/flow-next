---
satisfies: [R5, R12]
---

## Description

Foundation assets every other task consumes: the verified testimonial set, the mechanical boundary gates, and the private release-guidance narrative layer.

**Size:** M
**Files:** ~/work/mickel.tech (read-only git archaeology), ~/.claude/CLAUDE.md (private, "Flow-Next downstream properties" section), scratch testimonials manifest committed to this repo at agent_docs/testimonials.md

## Approach

1. Extract the full original testimonials array from mickel.tech git history: `git -C ~/work/mickel.tech show d7a4024:app/apps/flow-next/page.tsx` (+ scan later commits touching testimonials for additions). Capture name, handle, quote, x.com status URL per entry.
2. Verify every URL resolves (curl HEAD or WebFetch; an x.com status link behind login still counts if the status id is real - record verification method per entry). Merge with the GitHub pool: Novotny issue #111 (lead quote), Michalina #5, possibilities PR #95, raydocs #4, Rytis-J #54, awesome-list #96. Produce agent_docs/testimonials.md: the canonical verified manifest (quote verbatim, author, handle, URL, verified-date) that .2/.4/.7 render from.
3. Boundary gates: add the PSVI/client-name grep pair to the spec's Quick commands as an executable check; run it against current state to confirm baseline-clean.
4. Private CLAUDE.md (Workstream F): rewrite the "Flow-Next downstream properties" intro block to layer narrative discipline over the mechanics per the spec's Workstream F list (claim-hierarchy frame, story-beat habit, boundaries, per-property tone map, canonical-home pointer). Keep every existing mechanical instruction intact.

## Investigation targets

**Required:**
- mickel.tech commits d7a4024 (testimonials added) and any later `-S testimonial` hits
- fn-117 spec sections: messaging architecture, hard boundaries, Workstream F
- ~/.claude/CLAUDE.md current "Flow-Next downstream properties" section (do not lose content)

## Acceptance

- [ ] agent_docs/testimonials.md exists: every entry has a resolving public URL + verification note; the mangled/unverifiable entries are excluded with a reason line (R5 substrate)
- [ ] Boundary greps run clean on current state and are documented in the manifest header
- [ ] Private CLAUDE.md carries the narrative layer; mechanical chain unchanged (R12); diff reviewed against the Workstream F list

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
