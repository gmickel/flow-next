---
satisfies: [R2, R3, R4, R5, R6]
---
# fn-200-land-request-human-reviewers-at.2 land workflow: §2.6b human reviewer request (predicate, one-shot ledger, ready flip, dry-run, report)

## Description
Add the §2.6b gate (read-only predicate + planned action) and the Phase 3 `request-reviewers` action class (ready flip, reviewer request, ledger write) to the land workflow, one-shot per head SHA via ledger `reviewRequestSha`; wire the Phase 0 config read, the `author` field on the PR-state capture, the ledger schema note, dry-run report, Phase 4 evidence field, SKILL.md bullet, conduct row, and the static tests. Implements the spec's Architecture section verbatim — read it first; this task does not restate it.

**Size:** M
**Files:** plugins/flow-next/skills/flow-next-land/workflow.md, plugins/flow-next/skills/flow-next-land/SKILL.md, agent_docs/conduct/land.md, plugins/flow-next/tests/test_land_config.py
**Touches:** [plugins/flow-next/skills/flow-next-land/**, agent_docs/conduct/land.md, plugins/flow-next/tests/test_land_config.py]

### Approach
- Phase 0 (workflow.md ~l.66-72): `REQUEST_REVIEWERS="$(lcfg requestReviewers)"; [[ "$REQUEST_REVIEWERS" == "null" ]] && REQUEST_REVIEWERS=""` — same off-switch contract as `reviewTrigger`; stays inside the single `lcfg` capture (`test_skill_prose_diet` pins exactly one `config get`).
- Phase 1 PR-state capture (~l.195): add `author` to the `gh pr view --json` field list and extract `PR_AUTHOR` (`.author.login`); a null/empty login is the R4 failure path, never a self-request. No other new GitHub read.
- Ledger schema sentence (~l.90-98): add `reviewRequestSha` next to `triggerSha`.
- New `### 2.6b — Human reviewer request (land.requestReviewers)` between the §2.6 signal evaluation and §2.7, READ-ONLY: evaluate the spec's predicate from state already captured (CI tri-state, `UNRESOLVED`, signal satisfaction, `REVIEW_DECISION`, `HEAD_OID`, ledger `reviewRequestSha`, existence of the `(PR, HEAD_OID)` claim dir); when due set `PLANNED_ACTION=request-reviewers` (overriding a `silence` planned `merge`), provisional `AWAITING_REVIEW` / `NEEDS_HUMAN` per window; when already recorded for this head → `PLANNED_ACTION=none` and `reviewers=already:<sha8>`. Keep it no longer than the bot-trigger paragraph above it (G1). Leave the bot trigger untouched.
- New Phase 3 `### 3.x — request-reviewers` beside `3.4 label`: (0) atomic claim: `mkdir -p "$LEDGER_DIR/review-request-claims" && mkdir "$LEDGER_DIR/review-request-claims/${PR_NUMBER}-${HEAD_OID}"` — a failed second `mkdir` means another tick holds this head → `reviewers=already:<sha8>`, stop; remove the PR's claim dirs in §3.5's post-merge ledger cleanup (beside `del(.[$pr])`); (1) `[[ "$IS_DRAFT" == "true" ]] && gh pr ready`; (2) build the csv = configured tokens minus `codeowners` minus `PR_AUTHOR` (whole-token compare; `org/team` kept) → non-empty → `gh pr edit "$PR_NUMBER" --add-reviewer "<csv>"`; empty csv on a draft → ready flip was the request-producing action (`requested`); empty csv on an already-ready PR → `reviewers=skipped:already-ready, no explicit logins`; (3) write `reviewRequestSha = HEAD_OID` with the atomic jq+mv idiom (~l.476-481) regardless of 1-2's outcome; (4) failures → `reviewers=failed:<one-line>`, verdict per window, never BLOCKED. Add `request-reviewers` to the action-class enumeration in §2.8's PLANNED_ACTION line and Phase 3's intro.
- Dry-run section (~l.458): state that a planned `request-reviewers` reports `reviewers=would-request` (+ `would-ready` for a draft) — no new guard needed; Phase 3 is never entered.
- Phase 4 (~l.743-760): `action=` gains `request-reviewers`; `signal=` line gains `reviewers=<requested|would-request|already:<sha8>|skipped:<reason>|failed:<reason>|off>`; verdict priority order untouched.
- SKILL.md: one gate bullet in the `mergeVerdictCommand` style (~l.110-112) and `request-reviewers` in any action-class list; keep the Forbidden list as-is.
- `agent_docs/conduct/land.md`: one checklist row after the mergeVerdictCommand row: when set, reviewers are requested at most once per PR per head SHA and only when a human review is the sole missing merge input, via a Phase 3 action class; unset/empty = unchanged; `--dry-run` reports would-request and mutates nothing.
- Tests (`test_land_config.py`): a `RequestReviewersWorkflowStaticTestCase` in the style of `MergeVerdictGateWorkflowStaticTestCase` — smallest distinctive tokens only (G2): `lcfg requestReviewers` + no second `config get`; `author` in the `gh pr view --json` field list; `reviewRequestSha`; §2.6b heading between §2.6 and §2.7; a `request-reviewers` heading inside Phase 3 (after the "Phase 3" heading, before "Phase 4"); `reviewers=` report token with `off`/`skipped:`/`failed:`; `would-request`; the conduct row. No prose-sentence assertions. (Honest-harness note: the gate is host-executed prose; there is no stubbed-`gh` harness — see spec Decision Context.)
- Dogfood: `/flow-next:land --dry-run` in this repo with the key unset → `reviewers=off`, verdict line unchanged; then `flowctl config set land.requestReviewers gmickel` against a draft PR of this repo (if one is open) → `action=request-reviewers reviewers=would-request would-ready`, zero mutations; reset the key afterwards.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-land/workflow.md:58-98` — Phase 0 config capture + ledger resolution/schema
- `plugins/flow-next/skills/flow-next-land/workflow.md:188-200` — Phase 1 `PR_STATE` capture (add `author`)
- `plugins/flow-next/skills/flow-next-land/workflow.md:298-386` — §2.6 signal + bot trigger one-shot + §2.7
- `plugins/flow-next/skills/flow-next-land/workflow.md:388-470` — §2.8 PLANNED_ACTION enumeration, §2.9, dry-run stop
- `plugins/flow-next/skills/flow-next-land/workflow.md:464-548` — Phase 3 intro + action classes 3.1-3.4 (shape for the new class)
- `plugins/flow-next/skills/flow-next-land/workflow.md:743-772` — Phase 4 report shape
- `plugins/flow-next/tests/test_land_config.py:440-520` — static workflow test classes + the single-`config get` pin

**Optional:**
- `plugins/flow-next/tests/test_skill_prose_diet.py:77-95` — the one-config-get invariant
- `.flow/specs/fn-149-*.md` — stacked-PR hardening touches §2.8/§3.3/§3.5; leave a one-line cross-ref there if still open

### Key context
- `gh pr edit --add-reviewer` accepts `login` and `org/team`; GitHub 422s a self-request (hence the author filter) and rejects the whole batch on one bad entry; re-requesting an already-requested login is a no-op, re-requesting one who already reviewed is a re-request (intended for a new head).
- `ready_for_review` is not a push: it dismisses nothing, so §2.7's stale-approval detector needs no change.
- Exact-once under overlapping ticks comes from the atomic `mkdir` claim, not from the ledger jq+mv (which is last-writer-wins); the ledger sha stays the human-readable record.

### Acceptance
- [ ] §2.6b present between §2.6 and §2.7 and read-only (no `gh` write, no ledger write in Phase 2); `request-reviewers` action class present in Phase 3 with the atomic `mkdir` claim FIRST, then ready flip, author-filtered request, ledger write, failure rule; claim dirs cleaned with the PR's ledger entry
- [ ] Static test pins the `review-request-claims` token inside the Phase 3 section and `mkdir` preceding `gh pr ready` within it (ordering of two tokens, not prose)
- [ ] `PR_STATE` capture includes `author`; Phase 0 reads `requestReviewers` via `lcfg`; `test_skill_prose_diet` still green
- [ ] Phase 4 `reviewers=` field documented with the six values and `action=request-reviewers`; `--dry-run` section names would-request/would-ready
- [ ] SKILL.md bullet + conduct row added
- [ ] New static test class green; `cd plugins/flow-next/tests && python3 -m unittest test_land_config test_skill_prose_diet -q`
- [ ] Dogfood `--dry-run` ticks: key unset → `reviewers=off`, unchanged verdict; key set against a draft PR → `action=request-reviewers reviewers=would-request`, no mutation
## Acceptance
- [ ] TBD

## Done summary
Added the `land.requestReviewers` gate to the land workflow: §2.6b (read-only human-review-pending predicate from already-captured state, one-shot per head via ledger `reviewRequestSha` + claim dir, window-bound verdict, suppresses §2.8's merge under `silence`+`REVIEW_REQUIRED`) and the Phase 3 `§3.4b request-reviewers` action class (atomic `mkdir` claim -> head re-read (unreadable releases the claim; moved = no mutation) -> draft ready flip -> author-filtered `--add-reviewer` with `codeowners` riding the flip -> ledger write regardless, `failed:` never `BLOCKED`), plus Phase 0 `lcfg requestReviewers`, `author` on the PR_STATE capture, ledger schema note, dry-run would-request/would-ready, Phase 4 `reviewers=` field + `action=request-reviewers`, SKILL.md bullet, conduct row, fn-149 cross-ref, and `RequestReviewersWorkflowStaticTestCase` (R2-R6). Also regenerated `flowctl_tracker/MANIFEST.json` (stale since fn-200.1's flowctl.py change - inherited full-suite red, now green). Dogfood `--dry-run` ticks not reachable: no open PR in this repo (would be NO_WORK); substituted `bash -n` + a stubbed-`gh` simulation of every §3.4b branch. Codex mirror regen is task .3's (R7).

stage: impl-review - ran (codex gpt-5.6-sol high: NEEDS_WORK x2 -> SHIP; findings fixed in 3cf542be, a4b2e679)
## Evidence
- Commits: bc1a7cee1715d03ba1bbeeb95b52fb90388bfef0, 3cf542be8f174a10eb2610d45a95e51d1915033b, a4b2e6790d0dc3b61393c4e1ca06d876a4ccf37b
- Tests: baseline: green (cd plugins/flow-next/tests && python3 -m unittest test_land_config test_flow_config_schema_drift test_skill_prose_diet -q; uvx ruff@0.16.0 check .), cd plugins/flow-next/tests && python3 -m unittest test_land_config test_flow_config_schema_drift test_skill_prose_diet -q, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., python3 scripts/gen_tracker_manifest.py --check, bash -n on extracted §2.6b/§3.4b snippets + stubbed-gh simulation of §3.4b branches (.flow/tmp/sim_34b.sh, uncommitted)
- PRs: