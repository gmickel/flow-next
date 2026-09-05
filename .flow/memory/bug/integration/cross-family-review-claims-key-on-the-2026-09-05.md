---
title: "Cross-family review claims key on the writer's model family, never the host name"
date: "2026-09-05"
track: bug
category: integration
module: plugins/flow-next/docs
tags: [review-backend, claude, cross-family, docs, fn-221]
problem_type: integration
symptoms: "codex fan-out NEEDS_WORK on all three axes: backend docs called claude reviews cross-family per host while Cursor/Droid/OpenCode can run Claude writers"
root_cause: independence claim written per host name instead of per writer model family; multi-family hosts break it
resolution_type: fix
related_to: [bug/integration/adding-a-review-backend-sweep-all-2026-06-29, bug/integration/backend-special-case-in-a-shared-helper-2026-09-05, bug/integration/headless-review-backend-error-envelope-2026-09-05]
---

## Problem
Documenting the `claude` review backend (fn-221.4), every overview passage called the review "cross-family" from Codex, Cursor, Grok Build, Droid and OpenCode and "same-family" from Claude Code - keyed on the host name. The codex fan-out flagged it on all three axes: Cursor, Droid and OpenCode can run a Claude session model, so a Claude writer there followed by `review.backend claude` is same-family, and the reach pages for Droid/OpenCode already said so conditionally, so the docs contradicted each other and the reviewer-tier definition (a verdict from the writer's own family is not independent).

## What Didn't Work
Writing the independence claim per host ("From Codex, Cursor, ... the session model is another family").

## Solution
Condition independence on the writer's model family everywhere the backend is described: cross-family when another family's session model wrote the diff, same-family when a Claude model did (always on Claude Code; on Cursor, Droid, OpenCode whenever the session model is a Claude model); same-family reviews stay allowed and receipted. Sites: `docs/orchestration.md` "When `claude` is the cross-family pick", `docs/platforms.md` § Claude Code CLI review backend, `docs/flowctl.md` `### claude`, `docs/reach/{cursor,codex,grok-build}.md`, the CHANGELOG bullet.

## Prevention
When a doc sentence says "cross-family" or "same-family", the subject must be the model family of the writer (session model), never the harness. Before committing a backend docs change, grep the docs tree for `cross-family` and `same-family` (skip the codex mirror) and check each hit names a model family or a writer, not a host list. The reach pages are per-host by design - they may state the host's native family, but a multi-family host (Cursor, Droid, OpenCode) must keep the condition.
