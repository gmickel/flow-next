---
title: Factory Droid platform status — 2026-05
date: "2026-05-25"
track: knowledge
category: decisions
module: plugins/flow-next/docs/platforms.md
tags: [droid, factory-ai, cross-platform, fn-48, interop, plugin-root, hooks, Execute]
applies_when: Factory Droid platform status — 2026-05
---

## Problem

flow-next has carried cross-platform scaffolding for Factory Droid since 2026-02-03 (commits 103c708 → 8958bb8, releases 0.20.10 → 0.20.19). Three pieces are involved:

1. `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` env-var fallback in every flowctl-invoking bash block (30+ canonical files).
2. `.factory-plugin/plugin.json` fallback (referenced from 9 canonical files but **never actually present in this repo**).
3. `"matcher": "Bash|Execute"` regex-OR in hooks.json (Claude → `Bash`, Droid → `Execute`).

Between 2026-02-03 and 2026-05-25 (releases 1.0.0 → 1.1.11), zero Droid-specific work shipped. Surface evidence — missing `.factory-plugin/` directory anywhere in the repo, no Droid release notes, no Droid smoke tests — suggested the scaffolding might be dead. fn-48.6 needs an unambiguous answer to decide R4b's exact form (Path A keep+consolidate vs Path B drop entirely).

## What Didn't Work

The naive read of surface evidence (no `.factory-plugin/` in repo + no recent commits = Droid is dead) was wrong on the most important axis. Droid IS still divergent on env-var name and tool name; what's actually dead is just the `.factory-plugin/plugin.json` fallback (because Droid auto-translates Claude Code plugins).

## Solution

Web-verified against Factory's primary docs (`docs.factory.ai/cli/configuration/plugins`, `docs.factory.ai/cli/configuration/hooks-guide`, `docs.factory.ai/reference/hooks-reference`, and `github.com/Factory-AI/factory-plugins` on 2026-05-25):

**Finding 1 — `DROID_PLUGIN_ROOT` (still required).** Factory docs explicitly document `${DROID_PLUGIN_ROOT}` as the canonical plugin-root env var. `${CLAUDE_PLUGIN_ROOT}` is documented as: *"Alias for `${DROID_PLUGIN_ROOT}` (Claude Code compatibility)"*. Both vars resolve on Droid. The conservative `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` fallback chain is correct on both platforms. **Keep it.**

**Finding 2 — `.factory-plugin/plugin.json` (redundant for Claude-first plugins).** Factory's marketplace plugins all ship `.factory-plugin/plugin.json` natively. BUT Factory docs explicitly state: *"Droid is compatible with plugins built for Claude Code. If you find a Claude Code plugin you'd like to use, you can install it directly - the plugin format is interoperable."* flow-next is a Claude-first plugin with `.claude-plugin/plugin.json` only — Droid's interop layer handles it directly. **The fallback to `.factory-plugin/plugin.json` is dead code.** Remove the references from canonical files.

**Finding 3 — `Execute` matcher (still required).** Factory hooks-reference explicitly lists `Execute` as the canonical tool name for shell commands. `Bash` is NOT a recognized matcher in Droid. The `"Bash|Execute"` regex-OR pattern is required for a single hooks.json to fire on both platforms. **Keep it.**

**R4b verdict — Path A (modified):**
- KEEP the `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` prelude pattern, but consolidate to once-per-skill (the actual T6 work).
- KEEP the `Bash|Execute` hook matcher in `hooks/hooks.json`.
- DROP the `.factory-plugin/plugin.json` fallback in `flow-next-capture/SKILL.md:127`, `flow-next-make-pr/SKILL.md:110`, `flow-next-setup/workflow.md:116`, `flow-next-interview/SKILL.md`, `flow-next-plan/SKILL.md`, and any other canonical references (T6 sweep).
- UPDATE `docs/platforms.md` and `CLAUDE.md` to document the interop mechanism + the redundant-fallback removal (done in this task).
- The `sync-codex.sh:206` rule `'s|\.factory-plugin/plugin\.json|.claude-plugin/plugin.json|g'` becomes a no-op once canonical references are removed, but is harmless to keep as defense-in-depth.

## Prevention

- Standing rule: when adopting cross-platform scaffolding, web-verify the contract at adoption time AND set a calendar nudge for re-verification (or check before any consolidation/refactor).
- For Droid specifically: Factory's interop layer is opinionated about which side translates — Claude-first plugins are Droid-compatible automatically; Droid-first plugins (using `SessionStart`, `SessionEnd`, etc.) are not portable back. Author for the shared subset.
- When surface evidence (missing files, stale commits) suggests dead code, distinguish between "the platform doesn't exist anymore" and "the platform handles this for us now". Different remediation.

## References

- Factory Plugins doc: `https://docs.factory.ai/cli/configuration/plugins`
- Factory Hooks Guide: `https://docs.factory.ai/cli/configuration/hooks-guide`
- Factory Hooks Reference: `https://docs.factory.ai/reference/hooks-reference`
- Factory Building Plugins guide: `https://docs.factory.ai/guides/building/building-plugins`
- Factory-AI/factory-plugins marketplace: `https://github.com/Factory-AI/factory-plugins`
- Original Droid-compat commit: `103c708` (2026-02-03)
- Cross-platform env-var commit: `72068df` (2026-02-03)
- Cross-platform hooks duplicate-entries: `533e44e` (2026-02-03)
- Project-local ralph-guard (final shape): `8958bb8` (2026-02-03, tag flow-next-v0.20.19)
- Spec: `fn-48-backend-split-review-workflows-flowctl` R8
