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
Finalized all in-repo prime documentation for fn-92: rewrote the prime one-liners (README, docs/skills.md) to the verdict/classification framing and removed the stale 8-pillar/48-criteria census (including both plugin.json manifests); added a prime SKILL.md workflow-reference row to docs/README.md (with the deliberate no-docs/prime.md decision recorded), documented the new `flowctl prime classify` emitter in flowctl.md, nuanced the self-improving once-per-repo framing against re-runnable `--classify-only`, added the CLAUDE.md where-to-look row, added four GLOSSARY terms (Operability ladder, Hard gate, Delivery shape, Classification (prime)), touched up the optimizing-skills prime-scout framing, wrote the CHANGELOG Unreleased entry (naming the flow-next.dev prime page + both navbars as pending downstream per amended R14), and dropped prime from fn-85's Tier-C list (resolution 16; the fn-92 dependency was already recorded). No version bump (batched releases); no skill files touched so no Codex mirror regen needed. Full test suite green (1655 tests).
## Evidence
- Commits: 50551e3a723a8728d35e2b2986cc164606f3f23a
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' -> Ran 1655 tests, OK (skipped=2), exit 0 (green baseline), flowctl glossary list --json -> parses; 4 new terms present with correct avoid/relates, flowctl prime classify --json -> emits pinned schema, glossary_smoke_test.sh -> exit 1 by-design safety refusal (declines to run inside main plugin repo); glossary correctness verified via flowctl list instead
- PRs: