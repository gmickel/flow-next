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
Downstream docs for interview source tags: the tags are documented as coming from capture AND interview everywhere, and a real defect in the recipe published alongside 3.7.0 is fixed on both surfaces.

Repo `docs/spec-template.md`: names both writers, states the three rules a reader of a tagged spec needs (a pass tags only the criteria it authors and never retags an existing bullet, so provenance is frozen like the R-ID number; untagged means unknown provenance, never `[user]`; the read-back withholds an approve recommendation while unverified `[inferred]` items remain, narrowed in interview to inferred criteria no question covered), and adds a scope line so tags are not over-applied to task checklists or loose markdown files.

flow-next.dev: the two Evidence-first cookbook recipes stop implying capture is required, and the interview skill page gains a "Source tags on the criteria it writes" section (per-pass `[user]` meaning, the narrowing, the scope limit). Page was already in both nav sources, so no nav edit. `pnpm build` green, 76 pages.

Recipe fix, two bugs not one. Known: the class `[a-z:]+` silently dropped every `[strategy:*]` criterion, because a track name keeps its literal casing and may contain spaces or hyphens (`[strategy:Cross-platform parity]`). Found by running the corrected pipeline rather than assuming it: `awk` with the default whitespace split then puts a spaced track name in `$2` and reports a phantom tag - so the one-character class fix alone would have left the recipe broken in a quieter way. Now `[^]]+` plus a tab-delimited `awk -F'\t'`, verified against a synthetic case and the frozen fixture, with both traps documented inline.

CHANGELOG staged under `## Unreleased`, split Changed (the feature) / Fixed (the recipe bug). No version bump per the batched-release rule. Vault Lifecycle note updated maintainer-side with the coaching framing.
## Evidence
- Commits: e4d472b107e19788f7dc50ff404ffb56f6f18b29, flow-next.dev f8ade6c (pushed to main)
- Tests: python3 scripts/run_tests_parallel.py  (files=156 ran=3298 failures=0 errors=0 skipped=4), uvx ruff@0.16.0 check .  (All checks passed), cd plugins/flow-next/tests && python3 -m unittest test_interview_source_tags test_template_canonical -q  (30 tests OK), ./scripts/sync-codex.sh run twice - idempotent, guards green, cd ~/work/flow-next.dev && pnpm build  (76 pages, Complete), Recipe correctness verified two ways: synthetic case with a spaced track name ([strategy:Cross-platform parity]) tallies as one row, and the frozen fixture emission tallies user 2 / paraphrase 1 / inferred 2 / strategy:Self-serve 1 - the pre-fix awk reported a phantom 'parity' tag, Nav check: skills/interview present in BOTH src/lib/site.ts and astro.config.mjs - no nav edit required, Style: zero em dashes in added prose across all surfaces
- PRs: