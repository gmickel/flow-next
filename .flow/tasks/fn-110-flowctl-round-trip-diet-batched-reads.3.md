---
satisfies: [R8]
---

## Description

Docs across repo + docs-site, written in the post-fn-117 register: mechanical precision, plain imperative, NO speed/process brags, role labels, verification-first tone where relevant.

**Size:** S/M
**Files:** plugins/flow-next/docs/flowctl.md, CHANGELOG.md, .flow/usage.md, ~/work/flow-next.dev: src/content/docs/flowctl/cli-reference.mdx, src/content/docs/flowctl/configuration.mdx, src/content/docs/cookbook.mdx (scan)

## Approach

- flowctl.md: `config get` subtree subsection (prose convention, not tables); `task create` flag list + one sentence on file-flags vs set-spec; `spec create` paragraph: create-time `--branch` is the path, `set-branch` is for renames.
- CHANGELOG: new `## Unreleased` above 2.20.0; bold-lead + fn-110 id + mechanism sub-bullets + "Dual-copy flowctl mirrored." No version bump (batched).
- usage.md: the two canonical example lines gain the flags inline; one-line diffs, keep terse.
- flow-next.dev (post-overhaul site - read the CURRENT pages first): cli-reference.mdx collapse the create+set-branch two-call example; configuration.mdx subtree-read subsection after single-key examples; cookbook.mdx scanned for stale two-call recipes (fix any); note the register rules explicitly when writing (no "faster"/"fewer round-trips" marketing - state what the command does). pnpm build gate; commit separately in the flow-next.dev repo.

## Acceptance

- [ ] All repo docs updated; CHANGELOG Unreleased entry present; usage.md lines current (R8)
- [ ] docs-site pages updated, cookbook scanned, pnpm build green; copy passes the register check (no speed-brag phrasing) (R8)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
