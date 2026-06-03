---
title: "Linear GraphQL: every {nodes} connection needs first: — incl. workflowStates/tea"
date: "2026-06-03"
track: bug
category: performance
module: plugins/flow-next/skills/flow-next-tracker-sync/references/linear-graphql.md
tags: [fn-52, tracker-sync, linear, graphql, rate-limit, complexity, connection, first, impl-review]
problem_type: build-error
symptoms: "Unbounded GraphQL connection (workflowStates, teams) contradicts the file's own 'first: on every connection' rate-limit rule"
root_cause: "Lookup-shaped connections (workflowStates/teams-by-key) read as scalar so the first: bound was omitted, though they are Relay connections"
resolution_type: fix
---

## Problem
Two impl-review rounds (Major, confidence 100 each) on fn-52.3's Linear GraphQL rung reference: a `workflowStates(...)` query and a `teams(...)` example were written as unbounded GraphQL connections — directly contradicting the SAME file's stated rule "set an explicit `first:` on every connection" for Linear's complexity-based rate limit. The author bounded the obvious list/paging connections (`labels(first:50)`, `comments(first:$first)`) but missed the two "lookup" connections that feel scalar (a team's workflow states; a single team by key).

## What Didn't Work
Bounding only the connections that obviously return many items. `workflowStates` and `teams(filter:{key})` read like point lookups, so the `first:` requirement was overlooked — but in Linear's GraphQL schema they are connections (return `{ nodes }`) and count against the complexity budget like any other.

## Solution
Every Linear GraphQL field that returns `{ nodes }` is a connection and MUST carry an explicit `first:` — including small/lookup ones: `workflowStates(first:100, ...)`, `teams(first:1, filter:{key})`. Fixed in linear-graphql.md plus the mirrored shapes in linear-ladder.md (status-map prose + parity table). Verified by grepping all three files for connection-shaped fields.

## Prevention
When writing/reviewing Linear (or any Relay-style) GraphQL, grep the diff for every `{ nodes` / connection field and confirm each has `first:` — do not exempt "lookup" connections (`workflowStates`, `teams`, `users`, `labels`, `issues`). A file that states a "first: on every connection" rule should be swept against its own rule before review. MCP `limit:` params (e.g. `list_comments(limit:250)`) are NOT GraphQL connections and need no `first:`.
