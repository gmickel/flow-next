I've completed all phases. Here's my analysis:

**Phase 1–2 (re-anchor + explore):** fn-81.1 converted capture (`flow-next-capture/workflow.md`) and interview (`flow-next-interview/SKILL.md`) to the single-emission write pattern. I read the actual implementation of both touched files.

**Phase 3 (drift):** The implementation matches the spec's described approach on every convention the downstream tasks depend on:

| Convention downstream tasks assume | Actually built |
|---|---|
| Path-persistence rule (literal agent-composed path, no cross-tool-call shell var) | ✓ capture `${TMPDIR:-/tmp}/flow-capture-draft-<slug>-<suffix>.md`; interview `flow-interview-<kind>-<id>-<suffix>.md` |
| flowctl consumes `--file <literal path>` | ✓ `spec set-plan/set-acceptance/set-spec --file` |
| LEAF single-fetch at tracker gate | ✓ `LEAF="$(...config get tracker.perEvent.capture...)"` |
| Edit-cycle Read rule | ✓ stated in both files |
| Fixed `/tmp/spec.md`, `/tmp/acc.md`, `/tmp/desc.md` removed | ✓ gone |

The downstream tasks reference these via *generic* conventions (the path-persistence rule, the canonical LEAF pattern at `work/SKILL.md:184-190` which fn-81.1 never touched, `--file` consumption) — no stale variable name, API signature, or data-structure assumption from the completed task leaks into any downstream spec. Line-number shifts in the touched files (e.g. tracker gate `:786`→`:791`) don't affect downstream tasks, which cite their own files.

**Phase 3b:** Not husk (glossary 38 terms, decisions 2, strategy populated) — ran all three:
- **3b.1 glossary renames:** all 38 entries have empty `avoid` lists → no in-flight rename possible.
- **3b.2 decision overrides:** Decision 1 (Droid platform) names `flow-next-interview/SKILL.md`, which fn-81.1 touched — but the change is orthogonal (single-emission writes never re-add the `.factory-plugin` fallback and preserve the `DROID_PLUGIN_ROOT` prelude the decision says to keep). Decision 2 (tracker-sync=projection) — the capture/interview tracker gates still just project via the config leaf; nothing makes the tracker drive flow state. No contradictions.
- **3b.3 strategy drift:** pure skill-markdown token plumbing; no SaaS/dep/external service added; the parent spec's own Strategy Alignment cites only live tracks (Ralph, Cross-platform parity, Self-improving) — no contradiction, no track rename.

**Phase 4:** Read all three downstream specs (fn-81.2/.3/.4). None need updating. **Phase 4b:** skipped (CROSS_SPEC=false). **Phase 5:** DRY_RUN + no drift → no edits; traceability table already correctly maps R1/R2/R7/R13 to fn-81.1.

---

Drift detected: no

- fn-81.1 implemented capture + interview exactly per the spec's Approach 1 / R1 / R2 / R7 / R13: literal-path single-emission writes, `--file` consumption, tracker-gate LEAF single-fetch, edit-cycle Read rule, duplicate interview fetch collapsed, fixed `/tmp/*.md` paths removed.
- All conventions the downstream tasks (fn-81.2, fn-81.3, fn-81.4) build on are stable and present as assumed — the path-persistence rule, the canonical LEAF pattern (in untouched `work/SKILL.md`), and `--file` consumption. No downstream spec references a name/API that changed.

Would update (DRY RUN):
- Nothing — no downstream task carries a stale reference.

Would update traceability (DRY RUN):
- Nothing — the `## Requirement coverage` table already maps R1/R2 → fn-81.1 and R7/R13 → fn-81.1 (+ later tasks); fn-81.1's `satisfies: [R1, R2, R7, R13]` matches.

Decision overrides flagged for review:
- None.

Strategy drift flagged for review:
- None.

No files modified.