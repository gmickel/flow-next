# fn-56 Repo documentation improvements: accuracy, discoverability, contributor onboarding

> **Status note (2026-06-06):** Spec authored by a `/flow-next:plan` run on **Cursor** (proof the multi-agent planner works there). On review, the two phantom-reference bugs were verified real and **fixed standalone** (docs-only chore PR): **R2** (`flow-next-export-context` de-advertised its non-existent `/flow-next:export-context` slash command → now phrase-triggered) and **R3** (`docs/glossary.md` no longer references the non-existent `flow-next-glossary` skill → points at `flowctl glossary`). Two draft slips were corrected: the symlink direction (`CLAUDE.md` is the symlink → `AGENTS.md`, not the reverse) and R1's count (`flow-next-setup` is already visible → 4 invisible skills, not 5). **R1 / R4 / R5 / R6 / R7 remain open + deferred** (skills catalog, where-to-look parity, CONTRIBUTING/SECURITY + issue templates, stale-cohort pass, link-check CI gate) — coordinate with fn-54 per the Boundaries note before working them.

## Overview

The in-repo documentation surface (~30 hand-authored canonical docs + ~60 skill docs) has accumulated specific, verifiable defects: a phantom skill reference, an advertised slash command with no command file, several real skills invisible from every discoverability index, three "where to look" maps that have drifted out of parity, a stale-cohort of docs untouched since 2026-05-20, and missing standard community-health files (no `CONTRIBUTING.md` / `SECURITY.md`). This spec fixes the accuracy/consistency bugs, makes every shipped skill discoverable, adds contributor-onboarding + community-health docs, refreshes the stale cohort against current behavior, and (optionally) adds a markdown link-check CI gate to stop link drift from recurring.

Scope is **this repo only**. The `flow-next.dev` Starlight site is a paired-but-separate repo/workstream (per CLAUDE.md) and is explicitly out of scope here.

## Quick commands

```bash
# Skill count must match what every discoverability index lists
ls -d plugins/flow-next/skills/*/ | wc -l

# The phantom skill reference must be gone
grep -rn "flow-next-glossary" plugins/flow-next/docs/ && echo "STILL PRESENT (fix)" || echo "clean"

# After any skill/command edit, the Codex mirror must regenerate with no parity drift
./scripts/sync-codex.sh && git diff --stat

# Existing repo gate (R17 vocabulary + smoke) must stay green
bash scripts/ci_test.sh
```

## Architecture & Data Models

Documentation lives in four canonical zones (all edited as plain markdown, never the auto-generated `plugins/flow-next/codex/**` mirror):

- **Root**: `README.md` (front door + 5-command path + "Where to look" table at `README.md:253-276`), `AGENTS.md` (the real file; `CLAUDE.md` is a **symlink** to it — one file; carries the agent-facing "Where to look" table), `GLOSSARY.md`, `STRATEGY.md`, `CHANGELOG.md`, `LICENSE`.
- **`agent_docs/`**: `adding-skills.md`, `local-dev.md`, `releasing.md` (contributor/maintainer how-tos).
- **`plugins/flow-next/docs/`**: 13 reference docs + `README.md` (the doc index) + `ci-workflow-example.yml`.
- **Skill docs**: `plugins/flow-next/skills/<name>/SKILL.md` (+ `workflow.md`/`steps.md`/`references/`).

Three overlapping discoverability surfaces exist and drift independently: (1) `README.md` "Where to look" table, (2) `CLAUDE.md`/`AGENTS.md` "Where to look" table, (3) `plugins/flow-next/docs/README.md` doc index. There is **no skills catalog** anywhere — the doc index lists doc files, not skills.

**Cross-link discipline (inherited from fn-47):** relative repo paths only (no absolute `github.com` URLs), each doc self-contained, canonical sources linked never re-embedded (R17). The R17 forbidden-vocabulary guard already runs in `scripts/ci_test.sh`; `sync-codex.sh` enforces Codex-mirror parity.

## API Contracts

Not a code change — the "contracts" here are doc-surface invariants:

- Skill set on disk: `ls -d plugins/flow-next/skills/*/` (26 skills). Command set: `plugins/flow-next/commands/flow-next/*.md` (22 commands). Phrase-only skills with **no** command file: `flow-next-deps`, `flow-next-export-context`, `flow-next-rp-explorer`, `flow-next-worktree-kit`, `flow-next-drive`, and base `flow-next`.
- `flow-next-export-context/SKILL.md` advertises `Triggers on /flow-next:export-context` and gives `/flow-next:export-context ...` usage examples, but **no `commands/flow-next/export-context.md` exists** — the advertised command cannot resolve.
- `plugins/flow-next/docs/glossary.md:6` references `plugins/flow-next/skills/flow-next-glossary/` — a skill that does not exist. The real mechanism is `flowctl glossary` subcommands consumed by `/flow-next:interview`, `/flow-next:audit`, `/flow-next:sync`.

## Edge Cases & Constraints

- **Codex mirror parity:** any edit to a `SKILL.md`, a command file, or anything synced must be followed by `./scripts/sync-codex.sh`; the parity guard must stay green. Never hand-edit `plugins/flow-next/codex/**`.
- **Version-bump rule (fn-47 / CLAUDE.md):** pure docs / `agent_docs` / README changes do **NOT** bump the plugin version. BUT if a task adds a *command file* (a plugin surface) or otherwise changes runtime behavior, that is **not** docs-only and triggers a version bump + the count-sweep across all manifests (memory: `skill-adding-version-bump-leaves-stale`). Prefer the docs-only resolution for the `export-context` inconsistency (fix the SKILL.md advertisement) unless a command file is genuinely wanted.
- **Count drift:** human-readable skill/command/agent counts live on README + 3 JSON manifests; any change to the skill/command set must sweep all of them (memory entry).
- **`CLAUDE.md` is a symlink to `AGENTS.md`** (`AGENTS.md` is the real file) — edit `AGENTS.md` once, not twice.
- **String-enum config docs:** when documenting an enable command for a mode-selecting knob (`work.delegate`, `review.backend`), use the literal activating value, never the bool `true` idiom (memory: `docs-activation-command-for-string-enum`).

## Strategy Alignment

Active tracks served by this plan:
- **Spec-driven team patterns** — flow-next's identity as a *methodology* rests on accurate, discoverable docs; fixing discoverability and onboarding directly strengthens the methodology surface.
- **Cross-platform parity** — every skill/command doc edit re-runs `sync-codex.sh`; keeping the canonical docs accurate keeps the Codex mirror accurate.

## Boundaries

- **OUT: the `flow-next.dev` Starlight docs site.** Separate repo/workstream per CLAUDE.md. This spec touches only in-repo docs. (Maintainer-deferred site work from fn-50/51/52/53/55 is tracked there, not here.)
- **OUT: rewriting/trimming `SKILL.md` prompt *bodies*.** That is owned by the open spec **fn-54** (eval-driven prompt optimization, R4–R6). This spec only edits skill *frontmatter/discoverability metadata* and never the prompt-instruction bodies fn-54 is optimizing.
- **OUT: restructuring/trimming `CHANGELOG.md`.** It is intentionally the full release log (the scannable highlights live on the site). Any trim is a separate decision.
- **OUT: `llms.txt`.** Served by the docs site, not this repo.
- **OUT: deleting `docs/glossary.md` / `docs/strategy.md` / `docs/spec-template.md`** as "duplicates" — they are meta-references describing the shape of the root canon, not duplicates.

## Decision Context

The request ("improvements to our repo docs") is broad; research scoped it to verifiable, high-leverage defects rather than a speculative rewrite. We follow Diátaxis as a *lens* (label each doc's mode, fix mode-bleed when touched) rather than a top-down folder re-org — the official Diátaxis guidance explicitly warns against empty-quadrant restructures, and fn-47 already set the flat-`docs/` + index structure. We deliberately sequence after / coordinate with **fn-54** (the only open spec) because it rewrites many of the same `SKILL.md` files and adds a `CLAUDE.md` "Where to look" row — running both blind would cause heavy merge conflicts. The link-check CI gate is included because doc-link/drift bugs are a *recurring* failure mode in this repo's memory; a relative-path link-checker is a natural fit for the existing relative-paths-only discipline.

## Acceptance Criteria

- **R1:** Every skill shipped under `plugins/flow-next/skills/` is discoverable from at least one canonical index — specifically the four currently-invisible skills (`flow-next-deps`, `flow-next-export-context`, `flow-next-rp-explorer`, `flow-next-worktree-kit`) appear in the README commands/skills surface and a skills catalog; no shipped skill is missing. (`flow-next-setup` is **already** referenced in the README — it is NOT invisible; corrected from the initial draft.)
- **R2:** The `/flow-next:export-context` advertisement is consistent with reality — either a `commands/flow-next/export-context.md` exists OR `flow-next-export-context/SKILL.md` no longer advertises a slash command; the Codex mirror is regenerated and the parity guard is green.
- **R3:** `plugins/flow-next/docs/glossary.md` no longer references the nonexistent `flow-next-glossary` skill and instead points to the real mechanism (`flowctl glossary` + interview/audit/sync).
- **R4:** The "Where to look" tables in `README.md` and `CLAUDE.md`/`AGENTS.md` are in parity (identical doc-row set, or a deliberately documented divergence), coordinated with the row fn-54 adds.
- **R5:** The repo has `CONTRIBUTING.md` and `SECURITY.md` (and an issue-template set under `.github/ISSUE_TEMPLATE/`) following GitHub community-health conventions; `CONTRIBUTING.md` routes new contributors to the existing `agent_docs/` onboarding (`adding-skills.md`, `local-dev.md`, `releasing.md`).
- **R6:** The 2026-05-20 stale cohort (`memory-schema.md`, `glossary.md`, `strategy.md`, `spec-template.md`, `sync-codex.md`) plus `agent_docs/adding-skills.md` and `releasing.md` are verified against current behavior and corrected where stale; no doc describes removed/renamed behavior as current (legacy `flow`-plugin and epic-alias historical records are preserved as-is).
- **R7:** A markdown link-check CI gate validates internal relative links across the canonical docs surface and fails the build on dead links.

## Early proof point

Task fn-56-repo-documentation-improvements.1 validates the core approach: it makes the two consistency fixes (`export-context` advertisement + count/version invariants) and proves the edit → `sync-codex.sh` → parity-guard → `ci_test.sh` loop stays green for doc/skill edits. If that loop is not clean (parity drift, R17 guard trips, count sweep missed), re-evaluate the editing/sync discipline before proceeding with .2+.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | Every skill discoverable; 5 invisible skills surfaced + skills catalog | fn-56-repo-documentation-improvements.2 | — |
| R2  | `export-context` slash-command advertisement reconciled + mirror parity | fn-56-repo-documentation-improvements.1 | — |
| R3  | Phantom `flow-next-glossary` reference removed | fn-56-repo-documentation-improvements.4 | — |
| R4  | README vs CLAUDE.md "Where to look" parity (coordinated w/ fn-54) | fn-56-repo-documentation-improvements.2 | — |
| R5  | `CONTRIBUTING.md` + `SECURITY.md` + issue templates | fn-56-repo-documentation-improvements.3 | — |
| R6  | Stale-cohort + agent_docs correctness pass | fn-56-repo-documentation-improvements.4 | — |
| R7  | Markdown link-check CI gate | fn-56-repo-documentation-improvements.5 | — |
