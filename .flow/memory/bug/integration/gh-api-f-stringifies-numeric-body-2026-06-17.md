---
title: gh api -f stringifies numeric body fields (issue_id) → GitHub 422; use -F
date: "2026-06-17"
track: bug
category: integration
module: "plugins/flow-next/scripts/make-pr-create.sh, plugins/flow-next/skills/flow-next-resolve-pr/scripts"
tags: [fn-64, tracker-sync, github, gh-api, rest, graphql, "422", issue-dependencies, resolve-pr, make-pr]
problem_type: integration
symptoms: GitHub POST blocked_by returns 422 — issue_id sent as a JSON string instead of a number
root_cause: gh api -f/--raw-field always emits strings; the dependencies API requires numeric issue_id
resolution_type: fix
last_updated: "2026-10-05"
last_audited: "2026-10-05"
---

## Problem
GitHub's native issue-dependency POST (`/repos/{o}/{r}/issues/{n}/dependencies/blocked_by`) requires the request body `issue_id` to be a JSON **number** (the blocker's numeric DB id). The first draft of the github.md adapter snippet used `gh api -f "issue_id=$BLOCKER_ID"`, which sends a JSON **string** (`"issue_id":"123"`) and GitHub rejects with 422.

## Solution
Use `gh api -F "issue_id=$BLOCKER_ID"` (`--field`, type-aware: a bare integer is emitted as a JSON number). Equivalent: `jq -n --argjson issue_id "$id" '{issue_id:$issue_id}' | gh api ... --input -`. Originally fixed in `plugins/flow-next/skills/flow-next-tracker-sync/references/github.md` setIssueRelation native snippet, with an explicit `-F`-not-`-f` warning so the host agent never stringifies the id.

## Prevention
Pick the flag by value type. `-F/--field` is type-aware: integers, `true`, `false` and `null` become JSON literals, and a value starting with `@` is read from a file. Use it for ids, counts and flags. Use `-f/--raw-field` for free-form strings such as a comment or reply body, where `-F` would turn "123" into a number or read "@name" as a file. A request body built in code goes through `--input -` instead.

## Update 2026-10-05
The tracker snippet this entry cited moved into Python: `flowctl_tracker` sends request bodies with `--input -`. The remaining `gh api` callers are `plugins/flow-next/scripts/make-pr-create.sh` (stack links, `-F "pull_requests[]=..."`) and the resolve-pr scripts under `skills/flow-next-resolve-pr/scripts/` (GraphQL variables: `-F` for ids and numbers, `-f` for the query and the reply body).
