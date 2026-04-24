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
<!-- Updated by plan-sync: fn-32.1 validator block carries `kept` count and writes `verdict_before_validate` + `validator_timestamp`; upgrade path is NEEDS_WORK-only (never downgrades SHIP/MAJOR_RETHINK). -->
- **`--validate` flag** on `/flow-next:impl-review`. After NEEDS_WORK verdict, dispatches a validator pass (same backend session, receipt-driven session resume) that independently re-checks each finding. Drops false-positives with logged reasons. If all findings drop, verdict upgrades NEEDS_WORK → SHIP (never downgrades from SHIP or MAJOR_RETHINK); `verdict_before_validate` is recorded on upgrade. Receipt carries `validator: {dispatched, dropped, kept, reasons}` plus `validator_timestamp`. Env opt-in: `FLOW_VALIDATE_REVIEW=1`. Conservative bias — "only drop if clearly wrong; when uncertain, keep" (missing ids in validator output default to kept).
<!-- Updated by plan-sync: fn-32.2 receipt extensions include `cross_pass_promotions`, `verdict_before_deep`, `deep_timestamp` alongside `deep_passes`/`deep_findings_count`; deep-pass verdict path is SHIP → NEEDS_WORK only (never downgrades); cross-deep collisions dedup without promotion; auto-enable heuristic exposed via `flowctl review-deep-auto`. -->
- **`--deep` flag** on `/flow-next:impl-review`. Layers specialized deep-dive passes (adversarial always; security + performance auto-enabled based on changed file globs via `flowctl review-deep-auto`) on top of the primary Carmack-level review in the same backend session. Findings tagged `pass: <name>`; merged with primary via fingerprint dedup (primary wins on collision); primary+deep cross-pass agreement promotes primary's confidence one anchor step (0→25→50→75→100, ceiling 100). Cross-deep collisions dedup without promotion (avoids double-counting correlated passes). Explicit pass selection: `--deep=adversarial,security`. Env opt-in: `FLOW_REVIEW_DEEP=1`. Receipt carries `deep_passes` array, `deep_findings_count` per-pass dict, `cross_pass_promotions` list of `{id, from, to, pass}`, and `deep_timestamp`. Deep can upgrade verdict SHIP → NEEDS_WORK when it surfaces new blocking `introduced` findings (records `verdict_before_deep`); deep never downgrades the verdict.
<!-- Updated by plan-sync: fn-32.3 walkthrough block also carries `lfg_rest` (bool); receipt also writes `walkthrough_timestamp`. LFG-rest auto-classifier uses the simpler P0/P1 @ confidence ≥ 75 → Apply; otherwise → Defer rule (mirrors the primary-review suppression gate). Implementation ships two new flowctl helpers: `review-walkthrough-defer` (append-only sink writer) and `review-walkthrough-record` (atomic receipt stamper). Walkthrough never flips verdict. Branch slug allows `_` and `.` in addition to `a-zA-Z0-9-`. -->
- **`--interactive` flag** on `/flow-next:impl-review`. Per-finding walkthrough via platform blocking question tool (AskUserQuestion / request_user_input / ask_user). Four actions per finding: Apply / Defer / Skip / Acknowledge. "LFG the rest" escape hatch auto-classifies remainder: P0/P1 @ confidence ≥ 75 → Apply; otherwise → Defer (mirrors primary-review suppression gate). Deferred findings append to `.flow/review-deferred/<branch-slug>.md` (append-only; each review session gets a new `## <timestamp> — review session <receipt-id>` section). **Ralph-incompatible by design** — hard-errors when `REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1` is set. Receipt carries `walkthrough: {applied, deferred, skipped, acknowledged, lfg_rest}` + `walkthrough_timestamp`. Walkthrough never flips the verdict. New helpers: `flowctl review-walkthrough-defer` (appends to sink atomically) and `flowctl review-walkthrough-record` (stamps receipt counts).

### Changed
- Review workflow documents the phase ordering for flag combinations: primary → deep → validate → interactive → verdict.
- Receipt schema gains optional fields: `validator`, `validator_timestamp`, `verdict_before_validate` (validate); `deep_passes`, `deep_findings_count`, `cross_pass_promotions`, `verdict_before_deep`, `deep_timestamp` (deep); `walkthrough` (with `lfg_rest` field), `walkthrough_timestamp` (interactive). All additive — existing Ralph scripts work unchanged.
- New helpers: `flowctl review-deep-auto` reads changed files from stdin and emits the auto-enabled pass list (adversarial always + security/performance when globs match); `flowctl review-walkthrough-defer` appends deferred findings to `.flow/review-deferred/<branch-slug>.md`; `flowctl review-walkthrough-record` stamps walkthrough counts + timestamp into the receipt atomically.

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
