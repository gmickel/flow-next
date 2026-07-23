---
satisfies: [R2, R3, R11, R12, R13, R14]
---
# fn-130-reached-path-skill-prompt-optimization.10 Close fleet evidence, mirrors, docs, and host smokes

## Description
Reconcile every independently kept/discarded mutation into one auditable fleet result. Run authoritative mirror generation, full tests, cross-host smokes, privacy/hash audits, and repo/site documentation truth checks. No version bump or release.

**Size:** M
**Files:** `agent_docs/{optimizing-skills.md,optimization-log.md,setup-modes.md}`, `CHANGELOG.md`, `README.md`, `plugins/flow-next/docs/**` only where behavior changed, `optimization/reached-path/**`, every changed `optimization/<skill>/**`, generated `plugins/flow-next/codex/**`, flow-next.dev install/setup/troubleshooting sources.

### Approach
- Rebase/recheck open overlaps fn-129, fn-122, fn-61, fn-73 and classify any conflict before the final gate.
- Verify immutable `B0`, version-adjusted `V1/B1`, and every structural task's input hashes/candidate lineage. Reject any structural comparison that used original `B0` instead of `B1`.
- Audit every result against the ratchet: baseline existed first, accuracy/negative controls held, source and telemetry metrics separated, discarded experiments retained.
- Produce a fleet table per cluster: `B0`, `V1/B1`, candidate reached-path chars/token-equivalent, real model cells, backend telemetry, kept/discarded mutations, host coverage, manual gates.
- Review all explicitly deferred skills and record no-op rationale; do not force a trim.
- Run `sync-codex.sh` twice on the combined canonical tree and review semantic transforms, not just byte generation.
- Smoke direct and natural-language activation on Claude; Codex mirror; Cursor CLI/GUI, Droid, and Grok where authenticated. Surface unavailable hosts as manual release gates.
- Build flow-next.dev and verify copy-mode/Plan-only wording matches repo docs. Public docs stay untouched for behavior-neutral moves after a truth scan.

### Investigation targets
**Required**
- `scripts/sync-codex.sh:212-235` — recursive skill/reference and shared-reference mirroring.
- `plugins/flow-next/tests/test_skill_prose_diet.py` — canonical/mirror structural invariants.
- `agent_docs/optimizing-skills.md:255-263` — promotion text that must match batched releases.
- `README.md:127-133`, `plugins/flow-next/docs/troubleshooting.md:5-14`, `agent_docs/setup-modes.md:31-39` — version truth surfaces.
- `/Users/gordon/work/flow-next.dev/src/content/docs/{install.mdx,skills/setup.mdx,reference/troubleshooting.mdx}` — downstream copy-mode guidance.

**Optional**
- `plugins/flow-next/docs/platforms.md` and public glossary — update only if observable host/term behavior changed.

## Acceptance
- [ ] Immutable `B0`, version-adjusted `V1/B1`, and every structural candidate's hash lineage are complete; no structural task compares directly to `B0` or starts from an unverified prompt tree.
- [ ] Every cluster ledger proves baseline-first, zero-loss ratchet, kept/discarded status, fixture hashes, privacy scrub, and measured reached-path change; no directory-size or cache-only token claim appears.
- [ ] Explicit deferral/no-op list covers every skill outside structural scope and cites prior ceiling/regression evidence.
- [ ] `scripts/sync-codex.sh` runs twice with an empty second diff; canonical/mirror semantic parity and relative reference paths pass focused tests.
- [ ] Claude direct and natural-language, Codex mirror, and authenticated Cursor/Droid/Grok smoke results are recorded; unavailable manual hosts remain visible release gates.
- [ ] Focused suites, `python3 scripts/run_tests_parallel.py`, plugin smoke, docs-site build/link checks, privacy grep, and changed-reference existence checks all pass.
- [ ] README/repo/site copy-mode guidance consistently describes Plan-only detection and rerunning Setup; behavior-neutral refactors cause no public-doc churn.
- [ ] `CHANGELOG.md` uses `## Unreleased`; no version manifest, tag, release, or deployment is changed.
- [ ] Final evidence table and rollback notes are complete enough for make-pr and later release review.

## Done summary
Closed fn-130's fleet evidence across all independent mutation clusters. Added
the B0→V1/B1→candidate result table, model/telemetry separation, kept/discarded
ledger, current-source Claude/Codex/Cursor/Droid/Grok activation smokes,
explicit Cursor-GUI/TUI pre-release manual gates, overlap/no-op recheck, docs
truth scan, and atomic rollback guidance. Regenerated the Codex mirror twice,
validated privacy and hash lineage, ran the full repository and plugin gates,
and built flow-next.dev. Temporary Grok/Droid test installations were removed;
no version manifest, release, deployment, live tracker, or downstream docs
source changed.
## Evidence
- Commits: 97e9793a93bcad8c2bf18bdb1b8d28d3ae80b2ff, dc1dfe1c
- Tests: python3 optimization/reached-path/run_eval.py --self-test, python3 optimization/reached-path/run_eval.py --validate-b0 (117 manifests), python3 optimization/reached-path/run_eval.py --validate-b1 (117 manifests), evidence privacy regex + candidate B1 lineage/hash audit, ./scripts/sync-codex.sh twice (28 skills, 22 agents, idempotent), focused prompt/parity suites, python3 scripts/run_tests_parallel.py (2,286 run, 3 skipped, 0 failures/errors), bash plugins/flow-next/scripts/smoke_test.sh from /tmp (136 passed, 0 failed), flow-next.dev pnpm build (Astro check clean, 74 pages), Claude direct + natural-language, Codex mirror, Cursor CLI, Droid, Grok current-source smokes, git diff --check + changed-reference existence + docs truth scan
- PRs: