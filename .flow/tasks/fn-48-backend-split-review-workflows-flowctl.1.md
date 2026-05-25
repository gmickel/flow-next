---
satisfies: [R4a, R6, R7]
---

## Description

Drop the dead `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}` fallback chain from the Codex mirror's FLOWCTL prelude. Inside Codex, neither `DROID_PLUGIN_ROOT` nor `CLAUDE_PLUGIN_ROOT` is ever set — only `$HOME/.codex` resolves. The chain is dead code in the mirror only; the canonical files keep their form for now (R4b decides their fate after R8).

**Size:** S
**Files:** `scripts/sync-codex.sh` (line 179 rewrite rule), `plugins/flow-next/codex/skills/*/SKILL.md` (regenerated output).

## Approach

- Edit the sed rewrite rule at `scripts/sync-codex.sh:179` so the Codex mirror emits a direct form (e.g. `FLOWCTL="$HOME/.codex/scripts/flowctl"` or `FLOWCTL="${CODEX_PLUGIN_ROOT:-$HOME/.codex}/scripts/flowctl"`). Pick the form that matches Codex's actual env conventions in 2026; `$HOME/.codex` is the install target per `scripts/install-codex.sh`.
- Regenerate the mirror: `./scripts/sync-codex.sh`.
- Diff the mirror: should be a one-substitution change repeated across every Codex SKILL.md / workflow.md that had the chain.
- Run smoke: `bash plugins/flow-next/scripts/smoke_test.sh`.

This is the **early proof point** for fn-48 — single-rule edit + regen, validates the sync-codex.sh rewrite pattern end-to-end before any of the larger backend-split work begins.

## Investigation targets

**Required**:
- `scripts/sync-codex.sh:170-205` — the existing rewrite rules block, especially line 179 (FLOWCTL prelude rewrite).
- `plugins/flow-next/codex/skills/flow-next-work/SKILL.md` — sample post-rewrite output to verify the new form propagates.
- `scripts/install-codex.sh` — confirms `$HOME/.codex` is the canonical install target Codex resolves against.

**Optional**:
- One other canonical SKILL.md that uses the prelude (e.g. `plugins/flow-next/skills/flow-next-plan/SKILL.md`) to see what's being rewritten from.

## Acceptance

- [ ] `scripts/sync-codex.sh:179` rewrite rule emits a direct `$HOME/.codex`-based FLOWCTL form (no dead fallback chain).
- [ ] Mirror regenerates cleanly: `./scripts/sync-codex.sh` runs without errors.
- [ ] Every `plugins/flow-next/codex/skills/*/SKILL.md` that uses the prelude shows the new form (verify with `grep`).
- [ ] `bash plugins/flow-next/scripts/smoke_test.sh` is green across all skills (no regression).
- [ ] The canonical files (`plugins/flow-next/skills/*/`) are NOT modified — this task only touches the mirror's rewrite rule.

## Done summary

_(filled by `/flow-next:work` when the task completes)_

## Evidence

_(filled by `/flow-next:work` — commit hashes + test commands run)_
