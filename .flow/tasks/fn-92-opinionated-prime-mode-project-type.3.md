---
satisfies: [R3, R7, R8, R9, R10, R17]
---

## Description
New reference files: playbooks.md + harness.md.

**Size:** M | **Files:** `plugins/flow-next/skills/flow-next-prime/playbooks.md`, `plugins/flow-next/skills/flow-next-prime/harness.md` (both new)

## Approach
- playbooks.md: five shape playbooks (greenfield bootstrap plan ~8-12 items + recorded-deferral mechanic; standard; monorepo; huge/legacy as LEG1-LEG9 generic patterns with LEG4/6/7 marked all-shapes; constellation full home-base + the LIGHT product-family variant with its selector - spec "Lightweight product-family variant").
- The ranked-actions catalog (15 items) WITH a tier column (Critical/High/Medium/Bonus) mapping to existing --fix-all semantics (resolution 5); structural actions annotated explicit-consent-only.
- Report-shape templates per classification incl. the compression rule (failing detail, passing one-line - resolution 13).
- harness.md: HP1-HP16 rows (probe / pass condition / harness / evidence class / scored-core vs informational), per-harness instantiation table (Claude/Codex/Cursor/Copilot/Droid/OpenCode - which file, which syntax per function class), active-harness detection, P0 rules (inline secrets, suspicious hooks), and the remediation safety rules verbatim from spec (deny/ask scaffold-safe; allow only from Phase-2-verified commands + trust caveat; never-list).

## Key context
- LEG patterns reference stacks.md rows for instantiations - never name stacks in pattern logic.
- HP7 read-never-execute vs remediation exercise-what-you-scaffold distinction stated explicitly (gap 27).

## Acceptance
- [ ] Five playbooks + light constellation variant + selector present (R3, R7, R8, R9, R10)
- [ ] Ranked catalog carries tier column; consent boundaries per resolution 5/6 stated
- [ ] LEG1-9 written stack-agnostic; LEG4/6/7 marked all-shapes; instantiations point at stacks.md rows (R9)
- [ ] harness.md: HP rows with scored-core marked, per-harness instantiation table, P0 rules, remediation safety rules (R17)
- [ ] Report compression rule stated; zero dispatch/ask tokens (grep)

## Done summary
Created the two remaining prime reference files: playbooks.md (shape selector; greenfield bootstrap plan + recorded-deferral mechanic; standard/monorepo/huge-legacy playbooks; LEG1-LEG9 generic pattern definitions with LEG4/6/7 marked all-shapes and instantiations pointing at stacks.md; constellation full home-base + lightweight product-family variant + selector; 15-item ranked-actions catalog with Critical/High/Medium/Bonus tier column + consent boundaries; report-shape templates + compression rule) and harness.md (five function classes; active-harness detection; HP1-HP16 probe/mechanism table with scored-core HP1/2/5/7/9/12 per pillars.md; per-harness instantiation table for six harnesses; P0 rules; HP7 read-never-execute vs remediation exercise distinction; remediation safety rules verbatim). One-line-pointer discipline throughout, zero dispatch/ask tokens, no em dashes; codex mirror regenerated.
## Evidence
- Commits: 0a4c391c8f30678e25c5ea3459ea549096853ff6
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (1581 tests, OK; baseline green, post-edit exit 0), bash scripts/sync-codex.sh (all validators pass), grep: zero ask-tool/dispatch tokens + zero em dashes in both new files
- PRs: