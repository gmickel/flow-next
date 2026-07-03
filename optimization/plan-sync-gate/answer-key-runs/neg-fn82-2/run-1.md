Line 17 of fn-82.5 is the R12 token table — it lists tracker-sync `SKILL.md+steps.md` and qa `SKILL.md+workflow.md` as **pinned whole-file sets** for a `wc -c` before/after measurement. That's a forward-looking measurement of fn-82.2's own byte reduction, not a line-number/API reference that could go stale. No drift.

All checks complete. Writing the Phase 6 summary.

---

Drift detected: no

**Phase 1–4 — reference drift (fn-82.3, fn-82.4, fn-82.5):** none.

fn-82.2 was Class-1 archaeology confined to **tracker-sync, qa, map, memory-migrate** (canonical only) — pure deletion/prose-substitution, no behavior, no renamed API/variable/data-structure. The task was deliberately scoped off the downstream tasks' files ("audit + prospect archaeology ride with fn-82.3 to avoid file overlap"), so there is no shared surface to go stale:

- **fn-82.3** (impl-review, spec-completion-review, interview, plan/steps.md, audit, prospect) — zero references to fn-82.2's files. Its own `audit flowctl.py:172 / workflow.md:561` line refs are untouched by fn-82.2 (audit was correctly deferred to fn-82.3).
- **fn-82.4** (make-pr, capture, optimization/*) — zero references.
- **fn-82.5** — the only mention (line 17) is the R12 token table listing tracker-sync `SKILL.md+steps.md` and qa `SKILL.md+workflow.md` as **whole-file `wc -c` pinned sets**. That measures fn-82.2's byte reduction; no line-number/symbol reference exists to stale.

New artifact `agent_docs/tracker-sync-spikes.md` confirmed present (spike relocation); it lives outside the plugin tree, is never mirrored, so fn-82.5's mirror-regen/parity is unaffected.

**Phase 3b — glossary / decisions / strategy:** not a husk (38 terms, 2 decisions, populated STRATEGY) — all three sub-checks run, all clear.
- **3b.1 glossary:** all 38 entries have empty `avoid` → no in-flight rename signal.
- **3b.2 decisions:** no overrides. Decision `tracker-sync-is-projection-not-2026-06-01` — fn-82.2 *preserved* its direction (rewrote the `(fn-66)` tag into prose "a real merge is the sole Done driver" per its own done summary), so no contradiction. Decision `factory-droid-platform-status-2026-05` — its Consequences name capture/make-pr/interview/plan/setup/hooks/platforms.md, none of which fn-82.2 touched.
- **3b.3 strategy:** no contradiction (prompt-diet archaeology serves Ralph / Cross-platform parity / Self-improving per the spec's own Strategy Alignment; added zero deps → zero-dep track intact); no track-rename candidates.

**Traceability:** parent spec has a `## Requirement coverage` table; fn-82.2's coverage (R5 full, R6 partial — qa/map/mm, audit → fn-82.3) matches the table's existing rows exactly. No row affected → no update.

Would update: nothing. Decision overrides flagged for review: none. Strategy drift flagged for review: none.

No files modified (DRY_RUN).