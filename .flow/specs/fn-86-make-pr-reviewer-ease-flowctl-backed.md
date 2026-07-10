# make-pr reviewer-ease: deterministic traceability slice (payload data for the review plan)

## Goal & Context

fn-93's eval-validated "Review plan" render is only as trustworthy as its data. The blind-judge evidence (prbeval 2026-07-10) showed exactly where vibes fail: a traceability table WITHOUT deterministic backing scored worse than none (V3 trust 7 vs V2's 9 — "weakly supported"), the byte-identical dual-copy file inflated apparent risk, and the judge's residual complaint across every round was "no line/hunk anchors". This spec adds the small deterministic slice to `flowctl spec export-cognitive-aid` that turns fn-93's claims into data.

## Architecture & Data Models

Four additive payload fields in `export-cognitive-aid` (flowctl.py, dual-copied), all cheap and deterministic:

1. **`diff_summary.files[].changed_symbols`** — the function/section context per changed file, parsed from `git diff` hunk headers (the `@@ … @@ <context>` line; free, language-agnostic where git's xfuncname works). Gives fn-93's must-review items their anchors ("open `_dispatch_review_with_fallback`") — the judge's #1 residual.
2. **`diff_summary.files[].derived`** — deterministic derived-file classification: `{kind: mirror|dual-copy|state|none, source: <path|tool>}`. Detection: repo-configurable path rules seeded with the flow-next shapes (generated mirror dirs, byte-identical sibling detection via content hash against a named source file, `.flow/` state paths). Backs the safe-to-skim bucket with data ("byte-identical copy of scripts/flowctl.py — verified this export").
3. **`removed_export_refs`** — exports/symbols DELETED in the diff that are still referenced elsewhere in the repo (grep-based, conservative: report candidates with file:line, never claim completeness). Empty list ⇒ the render states "no removed symbols still referenced (checked at export time)". The classic silent-breakage class a skimming reviewer misses.
4. **`tasks[].evidence.files`** — surface each task's claimed files (already recorded at `flowctl done` time) into the export payload so the render can map task → files → commits without re-deriving.

## API Contracts

- All four fields are ADDITIVE — absent/empty fields render nothing (fn-93 degrades gracefully; older payload consumers unaffected). No schema version bump.
- `export-cognitive-aid` stays a single call, no new flags; derived-file rules read from an optional config leaf (`makePr.derivedPaths`, default = flow-next's own shapes) — projects override, never required.
- Determinism contract: every field value must be reproducible from the repo state at export time; no LLM judgment inside flowctl (the render layer judges, the payload reports).

## Edge Cases & Constraints

- Hunk headers give function context only where git's language detection works — `changed_symbols` may be empty per file; the render falls back to file-level anchoring (never fabricates).
- `removed_export_refs` is candidates-not-proof: word-boundary grep over the repo minus the diff's own removals; false positives acceptable (they steer a human look), silent false negatives minimized by conservative matching. Cap the scan cost (bounded file set from the diff's languages).
- Byte-identical dual-copy detection compares content hashes at export time — a drifted copy is NOT marked derived (that's a real review item).
- Windows-safe (no shell-outs beyond git; existing subprocess discipline); dual flowctl copies; mirror regen.

## Acceptance Criteria

- [ ] **R1:** `changed_symbols` per changed file from diff hunk headers; unit-tested on a fixture diff (incl. a file with no detectable symbols → empty list).
- [ ] **R2:** `derived` classification (mirror/dual-copy/state) with the flow-next default rules + config override; dual-copy verified by hash at export time; unit-tested both directions (identical → derived, drifted → not).
- [ ] **R3:** `removed_export_refs` conservative candidate scan with file:line refs; empty-clean case explicit; unit-tested (removed-and-referenced, removed-and-unreferenced, added-only).
- [ ] **R4:** `tasks[].evidence.files` surfaced in the payload; make-pr render contract references all four fields opportunistically (one small prose touch, coordinated with fn-93's sections).
- [ ] **R5:** Full suite + smoke green; dual-copy parity; mirror regen; docs (flowctl.md export-cognitive-aid section) + CHANGELOG Unreleased.

## Boundaries

- Out: the render/prose layer itself (fn-93 owns it); AST-level analysis or language servers (hunk headers + grep only — cheap and universal beats precise and heavy); HTML lens changes; any LLM call inside flowctl.

## Decision Context

Scoped BY eval evidence, not speculation: prbeval showed the render's remaining weaknesses are exactly data gaps — anchors (judge's residual every round), derived-file trust (dual-copy inflated risk), and unsupported traceability (V3 scored below V2 without real data). Each payload field maps 1:1 to a measured gap. fn-93 ships independently (graceful absence); this spec upgrades its trust ceiling. Soft ordering: fn-93 first (prose, immediate), fn-86 second (data), no hard dependency either way.

> Field origin — same external-team AI-SDLC weekly as fn-93 (2026-07-10); this is the deterministic half of the "get to the 20%" promise. Detailed notes in the maintainer's vault (AI-SDLC weekly 2026-07-10).
