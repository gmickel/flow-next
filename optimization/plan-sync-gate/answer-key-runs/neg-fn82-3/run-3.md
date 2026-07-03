All confirmations pass. The review skills delegate Phase 0 to `workflow-common.md` (single `review-backend` call — validates fn-82.5's `SKILL.md+workflow-common.md` pin), and both cross-refs (plan `steps.md:276`, `docs/spec-template.md:27`) repoint to the new reference. Analysis complete.

---

Drift detected: no

**Completed task fn-82-skill-prompt-diet-progressive.3** (satisfies R3, R6, R7) landed as summarized. Implementation matches what the two downstream tasks assume:

- Review skills (impl-review, spec-completion-review) delegate the executable Phase 0 to `workflow-common.md` → one `flowctl review-backend` call per run; SKILL.md keeps intent + at-a-glance only.
- Interview template-discovery walker single-sourced verbatim, linked one hop from interview `SKILL.md`; plan `steps.md` + `docs/spec-template.md` both repointed; aux-section rule defined once.
- Audit Replace/supersede/mark-stale flows delegate to `phases.md`; prospect python-picker defined once in the Preamble; `flowctl.py` line refs + task-N scaffolding stripped. Canonical-only.

**One divergence from the plan's literal wording — benign, no downstream impact:** the plan's Quick-commands note cited the skill-dir mirror path (`sync-codex.sh:133-136`) for "new `references/*.md` under skill dirs," but the walker actually landed at plugin-level `plugins/flow-next/references/spec-template-discovery.md`. That dir is *also* wholesale-mirrored (`sync-codex.sh:155-157`, byte-identical), and the walker carries an inline 4-way plugin-root fallback `${CLAUDE_PLUGIN_ROOT:-${DROID_PLUGIN_ROOT:-${CODEX_HOME:-$HOME/.codex}}}` so the un-rewritten mirror copy still resolves on Codex. Net outcome (auto-mirror + parity on `sync-codex.sh` run) is unchanged.

**Downstream check (fn-82.4, fn-82.5):**
- fn-82.4 (make-pr + capture) — zero file overlap with fn-82.3; no stale references.
- fn-82.5 — mirror step is generic (`bash scripts/sync-codex.sh`, "includes the NEW references/*.md files") and covers the new file via the plugin-references copy; token-table pins all still accurate (impl-review `SKILL.md+workflow-common.md`; interview `SKILL.md` — walker moved to an on-demand ref, so always-loaded set unchanged; audit `SKILL.md+workflow.md+phases.md`; prospect `SKILL.md+workflow.md`); gate-contract greps target only the work-bridge + pilot-qa gates (fn-82.1), untouched by fn-82.3.

**Phase 3b (glossary / decisions / strategy):** all clear.
- Glossary: 38 terms, every entry `avoid: []` → no rename aliases to propagate.
- Decisions: 2 active (`factory-droid-platform-status`, `tracker-sync-is-projection`); neither's named module (`platforms.md` / strategy+tracker-sync files) is touched by this dedupe → no override flagged.
- Strategy: dedupe reduces always-loaded weight — explicitly serves *Ralph autonomous mode*, *Cross-platform parity*, *Self-improving through normal work*; adds no dependency/SaaS → aligned, no contradiction, no track-rename.

Would update (DRY RUN): none — no downstream task spec carries a reference made stale by this task.
Traceability: parent spec `## Requirement coverage` already maps R3/R6/R7 → fn-82.3; matches the task's `satisfies`, no row change.

No files modified (DRY_RUN=true).