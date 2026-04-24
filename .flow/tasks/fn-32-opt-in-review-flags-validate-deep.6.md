# fn-32-opt-in-review-flags.6 Docs, website, codex mirror, version bump

## Description

Rollup for Epic 4: CHANGELOG, READMEs, CLAUDE.md, website page, codex regeneration, version bump.

**Size:** M (docs only)

**Files:**
- `CHANGELOG.md`
- `plugins/flow-next/README.md`
- `CLAUDE.md`
- `/Users/gordon/work/mickel.tech/app/apps/flow-next/page.tsx`
- Version manifests + codex mirror (via bump + sync-codex)

## CHANGELOG.md

```markdown
## [flow-next 0.36.0] - YYYY-MM-DD

### Added
- **`--validate` flag** on `/flow-next:impl-review`. After NEEDS_WORK verdict, dispatches a validator pass (same backend session) that independently re-checks each finding. Drops false-positives with logged reasons. If all findings drop, verdict upgrades to SHIP. Receipt carries `validator: {dispatched, dropped, reasons}`. Env opt-in: `FLOW_VALIDATE_REVIEW=1`. Conservative bias — "only drop if clearly wrong; when uncertain, keep."
- **`--deep` flag** on `/flow-next:impl-review`. Layers specialized deep-dive passes (adversarial always; security + performance auto-enabled based on changed file globs) on top of the primary Carmack-level review in the same backend session. Findings tagged `pass: <name>`; merged with primary via confidence anchors; cross-pass agreement promotes confidence one anchor step. Explicit pass selection: `--deep=adversarial,security`. Env opt-in: `FLOW_REVIEW_DEEP=1`. Receipt carries `deep_passes` array + per-pass finding counts.
- **`--interactive` flag** on `/flow-next:impl-review`. Per-finding walkthrough via platform blocking question tool (AskUserQuestion / request_user_input / ask_user). Four actions per finding: Apply / Defer / Skip / Acknowledge. "LFG the rest" escape hatch auto-classifies remainder by severity + confidence. Deferred findings append to `.flow/review-deferred/<branch-slug>.md`. **Ralph-incompatible by design** — hard-errors when `REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1` is set. Receipt carries `walkthrough: {applied, deferred, skipped, acknowledged}`.

### Changed
- Review workflow documents the phase ordering for flag combinations: primary → deep → validate → interactive → verdict.
- Receipt schema gains 3 optional fields: `validator`, `deep_passes`, `walkthrough`. All additive — existing Ralph scripts work unchanged.

### Notes
- **Default review is unchanged.** These flags are opt-in. The Carmack-level single-chat primary review remains the baseline and the primary. Flags add structure, validation, and deep-dives **on top** — they do not replace.
- `--deep` in same backend session means context carry-over (cheaper per pass); parallel multi-agent dispatch is intentionally not adopted to preserve rp/codex/copilot parity.
- `--interactive` has no env var; per-invocation only to prevent accidental Ralph engagement.
- Depends on flow-next 0.33.0 (confidence anchors, pre-existing classification) for flag semantics.
```

## plugins/flow-next/README.md

New section "Opt-in review flags":

- `--validate` description + cost trade-off + env opt-in
- `--deep` description + pass auto-enable heuristics + explicit pass selection + env opt-in
- `--interactive` description + Ralph-block note + defer sink location
- Flag combination matrix (8 rows)
- Link to CHANGELOG for details

## CLAUDE.md (root)

Add bullets under flow-next review section:

```markdown
**Opt-in review flags (0.36+):**
- `--validate` or `FLOW_VALIDATE_REVIEW=1` — drops false-positive findings via validator pass on NEEDS_WORK
- `--deep` or `FLOW_REVIEW_DEEP=1` — adversarial + auto-enabled security/performance passes on top of primary review
- `--interactive` — per-finding walkthrough (Apply/Defer/Skip/Acknowledge); user-triggered only, not Ralph-compatible
- Flags combine freely; receipt extensions additive
```

## Website: ~/work/mickel.tech/app/apps/flow-next/page.tsx

- Update version string → 0.36.0
- Add feature card / FAQ entry describing opt-in review rigor
- Emphasize that **default review is unchanged** — flags are additive

## sync-codex + bump

```bash
scripts/sync-codex.sh
scripts/bump.sh minor flow-next
```

## Tag + release

```bash
git tag flow-next-v0.36.0
git push origin flow-next-v0.36.0
```

## Acceptance

- **AC1:** CHANGELOG has `[flow-next 0.36.0]` entry describing all three flags with Ralph-compat notes.
- **AC2:** plugin README "Opt-in review flags" section describes each flag + combination matrix.
- **AC3:** CLAUDE.md root mentions all three flags with env-var forms + Ralph notes.
- **AC4:** Website page updated: version + feature mention that emphasizes additive-not-replacing nature.
- **AC5:** sync-codex.sh run cleanly.
- **AC6:** bump.sh updates all three manifests + README badge.
- **AC7:** Tag pushed (or staged) to trigger release.

## Dependencies

- fn-32-opt-in-review-flags.1, .2, .3, .4, .5 (all features + tests land first)

## Done summary
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
