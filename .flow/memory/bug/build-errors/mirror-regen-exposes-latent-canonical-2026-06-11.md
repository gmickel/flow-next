---
title: "Mirror regen exposes latent canonical gaps: path rewrites, .flow persistence, di"
date: "2026-06-11"
track: bug
category: build-errors
module: "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-land/workflow.md"
tags: [fn-60, sync-codex, codex-mirror, land, flow-persistence, tracker-dispatch, ledger, review-feedback, release]
problem_type: build-error
symptoms: "4 NEEDS_WORK rounds on a docs/release task: broken /skills/ path in Codex mirror, spec close never pushed, free-prose tracker dispatch, split ledger writes"
root_cause: Mirror regen reviewed as introduced content; sync-codex lacked a generic /skills/ rewrite+validator; land tail mutated .flow with no persistence story
resolution_type: fix
related_to: [bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05, bug/build-errors/codex-mirror-smoke-docs-miss-composed-2026-05-18, bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/docs-activation-command-for-string-enum-2026-06-05, bug/build-errors/fn-44-review-cycle-lessons-2026-05-21, bug/build-errors/r2-ask-block-must-never-anchor-in-2026-06-10, bug/build-errors/skill-adding-version-bump-leaves-stale-2026-06-05, bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11, bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem
The fn-60.3 release/docs pass regenerated the Codex mirror with the new land skill, and the codex impl-review pulled four NEEDS_WORK rounds out of it. The recurring theme: a release task that regenerates the mirror exposes the WHOLE mirrored skill content to review as "introduced", surfacing latent gaps in the canonical skills it mirrors. Concrete review-caught gaps: (1) the resolve-pr mirror's `SCRIPTS="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/skills/..."` expanded to a broken `/skills/...` path inside Codex — sync-codex.sh only rewrote two hardcoded skill paths (worktree-kit, ralph-init) and had no catch-all or validator; (2) land's post-merge tail mutated `.flow` (spec close) without ever committing/pushing it — the dirty-tree guards exclude `.flow/`, so the un-persisted close would sit silently while discovery (`status=="open"`) could never re-enter; (3) a free-prose tracker-sync dispatch instead of the fn-57 `operation: <verb> <id>, event: <key>` grammar; (4) ledger writes split so `decision_at_push` was only written on one of three push paths, breaking stale-approval detection for resolve/rebase pushes.

## What Didn't Work
Treating the mirror regen as a mechanical step ("validators green = done"). The token-level validators passed every round; the breaks were semantic: unrewritten path vars, state mutated but never persisted, dispatch shapes that drift from the established lifecycle grammar.

## Solution
- sync-codex.sh: generic catch-all rewrites `${...PLUGIN_ROOT...}/skills/` → `$HOME/.codex/skills/` AFTER the specific rules (specific destinations win since sed -e exprs run in order), `$HOME` not `~` so it expands inside double quotes; plus a RED validator failing on any surviving plugin-root /skills/ ref (scripts/sync-codex.sh ~:232, ~:1540).
- land workflow tail: spec close → tracker touchpoint → ONE `.flow` persistence commit + push (covers close AND tracked sync state), `git pull --rebase` retry, and on still-failing push `git reset --hard HEAD^` of the .flow-only commit so the merged-but-unclosed re-entry path stays reachable (plugins/flow-next/skills/flow-next-land/workflow.md 3.5).
- Lifecycle dispatches use the fn-57 grammar verbatim: `skill: flow-next-tracker-sync (operation: push <spec-id>, event: land.merged)`.
- Centralize ledger post-push writes in ONE canonical snippet (sha + decision) that all push paths reference.

## Prevention
- When a release regenerates the Codex mirror with a NEW skill, expect the reviewer to treat the whole mirror as introduced — pre-audit the mirrored skill's path vars (`grep -rE '(PLUGIN_ROOT)[^ ]*/skills/' codex/skills/`) and any state-mutating steps for a persistence/commit story before sending to review.
- Any skill step that mutates `.flow` outside the worker-commit flow needs an explicit commit+push+rollback story — the `.flow/`-excluding dirty-tree guards make silent stranding the default failure mode.
- Skill-dispatches-skill must reuse the existing dispatch grammar (grep work/make-pr for `operation:` + `event:`), never free prose.
