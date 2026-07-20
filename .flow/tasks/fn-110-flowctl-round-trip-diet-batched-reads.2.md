---
satisfies: [R3, R4, R5, R6, R7, R7b]
---

## Description

The skill-prose half: consume the snapshot plumbing, consolidate fences, and pin every invariant with durable structural tests.

**Size:** L
**Files:** plugins/flow-next/skills/flow-next-land/workflow.md, flow-next-plan/steps.md (+SKILL.md if reads move), flow-next-pilot/SKILL.md+workflow.md+references/backlog-mode.md, flow-next-make-pr/workflow.md, flow-next-impl-review/SKILL.md, flow-next-plan-review/SKILL.md+workflow.md, plugins/flow-next/tests/test_skill_prose_diet.py (new), plugins/flow-next/codex/ (regenerated mirror)

## Approach

Per the spec Approach items 3-4, with these hard rules:
- land: cfg() -> one `config get land --json` capture + jq lookups; preserve the null-tolerant defaults EXACTLY (the CLEAN_REVIEW_PATTERN ""-vs-null contract is subtle).
- plan: one root snapshot early (<=2 reads total only if sync-gating order forces a late leaf); `spec create --branch`; `task create --description-file --acceptance-file --satisfies` = ONE call per task, zero set-spec on the plan path (set-spec stays for later edits).
- pilot: RE-SCOUT FIRST (structure changed since fn-101). SKILL.md is the snapshot OWNER (mode detection resolves PILOT_AUTONOMY from config before workflow.md loads): capture the root snapshot there, derive/export PILOT_AUTONOMY; workflow.md and references/backlog-mode.md derive gateClasses/pipeline.qa from the captured snapshot. EXACTLY ONE config call across all three pilot files, located in SKILL.md. Never inline backlog-mode.md.
- make-pr: Phase 0 -> <=3 read fences, §0.5 tasks-done semantics intact.
- impl-review: 3 arg-parse fences -> 1.
- plan-review: single-source the per-backend block. Byte-preserve the Foreground rule + the deterministic-cap sentence; stale agent-counter prose MAY be removed (fn-90 moved the cap to flowctl) - the invariant is no agent-side counting reintroduced.
- Structural tests (test_skill_prose_diet.py): assert on the markdown - land Phase 0 has exactly 1 config-get; plan has no set-branch/set-spec on the create path; impl-review has 1 `for arg in $ARGUMENTS` fence; plan-review backend block in exactly one file; backlog-mode.md has zero flowctl config calls; protected prose byte-exact. Plus the committed before/after 4-task all-frontmatter plan fixture with invocation counts.
- sync-codex.sh TWICE, mirror committed; portable-host clauses for anything Claude-only.

## Investigation targets

**Required:**
- The exact JSON shapes .1 shipped (read its tests first)
- pilot SKILL.md + workflow.md + references/backlog-mode.md CURRENT structure (fresh scout; fn-101 anchors stale)
- land/workflow.md:53-72 cfg() + all its consumers

## Acceptance

- [ ] land Phase 0: exactly 1 config invocation (R3)
- [ ] plan fixture: >=40% fewer flowctl invocations on the standard 4-task all-frontmatter plan, fixture committed (R4)
- [ ] pilot: exactly 1 config call across SKILL.md/workflow.md/backlog-mode.md, located in SKILL.md; re-scout summary in evidence (R5)
- [ ] make-pr <=3 fences; impl-review 1 arg fence; plan-review single-sourced; protected prose byte-exact, stale counter prose removed if found (R6)
- [ ] test_skill_prose_diet.py green and pinning every invariant above (R7b)
- [ ] sync-codex x2 idempotent, mirror committed; smoke + unittest green (R7)

## Done summary
Skill callsite round-trip diet across 6 hot skills: land Phase 0 = 1 config-get subtree capture (was 7), plan = 1 root snapshot + one-call task create (fixture 20->12 invocations, 40%), pilot = exactly 1 config call (SKILL.md-owned TMPDIR snapshot; symlink-safe, dry-run-clean), make-pr Phase 0 = 3 fences with NEED_INPUT ask exemption, impl-review = 1 arg fence, plan-review backend blocks single-sourced as atomic dispatch fences (Foreground rule + fn-90 cap sentence byte-preserved, stale agent-counter prose removed). Pilot re-scout: 4 config fences found (SKILL:114, workflow:260/306, backlog-mode:384), no repeated-show dup remained. test_skill_prose_diet.py (14 tests) pins every invariant on canonical + codex mirror. Codex impl-review: SHIP after 3 fix rounds (symlink/dry-run/var-atomicity/fix-loop-ownership regressions fixed).
## Evidence
- Commits: 29d728fae8e522bdeaf738e32478fe2ee8e71e2e, e66c2e938822f4ee24e3b1d18673bf818a1a4247, 4294a7845b84fdbb9e0dc86b020ac122d21dc77a, 2bb41aca84e873ce3e31f261c9d51979d0d50306
- Tests: baseline: green via receipts - GATE_SKIPPED:unittest:green-receipt 85954cb2 - baseline reused from prior post-gate pass, GATE_SKIPPED:smoke:green-receipt 85954cb2 - baseline reused from prior post-gate pass (baseline only; final gates ran full), python3 -m unittest discover -s plugins/flow-next/tests -q (1944 tests OK, receipts 2bb41aca), (cd $(mktemp -d) && bash .../plugins/flow-next/scripts/smoke_test.sh) (142 passed, 0 failed), ./scripts/sync-codex.sh x2 (idempotent, rc=0), cmp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py (dual-copy parity)
- PRs: