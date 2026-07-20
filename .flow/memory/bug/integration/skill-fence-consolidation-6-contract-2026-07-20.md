---
title: "Skill-fence consolidation: 6 contract regressions (var-atomicity, symlink, dry-r"
date: "2026-07-20"
track: bug
category: integration
module: plugins/flow-next/skills
tags: [skill-prose, fences, dry-run, symlink-safety, fn-110]
problem_type: integration
symptoms: "Review found consolidated fences violating var-persistence, ask-pause, symlink, and dry-run contracts"
root_cause: Fence merging treated bash vars/paths as persistent and repo paths as safe scratch
resolution_type: fix
related_to: [bug/integration/byte-for-byte-spec-contract-branch-2026-07-01, bug/integration/skill-bash-blocks-re-declare-every-2026-07-02]
---

## Problem
fn-110.2 moved skill-prose config reads into captured snapshots and consolidated bash fences; codex impl-review found 6 introduced contract regressions across 3 rounds: (1) a pilot snapshot written under repo-controlled `.flow/tmp` defeated the skill's autonomous symlink defense, (2) a merged make-pr fence embedded `: "ask user"` no-ops then consumed the asked-for vars (a Bash call cannot pause for AskUserQuestion), (3) plan-review's now-authoritative workflow fences set `SPEC_ID` in one fence and consumed it in another (vars die across tool calls), (4) per-backend "repeat until SHIP" mini-loops bypassed the shared cap/MAJOR_RETHINK/task-sync fix loop, (5) `VAR="$(cmd || echo '{}')"` APPENDED the fallback to partial JSON a failing producer printed, (6) dry-run ticks persisted the snapshot file, violating the mutate-nothing contract.

## What Didn't Work
Fixing cleanup terminal-by-terminal (round 2 covered 2 of 4 dry-run exits; the reviewer found the NO_WORK exits still leaked).

## Solution
plugins/flow-next/skills: pilot snapshot moved to `${TMPDIR}/flow-pilot-config-<repo-hash>.json` recomputed per fence (flow-next-pilot/SKILL.md); make-pr fences exit with a `NEED_INPUT:` marker and are re-run with the value preset (flow-next-make-pr/workflow.md); plan-review made each backend ONE atomic dispatch fence + re-declared `SPEC_ID` in every status fence + returned verdicts to the single shared Fix Loop (flow-next-plan-review/workflow.md); land used `if ! VAR=$(cmd); then VAR='{}'; fi` (flow-next-land/workflow.md:53); dry-run cleanup centralized as a verdict-contract rule ("at EVERY terminal", the SETUP_STALE pattern) instead of per-site rm lines.

## Prevention
When editing skill prose fences: (a) never write agent scratch under repo-controlled paths (`.flow/tmp` symlink vector) - use `${TMPDIR}` with a deterministic recomputed name; (b) any var consumed in a fence must be (re)declared in THAT fence; (c) ask-the-user steps must sit BETWEEN fences with an explicit exit marker + re-run rule; (d) capture fallbacks must replace, never append (`if ! VAR=$(...)`); (e) contracts that apply to "every terminal" belong in the verdict contract once, not sprinkled per site. Structural tests in plugins/flow-next/tests/test_skill_prose_diet.py pin all of these.
