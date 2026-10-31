---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10]
---
# fn-307-dead-stale-and-duplicated-instruction.1 Implement Dead, stale and duplicated instruction text (audit 2026-10 wave 1)

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Wave 1 of the 2026-10 audit: dead, stale and duplicated instruction text removed or corrected across flow, work, the review skills, resolve-pr, QA, drive, tracker-sync, prime, audit, memory-migrate, map, features, capture, plan, refine, chart, prospect and strategy (R1-R10), plus the prime scout-dispatch Codex rewrite (R2) and zsh-safe argument loops in resolve-pr and QA (R3). No behaviour change; 91 source files, about 180 lines added and 800 removed outside the regenerated mirror.

Tier: session (jev intelligent 0.59) at default effort (model: claude-opus-5-5)

Verification (measured):
- Baseline before edits: full suite green (4067 tests), Ruff clean.
- Final: `python3 scripts/run_tests_parallel.py` green (219 files, 4070 tests, 0 failures); `uvx ruff@0.16.0 check .` clean; `./scripts/sync-codex.sh --check` clean after regeneration; test_shipped_links, test_flowctl_surface and test_skill_prose_flowctl_surface pass.
- R2: the regenerated mirror's prime workflow reads "Run all 9 scouts in parallel (Codex spawns them as multi-agent threads)."; the new assertion in test_sync_codex_check.py fails against the old mirror.
- R3: new tests/test_arg_loop_zsh.py runs both parse fences under bash and zsh with two flags and with no arguments; it fails on the old loops.
- R9/R10 greps: no shipped flow text says ready mode exports FLOW_AUTONOMOUS (auto.md keeps the export inside the backlog branch); no plan text or scout prompt gives repo-scout the docs-gap charter.
- Host smokes from the branch plugin (`claude -p --plugin-dir`), each against a disposable fixture:
  - `flow --auto --explain` on a ready one-task spec: same result as the pre-change plugin, `PILOT_VERDICT=NEEDS_HUMAN spec=fn-1-... stage=-` because the fixture has no remote and the PR probe fails, with `work` as the next route. The `Route:` line's wording differs between runs; route and stage do not.
  - impl-review `--review=host --validate`: VERDICT=SHIP from a fresh cross-family reviewer subagent; the receipt has verdict, mode host, draws and `validator_note` (the validator runs only on NEEDS_WORK); the run read workflow-common.md for its setup and foreground rule.
  - plan-review `--review=host`: SHIP, receipt written at `.flow/tmp/plan-review-receipt-<spec>.json`.
  - audit `mode:autofix` over five fixture entries: Keep 1, Consolidate 2, Delete 1, all through one `flowctl memory apply` plan; no `git rm`, no hand-edited YAML (the only Write was the plan file).
  - resolve-pr `567 --dry-run` on a real pull request: plan printed (empty: no open threads), nothing edited, committed or posted. The open PRs I checked had no unresolved threads, so this smoke exercised fetch and triage only, not the resolver plan for a live thread.

R8 removed copies and where each rule is still stated (same path):
- flow auto.md Phase 6 terminal paragraph and verdict prose -> Phase 2 all-done PR probe bullets and "The verdict contract" (both verdict templates and the "has broken this" line stay); Phase 3 "Reuse BRANCH_NAME" -> next line (`selected.branch_name`).
- work SKILL.md routing paragraph and tracker section -> phases.md Phase 1 (handle rule), Phase 3 and Phase 5; multi-task "Why spawn a worker?" -> multi-task 3c; multi-task verdict-independence prose -> host-deferred-review.md (the flag instruction and link stay); plan-sync closing paragraphs -> 3b.2/3b.3 (T11 pins) and Rules; sync error table and two rules -> Steps 1-6 inline.
- impl-review other-paths backend selection, input/flags and Steps 1-2 -> SKILL.md setup, Step 0, top routing; fix-loop sub-bullets -> optional-phases.md (read whenever a flag fires); fix-pass OVERRIDDEN -> SKILL.md step 4; workflow-host prompt-contents list -> flowctl review-prompt (rubric, prior findings, reply grammar, re-review scope); workflow-common removals -> other-paths hard invariants (one line added there for "the verdict is acted on ... has broken this"), Step 0.5, triage-rules.md.
- plan-review SKILL.md backend selection -> workflow.md Phase 0; workflow.md philosophy, anti-patterns, transport bullet -> SKILL.md critical rules (the fail-closed sentence stays).
- completion review backend selection, Steps 1-2, routing table, two anti-patterns -> workflow-common Phase 0, SKILL.md routing list, hard invariants; per-backend receipt formats -> flowctl writes the receipt.
- resolve-pr SKILL.md flowctl block, output list, forbidden and bounds bullets -> workflow.md preamble, Phase 10, Safety invariants and Phases 7-9; cluster-gate summary -> cluster-analysis.md; coordinator sibling audit -> agents/pr-comment-resolver.md §2a (serial dispatch follows that file); Phase 9 open-thread rule -> Phase 1. QA SKILL.md flowctl preamble -> qa workflow.md preamble. Drive SKILL.md reference index -> references/agent-browser.md (one pointer line stays).
- capture must-ask history marker; plan examples Golden Rule -> plan SKILL.md "No implementation code"; strategy-alignment comments -> same file's rules; chart SKILL.md step list -> workflow.md; tracker-projection second gate statement -> its line 3.
- prime tier claim -> workflow Phase 1 opening; `--classify-only` exit (unreachable) -> classification.md; parallel-launch line -> Phase 1 first sentence; pillars.md second floor-check rule -> pillars.md first one; SKILL.md re-run line -> workflow 0.6 and remediation-flow Phase 7; playbooks --fix-all boundaries -> SKILL.md "--fix-all boundaries" (the CI-config sentence stays). memory-migrate phase list -> workflow.md ("renamed, never deleted" stays). audit phases consolidate steps -> workflow.md §4.3 (track and category added to its preserve list).

Conduct checklists (flow, work, impl-review, plan-review, spec-completion-review, resolve-pr, qa, audit, prime and the other touched skills): walked against the diff. No checklist item's verdict line, receipt, refusal or "has broken this" condition was removed. The smokes above observed flow's explain line set and its no-write behaviour, impl-review's and plan-review's receipts, and audit's apply-only writes.

Decisions:
- auto.md heading "Phase 1 - SELECT (two-pass)" and its body's "two-pass" (plus backlog-mode's "two-pass-filters") became plain "SELECT"/"filters". No passes exist, and R1 already removes the "Pass 2" pointers.
- Kept the "verdict is acted on" guard by moving it into other-paths' hard invariants when workflow-common was cut (R7); every reader of workflow-common came through other-paths.
- The mirror assertion reads the committed mirror; CI's `sync-codex.sh --check` keeps it equal to a fresh regeneration. After review it pins only the `multi-agent` token and the absent Task-tool wording (G2).
- Not done because the spec's dropped list or Boundaries covered them: auto.md :191 wording beyond "two-pass", multi-task's bridge one-liner (no separate rolling-mode copy of the bridge rule exists), sync's COMPLETED note, computer-use.md (it has no "moved from" or "until now" note), prime's per-shape list.

Follow-ups (found, not part of this spec):
- zsh word-splitting is also unfixed in flow SKILL.md:37, auto.md:48/:50, features SKILL.md:64 and capture SKILL.md:61 (`for X in $ARGUMENTS/$RAW_ARGS`). resolve-pr's Phase 0 fence reads `BASH_REMATCH`, which zsh does not set, so comment-URL and PR-URL parsing come back empty under zsh.
- In chart re-entry.md, the locate fence's `2>/dev/null) || LOCATE_JSON=""` discards the `--json` failure envelope that "Print the structured failure" relies on.
- audit workflow.md Phase 4's "Done when" still says "staged in git" and "edits land via Write or flowctl helper", which clashes with apply-only persistence.
- auto.md's multi-defer sentence says the reason reads `defer to land`, but the DEFERRED_TO_LAND template's reason differs. cua.md keeps a dated provenance note.
- Codex impl-review: one of three draws (integration) timed out after 1800s. The verdict rests on the correctness and contracts draws.

stage: impl-review - ran (codex, 3 draws, 2 voted, VERDICT=SHIP; one P2 G2 finding fixed after SHIP in 7a2106a4)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 09253fb81fc3311db8ac75ad96568e9da3fece09, 7a2106a4fe63267b7ce48a6a7e97f0e93e33387e
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check, python3 scripts/run_tests_parallel.py --pattern test_sync_codex_check.py
- PRs: