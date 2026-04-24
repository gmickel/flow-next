# /flow-next:prospect — upstream-of-plan idea generation with ranked candidates

## Overview

New user-triggered skill that fills the "what should I build?" gap above `/flow-next:interview` and `/flow-next:plan`. Given a codebase and an optional focus hint, `prospect` generates many candidate ideas grounded in the repo, critiques every one with explicit rejection reasons, and surfaces only the survivors bucketed by leverage. Output is a ranked artifact under `.flow/prospects/<slug>-<date>.md` that feeds directly into `interview` or `plan` via a promote command.

Current flow-next upstream-of-work pipeline assumes a formed target: `interview` refines a known spec/epic, `plan` breaks a known spec into tasks. Neither handles the phase where the user is asking the system to propose directions. `prospect` closes that gap without forcing users to pre-invent candidates.

## Quick commands

```bash
# Smoke tests
plugins/flow-next/scripts/smoke_test.sh
plugins/flow-next/scripts/prospect_smoke_test.sh

# Unit tests
python3 -m unittest discover -s plugins/flow-next/tests
```

## Constraints (CRITICAL)

- Zero-dep: bash + Python stdlib + flowctl only. No new runtime deps.
- Cross-backend: works on Claude Code, Codex, Copilot, Droid. Blocking questions use each platform's tool (`AskUserQuestion` / `request_user_input` / `ask_user`); frozen numbered-options fallback when no blocking tool available or unavailable in current mode.
- Ralph-out: autonomous loops must not decide "what to build next". `/flow-next:prospect` hard-errors with exit 2 when `REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1` is set, same shape as fn-32 `--interactive`.
- Artifact-first: output is a markdown file under `.flow/prospects/`, not chat prose that vanishes. Resumable, queryable, promotable.
- Additive to existing lifecycle: does not replace `interview` or `plan`. Users with clear targets skip `prospect` and go straight to interview/plan as today.
- Inline skill (no `context: fork`): keeps `AskUserQuestion` available throughout.

## Approach

### Skill: `/flow-next:prospect [focus hint]`

Single skill invocation per ideation session. The optional argument is a freeform focus hint:

- **Concept:** `DX improvements`, `review-skill polish`, `test-suite health`
- **Path:** `plugins/flow-next/skills/` (ideate inside a subtree)
- **Constraint:** `quick wins under 200 LOC`, `minor-bump only`, `no new deps`
- **Volume hint:** `top 3` (survivors), `50 ideas` (generate ≥50), `raise the bar` (bias toward fewer, higher-leverage survivors)

**Volume semantics clarified:**
- `top N` means **exactly N survivors** after critique (generate enough to land N after ≥40% rejection floor).
- `N ideas` means **generate ≥N candidates** before critique; survivor count determined by critique pass.
- `raise the bar` means critique rejects more aggressively (target 60-70% rejection rate instead of 40%).

If no hint, ideation is open-ended — the skill picks its own coverage targets from repo structure and aims for 15-25 candidates → 5-8 survivors.

### Phase order

1. **Phase 0 — Resume check.** If `.flow/prospects/*.md` contains an artifact <30 days old, list them and ask (via blocking question tool) whether to extend, start fresh, or open the prior artifact. Corrupt artifacts (frontmatter parse fails, missing required sections) surface as `status: corrupt` and are never offered for extension. Artifacts >30 days stay visible via `list --all` but don't surface in resume.
2. **Phase 1 — Ground.** Scan the repo with graceful degradation:
   - Recently-modified files (git log, last 30 days; `scanned: none (no git)` if repo is ungitted).
   - Open `.flow/epics/*.json` with `status: open` (what's already being thought about; `scanned: none (no open epics)` if empty).
   - `.flow/memory/knowledge/*/` entries tagged with the focus hint (skip if `memory.enabled=false` or empty).
   - `.flow/memory/_audit/*.md` stale-flagged entries (if fn-34 has run — "bugs we keep hitting but haven't epic'd"; opt-in via `--no-memory` to skip).
   - `CHANGELOG.md` top 3 entries (what shipped recently — anti-duplication signal; skip if absent).
   - Focus-hint path resolution: if hint is a path that resolves to nothing, ask whether to open-ended or narrow differently.
3. **Phase 2 — Generate.** Produce a candidate list using **divergent-convergent scaffolding** and **persona seeding**. Prompt explicitly separates divergent phase ("wide net, encourage contrarian takes") from convergent. Personas used: `senior-maintainer`, `first-time-user`, `adversarial-reviewer` (minimum 2; bias toward distinct semantic regions). Volume: 15-25 default, or per hint. Each candidate has: `title`, `one-line summary`, `affected area(s)`, `estimated size (S/M/L/XL)`, `risk notes`.
4. **Phase 3 — Critique every candidate (second pass, separate prompt).** Input: flat candidate list from Phase 2. Output: `{verdict: keep|drop, reason}` per item using the rejection taxonomy `duplicates-open-epic | out-of-scope | insufficient-signal | too-large | backward-incompat | other`. Critique must reject at least 40% (or higher under `raise the bar`); if critique rejects fewer, skill reports "floor violation" and asks whether to regenerate, loosen, or ship anyway (R12).
5. **Phase 4 — Rank survivors (prose-only, bucketed).** Survivors go into three labeled buckets:
   - `High leverage (positions 1-3)` — small-diff, large-impact wins
   - `Worth considering (positions 4-7)` — solid mid-leverage
   - `If you have the time (position 8+)` — lower priority
   Each survivor carries a forced-format leverage sentence: `"Small-diff lever because X; impact lands on Y"`. No numeric scores.
6. **Phase 5 — Write artifact.** Emit `.flow/prospects/<slug>-<date>.md` atomically (write-then-rename) with YAML frontmatter and body sections. On same-day slug collision, suffix with `-2`, `-3` (R13). **Artifact is written before the handoff prompt** — Ctrl-C at Phase 6 preserves the artifact.
7. **Phase 6 — Offer handoff.** Blocking prompt: "Promote a survivor to an epic now? (`1`|`2`|...|`skip`|`interview`)". Route to `flowctl prospect promote` or `/flow-next:interview`. Numbered-options fallback uses the exact frozen string format.

### Promote command

```bash
flowctl prospect promote <artifact-id> --idea <N> [--epic-title "..."] [--force] [--json]
```

- Reads the artifact via `prospect read`; extracts survivor #N's title/summary/leverage.
- **Idempotency guard (R14):** if artifact frontmatter's `promoted_ideas` already contains N, refuses with an error + exit 2. `--force` overrides.
- Creates epic via existing `cmd_epic_create` infrastructure; pre-fills the spec skeleton with: original idea summary, leverage reasoning, suggested size, `## Source` section linking back to `.flow/prospects/<artifact-id>.md#idea-N`.
- Appends N to artifact frontmatter `promoted_ideas: [...]` (R20) — subsequent `list` shows `3/6 promoted`.
- Returns new epic ID via stdout / `--json`.

### List / read / archive

- `flowctl prospect list [--all] [--json]` — default filters to artifacts <30 days old; `--all` shows everything including archived and stale. Columns: id, date, focus, survivor count, promoted count, status.
- `flowctl prospect read <artifact-id>` — print body (parallels `flowctl memory read`); supports full id, slug+date, slug-only (latest date wins).
- `flowctl prospect archive <artifact-id>` — move to `.flow/prospects/_archive/`; never auto-archives.

## Artifact schema

```yaml
---
title: "DX improvements for flow-next"
date: 2026-04-24
focus_hint: "DX improvements"
volume: 22
survivor_count: 6
rejected_count: 16
rejection_rate: 0.73
artifact_id: dx-improvements-2026-04-24
promoted_ideas: []  # numeric survivor positions; updated by promote
status: active      # active | corrupt | stale | archived
---

## Focus
<focus_hint expanded>

## Grounding snapshot
- git log (30d): 34 recently-modified files
- Open epics: fn-14, fn-18, fn-21 (considered for overlap)
- CHANGELOG: 0.33.0 → 0.35.1 shipped in last 60d
- Memory: 3 knowledge entries matching "DX"
- Memory audit: n/a (not run)

## Survivors

### High leverage (1-3)

#### 1. <title>
**Summary:** <one line>
**Leverage:** Small-diff lever because <X>; impact lands on <Y>.
**Size:** S
**Next step:** /flow-next:interview

#### 2. ...

### Worth considering (4-7)

#### 4. ...

### If you have the time (8+)

#### 8. ...

## Rejected

- <title> — <taxonomy: reason>
- ...
```

## Acceptance criteria

- **R1:** `/flow-next:prospect [hint]` scans repo (recent files + open epics + recent CHANGELOG + memory + memory audit if present) before generating candidates; "Grounding snapshot" section lists exactly what was scanned with graceful-degradation fallbacks for missing inputs.
- **R2:** Volume semantics: `top N` = N survivors; `N ideas` = generate ≥N candidates; `raise the bar` = 60-70% rejection target; default = 15-25 candidates → 5-8 survivors.
- **R3:** Every candidate gets an explicit critique via a separate prompt pass; rejected candidates surface only in "Rejected" with a taxonomy reason (`duplicates-open-epic | out-of-scope | insufficient-signal | too-large | backward-incompat | other`); survivors only get prose in "Survivors".
- **R4:** Artifact writes atomically (write-then-rename) to `.flow/prospects/<slug>-<date>.md` before Phase 6 handoff prompt; YAML frontmatter matches the schema (title, date, focus_hint, volume, survivor_count, rejected_count, rejection_rate, artifact_id, promoted_ideas, status).
- **R5:** Resume check on Phase 0 — artifacts <30 days old list and ask whether to extend, start fresh, or read prior; extending appends a new section to the existing artifact with a dated header. Malformed artifacts detected (frontmatter parse, required sections present) and never offered for extension.
- **R6:** `flowctl prospect promote <id> --idea <N>` creates an epic with pre-filled skeleton (title, summary, leverage reasoning, `## Source` link) and returns the new epic ID via stdout / `--json`.
- **R7:** `flowctl prospect list / read / archive` implemented with `--json` support; `list` defaults to <30-day artifacts, `--all` shows everything.
- **R8:** Ralph-blocked: `/flow-next:prospect` exits 2 (matching fn-32 `--interactive`) when `REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1` is set. No env-var opt-in.
- **R9:** Handoff prompt at end of Phase 6 offers promote / interview / skip via blocking question tool; frozen numbered-options fallback (`1`|`2`|`skip`|`interview`) with exact string format when no blocking tool available.
- **R10:** Smoke test covers: generate-with-hint, generate-no-hint, resume of <30-day artifact, promote-to-epic, list/read/archive, Ralph-block exit 2, slug collision (same-day rerun suffixed), idempotent re-run (promote twice fails without `--force`).
- **R11:** Docs updated: CHANGELOG entry, plugins/flow-next/README.md (new "Prospecting" section before Planning + command catalog + flowctl cheat sheet + lifecycle diagram), CLAUDE.md command list entry, root README.md commands table, .flow/usage.md, website (`~/work/mickel.tech/app/apps/flow-next/page.tsx` — new feature card + command reference + FAQ + lifecycle diagram if present).
- **R12:** Rejection floor — critique must reject ≥40% (or 60-70% under `raise the bar`); if fewer, skill reports floor violation and asks whether to regenerate, loosen, or ship anyway.
- **R13:** Same-day slug collision: suffix with `-2`, `-3`, ...; slug base stays stable for `promote` lookup.
- **R14:** Promote idempotency: refuses if `promoted_ideas` contains the target N; `--force` overrides and warns.
- **R15:** Stale (>30d) artifacts hidden from default `list` but surface under `list --all`; `archive` never auto-fires.
- **R16:** Malformed artifact detection — resume check validates frontmatter parses and required sections exist; corrupt artifacts are listed with `status: corrupt` and never extended or promoted-to.
- **R17:** Graceful degradation when git/CHANGELOG/memory/audit is absent — grounding snapshot records `scanned: none (reason)` rather than erroring.
- **R18:** Persona seeding in Phase 2 — at least 2 distinct critic personas (from `senior-maintainer` / `first-time-user` / `adversarial-reviewer`); documented explicitly in workflow.md prompts.
- **R19:** Numbered-options fallback format frozen: `1`|`2`|`...`|`skip`|`interview` exact string; tested under cross-backend smoke.
- **R20:** Promote closes the loop — artifact frontmatter `promoted_ideas: [N...]` updated atomically on successful promote; `list` shows `<promoted>/<survivors>` counts.

## Early proof point

Task fn-33-…1 validates the core single-phase approach (Phases 0-1: resume check + grounding) without any LLM generation. If grounding can't produce a useful snapshot from a real repo (too noisy, too sparse, or too slow), re-evaluate the scanning strategy before building Phases 2-5.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|---|---|---|---|
| R1 | Grounded scan with snapshot | fn-33-…1, fn-33-…6 | — |
| R2 | Volume semantics | fn-33-…2 | — |
| R3 | Two-pass critique | fn-33-…2 | — |
| R4 | Atomic artifact write | fn-33-…3 | — |
| R5 | Resume check | fn-33-…1, fn-33-…4 | — |
| R6 | Promote command | fn-33-…5 | — |
| R7 | list/read/archive | fn-33-…4 | — |
| R8 | Ralph-block | fn-33-…1, fn-33-…6 | — |
| R9 | Handoff prompt + fallback | fn-33-…3 | — |
| R10 | Smoke test | fn-33-…6 | — |
| R11 | Docs | fn-33-…7 | — |
| R12 | Rejection floor | fn-33-…2 | — |
| R13 | Slug collision | fn-33-…3, fn-33-…6 | — |
| R14 | Promote idempotency | fn-33-…5, fn-33-…6 | — |
| R15 | Stale artifacts hidden | fn-33-…4 | — |
| R16 | Malformed detection | fn-33-…4 | — |
| R17 | Graceful degradation | fn-33-…1, fn-33-…6 | — |
| R18 | Persona seeding | fn-33-…2 | — |
| R19 | Numbered-options fallback | fn-33-…3, fn-33-…6 | — |
| R20 | promoted_ideas tracking | fn-33-…5 | — |

## Testing strategy

- **Unit:** YAML frontmatter round-trip, grounding-snapshot collector with graceful degradation cases, rejection-taxonomy parser, two-pass critique handoff, promote skeleton generation, idempotency guard, malformed-artifact detector.
- **Smoke (synthetic repo):** full end-to-end — generate artifact, list, read, promote to epic, verify epic pre-filled with `## Source` link, `promoted_ideas` updated. Second run reuses resume path. Same-day rerun produces `-2` suffixed slug. Promote twice fails without `--force`. Malformed artifact surfaces as `status: corrupt` and is not offered for extension.
- **Ralph regression:** `/flow-next:prospect` invoked with `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` must exit 2 without writing any artifact.
- **Edge cases:** empty repo (no git), zero open epics, focus hint resolves to nothing, concurrent runs (slug collision), interrupted mid-write (atomic rename prevents partial artifact).

## Boundaries

- Not replacing `interview` or `plan`. Prospect is only for the "I don't know yet" phase.
- Not a multi-persona parallel dispatch. Single-chat, sequential: generate → critique → rank → write. Personas are prompt-level scaffolding, not parallel subagent dispatch.
- Not inventing a ranking algorithm. Prose reasoning wins over quantitative scores; bucketed ranking (3/4/∞) provides just enough structure.
- Not committing the artifact. Artifacts are under `.flow/prospects/`, same convention as `.flow/epics` and `.flow/tasks`.
- Prospect never writes to `.flow/epics/` directly — only `promote` does.
- Prospect never invokes network calls (no web fetch, no external scoring); grounding is local-filesystem only.
- Prospect does not delete artifacts; only `archive` moves them.
- Prospect does not auto-seed memory with rejection reasons (out of scope; noise risk).

## Decision context

**Why "prospect" and not "ideate"?** "Ideate" is generic across plugins; "prospect" is engineering-adjacent (prospecting for leads / opportunities) and matches flow-next's action-verb vocabulary (plan, work, interview, resolve-pr, prime).

**Why artifact-first, not chat-first?** Chat prose vanishes. Artifacts are resumable (Phase 0), queryable (list / read), promotable (promote → epic). The point is to stop half-formed ideas evaporating between sessions.

**Why two-pass generate-then-critique?** Single-pass prompts soft-reject — everything is kept, just ordered. Two passes with separate system prompts force explicit rejection with a taxonomy; the critique pass doesn't see its own generation prompt, avoiding rationalization.

**Why persona seeding?** Post-RLHF LLMs exhibit pronounced mode collapse (Artificial Hivemind effect). Persona-seeded generation converges on distinct semantic regions, measurably increasing idea diversity. Two personas minimum; spec names three to choose from.

**Why bucketed ranking (3/4/∞) instead of flat?** Prose-only ranking is robust for top-3 but near-random past position 5 across reruns. Bucketing stabilizes the top-3 while preserving prose reasoning within each bucket.

**Why rejection floor ≥40%?** Without a forcing function, LLMs reject 0-10% and pad survivors. The 40% floor (and 60-70% for `raise the bar`) keeps critique sharp; violations trigger a user confirmation rather than silent pass-through.

**Why no Ralph opt-in?** Prospect is exploratory. An autonomous loop has no business deciding what a repo should tackle next; that's a human-in-the-loop judgement call. Matches fn-32 `--interactive` treatment.

**Why not seed memory with rejection reasons?** Tempting but noisy — half of "rejected" entries are legitimately reconsidered a month later under different context. Keep the artifact history as the audit trail.

## Risks

| Risk | Mitigation |
|---|---|
| Mode collapse (same 5-8 "obvious" ideas every run) | Persona-seeded divergent generation (R18); prior-session survivors fed as "already proposed" grounding, not re-ranked |
| Sycophancy (critique rationalizes generator) | Two-pass separation (R3); critique doesn't see generator's system prompt |
| Ranking inflation / soft-rejection | Forced rejection floor ≥40% (R12); separate rank pass after critique |
| Artifact sprawl (weekly runs accumulate) | Resume check extends recent (R5); `archive` subcommand for cleanup; >30d hidden from default `list` (R15) |
| Same-day slug collision on concurrent runs | Numeric suffix `-2`, `-3` (R13) |
| Promote duplication | Idempotency guard via `promoted_ideas` (R14, R20) |
| Grounding crashes on minimal repos | Graceful degradation — `scanned: none (reason)` (R17) |
| Interrupted mid-write corrupts artifact | Atomic write-then-rename (R4); malformed detection on resume (R16) |
| Numbered-options fallback drifts across backends | Frozen string format tested in smoke (R19) |
| Users confuse prospect with interview | Docs explicitly state: prospect = "many candidates, rank"; interview = "one, go deep"; plan = "one, break into tasks" |

## Follow-ups (not in this epic)

- Cross-project prospecting (scan multiple repos simultaneously)
- LLM-powered survivor-scoring (currently prose-only ranking)
- Scheduled weekly prospect via `/schedule` remote agent
- Integration with fn-34 `memory audit` — surface stale memory entries as ideation seed signal (partial in R1; deeper integration deferred)

## References

- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md:217-222` — Ralph-block pattern (copy for R8)
- `plugins/flow-next/skills/flow-next-impl-review/walkthrough.md:40-46` — platform tool table (copy for R9)
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:78-92` — AskUserQuestion usage discipline
- `plugins/flow-next/scripts/flowctl.py:3874-3955` — YAML writer + `write_memory_entry` (reuse for R4)
- `plugins/flow-next/scripts/flowctl.py:4441-4472` — `require_memory_enabled` gate (mirror for `require_prospects_enabled`)
- `plugins/flow-next/scripts/flowctl.py:4917-5242` — `cmd_memory_read` / `cmd_memory_list` (mirror for R7)
- `plugins/flow-next/scripts/flowctl.py:3009-3031` — `create_epic_spec` + `cmd_epic_create` (reuse for R6)
- `plugins/flow-next/skills/flow-next-resolve-pr/` — multi-file skill layout precedent
