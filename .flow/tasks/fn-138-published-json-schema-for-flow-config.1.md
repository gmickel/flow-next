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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
