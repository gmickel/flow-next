---
satisfies: [R1, R2, R3, R4, R6, R7, R8, R9, R10, R12, R13, R14, R16, R17]
---

## Description

Build the `flow-next-land` skill: SKILL.md + workflow.md + the `/flow-next:land` command shim + sync-codex registration. One invocation = one tick over all build-loop-authored open PRs; per-PR verdicts echoed as evidence, exactly one terminal `LAND_VERDICT=` line last. All gate semantics are BINDING from the spec's "Resolved at planning" section — tri-state CI, silence-convergence default, explicit merge with `--match-head-commit`, re-entry idempotency, branch hygiene, ledger + durable label.

**Size:** L (mirror of fn-59.1, which shipped as one task)
**Depends on:** fn-60.2 (resolve-pr autonomous parse + land.* defaults must exist before land dispatches them)
**Files:** plugins/flow-next/skills/flow-next-land/SKILL.md (new), plugins/flow-next/skills/flow-next-land/workflow.md (new), plugins/flow-next/commands/flow-next/land.md (new), scripts/sync-codex.sh (registration only)

## Approach

- Mirror pilot's structure file-for-file: `skills/flow-next-pilot/SKILL.md` (preamble :16-23, hard guards :40-55, verdict contract :93-110, Forbidden :112-119) and `workflow.md` (ledger pattern :46-54, atomic jq+mv writes).
- Tick phases in workflow.md: guards → DISCOVER (per open spec with all tasks done: `gh pr list --head <branch_name> --state all --json url,state,number`, filter OPEN; authorship needs BOTH branch match AND make-pr body breadcrumb — branch-only → NEEDS_HUMAN; merged-but-unclosed → resume tail) → per-PR GATE tree (CI tri-state over ALL checks → patience window → resolve dispatch → review signal incl. [bot]-suffix/land.automatedReviewers rule → merge gates) → ACT (one action class per PR per tick) → REPORT (per-PR verdicts + terminal line, worst-severity priority rule). `--dry-run` stops after GATE: full classification report, zero mutations (R17).
- CI-fix contract + mechanical-rebase conflict path + bounded release-follow exactly per the spec's Resolved-at-planning bullets (relatedness/rerun rule, strike-before-push, fix(ci) commits, staged-files-only; Actions-run-id log branch vs external checks → NEEDS_HUMAN when logs unavailable and no local validation; rebase abort on any conflict hunk → BLOCKED, --force-with-lease; release idempotency probe + clean-tree bounds; post-merge base checkout before the tail).
- resolve-pr dispatch: `/flow-next:resolve-pr <pr-number> mode:autonomous`; gate on its terminal `RESOLVE_PR_VERDICT=…` line (fn-60.2 ships the parse + line first — this task depends on .2).
- Merge: `gh pr ready` (skip when not draft) → `gh pr merge --squash --delete-branch --match-head-commit <head-sha>`; mismatch → re-tick. Post-merge: checkout base + `git pull --ff-only` + verify the squash commit landed BEFORE the tail (close/tracker/release run from the clean base, never the deleted PR branch). Then `flowctl spec close <spec>` (all-tasks-done precondition; stray tasks → NEEDS_HUMAN) → opt-in tracker touchpoint (`tracker.perEvent.land.merged`, dispatch tracker-sync skill, event-tagged receipt) → release-follow (discovery order from Resolved at planning; failure after merge → NEEDS_HUMAN + label, never re-merge).
- Ledger: `$(git rev-parse --git-common-dir)/flow-next/land-strikes.json` — per-PR CI-fix counts; budget from `land.ciFixBudget` (read via config get; fn-60.2 seeds defaults — workflow must tolerate null → fallback 3 until .2 lands).
- sync-codex.sh: `generate_openai_yaml "flow-next-land" …` (group with pilot ~:1204) + `REQUIRED_OPENAI_YAML_SKILLS` entry (~:1258). Run sync as LOCAL validation only; committed mirror regen rides fn-60.3.
- Memory discipline: every flowctl invocation in prose must use real subcommands/fields (bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10); no AskUserQuestion anywhere in the tick path (autonomous by design — also avoids R2-block injection issues).

