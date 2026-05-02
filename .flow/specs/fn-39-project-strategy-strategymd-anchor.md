# Project strategy: STRATEGY.md anchor + downstream grounding

## Overview

Add a `/flow-next:strategy` skill that writes/maintains a repo-root `STRATEGY.md` (target problem, our approach, who it's for, key metrics, tracks, optional milestones, optional not-working-on). Downstream skills (`/flow-next:prospect`, `/flow-next:plan`, `/flow-next:interview`, `/flow-next:capture`, `/flow-next:sync`) read it as constraint-check input.

This is the third leg of flow-next's doc-aware infrastructure (joining `GLOSSARY.md` and `knowledge/decisions/` shipped in 0.39.0). Today the prospect → plan → interview → capture pipeline starts cold every time on "what should this repo build?" — there's no concept of strategic intent. STRATEGY.md fixes that.

Section structure derived from Richard Rumelt's strategy kernel (*Good Strategy Bad Strategy*: diagnosis / guiding policy / coherent action), extended with persona + metrics for repo-doc utility. flow-next conventions: drop a `Marketing` optional section that was considered (over-rotated for OSS-tools repo); use bare `AskUserQuestion` in canonical (no inline cross-platform tables); apply lead-with-recommendation only to routing questions (substance questions stay free-form so the user's own language is preserved).

## Scope

**In scope:**
- New skill `plugins/flow-next/skills/flow-next-strategy/` with `SKILL.md`, `references/interview.md`, `references/strategy-template.md`
- Slash command `plugins/flow-next/commands/flow-next/strategy.md`
- Repo-root `STRATEGY.md` artifact (peer of `GLOSSARY.md` / `README.md`, never under `.flow/`)
- Thin flowctl plumbing: `flowctl strategy status [--json]`, `flowctl strategy read [--section <name>] [--json]`, `flowctl strategy list [--json]`. NO add/edit (skill writes file directly via host agent's `Write` tool, mirroring `/flow-next:audit` and `/flow-next:capture` patterns)
- Doc-aware autodetect extension — third condition (`strategy.sections_filled >= 1`) joins glossary and decisions checks
- Override flags `--strategy` / `--no-strategy` independent of `--docs` / `--no-docs` (5-row matrix documented)
- Downstream grounding integration in 5 skills: prospect, plan, interview, capture, sync (plan-sync agent)
- Codex mirror via `scripts/sync-codex.sh` (REQUIRED_OPENAI_YAML_SKILLS + generate_openai_yaml workflow blue `#3B82F6`)
- Forbidden-vocabulary guard extension (Tier 1 jargon only): synergy / pivot / disrupt / thought-leadership / best-in-class / world-class / 10x. Separate guard block in `ci_test.sh` (not extending the R17 DDD pattern) + mirrored in `sync-codex.sh` validation block
- Smoke test `plugins/flow-next/scripts/strategy_smoke_test.sh` exercising T1-T12 happy paths + corner cases
- Doc updates: CHANGELOG, plugins/flow-next/README.md, CLAUDE.md, .flow/usage.md, mickel.tech (Gordon's external repo, in scope per user request)

**Out of scope:**
- No `flowctl strategy add/edit/remove/section-set` CLI — skill IS the editor. Strategy is too prose-heavy for atomic field-set plumbing.
- No metrics computation (records *which* metrics matter, not current values)
- No issue-tracker reconciliation
- No per-subdirectory STRATEGY.md cascade — repo-wide single root only. Subdirectory invocation walks up; "Using repo-root STRATEGY.md at <path>" surfaced before interview.
- No multi-format migration — v1 refuses to overwrite a file without `generator: flow-next-strategy` sentinel; tells user to delete or rename. CE-format / hand-written migration deferred to v2.
- No `/flow-next:product-pulse` equivalent (a separate ideation considered and dropped — SaaS-shop-specific, out of scope per gap analysis)
- No `/flow-next:simplify-code` (Gordon has global `simplify`)

## Architecture & data model

**File shape:**
```
---
name: <product-name>
last_updated: 2026-05-01
generator: flow-next-strategy
---

# <product-name> Strategy

## Target problem
1-2 sentences. Diagnosis. Names the user situation and the crux. No solution language.

## Our approach
1-2 sentences. Guiding policy. What this product commits to that makes the problem tractable.

## Who it's for
**Primary:** <persona> — <one-sentence JTBD>

## Key metrics
- **<metric>** — definition; where measured

## Tracks
### <track>
One line: investment area, not feature list.
_Why it serves the approach:_ one line.

## Milestones (optional)
- **YYYY-MM-DD** — milestone

## Not working on (optional)
- one line per item
```

Plain GFM markdown only. No MDX / admonitions / `:::tip` blocks.

**Husk semantics:** file with H1 + frontmatter only, no populated H2 sections, returns `{exists: true, husk: true, sections_filled: 0}` from `flowctl strategy status`. Doc-aware autodetect uses `sections_filled >= 1`, NOT `[[ -f STRATEGY.md ]]` — same trap glossary fell into.

**Atomic per-section writes:** each completed section lands on disk before the next interview prompt fires. `last_updated` bumps on every save. No draft state file. Re-invocation reads existing sections via `flowctl strategy status`, asks user which empty/stale section to revisit. Concurrent reads see a coherent older snapshot (race accepted, documented in skill prose).

**Foreign-file detection:** frontmatter `generator: flow-next-strategy` is the sentinel. Missing or different value → skill blocks via `AskUserQuestion` ("migrate / keep / rewrite?"). On "keep" — exits without writing. v1 explicitly defers automatic migration.

**Section deletion:** H2 stays with body `_Not currently tracking._` to preserve R-ID locked structure. Last-section delete leaves a husk (`# <name> Strategy` H1 + frontmatter) — file never deleted (R18 invariant, mirrors `render_glossary_file`).

**Single-root walk:** `flowctl strategy *` walks UP from cwd to first STRATEGY.md found, capped at repo root. NOT nearest-ancestor like glossary — strategy is repo-wide by Rumelt's definition. Subdirectory invocation surfaces "Using repo-root STRATEGY.md at <path>" before interview.

## Quick commands

```bash
# Smoke test (after Tasks 1-5 complete)
plugins/flow-next/scripts/strategy_smoke_test.sh

# Manual end-to-end check
flowctl strategy status --json
flowctl strategy read --section approach --json
flowctl strategy list --json

# Sync verification (after Task 5)
./scripts/sync-codex.sh && ls plugins/flow-next/codex/skills/flow-next-strategy/

# CI guard
plugins/flow-next/scripts/ci_test.sh
```

## Acceptance

- **R1:** `STRATEGY.md` lives at repo root (peer of `GLOSSARY.md` / `README.md`, never under `.flow/`). Survives a wipe of `.flow/` (R18 invariant from glossary epic). Frontmatter contains `name`, `last_updated` (ISO date), `generator: flow-next-strategy` only — no other keys.
- **R2:** Section structure locked: 5 required (`Target problem`, `Our approach`, `Who it's for`, `Key metrics`, `Tracks`) + 2 optional (`Milestones`, `Not working on`). Section order maps onto Rumelt's strategy kernel. A `Marketing` section is explicitly NOT included (considered and dropped). Optional sections deleted entirely if unused; never left as empty headers.
- **R3:** Skill uses bare `AskUserQuestion` in canonical files (no inline cross-platform tables). `sync-codex.sh` rewrites to `request_user_input` for Codex mirror. Free-form responses for substance questions (problem/approach/persona); single-select reserved for routing decisions only. Lead-with-recommendation pattern applies only to routing questions, NOT to substance questions — substance questions must capture the user's own language without priming.
- **R4:** Re-run on existing file routes via `AskUserQuestion` ("which section to revisit?"). Untouched sections preserved byte-identical (verified by `git diff --unified=0`). `last_updated` bumps on every per-section save (atomic per-section writes; no draft state file).
- **R5:** Pushback discipline enforced: 2 rounds maximum per section, then capture what user gave and add `<!-- worth revisiting -->` comment. Anti-pattern examples loaded from `references/interview.md` non-optionally (CE's "improvising from memory produces passive transcription" rule). Anti-pattern labels (vanity / fluff / feature-list) NOT leaked to user — only used internally to formulate sharper follow-up questions. Quote user's own words back when challenging (paraphrase softens).
- **R6:** `flowctl strategy status [--json]` returns `{exists: bool, husk: bool, sections_filled: int, total_sections: int, last_updated: str|null, file_path: str|null}`. Husk definition: file exists but `sections_filled == 0`. Used by downstream autodetect; rule is `sections_filled >= 1`, NOT `[[ -f STRATEGY.md ]]`.
- **R7:** `flowctl strategy read [--section <name>] [--json]` walks UP from cwd to first `STRATEGY.md` (single-root, capped at repo root, NOT nearest-ancestor). Returns `{path, name, last_updated, target_problem, approach, personas, metrics, tracks, milestones, not_working_on}`; `--section` filters to one block. Fenced code blocks in section bodies masked during parse (mirrors `_glossary_strip_fenced_code` helper at `flowctl.py:266`).
- **R8:** `flowctl strategy list [--json]` returns `{groups: [{path, sections, count}], file_count, total_sections}` — degenerate single-element group for v1 (single-root), kept for symmetry with `flowctl glossary list` so downstream skills can iterate generically.
- **R9:** Doc-aware autodetect activates when ANY of: `glossary.total_terms > 0` OR `decisions/` has entries OR `strategy.sections_filled >= 1`. Override flags `--strategy` / `--no-strategy` independent of `--docs` / `--no-docs`. Flag matrix: `(default)` = autodetect all three; `--docs` = on; `--no-docs` = off; `--no-docs --strategy` = strategy on / glossary+decisions off; `--docs --no-strategy` = glossary+decisions on / strategy off. Documented in CLAUDE.md and `flow-next-interview/SKILL.md`.
- **R10:** `/flow-next:prospect` Phase 0 grounding scan reads `STRATEGY.md` when `sections_filled >= 1`. Injects approach + active tracks verbatim into candidate-generation prompt — verbatim emit (no paraphrasing) so the candidate generator sees the exact language the user committed to. Adds `out-of-scope-vs-strategy` to rejection taxonomy. Surface as advisory at prospect phase (not auto-reject).
- **R11:** `/flow-next:plan` research scan (in `flow-next-plan/steps.md` Step 1) reads `STRATEGY.md`. Plan emits `## Strategy Alignment` spec section listing which active tracks the plan serves. Drift surfaced as `## Strategy drift flagged for review` block (read-only — never auto-supersedes; mirrors decision-record convention at `agents/plan-sync.md:101`).
- **R12:** `/flow-next:interview` doc-aware mode reads `STRATEGY.md` before terminology questions. Surfaces conflicts in `## Strategy Conflicts` spec section parallel to existing `## Glossary Conflicts` (`flow-next-interview/SKILL.md:192-249`). Throttle: ≤1 strategy-conflict question per interview turn (parallel to existing glossary-question throttle).
- **R13:** `/flow-next:capture` Phase 0 reads `STRATEGY.md` as input. Source-tags strategy-derived acceptance criteria as `[strategy:<track-name>]` (joins existing `[user]` / `[paraphrase]` / `[inferred]` tags). Refuses to write spec contradicting an active track without `--override-strategy` flag. On flag fire: prompts user via `AskUserQuestion` to record a decision via `flowctl memory add --track knowledge --category decisions ...` (recommendation: yes; user can decline). Audit trail captured for future review.
- **R14:** `/flow-next:sync` (plan-sync agent at `agents/plan-sync.md`) Step 5 reads `STRATEGY.md`. Surfaces drift in `## Strategy drift flagged for review` spec heading parallel to existing "Decision overrides flagged for review". NEVER auto-supersedes — read-only surface only. Track renames replace inline with breadcrumb `<!-- Updated by plan-sync: track rename ... -->` mirroring existing glossary rename pattern.
- **R15:** Foreign-file refusal — `STRATEGY.md` without `generator: flow-next-strategy` frontmatter (or with different generator value) → skill prompts user via `AskUserQuestion` ("migrate / keep / rewrite?"). On "keep" — exits without writing. On "rewrite" — confirms via second prompt before destructive overwrite. Multi-format migration explicitly deferred to v2.
- **R16:** Subdirectory invocation walks up to repo root (`git rev-parse --show-toplevel`); surfaces `Using repo-root STRATEGY.md at <path>` line before any interview question fires. Does NOT create per-subdirectory STRATEGY.md files.
- **R17:** Ralph-block — `/flow-next:strategy` exits 2 with stderr message `[STRATEGY: user-triggered only — Ralph cannot run /flow-next:strategy]` when `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` is set. Mirrors `/flow-next:prospect` precedent. Autonomous loops have no business deciding repo strategy.
- **R18:** Codex mirror generated by `scripts/sync-codex.sh` validates green. `REQUIRED_OPENAI_YAML_SKILLS` array (lines 537-552) includes `flow-next-strategy`. `generate_openai_yaml` call added in workflow blue group `#3B82F6` (after the existing `flow-next-capture` call). After running sync, `plugins/flow-next/codex/skills/flow-next-strategy/` exists with rewritten tool names (`request_user_input` not `AskUserQuestion`); `plugins/flow-next/codex/agents/openai.yaml` updated.
- **R19:** Forbidden-vocabulary guard extension. Tier 1 jargon only (synergy / pivot / disrupt / thought-leadership / best-in-class / world-class / 10x — Rumelt's "fluff" hallmarks). NEW guard block in `ci_test.sh` (separate from R17 DDD-vocab guard at section 5c — comment must specify "this is the strategy-doc fluff guard, not R17"). Block scopes: `plugins/flow-next/skills/flow-next-strategy/` and `plugins/flow-next/scripts/flowctl.py` (cmd_strategy_*) and `plugins/flow-next/commands/flow-next/strategy.md`. Mirrored in `sync-codex.sh` validation block. References file `references/interview.md` excluded from guard (must describe anti-patterns to push back on them — same exemption pattern as glossary references).
- **R20:** Adding-a-new-user-facing-skill checklist (CLAUDE.md ~line 280) followed: canonical `SKILL.md` + `references/`, slash command, sync-codex `generate_openai_yaml` call, `REQUIRED_OPENAI_YAML_SKILLS` update, doc updates in `CLAUDE.md` + `plugins/flow-next/README.md` + `.flow/usage.md` + `~/work/mickel.tech/app/apps/flow-next/page.tsx`, `CHANGELOG.md` entry under `[flow-next 0.40.0]`. Version bump via `./scripts/bump.sh minor flow-next` updates 3 manifests; `./scripts/sync-codex.sh` regenerates Codex mirror; counts updated in 3 plugin.json descriptions.
- **R21:** Smoke test `plugins/flow-next/scripts/strategy_smoke_test.sh` exercises 12 cases T1-T12: (T1) first-run create-from-scratch; (T2) targeted section re-run preserves rest; (T3) subdir invocation walks up; (T4) husk file detected via `sections_filled == 0`; (T5) foreign-file refusal (no `generator` sentinel); (T6) mid-flow abandonment + resume; (T7) forbidden-vocab pushback; (T8) strategy-glossary conflict surfaces in interview spec; (T9) capture `--override-strategy` writes decision record; (T10) prospect grounding emits verbatim approach + tracks; (T11) plan-sync drift surfacing read-only; (T12) Ralph-block exit-2. Refuses to run from main plugin repo (per `glossary_smoke_test.sh:60-63` precedent). `KEEP_TEST_DIR=1` env opt-in. `trash` cleanup with `rm` fallback. Target <30s runtime.
- **R22:** STRATEGY.md survives a wipe of `.flow/` — repo-root invariant (R18 from glossary epic, mirror it explicitly in the skill prose). Project's strategy belongs to the project, not flow-next.
- **R23:** Last-section deletion leaves a husk — file never deleted; H1 + frontmatter remain (mirrors `render_glossary_file` rule at `flowctl.py:344`). `cmd_strategy_*` use shared `atomic_write` helper (already used by glossary subcommands at `flowctl.py:8669, 8796`).

## Early proof point

Task `fn-39-project-strategy-strategymd-anchor.1` (flowctl plumbing) validates the core file-shape contract — frontmatter sentinel parse/render round-trip, husk detection, atomic write, single-root walk. If the JSON-shape decisions don't hold up under round-trip testing, the whole multi-skill integration needs reconsideration before tasks 2-6 fire. Tasks 2-5 all consume `flowctl strategy status/read/list` output; task 1 freezes that contract.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | Repo-root file location + frontmatter shape | fn-39-project-strategy-strategymd-anchor.1, fn-39-project-strategy-strategymd-anchor.2 | — |
| R2  | Section structure locked, drop CE Marketing | fn-39-project-strategy-strategymd-anchor.2 | — |
| R3  | Bare AskUserQuestion + free-form substance / single-select routing | fn-39-project-strategy-strategymd-anchor.2 | — |
| R4  | Re-run section preservation + atomic per-section writes | fn-39-project-strategy-strategymd-anchor.1, fn-39-project-strategy-strategymd-anchor.2 | — |
| R5  | Pushback discipline + references/interview.md non-optional load | fn-39-project-strategy-strategymd-anchor.2 | — |
| R6  | flowctl strategy status JSON shape + husk semantics | fn-39-project-strategy-strategymd-anchor.1 | — |
| R7  | flowctl strategy read single-root walk + section filtering | fn-39-project-strategy-strategymd-anchor.1 | — |
| R8  | flowctl strategy list parallel to glossary list | fn-39-project-strategy-strategymd-anchor.1 | — |
| R9  | Doc-aware autodetect 3-condition + flag matrix | fn-39-project-strategy-strategymd-anchor.4 | — |
| R10 | Prospect Phase 0 grounding + out-of-scope-vs-strategy | fn-39-project-strategy-strategymd-anchor.3 | — |
| R11 | Plan research-scan + Strategy Alignment spec section | fn-39-project-strategy-strategymd-anchor.3 | — |
| R12 | Interview Strategy Conflicts section + ≤1/turn throttle | fn-39-project-strategy-strategymd-anchor.4 | — |
| R13 | Capture [strategy:<track>] tagging + --override-strategy + decision record | fn-39-project-strategy-strategymd-anchor.4 | — |
| R14 | plan-sync Strategy drift flagged for review (read-only) | fn-39-project-strategy-strategymd-anchor.4 | — |
| R15 | Foreign-file refusal via generator sentinel | fn-39-project-strategy-strategymd-anchor.1, fn-39-project-strategy-strategymd-anchor.2 | — |
| R16 | Subdirectory walk-up + UX surfacing | fn-39-project-strategy-strategymd-anchor.1, fn-39-project-strategy-strategymd-anchor.2 | — |
| R17 | Ralph-block exit-2 | fn-39-project-strategy-strategymd-anchor.2 | — |
| R18 | Codex sync + REQUIRED + generate_openai_yaml | fn-39-project-strategy-strategymd-anchor.5 | — |
| R19 | Forbidden-vocab Tier 1 guard (separate from R17 DDD) | fn-39-project-strategy-strategymd-anchor.5 | — |
| R20 | Doc updates + version bump + mickel.tech | fn-39-project-strategy-strategymd-anchor.5 | — |
| R21 | strategy_smoke_test.sh T1-T12 | fn-39-project-strategy-strategymd-anchor.6 | — |
| R22 | Survives `.flow/` wipe (R18 invariant mirror) | fn-39-project-strategy-strategymd-anchor.1, fn-39-project-strategy-strategymd-anchor.2 | — |
| R23 | Last-section delete leaves husk | fn-39-project-strategy-strategymd-anchor.1 | — |

## Decision context

- **Why repo-root STRATEGY.md, not `.flow/strategy.md`** — survives a wipe of `.flow/`, peer of README/CHANGELOG/GLOSSARY, generic markdown tooling reads it. R18 invariant established by 0.39.0 glossary epic; same rationale applies. Project's strategy belongs to the project, not flow-next.
- **Why single-root, NOT nearest-ancestor walk like glossary** — strategy is repo-wide by Rumelt's definition (one diagnosis, one guiding policy, coherent action). Multiple cascading STRATEGY.md files re-introduce the "is for everyone, is for no one" problem the skill exists to prevent. Glossary cascades because vocabulary is local; strategy is global.
- **Why this section structure** — derived from Richard Rumelt's *Good Strategy Bad Strategy* kernel (diagnosis / guiding policy / coherent action). Target problem maps to diagnosis, Our approach to guiding policy, Tracks to coherent action; Persona + Key metrics extend the kernel for repo-doc utility.
- **Why drop CE's Marketing section** — over-rotated for OSS-tools repos (the marketplace manifest IS the distribution surface). Adding sections has cost; CE's principle 3 ("Short is a feature") supports the cut.
- **Why no atomic-write `flowctl strategy add` plumbing** — strategy is too prose-heavy for atomic field-set CLI. The skill running the interview IS the LLM that should write the file (per CLAUDE.md "agentic vs deterministic" architecture rule). Atomic CLI plumbing fits term-list / decision-record / memory shape but not prose-heavy strategy shape.
- **Why bare `AskUserQuestion` in canonical (no inline cross-platform tables)** — flow-next CLAUDE.md explicitly forbids inline multi-platform tool tables ("they pollute the agent's context with abstraction noise"). Canonical files use Claude-native; sync-codex.sh rewrites to Codex form.
- **Why lead-with-recommendation only on routing questions, NOT substance** — substance questions (problem / approach / persona / metrics / tracks) must capture the user's own language. flow-next 0.39.0's lead-with-recommendation pattern primes the user out of their own framing; for strategy that's specifically what we don't want. Apply to routing only.
- **Why Tier 1 forbidden-vocab only (drop "leverage" verb)** — Rumelt's source uses "leverage" as a noun in *Good Strategy Bad Strategy* (the reference itself). False-positive risk too high for `references/learn-more.md` prose. Tier 1 list (synergy / pivot / disrupt / thought-leadership / best-in-class / world-class / 10x) is unambiguous.
- **Why separate guard block in `ci_test.sh` (not extending R17 DDD pattern)** — R17 comment specifically says "DDD vocabulary guard"; mixing concerns muddies the failure message and makes future maintenance harder. Each grep block has one purpose.
- **Why `--override-strategy` prompts decision record (not auto-write, not bypass)** — the override is exactly the kind of "load-bearing architectural choice" the decisions track was added for. Strong recommendation toward yes; user retains override authority. Aligns with three-criteria gate already in `/flow-next:interview` 0.39.0.
- **Why foreign-file refusal in v1 (no migration)** — CE-format and hand-written STRATEGY.md files have ambiguous section mappings. Multi-format migration is a v2 problem; v1 ships the sentinel + refusal pattern, documents the limitation, lets early adopters delete-or-rename to bootstrap.
- **Why per-section atomic writes (no draft state)** — race-window avoidance; mid-flow abandonment leaves a partially-populated file readable on disk; resume = "read existing sections, ask which empty/stale to fill next." Mirrors `flowctl epic set-plan` whole-file replace, but per-section. No `.flow/strategy/draft-*.md` state files.
- **Naming `/flow-next:strategy` writing `STRATEGY.md`** — mirrors GLOSSARY.md repo-root convention; well-known-filename discoverability. STRATEGY.md is not on the kmindi canonical OSS-root-files list, but the ALL_CAPS pattern is generic-tooling-readable and `glow` / `mdcat` / GitHub render handle it.

## Open questions

None for v1 — all priority architectural decisions resolved during planning. Documented for future revisits:
- Multi-strategy cascade for monorepos with genuinely independent subprojects (deferred — current rule: single root, surface "this monorepo has no per-project strategy split")
- Foreign-format / hand-written migration (deferred to v2 — v1 refuses with sentinel)
- Track ordering significance (priority vs alphabetical vs user-chosen — defaults to user-chosen; revisit if prospect rejection prose needs to cite "highest-priority track")
- Reverse loop ("you've shipped 5 epics in track X, suggest renaming") — out of scope for v1; strategy drives downstream, not the other way around

## References

- Rumelt strategy kernel: *Good Strategy Bad Strategy* — diagnosis / guiding policy / coherent action
- Glossary plumbing model: `plugins/flow-next/scripts/flowctl.py:63-405,8560-8812,16547-16622`
- Doc-aware autodetect precedent: `plugins/flow-next/skills/flow-next-interview/SKILL.md:81-106,192-318`
- plan-sync read-only-surface convention: `plugins/flow-next/agents/plan-sync.md:95-110,200-245`
- Smoke-test template: `plugins/flow-next/scripts/glossary_smoke_test.sh` (784 lines, 25 cases)
- Adding-a-new-user-facing-skill checklist: `CLAUDE.md` ~line 280
- R18 (survives uninstall) precedent: `CLAUDE.md` "Project glossary (v0.39.0+)" subsection
- Rumelt kernel: https://www.alexmurrell.co.uk/summaries/richard-rumelt-good-strategy-bad-strategy
- Repo-root file conventions: https://github.com/kmindi/special-files-in-repository-root
- Practice scout findings: arxiv 2507.02858 (RE 2025) interviewer-mistake taxonomy; matklad ARCHITECTURE.md cadence guidance
