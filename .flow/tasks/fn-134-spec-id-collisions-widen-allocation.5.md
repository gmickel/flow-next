---
satisfies: [R16, R17]
---
# fn-134-spec-id-collisions-widen-allocation.5 flow-next.dev: config, teams, troubleshooting, FAQ, Notable updates

## Description
flow-next.dev pass: surface that tracker-keyed spec ids exist and are the team default, document the config, answer the collision question in the FAQ, and add the Notable updates section to the landing page.

This is a **separate repo** (`~/work/flow-next.dev`) and commits there separately from the flow-next repo.

**Size:** M
**Files (in `~/work/flow-next.dev`):**
- `src/content/docs/teams/tracker-sync.mdx`
- `src/content/docs/teams/collaboration.mdx`
- `src/content/docs/flowctl/configuration.mdx`
- `src/content/docs/specs/schema.mdx`
- `src/content/docs/reference/troubleshooting.mdx`
- `src/content/docs/proof/faq.mdx`
- the landing page (Notable updates section)

### Approach

- `teams/collaboration.mdx` is the page a team actually reads when they hit this, so it carries the recommendation: tracker-keyed ids avoid the collision entirely, here is the one-line config.
- `teams/tracker-sync.mdx` - the hybrid id model, synthetic `gh-` / `gl-` keys, and that all four trackers now support tracker-first.
- `flowctl/configuration.mdx:123-131` - add `tracker.specIds` alongside the other `tracker.*` keys, matching the existing row format and the strict-enum note.
- `specs/schema.mdx` - the id scheme, both forms coexisting.
- `reference/troubleshooting.mdx` - what to do when two people got the same ordinal: it is a warning not a break, ids never change, do not renumber, and here is how to avoid it next time.
- `proof/faq.mdx` - one new question in the page's existing voice and heading shape (`## <question>`), covering "two of us created specs and both got fn-122". Match the register of the existing entries: direct, non-defensive, names the real limitation.
- **Notable updates on the landing page** - the customer-facing half of R17, mirroring the repo docs-home section. Short, scannable, one line per change plus how to enable.

Register rules for this site are strict and non-optional: lead with the reader's problem rather than the mechanism, plain hyphens and never em dashes, numbers as outcomes rather than inventory, and honest bounds kept rather than trimmed.

### Investigation targets

**Required** (read before coding):
- `~/work/flow-next.dev/src/content/docs/proof/faq.mdx` - question voice and heading shape
- `~/work/flow-next.dev/src/content/docs/flowctl/configuration.mdx:118-135` - the `tracker.*` config block and row format
- `~/work/flow-next.dev/src/content/docs/teams/collaboration.mdx` - where the recommendation belongs
- `~/work/flow-next.dev/CLAUDE.md` - navigation rules (a new page needs BOTH navbars; this task adds sections, not pages, so verify no nav change is needed)

**Optional** (reference as needed):
- `~/work/flow-next.dev/src/content/docs/reference/troubleshooting.mdx`
- the flow-next repo's `plugins/flow-next/docs/README.md` Notable updates section from task `.4`, to keep the two consistent

### Key context

Document what shipped, not what was planned. Read the landed repo docs from task `.4` and keep the two consistent without copy-pasting: the site is customer-facing prose, the repo docs are reference.

No version bump or changelog entry here unless a release is being cut; this is a docs-only pass on an already-released capability.

## Acceptance

- [ ] `teams/tracker-sync.mdx` and `teams/collaboration.mdx` state that tracker-keyed spec ids exist, are the recommended team default, and why (R16).
- [ ] `flowctl/configuration.mdx` documents `tracker.specIds` alongside the other `tracker.*` keys in the existing row format (R16).
- [ ] `specs/schema.mdx` covers the id scheme with both forms coexisting (R16).
- [ ] `reference/troubleshooting.mdx` explains the duplicate-ordinal case: warning not break, ids never change, do not renumber, how to avoid it (R16).
- [ ] `proof/faq.mdx` gains one question in the existing voice and heading shape covering the collision (R16).
- [ ] The landing page carries a **Notable updates** section consistent with the repo docs-home version, seeded with `tracker.specIds` (R17).
- [ ] No em dashes in new prose; register rules followed.
- [ ] Site build gate passes: `cd ~/work/flow-next.dev && pnpm build`.
- [ ] Committed and pushed in the flow-next.dev repo, separately from the flow-next repo.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
