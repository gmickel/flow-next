# Prime CX group: context-rightsizing checks for agent instruction files

## Goal & Context
<!-- scope: business -->

`/flow-next:prime` asks exactly one question today, in every pillar: **is there enough?** Enough substance in the instruction file, enough commands that actually resolve and run, enough test/build/observability evidence to earn a rung on the operability ladder. fn-92 made that question opinionated (classify first, judge substance, hard gates), and it works.

It never asks the opposite question: **is there too much, and is it the right shape?**

That gap stopped being theoretical in July 2026. Claude Opus 5 shipped on 2026-07-23 and the first field reports were not about capability but about *instruction load*: two independent teams (Compound Engineering; Every's week-long Day-0 review) reported the model arguing with instructions, stopping before work finished, and behaving materially better once elaborate hand-tuned skills were deleted and rebuilt from scratch. The model card's own FrontierCode curve corroborated the effort half first-party (peak at medium, degrading through high/xhigh). flow-next's own pipeline did not reproduce the failure (fn-122 probe, 2026-07-25: a full opus-5@medium-conducted plan-to-merged-PR arc chained cleanly), and the working hypothesis for why is that a verdict-line-and-receipt CONTRACT survives where freeform accumulated prose does not.

Both halves of that story point at the same user-facing problem: **teams are carrying instruction files tuned for a previous model generation, and nobody has a check that tells them.** An instruction written to compensate for a 2025-era weakness ("always restate the full file path", "do not stop before finishing", elaborate step-by-step scaffolding for something the model now does unprompted) is not neutral once the compensation is unnecessary. It is context that competes with the actual task, and in the Opus 5 reports it actively degraded behavior.

This spec adds a **CX (context-rightsizing) check group** to prime: a small, evidence-gated set of judgments about whether a repo's agent instruction files are the right size and shape, with the stale-model-compensation check as the headline. It is deliberately narrow, deliberately informational in v1, and deliberately proposal-only. The value is telling a team something no other readiness tool tells them; the risk is becoming a false-positive generator that trains users to ignore prime, and every design decision below is made against that risk.

**Provenance (honest):** the CX idea originated as an out-of-scope proposal (a CX1-CX8 group) drafted by a different agent against a v3.1.1-era checkout on another host. That diff was never present in this repository and was not consulted; only its eight one-line headings were. This spec re-derives the durable subset against current main (3.4.5), drops what is already shipped or already covered, and folds eight headings into three checks plus one constraint.

## Architecture & Data Models
<!-- scope: technical -->

Standard flow-next split, and this feature sits hard on the skill side of it. "Is this instruction a stale model compensation?" and "do these two rules contradict?" are judgment questions over prose. There is **no deterministic scorer, no new flowctl subcommand, no `flowctl prime cx` anything**, and no weighted math substituting for the judgment (the CLAUDE.md how-to-spot-a-mistake list applies directly: a stoplist of "bad instruction phrases" would be exactly the deterministic-when-it-should-be-agentic error).

### The three checks

Eight proposed headings collapse to three, because several were the same finding wearing different names and two were already covered:

| id | Check | What a finding requires |
|---|---|---|
| **CX1** | **Stale model compensations** | An instruction whose only purpose is to work around a limitation the current model generation does not have. Evidence: quote the line, name the compensation pattern (anti-laziness nagging, output-format babysitting, redundant self-verification scaffolding, step-count padding, "think step by step" ritual), and state what breaks if removed (usually nothing) |
| **CX2** | **Contradictory or duplicated instructions** | Two rules that cannot both be satisfied, or the same rule restated in materially different words. Evidence: both locations quoted, plus which one the repo's own behavior/commits suggest is live |
| **CX3** | **Encyclopedic drift** | The instruction file inlines content the agent can read off the repo itself (directory listings, dependency versions, generated inventories) or buries load-bearing rules under reference material that belongs behind a pointer. Evidence: the inlined block, the source it duplicates, and the navigational rewrite |

CX3 absorbs three of the original headings (navigational-vs-encyclopedic, inferable/generated clutter, progressive disclosure) because they produce one finding with one fix: *make this file a map, not a textbook*.

**Dropped, with reasons stated so they are not re-proposed:** *expressive CLI/tool interfaces* overlaps AO1 (agent-readable logs) and TO1 (failure artifacts) and belongs in the operability ladder if anywhere; *rich source/test/rubric references* overlaps the existing instruction-file substance grading; and *retention of hard security controls* is not a check at all but a constraint on the other three (see below).

### The safety constraint (was CX8)

Every CX finding is a **proposal**, never an application, in v1. Prime's existing license to fix agent readiness does not extend here.

- **Never propose deleting** security rules, approval gates, forbidden-action lists, consent boundaries, or credential-handling instructions, even when they look redundant. A duplicated security rule is cheap; a deleted one is a live incident.
- **Never auto-apply.** CX findings surface in the report and ranked next-actions. Any instruction-file edit is human-applied, or explicitly consented per-finding if a later spec adds an apply path.
- **Autonomous invocations report only.** Under `FLOW_AUTONOMOUS` / Ralph / receipt-driven prime, CX behaves as it does elsewhere: findings in the report, nothing written.

### Scoring posture: informational in v1

CX findings do **not** score into the pillar totals, do not move the agent-readiness level, and do not participate in the hard gates (G1/G2/G3). They surface as ranked next-actions alongside the verdict.

This is a deliberate asymmetry with the rest of prime, and the reason is calibration risk. A missing test command is objectively missing; "this instruction is stale" is a judgment that will sometimes be wrong, and a wrong judgment that *lowers a team's readiness score* is far more damaging to trust than one that adds a declinable suggestion. Precedent exists in the skill (HP4, HP15, DC8 are informational). Promotion to scored is a follow-up decision to be made on evidence from real runs, not now.

### Where it lands

- `plugins/flow-next/skills/flow-next-prime/pillars.md` - the three CX rows, evidence contracts, informational marking.
- `plugins/flow-next/skills/flow-next-prime/workflow.md` - the scan step that gathers CX evidence and the judgment pass.
- `plugins/flow-next/skills/flow-next-prime/remediation.md` - the proposal shapes (consolidation and navigational rewrites), plus the never-delete constraint.
- `plugins/flow-next/agents/claude-md-scout.md` - cheap evidence gathering only (file inventory, near-duplicate line pairs, blocks that mirror a real repo artifact). The scout gathers; the host judges. Its existing substance grading is unchanged.
- `plugins/flow-next/skills/flow-next-prime/SKILL.md` - one line in the outcome/verdict description.
- Codex mirror regenerated; guards stay green.

## API Contracts
<!-- scope: technical -->

**No new flowctl surface.** `flowctl prime classify` is the deterministic classification emitter and stays exactly as it is: CX is a judgment layer in the skill, not classification data, and adding it there would put intelligence in the plumbing.

Report contract (the deliverable is the report, per prime's existing output rules): CX findings appear in their own section, each carrying id, the quoted evidence, the named pattern, the proposed rewrite, and an explicit `informational` marker so no reader mistakes a CX finding for a scored gap. Findings are ordered by confidence, and a run with zero CX findings prints one line saying so rather than an empty section.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Length alone is never a finding.** A long instruction file that is dense and load-bearing is correct. Every CX finding must cite specific lines and a specific defect. A "your CLAUDE.md is 400 lines" observation is not a finding and must not be emitted.
- **Model-era detection must not become a version blocklist.** CX1 judges the *shape of the compensation*, never a model name. The repo's own doctrine is role labels over volatile model ids; a check that greps for "GPT-4" or "Claude 3" would rot immediately and would miss compensations that name no model at all (the common case).
- **Intentional redundancy is legitimate.** A rule restated in a per-directory instruction file for locality is often correct, not duplication. CX2 fires on contradiction or on verbatim-scale restatement in the same file, not on deliberate local reinforcement.
- **Nested and monorepo instruction files.** The check runs against the substantive file set prime already discovers (including the `@`-include shim discipline); a shim is never flagged for being thin.
- **Non-code and docs repos.** Instruction files there are legitimately more prose-heavy. CX3 must weigh "can the agent read this off the repo?" against what the repo actually contains.
- **Generated instruction files.** If the file is generated (a tool writes it), the finding belongs against the generator, and the report must say so rather than proposing a hand edit that the next generation overwrites.
- **flow-next's own CLAUDE.md is a calibration fixture, not an assumed negative.** It is long, dense, and deliberately encyclopedic in places. The bar is not "produces zero findings" - it is that a human reading whatever CX proposes on it judges the proposals reasonable and non-destructive. If CX proposes gutting it, the check is miscalibrated.
- **Security content is out of scope for removal in every case**, including when it duplicates.

## Acceptance Criteria
<!-- scope: both -->

- [ ] **R1** CX1 (stale model compensations) is implemented as a judgment check with the evidence contract above; a finding without a quoted line and a named pattern is not emitted.
- [ ] **R2** CX2 (contradictions and duplication) is implemented, distinguishing contradiction from legitimate local reinforcement.
- [ ] **R3** CX3 (encyclopedic drift) is implemented, covering inlined-inferable content and load-bearing rules buried behind reference material, with a navigational rewrite proposed per finding.
- [ ] **R4** CX findings are informational: they do not change pillar scores, the readiness level, or the hard gates, and each finding is marked as such in the report.
- [ ] **R5** No CX finding ever proposes deleting security, approval, consent, forbidden-action, or credential-handling content. Verified by a fixture whose instruction file contains a duplicated security rule: the run must not propose removing either copy.
- [ ] **R6** CX never auto-applies an edit, in any mode; autonomous/Ralph/receipt-driven invocations report only.
- [ ] **R7** Length alone produces no finding. Verified by a long-but-dense fixture that yields zero CX findings.
- [ ] **R8** CX1 contains no model-name matching; detection is by compensation shape.
- [ ] **R9** Evaluation before ship, on a fixture corpus of at least six instruction files spanning: a known-stale compensated file, a contradictory file, an encyclopedic file, a long-but-dense file, a thin shim, and flow-next's own CLAUDE.md. Recorded in `optimization/` with the false-positive count per fixture. Ship bar: zero findings on the long-but-dense and shim fixtures, and human-judged-reasonable proposals on the flow-next fixture.
- [ ] **R10** `./scripts/sync-codex.sh` runs twice idempotently with all validation guards green, and the mirror diff is committed with the canonical change.
- [ ] **R11** Prose-contract tests cover the informational marking, the never-delete constraint, and the no-model-name rule.
- [ ] **R12** Full suite green; docs updated where prime's behavior is described (`docs/` + the flow-next.dev prime page in the same workstream); CHANGELOG staged under `## Unreleased` with no version bump.

## Boundaries
<!-- scope: business -->

**Not in scope:**

- **Auto-editing instruction files.** Proposal-only in v1. An apply path with per-finding consent is a possible follow-up once the false-positive rate is known from real runs.
- **A token counter or size budget.** Prime does not tell users how many tokens their file is worth; that is a metric without a decision attached.
- **Auditing the user's own skills or agent definitions.** CX v1 covers instruction files (CLAUDE.md / AGENTS.md and their nested equivalents) only. Skill-body rightsizing for user repos is a larger surface and a separate decision.
- **flow-next's own skills.** Already done with eval gates: fn-82 (prompt diet, -10.7k always-loaded tokens) and fn-130 (progressive disclosure, 3% to 79% default-path reductions). Re-running a diet pass over our own skills is out of scope and would risk regressing measured work.
- **The two dropped headings** (expressive CLI interfaces, rich source references) - reasons recorded in Architecture; do not re-add without new evidence.
- **Scoring CX into the ladder.** Explicitly deferred, not forgotten.

## Decision Context
<!-- scope: both -->

**Why CX1 leads.** It is the only check here that no other readiness tool performs, and its timeliness is unusual: the Opus 5 launch week produced two independent field reports plus a first-party effort curve all pointing at over-instruction as a live regression source. It is also the check with the clearest generalization beyond one model generation, since the pattern recurs at every frontier step: yesterday's necessary scaffolding becomes today's noise. The other two checks are good hygiene that a careful reviewer would eventually find; CX1 is a claim.

**Why informational, not scored.** Prime's credibility rests on findings being defensible. Scored checks are objective (a command runs or it does not); CX is interpretive. Shipping interpretive findings into a score would put prime's hardest-won property - substance over vibes, verdicts you can act on - behind a judgment that will sometimes be wrong. Informational-first also produces the evidence needed to decide the promotion question honestly.

**Why three checks and not eight.** Four of the original headings either duplicated each other (three of them produce one finding and one fix) or duplicated existing coverage. A check group that fires four overlapping findings on one file trains users to skim. The calibration lesson from Harden's thresholds applies: a signal that fires on a quarter of everything gets declined reflexively and stops being read.

**Why proposal-only, and never on security content.** Consistent with the Harden precedent shipped in 3.4.5: edits to shared repo infrastructure are human-accepted, and a gate or rule that stops firing is worse than one that was never proposed. Deleting a redundant security rule is the highest-cost mistake available in this feature, so it is prohibited outright rather than mitigated.

**Relationship to other specs.** fn-130 (shipped 3.4.3) proved progressive disclosure internally with a zero-loss ratchet; this applies the outward-facing version of that judgment. fn-129 (skill-only invocation architecture, open) touches the same prime surfaces and should be sequenced to avoid conflicting edits. fn-92 (2.13.0) established the substance-over-existence doctrine that CX extends in the opposite direction.
