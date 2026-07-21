---
satisfies: [R10, R18]
---
# fn-121-plugin-mode-zero-rerun-setup-on-claude.3 flow-next.dev downstream walk: get-started/installation/update + changelog

## Description
Downstream docs-site walk for the plugin-mode story. Separate repo: `~/work/flow-next.dev` (commit there, NOT in this repo; do not push unless asked). Size: S.

**Context**: Read the fn-121 spec + the landed .1/.2 diffs first (source of truth for behavior). Per flow-next.dev/CLAUDE.md: navigation has TWO sources (DocsRail + astro sidebar) - no new page is planned here, so only touch them if you decide a new page is warranted (not expected). Do NOT bump FLOW_NEXT_VERSION or package.json (batched-release rule; the changelog entry stages under the unreleased/latest convention per agent_docs/releasing.md "Docs-site changelog entry").

**Work**:
1. Get-started / quick-start / installation pages: Claude Code path becomes "install plugin, use it" - setup is optional/run-once (snippet + mode choice); document the mode question (plugin vs copy), that plugin mode never needs a setup rerun, and `flowctl usage` as the guide entry point.
2. Update/upgrade page: the "re-run setup after every update" instruction becomes copy-mode-only; plugin mode updates ride the plugin silently.
3. Any page asserting `.flow/bin/flowctl` or `.flow/usage.md` as universal paths: mode-qualify (grep the docs source for both strings).
4. Two-layers explainer (R18, site half): the orchestration page mirrors the new repo-docs "Two layers of steering" section - session steering vs machinery steering, precedence chain, the persists-nothing prompt example; practitioner register, copy-paste friendly.
5. Stage the docs-site changelog entry (scannable highlights, not a repo-CHANGELOG copy) - under the Unreleased/staged convention, no version bump.
6. Tone: skeptical-staff-engineer register per the messaging architecture; lead with the proof-backed claim (probe-validated zero-setup), no hype.

**Gate**: `cd ~/work/flow-next.dev && pnpm build` green. Commit separately in that repo with a conventional message referencing fn-121.
## Acceptance
- R10: get-started/installation/update pages reflect plugin mode (zero-rerun Claude Code story, mode question, flowctl usage pointer); no page asserts `.flow/bin/flowctl` or `.flow/usage.md` as universal (grep-verified in docs source); docs-site changelog entry staged; NO FLOW_NEXT_VERSION/package.json bump.
- R18 (site half): orchestration page carries the two-layers section (session vs machinery steering + precedence chain).
- `cd ~/work/flow-next.dev && pnpm build` exits 0.
- Changes committed in the flow-next.dev repo (separate commit, references fn-121); nothing pushed.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
