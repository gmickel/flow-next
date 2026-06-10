---
title: "Skill prose must match real flowctl surfaces (fields, status enums, subcommands)"
date: "2026-06-10"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-pilot/workflow.md
tags: [fn-59, pilot, skill-authoring, flowctl-json, task-status, rp-review]
problem_type: build-error
symptoms: "RP impl-review 2x NEEDS_WORK: assignee read from listing that lacks it, phantom flowctl whoami, ready/open vs todo status enum, var used before assignment"
root_cause: "Workflow bash written from spec vocabulary without verifying flowctl JSON emitters, status enums, and subcommand existence"
resolution_type: fix
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
