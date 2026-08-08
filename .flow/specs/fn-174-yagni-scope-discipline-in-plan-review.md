# Overview

Planning agents systematically overbuild: in the flow-efficiency replay campaign, two independent opus runs of the same real request (gno fn-107) each produced 6 tasks / 21-23KB specs / a 500-900-line trust-consent subsystem, where the human-steered shipped version needed 4 tasks / 6.7KB and eliminated the trust problem structurally. A third run with scope-minimality prose produced 4 tasks, explicitly declined the trust machinery in Boundaries, and delivered -43% output tokens / -57% cost with reviewed quality ABOVE the unmodified arm. This spec lands that prose.

**Evidence standing: validated in the flow-efficiency replay campaign (`~/work/agent-scripts/flow-efficiency/results/06-IMPLEMENTATION-LIST.md` §1, `05-REPLAY-CAMPAIGN.md`). No further evaluation is required before landing.** Tested prose exists verbatim in worktree commit `5a54d5f0` (`replay/wt/flow-next-yagni`); this spec lands it plus one amendment its quality review demanded.

## Goal & Context

Make scope minimality a first-class, checkable planning discipline: every task traces to an R-ID, every R-ID traces to the request, unrequested capabilities go to Boundaries as one-line exclusions, and risk-elimination is preferred over risk-management machinery. Overengineering becomes a plan-review FINDING, not a taste note.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_review_prompt_template_parity test_review_prompt_constraints test_dogfood_template_parity test_template_canonical -q
./scripts/sync-codex.sh && ./scripts/sync-codex.sh && git status --short       # mirror regen, idempotent (2nd run = no diff)
```

## Architecture & Data Models

Prose/prompt edits only; the sole flowctl.py change is the byte-identical prompt-string mirror sync described below (no new verbs, no behavior change). Five edit sites (tested wording for the first four in `5a54d5f0`; all verified against main HEAD):

1. `plugins/flow-next/skills/flow-next-plan/steps.md` Step 2 (insert between the stakeholder paragraph ~L232 and `## Step 3` ~L234): binding scope-minimality block - trace-to-request rule, smallest architecture satisfying the ACs, structural-elimination-over-risk-machinery principle, one-line rejections in Decision Context, extras go to Boundaries.
2. `plugins/flow-next/skills/flow-next-plan-review/references/plan-review-prompt.md` criterion 6 (~L46): overengineering is a finding, with three concrete patterns (untraceable surface; risk-machinery where structural elimination is available; N-way generality for a one-case request).
3. `plugins/flow-next/templates/spec.md` (insert comment block between the second `-->` ~L62 and `# <spec-id> <Title>` ~L64): SCOPE DISCIPLINE comment block.
4. `plugins/flow-next/agents/worker.md` Rules list (insert between `- Follow existing code style` L278 and `- Add tests if spec requires them` L279): build to the AC, not past it; follow-ups noted in the done summary, never built.
5. `plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md` ~L189: the rp backend carries an independent copy of the criteria list where Scope is criterion **7** - apply the same expanded text there (renumbered as 7) so the rp review path gets the identical rubric.

**Pinned-prompt blast radius (site 2):** `plan-review-prompt.md` is one of the four extracted review prompts mirrored byte-identically as `PLAN_REVIEW_PROMPT_FALLBACK` in `plugins/flow-next/scripts/flowctl.py` (~L9323), guarded by `test_review_prompt_template_parity` (fallback==template, plus rendered fixtures `tests/fixtures/review_prompts/plan.txt` and `plan_no_tasks.txt`) and hash-pinned twice in `tests/test_prompt_text_pinned.py` (`PROMPT_HASHES["PLAN_REVIEW_PROMPT_FALLBACK"]` ~L95 and `TEMPLATE_HASHES[...plan-review-prompt.md]` ~L167). `.flow/bin/flowctl.py` must stay byte-identical to `scripts/flowctl.py`. So the site-2 edit carries five mechanical co-edits: fallback constant sync, `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py`, both hash-table updates, fixture rebaseline via `optimization/reached-path/generate_review_prompt_parity_evidence.py`, and a commit message stating what prompt text changed and why. Precedent commit for this exact shape: `16dcd7a0`.

Amendment (R2, applied at ALL five sites): each site's rigor-exemption clause must name BOTH (a) error/negative-case enumeration per AC AND (b) filesystem-identity, permission, and concurrency guards (realpath/symlink containment, lock-guarded writes, forced excludes of runtime state) as rigor, not scope. The amendment EXTENDS the tested exemption sentence in each site's own voice; exact per-site sentences are specified in task fn-174.1. It never replaces or weakens the tested wording.

Mirrors and copies: `scripts/sync-codex.sh` regenerates `codex/skills/flow-next-plan/steps.md`, `codex/skills/flow-next-plan-review/references/plan-review-prompt.md`, `codex/skills/flow-next-plan-review/workflow-rp.md`, `codex/templates/spec.md`, and `codex/agents/worker.toml` (md-to-toml transform - verify the multi-line bold bullet survives). `.flow/templates/spec.md` is the setup-managed copy the discovery cascade resolves BEFORE the bundled template - refresh it in the same change (fn-165 precedent: both updated together; `test_dogfood_template_parity` enforces it). Cursor ships no committed mirror - `install-cursor.sh` rsyncs the canonical tree at install time.

## Edge Cases & Constraints

- The rigor exemption is the load-bearing safety clause and MUST appear at all five sites (the yagni arm's only defect was eliminating a containment guard along with the features - "an eliminated guard, not an eliminated feature").
- worker.md phrasing risk: the guards clause gets its own sentence appended to the YAGNI bullet, so it cannot be read as re-muddying the build-to-AC rule.
- New prose is pure markdown/comment text with no Claude-native tool names - portable to Cursor/Droid/Grok as-is; the amendment must not introduce any.
- Hash recomputation: `test_prompt_text_pinned.py` hashes CRLF-normalized text; the FALLBACK hash is over the in-memory Python constant, not a file. Task fn-174.1 carries the literal commands.

## Acceptance Criteria

- **R1:** All five edit sites carry the scope-minimality prose functionally equivalent to `5a54d5f0` (site 5 = the same criterion text as site 2, renumbered 7). Errors: no error surface beyond prose consistency.
- **R2:** Every site's exemption clause names BOTH error-case enumeration AND filesystem-identity/permission/concurrency guards as rigor, not scope. Errors: a site missing either exemption fails review.
- **R3:** Both plan-review rubric copies (sites 2 and 5) list the three overengineering patterns as findings. Errors: none beyond R1.
- **R4:** Codex mirror regenerated (idempotent); `PLAN_REVIEW_PROMPT_FALLBACK` + dual copy + both hash pins + parity fixtures in step; CHANGELOG `## Unreleased` entry cites the replay-campaign evidence. Docs-site changelog rides the batched release (owed, recorded in the done summary). Cursor consumes the canonical tree at install time - no mirror artifact exists. Errors: parity/hash/fixture test red blocks merge.

## Boundaries

- No new evals or benchmark runs (evidence standing above).
- No enforcement code, no lint, no new flowctl verbs or behavior - the only flowctl.py delta is the byte-identical prompt-string mirror.
- No prose-presence/token guard tests (repo policy: live-file prose pins were deliberately removed 2026-08-07; deliberate-change detection is test_prompt_text_pinned.py only).
- No length/byte budgets (measured ignored 3x; rejected lever).
- No change to error-enumeration discipline itself (fn-165 stands as-is).

## Strategy Alignment

Active tracks served by this plan:
- **Self-improving through normal work** - replay-campaign evidence converted directly into pipeline prose discipline.
- **Cross-platform parity** - mirrors regenerated; new prose is portable-host-safe by construction; rp path gets the same rubric.

## Decision Context

Chosen over per-project config because the failure is universal in unattended planning and the discipline is self-exempting where a request genuinely needs the bigger design (the rules bind derivation, not outcomes - a traced task satisfying a real R-ID is always legal). Structural-elimination principle sourced from the campaign's sharpest reviewer finding: the shipped fn-107 made the profile format inert instead of building consent machinery; both unguided replay arms built the machinery. Rejected: shipping the tested prose without the guard-exemption amendment - the yagni arm's symlink-containment miss shows minimality pressure needs the guard clause before fleet exposure. Rejected: leaving `.flow/templates/spec.md` stale as overkill-avoidance - the cascade resolves it first, so a stale copy silently hides the new block from this repo's own planning. Rejected (review round 1): a token-presence guard test for the exemption clause - violates the repo's no-prose-pin policy; exact per-site sentences in the task file carry the discipline instead.

## Early proof point

Task fn-174.1 validates the core approach (the tested prose transplants cleanly and the guard-exemption amendment reads as rigor-preserving at all five differently-voiced sites). If a site's amendment fights its voice, re-evaluate wording before mirrors/CHANGELOG.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | Five sites carry 5a54d5f0-equivalent prose | fn-174.1 | - |
| R2  | Both exemptions named at every site | fn-174.1 | - |
| R3  | Three overengineering patterns in both rubric copies | fn-174.1 | - |
| R4  | Mirrors + parity chain + CHANGELOG | fn-174.1 (mirrors/parity), fn-174.2 (CHANGELOG/docs) | - |
