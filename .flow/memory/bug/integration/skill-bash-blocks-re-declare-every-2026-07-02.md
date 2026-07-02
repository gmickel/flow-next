---
title: "Skill bash blocks: re-declare EVERY literal path per block (vars die across tool"
date: "2026-07-02"
track: bug
category: integration
module: plugins/flow-next/skills
tags: [path-persistence, skill-authoring, rp-review, fn-81]
problem_type: integration
symptoms: "RP review NEEDS_WORK: send block used $PROMPT_FILE from a prior block — empty path at runtime"
root_cause: bash vars do not survive across tool calls; block re-declared only one of two paths it used
resolution_type: fix
related_to: [bug/integration/ceremony-validation-must-read-persisted-2026-06-28, bug/integration/heredoc-built-json-breaks-on-free-form-2026-06-05]
---

## Problem
While implementing fn-81.2's file-composition pattern (RP review prompts built across multiple bash blocks), the send block re-declared `RESPONSE_FILE` but still referenced `$PROMPT_FILE` from the earlier build block. Bash vars do not survive across tool calls, so an agent following the docs literally would run `chat-send --message-file ""`. RP impl-review caught it (Major, confidence 100) — the diff violated the exact path-persistence rule it was introducing.

## What Didn't Work
Relying on "the agent will probably run build+send in one block". The docs present them as separate fenced blocks, and any block that re-declares ONE path while borrowing another is self-contradictory.

## Solution
Every separately-runnable bash block re-declares EVERY literal path it references, with a `# same literal path from the build block` comment. Fixed in all three RP send blocks: `flow-next-impl-review/workflow-rp.md`, `flow-next-plan-review/workflow.md`, `flow-next-spec-completion-review/workflow-rp.md` (commit 23797981).

## Prevention
When authoring skill markdown with multi-block bash flows: audit each fenced block in isolation — any `$VAR` not assigned inside that block is a cross-tool-call leak. A partial re-declaration (one path re-declared, another borrowed) is the tell-tale smell.
