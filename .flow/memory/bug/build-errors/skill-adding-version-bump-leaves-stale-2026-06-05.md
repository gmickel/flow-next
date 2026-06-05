---
title: Skill-adding version bump leaves stale skill/command counts in JSON manifest des
date: "2026-06-05"
track: bug
category: build-errors
module: "plugins/flow-next/.claude-plugin/plugin.json, .claude-plugin/marketplace.json, plugins/flow-next/.codex-plugin/plugin.json"
tags: [fn-53, version-bump, bump.sh, skill-count, manifest, marketplace, codex-mirror, docs-drift, release]
problem_type: build-error
symptoms: Manifest descriptions still say '25 skills' / '21 commands' after adding a new skill; impl-review flags the count drift and holds the docs R-ID partial
root_cause: bump.sh updates version numbers + README badges but not the prose skill/command counts embedded in the JSON manifest description strings; the README prose count was updated but the three manifests were missed
resolution_type: fix
related_to: [bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05, bug/build-errors/docs-activation-command-for-string-enum-2026-06-05, bug/build-errors/fn-44-review-cycle-lessons-2026-05-21, bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05]
---

## Problem
When a version-bump task adds a NEW skill, the human-readable skill/command counts are spread across **multiple surfaces**, not just the README. The fn-53.6 docs+bump pass updated the root README's prose count ("Twenty-five → Twenty-six agent-native skills") but missed the three machine-readable manifest descriptions that also carry counts:
- `.claude-plugin/marketplace.json` (`description`: "...21 subagents, 21 commands, 25 skills.")
- `plugins/flow-next/.claude-plugin/plugin.json` (`description`)
- `plugins/flow-next/.codex-plugin/plugin.json` (`longDescription`: "...21 subagents, 25 skills.")

Impl-review (rp) flagged it P2/confidence-100 and held R12 at `partial` until fixed.

## What Didn't Work
Updating only the README prose count. The manifest descriptions are easy to forget because they are JSON `description`/`longDescription` strings, not an obvious "count" field, and they each phrase the count slightly differently (the codex plugin omits the command count entirely).

## Solution
Before committing a skill-adding bump, sweep ALL count surfaces:
`grep -rn "[0-9]\+ skills\|[0-9]\+ commands\|Twenty-" .claude-plugin/ .agents/ plugins/flow-next/.claude-plugin/ plugins/flow-next/.codex-plugin/ README.md plugins/flow-next/README.md`
Derive the true counts deterministically: skills = `ls -d plugins/flow-next/skills/*/ | wc -l`; commands = `ls plugins/flow-next/commands/flow-next/*.md | wc -l`; subagents = `ls plugins/flow-next/agents/*.md | wc -l`. Update every surface to match, then re-run `./scripts/sync-codex.sh`.

## Prevention
`bump.sh` updates version numbers + README badges but does NOT touch the prose skill/command counts in the JSON manifest descriptions. When a release ADDS or REMOVES a skill/command/agent, treat the count-sweep as a manual checklist item (or add it to a release smoke check). A grep for the old count across all four manifests + both READMEs catches every surface in one pass.