## Investigation targets

**Required** (read before writing):
- `plugins/flow-next/skills/flow-next-pilot/SKILL.md` + `workflow.md` — the template to mirror
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md:218-245` — OPEN-state filter (fn-42), `:1318-1399` — Ref-line signals
- `plugins/flow-next/skills/flow-next-resolve-pr/SKILL.md` + `workflow.md:23-30` — dispatch surface land calls
- `plugins/flow-next/scripts/flowctl.py:17259-17298` — `cmd_spec_close` all-done gate
- `scripts/sync-codex.sh:1190-1280` — registration sites

**Optional:**
- `.flow/specs/fn-60-ship-loop-skill-autonomous-pr.md` Resolved-at-planning (binding)

## Acceptance

- [ ] `/flow-next:land` exists (SKILL.md + workflow.md + command shim) with pilot-style guards (Ralph nesting, dirty tree), `user-invocable: false`, `allowed-tools: Read, Bash, Grep, Glob, Write, Edit, Skill` (Skill required for resolve-pr/tracker-sync dispatch; no Task)
- [ ] Tick implements DISCOVER → GATE → ACT → REPORT with the binding gate semantics (CI tri-state incl. exit 8 + empty-list rule; patience window anchored to last push; silence/approve/login review signal; explicit merge `--squash --delete-branch --match-head-commit`; never `--auto`)
- [ ] Re-entry: merged-but-unclosed spec resumes close → tracker → release; stray non-done tasks → NEEDS_HUMAN
- [ ] Bounded CI fixes via land ledger + `flow-next:needs-human` label skip; stale-approval detection → NEEDS_HUMAN
- [ ] Terminal `LAND_VERDICT=` grammar exactly per spec (worst-severity rule, NO_WORK case), nothing printed after it
- [ ] `--dry-run` exercises discovery, CI tri-state parsing, review-signal classification, and terminal-line aggregation against this repo with ZERO mutations — and that dry-run output is captured as task evidence (the local smoke for the gate grammar)
- [ ] sync-codex registration added; `./scripts/sync-codex.sh` validators green locally (mirror diff reverted; commit rides fn-60.3)
- [ ] All flowctl/gh invocations in prose verified against real CLI surfaces (gh 2.93.0)

## Done summary
Built the /flow-next:land skill (SKILL.md + workflow.md + command shim + sync-codex registration): a cadence-tick autonomous PR babysitter that discovers build-loop-authored PRs (dual authorship signals, merged-but-unclosed re-entry), gates each through CI tri-state / patience window / review signal / merge gates, takes one action class per PR (bounded ledger-tracked CI fixes, resolve-pr mode:autonomous dispatch, mechanical rebase, explicit gated merge + spec close + tracker touchpoint + bounded release-follow), and ends with the worst-severity terminal LAND_VERDICT line; --dry-run classifies with zero mutations. Codex impl-review SHIP after one fix round (discovery PR_NUMBER assignment, hard TAIL_OK post-merge gate, explicit tracker-sync dispatch).
## Evidence
- Commits: ad6734a334b0e21f30cdf8db9ae50c08ff963fce, 85c582ee0db2f18c94716ae90c1c8f209f588c2b
- Tests: for f in plugins/flow-next/tests/test_*.py; do python3 $f; done (all green), bash -n scripts/sync-codex.sh && ./scripts/sync-codex.sh (validators green, 21 required skills incl. flow-next-land; mirror diff reverted per task scope), land --dry-run smoke against this repo: Phase 0 guards pass, config reads (release=true patienceMinutes=30 reviewSignal=silence ciFixBudget=3), discovery NO_WORK with 4 non-spec open PRs correctly ignored, terminal line LAND_VERDICT=NO_WORK prs=0 pr=- emitted last; GATE snippets exercised read-only vs live PR #95 (CI tri-state rc=1/empty->none-beyond-window, patience anchor parse, unresolved-threads GraphQL=0, silence signal=never); zero mutations verified (no ledger dir, no label, clean tree) — /tmp/land-dry-run-evidence.txt
- PRs: