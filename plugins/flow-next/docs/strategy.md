# Project Strategy

`STRATEGY.md` is a project-canonical strategic-intent file shipped in v0.40.0. Lives at the **repo root** (peer of `GLOSSARY.md` / `README.md`), NOT inside `.flow/`. Survives `rm -rf .flow/` — strategic intent is the project's, not flow-next's (R1 / R22, mirrors the glossary R18 invariant).

> Canonical example for this repo: [`../../../STRATEGY.md`](../../../STRATEGY.md).
> The skill that writes/maintains it: `plugins/flow-next/skills/flow-next-strategy/` — `/flow-next:strategy` is the editor. NO `flowctl strategy add/edit` plumbing (prose is too heavy for atomic field-set CLI).

## Format

Plain GFM markdown. Frontmatter contains 3 keys only — `name`, `last_updated` (ISO date), `generator: flow-next-strategy`. The generator key is the foreign-file sentinel.

Section structure derived from Richard Rumelt's strategy kernel (*Good Strategy Bad Strategy*: diagnosis / guiding policy / coherent action), extended with persona + metrics for repo-doc utility.

| Section | Required | Notes |
|---------|----------|-------|
| `Target problem` | yes | Diagnosis |
| `Our approach` | yes | Guiding policy |
| `Who it's for` | yes | Personas |
| `Key metrics` | yes | What we're tracking |
| `Tracks` | yes | Coherent actions |
| `Milestones` | optional | Delete entirely if unused |
| `Not working on` | optional | Delete entirely if unused |

CE's `Marketing` section explicitly NOT included — over-rotated for OSS-tools repos. Optional sections deleted entirely if unused; never left as empty headers.

## Resolution

Single-root walk from cwd UP to first `STRATEGY.md` found, capped at repo root via `git rev-parse --show-toplevel`. NOT nearest-ancestor like glossary — strategy is repo-wide by Rumelt's definition (one diagnosis, one guiding policy, coherent action). Subdirectory invocation surfaces `Using repo-root STRATEGY.md at <path>` before any interview question fires; does NOT create per-subdirectory `STRATEGY.md` files.

## Subcommands

```bash
flowctl strategy status                          # exists/husk/sections_filled/total_sections/last_updated
flowctl strategy status --json
flowctl strategy read                            # full file
flowctl strategy read --section approach
flowctl strategy read --json
flowctl strategy list --json                     # parallel to flowctl glossary list
```

## Husk semantics

A file with H1 + frontmatter only and no populated H2 sections returns `{exists: true, husk: true, sections_filled: 0}` from `flowctl strategy status`. Last-section deletion leaves a husk on disk — the file is **never** deleted (R23, mirrors `render_glossary_file`). Doc-aware autodetect branches on `flowctl strategy status --json | jq '.sections_filled >= 1'`, NOT on `[[ -f STRATEGY.md ]]` — same trap glossary fell into.

## How the rest of flow-next uses it

- **`/flow-next:prospect`** Phase 0: reads `STRATEGY.md` when `sections_filled >= 1`. Injects approach + active tracks verbatim into candidate-generation prompt. Adds `out-of-scope-vs-strategy` to the rejection taxonomy. Advisory — never auto-rejects.
- **`/flow-next:plan`** research scan: emits a `## Strategy Alignment` spec section listing which active tracks the plan serves. Drift surfaced as a `## Strategy drift flagged for review` block (read-only — never auto-supersedes).
- **`/flow-next:interview`** doc-aware mode: surfaces conflicts in a `## Strategy Conflicts` spec section parallel to `## Glossary Conflicts`. Throttle ≤1 strategy-conflict question per interview round.
- **`/flow-next:capture`** Phase 0: source-tags strategy-derived acceptance criteria as `[strategy:<track-name>]` (joins `[user]` / `[paraphrase]` / `[inferred]` tags). Refuses to write spec contradicting an active track without `--override-strategy`. On flag fire: prompts to record a decision via `flowctl memory add --track knowledge --category decisions ...`.
- **`/flow-next:sync`** Step 5: surfaces drift in a `## Strategy drift flagged for review` heading. NEVER auto-supersedes — read-only surface only. Track renames replace inline with a `<!-- Updated by plan-sync: track rename ... -->` breadcrumb.

## Foreign-file refusal (v1)

A `STRATEGY.md` without `generator: flow-next-strategy` frontmatter (or with a different generator value) routes via the platform's blocking-question tool (migrate / keep / rewrite?). On "keep" — exits without writing. On "rewrite" — confirms via second prompt before destructive overwrite. Multi-format migration (CE-format / hand-written) explicitly deferred to v2.

## Forbidden vocabulary (R19, separate from R17 DDD)

Tier 1 jargon only — Rumelt's "fluff" hallmarks: `synergy / pivot / disrupt / thought-leadership / best-in-class / world-class / 10x`. Two-tier guard: canonical scan in `ci_test.sh` (separate block from R17 — never merge them) covers `flow-next-strategy/SKILL.md` + `cmd_strategy_*` regions in `flowctl.py` + `commands/flow-next/strategy.md`; mirror scan in [`../../../scripts/sync-codex.sh`](../../../scripts/sync-codex.sh) validation block covers `plugins/flow-next/codex/skills/flow-next-strategy/`. The `references/interview.md` file is excluded — it must describe these anti-patterns to push back on them.

## See also

- [`../../../STRATEGY.md`](../../../STRATEGY.md) — canonical strategy for this repo.
- [`glossary.md`](glossary.md) — peer doc for repo-root `GLOSSARY.md`.
- [`memory-schema.md`](memory-schema.md) — `knowledge/decisions/` subtree pairs naturally with strategy for load-bearing track choices.
