## Description

Update the externally-facing flow-next page at `~/work/mickel.tech/app/apps/flow-next/page.tsx` to surface the new affordances: structured business-context capture, the symmetric-interview `--scope=business|technical|both` pattern. Standalone PR against `gmickel/mickel.tech` (out-of-tree from this repo).

**Size:** S/M
**Files:**
- `~/work/mickel.tech/app/apps/flow-next/page.tsx`

## Approach

Audit current page for existing spec-driven framing (added during fn-43). Extend with:
- One section or paragraph on structured business-context capture: brief framing that fn-44's symmetric-interview pattern formalizes the PO→dev-agent handover; mention `--scope` flag as the entry point
- Highlight the nine business-context dimensions as "structured input for implementing agents"
- Keep existing spec-driven framing as anchor; new content layers under it

Open PR against `gmickel/mickel.tech` (separate repo). Title: "Surface --scope flag + structured biz capture in flow-next page".

## Investigation targets

**Required:**
- `~/work/mickel.tech/app/apps/flow-next/page.tsx` — full current content
- fn-44 spec Goal & Context — value-prop framing to mirror externally

## Acceptance

- [ ] mickel.tech page updated with structured biz-context framing + `--scope` flag mention
- [ ] Existing spec-driven framing preserved as anchor
- [ ] Local lint + build pass in `~/work/mickel.tech` before opening the PR (e.g., `pnpm lint && pnpm build` or the project's equivalent). Evidence recorded in the task done-summary (command output excerpt or commit hash that the CI green-lit).
- [ ] PR opened against `gmickel/mickel.tech`; URL recorded

## Done summary
Surfaced fn-44 1.1.0 affordances on the externally-facing flow-next page at mickel.tech: symmetric interview `--scope=business|technical|both` flag + structured business-context capture (nine dimensions, sparse-layer suggestion semantics). Also fixed the "Business spec / Full spec" naming bug (fn-44 R12/R13) — handovers are now described as layer-state ("Spec — business-layer complete" / "Spec — fully complete") of one evolving spec, not two distinct artefacts. Bumped APP_DATA version to 1.1.0. `pnpm lint && pnpm build` green in mickel.tech. PR #7 opened against gmickel/mickel.tech.
## Evidence
- Commits: b097af93a8ac5ced0b9b326ce7eaa96e7d21722b
- Tests: pnpm lint (mickel.tech) — clean, pnpm build (mickel.tech) — Compiled successfully in 2.2s; 111/111 static pages generated
- PRs: https://github.com/gmickel/mickel.tech/pull/7