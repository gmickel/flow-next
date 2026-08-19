---
satisfies: [R4, R7]
---
# fn-160-setup-speed-batched-plumbing-refresh.3 workflow.md split: slim core + per-platform references, wire plumbing, retarget sync transforms

## Description
Split the 1000-line setup `workflow.md` into a slim core + per-platform conditionally-loaded references, wire the new plumbing (`setup detect`, batched `config set`, `setup refresh` entry) into the skill prose, and retarget the sync-codex.sh transforms. Behavior parity is proven by deterministic evidence, not a spot-check (review round 1).

**Size:** M (large-M; cohesive — do not split the split)
**Files:** `plugins/flow-next/skills/flow-next-setup/workflow.md`, new `plugins/flow-next/skills/flow-next-setup/references/questions-<platform>.md` + `references/detection-notes.md` (naming free), `plugins/flow-next/skills/flow-next-setup/SKILL.md`, `scripts/sync-codex.sh`, `plugins/flow-next/tests/optimization/reached-path/setup-routing-evidence.json` (regen), `plugins/flow-next/tests/test_setup_reference_routing.py`, `plugins/flow-next/tests/test_setup_cursor_host.py`, `plugins/flow-next/tests/test_setup_grok_host.py`, `plugins/flow-next/tests/test_model_routing_scaffold.py`, codex mirror (regen)

### Approach
- Core keeps: step order, all gates and consent semantics, the mode-transition table, bash blocks (binding code — memory lesson), and the MUST-read-exactly-one-reference dispatch pattern already used for model-routing/ralph (workflow.md:719-721, 847-856). Move OUT: the five platform variants of the Review and Docs questions (one reference per platform or per question-set), and the Step 0 detection-fixture archaeology (reference consulted only when detection misbehaves; the executable detection bash stays in core).
- Replace Step 6a's probe fences with one `flowctl setup detect --json` call + jq reads; replace Step 7's per-answer `config set` runs with the batched form (task .1). Add the refresh entry: a re-run whose only intent is version refresh routes to `flowctl setup refresh --plugin-root ... --platform ...` (task .2; prose supplies both args) instead of the full ceremony — full ceremony remains the reconfigure path. Wire `flowctl setup usage-record` into the interactive usage.md handling: called after every outcome that leaves a canonical file on disk (missing→written, identical→record-if-absent, user-accepted overwrite) so post-fn-160 installs carry provenance from day one.
- sync-codex.sh:478-537 keys awk/sed rewrites to literal workflow.md strings — retarget each moved anchor to its new file and add a hard-fail guard per moved transform (fn-100 pattern; a transform that no longer matches must fail the sync, not silently no-op). sync copies the whole skill dir (sync-codex.sh:205-208) so new references need no registration.
- Regenerate `setup-routing-evidence.json` (test_setup_reference_routing.py:108-121 hardcodes SKILL.md+workflow.md byte sizes) in the same commit; update prose-location assertions in the host/scaffold tests to the new files.
- **Parity evidence (mandatory, per spec plan decision):** (a) deterministic question/option INVENTORY — extract every ask header, option label, and recommendation marker from the canonical skill AND the post-transform Codex mirror, before and after the split; diff must be empty (regrouping moves land in .4, not here). (b) Scenario walk of the fn-130 frozen matrix (first-install, refresh, customization, marker, question, stamp, host-specific rows) against the split prose, canonical + post-transform. Attach both artifacts to the task evidence.

### Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-setup/workflow.md` — full read; the thing being split
- `scripts/sync-codex.sh:478-537` + `:205-208` — transforms to retarget
- `plugins/flow-next/tests/test_setup_reference_routing.py:108-121` — evidence fixture contract
- `agent_docs/adding-skills.md:26-81` — the two split patterns to follow (prior art b2f6f0e, 06f6e6f)

**Optional:**
- `.flow/specs/fn-130-reached-path-skill-prompt-optimization.md` — frozen matrix + measurement harness to reuse
- `plugins/flow-next/tests/test_setup_cursor_host.py`, `test_setup_grok_host.py` — prose assertions to relocate

### Key context
- Depends on .1/.2 landing first so the rewritten prose references real commands.
- fn-156 also edits sync-codex.sh guards — rebase onto main after fn-156 merges before starting this task.
- Memory lessons: mirror smoke must grep POST-transform output; run sync-codex.sh twice and commit the mirror diff with the canonical change.
- workflow.md is NOT pinned by test_prompt_text_pinned.py; keep it that way unless a moved fallback constant crosses a pinned surface (check test_review_prompt_template_parity does not reach into these files).

### Acceptance
- [ ] Resolved-platform mandatory pre-read (core + that platform's references) is well under half of today's ~75KB; evidence fixture regenerated and test green
- [ ] Question/option inventory diff (canonical + post-transform mirror, before vs after) is EMPTY; fn-130 matrix scenario walk attached — both as evidence artifacts
- [ ] Step 6a is one detect call + jq; Step 7 writes are batched; refresh-only re-runs route to `setup refresh` with prose-supplied `--plugin-root`/`--platform`
- [ ] Interactive usage.md path calls `setup usage-record` on written/identical/accepted-overwrite outcomes (provenance from first setup)
- [ ] sync-codex.sh run twice: idempotent, all guards green, moved anchors covered by hard-fail guards; mirror diff committed
- [ ] Host prose tests (cursor/grok/model-routing) updated and green; ruff green
## Acceptance
- [ ] R4: split + conditional loading + evidence regen
- [ ] R1/R2 consumed by skill prose (detect + batched set wired in)
- [ ] R7 (this task's share): empty inventory diff + fn-130 matrix walk as attached evidence
## Done summary
Not built — superseded. fn-160 planned a copy-mode refresh fast path + setup_version stamp; the copy-less install model (#352/#353, 4.0.0) removed copy mode, setup-mode, and the setup_version field entirely, so there is nothing to refresh or stamp. Closed 2026-08-19 alongside issue #314.
## Evidence
- Commits:
- Tests:
- PRs: https://github.com/gmickel/flow-next/pull/352, https://github.com/gmickel/flow-next/pull/353