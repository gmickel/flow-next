# make-pr reviewer-ease: flowctl-backed traceability

## Goal & context

Follow-up to the make-pr reviewer-ease render sections (landed on the fn-84 branch, commit 4976833f). Those four sections (Not-in-this-PR, Verification, Review plan, provenance chip) were render-only — no flowctl change. A fable DESIGN review (2026-07-04) ranked two further review-ease wins that need **deterministic flowctl computation** (not renderable from the current payload): they make each removed export and each R-ID claim traceable to exact in-repo evidence. Same discipline: every rendered claim traces to a flowctl-computed field; zero agent investigation; no "non-breaking" inference.

## Non-goals / boundaries

- NOT re-touching the four render-only sections already shipped (they need no flowctl change).
- NOT reading diff CONTENT to narrate before→after behavior (the payload has no "before" semantics; that stays the fabrication surface make-pr forbids).
- NOT a second-model review pass or auto-generated review comments (make-pr's stance: the structured payload does the heavy lifting).
- NOT touching the opt-in HTML lens (its mismatch check already implies the evidence.files computation; this brings it to the default markdown body).

## Approach

Two flowctl extensions to `export-cognitive-aid` plus thin make-pr render additions, each behind the existing trace-to-field discipline:

1. **Removed-export remaining-references (R1-R3).** flowctl computes, per removed symbol, a `removed_detail` record `{symbol, remaining_refs: N, locations: [path:line, ...] capped at 5}` via a bounded `git grep -nF <symbol>` at HEAD. make-pr renders it as a clause on the existing Critical-changes tier-3 bullet: "removes `_legacy_token_env` — 0 in-repo references remain at HEAD" or "— 3 references remain (path:line, ...) — confirm intended".

2. **Per-task evidence.files (R4-R6).** flowctl computes `tasks[].evidence.files[]` as the union of `git diff-tree --no-commit-id --name-only -r <sha>` over the task's evidence commits (SHAs already in the payload). make-pr upgrades R-ID-table evidence links to per-file `#diff-<sha256(path)>` anchors (the anchor form the linkable-file-references rule already specifies) and renders the HTML lens's mismatch flag in the markdown body too (an evidence commit touching no file in `diff_summary.files[]` becomes a visibly-flagged table row).

Extend `optimization/make-pr/` fixtures with the two new fields; add E11 (removed-export refs) + E12 (evidence.files traceability + mismatch flag) to the eval harness; re-baseline.

## Key files / interfaces

- `plugins/flow-next/scripts/flowctl.py` — the `export-cognitive-aid` payload builder (`_export_detect_public_exports`, `_export_path_is_security_sensitive`); add `removed_detail` + `evidence.files[]` computation (bounded git plumbing, no network).
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md` — the tier-3 bullet (removed-export clause), the R-ID evidence links (per-file anchors + mismatch row), and the no-weakening guardrail (0-refs is a repo-local FACT, NEVER license to write "non-breaking").
- `optimization/make-pr/` — fixtures + E11/E12 + re-baseline; `plugins/flow-next/tests/` — flowctl unit tests for the two computations.

## Acceptance criteria

- **R1:** `export-cognitive-aid` emits per removed export a `removed_detail` record `{symbol, remaining_refs, locations[]}` computed by a bounded `git grep -nF` at HEAD; locations capped at 5; deterministic; no network.
- **R2:** make-pr renders the remaining-refs clause on the tier-3 removed-export bullet with the verbatim numbers; both 0-refs and N-refs handled.
- **R3:** the no-weakening guardrail is extended so `remaining_refs: 0` is a fact about THIS repo only and NEVER licenses "non-breaking" / "internal" / "safe" (external consumers are invisible); reviewer judgment preserved.
- **R4:** `export-cognitive-aid` emits `tasks[].evidence.files[]` as the union of the task's evidence-commit diff-trees; deterministic git plumbing; empty when the task has no evidence commits.
- **R5:** make-pr R-ID evidence links resolve to per-file `#diff-<sha256(path)>` anchors; an evidence commit touching no `diff_summary.files[]` path renders a visibly-flagged mismatch row (never silently dropped).
- **R6:** `optimization/make-pr/` gains E11 (removed-refs) + E12 (evidence.files + mismatch), the fixtures carry the new fields, and a re-baseline shows E1-E12 pass with no regression; flowctl unit tests cover both computations.

## Test / verification notes

flowctl computations are unit-tested (deterministic git plumbing — feed known commits, assert `removed_detail` / `evidence.files`). Render additions verified via the `optimization/make-pr/` dry-run harness (E11/E12 plus E1-E10 no-regression). Run the make-pr smoke test + the unittest suite before handoff. Docs: CHANGELOG Unreleased + the flowctl payload-schema reference + the make-pr reference; downstream docs-site in the same workstream.
