---
satisfies: [R9]
---
# fn-147-source-tags-in-interview-provenance-for.2 Downstream docs: repo + flow-next.dev + changelog

## Description
Downstream docs for interview source tags: repo docs stop being capture-only, docs site follows, CHANGELOG staged. Docs only; no behavior.

**Size:** XS

**Files:**
- `plugins/flow-next/docs/spec-template.md` (§ Source tags: written by capture AND interview; note untagged = unknown provenance)
- `CHANGELOG.md` (`## Unreleased` entry; no bump, batched release)
- `~/work/flow-next.dev/src/content/docs/cookbook.mdx` (two Evidence-first tag recipes stop implying capture-only)
- `~/work/flow-next.dev/src/content/docs/` interview skill page (mention tags in write-back)

### Approach

- Repo docs first, then the site; `pnpm build` gate on the site; plain hyphens, customer register on the site.
- Vault note update (Lifecycle & Handover Objects) is maintainer-side; do it in the same sitting.
- flow-next.dev commits separately in its own repo.

### Key context

3.7.0 shipped the tally + targeted-re-interview recipes documented as capture-only in effect. This task makes those docs true for interview-authored specs. Do not promise anything task 1 did not implement.

## Acceptance
- [ ] docs/spec-template.md § source tags names interview as a tag writer and states untagged = unknown provenance
- [ ] CHANGELOG `## Unreleased` entry staged (no version bump)
- [ ] flow-next.dev cookbook recipes + interview page updated; pnpm build green
- [ ] No doc claims beyond implemented behavior


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
