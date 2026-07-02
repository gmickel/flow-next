# fn-79 task set-acceptance/set-description must replace the whole section — H2-in-input layering fix

## Goal & Context
<!-- scope: business -->

Found live in the fn-78 autonomous dogfood: `flowctl task set-acceptance` appeared to *layer* a new acceptance block above the old one, leaving a task `.md` with two contradicting acceptance-criteria blocks — the cursor plan-review caught the contradiction, but only after a wasted review round. Agents routinely pass section content that begins with its own `## …` heading (e.g. `## Acceptance Criteria (fn-78 R1–R6)`), and flowctl's section plumbing mishandles that shape at two write sites:

1. **`task create --acceptance-file`** embeds the file verbatim under the skeleton's `## Acceptance` heading — a file that starts with its own H2 plants a *rogue sibling section* in the task `.md`.
2. **`patch_task_section` (`flowctl.py:5124`, used by `task set-description` / `set-acceptance` via `_task_set_section` `flowctl.py:15597`)** replaces only the lines between the target heading and the *next* `## ` heading, and strips the input's leading heading only when it is byte-equal to the section name. The rogue H2 from (1) is a "next section" → the old block survives below the new one; and the new input's own H2 becomes the next rogue. Every subsequent `set-acceptance` compounds the layering.

Deterministic plumbing writing a structurally wrong file is exactly what flowctl exists to prevent. Fix it at the plumbing layer so any agent-supplied section content lands as ONE well-formed section, idempotently.

## Architecture & Data Models
<!-- scope: technical -->

**One normalization helper, applied at every task-section write site.** Canonical task `.md` structure treats H2 (`## `) headings as section boundaries (skeleton: `## Description`, `## Acceptance`, `## Done summary`, `## Evidence`). Therefore *content* placed inside a section must never itself contain H2 headings.

Normalization rules (pure function, e.g. `normalize_section_content(section: str, new_content: str) -> str`):
1. Strip a leading H2 heading line when it equals the target section name (existing behavior, kept) **or** when it is a title-like variant of it (e.g. `## Acceptance Criteria (…)` for `## Acceptance`, `## Description — …` for `## Description`): case-insensitive prefix match on the section word.
2. **Demote every remaining H2 (`## `) line inside the content to H3 (`### `)** so embedded structure survives visually but never becomes a section boundary.
3. Leave H3+ headings, code fences, and prose untouched; do not demote `## ` occurrences inside fenced code blocks.

Applied at:
- `patch_task_section` (`flowctl.py:5124`) — normalize `new_content` before splice (covers `task set-description`, `task set-acceptance`, and the section-patch mode of `task set-spec`).
- `cmd_task_create`'s `--acceptance-file` embed path — normalize before writing the skeleton so the rogue section never enters the file.

**Self-heal on write:** when `patch_task_section` detects the *current* file already carries a rogue layered section (an H2 immediately following the target section that is a title-like variant per rule 1 — the fn-78 damage shape), fold that rogue section's span into the replacement (i.e. replace through it) instead of preserving it, so one corrective `set-acceptance` heals a previously layered file. Conservative match: only title-like variants of the SAME section word are folded; unrelated H2s (`## Done summary` etc.) stay boundaries.

## API Contracts
<!-- scope: technical -->

```
normalize_section_content(section: str, new_content: str) -> str
  # rule 1: strip leading H2 when byte-equal OR title-like variant of `section`
  # rule 2: demote remaining H2 → H3 outside fenced code blocks
  # rule 3: everything else byte-preserved
```

- `flowctl task set-acceptance <id> --file f.md` — resulting `.md` contains exactly ONE `## Acceptance` section whose body is the normalized input; running it twice with the same input is byte-idempotent.
- `flowctl task set-description` and `task set-spec --description/--acceptance` — same contract for their sections.
- `flowctl task create --spec … --acceptance-file f.md` — the created `.md` has the canonical skeleton with the normalized content under `## Acceptance`; no sibling H2 from the input.
- Error semantics unchanged: duplicate canonical headings still raise (`Cannot patch: duplicate heading`); missing section still raises.
- JSON output shapes unchanged.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Fenced code blocks** containing `## ` lines (bash comments, markdown examples) must NOT be demoted — track fence state (``` / ~~~) while scanning.
- **Legacy heading variants** (`## Acceptance criteria`, `## Acceptance Criteria`) are title-like variants of `## Acceptance` (case-insensitive first-word match) — both stripped as leading titles (rule 1) and folded by self-heal.
- **Self-heal must not eat legitimate skeleton sections:** folding only applies to title-like variants of the target section word; `## Done summary` / `## Evidence` / `## Description` remain hard boundaries.
- **Already-clean files** round-trip byte-identically (no gratuitous rewrites; `updated_at` bump only on actual change is NOT required — keep current always-bump behavior).
- **Spec-side (`spec set-plan`) is out of scope** — it is full-file replacement, no section splice, no layering surface.
- Pure-stdlib Python; no new deps; no schema change.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A single normalization helper strips a leading title-like H2 (byte-equal OR case-insensitive section-word variant, e.g. `## Acceptance Criteria (…)` for `## Acceptance`) and demotes all remaining H2 headings in section content to H3, skipping fenced code blocks.
- **R2:** `patch_task_section` applies the helper to `new_content`; `task set-acceptance` / `set-description` / `set-spec --acceptance/--description` produce exactly ONE target section — repeated invocation with the same input is byte-idempotent (no layering).
- **R3:** `task create --acceptance-file` applies the helper before embedding, so an input file beginning with its own `## Acceptance Criteria …` H2 yields a well-formed skeleton with no rogue sibling section.
- **R4:** Self-heal: on a file already damaged in the fn-78 shape (rogue title-like H2 section directly after the target section), one `set-acceptance` call replaces the target section AND the rogue span, leaving one clean section. Unrelated skeleton sections are never folded.
- **R5:** Regression tests cover: leading-H2 acceptance file at create; set-acceptance twice (idempotent, no layering); embedded H2 demotion; `## ` inside code fences untouched; legacy `## Acceptance criteria` variant; self-heal of a pre-layered file; unrelated-section preservation.
- **R6:** Existing error semantics (duplicate canonical heading, missing section) and JSON output are unchanged; full existing test suite green (`python3 -m unittest` + `bash tests/smoke_test.sh` or repo equivalent).
- **R7:** Docs: `docs/flowctl.md` section for `task set-acceptance`/`set-description`/`create --acceptance-file` gains one line documenting the normalization (content H2s demoted; leading title stripped). CHANGELOG `## Unreleased` entry. No version bump in this spec (batched).

## Boundaries
<!-- scope: business -->

- **In scope:** flowctl task-section write plumbing (`patch_task_section`, `_task_set_section` consumers, `task create --acceptance-file`), its tests, one docs line, CHANGELOG.
- **Out of scope:** spec-side `spec set-plan` (full-file, no surface); any skill prose changes; retroactive repair of existing damaged task files beyond the R4 on-write self-heal; markdown linting beyond the H2 rule.
- **Out of scope:** changing the canonical task skeleton or section names.

## Decision Context
<!-- scope: both — conditionally substructured -->

**Demote, don't reject.** Rejecting H2-bearing input would break every agent that naturally writes `## Acceptance Criteria` headers (the observed shape) and turn a papercut into a hard error mid-autonomous-run. Demoting to H3 preserves the author's visual structure while keeping the file's section algebra intact. Stripping only the *leading* title (not all H2s) would still let mid-content H2s split the section.

**Fix at the plumbing, not the prompts.** A skill-prose rule ("don't start acceptance files with H2") depends on every model remembering it; the deterministic layer is where flow-next puts structural guarantees (CLAUDE.md architecture rule). The fn-78 workaround (`task set-spec --file` full replace) remains available but shouldn't be required.

**Self-heal on write** (rather than a migration): damaged files are rare (known shape, fn-78 vintage), and the next legitimate section write is the natural repair point — no migration surface, no scanning pass.

**Why now:** hit live in the first fully-autonomous pilot→land run; the duplicate criteria actively confused a review round (cursor flagged the contradiction as a Major finding). Cheap fix, real autonomy-reliability payoff.
