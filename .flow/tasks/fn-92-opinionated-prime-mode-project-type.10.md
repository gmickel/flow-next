---
satisfies: [R14]
---

## Description
Docs finalization + CHANGELOG + cross-spec edit.

**Size:** M | **Files:** README.md (L99/L301), plugins/flow-next/docs/ (skills.md L38, README.md index, orchestration.md L34/L119, flowctl.md L907/L956, self-improving.md, platforms.md L80/L86), CLAUDE.md where-to-look row, GLOSSARY.md (candidates: operability ladder, hard gate, delivery shape, classification), agent_docs/optimizing-skills.md touch-up, CHANGELOG.md (Unreleased), .flow/specs/fn-85-* (drop prime from Tier C or record the dep)

## Approach
- Per the docs-gap table: rewrite the two prime one-liners (verdict/classification framing, no stale 8/48 counts), add docs/README.md index row (decide docs/prime.md vs skills.md-only and note the docs-site follow-on), update orchestration tier wording (new groups are host-inline - scanners line stays true), criterion-id callouts in flowctl.md, self-improving once-per-repo framing vs --classify-only, agent counts in README/platforms (check after task 8), GLOSSARY candidates (judgment: only if public vocabulary).
- CHANGELOG under Unreleased, no version bump (batched releases); the entry NAMES the flow-next.dev prime page + both navbars as pending downstream items per amended R14 (the release walk consumes that note).
- fn-85 cross-edit per resolution 16.

## Acceptance
- [ ] Every docs-gap row addressed or consciously skipped with a note; no stale criteria counts anywhere (grep for the old census across docs)
- [ ] CHANGELOG Unreleased entry naming the docs-site downstream items; no bump
- [ ] fn-85 edited (prime dropped from Tier C or dep recorded)
- [ ] CLAUDE.md where-to-look row added

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
