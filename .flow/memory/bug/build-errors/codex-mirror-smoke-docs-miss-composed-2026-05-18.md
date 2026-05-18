---
title: Codex mirror smoke docs miss composed transform output (abort + Other)
date: "2026-05-18"
track: bug
category: build-errors
module: agent_docs/local-dev.md
tags: [sync-codex, codex, mirror, fn-45, smoke-docs, AskUserQuestion, abort-option]
problem_type: build-error
symptoms: Smoke docs claim N options where post-transform mirror has N+1 (final Other - type your own answer added by sync transform)
root_cause: Authored invariants from spec acceptance alone without grepping post-sync mirror to verify composed transform output
resolution_type: fix
related_to: [bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18, bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18]
---

## Problem
fn-45.4's `agent_docs/local-dev.md` Codex plain-text smoke procedure documented the migration-prompt invariant as having 4 options with `4. abort` as the final option. The reviewer caught a contract drift: fn-45.2 added `abort` as the 4th canonical option AND the fn-45.1 transform appends `N+1. Other — type your own answer` as a final freeform-input option. Rendered prompt has 5 numbered options, not 4. Authoring docs that span two upstream tasks (.1 transform + .2 abort) without re-checking the combined rendered output produced an invariant the reader would test against and find broken.

## What Didn't Work
Authoring the smoke procedure by reading the spec acceptance criteria alone (R4 for abort, R2 for Other-option) without inspecting the *actual* post-sync mirror at `plugins/flow-next/codex/skills/flow-next-setup/workflow.md`. The transform behavior and the abort-option are described in separate spec sections; their composition is only visible by reading the regenerated mirror.

## Solution
Updated `agent_docs/local-dev.md` smoke section to enumerate all 5 expected options explicitly (`1. Migrate now`, `2. Defer`, `3. Suppress permanently`, `4. abort`, `5. Other — type your own answer`) and changed the count from "4 numbered options" to "5 numbered options". The fn-45 spec's Decision Context made the additive composition clear in retrospect — should have grepped the post-sync mirror first.

## Prevention
When docs describe rendered behavior that's the composition of multiple sync-time transforms or canonical edits across tasks, **inspect the post-sync Codex mirror file** for the relevant skill before authoring the invariant. Don't synthesize the expected output from the spec acceptance criteria alone — the transform composition is only visible in the regenerated artifact. Same applies to any "post-X expected behavior" smoke doc where X spans multiple upstream tasks.
