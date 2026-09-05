---
title: "Adding a review backend: sweep ALL enumeration sites (config table, stage list, "
date: "2026-06-29"
track: bug
category: integration
module: "plugins/flow-next/docs, plugins/flow-next/scripts/flowctl.py"
tags: [review-backend, enumeration-drift, docs-sweep, cursor, fn-74, claude, fn-221]
problem_type: integration
symptoms: "codex impl-review NEEDS_WORK x3: each round found another stale rp/codex/copilot enum missing the new backend"
root_cause: "review-backend enumerations are scattered across many non-obvious sites (config tables, stage lists, setup templates, vault notes); several already omitted copilot, so a new backend exposes them as contradictions"
resolution_type: fix
last_updated: "2026-09-05"
---

## Problem
Adding a 4th cross-model review backend (`cursor`, fn-74) and doing the "docs sweep" task, codex impl-review went NEEDS_WORK three times — each round surfaced ANOTHER stale backend-enumeration site the obvious prose lists had missed. The enumerations live in many non-obvious places, and several already omitted even the *previous* backend (`copilot`), so they read as contradictions the moment you add the new one.

## What Didn't Work
Updating only the visible "RepoPrompt / Codex / Copilot" prose lists (README adversarial-gates row, GLOSSARY cross-model-review line, the impl-review command row). That left contradictory enumerations elsewhere in the SAME files the reviewer flagged as introduced findings.

## Solution
Sweep ALL of these enumeration sites when adding a review backend (the ones missed in fn-74, in flag order):
- `docs/flowctl.md`: the command list (~L14), the new `### <backend>` section (mirror copilot), the `review-backend` spec-grammar example (~L647), AND the **config-table `review.backend` row** (~L597) + the `config set` example comment (~L583) — these two were stale at `rp, codex, none` (omitted copilot too).
- `docs/teams.md`: BOTH the "RepoPrompt / Codex / Copilot" prose (×2) AND the **stage-[6] `Backends: rp, codex, copilot, none` exhaustive list** (~L171).
- `docs/skills.md`: the plan-review row's `(rp/codex/copilot)`.
- `skills/flow-next-setup/templates/usage.md`: the `review.backend # rp|codex|copilot|none` comment (~L165).
- Vault (`~/Documents/GordonsVault/.../flow-next - *.md`): Vocabulary backends line, Skills Catalog plan-review row, Lifecycle handover-#5 line, Architecture cmd list, **Release Timeline** (watch for a concurrent release-doc agent leaving a DUPLICATE row — dedupe).
- Downstream repos: flow-next.dev (`review/workflow` table + `--review` examples + spec-form note, `review/receipts` mode field, `releases/changelog`), AI×SDLC (`guides/flow-next.md` backend list + `code-review-tools-changelog.md`), GF (`spec/05-cross-model-review.md` + re-render `dist/*.html` + the bundled `code-factory-onboarding.html`).

NOTE: codex impl-review READS the vault file via its absolute path (flagged the duplicate/stale Release Timeline row) — downstream repo files in OTHER git repos are not in the diff, but vault notes referenced by absolute path are visible to it.

## Prevention
Before committing a review-backend docs task, run `grep -rniE "rp.{0,3}codex.{0,3}copilot|rp, codex|review.backend" docs/ skills/ README.md GLOSSARY.md | grep -vi <new-backend>` and confirm every hit is either a per-backend section header, a host-platform mention (Codex/Copilot/Droid as *drivers*), or a deliberately-scoped recommendation — never a stale exhaustive enumeration. Same shape as the tracker-adapter sweep (see related entry).

## Update 2026-08-01
The backend enum has grown since this entry: rp/codex/copilot/cursor/host/none (fn-123 added `host`). Add a new enumeration site to the sweep checklist: the PUBLISHED CONFIG SCHEMA (`scripts/gen_flow_config_schema.py` TABLE + `plugins/flow-next/schema/flow-config.schema.json`). Since fn-138, a new backend or effort value must be added there and the schema artifact regenerated, or `test_flow_config_schema_drift` fails.

## Update 2026-09-05

## Update 2026-09-05 (fn-221, `claude` backend)

The pipe-form grep (`rp|codex|copilot|cursor`) misses three enumeration shapes that the codex fan-out flagged on round 1 of the skill-prose task:

- Prose lists with backticks and commas: `Accepted explicit modes: \`rp\`, \`codex\`, \`copilot\`, \`cursor\`, \`host\`, \`export\`, \`none\`` in `flow-next-plan-review/workflow.md` — a parse branch the coordinator follows before it reaches the routing row, so the new `--review=<backend>` was advertised and rejected in the same skill.
- Slash-form return sets: `\`rp\`/\`codex\`/\`copilot\`/\`cursor\`/\`host\`/\`none\`` (`flow-next-work/SKILL.md` `review-backend` return line) and parenthesised "every other backend (...)" lists in reference files (`flow-next-work/references/host-deferred-review.md`).
- Receipt-contract prose copied from a sibling backend: the cursor workflow says "no effort key"; an effort backend's floor receipt carries `"effort": null`, never an absent key (`_backend_review_receipt_payload` always writes it when `include_effort` is set). Verify the receipt builder before promising a key shape.

Sweep command that catches all three: `grep -rnE 'rp\|codex|codex\|copilot|copilot\|cursor|codex, copilot|copilot, cursor|codex/copilot|copilot/cursor|\`rp\`, \`codex\`|\`copilot\`/\`cursor\`|copilot, (or|and) cursor' plugins/flow-next/skills plugins/flow-next/agents --include='*.md' --include='*.sh' --include='*.env' | grep -v codex/ | grep -vi <new-backend>` and read every hit; residual hits must be per-backend case arms or section headers only.
