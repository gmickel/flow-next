---
satisfies: [R2, R10, R12]
---
# fn-130-reached-path-skill-prompt-optimization.12 Gate Pilot backlog-only branches

## Description
Apply one conservative Pilot cold-branch extraction: move only backlog-only grammar/context behind the selected backlog route. Preserve verdict, strike, safety, receipt, failure, tracker, and autonomous conductor semantics at every consuming action site.

**Size:** S
**Files:** `plugins/flow-next/skills/flow-next-pilot/**`; existing Pilot optimization assets/tests; `optimization/reached-path/pilot-*`; corresponding Codex mirror.

### Approach
- Verify task input hashes match `V1/B1`; compare candidates only against `B1`.
- Move only backlog-only grammar/context into a direct reference selected by backlog mode.
- Keep common verdict/strike/safety instructions beside every phase that consumes them.
- Score the mutation independently; retain the candidate as a discard if any frozen grammar or terminal behavior changes.
- Recheck dormant fn-61 before edits; its verdict changes take precedence.

### Frozen fixtures
- ready normal; no-ready; backlog off; backlog on; blocked; deferred; strike escalation; failure; dry-run; tracker relations; autonomous restrictions.

### Investigation targets
**Required**
- `plugins/flow-next/skills/flow-next-pilot/SKILL.md:110-189` — backlog/verdict contract.
- `plugins/flow-next/tests/test_pilot_backlog_mirror_safety.py:84-390` — canonical/mirror safety matrix.
- fn-85 frozen Pilot conductor grammar.

**Optional**
- fn-61 Pilot/Land spec for overlapping files/semantics.

## Acceptance
- [ ] Task input hashes match `V1/B1`; Pilot has an independent `B1`/candidate ledger and every candidate can be kept or discarded without affecting Strategy or Make PR.
- [ ] Normal paths avoid backlog-only material; backlog paths retain complete selected backlog instructions.
- [ ] Verdict, strike, relation, receipt, dry-run, failure, tracker, and autonomous safety behavior match `B1` at all consuming action sites.
- [ ] Existing and new route assertions pass on canonical and Codex mirror; fn-61 status is rechecked.
- [ ] Reached-path improvement and every discard reason are recorded without claiming unmeasured wall-time gains.

## Done summary
Gated Pilot's backlog-only `ASKED` / diagnostic `TRIAGED` grammar behind the strict backlog route while leaving the B1 workflow and QA reference byte-identical. Added an independent hash-addressed Pilot candidate ledger and route/metric assertions: ready reached path improves from 63,302 to 61,293 characters (-2,009; -3.17%), with no wall-time or backend-token claim.

The canonical change is committed at `678da0eb8f95f0dfe0e0426afc04a560ccbb32a7`. The conductor owns combined Codex mirror regeneration, cross-host parity, review, integration, and lifecycle completion.
## Evidence
- Commits: 0a4400f7, ed9b6206, 63e9942e, 3e4e92ee, f3d1ff79, f7c85984, e901aa00, 1ab5bb3b, 0f08c608, c00dc797, c0142c0d, 97e9793a
- Tests: ./scripts/sync-codex.sh twice: 28 skills, 22 agents, idempotent, python3 scripts/run_tests_parallel.py: 2,286 run, 3 skipped, 0 failures/errors, bash plugins/flow-next/scripts/smoke_test.sh from /tmp: 136 passed, 0 failed, flow-next.dev build: Astro check 0 errors/warnings/hints; 74 pages built, git diff --check and changed-reference existence audit: passed, Prime authenticated Claude baseline and candidate: 7/7 each; 6/6 synthetic plus negative control
- PRs:
