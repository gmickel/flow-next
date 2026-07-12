---
satisfies: [R1, R2, R15]
---

## Description
SKILL.md rewrite + workflow.md Phase 0.5/0.6 (classification + ask protocol + args).

**Size:** M | **Files:** `plugins/flow-next/skills/flow-next-prime/SKILL.md`, `plugins/flow-next/skills/flow-next-prime/workflow.md` (Phases 0.5/0.6 insertion + Phase 1 dispatch contract line)

## Approach
- SKILL.md: `--classify-only` in args (L48-67, ROOT threading extends to probes); phase list gains 0.5/0.6 (L89-101); two-tier table (L31-36) + description line reference pillars.md census instead of hardcoding counts; maturity table demoted under the verdict headline (L103-118 keeps pillars.md-single-source); "Why This Matters" (L38-46) reframed to layered gates (drops the pre-commit-hook praise, resolution 15); guardrails gain the --fix-all boundary rules (resolutions 5/6: outside-ROOT, harness files, structural artifacts = explicit consent; greenfield = exercised hygiene only).
- workflow.md Phase 0.5: host-inline classification per classification.md (reference, do not restate mechanics - one-line-pointer memory rule); low-confidence interactive confirm; Phase 0.6: R15 ask protocol with the SCOPED budget (resolution 4 - excludes Phase 5/5.5/fn-95 asks; all suppress under classify-only/report-only/autonomous), Repo-context recording offer; Phase 7 re-run reuse rule (resolution 6).
- Phase 1 dispatch contract (L13) gains the per-scout classification context line.

## Key context
- NEVER name the ask-tool in autonomous-branch prose (memory R2 rule); keep the existing Phase 5 consent sentence (L253) byte-identical (sync-codex anchor).
- Every fenced block re-declares its vars; verify flowctl invocations against the real emitter.

## Acceptance
- [ ] --classify-only implemented as arg + early-exit printing the classification.md schema; cheap on huge repos (R2)
- [ ] Phase 0.5 classifies five axes with evidence + confidence, referencing classification.md; low-confidence confirm interactive-only (R1)
- [ ] Phase 0.6 ask budget scoped per resolution 4; Repo-context recording offered; non-interactive = assumptions + Unresolved questions section (R15)
- [ ] SKILL.md two-tier/census/maturity/why-this-matters/guardrails updated; no hardcoded criteria counts left in SKILL.md
- [ ] Sync-codex anchor sentences untouched (diff-check); autonomous prose names no ask tool

## Done summary
Rewrote the prime SKILL.md and inserted workflow.md Phase 0.5 (host-inline five-axis classification via the `flowctl prime classify` emitter + judgment layer, low-confidence interactive confirm, `--classify-only` early exit) and Phase 0.6 (the R15 bounded ask protocol with the scoped budget, suppression under classify-only/report-only/autonomous, Repo-context recording offer, Phase 7 re-run reuse). SKILL.md gains the `--classify-only` arg with ROOT threading, the 0.5/0.6 phase entries, a pillars.md census reference replacing all hardcoded criteria counts, the four reference-file links, the maturity table demoted under the verdict headline, a layered-gates "Why This Matters" reframe, and the `--fix-all` boundary + re-run rules. Phase 1 dispatch contract gains the per-scout classification context sentence. Sync-codex anchors kept byte-identical; Codex mirror regenerated; new prose uses plain hyphens.
## Evidence
- Commits: 6328ea0de2426abe7a924ae055e1b462498d27ac
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' (1615 tests, OK, skipped=2), python3 -m unittest ... test_prime_eval.py (34 tests, OK) - baseline green pre-edit, bash scripts/sync-codex.sh (all validation guards pass; mirror regenerated)
- PRs: