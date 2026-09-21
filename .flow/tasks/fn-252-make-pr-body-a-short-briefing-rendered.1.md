---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11]
---
# fn-252-make-pr-body-a-short-briefing-rendered.1 Implement make-pr body: a short briefing rendered from the aid artifact

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
flowctl now renders one briefing of at most 40 lines from the aid artifact for every pull-request size, and the make-pr skill delivers that briefing after the spec-close commit. R1 to R10 are implemented and the changelog half of R11 is done; R11's timed measurement is the conductor's and was not run.

Tier: implementer = gpt-6-astra at medium (explicit invocation; reached over the codex CLI bridge)

stage: implement - ran (model: gpt-6-astra at medium, codex exec --sandbox workspace-write, 3 runs in this continuation after 2 earlier; delegated: 3)
stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)

What changed, by requirement:
- R7 (reworked to the 2026-09-21 decision): `unverifiedSteps` is removed with its tests and doc. `changeWalkthrough` accepts optional strings `userImpact`, `blastRadius`, `tradeoffs`, `openItems`; each proof cell accepts optional `outcome` (pass, fail, unverified), and any other value is rejected naming the cell. Schema version 1, path unchanged. Tests: `plugins/flow-next/tests/test_pr_cognitive_aid_authored_fields.py`.
- R1 to R6, R8: `render_pr_cognitive_aid_markdown` is one form. The inline threshold (`>= 200` review lines or `>= 6` canonical files) and the compact and full forms are deleted. Tests, one per criterion and error case: `plugins/flow-next/tests/test_pr_cognitive_aid_briefing.py`. The HTML lens and `html-input` are unchanged.
- R9, R10: make-pr skill text cut; the artifact is composed after the close commit; a failed close stops before export. The land redesign spec already states the ordering (fn-250 R2), so it was not edited.
- R11: `CHANGELOG.md` `## Unreleased` credits @flecamos for #447. Measurement not run; `.flow/artifacts/fn-249-make-pr-measurement/` is untouched and not ignored (`git check-ignore` rc=1).

Worker edits on top of the child's renderer (range check, not a verdict): Scope groups are numbered and the coverage line cites the numbers, because the child's line repeated full group titles per requirement (the real sample's coverage line ran to about 600 characters); outcome-less proof cells render as plain `- ` items, because bare consecutive lines merge into one paragraph on a forge; counted lines pluralize; the last tree row closes with `└──`. Also restored the `Reviewer feedback → /flow-next:resolve-pr <number>` hint the child had dropped, and removed a token the tracker caller oracle forbids.

Instruction lines an ordinary run loads (HTML lens reference excluded), before at b831c033 and after:
- SKILL.md 137 to 35; workflow.md 1,360 to 282; pr-cognitive-aid.md 143 to 69; create-and-finalize.md 774 to 211; mermaid-rules.md 346 to deleted; references/live-qa-section.md 90 to deleted; docs/prose.md 67 to no longer loaded. Total 2,917 to 597.
- Not counted because no run reads them: phases.md (6-line link stub) and references/manual-smoke.md (maintainer checklist).
- Deleted: the hand-assembled body-section recipes (title block, TL;DR, R-ID coverage table and ratio, verification, critical changes, review plan, memory, glossary and strategy notes, footer), compact and full selection guidance, truncation and spill instructions, the Mermaid rules file, the live-QA section reference, the absolute-https link rule, and the marker comment emitters. 597 is three lines under the bound.

Renderer lines in flowctl.py: 175 deleted and 168 added across the two renderer commits (a98da806..HEAD); functions removed: `_pr_aid_markdown_cell`, `_pr_aid_links`, `_pr_aid_file_row`.

Samples (in gitignored `.flow/tmp`, regenerate with `python3 .flow/tmp/fn-252.1-render-samples.py`):
- Real stored artifact `.flow/artifacts/fn-185-memory-yaml-round-trip-mid-string-hash/pr-cognitive-aid/fn-185-aid-30e1bfb5.json`: 30 lines, `.flow/tmp/fn-252.1-sample-real.md`. It predates outcomes, so its four proof cells render as plain items with no ticks.
- New-style fixture with all seven sections: 35 lines, `.flow/tmp/fn-252.1-sample-full.md`.

R5 marker comment: no reader remains after the land redesign. Searched skills, flowctl, scripts, tests and agent_docs for `flow-next:make-pr spec=`; the only hits are a released changelog section and the fn-152 spec text. The emitters in SKILL.md and workflow.md are removed and `agent_docs/conduct/make-pr.md` says so.

Spot-checks of the settled findings: the coverage line renders from `rid` sources alone (test `test_uncovered_and_undeclared_requirements_have_table`); the threshold was inline renderer logic, so no retired-config work was done.

Field feedback folded into the skill text: `files` required on every group even when empty; explicit `--base <branch>` resolves against `origin/<branch>` (new fixture test `test_explicit_base_uses_remote_tracking_when_local_branch_is_stale`); required "recorded in the PR" findings go to Open items or Tradeoffs; the absolute-link rule is gone; empty-summary rows land in the counted "not described" line.

Follow-ups, not built:
- The body no longer distinguishes "claimed, not yet evidenced" from "undeclared", and no longer marks orphaned evidence SHAs (fn-180). Both remain in `spec export-cognitive-aid`; the briefing's coverage is what the artifact's groups cite. The tests that pinned those body strings were deleted with that rationale.
- When the whole Scope collapses to one counted line (thesis near or over the budget), the coverage line's group numbers have no visible group to point at.
- `scripts/sync-codex.sh` lost two closer-literal rules and roster rows whose canonical sentences no longer exist.

Gates at HEAD 4eae94f9:
- GATE_SKIPPED:unittest:green-receipt 78157205 - baseline reused from prior post-gate pass
- `python3 scripts/run_tests_parallel.py`: suite_rc=0, 4973 ran, 0 failures, 6 skipped; green receipt written.
- `uvx ruff@0.16.0 check .`: rc=0.
- `bash scripts/make-pr_smoke_test.sh`: rc=0, 63 pass.
- `bash scripts/smoke_test.sh`: rc=1, 132 pass, 1 fail, which is only `copilot plan-review re-review ... NOT_RETRYABLE: artifact unchanged since last verdict`, the known local-environment case.
- `./scripts/sync-codex.sh` twice, second run a no-op; tracker manifest regenerated.

Every child commit was denied by the sandbox as expected; the worker committed each tree. No command is still running.

### Host review (4 rounds, SHIP)

Round 1 (three draws) found 13 issues, chiefly the collapse order and a thesis reflow that hid fail cells
and open items. Rounds 2 and 3 found a collapse step that cost a line and a 40-line bound that broke for
mixed proof outcomes. Final renderer: ordered steps applied only when they shorten the body, then one
shared proof pass; bound holds at 39 lines worst case, 10,000-body sweep clean. `--no-mermaid` removed.
Ordinary make-pr run loads 596 instruction lines. Gates at 529e5ffc: 4,998 tests, ruff, anchors, smokes.
## Evidence
- Commits: 82901879c9beb18e9c155c8ab6fe2c8a8b163f94, 7815720500efeeda7ae51456e8945fa1bf107403, 5a09be18cee4e6e9fd95cfc69cff3a392a6a482a, a98da8068a4d79f1bbdb9dfeb1c000964cc70bee, bb80bc8b6444036bcd65c75fd4052f6bc4f65038, 861349a9a3977bcc80f21c872f45398613eb5442, 55c014333ded1dcf93dd2db0e9af697bf49391f4, cbfd0c29d310427f0f9e4faf922e0419b8f6c8f2, 4eae94f9da6ad62262bb42742abce116713a0cd7, 4bb2a8b81269f1d38344c10efbabfe3c2b19241d, 13bc759317f87a1aaedbc0c8dbd9e77d7090b917, 4070c45dbdd0793d29650a3b83f49096a5de5a3f, d0f06f2f1055573c30f36df98d4343bb88b05675, 529e5ffcae2e5ef10f31d09ea68f0b01d38bbc93
- Tests: python3 scripts/run_tests_parallel.py (4998 tests, rc 0), uvx ruff@0.16.0 check . (rc 0), python3 scripts/check_doc_anchors.py (rc 0), plugins/flow-next/scripts/make-pr_smoke_test.sh (63 pass, rc 0), plugins/flow-next/scripts/smoke_test.sh (132 pass, 1 known local failure: live copilot re-review), ./scripts/sync-codex.sh twice, second a no-op
- PRs: