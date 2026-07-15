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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
