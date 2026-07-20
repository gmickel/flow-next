---
satisfies: [R8]
---

## Description

Docs across repo + docs-site, written in the post-fn-117 register: mechanical precision, plain imperative, NO speed/process brags, role labels, verification-first tone where relevant.

**Size:** S/M
**Files:** plugins/flow-next/docs/flowctl.md, CHANGELOG.md, .flow/usage.md, ~/work/flow-next.dev: src/content/docs/flowctl/cli-reference.mdx, src/content/docs/flowctl/configuration.mdx, src/content/docs/cookbook.mdx (scan)

## Approach

- flowctl.md: `config get` documents ALL THREE read forms (keyed scalar, keyed subtree, keyless root) with `--raw` behavior and exact JSON shapes per form (prose convention, not tables); `task create` flag list gains `--description-file` AND `--satisfies` (comma-list grammar, R-ID token rule, error-before-write, relationship to set-spec edits); `spec create` paragraph: create-time `--branch` is the path, `set-branch` is for renames.
- CHANGELOG: new `## Unreleased` above 2.20.0; bold-lead + fn-110 id + mechanism sub-bullets + "Dual-copy flowctl mirrored." No version bump (batched).
- CHANGELOG rider sub-bullet: the Foreground-rule fence-embedding fix (commit 1e8353d0, rides this PR) - one line, fn-78 stall-class recurrence hardening.
- usage.md: the two canonical example lines gain the flags inline incl. --satisfies; one-line diffs, keep terse.
- flow-next.dev (post-overhaul site - read the CURRENT pages first): cli-reference.mdx collapse the create+set-branch two-call example; configuration.mdx documents ALL THREE read forms (keyed scalar, keyed subtree, keyless root) with --raw behavior and exact JSON shapes per form, placed after the single-key examples; cookbook.mdx scanned for stale two-call recipes (fix any); note the register rules explicitly when writing (no "faster"/"fewer round-trips" marketing - state what the command does). pnpm build gate; commit separately in the flow-next.dev repo.

## Acceptance

- [ ] All repo docs updated; CHANGELOG Unreleased entry present; usage.md lines current (R8)
- [ ] docs-site pages updated, cookbook scanned, pnpm build green; copy passes the register check (no speed-brag phrasing) (R8)

## Done summary
Docs pass for fn-110 in the post-fn-117 register: flowctl.md documents the three config get read forms (scalar/subtree/root, --raw shapes, snapshot parse contract), task create's --description-file/--satisfies (R-ID grammar, error-before-write) and create-time --branch vs set-branch renames; CHANGELOG gains the fn-110 Unreleased entry (incl. the 1e8353d0 Foreground-rule fence-embedding rider); usage.md + setup template example lines carry the one-call flags (codex mirror regenerated, x2 idempotent). flow-next.dev: cli-reference two-call create+set-branch collapsed to create-time --branch, configuration.mdx gains a Reading-configuration section with exact JSON shapes, cookbook scan clean; pnpm build green; committed on its main (b12897c, 99812d9), not pushed. Codex impl-review: SHIP first pass (one non-blocking wording FYI applied in both repos).
## Evidence
- Commits: 85a1716880961c8ce8ff9d81bf01da1b85790da7, c063bb47714ce4cc7e4d1802b4f998d54086b132, e01dcc954b0f9f27ff1bb1d82f4064feb4f7d3a7, e9dcd13da8dbde91a3420241941e25cf4d8449e5, 755ff7ef3459554881119b58c5775b1f1a704292
- Tests: GATE_SKIPPED:unittest:green-receipt 2bb41aca - baseline reused from prior post-gate pass, GATE_SKIPPED:smoke:green-receipt 2bb41aca - baseline reused from prior post-gate pass, python3 -m unittest discover -s plugins/flow-next/tests -q (rc=0, green receipt 755ff7ef-unittest), (cd $(mktemp -d) && bash .../plugins/flow-next/scripts/smoke_test.sh) (rc=0, green receipt c063bb47-smoke), ./scripts/sync-codex.sh x2 (idempotent, mirror committed), cmp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py (dual-copy OK), cd ~/work/flow-next.dev && pnpm build (rc=0, 74 pages; docs-site commits b12897c, 99812d9 on its main, not pushed)
- PRs: