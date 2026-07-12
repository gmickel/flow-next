---
satisfies: [R5, R6, R6b, R13]
---

## Description
Own ALL scoring architecture in one place: pillars.md rewrite.

**Size:** M | **Files:** `plugins/flow-next/skills/flow-next-prime/pillars.md` (only; plus a one-line back-propagation into the spec md if the pinned wording drifts)

## Approach
- Substance pass-conditions per spec Architecture "Substance-not-existence upgrades": SV3 (L17), SV4 full feedback-gate rewrite (L18), SV5/SV6 (L19-20), BS2/BS3 (L38-39), TS5 (L63), DC2 (L82 - ONE published scale, see denominator drift below), DE1 (L107), DE4 (L110), DE5 (L111). Every pass condition states its executed/cross-referenced evidence requirement.
- New group tables: AO/DR/TO, HP, and the gap-diff criteria (docs-freshness, large-file metrics, CI-actually-gates, gh-CLI host line, secrets gate, destructive scan, API contract) with an explicit taxonomy column (scored-in-tier / report-only / informational) per Planning resolution 1: scored groups live in the agent-readiness tier but are EXCLUDED from the maturity-percentage formula (level stays avg Pillars 1-5).
- SV4 vs CI-actually-gates boundary per resolution 2 (topology vs triggers; no double-scoring; Pillar 8 untouched). SV4 pass = tests gated at L3/L4; L1/L2 = strength/headroom-warn only (R6b as amended).
- The criterion-to-score MAP per amended resolution 1: every new row declares group, taxonomy, denominator behavior, aggregate presentation, remediation eligibility, hard-gate impact; DR-core named as the four-ID set (seeded data, dev login, drivable surface, readable evidence).
- N/A whitelist becomes a single table here (resolution 11), including the classification-driven entries (greenfield deferrals, shape/tier caps, inactive harnesses); floor rule gains "pillars with all criteria excluded skip floor checks".
- Update the 48/50 census sentence (L120) and the scoring/floors section (L193-217) for the new census; hard-gate Level-2 cap rule stated here.
- DC2 denominators: pillars.md says 5/8, remediation.md 5/10, claude-md-scout X/8 - define the single scale HERE; tasks 7/8 sweep the other two files.

## Key context
- R13: all 48 legacy criteria remain present and scored - tighten, never remove.
- Memory: prose is executable contract; POSIX classes in any embedded grep.

## Acceptance
- [ ] Every upgraded criterion row states a substance pass condition with its evidence requirement (quote or executed output)
- [ ] SV4 row = layer-agnostic deterministic feedback gate: tests-at-L3/L4 required; L1/L2 absence = headroom warn; stub-hook, tests-in-precommit, unhardened-hook flags present
- [ ] AO/DR/TO + HP + gap-diff tables exist with taxonomy column; scored groups documented as level-formula-excluded (resolution 1)
- [ ] Single N/A whitelist table exists incl. classification-driven entries; floor rule handles all-excluded pillars
- [ ] Census arithmetic + level floors updated; hard-gate cap rule stated; 48 legacy criteria all present
- [ ] DC2 has ONE published scale; SV4/CI-gates boundary stated per resolution 2
- [ ] Criterion-to-score map present for every new row; DR-core four-ID set named with the all-four QA-readiness rule

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
