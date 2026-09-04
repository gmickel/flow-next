# `flowctl spec create` / `spec skeleton` render the canonical `templates/spec.md` (one spec template, override cascade, exporter synonyms)

## Goal & Context

flow-next ships two spec canons. `flowctl spec create` and `flowctl spec skeleton` render `SPEC_SKELETON_TEMPLATE` (`Overview / Scope / Approach / Quick commands / Acceptance / References`, `flowctl.py` ~:19391, R22 byte-for-byte baseline from fn-44.1), while `/flow-next:capture` synthesizes against `plugins/flow-next/templates/spec.md` (`Goal & Context / Architecture & Data Models / API Contracts / Edge Cases & Constraints / Acceptance Criteria / Boundaries / Decision Context`). Every downstream reader keys on the template's headings — plan-review, the R-ID coverage rules, completion review, `spec export-cognitive-aid` (`_export_parse_spec_section` → `spec_sections.goal_and_context`, …) — so a spec born through `spec create --plan-file` (the documented CLI path since fn-163) exports with empty `goal_and_context`/boundaries and make-pr falls back to the spec id as the PR title. Observed 2026-09-03/04 on three MergeFoundry specs (fn-213/214/215). The skeleton is legacy; `templates/spec.md` is the one to keep.

## Architecture & Data Models

- `spec_skeleton_text()` becomes a renderer over `templates/spec.md` with placeholder substitution (`<spec-id>`, `<Title>`), replacing the `SPEC_SKELETON_TEMPLATE` constant; `cmd_spec_skeleton` and `cmd_spec_create` keep their signatures.
- Override cascade for the scaffold, first match wins: repo `SPEC.md` → repo `spec.md` → bundled `templates/spec.md`. The cascade is documented in the plan/capture skills' prose already ("Scaffold cascade (first match wins): SPEC.md -> spec.md -> bundled template") but is not implemented in `flowctl.py`; implement it where the prose says it lives and keep the prose.
- `_export_parse_spec_section` accepts read-only synonyms for historical specs: `Overview`/`Context` → goal_and_context, `Acceptance` → acceptance criteria, `Boundaries / non-goals`/`Non-goals` → boundaries, `Decision context` (any case) → decision context. Synonyms are parse-time only; nothing writes them.
- R22 baseline: the fn-44.1 byte-for-byte snapshot of `spec skeleton` is superseded — bump the baseline and refresh the snapshot fixture deliberately (the constant's own comment demands this), never silently.

## API Contracts

- `flowctl spec skeleton [--json]` prints the resolved scaffold (cascade applied) — same headings as `templates/spec.md`.
- `flowctl spec create --title … [--plan-file|--plan -]` writes the resolved scaffold, then applies the plan when given (unchanged one-shot semantics).
- `flowctl spec export-cognitive-aid` output shape unchanged; only more specs populate `spec_sections.*`.
- No new commands, flags, or config keys.

## Edge Cases & Constraints

- A repo `SPEC.md`/`spec.md` that lacks a required heading (e.g. no `## Acceptance Criteria`): scaffold still renders it verbatim; `flowctl validate` (existing R-ID rules) reports the missing section — the override is trusted, not patched.
- `--plan-file` content replaces the scaffold wholesale (today's behavior); a plan file with legacy headings still exports thanks to the synonyms, and `validate` should warn once (`legacy spec headings: … — prefer templates/spec.md`) so authors migrate.
- Existing `.flow/specs/*.md` files are never rewritten.
- Windows/CRLF: the cascade reads override files as UTF-8 text; CRLF is normalized like every other markdown read in flowctl.
- Tests that pinned the old skeleton bytes are updated in the same change (R22 bump), not deleted.

## Acceptance Criteria

- **R1:** `flowctl spec skeleton` and a fresh `flowctl spec create --title X` produce a spec whose H2 set equals `templates/spec.md`'s (`Goal & Context`, `Architecture & Data Models`, `API Contracts`, `Edge Cases & Constraints`, `Acceptance Criteria`, `Boundaries`, `Decision Context`) with `<spec-id>`/`<Title>` substituted. Errors: none beyond a missing bundled template, which is an install error and exits non-zero with the path.
- **R2:** Override cascade `SPEC.md` → `spec.md` → bundled, first match wins, applied identically by `spec skeleton` and `spec create`; pinned by a test that plants each override in a temp repo. Errors: an unreadable override file falls through to the next rung with one warning.
- **R3:** `spec export-cognitive-aid` populates `goal_and_context`, acceptance, boundaries, and decision context for specs using the legacy skeleton headings or the `Boundaries / non-goals` variant (synonym table above); a fixture spec with legacy headings exports non-empty fields. Errors: no synonym invents content — a section absent under every name stays empty.
- **R4:** The R22 byte-for-byte skeleton baseline is bumped in the same change: the snapshot fixture is regenerated, the constant's comment updated, and CHANGELOG records the scaffold change as a MINOR behavior change (existing specs untouched). Errors: none.
- **R5:** `flowctl validate` warns once per spec when it parses only through legacy synonyms (`legacy spec headings`), never errors. Errors: none.
- **R6:** Docs: `docs/flowctl.md` (spec create/skeleton), the plan and capture skills' "scaffold cascade" prose, and `templates/spec.md`'s own header note say there is ONE spec template and name the cascade; `sync-codex.sh`/mirrors regenerate if they embed the skill text. Errors: none.

## Boundaries

- No change to `templates/spec.md`'s section list or R-ID grammar.
- No rewrite of existing spec files, and no new config key for the cascade.
- Capture's synthesis flow is untouched (it already targets the template).

## Decision Context

- Which canon wins: `templates/spec.md`. Every reader (plan-review, coverage, completion review, cognitive-aid export) keys on its headings; the skeleton's `Scope`/`References` are read by nothing. Keeping both guarantees drift for every CLI-created spec.
- Synonyms are read-only on purpose: they rescue historical specs' PR bodies without giving new specs a second vocabulary; the `validate` warning is the migration nudge.
- R22 baseline bump is explicit: the fn-44.1 comment forbids silent edits, so this spec owns the bump.
