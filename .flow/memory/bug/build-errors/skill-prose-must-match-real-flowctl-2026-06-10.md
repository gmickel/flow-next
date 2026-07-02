---
title: "Skill prose must match real flowctl surfaces (fields, status enums, subcommands)"
date: "2026-06-10"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-pilot/workflow.md
tags: [fn-59, pilot, skill-authoring, flowctl-json, task-status, rp-review, fn-68, backlog-mode, safety-gates, dry-run, review-feedback, fn-82, skill-prose, dedupe, progressive-disclosure]
problem_type: build-error
symptoms: "RP impl-review 2x NEEDS_WORK: assignee read from listing that lacks it, phantom flowctl whoami, ready/open vs todo status enum, var used before assignment"
root_cause: "Workflow bash written from spec vocabulary without verifying flowctl JSON emitters, status enums, and subcommand existence"
resolution_type: fix
last_updated: "2026-07-02"
---

## Problem
fn-59.1 authored the new flow-next-pilot skill (single-tick conductor). RP impl-review needed two NEEDS_WORK rounds; every finding was skill prose referencing flowctl/state surfaces that do not exist as written:
1. Collision check read `assignee` from `flowctl tasks --spec --json` — that minimal listing emits only id/spec/title/status/priority/depends_on; `assignee` lives on `show <task-id> --json`.
2. Prose called `$FLOWCTL whoami` — no such subcommand exists.
3. Stage classification matched task statuses `ready`/`open` — the canonical TASK_STATUS enum is `todo|in_progress|blocked|done` (flowctl.py:162); a normal planned spec with `todo` tasks would not classify.
4. A Phase-2 bash snippet used `$BRANCH_NAME` that was only assigned in Phase 3.

## What Didn't Work
Writing workflow bash/predicates from the parent spec's conceptual vocabulary ("ready tasks", "assignee", "whoami") without grepping the actual flowctl JSON emitters for field names, status enums, and subcommand existence.

## Solution
Per finding: fetch `assignee` via `show <task-id> --json` for in_progress tasks; actor identity from `git config user.email`; classify work on non-`done` statuses (`todo`/`blocked`/`in_progress`); resolve `BRANCH_NAME` in Phase 2 before the PR probe and reuse in Phase 3. Commits 9247c0c + 90b3287.

## Prevention
When a skill's prose embeds flowctl invocations or JSON-field predicates, verify EACH against the real surface before review: run the subcommand once (`flowctl <cmd> --json | jq keys`), grep `TASK_STATUS`/emitter functions in flowctl.py for enums, and check every `$VAR` in a snippet is assigned in the same or an earlier phase. Spec vocabulary ("ready", "claimed") is conceptual, not the wire format.

## Update 2026-06-27

## Problem
fn-68.4 wired backlog mode into the pilot skill. RP impl-review returned NEEDS_WORK twice (5 findings total), every one a "skill bash snippet read as authoritative but not actually enforcing/correct under literal execution":
- R1: never-merge / never-author guards sat at Phase 0.5 but depended on vars (`DISPATCH_TARGET`, `ASK_WRITES_SPEC`, `SPEC_PATH`) assigned in a LATER phase → guards no-op if run literally.
- R1: single-tick + dep-cycle invariants were prose-only ("there is no loop", "a cycle is surfaced") with NO bash branch/flag/terminal.
- R1: live verdict-grammar enum omitted `TRIAGED` while the dry-run path emitted `PILOT_VERDICT=TRIAGED` → contract inconsistency.
- R2: backlog `--dry-run` still dispatched tracker-sync `reconcile`/`list-open` before triage → a dispatch-free inspection tick mutated readiness/receipts.
- R2: `export FLOW_AUTONOMOUS=1` was a bare snippet OUTSIDE the `if PILOT_AUTONOMY=backlog` branch → ready mode (gate off) got the autonomy side-effect, violating "gate off byte-for-byte unchanged".

## What Didn't Work
Stating an invariant in prose next to an illustrative snippet, and defining a guard early then relying on prose to "call it later". A reviewer (and an executing host agent) reads the SNIPPET as authoritative: a guard whose `$VAR` is unset no-ops; a prose-only "single-tick" claim enforces nothing; a bare `export`/side-effect outside the mode branch runs in BOTH modes.

## Solution
- Define guards as `assert_allowed_dispatch` / `assert_spec_write_allowed` shell functions and CALL them inline at every real dispatch + spec-write site (Phase 1.5 tracker ops, Phase 3.5 question op, Phase 4 stage dispatch), setting `DISPATCH_TARGET` on the line before each call.
- Make single-tick a `SELECTED_COUNT` hard-assert and dep-cycle a `DEP_DEADLOCK` branch routing to a terminal — both enforcing bash, not prose.
- Split the verdict grammar explicitly: live set (no TRIAGED) vs dry-run-only set (adds TRIAGED).
- Gate every Phase 1.5 tracker dispatch on `[ "$DRY" = "0" ]` and add a Phase 1.6 `exit 0` short-circuit emitting diagnostic TRIAGED before any routing.
- Move `export FLOW_AUTONOMOUS=1` + all helper defs INSIDE the `else` (backlog) branch of the autonomy guard; ready mode hits a bare `:` no-op.

## Prevention
When authoring a config-gated mode on an existing skill: (a) every safety invariant the prose promises must be a HARD bash branch (flag/assert/exit) at the site it protects — never prose-only, never a guard floating on a var assigned in a different phase; (b) any mode-specific side-effect (`export`, helper def, dispatch) must live INSIDE the `if mode==X` branch so the gate-off path is provably side-effect-free; (c) cross-check the `--dry-run` / inspection path dispatches NOTHING and mutates NOTHING — gate every dispatch on the dry-run flag and short-circuit to the diagnostic terminal before routing; (d) keep the live verdict enum and any diagnostic-only verdict in explicitly separate grammars. This is the fn-68.4 instance of `skill-workflow-snippets-must-enforce` — two NEEDS_WORK rounds, same root cause.

## Update 2026-07-02

## Problem
fn-82.1 deduped pilot's backlog SELECT/TRIAGE/ASK prose "with a one-line pointer per phase" to backlog-mode.md, but the first pass kept step-level parenthetical restatements ("backlog-mode.md 1a — never blocks, never prompts; inactive-bridge no-op falls back…") and re-enumerated the triage class table in the Phase 1.6 intro. RP impl-review flagged it Major: the prose was still double-sourced and the always-loaded diet goal (R2) unmet.

## What Didn't Work
Treating "one-line pointer" as "one line that also summarizes the mechanics". A pointer that restates the pointed-at content is still a duplicate — reviewers (and token counts) read it as such.

## Solution
Commit 691c9a2d: pointers reduced to bare section references (`(backlog-mode.md 1a)`), the class-table enumeration dropped from the Phase 1.6 intro, and the redundant class→terminal mapping paragraph deleted (the pre-existing route-by-class sentence already carried it). Kept inline: enforcing bash, invariants #1–#4, dry-run rules (workflow-owned, absent from the reference), and verdict-grammar lines.

## Prevention
When a spec says "delegate prose with a one-line pointer per phase": the pointer names the owning file+section and NOTHING of the mechanics. Before committing, re-read each pointer and ask "does any clause here restate what the reference says?" — if yes, cut it. Keep only content the reference genuinely does not own (enforcing bash, invariants, verdict grammar, mode-specific rules like dry-run).
