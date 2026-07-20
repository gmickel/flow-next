---
satisfies: [R3, R4, R7, R8]
---

## Description

Proof + reference pages, and the skill-page content pass. Repo: ~/work/flow-next.dev.

**Size:** L (split candidate at work time: reference pages vs skill-page pass)
**Files:** new pages - verification-spine, field-notes, faq, first-30-minutes, troubleshooting (port), glossary; ~21 skill pages under src/content/docs/skills/; both nav sources

## Approach

- Verification spine page: the philosophy as ONE system (receipts, evidence JSON, QA live-app verdicts, gate receipts, evidence-over-narration, no-self-grading); lineage citations exactly once sitewide (Wei/Karpathy/Vogels/Sonar/Willison) + Sonar 96/48 stat with link. This page owns "bias towards verification". Use the ReceiptCallout component from .4 (src/components/ReceiptCallout.astro) for receipt/gate-outcome facts on this page.
- Field notes page: anonymized-BOLD enterprise evidence (Decision 5): discovery throughput (2-3h interviews -> 8-11 specs), PM verdicts, same-day field-fix arcs, GHE/Windows/GitLab/Jira environments; honest asymmetry (PM relief vs senior-dev friction); OSS proof strip (linked quotes, awesome-list, 3-OS CI) using the CaseCapsule component from .4 (src/components/CaseCapsule.astro) for the linked case/testimonial quotes. NO client names; boundary grep must stay clean.
<!-- Updated by plan-sync: fn-117.4 built ReceiptCallout/CaseCapsule as concrete component names (task text previously described them only generically) -->
- FAQ: real coaching objections as seeds (spec-becomes-the-app sizing fear; perpetual-spec-library misconception - completed specs are immutable change history, living docs are separate; guardrails vs security controls taxonomy; "do I need all of this? no - smallest sufficient workflow"). NO competitor comparison content (Decision 2).
- First 30 minutes: narrative first-spec tutorial with real command output.
- Troubleshooting: port repo docs/troubleshooting.md; Glossary: render from GLOSSARY.md.
- Skill-page pass: all ~21 bare pages gain a Tips box + a Dynamic usage section (cookbook cross-links) + ONE worked example (real invocation + output excerpt). pilot + flow-next-drive already exceed the bar - align, don't bloat.

## Acceptance

- [ ] Six new pages live in both navs; lineage cited exactly once sitewide; Sonar stat linked (R3)
- [ ] Field notes anonymized-bold; boundary grep clean (R4)
- [ ] 21 skill pages carry Tips + Dynamic usage + worked example (R8)
- [ ] pnpm build green (R7)

## Done summary
Proof + reference pages and the skill-page pass shipped in ~/work/flow-next.dev (commits 6d9adfd, 07c0e60). Six new pages, all in BOTH nav sources (site.ts navGroups + astro.config sidebar; First 30 Minutes also as a DocsRail top link): strategy/verification-spine (owns "bias towards verification"; the five lineage citations - Wei/Karpathy/Vogels/Sonar/Willison - appear there and ONLY there sitewide, every URL web-verified resolving; Sonar 96/48 stat linked to the sonarsource press release; ReceiptCallout renders for review + green receipts), proof/field-notes (anonymized-BOLD enterprise evidence - sector descriptors only, PM verdicts unquoted per linked-quotes-only discipline; OSS proof strip from the verified GitHub pool via CaseCapsule: Novotny #111 lead, Michalina #5, possibilities #95, raydocs #4, awesome-list #96, 3-OS CI; honest asymmetry section; X set NOT used per manifest exclusion), proof/faq (real coaching objections: smallest-sufficient-workflow, spec-sizing fear, immutable-spec-library, guardrails vs security controls; zero competitor content), first-30-minutes (narrative tutorial with realistic flowctl/verdict output), reference/troubleshooting (full port of repo docs/troubleshooting.md with site-local links), reference/glossary (rendered from GLOSSARY.md with anchor cross-links). Landing proof pillar retargeted to the spine page; llms.txt site map extended. Skill-page pass: all 23 bare pages gain Worked example + Tips aside + Dynamic usage cookbook cross-links (anchors verified against dist); pilot + flow-next-drive aligned with a compact Dynamic usage block only. pnpm build green (74 pages); PSVI + client-name boundary greps clean; role labels only, no banned patterns marketed.
## Evidence
- Commits: 6d9adfd, 07c0e60
- Tests: baseline: green (gate check --gate docs_build: RUN, no receipt; cd ~/work/flow-next.dev && pnpm build, 68 pages, rc=0), cd ~/work/flow-next.dev && pnpm build (post-change: 74 pages, rc=0; green receipt recorded via flowctl gate receipt --gate build), grep -ri 'PSVI|Velocity Index' over flow-next.dev/src + mickel.tech/app/apps/flow-next + README.md + plugins/flow-next/docs (empty, exit 1), client-name boundary grep via ~/.claude/flow-next-client-names.txt over the same trees (empty, exit 1), lineage-once check: grep Karpathy/Vogels/Willison/jasonwei/sonarsource over src -> only strategy/verification-spine.mdx, anchor check: all 6 new pages built in dist; troubleshooting anchor slugs (#review-loop..., #just-updated..., #uninstall) present; cookbook category ids verified against dist
- PRs: