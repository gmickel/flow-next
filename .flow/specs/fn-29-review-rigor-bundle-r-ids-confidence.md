# Review rigor bundle: R-IDs, confidence anchors, pre-existing separation, protected artifacts, trivial-diff skip

## Overview

Five prompt-level + minimal-flowctl changes that raise review signal quality and cut review cost across all three backends (rp, codex, copilot). All Ralph-integrated — the autonomous loop gets sharper verdicts and skips pointless work. Ships as one coherent patch release.

Inspired by MergeFoundry upstream patterns at `/tmp/mergefoundry-upstream` — specifically the review-rigor discipline, requirement-ID traceability, anchored confidence rubric, pre-existing classification, protected-artifact rules, and trivial-PR triage judgment.

**All changes preserve the current Carmack-level review as the default. Nothing in this epic replaces the existing review — only adds structure to its inputs and outputs.**

## Constraints (CRITICAL)

- Prompt-only for review skills; minimal flowctl additions (trivial-skip helper, extended receipt fields)
- Zero breaking changes to receipt contract — only additive fields (`unaddressed`, `suppressed_count`, `triage_skip` mode)
- Ralph mode unchanged — receipt contract extended, fix loop consumes new fields gracefully
- All three review backends (rp, codex, copilot) must benefit equally
- No new dependencies
- MergeFoundry-compatible: `.flow/specs/*.md` + `.flow/tasks/*.md` prose additions are additive; runtime state layered on top
- Run `scripts/sync-codex.sh` after prompt changes; `scripts/bump.sh patch flow-next` for this release

## Approach

Five features, grouped into 6 implementation tasks + 1 docs task:

1. **R-IDs + per-R-ID coverage** — stable requirement IDs in epic specs that travel into reviews
2. **Confidence anchors (0/25/50/75/100)** + suppression gate
3. **Pre-existing vs introduced separation**
4. **Protected artifacts** in review prompts
5. **Trivial-diff skip pre-check** via cheap model

## Design & Data Models

### R-ID convention

Epic specs get explicit numbered acceptance criteria:

```markdown
## Acceptance criteria
- **R1:** OAuth login works for Google provider
- **R2:** Session persists across page reloads
- **R3:** Logout clears session tokens
```

Rules:
- R-IDs are **plain markdown prose**, not YAML. Keeps `.flow/specs/*.md` human-editable.
- **Renumber-forbidden** after first review cycle. Reordering preserves IDs (`R1, R3, R5` is fine after deletion); never compact gaps.
- Plan skill writes R-IDs automatically when creating/refining specs.
- Plan-sync agent preserves R-IDs when syncing drift.

Task specs gain optional frontmatter:

```yaml
---
satisfies: [R1, R3]
---
```

Additive; tasks without `satisfies` work unchanged. Plan-sync and plan skills populate when obvious.

### Confidence anchor rubric

Reviewer rates each finding on exactly 5 discrete values:

| Anchor | Meaning |
|--------|---------|
| 100 | Verifiable from code alone, zero interpretation. Off-by-one in tested algorithm. Type error. Swapped arguments. |
| 75 | Full execution path traced: input X → branch Y → line Z → wrong output. Reproducible from code alone. A normal caller hits it. |
| 50 | Depends on conditions visible but not fully confirmable — e.g., whether a value can be null depends on unseen callers. |
| 25 | Requires runtime conditions with no direct evidence (specific timing, specific input shapes). |
| 0 | Speculative. |

**Suppression gate:** after dedup, suppress findings below anchor 75. **Exception:** P0 findings at anchor 50+ survive — critical-but-uncertain issues stay visible. Report `suppressed_count` (by anchor) in the review summary.

Review prompts instruct reviewers to use only these 5 values (no 33, 80, etc.). Treat as integers.

### Pre-existing classification

Reviewer classifies each finding with `pre_existing: true | false`:

- **introduced** — caused by this branch's diff
- **pre_existing** — was broken before this branch touched it

Verdict gate: **only `introduced` findings affect verdict.** `pre_existing` surface in a separate "Pre-existing issues (not blocking)" section.

Review prompt: "For each finding, inspect `git blame` or surrounding context. If the bug was present on the base branch, mark `pre_existing: true`."

### Protected artifacts

Review prompts include a hard-coded never-flag list. Any finding recommending deletion, gitignore, or removal of these paths must be discarded during synthesis:

- `.flow/*` — flow-next state, specs, tasks, memory
- `.flow/bin/*` — bundled flowctl
- `.flow/memory/*` — learnings store
- `docs/plans/*` — plan artifacts (if project uses this convention)
- `docs/solutions/*` — solutions artifacts (if project uses this convention)
- `scripts/ralph/*` — Ralph harness (when present in user project)

Path list is prose in the review prompt, not a runtime check — reviewer honors it during finding generation.

### Trivial-diff skip

New flowctl helper: `flowctl triage-skip --base <ref>` (or inline in impl-review skill).

Runs a cheap-model judgment (haiku for Claude, `gpt-5.4-mini`/`gpt-5.4-nano` for Codex, `claude-haiku-4.5` for Copilot) with the diff summary:

> "Is this diff worth a full code review? Answer SKIP or REVIEW.
> Skip only for: lockfile-only bumps (package-lock.json, bun.lock, pnpm-lock.yaml, yarn.lock, Gemfile.lock only), pure release chores (version bump + CHANGELOG entry only), pure generated-file regeneration (codex/ directory from sync-codex.sh), documentation-only diffs with no code changes. When in doubt, REVIEW — false SKIPs are worse than false REVIEWs."

Returns:
- `SKIP` → impl-review writes receipt `{mode: "triage_skip", verdict: "SHIP", reason: "<one-line>"}`, skips full review
- `REVIEW` → proceeds to configured backend

Default-on for Ralph (saves cycles). Opt-out via `--no-triage`.

## Receipt contract extensions

All review receipts gain these optional fields (existing consumers ignore unknown fields):

```json
{
  "unaddressed": ["R2", "R5"],
  "suppressed_count": {"50": 3, "25": 7, "0": 2},
  "pre_existing_count": 4,
  "introduced_count": 2
}
```

New receipt mode for triage-skip:

```json
{
  "type": "impl_review",
  "id": "...",
  "mode": "triage_skip",
  "base": "main",
  "verdict": "SHIP",
  "reason": "lockfile-only (bun.lock)",
  "model": "claude-haiku-4.5",
  "timestamp": "..."
}
```

Ralph reads these naturally — verdict is still SHIP/NEEDS_WORK, `unaddressed` gives the fix loop specific targets, `triage_skip` mode signals fast-path.

## File change map

### Prompts (zero flowctl change)
- `plugins/flow-next/skills/flow-next-plan/steps.md` — R-ID generation in spec template; note rule for renumber-forbidden
- `plugins/flow-next/skills/flow-next-plan/SKILL.md` — minor — mention R-ID output rule
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md` — confidence anchor rubric, pre-existing classification, protected artifacts list, per-R-ID coverage block
- `plugins/flow-next/skills/flow-next-epic-review/workflow.md` — same additions for epic-level review; per-R-ID coverage is most valuable here (matches fn-25's bidirectional coverage)
- `plugins/flow-next/agents/plan-sync.md` — preserve R-IDs; update `satisfies` when drift closes a gap
- `plugins/flow-next/agents/quality-auditor.md` — confidence anchors on findings it emits

### flowctl additions
- `plugins/flow-next/scripts/flowctl.py` — `triage_skip` subcommand (lightweight; calls existing codex/copilot/claude shell-out or uses a minimal prompt via the configured backend's fast model); extended receipt schema (add optional fields); `.flow/bin/flowctl.py` synced

### Docs
- `CHANGELOG.md` — new entry for this release
- `README.md` — brief mention of new review features
- `plugins/flow-next/README.md` — review rigor section; trivial-skip behavior; R-ID convention
- `CLAUDE.md` — spec grammar section gets R-ID bullet; receipt-extensions bullet
- `~/work/mickel.tech/app/apps/flow-next/page.tsx` — update feature list / FAQ to mention requirement-ID traceability + trivial-skip

### Codex mirror
- `scripts/sync-codex.sh` run after prompt edits to regenerate `plugins/flow-next/codex/`

### Version bump
- `scripts/bump.sh patch flow-next` → 0.32.0 → 0.32.1 (or minor if reviewer feels scope warrants 0.33.0)

## Ralph compatibility audit

Every change must preserve Ralph's autonomous contract. Per feature:

| Feature | Ralph impact |
|---------|--------------|
| R-IDs | Receipt gains `unaddressed` array; fix loop uses it for targeted fixes. Backward-compatible — receipts without `unaddressed` work as before. |
| Confidence anchors | Noise reduction — Ralph fixes fewer speculative findings per cycle. |
| Pre-existing separation | Ralph stops fighting bugs it didn't introduce. Verdict gate only considers `introduced` count. |
| Protected artifacts | Safety rail — Ralph can't auto-apply "delete `.flow/`" findings. |
| Trivial-diff skip | Default-on for Ralph. Saves rp/codex/copilot calls on release chores, lockfile bumps. Receipt mode `triage_skip` is valid for fix-loop gating. |

All changes are opt-out (not opt-in) for Ralph — the sharper review is the new default.

## Acceptance criteria

- **R1:** Plan skill emits R-IDs on acceptance criteria in every new `.flow/specs/*.md`; existing specs without R-IDs are not retroactively modified.
- **R2:** Task specs support optional `satisfies: [R1, R3]` frontmatter; plan and plan-sync populate when obvious.
- **R3:** Impl-review and epic-review workflows produce per-R-ID coverage status (met/partial/not-addressed/deferred) when a plan with R-IDs exists.
- **R4:** Any unaddressed R-ID (unless explicitly marked deferred in spec) flips verdict to NEEDS_WORK; receipt carries `unaddressed` array.
- **R5:** Review prompts instruct reviewer to use discrete 0/25/50/75/100 confidence anchors and to suppress <75 except P0@50+; receipt reports `suppressed_count`.
- **R6:** Review prompts instruct reviewer to classify each finding `pre_existing: true|false`; verdict gate considers only `introduced`; pre-existing findings surface in separate report section.
- **R7:** Review prompts contain protected-artifact path list; findings recommending deletion of those paths are discarded during synthesis.
- **R8:** `flowctl triage-skip --base <ref>` (or equivalent inline logic) returns SKIP for lockfile-only / release-chore / docs-only / generated-file-only diffs using a fast model.
- **R9:** On SKIP, impl-review skill writes receipt with `mode: "triage_skip"`, `verdict: "SHIP"`, `reason: "<one-line>"`; no expensive backend review is invoked.
- **R10:** Ralph mode respects all above changes without any Ralph-config file changes; trivial-skip is on by default in Ralph mode, opt-out via `--no-triage`.
- **R11:** All three backends (rp, codex, copilot) emit the new receipt fields consistently. Receipt format remains JSON and remains readable by existing Ralph scripts (unknown fields ignored).
- **R12:** Docs updated: README, plugin README, CLAUDE.md, CHANGELOG, website flow-next page. All mention the five features.
- **R13:** `scripts/sync-codex.sh` run after edits; Codex mirror regenerated. `scripts/bump.sh` run for version bump. No manual edits to `plugins/flow-next/codex/`.

## Boundaries

- Not adding multi-persona dispatch (see Epic 4 `--deep` flag instead).
- Not adding validation pass (Epic 4 `--validate`).
- Not adding walk-through routing (Epic 4 `--interactive`).
- Not touching the Carmack-level review prompt content — only adding structure around it.
- Not migrating existing open epic specs to add R-IDs retroactively.
- Not changing hooks, flowctl state schema, or Ralph config.env format.

## Risks

| Risk | Mitigation |
|------|------------|
| Reviewer ignores confidence rubric and uses ad-hoc numbers | Prompt explicitly enumerates the 5 values; ask reviewer to restate their anchor choice before scoring |
| Trivial-skip false positives (real issues skipped) | Strict whitelist (lockfile-only, chore-only, docs-only); "when in doubt, REVIEW" rule baked into prompt |
| Pre-existing classification drift — reviewer marks everything pre-existing to pass | Prompt requires `git blame`/base-branch evidence; Ralph fix loop can't auto-close a PR with 0 introduced findings if tests fail |
| R-ID schema drift across edits | Plan-sync preserves R-IDs; renumber-forbidden rule stated in plan skill prompt and in CLAUDE.md |
| Receipt field additions break older Ralph scripts | All new fields are optional; Ralph scripts read by key (`verdict`, `mode`) not by field count |
| Codex/Copilot fast-model cost | Trivial-skip calls are cheaper than full reviews; net cost goes down |

## Decision context

**Why bundle as one epic:** all five features touch the same three review prompt files and the same receipt contract. Shipping separately triples the review/CHANGELOG/bump overhead for the same surface area.

**Why all Ralph-integrated (not opt-in):** these are safety + signal improvements. Nothing added here costs more per review (trivial-skip saves cost). No reason to gate.

**Why R-IDs in prose, not YAML:** `.flow/specs/*.md` is human-edited during interviews. Prose is more readable and survives markdown re-rendering; runtime doesn't need to parse the IDs strictly (reviewer matches them via LLM reasoning).

**Why explicit 5 anchors:** continuous confidence scores collapse to a few discrete clusters in practice. Forcing the reviewer to pick one of five makes signal calibration reliable — MergeFoundry upstream data confirmed this pattern.

## Testing strategy

No unit tests added (prompt-only + minor flowctl). Validate via:

- Run `/flow-next:plan` on a new feature → verify spec has R1/R2/... prefixes
- Run `/flow-next:work` on any task from an R-ID-bearing spec → verify task spec may carry `satisfies` if plan populated it
- Run `/flow-next:impl-review` on a branch → verify output includes per-R-ID coverage table + confidence anchors + pre-existing section
- Trigger a "delete .flow/ runtime" finding synthetically (prompt the reviewer with a diff that includes `.flow/*`) → verify it's discarded
- Run `/flow-next:impl-review` on a lockfile-only branch → verify triage-skip fires, receipt has `mode: triage_skip`, no rp/codex/copilot call
- Run Ralph E2E smoke (`plugins/flow-next/scripts/ralph_smoke_test.sh`) to confirm loop still closes on an epic

## Follow-ups (not in this epic)

- Validation pass after NEEDS_WORK (Epic 4 `--validate`)
- Multi-persona lite (Epic 4 `--deep`) — adds passes **on top of** the existing Carmack review, not replacing it
- Walk-through routing (Epic 4 `--interactive`)
