---
satisfies: [R2, R11]
---

## Description

AI x SDLC Starter Kit updates per Workstream D. Repo: ~/work/AI-x-SDLC-Starter-Kit (direct push to main OK).

**Size:** M
**Files:** guides/flow-next.md, guides/plugins.md (L165), guides/team-enterprise.md, guides/code-review-tools.md, guides/factory-and-multi-agent.md, resources/assets/code-factory-onboarding.html (regen - source in ~/work/code-factory-package)

## Approach

- flow-next.md: expand "Reproducible floor, tunable ceiling" (7 abstract lines today) into the full menu-not-rail treatment with concrete patterns (skip, reorder, prompt-into, one-shot, parallelize incl. both task-parallelism forms, model-per-step via model-routing.md cross-link); light multi-harness beef-up of the install/platforms section.
- plugins.md L165: retired gmickel-claude-marketplace -> gmickel/flow-next.
- team-enterprise.md: substantive flow-next section (enterprise ways-of-working: governed context split, symmetric interview, receipts-as-audit-trail, anonymized field evidence per boundaries).
- code-review-tools.md: backend pluggability + receipts story. factory-and-multi-agent.md: map pilot/land/Ralph onto its architecture ladder.
- code-factory-onboarding.html: full regen from its markdown source in ~/work/code-factory-package (narrative pinned at 2.4.0 - bring to current; keep four-tracker text); verify the guide's bundled copy path.

## Acceptance

- [ ] flow-next.md teaches the menu concretely (>= 6 named patterns with invocations) (R2)
- [ ] All 4 guide additions + plugins.md fix landed; onboarding.html regenerated with current release narrative (R11)
- [ ] Boundary grep clean on all touched files

## Done summary
AI x SDLC guide (Workstream D) shipped and pushed (AI-x-SDLC-Starter-Kit@993eca3, direct-to-main per repo convention): guides/flow-next.md's 7-line "Reproducible floor, tunable ceiling" expanded into "The pipeline is a menu, not a rail" with 6 named patterns each carrying a real invocation (skip/lighten, one-shot chain, prompt-into, reorder/enter-anywhere, parallelize in both Decision-7 live forms, model-per-step cross-linked to model-routing.md + orchestration) plus cookbook/menu-not-a-rail doctrine links, and a multi-harness install-section beef-up (Grok Build compat, process-outlives-your-agent, Ralph host caveat). plugins.md L165 retired-marketplace ref fixed to gmickel/flow-next (+3 identical retired refs in claude-code.md, same defect). team-enterprise.md gained "Enterprise ways of working with a spec-driven harness" (governed context split, symmetric interview with the 2-3h/8-11-specs field pattern, receipts-as-audit-trail governance table, anonymized-bold sector-descriptor field evidence). code-review-tools.md gained the DIY-path flow-next subsection (pluggable backends, per-task review: override, receipts + shrink-only ratchet + deterministic cap). factory-and-multi-agent.md gained "Mapping flow-next onto the ladder" (Tier 1 fresh-context workers, recursive planner/worker split, pilot+land as a Tier 2 two-agent fleet, Ralph as the seatbelted long-running harness; durable-artifact coordination and rung-invariant quality spine as the transferable lessons). code-factory-onboarding.html fully regenerated from ~/work/code-factory-package source at flow-next 2.20.0 (was pinned 2.4.0; spec/03 narrative refreshed to July 2026 with three headlines and current also-recent list, four-tracker text kept verbatim; committed there as code-factory-package@618c167, gf overlay provenance stamped, 27/27 smoke tests green, shd.html test-run side effect restored to committed bytes). Boundary greps clean on all touched files (word-boundary client-names; zero new PSVI in the diff).
## Evidence
- Commits: AI-x-SDLC-Starter-Kit@993eca3d0f9bfdc31baab094e7c9db30da00b941, code-factory-package@618c167a8c22fe6da9f2c9010a1ea187d4c1edb8
- Tests: baseline: none in guide repo (no test/lint tooling; markdown + prebuilt HTML) - boundary greps ran pre-edit: client-names clean on all touched files (word-boundary; sole -i hit = 'shD' substring inside 'pushDefault', false positive), PSVI hits pre-existing only (GF's own publicly disclosed patent-noted methodology in guide measurement content incl. onboarding.html - inherited, sanctioned framing, not this task's diff), bun scripts/test.mjs in ~/work/code-factory-package (suite_rc=0, 27 passed 0 failed; log captured), bun scripts/render gf + render --check gf (OK: self-contained, under 2MB, spec/ portco-agnostic; provenance stamped 2.20.0/2026-07-20), post-edit: grep -riwf ~/.claude/flow-next-client-names.txt over all 7 touched guide files -> clean; git diff added lines contain zero PSVI/Velocity Index; spec-level boundary gate (flow-next.dev/src + mickel.tech/app/apps/flow-next + README.md + plugins/flow-next/docs) -> clean, onboarding.html verification: flow-next 2.20.0 x2, zero 2.4.0/2.8.1 remnants, four-tracker sentence present x2, bundled copy path refs verified (guides/flow-next.md L116 + README.md L32), GATE_SKIPPED:unittest:docs-only - flowctl gate classify --base 583347fb -> TIER_B docs-only in flow-next repo (task-tracking files only; all content changes live in the two external repos above); docs-site/microsite Quick-command builds not run (neither repo touched by this task)
- PRs: