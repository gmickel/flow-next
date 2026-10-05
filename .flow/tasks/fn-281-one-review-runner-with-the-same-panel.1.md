---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11]
---
# fn-281-one-review-runner-with-the-same-panel.1 Implement One review runner with the same panel on every backend

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Every CLI reviewer (codex, claude, copilot, cursor) now runs the first implementation-review round through one flowctl runner (`flowctl <backend> impl-review-fanout` / `-finalize`), sized by one panel rule stated once in the impl-review skill and applied by host too; the four CLI workflow files became `workflow-cli.md`. Also landed: stall check at record time over three rounds (R7), standing criteria on a one-task spec (R6), #513 range/model provenance (R11), host reads the routing block from CLAUDE.md or AGENTS.md (R8), changelog says `review.backend` stays (R9). flowctl.py net -19 lines; skill text net -268.

Decision (maintainer, 2026-10-05, spec commit 9f6fe1da): CLI reviewers, Copilot included, run a three-reviewer round concurrently; a refused call fails and does not vote. Back-to-back is only for a host that cannot dispatch three reviewer subagents at once. Build matches: no serial path in flowctl, and the only back-to-back wording left in skills/docs is the host fallback (workflow-host.md, orchestration.md).

Surfaces swept: flowctl.py review code (registry, fan-out runner, parser, record/increment, stall, review-route, prompt builder), impl-review SKILL.md / other-paths.md / workflow-cli.md (merged from workflow-codex/claude/copilot/cursor) / workflow-host.md / optional-phases.md / references fix-pass.md (renamed from codex-fix-pass.md) and fix-loop.md; plan-review and spec-completion-review workflow-host.md (routing file, --model); docs flowctl.md, orchestration.md, running-lean.md, review-findings.md, troubleshooting.md; agent_docs conduct/impl-review.md and review-architecture.md; CHANGELOG; tests; regenerated Codex mirror and tracker manifest. Unchanged and checked: worker.md, work/flow skills, commands, setup (Cursor-only AGENTS.md mentions are correct there), templates/usage.md (Cursor section), install scripts (skill dirs are replaced wholesale, so removed workflow files leave cleanly), scripts/flowctl-help.txt (top-level help unchanged under python3.14).

Review fixes from round 1 (all four findings fixed): stale non-codex refund recorded as codex; serial Copilot draws overran the foreground call and claim; branch fan-out required a .flow/ project (regression for claude/copilot/cursor); a restarted coordinator after a stall started another fix pass (review-route now stops with reason `stalled` until a new commit).

Measurements (R4, live, scratch repos, Claude Code coordinator over the 8.0 plugin dir): small one-line bug -> one reviewer, larger persisted/concurrent change -> three reviewers, every path reached a verdict: codex 1/SHIP and 3/NEEDS_WORK, claude 1/SHIP and 3/NEEDS_WORK, cursor 1/SHIP and 3/NEEDS_WORK, host 1/SHIP and 3/NEEDS_WORK (host read the CLAUDE.md routing block; attempt rows carry base_sha, head_sha_observed true, model). Copilot: inconclusive, every call refused with "You've reached your additional usage limit for your plan. Go to https://github.com/settings/copilot/features for more details."

Measurements (R10, fn-271 harness, same-load pairs 7.1.2 tag vs c5b2b00c, 3 draws each): hidden checks pass on all 24 draws.
- Case 2 attended (branch review, no spec): judge 19.3 vs 18.7 mean; first handoff median 253 vs 233 s; wall median 601 vs 656 s; cost median $2.31 vs $2.11. Level.
- Case 4 attended: judge 18.3 vs 18.3; first handoff median 599 vs 594 s; wall median 1368 vs 2230 s, cost $5.66 vs $7.57. The gap is the simulated person: all three 8.0 people asked for the full suite after hand-back (one also had the frozen ask fixture refreshed), against one of three on 7.1.2.
- Case 4 --auto: 8.0 better: judge 19.0 vs 18.0, wall median 966 vs 1256 s, cost $5.56 vs $6.13.
- Case 2 --auto (single-task spec with active criteria G1-G7, the R6 case): judge 18.2 vs 17.2 mean, wall median 1003 vs 1184 s, cost $4.93 vs $6.11. Mechanism: on 8.0 every reviewer judged G1-G7 and flagged G7 (behavior change needs docs + ADR) in all three draws, and each run then wrote an ADR and architecture docs; 7.1.2 never checked the criteria on this route. The judge drop is one 8.0 draw (14/14) whose design kept a large crash-loss window (the deferred-flush pitfall seen on this case in earlier rounds), not tied to the change (inferred). The +$1.2 / +3 min is R6 working as specified; whether that cost is acceptable is the maintainer's call.

Follow-ups (not part of this task): a reviewer `File:Line` with a trailing parenthetical (`store.py:18-25 (with store.py:12-13)`) fails the anchor parser, so `--merge-plan` refuses the round until the coordinator uses `--merged-file` (seen once in a claude draw; pre-existing, any backend). Release work for R9: correct downstream notes that announced `review.backend` removal. The fn-168 decision record under .flow/memory still describes the two-round stall rule.

Commits: 6102845e (feature), c5b2b00c (review fixes), b1db520d (review ledger state); spec amendment 9f6fe1da is the maintainer's.

stage: impl-review - ran (codex gpt-6-astra: round 1 three reviewers NEEDS_WORK, 4 findings fixed; re-review NEEDS_WORK on the old R1; re-review against the amended spec SHIP)
stage: implement - ran (model: session; delegated: 0)
Tier: session (jev intelligent 0.84)

stage: plan-sync - skipped(config: planSync.enabled != true)
- Follow-ups (maintainer-requested, 2026-10-05): case 2 --auto rerun with the case repo's standing criteria dropped (harness default since bb1217c), 3 same-load pairs 7.1.2 vs c5b2b00c (rounds fn281-c2auto-{C,D,E}{a,b}-1005): hidden 3/3 vs 3/3; judge mean 17.7 vs 18.2; wall 1369/1124/1191 s vs 962/1269/1159 s (median 1191 vs 1159); cost $6.89/$6.76/$6.12 vs $5.66/$6.86/$5.95 (median $6.76 vs $5.95). No regression: the earlier case-2 --auto gap was the criteria (R6 judging G7). Copilot live check once quota returned: one-draw round SHIP in 32 s; three concurrent draws NEEDS_WORK x3 in 93 s total (draws 73/90/93 s), gpt-6-astra, 4 Copilot requests.

## Evidence
- Commits: 6102845e03dc12e5ebe089da79e1951b32e03b44, c5b2b00c4ba0bd7515421ec890c19ca1f2de25b0, b1db520dce618652243ee855c4ae5a2a75d33fef, 9f6fe1da77b7b7be26ba243a428f131b1332126f, 9c6a80319dbe8b97bca0acf4b54c5ae0ad1710c2
- Tests: python3 scripts/run_tests_parallel.py (full suite: 3938 tests, 0 failures), bash scripts/sync-codex.sh --check, python3 scripts/check_doc_anchors.py, uvx ruff@0.16.0 check .
- PRs: