---
satisfies: [R1]
---
# fn-138-published-json-schema-for-flow-config.1 Schema generator + committed artifact

## Description
Deterministic generator + byte-stable committed schema.

**Size:** M

**Files:** new generator (scripts/ or flowctl subcommand - pick per repo convention; pure stdlib), committed artifact at plugins/flow-next/schema/flow-config.schema.json, regen test.

### Approach
- One structured table (key path -> type/enum/pattern/description) as the single source; descriptions lifted from flowctl.md config docs. Survey the CURRENT surface at implementation time (~44 dotted keys as of 3.11.0): the review-backend spec grammar backend[:model[:effort]] as a pattern, pipeline.qa, work.delegate*, artifacts.html.*, the full tracker.* block incl. the fn-139 `tracker.resolved` destination/capability cache (atomic, partially-absent-by-design - schema must tolerate absence) and `tracker.conflictTiebreak` (fn-146), models.roles.*/verifiedAt/verifiedWith (fn-115), land.* incl. cleanReviewCommentPattern (empty-string-means-disabled contract), pilot.autonomy/gateClasses. flowctl.md § config is authoritative; the .2 drift guard is the honesty mechanism.
- Emit draft 2020-12 with ALL determinism knobs pinned: explicit key ordering (sort_keys or table order), `ensure_ascii` picked and fixed, explicit `separators`, exactly one trailing newline, written in binary/`newline=""` mode so windows-latest cannot CRLF it; add `*.schema.json text eol=lf` to .gitattributes (repo currently pins only *.cmd and flowctl). Regen test asserts byte-identity (precedent: tests/test_template_canonical.py byte-for-byte assertions - NOT fn-113, which is unrelated).
- Open maps (`models.roles.<role>.<backend>`, labelMap/priorityMap/statusMap) use patternProperties/typed additionalProperties; fixed nested families (tracker.perEvent.*) enumerate from defaults - the .2 comparator canonicalizes both sides identically.
- Schema `default` annotations equal `get_default_config()` leaves, asserted (docs supply descriptions only; flowctl.md's memory.enabled/planSync.enabled default rows are wrong and get corrected in .3).

## Acceptance
- [ ] Generator + committed artifact byte-stable w/ regen test; full documented surface covered (R1).

## Done summary
Added the deterministic flow-config JSON Schema generator (scripts/gen_flow_config_schema.py, pure stdlib, standalone-script convention mirroring gen_tracker_manifest.py with --check mode) and the committed draft 2020-12 artifact at plugins/flow-next/schema/flow-config.schema.json, covering the full ~44-key documented surface with code-authoritative keys/types/defaults (get_default_config leaves, TRACKER_* enums, MODEL_ROLES/MODEL_ROLE_BACKENDS, BACKEND_REGISTRY-derived backend[:model[:effort]] patterns, resolved_cache SCOPES) and docs-authored descriptions. Determinism fully pinned (insertion order, ensure_ascii, explicit separators, one trailing newline, binary write, *.schema.json eol=lf in .gitattributes); the new test module asserts byte-identity regen, defaults honesty both directions, the tracker.resolved/scopeResolvedAt open-map contract, and description coverage. Implementation code was delegated to grok-4.5 via the cursor-agent bridge per run direction (one polish pass applied in-session); flowctl.py untouched, so no dual-copy/manifest/sync-codex propagation was needed.
## Evidence
- Commits: 8e22df13171cdc1cccc3203ec07d49599dd58550, f0d2571f
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p "test_flow_config_schema.py" -v (10 tests OK), python3 -m unittest discover -s plugins/flow-next/tests -p "test_config_snapshot.py" -q (OK), python3 scripts/run_tests_parallel.py (files=166 ran=3532 failures=0 errors=0; green receipt 8e22df13-unittest), python3 scripts/gen_flow_config_schema.py --check (current), uvx ruff@0.16.0 check . (All checks passed), post-review: test_flow_config_schema 10/10 OK; reviewer fuzz 63 specs schema==BackendSpec.parse; repo config validates 0 errors
- PRs: