# Chart notes: record corrections when discovery refutes a grounding fact

## Goal & Context
<!-- scope: business -->

Chart mode seeds `## Notes` with grounding facts at `chart create` time. The premise of a chart is that discovery resolves unknowns - and discovery routinely disproves its own starting facts. Today there is no way to record that: `## Notes` is write-once for the life of the chart, `resolve --sharpen-file` silently ignores any key it does not know (including a `notes` key a caller naturally reaches for), and `chart briefing` copies the stale note verbatim into an immutable artifact that `/flow-next:capture` reads - placing a refuted claim above the ledger that contradicts it.

Reported upstream as issue #292 (reproduced on 3.15.0+ and re-verified on 3.16.0). The reporter's own field case: a chart about stale documentation whose grounding note was itself stale, with no instrument to say so.

Value: charts stay honest. A decision that disproves a premise corrects it in the same transaction that closes it, the correction travels into the briefing, and a caller who attempts a correction through an unsupported key gets an error instead of silent success.

## Architecture & Data Models
<!-- scope: technical -->

All changes live in `plugins/flow-next/scripts/flowctl.py` (chart subsystem), with dual-copy propagation (`cp` to `.flow/bin/flowctl.py`), tracker-manifest regen (`scripts/gen_tracker_manifest.py` - the SOURCE_SHA256 single pin was replaced by the distribution manifest, fn-139.5), and codex mirror regen (twice).

1. **`notes_append` key in `resolve --sharpen-file`** (`_parse_sharpen_file`, flowctl.py:15806-15861). New optional key `notes_append`: a non-empty string of one or more markdown bullet lines. On resolve, appended to the chart's `## Notes` section via `_replace_chart_section` (flowctl.py:14041 - literal-text lambda substitution, appends the section if missing) on the SAME `md_text` local the resolve transaction already mutates (ledger pattern at 15533-15549), committed through the single `run_chart_transaction` at ~16616. **flowctl stamps the date**: each appended bullet is prefixed `- [corrected <YYYY-MM-DD>]` by flowctl (tool owns metadata; caller text is prose). Append-only: no mutation or deletion of existing notes, ever.
2. **Unknown-key rejection in `--sharpen-file`.** Accepted keys: `decisions`, `remove_questions`, `remove_parked`, `parked_removals`, `notes_append`. Any other key -> validation `ChartError("validation", "sharpen_file_unknown_key", ...)` naming the offending key(s) and the accepted set. **Ordering**: the unknown-key (structural) check runs BEFORE unsafe-prose refusal, so a mistyped key gets the key error, not a prose-scan error.
3. **Unsafe-prose refusal**: `notes_append` content goes through `refuse_if_unsafe_prose` (flowctl.py:15171), same as create-time notes (14498), before any allocation or persistence.
4. **Idempotent-retry interplay.** The identical-retry guard (flowctl.py:15952-15988) raises `decision_immutable` with `details.ignored_sharpen` when the payload carries sharpen content. `notes_append` joins the non-empty check and is reported in `ignored_sharpen` (no double-append). A legitimate re-resolve after `chart reopen` is NOT a retry (status no longer `resolved`) and appends fresh - intended; fixture required.
5. **Briefing renders appended corrections.** `_render_briefing_index_md` (17330-17351) copies the `## Notes` body; corrections ride along. Verify with a fixture. **Post-final-briefing corrections are out of scope**: a final briefing is an immutable snapshot; a correction appended after it lands in the chart and reaches artifacts only via the existing `chart reopen` re-mint path (documented, not changed).
6. **Briefing `**Chart status:**` fix.** The render call (17635) reads the pre-transition chart dict; the open->done flip happens later (17700-17740). Pass the resolved post-transition chart status into the render (do NOT conflate with the `status` kwarg at 17325, which is the BRIEFING's status).

## API Contracts
<!-- scope: technical -->

- `flowctl chart resolve <did> --answer-file f.md --sharpen-file s.json`:
  - `s.json` may carry `"notes_append": "- the auth module DOES have tests (src/auth/tests/, 14 files)"` alongside `decisions` / `remove_questions`.
  - JSON result gains `notes_appended`: **always a list** of the appended bullet strings as written (empty list when none) - consistent with `removed_questions`, never a boolean.
  - Unrecognized key in `s.json` -> exit 1, `error.code: "sharpen_file_unknown_key"`, message listing offending + accepted keys. Keep the accepted-key list in ONE constant shared by the error message and the `--sharpen-file` help text so they cannot drift.
  - Cascade/`--supersedes` resolves append the note ONCE per resolve call (chart-level), never once per superseded decision.
- No new top-level chart verb.
- Chart skill prose (`skills/flow-next-chart/workflow.md` sharpen block ~374/410/533 + SKILL.md tool table): when a resolution disproves a grounding note, carry the correction in `notes_append` in the same resolve. Unattended/autonomous chart driving: a correction is written only when the decision's measured answer directly contradicts a specific note - never speculative.

## Edge Cases & Constraints
<!-- scope: technical -->

- `notes_append` empty / whitespace-only / non-string -> validation error, not a silent no-op.
- Multi-line content: normalize per-line - lines already starting `- ` keep their marker; bare lines get `- ` prefixed. The date stamp goes on each appended bullet.
- Chart markdown lacking a `## Notes` section (created without notes): `_replace_chart_section` appends the section; must not crash.
- Replacement text goes through the literal-text lambda call pattern (no regex backslash expansion - a correction containing `\d` must not corrupt the file).
- Successive resolves on different decisions each append under the same cross-process lock; each resolve reloads `md_text` before writing. Fixture: two sequential appends both survive.
- Verify `chart_revision` fingerprint scope: confirm whether `## Notes` participates; if a notes append does NOT stale prior briefings, state that in the docs line (it should not - briefings are immutable snapshots by design).
- In-repo `--sharpen-file` callers (chart workflow.md:374,410; SKILL.md:97,109) pass only accepted keys today - confirm before landing the rejection.
- No prompt-text changes expected; `test_prompt_text_pinned` stays untouched.

## Acceptance Criteria
<!-- scope: both -->

- R1: A `resolve --sharpen-file` payload with a `notes_append` string appends date-stamped, append-only correction bullet(s) to the chart's `## Notes` via the chart writer inside the same resolve transaction; existing notes are byte-untouched; cascade resolves append once per call. Errors: empty/whitespace/non-string payload rejected; unsafe prose refused before persistence.
- R2: The resolve JSON result reports `notes_appended` as a list; a subsequent `chart briefing` renders both the original fact and the correction in `## Notes`. Errors: no error surface beyond R1's validation.
- R3: A `--sharpen-file` payload containing any unrecognized key fails with `sharpen_file_unknown_key` naming the key(s) and accepted set, checked before prose refusal; nothing allocated or persisted. Errors: this IS the error surface; alias keys `remove_parked`/`parked_removals` remain accepted.
- R4: An identical-retry resolve carrying `notes_append` does not double-append and reports it under `ignored_sharpen`; a post-reopen re-resolve is not a retry and appends fresh. Errors: `decision_immutable` shape unchanged otherwise.
- R5: The briefing header renders the chart's post-transition status (a final briefing that closes the chart says `done`, matching `chart show` immediately after). Errors: no error surface beyond existing briefing validation.
- R6: Regression tests cover R1-R5 in `test_chart_resolution.py` / `test_chart_briefing.py` conventions: no-Notes-section chart, mixed bulleting, backslash content, two sequential appends, reopen re-resolve, unknown-key + prose-refusal ordering.
- R7: Docs + prose updated: `docs/flowctl.md` chart resolve section (new key, error code), chart skill workflow.md + SKILL.md correction path, CHANGELOG under `## Unreleased` crediting @sn-furali (#292); dual-copy + tracker manifest regen + sync-codex twice.

## Boundaries
<!-- scope: business -->

- NOT building a standalone `flowctl chart note` verb - the resolve-time transaction covers the reported need; revisit on a second field report.
- NOT making notes mutable or deletable - append-only and dated, deliberately.
- NOT reordering briefing sections.
- NOT touching `chart reopen` semantics; post-final-briefing corrections reach artifacts only via the existing reopen re-mint path.
- NOT re-minting or mutating already-final briefings.

## Decision Context
<!-- scope: both -->

Shape: reporter's option 2 (`notes_append` in sharpen) + their fallback ask (reject unknown keys) + the status cosmetic. Option 1 (reorder/label) insufficient alone; option 3 (new verb) YAGNI. Gap-analysis resolutions folded in: `notes_appended` is always a list (no polymorphic result fields); flowctl stamps dates (tool owns metadata); unknown-key check precedes prose refusal (better diagnostics for typos); post-final-briefing staleness is documented out of scope (immutability + reopen re-mint is the existing answer); cascade appends once per call. Reporter explicitly did NOT ask for mutable notes and we agree: the refuted fact plus its dated correction is itself a finding worth keeping.
