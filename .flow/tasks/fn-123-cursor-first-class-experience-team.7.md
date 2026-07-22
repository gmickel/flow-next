---
satisfies: [R10, R12]
---
# fn-123-cursor-first-class-experience-team.7 Cursor install truth rewrite + downstream onboarding walk

## Description
Rewrite Cursor installation truth + downstream onboarding. flow-next repo: README.md, scripts/install-cursor.sh + .ps1 output, plugins/flow-next/docs/platforms.md, CHANGELOG.md (`## Unreleased` only - no version bump). Team-marketplace repo import becomes the RECOMMENDED Cursor install; local scripts stay as documented fallback. Add a short admin onboarding runbook (import repo -> choose Default On vs Required -> verify auto-refresh -> per-repo `/flow-next-setup`). Correct stale caveats everywhere: slash autocomplete DOES list commands (hyphenated `/flow-next-plan` form), natural-language triggering works, AskUserQuestion native incl. multi-question batches; remove/correct claims that Cursor lacks hooks or has an incompatible hook schema (accurate statement: flow-next intentionally does not build Ralph on Cursor). Add `test_cursor_docs_contract.py`. flow-next.dev repo (SEPARATE commits in that repo): install/introduction/orchestration/review/setup/subagents pages + docs-site changelog `## Unreleased` entry per releasing.md register.

## Acceptance
- Team-marketplace import is the recommended Cursor path on all active surfaces; local installers accurate as fallback (no longer presented as the primary enterprise path).
- Admin runbook present (import, install modes, auto-refresh verification, per-repo setup).
- All stale caveats corrected (autocomplete, natural-language triggering, native asks, hooks claims); no public-marketplace submission path introduced.
- Repo + docs-site get matching `## Unreleased` entries; no version manifests / FLOW_NEXT_VERSION touched.
- `pnpm --dir ~/work/flow-next.dev build` green; flow-next.dev changes committed separately in that repo (conventional commits).
- Focused suites green (`test_install_cursor_parity`, `test_cursor_docs_contract`).


## Done summary
Rewrote Cursor install truth for team-marketplace-first onboarding (R10/R12).

- platforms.md: full Cursor section rewrite — team-marketplace recommended, admin runbook, corrected autocomplete/asks/hooks claims, documented rules rail / host backend / AGENTS routing / readonly / alias-inherit
- install-cursor.sh + .ps1: removed under-lists caveat; team-marketplace recommended note
- README Cursor row: marketplace import recommended + platforms.md#cursor link
- CHANGELOG ## Unreleased: whole fn-123 summary (no version bump)
- test_cursor_docs_contract.py: prose contracts for platforms/install/README
## Evidence
- Commits:
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_cursor_docs_contract test_install_cursor_parity -q
- PRs: