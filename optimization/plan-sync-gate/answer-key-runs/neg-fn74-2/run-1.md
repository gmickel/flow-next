**Phase 3b complete:**
- **3b.1 (glossary):** all 38 entries have empty `avoid` arrays → no rename candidates.
- **3b.2 (decisions):** both active decisions name concrete code refs unrelated to the change. Decision 1 (Factory Droid) commits to `${DROID_PLUGIN_ROOT}` fallbacks, `Bash|Execute` matchers, `.factory-plugin/plugin.json` removal, `platforms.md`, `sync-codex.sh:206`. Decision 2 (tracker-sync projection) commits to two-way body/status/comment sync. The completed task touched only `flowctl.py` (cursor review commands) — neither decision's code surface is contradicted.
- **3b.3 (strategy):** the cursor backend *advances* the Cross-model review track and honors the zero-dep/lean-flowctl contract (opt-in subprocess to an already-installed CLI, mirroring codex/copilot — flowctl core imports nothing new). No track contradicted; the spec's "Strategy Alignment" bullets are bold bullets, not `### H3` track headers, so no rename candidate.

**Phase 4:** downstream `.3`/`.4` cite only stable identifiers that landed exactly as named (cursor subcommands, `mode:"cursor"`, backend name `cursor`, `run_cursor_exec`, `workflow-copilot.md` template). `.3`'s `--review=rp|codex|copilot|none` literals are its own edit targets, not stale refs. **Phase 4b:** CROSS_SPEC=false → skipped. **Phase 5:** parent spec's `## Requirement coverage` table assigns R5/R6/R7/R8/R11/R14 to `.2` — the completed task satisfied exactly those, so no coverage drift.

---

Drift detected: no
- fn-74…​.2 was a clean parity port of the `copilot` backend; every symbol landed with its spec-planned name. Verified in `flowctl.py`: handlers `cmd_cursor_impl_review`/`_plan_review`/`_completion_review`/`_validate`/`_deep_pass`, subcommands `impl-review`/`plan-review`/`completion-review`/`validate`/`deep-pass`, `run_cursor_exec`, `"mode": "cursor"` receipts, and the `mode == "cursor"` resume guard (L23561) all match the spec and the downstream tasks' assumptions.

Would update (DRY RUN):
- None. No downstream task references a name, API, receipt shape, or backend string that drifted.

Would update traceability:
- None. `## Requirement coverage` rows for R5/R6/R7/R8/R11/R14 already map to `.2` and remain accurate.

Decision overrides flagged for review:
- None. Neither active decision's `## Consequences` code surface intersects the cursor review-backend change.

Strategy drift flagged for review:
- None. The change advances the Cross-model review track and preserves the zero-dependency / lean-flowctl contract.

No files modified (DRY_RUN=true).