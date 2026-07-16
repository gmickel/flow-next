# fn-99-setup-block-diet-evidence-schema-inline.4 Post-trim eval gate, restoration loop, changelogs + docs-site staging

## Description
Gate + staging: post-trim eval, restoration loop, changelogs, docs-site. Satisfies R4 (gate half), R6, R7. Depends on .2 (harness + baseline) and .3 (trimmed content).

Scope:
1. EVAL GATE (R4): run the task-2 harness on the trimmed docs - full R13 matrix (both scenarios; minimal + full-block arms; sonnet + terra + haiku; 3 reps on discriminating cells). Gate = no regression vs the task-2 baseline on ANY graded dimension. On regression: restore the implicated content in a follow-up commit to task .3's surface, re-run the gate; never ship a regressed trim. Record post-trim ledger rows.
2. CHANGELOG Unreleased entry with before/after token counts (block + usage.md, chars/4) (R6).
3. Docs-site staging (R7): changelog entry per releasing.md format; review skills/setup.mdx (content description currency), flowctl/cli-reference.mdx lines 19/69 + skills/flow-next.mdx:29 (add the evidence schema example where --evidence-json is shown bare); verify orchestration/index.mdx's usage.md section anchor survived; `pnpm build` green; commit in the docs-site repo (push per maintainer handoff convention).
4. Full repo gate: unit + smoke green.
## Acceptance
- Post-trim ledger complete; no regression vs baseline on any dimension incl. haiku floor; any restoration documented (R4).
- CHANGELOG entry with before/after token counts (R6).
- Docs-site: changelog staged, bare --evidence-json mentions now show the schema, anchors verified, build green (R7).
- Unit + smoke green.
## Done summary
Ran the post-trim guidance-eval gate (full 28-run R13 matrix on the fn-99.3-trimmed docs): minimal arm 14/14 with the haiku floor intact - no regression on any graded dimension, so the usage.md trim ships; the amended full block scored 12/14 vs the 9/14 baseline (no cell regressed; sonnet multitask 1/3->3/3, haiku slugify 0/3->1/3, residual is a strictly-softer task-granularity artifact: intermediate micro-tasks done with empty evidence while the final commit task records the real sha). No restoration needed. Post-trim ledger rows ("post-usage-trim + block-evidence-amendment", 2026-07-16, codex-cli 0.144.1 gpt-5.6-terra med / claude 2.1.210 sonnet+haiku) recorded in the harness README; grade.py fixed to merge multi-line shim records (a multi-line --text arg crashed the old line-per-record parse) and all 28 runs re-graded from retained run dirs.

CHANGELOG Unreleased entry with before/after token counts (block 575->249 tok-equiv, usage.md 5392->1928) staged; docs-site (~/work/flow-next.dev, committed locally, not pushed): Unreleased changelog entry, evidence-JSON schema added at the bare --evidence-json sites (cli-reference.mdx x2, skills/flow-next.mdx), "read every session" corrected to read-on-demand in orchestration/index.mdx, pristine-upgrade currency line in skills/setup.mdx; pnpm build green. Full repo gate green (unit + smoke). Codex impl-review (gpt-5.5): NEEDS_WORK r1 (Unreleased insert dropped the 2.14.0 heading - restored) -> SHIP r2.
## Evidence
- Commits: 9dfecbedce4eca0b3eec3aca0936c8663ccb16ed, b33426d5cb8b32128a6dc2e229b4555ce88e626e
- Tests: python3 -m unittest discover -s tests (1786 tests OK, skipped=2; baseline green pre-edit and green post-edit), bash plugins/flow-next/scripts/smoke_test.sh from /private/tmp (144/144, baseline and post-edit), guidance-eval post-trim gate: 28-run R13 matrix (slugify+multitask x minimal+full x sonnet/haiku/gpt-5.6-terra-med, 3 reps Claude cells) - minimal arm 14/14 (no regression, haiku floor holds), amended full block 12/14 vs 9/14 baseline (no cell regressed; sonnet multitask 1/3->3/3, haiku slugify 0/3->1/3); ledger rows recorded in agent_docs/guidance-eval/README.md, pnpm build in ~/work/flow-next.dev (65 pages, green)
- PRs: