---
satisfies: [R3, R4, R7, R8]
---

## Description

Proof + reference pages, and the skill-page content pass. Repo: ~/work/flow-next.dev.

**Size:** L (split candidate at work time: reference pages vs skill-page pass)
**Files:** new pages - verification-spine, field-notes, faq, first-30-minutes, troubleshooting (port), glossary; ~21 skill pages under src/content/docs/skills/; both nav sources

## Approach

- Verification spine page: the philosophy as ONE system (receipts, evidence JSON, QA live-app verdicts, gate receipts, evidence-over-narration, no-self-grading); lineage citations exactly once sitewide (Wei/Karpathy/Vogels/Sonar/Willison) + Sonar 96/48 stat with link. This page owns "bias towards verification".
- Field notes page: anonymized-BOLD enterprise evidence (Decision 5): discovery throughput (2-3h interviews -> 8-11 specs), PM verdicts, same-day field-fix arcs, GHE/Windows/GitLab/Jira environments; honest asymmetry (PM relief vs senior-dev friction); OSS proof strip (linked quotes, awesome-list, 3-OS CI). NO client names; boundary grep must stay clean.
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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
