---
satisfies: [R11, R21, R22]
---

## Description

Extract the canonical spec template to a single source of truth that skills, CLAUDE.md, and future tooling reference rather than duplicate. Add a sync-codex.sh drift guard that catches re-divergence across ALL skill markdown files. Set up deterministic test helpers for R22's static-invariant checks (no interactive-skill markdown fixture — R22 explicitly rejects that approach).

**Size:** M
**Files:**
- `plugins/flow-next/templates/spec.md` (NEW)
- `scripts/sync-codex.sh` (extend validation block)
- `plugins/flow-next/scripts/flowctl.py` (NEW five subcommands: `scope resolve`, `scope bank`, `scope write-policy`, `scope suggest`, `spec skeleton`; production code)

## Approach

Template file follows the convention at `plugins/flow-next/templates/memory/*.tpl` but uses plain `.md` (no placeholder substitution — consumed as a reference scaffold).

Template content:
- Frontmatter declaring purpose + which skills consume it (capture, interview, plan, work)
- 7 canonical sections per the fn-44 spec Architecture & Data Models table (Goal & Context, Architecture & Data Models, API Contracts, Edge Cases & Constraints, Acceptance Criteria, Boundaries, Decision Context). `## Decision Context` template scaffold shows BOTH the flat default form AND the H3-substructured form (two H3 subsections: `### Motivation` biz-owned with `<!-- scope: business -->` comment, `### Implementation Tradeoffs` tech-owned with `<!-- scope: technical -->` comment) in a commented-out example. The flat form is the default for zero-flag-tech specs (R22 backward-compat); the H3 form is introduced only when a biz pass runs OR an existing spec already has it. Template comments explain the conditional.
- Each section header annotated with `<!-- scope: business -->` / `<!-- scope: technical -->` / `<!-- scope: both -->` HTML comment
- One-line guidance per section
- Footer cross-link to docs/teams.md Symmetric-interview + CLAUDE.md Creating-a-spec

**Sync-codex drift guard (broader scope per R21)**: follows existing mirror-scan pattern at `scripts/sync-codex.sh:828-872`. Detection: ANY skill markdown file (`*.md` under `plugins/flow-next/skills/*/`, not limited to `SKILL.md`) containing `^## Goal & Context` followed within 30 lines by `^## Architecture & Data Models` AND `^## API Contracts` triggers an error. The canonical template at `plugins/flow-next/templates/spec.md` is the only file allowed to contain the full canonical sequence.

**R22 production helpers as flowctl SUBCOMMANDS (runtime-coupled to SKILL.md)**: add five deterministic flowctl subcommands. SKILL.md invokes them at runtime; tests invoke the same subcommands. Same code path — no drift possible.

New subcommands:
- `flowctl scope resolve [args ...]` → token-safe parser. Plain output: `business` | `technical` | `both` (just the resolved scope). `--json` output: `{"scope": "...", "remaining_args": [tokens...]}` where `remaining_args` is the input arg list with all scope tokens (`--scope=VALUE`, `--biz`, `--tech`) stripped IN-ORDER, preserving spec ids, file paths, and other flags. Default `technical` when no scope tokens present. Exits non-zero on conflict (`--biz --tech`) or invalid value (`--scope=foo`) with explicit error message.
- `flowctl scope bank <scope> [--json]` → prints absolute path to the question-bank file. Errors on invalid scope.
- `flowctl scope write-policy <scope> --current-sections-json <path|->` → reads existing-section-state JSON from file or stdin, prints the write-policy JSON (which sections may be written, which preserved byte-for-byte). Used by SKILL.md before any markdown edit.
- `flowctl scope suggest --signal-categories-count <N>` → prints `fire` if the capture biz-suggestion should fire (`1 <= N < 3`) or `no-fire` otherwise (`N == 0` or `N >= 3`). Pure threshold function; called by `/flow-next:capture` skill to decide whether to append the suggestion footer; T9 tests assert on the same.
- `flowctl spec skeleton [--json]` → prints the canonical fresh-spec-create skeleton (the literal string `flowctl spec create` writes today). Called by `flowctl spec create` internally AND by T9 tests for byte-for-byte verification.

**Runtime coupling**: SKILL.md text MUST invoke these subcommands (bash `$($FLOWCTL scope resolve "$@")`, `$($FLOWCTL scope write-policy ...)`). Acceptance verification: grep `SKILL.md` for the exact invocation strings; CI fails if not present. Tests invoke the same subcommands via subprocess — if the implementation drifts, both sides fail consistently.

## Investigation targets

**Required:**
- `plugins/flow-next/templates/memory/knowledge-track-entry.md.tpl:1-30` — template frontmatter + section conventions
- `plugins/flow-next/templates/memory/README.md.tpl` — README-in-templates convention
- `scripts/sync-codex.sh:828-872` — mirror-scan guard pattern; copy shape
- `CLAUDE.md:120-147` — current embedded heredoc (content to extract)
- fn-44 spec Architecture & Data Models table — canonical 7 sections + scope owners
- fn-44 spec R22 (deterministic-static-check framing)

**Optional:**
- `plugins/flow-next/skills/flow-next-capture/workflow.md:274-298` — section-by-section drafting reference (verify the new guard catches any duplication here)

## Acceptance

- [ ] `plugins/flow-next/templates/spec.md` exists with frontmatter + 7 canonical sections + scope-owner HTML comments + footer cross-links
- [ ] Auxiliary sections (Strategy Alignment / Glossary Conflicts / Conversation Evidence / Resolved via Codebase) noted as "optional, skill-conditional" in template comments
- [ ] `scripts/sync-codex.sh` validation block adds drift guard scanning ALL `*.md` under `plugins/flow-next/skills/*/` (not just SKILL.md); passes on current canonical
- [ ] Drift guard fails the build if a skill markdown file inline-duplicates the canonical section sequence; verified by a temporary test-fixture violation that gets reverted before commit
- [ ] Five flowctl subcommands added: `scope resolve`, `scope bank`, `scope write-policy`, `scope suggest`, `spec skeleton`. All accept `--json`. Exit non-zero on conflict / invalid input.
- [ ] `SKILL.md` text invokes these subcommands at runtime (bash subprocess form like `RESOLVED=$($FLOWCTL scope resolve "$@")`). Verifiable via grep — the literal invocation string must appear in SKILL.md.
- [ ] `flowctl spec create` is updated to invoke `flowctl spec skeleton` internally (no inline skeleton string).
- [ ] `bash scripts/sync-codex.sh` passes after changes


## Done summary
T1 of fn-44 landed: canonical spec template at plugins/flow-next/templates/spec.md (7 sections + YAML frontmatter + scope-owner HTML comments + flat-vs-H3 Decision Context conditional), R21 drift guard in scripts/sync-codex.sh scanning every *.md under plugins/flow-next/skills/*/ for the canonical 7-section sequence, five new flowctl subcommands (scope resolve / bank / write-policy / suggest and spec skeleton) consumed by /flow-next:interview and /flow-next:capture at runtime, refactored cmd_spec_create to source the skeleton from a single helper (R22 byte-for-byte parity preserved), and updated /flow-next:setup to copy the template into .flow/templates/spec.md so downstream snippets resolve. Five rounds of codex impl-review (gpt-5.5 high) hardened the --json-everywhere contract, eliminated nested HTML comments, added --raw for shell-quoting safety, fixed JSON-mode exit-code semantics on scope suggest, and made setup same-version-refresh re-copy files. Final verdict: SHIP.
## Evidence
- Commits: e87292e, 455ed7f, 6b35771, db23eca, 07d3ea5, a490463, e7b99c8
- Tests: python3 -m unittest discover plugins/flow-next/tests -p test_*.py (463 tests, OK), bash scripts/sync-codex.sh (all 14 validators green, including new R21 spec-template drift guard), smoke: flowctl scope resolve happy + conflict + invalid + --raw paths, smoke: flowctl scope bank happy + invalid scope (JSON error), smoke: flowctl scope write-policy happy + invalid scope (JSON error), smoke: flowctl scope suggest 0/1/2/3/5 in plain + --json mode, exit-code semantics differ correctly, smoke: flowctl spec skeleton byte-for-byte parity vs 1.0.2 baseline (verified by diff), drift-guard validation: temporary 7-section duplicate inserted under skills/, sync-codex.sh caught it; reverted before commit
- PRs: