---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-237-optional-task-decomposition-and.1 Implement optional decomposition and downstream guidance

## Description
Implement the complete parent spec as one owner. Core routing, CLI lifecycle, documentation and generated consumers share one acceptance contract; maintainer downstream properties are verified separately so private material does not enter this public repository.

Implementation is committed and core gates are green. The conductor completed the following downstream verification on 2026-09-10:
- Public documentation site: build, four tests, internal links, SEO, 85 HTTP exports and browser checks passed; current pipeline headings and examples mark decomposition optional.
- Methodology/onboarding package: six isolated renders and 29 tests passed, introduced links and HTML anchors checked, representative browser inspection passed.
- Methodology guide: current guidance updated, native Plan Mode distinguished from task decomposition, introduced links checked, bundled onboarding render byte parity verified.
- Product page: production build, lint and desktop/mobile browser checks passed.
- Canonical knowledge: 14 existing notes/indexes/logs updated, new links resolved, collection indexing and collection audit passed; title and route claim retrieved.

Downstream source changes are locally committed; knowledge files are saved and indexed. No push, deployment, version bump or release is claimed. Private downstream receipts are retained outside this public repository and are not inputs for the core reviewer. R7 implementation and verification are conductor-owned; publication state remains explicit.
## Acceptance
Every R-ID in the parent spec's Acceptance Criteria is satisfied; judge this owner task against the complete spec.

## Done summary
Implemented optional task decomposition across the core workflow and maintainer downstream documentation. Ready cohesive specs execute through Flow-Next work --no-plan; accepted intent persists before guarded owner creation. Explicit planning clears old direct intent. Pilot and work preserve that owner, require matching ownership and positive ended-run evidence for resume, and retain spec-level completion policy. next reports taskless direct work truthfully, and legacy Ralph refuses taskless dispatch while accepting existing executable owners subject to its configured review gates.

The full spec remains the acceptance contract. Current guide/capture/interview/work/pilot guidance, pipeline variants, README, glossary, strategy, references, transforms and Codex mirrors align. Public benchmark wording is qualitative and contains no private study details. G1: added prose explains required route/ownership behavior; G2: regression coverage exercises CLI lifecycle and the actual Bash guard, with a bounded prompt replay for resume rather than duplicated routing logic or prose sentence pins.

Configured implementation review reached SHIP after one corrected resume finding. Both supplemental audit findings were addressed. Independent reviewer checks were source-based due its read-only sandbox; full runtime unit checks and the bounded routing replay were executed separately. No full live pilot-resume run or public deployment is claimed.

Maintainer downstream checks passed: documentation-site build/tests/links/SEO, 85 HTTP exports and browser inspection; six isolated onboarding renders, 29 package tests and bundled-artifact parity; methodology links; product-page build/lint and desktop/mobile inspection; maintained knowledge links, indexing/retrieval and collection audit. The private downstream checklist now shares the spec-first claim. Source changes are locally committed across all affected repositories; 14 knowledge files are saved and indexed. Publication is separate and has not occurred.

stage: wave-dispatch - ran
stage: plan-sync - skipped(config: disabled)
stage: impl-review - ran [2026-09-10T14:56:11Z..2026-09-10T15:09:46Z] (model: gpt-6-astra)
stage: QA - skipped(config: pipeline.qa=off; property-specific browser checks ran)
## Evidence
- Commits: 86533928c78b0c398015391c3f12eeaf82756546, 90c9b70d167573fd02664c82227e94fc5f38fdbc, 87eb1ad875ae0bd88ea43fe771a6b6fc01f6d599
- Tests: TMPDIR=/var/tmp python3 scripts/run_tests_parallel.py: 209 files, 4841 tests, zero failures/errors, six skips; final source 87eb1ad8, uvx ruff@0.16.0 check .: passed, python3 scripts/check_doc_anchors.py: passed, ./scripts/sync-codex.sh twice: passed and byte-idempotent; manifest regenerated, Installed consumer checks passed: Codex 11, OpenCode 16, Cursor parity 7, Cursor verifier 6, Focused CLI lifecycle and actual Ralph taskless guard passed; seven-case bounded routing replay verifies direct-owner resume and preserved ownership/review boundaries, Configured implementation re-review: SHIP on 87eb1ad8; prior finding fixed, no unaddressed R-IDs, Documentation site: build, 4 tests, links, SEO, 85 HTTP exports and browser checks passed, Onboarding: six isolated renders, 29 tests, introduced links/anchors and representative browser checks passed; bundled render parity verified, Methodology: current route guidance and native Plan Mode distinction checked; introduced links valid, Product page: production build, lint and desktop/mobile browser checks passed, Maintainer guidance: shell syntax, 3 unit tests and diff checks passed, Knowledge: 14 saved files, introduced links resolved, collection index/retrieval and collection audit passed
- PRs: