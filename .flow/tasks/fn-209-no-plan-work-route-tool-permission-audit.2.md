---
satisfies: [R2, R3, R4, R5, R6, R7]
---
# fn-209-no-plan-work-route-tool-permission-audit.2 work zero-task fork: ask + flag/NL, minimal implicit task, judicious-subagent prose, gated reference

## Description
The core route (R2-R7): the zero-task fork in work's spec mode, the pre-answer flag/NL, the minimal implicit-task mint, the judicious-subagent dispatch prose, all behind a new gated reference - plus the host-deferred rationale correction that R1 makes necessary (this task owns the work skill's files).

**Size:** L-leaning-M (cohesive; do not split - all edits land in the work skill's own files)
**Files:** `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/skills/flow-next-work/SKILL.md`, `plugins/flow-next/skills/flow-next-work/references/no-plan-route.md` (new), `plugins/flow-next/skills/flow-next-work/references/host-deferred-review.md`
**Touches:** [plugins/flow-next/skills/flow-next-work/**]

### Approach
- Fork site: `phases.md:46-50` (SPEC_MODE, after `ready --spec` returns empty; byte-stable post-fn-208 - every 208 hunk starts at :142+). The fork now sits immediately above the new `### 3f.1 Pause path` (:410-430) - coexist, do not reorder. Distinguish zero-tasks-ever from all-done BEFORE the Phase 3 fall-through; route the legacy fall-through out of existence (R2). Spec-file/idea-text entry shapes (`phases.md:51-70`) stay untouched - direct-by-construction.
- Gate the whole branch behind a sentinel + new `references/no-plan-route.md` (copy the sentinel phrasing at `phases.md:502-505` and the reference-header convention of `references/host-deferred-review.md:1-6`). Plan-full runs read nothing new (R7). In the same pass evaluate - defensively, no forced moves - whether existing plan-full-only machinery can also lift behind gates.
- The reference owns: the ask (plan-first vs work-directly; copy the lettered-options + natural-language-fallback phrasing of `references/setup-questions.md:12-42`; recommendation is agent-judged per spec from size/independent-surfaces/blast-radius with the reason stated, R3; consequence-explained options; fallback to plan-first when the spec is unreadable), the autonomous typed refusal ("spec has no tasks - run /flow-next:plan" under any autonomy marker without an explicit no-plan instruction; scan the marker FAMILY - FLOW_RALPH, FLOW_AUTONOMOUS, REVIEW_RECEIPT_PATH, mode:autonomous - per the memory lesson), the plan-first semantics (that answer STOPS the run with a one-line pointer to /flow-next:plan - work never invokes plan itself), and the mint.
- Flag/NL parsing joins `SKILL.md:94-117` (`--no-plan` + phrases like "no plan"/"skip planning"); contradictory signals ask; the flag on a spec WITH tasks is ignored with a one-line notice (R4).
- Post-fn-208 dispatch contract for the minted task: it still prints the mandatory `Selection rule:` report line (:143, :149-153 - five report lines now); the 3c dispatch template's new `FORBIDDEN:` field echoes declared Touches and the minted task has NONE, so `FORBIDDEN:` renders OMITTED (no path ban - whole-spec surface is the point); `TIMEBOX:` applies unchanged. The join-barrier prose should cite the new workspace cleanup gate at `references/wave-join.md:31-40` (teardown only on reachable commits + clean tree). worker.md deliberately gains NO subagent prose (the license lives in this route's dispatch prose only; plan-full judgment governs - recorded in spec Decision Context).
- Mint: reuse the exact call shape at `phases.md:51-70` - `task create --spec <id> --title "Implement <spec title>"` - MINIMAL body (never an emulated plan), `--satisfies` listing ALL spec R-IDs (keeps 3g policy skip + make-pr coverage correct), no Touches line. Re-run resolves as resume (task count 1) - state it in the reference (R5).
- Judicious-subagent prose (R6, in the reference, part of the worker dispatch for the minted task): broad license - parallel implementation of independent surfaces, background research, scouting - shape chosen by the harness; portable-host degradation clause (no nested dispatch -> serial, never errors; no capability probing); commit ownership unchanged (worker is the only committer, single-commit + `git add -A` stand; hand subagents disjoint surfaces or serialize), and a join barrier: every dispatched subagent is awaited and reconciled before staging, verification, and commit - no live writer at `git add -A` time.
- host-deferred correction: `phases.md:232` and `references/host-deferred-review.md:15` currently justify the contract with "worker cannot dispatch Task" - false after task 1. Re-justify on verdict independence: the agent that wrote the code never dispatches or issues its own review verdict. Contract mechanics unchanged.
- Mirror note: canonical 3c is NOT touched. Do NOT run `./scripts/sync-codex.sh` in this task - the worker's `git add -A` would stage a partial mirror regen; the committed regen and its guards belong wholly to task 6.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-work/phases.md:40-110` - Phase 1 entry shapes + zero-task fall-through
- `plugins/flow-next/skills/flow-next-work/phases.md:431-528` - 3g gate incl. single-task policy skip + sentinel pattern
- `plugins/flow-next/skills/flow-next-work/SKILL.md:94-117` - option parsing block
- `plugins/flow-next/skills/flow-next-work/references/setup-questions.md:12-42` - ask phrasing convention
- `plugins/flow-next/skills/flow-next-work/references/host-deferred-review.md` - contract whose rationale this task corrects
- `plugins/flow-next/skills/flow-next-work/references/wave-join.md:31-40` - new cleanup gate the join barrier cites

**Optional:**
- `plugins/flow-next/skills/flow-next-work/references/spec-id-mint.md` - mint-gate reference shape

### Acceptance
- [ ] zero-task spec-id run forks: interactive ask (agent-judged rec, consequences explained), autonomous typed refusal, flag/NL pre-answer - legacy fall-through unreachable
- [ ] direct route mints exactly one minimal task, satisfies = all spec R-IDs, no Touches; re-run resumes, never re-mints
- [ ] judicious-subagent prose present with portable-host degradation, commit-ownership bound, and the await-before-staging join barrier
- [ ] no-plan machinery lives in `references/no-plan-route.md` behind a sentinel; plan-full path loads nothing new
- [ ] host-deferred rationale corrected to verdict independence in both files
- [ ] no sync-codex run in this task (regen wholly owned by task 6)
- [ ] one live dogfood run of the no-plan route on a throwaway spec - fork ask, flag pre-answer, and autonomous refusal each exercised once - with the evidence recorded in the done summary
### Acceptance
- [ ] TBD

### Done summary
TBD

### Evidence
- Commits:
- Tests:
- PRs:
## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
