# fn-29-review-rigor-bundle.7 Docs, website, codex mirror, version bump

## Description

Roll up the five preceding tasks into user-facing communication: CHANGELOG entry, README/plugin-README updates, CLAUDE.md note, website page refresh, codex mirror regeneration, version bump.

**Size:** M (docs + scripts, no code logic)

**Files:**
- `CHANGELOG.md`
- `README.md`
- `plugins/flow-next/README.md`
- `CLAUDE.md`
- `/Users/gordon/work/mickel.tech/app/apps/flow-next/page.tsx`
- `plugins/flow-next/.claude-plugin/plugin.json` (via bump.sh)
- `plugins/flow-next/.codex-plugin/plugin.json` (via bump.sh)
- `.claude-plugin/marketplace.json` (via bump.sh)
- `plugins/flow-next/codex/**` (via sync-codex.sh — auto-regenerated)

## Change details

### CHANGELOG.md

Prepend a new entry at top. Style matches existing flow-next 0.32.0 / 0.31.0 entries. Version target: patch bump to 0.32.1 (prompt-only + minor flowctl additive) or minor bump to 0.33.0 if scope warrants it. Recommend 0.33.0 — it introduces multiple new review behaviors and a new flowctl subcommand.

Template:

```markdown
## [flow-next 0.33.0] - YYYY-MM-DD

### Added
- **Requirement-ID traceability (R-IDs).** Epic specs emit numbered acceptance criteria (`R1:`, `R2:`, ...). Task specs support optional `satisfies: [R1, R3]` frontmatter. Impl-review and epic-review produce per-R-ID coverage tables (met / partial / not-addressed / deferred). Any unaddressed R-ID → verdict=NEEDS_WORK; receipt carries `unaddressed` array. Renumber-forbidden after first review cycle.
- **Confidence anchors (0/25/50/75/100) + suppression gate.** Reviewers rate each finding on 5 discrete anchors. Findings below 75 are suppressed except P0@50+. Review output reports suppressed count by anchor; receipt optionally carries `suppressed_count` dict.
- **Introduced vs pre-existing classification.** Reviewers mark each finding `introduced` (caused by this branch) or `pre_existing` (was broken before). Verdict gate considers only `introduced`. Pre-existing findings surface in a separate non-blocking section. Receipt carries `introduced_count` and `pre_existing_count`.
- **Protected artifacts in review prompts.** Hardcoded never-flag list (`.flow/*`, `docs/plans/*`, `docs/solutions/*`, `scripts/ralph/*`, etc.). Review synthesis discards findings recommending their deletion/gitignore. Prevents external reviewers unfamiliar with flow-next conventions from proposing destructive cleanups.
- **Trivial-diff skip (`flowctl triage-skip`).** Deterministic whitelist pre-check (lockfile-only / docs-only / release-chore / generated-file-only) returns `VERDICT=SHIP` with receipt `mode: triage_skip` (`source: deterministic`). Optional fast-model LLM judge (gpt-5-mini / claude-haiku-4.5) gated behind `FLOW_TRIAGE_LLM=1`; deterministic layer is conservative (ambiguous → REVIEW). On by default in Ralph mode; opt-out via `--no-triage` or `FLOW_RALPH_NO_TRIAGE=1`. Saves rp/codex/copilot calls on trivial commits. <!-- Updated by plan-sync: fn-29-review-rigor-bundle-r-ids-confidence.6 shipped deterministic-default (LLM opt-in via FLOW_TRIAGE_LLM=1), not fast-model-first as the spec originally described. -->

### Changed
- Impl-review and epic-review workflows emit structured per-finding metadata (severity, confidence, classification) instead of free-form prose.
- Receipt schema gains optional fields: `unaddressed`, `suppressed_count`, `introduced_count`, `pre_existing_count`, plus new receipt mode `triage_skip`. All additive — existing Ralph scripts read by key and ignore unknowns.

### Notes
- Zero breaking changes. Specs without R-IDs continue to work. Ralph's autonomous loop is unchanged in shape; review inputs and outputs are sharper.
- Carmack-level review remains the default and baseline. This release adds structure; it does not change the review style.
```

### README.md (root)

Short bullet in the flow-next feature list mentioning the rigor bundle. One sentence max.

### plugins/flow-next/README.md

Add a "Review rigor" section describing the five features with example outputs. Reference the receipt extensions. Link to CHANGELOG for specifics.

Also update the version badge (`bump.sh` handles this automatically).

### CLAUDE.md (root)

Add bullets under flow-next section:

- R-IDs: epic specs use `R1:`, `R2:` prefixes on acceptance criteria; renumber-forbidden.
- Review receipts may carry `unaddressed`, `suppressed_count`, `introduced_count`, `pre_existing_count`; `mode: triage_skip` indicates fast-path.
- `flowctl triage-skip --base <ref>` skips trivial diffs via deterministic whitelist; `FLOW_TRIAGE_LLM=1` enables optional fast-model judge for ambiguous diffs. <!-- Updated by plan-sync: fn-29-review-rigor-bundle-r-ids-confidence.6 shipped deterministic-default, not fast-model-first. -->

### Website: ~/work/mickel.tech/app/apps/flow-next/page.tsx

Update:
- Version string `0.32.0` → new version
- Metadata description — add "requirement-ID traceability" / "trivial-diff triage" keywords if feature-section permits
- Feature grid / FAQ if it mentions review rigor

The page currently is 1029 LOC of Next.js JSX with a curated feature list. Target the most visible sections: hero, feature grid, FAQ.

### sync-codex + bump

Run in order after all task 1-6 edits land:

```bash
# From repo root
scripts/sync-codex.sh
scripts/bump.sh minor flow-next   # or patch — judge scope
```

`sync-codex.sh` regenerates `plugins/flow-next/codex/{skills,agents,hooks.json}` — the Codex mirror of the new prompts. Commit the regenerated files.

`bump.sh minor flow-next` updates three manifests (marketplace.json, flow-next plugin.json, codex-plugin plugin.json) and the README badge.

### Tag + release

After merge:

```bash
git tag flow-next-v0.33.0
git push origin flow-next-v0.33.0
```

Triggers release automation + Discord notification per existing release workflow (docs/RELEASING.md).

## Rationale

This is pure rollup. Split out because doing all of this in the same task as prompt edits produces a muddy commit history and risks shipping docs that describe half-implemented features.

## Acceptance

- **AC1:** CHANGELOG has a new `[flow-next 0.33.0]` (or 0.32.1) entry listing all five features.
- **AC2:** plugin README has a "Review rigor" section.
- **AC3:** CLAUDE.md root references R-IDs, new receipt fields, triage-skip.
- **AC4:** Website page version + metadata reflect new release; at least one feature mention added.
- **AC5:** `scripts/sync-codex.sh` run cleanly with no manual edits needed to `plugins/flow-next/codex/`.
- **AC6:** `scripts/bump.sh` updates all three manifests + README badge.
- **AC7:** Git status shows no stray files after the codex regeneration step.
- **AC8:** Tag pushed (or staged, per user decision) to trigger release.

## Dependencies

- Depends on tasks 1-6 all merging first.

## Out of scope

- Separate Discord announcement copy (uses default release automation).
- npm package publish (flow-next is not an npm package).
- Breaking-change migration docs (this release is additive).

## Done summary
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
