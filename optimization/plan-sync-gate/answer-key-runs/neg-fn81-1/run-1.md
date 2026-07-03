I have everything needed. Both decision entries confirm no contradiction with the completed task, and my exploration confirms the implementation matches the spec. Let me record my analysis findings.

**Phase 1–2 (re-anchor + explore):** fn-81.1's done summary and evidence commit `94924748` touched exactly the two planned files — `flow-next-capture/workflow.md` and `flow-next-interview/SKILL.md`. I read both. Implementation matches the spec: single-emission Write pattern, `spec set-plan/set-acceptance/set-spec --file <literal path>`, edit-cycle Read rule, capture tracker gate `LEAF=` single-fetch (`workflow.md:791`), interview duplicate-fetch collapse (`SKILL.md:736`).

**Phase 3 (drift):** One benign in-flight path-naming refinement — the spec §Approach described a generic `flow-<skill>-draft-<spec-id>-<suffix>.md`; capture actually uses `flow-capture-draft-<working-title-slug>-<suffix>.md` (no spec-id exists yet on the new-spec branch — documented at `workflow.md:467`) and interview uses `flow-interview-<kind>-<id>-<suffix>.md`. This is fully within the path-persistence *rule* the downstream tasks reuse. No downstream task spec hardcodes fn-81.1's literal path strings.

**Phase 3b (glossary/decisions/strategy):** not a husk. 3b.1 — every glossary entry has an empty `avoid` list ⇒ zero rename signal. 3b.2 — both decisions active; neither's concrete-code references (`docs/platforms.md`/`.factory-plugin` for Droid; tracker projection semantics for the other) are contradicted by fn-81.1's skill-markdown efficiency edits. 3b.3 — fn-81.1 *aligns* with Cross-platform-parity + Self-improving tracks; no contradiction, no track-rename.

**Phase 4 (downstream .2/.3/.4):** none reference a stale name/API/path from fn-81.1. Task .4's fixed-path grep list (`/tmp/spec.md`, `/tmp/acc.md`, `/tmp/desc.md`) targets the OLD paths fn-81.1 *correctly removed* — the list stays valid, expecting zero hits. Task .2 reuses the generic literal-path convention (implemented as described); task .3's canonical LEAF reference points at `work/SKILL.md:184-190`, not fn-81.1. **Phase 4b:** CROSS_SPEC is false → skipped. **Traceability:** `satisfies:[R1,R2,R7,R13]` matches the coverage table; no scope change → no table edit.

---

Drift detected: no

- fn-81.1 implemented capture + interview single-emission writes exactly as specified (Write-once render as read-back, Edit-cycle Read rule, `spec set-plan/set-acceptance/set-spec --file <literal path>`, capture `LEAF=` tracker gate, interview duplicate-fetch collapse). Evidence commit `94924748`; RP impl-review SHIP.
- The only spec-vs-impl divergence is a documented path-slug refinement (`flow-capture-draft-<working-title-slug>` / `flow-interview-<kind>-<id>` vs the spec's generic `flow-<skill>-draft-<spec-id>`), which honors — rather than breaks — the path-persistence rule downstream tasks depend on.

No downstream task specs reference stale names/APIs/paths — no updates needed:
- fn-81.2: reuses the generic literal-path + single-entry conventions (accurate); its own sites (`rp prompt-get`, `chat-send`, `MAX_REVIEW_ITERATIONS`, `git add -A`) are untouched by fn-81.1.
- fn-81.3: canonical LEAF reference correctly cites `flow-next-work/SKILL.md:184-190`, not fn-81.1; `--flow-file` / make-pr / deps / prime sites unaffected.
- fn-81.4: fixed-path grep list (`/tmp/spec.md`, `/tmp/acc.md`, `/tmp/desc.md`) still valid — those paths were the ones fn-81.1 removed, so zero-hit expectation holds.

Would update (DRY RUN): none.
Would update traceability: none (`## Requirement coverage` table unaffected; R-IDs preserved).
Decision overrides flagged for review: none.
Strategy drift flagged for review: none.

No files modified (DRY_RUN=true).