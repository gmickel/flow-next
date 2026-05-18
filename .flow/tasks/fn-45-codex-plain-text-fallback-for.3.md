---
satisfies: [R5]
---

## Description

Audit `plugins/flow-next/skills/flow-next-setup/workflow.md` for safe-default behavior on non-critical setup preferences: preserve existing config when set; fold unset optional config into one grouped numbered prompt or skip with a "configure later via …" summary line; preserve repo-custom docs (no clobber of customized CLAUDE.md / AGENTS.md / .flow/usage.md sections).

**Size:** S

**Files:**
- `plugins/flow-next/skills/flow-next-setup/workflow.md`
- `plugins/flow-next/codex/skills/flow-next-setup/workflow.md` (regenerated after canonical edits — verify mirror)

## Approach

- Walk `flow-next-setup/workflow.md` end-to-end.
- For each `flowctl config set` / `flowctl config get` site: confirm the workflow reads the existing value first and only sets when unset (or asks via AskUserQuestion if optional).
- For doc-generation sites (CLAUDE.md / AGENTS.md / .flow/usage.md additions): confirm the workflow checks for an existing flow-next section and merges/skips instead of clobbering. The "preserve customized Flow sections" invariant is the load-bearing check.
- For optional unset config: prefer one grouped `AskUserQuestion` with multi-select over many single-question prompts. If grouping isn't possible, skip with a footer like `Configure later via \`flowctl config set <key> <value>\``.

## Investigation targets

**Required**:
- `plugins/flow-next/skills/flow-next-setup/workflow.md` (full file — ~400 lines)
- `plugins/flow-next/scripts/flowctl.py` — search for `config get/set` semantics if unclear about idempotency

**Optional**:
- `plugins/flow-next/skills/flow-next-setup/SKILL.md` — front-matter / role description
- `CLAUDE.md` template content that setup injects — confirm it has a recognizable header for the preserve-on-rerun check

## Key context

- This task is audit-and-patch, not refactor. Most likely outcome: 1-3 small edits to add "if already set, skip" guards or to merge multiple prompts into one grouped prompt. If audit finds the workflow already complies, document the finding in the task summary and ship a no-op-edit task.
- "Repo-custom docs" — the setup writes specific marker comments / sections into CLAUDE.md / AGENTS.md / .flow/usage.md. Preserving customization means: if a marker exists, update only between the markers; if a customized variant is detected (deviation from canonical template), ask before overwriting.
- Coordinate with fn-45.2's destructive-action audit: any "overwrite existing doc?" prompt this task identifies should have an `abort` option (fn-45.2's scope).
- Re-run `./scripts/sync-codex.sh` after canonical edits to ensure the Codex mirror reflects the changes and passes validation guards from fn-45.1.

## Acceptance

- [ ] Audit of `flow-next-setup/workflow.md` complete; behavior on existing-set config documented (in-place edits or a no-op summary if already compliant).
- [ ] Optional unset config: grouped into a single `AskUserQuestion` where feasible, OR a "configure later via …" footer where not.
- [ ] Repo-custom docs preservation: explicit "if marker block exists, update only between markers; if customized, ask" logic.
- [ ] After canonical edits, `./scripts/sync-codex.sh` runs cleanly; Codex mirror for setup regenerates without new validation-guard failures.
- [ ] No regression: `smoke_test.sh` (covers setup-related flowctl init/config behavior) stays green.

## Done summary
Audited `flow-next-setup/workflow.md` for R5 acceptance: (1) existing config is now explicitly preserved by Step 6d (per-question gating on `CURRENT_*` empty, with the preserve-existing-config contract documented in prose so it's auditable); (2) `.flow/usage.md` (Step 4) and CLAUDE.md / AGENTS.md marker blocks (Step 7) now byte-compare against canonical and `AskUserQuestion` (Keep / Overwrite / abort) before replacing customized content — no silent clobber, and content outside the BEGIN/END FLOW-NEXT markers is explicitly invariant. Codex mirror regenerated cleanly via `./scripts/sync-codex.sh`; all 130 smoke tests pass; codex impl-review SHIP first-pass.
## Evidence
- Commits: be10a081a8aeb5bb36ab65876473b3fbdb208cff
- Tests: bash plugins/flow-next/scripts/smoke_test.sh (130/130 pass, baseline + post-edit), ./scripts/sync-codex.sh (regenerated codex mirror cleanly; all validation guards pass), sync-codex.sh idempotency (md5sum-twice → IDENTICAL), flowctl codex impl-review fn-45-codex-plain-text-fallback-for.3 --base e536b62 → VERDICT=SHIP (first-pass)
- PRs: