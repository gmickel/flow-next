---
title: gh api -f stringifies numeric body fields (issue_id) → GitHub 422; use -F
date: "2026-06-17"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-tracker-sync/references/github.md
tags: [fn-64, tracker-sync, github, gh-api, rest, "422", issue-dependencies]
problem_type: integration
symptoms: GitHub POST blocked_by returns 422 — issue_id sent as a JSON string instead of a number
root_cause: gh api -f/--raw-field always emits strings; the dependencies API requires numeric issue_id
resolution_type: fix
related_to: [bug/integration/set-tracker-id-rejected-github-n-2026-06-03, bug/integration/trackers-auto-linkify-issue-key-2026-06-03]
---

## Problem
GitHub's native issue-dependency POST (`/repos/{o}/{r}/issues/{n}/dependencies/blocked_by`) requires the request body `issue_id` to be a JSON **number** (the blocker's numeric DB id). The first draft of the github.md adapter snippet used `gh api -f "issue_id=$BLOCKER_ID"`, which sends a JSON **string** (`"issue_id":"123"`) and GitHub rejects with 422.

## Solution
Use `gh api -F "issue_id=$BLOCKER_ID"` (`--field`, type-aware: a bare integer is emitted as a JSON number). Equivalent: `jq -n --argjson issue_id "$id" '{issue_id:$issue_id}' | gh api ... --input -`. Fixed in `plugins/flow-next/skills/flow-next-tracker-sync/references/github.md` setIssueRelation native snippet, with an explicit `-F`-not-`-f` warning so the host agent never stringifies the id.

## Prevention
Whenever a `gh api` POST/PATCH body field must be a JSON number/boolean/null (an id, a count, a flag), use `-F/--field` (type-aware) — reserve `-f/--raw-field` for genuinely string values. A stringified numeric id is the classic 422 here.
