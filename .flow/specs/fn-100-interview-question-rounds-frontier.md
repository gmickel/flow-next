# Interview question rounds: frontier batching for /flow-next:interview

## Goal & Context

`/flow-next:interview` currently asks exactly one `AskUserQuestion` call per turn, bundling only 2-4 closely related sub-questions, and walks the decision tree depth-first, adapting after every call. On a deep interview (the skill itself says to expect 40+ questions) that means an adaptation pass - a full model re-reasoning over the ~12k-token technical-scope loaded set - between every 2-4 questions, and the user receives unrelated micro-batches drip-fed one at a time.

This spec replaces the question-ordering protocol with frontier rounds:

- Model the interview as a design tree: every decision branches into the decisions that hang off it.
- The frontier is every question whose prerequisites are already settled: askable NOW without guessing at unheard answers.
- Each round asks the whole frontier, split across `AskUserQuestion` calls of up to 4 questions grouped by topic and announced as one round.
- Answers reshape the tree; the agent recomputes the frontier, announces pruned branches, and asks the next round. Done when the frontier is empty.
- Dependency discipline is preserved and made explicit: a question whose answer depends on another question still open in the same round belongs to a later round, never the same one.

The plain-language question contract, confidence tiers, skipped-questions contract, scope passes (business/technical/both), doc-aware behaviors, write-back, and tracker sync are all untouched. This is an ordering/batching change only.

## Quick commands

```bash
# Gate after edits land:
python3 -m pytest plugins/flow-next/tests/test_interview_scope_flag.py
bash plugins/flow-next/scripts/smoke_test.sh
./scripts/sync-codex.sh && git diff --stat plugins/flow-next/codex/ && ./scripts/sync-codex.sh && git diff --quiet plugins/flow-next/codex/ && echo "mirror idempotent"
grep -n "plain-text numbered" plugins/flow-next/codex/skills/flow-next-interview/SKILL.md
```

## Strategy Alignment

Active tracks served by this plan:
- **Spec-driven team patterns** - the interview is the core spec-refinement ceremony; rounds collapse the adaptation passes between question batches (one per round instead of one per 2-4-question call) without losing the dependency discipline or the plain-language contract.
- **Cross-platform parity** - the canonical prose stays Claude-native; the Codex mirror carries the rounds protocol through the existing sync transform.

## Decision Context

Eval-validated on the canonical `optimization/interview/` harness (2026-07-18, fn-84.3 protocol: sonnet question-emission runs on the 4 frozen fixtures, blind fable judges for E4 NFR-coverage / E5 overall quality, host-scored E1-E3 accuracy):

- Accuracy floor (E1-E3): 12/12 on every rep of both arms (baseline = current prose, rounds = mutated prose). No codebase-answerable re-asks, format contract held, I3 DECIDED boundaries never re-opened, no R-ID renumbering.
- Restraint on the thorough spec (I4): both arms perfect; the rounds framing (empty frontier = done) if anything sharpened it (1 question vs baseline 2, with an explicit already-settled ledger).
- Frontier partition correctness (rounds-specific check): 11/11 rounds runs had zero intra-round dependency violations; every dependent question was deferred with an explicit unblocked-by annotation and conditional prunes were announced.
- First-pass rounds wording lost E5 on the thin fixture I1 (judges read queued cosmetic follow-ups as padding: the draft rule said "never hold a frontier question back", licensing marginal questions). One scoped rule fixed it: "a frontier slot is earned" - every genuinely open decision joins the round and NFR probes always qualify (guarding the fn-84 exp-1 trap where an unscoped prune cue dropped thin-spec NFR probes), but pure-cosmetic polish folds into a related question's options or a stated write-back default.
- With that rule (v2, the wording shipped here), the I1 cell at N=3 scored E4 3/3 PASS and E5 3/3 PASS, versus baseline E4 0/2 FAIL / E5 2/2 PASS and rounds-v1 E4 0/2 / E5 0/2. The earned-slot rule pushed substantive probes (change-detection mechanism with scale rationale, repo-size question, Windows/SIGTERM nuance, retry-exhaustion chain) into the freed slots.
- Guard reps of I3/I4 under v2 (bleed check for the earned-slot rule, N=1 each): I4 PASS/PASS with a single question that surfaced a genuine R1-vs-R4 contract gap no other run in the eval found, and with the fold-as-stated-default behavior firing exactly as written. I3 E5 PASS with both DECIDED boundaries intact and content near item-for-item with the passing baseline reps (plus a security probe baseline lacked); its E4 FAIL is documented judge-counting noise on that fixture (judges split all session on crediting append-perf from the append-mode rationale, and on an R-ID-gap probe that no run in any arm ever asked). No bleed detected.
- Efficiency: what the eval establishes is that ADAPTATION CHECKPOINTS (full model re-reasoning passes over the ~12k-token loaded set between question batches) collapse from one per call to one per round - measured 1-3 rounds vs 2-4 sequential baseline calls on the emission fixtures, with question quality held. Wall-clock and turn mechanics in live hosts are platform-dependent (each AskUserQuestion call still blocks for answers; the Codex mirror's plain-text fallback blocks per prompt part) and are NOT claimed from the eval - they get validated in dogfood after ship. The protocol's structural win stands regardless: between the parts of a round the agent does no frontier recomputation.

Rejected alternative: keeping one-call-per-turn and just raising the bundle size. That loses the explicit dependency partition (the frontier rule is what keeps same-round questions independent) and keeps a full adaptation turn between every 4 questions.

## Boundaries / non-goals

- Files touched: `plugins/flow-next/skills/flow-next-interview/SKILL.md` (two blocks, exact text below), `plugins/flow-next/skills/flow-next-interview/references/doc-aware.md` (six "per interview turn" throttle sites, R8), the regenerated Codex mirror, `optimization/interview/{results.tsv,changelog.md}`, and `CHANGELOG.md`. No flowctl changes.
- Other question-asking skills (capture, audit, strategy, prime, setup) keep their own protocols; migrating them is a possible future spec once this one has dogfood mileage.
- questions-shared.md / questions-business.md / questions-technical.md untouched. Accepted, no edit: questions-shared.md line 35 "Continue until complete - multiple rounds expected" reads correctly under the formal rounds term; line 33 "dig deep" holds across rounds.
- Codex mirror chunking: the "up to 4 questions per call" rule inherits a Claude tool-schema cap that the mirror's plain-text numbered-prompt fallback does not strictly need. Accepted as a cosmetic mirror artifact for v1 - no sync-codex.sh changes.
- Coordination: open spec fn-89 task .3 edits a DIFFERENT section of the same SKILL.md (tracker reconcile block). No textual overlap; whichever lands second rebases and re-runs sync-codex.sh before merging.
- No version bump (batched-release rule): stage under `## Unreleased` (the heading does not currently exist - 2.15.0 consumed it; create it).

## Exact SKILL.md edits (R1/R2 source of truth - apply verbatim)

Edit A - in `## Interview Process`, replace the bullet:

```
- Group 2-4 related questions per tool call
```

with:

```
- Ask in rounds: each round carries the whole frontier (see Question Order below), split across AskUserQuestion calls of up to 4 questions each
```

Edit B - replace the entire `### Question Order: Walk the Decision Tree` section (heading through the example flow blockquote, inclusive) with:

```markdown
### Question Order: Rounds over the Decision Tree

Map the interview as a **design tree**: every decision branches into the decisions that hang off it. The **frontier** is every question whose prerequisites are already settled — the questions you can ask NOW without guessing at answers you haven't heard yet. Work the tree in **rounds**: ask the whole frontier, wait for answers, recompute, repeat.

Concrete rules:

1. **Each round asks the entire current frontier.** A question whose answer depends on another question still open in this round belongs to a *later* round, not this one — never ask a question alongside its own prerequisite.
2. **Split the frontier across `AskUserQuestion` calls of up to 4 questions each**, grouped by topic (closest-related together), announced as one round ("Round N — part 1/2"). Never pad a call to reach 4; never hold a genuine frontier question back to a later round just to smooth pacing.
   **A frontier slot is earned.** Every genuinely open decision joins the round — NFR probes (failure modes, concurrency/races, scale, portability, testing) ALWAYS qualify, however thin the spec. Pure-cosmetic polish (message wording, label/flag spelling, visual formatting) does not get its own question: fold it into a related question's options, or carry it as a stated default the user can veto at write-back.
   Standalone checkpoint questions (scope selection, the code-mismatch question, the write-back consent checkpoint, the mark-ready offer) sit outside rounds — never labeled "Round N", never counted against round depth. Doc-aware meta-questions keep their own per-round budget (references/doc-aware.md): a meta-question deferred by that budget is pending for a later round, not dropped — the one sanctioned hold-back.
3. **Recompute the frontier after each round.** Answers reshape the tree — settled decisions unblock their dependents; adapt the next round to what you heard. Don't lock the whole tree before you start: deeper rounds are discovered from answers, not pre-scripted.
4. **Surface abandoned branches.** When an answer prunes a sub-tree, say so explicitly at the next round's opener: "Skipping persistence questions — you said no DB."
5. **Cap branch depth at 4 rounds** down any one branch. Research shows >4 prior turns rarely improves question quality — drop deeper threads, ask about something else. Heuristic; revisit if too restrictive in real use.
6. **Finish the round before recomputing.** If a later part of a round never got asked (tool error, interruption), ask the missed part first — never silently drop frontier questions and move on.

Example flow:

> Round 1 (frontier: persistence?, auth model?, error surface?) — asked together in one call.
> A: "No persistence — ephemeral is fine. API-key auth. Errors: existing JSON convention."
> [agent prunes the {DB choice, schema design, migration plan} sub-tree]
> Round 2 opener: "Skipping DB questions — you said ephemeral." (frontier now: reload survival?, key-tier limits? — the questions those answers unblocked)
```

## Exact SKILL.md edit C (R9 source of truth - apply verbatim)

Edit C - in the `### Plain-language question contract` section, append one bullet to the list that currently ends with "**Every option description states its consequence in plain words**: "Choose this if…" / "This means…".":

```markdown
- **Gloss referenced acceptance criteria.** When a question cites a spec R-ID, attach a short plain-words gist at first mention — "R3 (the audit line's required fields)" — never a bare "R3" the interviewee must open the spec to decode. Gist, not quote: pasting full criterion text bloats the question body.
```

Like rule 6, this is an additive post-eval bullet (legibility, not question-selection prose); it extends the contract's existing no-unexplained-shorthand rule to R-IDs. (Revised from an earlier full-quote form on maintainer feedback: full criterion text risks overlong AskUserQuestion bodies; a gist carries the meaning at a fraction of the length.)

## Exact SKILL.md edit D (R12 source of truth - apply verbatim)

Edit D - insert as a new H4 subsection at the END of the `### Investigate Codebase Before Asking` section (after the "If you find yourself answering a "should" question via grep, that's the bug" paragraph, before `#### Code-versus-assertion contradiction`):

```markdown
#### Async fact-scouts (optional, rounds mode)

While the user answers the current round, you MAY dispatch ONE read-only fact-scout subagent (`Task` with `subagent_type: Explore`) to resolve codebase lookups that gate NEXT-round questions — investigation latency hides inside user-answer time instead of stalling the interview between rounds.

- **The brief is the contract.** Number each lookup: what to look up, where to start, and which question it gates or could eliminate. Facts only, never judgments. Deferring a question on a pending fact REQUIRES the brief to already name that lookup — no brief, no deferral: investigate inline as usual.
- **Scout tier: judgment-capable, never a fastest-tier scanner** — mid-tier or stronger (sonnet on Claude Code), escalating toward the session model's tier when it is stronger or a digest comes back thin. Eval-validated: the fastest tier missed a load-bearing storage-architecture fact that the mid tier found on the identical brief.
- **Digest discipline.** The scout returns facts with file:line evidence; absence findings count. Treat the digest as investigation results, state residual uncertainty honestly, and spot-verify a load-bearing fact yourself before building a `[high]` recommendation on it.
- **Never block, never degrade silently.** Scout unavailable or digest missing → investigate inline exactly as today, and say so. Doc-aware budgets and their sanctioned hold-back are unchanged.
```

## Acceptance Criteria

- **R1:** SKILL.md `## Interview Process` bullet (line ~266, "Group 2-4 related questions per tool call") replaced per Edit A, verbatim.
- **R2:** SKILL.md `### Question Order: Walk the Decision Tree` section (lines ~335-352, heading through example-flow blockquote inclusive) replaced per Edit B, verbatim (heading becomes "Rounds over the Decision Tree"). Rule 6 and rule 2's final paragraph (checkpoint exclusion + doc-aware budget reconciliation) are additive post-eval operational clauses, not part of the evaluated question-selection prose; the rest of rules 1-5 + the example are the evaluated artifact and must not be reworded. No other SKILL.md content changes.
- **R3:** All other SKILL.md sections byte-identical: the CRITICAL AskUserQuestion block (minus Edit A's bullet), "Expect 40+ questions" line, plain-language question contract (minus Edit C's appended bullet), Skipped Questions contract, scope selection, code-mismatch question, scope passes, doc-aware GATE paragraph, write-back, tracker-sync, mark-ready, Completion.
- **R4:** Codex mirror regenerated via `scripts/sync-codex.sh` (full-regen; commit the diff). Post-regen audit per memory lessons: no surviving `AskUserQuestion` literal outside sanctioned transforms; every injected plain-text-ask block sits at a genuine ask site (never mid-sentence, never inside negation/example prose - `grep -n "plain-text numbered" plugins/flow-next/codex/skills/flow-next-interview/SKILL.md` and eyeball context); second `sync-codex.sh` run is byte-identical (idempotency).
- **R5:** `optimization/interview/results.tsv` gains row `experiment=3` and `optimization/interview/changelog.md` an `## Experiment 3` entry for the rounds mutation, using the numeric mapping in the Appendix (status `shipped`, description references fn-100). The fn-84 rows/entries stay untouched (append-only).
- **R6:** `CHANGELOG.md` gains a newly created `## Unreleased` heading (directly under the intro, before `## [flow-next 2.15.0]`) with a `### Changed` entry describing the interview rounds protocol, matching the repo's bold-lead-in bullet format. No version bump.
- **R7:** Gates green: `python3 -m pytest plugins/flow-next/tests/test_interview_scope_flag.py` (plus the full unit suite per repo convention) and `bash plugins/flow-next/scripts/smoke_test.sh`; no flowctl behavior changes expected.
- **R9:** SKILL.md plain-language question contract gains the Edit C bullet, verbatim: questions citing a spec R-ID attach a short plain-words gist at first mention ("R3 (the audit line's required fields)"), never a bare R-ID pointer that forces the interviewee to open the spec, and never the full criterion text (body bloat).
- **R10:** The two repo docs that promise per-TURN doc-aware throttling are updated to per-round wording consistent with R8: `plugins/flow-next/docs/teams.md` (~line 137) and `plugins/flow-next/docs/strategy.md` (~line 49). Minimal word-level edits; nothing else in those files changes.
- **R11:** The flow-next.dev docs site (`~/work/flow-next.dev`, separate repo - NOT part of this repo's PR, tracked as its own task in this workstream per the repo guide's same-workstream rule) is updated: the interview skill page describes the rounds protocol and `pnpm build` passes in that repo; committed separately there. The docs-site CHANGELOG entry is explicitly DEFERRED to the batched release (that site's changelog couples entries to version bumps - it has no unreleased-staging convention); the release-time note is recorded in the task completion summary so the release walk picks it up.
- **R12:** SKILL.md gains the Edit D subsection verbatim (async fact-scouts in rounds mode); Codex mirror regenerated (sync-codex rewrites `Task`/`Explore` per its existing transforms); one sentence added to the flow-next.dev interview page's Question rounds section describing background fact-finding during rounds (flow-next.dev commit, separate repo, build green); CHANGELOG Unreleased entry extended with one bullet; `optimization/interview/changelog.md` Experiment 3 entry gains a short "Async fact-scout addendum" paragraph recording the scout eval (data in the Appendix); no results.tsv row (feature validation, arm not a prose mutation of the emission harness).
- **R8:** `references/doc-aware.md` "per interview turn" redefined as "per round" at all six throttle sites (lines ~55, 63, 76, 78, 131, 171): one glossary question per round; the sharpening body text names rounds; the glossary re-read note reads per-round; the "<=6 turns" heuristic becomes "<=6 rounds"; one decision write per round; one strategy-conflict question per round with the combined doc-aware budget staying "3 max" per round. Intent preserved: meta-questions never crowd a round; the budget does NOT multiply by calls within a round.

## Early proof point

Task fn-100-interview-question-rounds-frontier.1 validates the core change (both verbatim SKILL.md edits + the doc-aware turn-to-round redefinition + a clean, idempotent mirror regen with the R2-injection audit passing). If the mirror transform mangles the rounds prose, revisit the wording of rule 2's ask phrasing before continuing.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Edit A bullet replacement | fn-100-interview-question-rounds-frontier.1 | - |
| R2 | Edit B section replacement (evaluated wording + rule 6) | fn-100-interview-question-rounds-frontier.1 | - |
| R3 | All other SKILL.md sections byte-identical | fn-100-interview-question-rounds-frontier.1 | - |
| R4 | Mirror regen + R2-injection audit + idempotency | fn-100-interview-question-rounds-frontier.1 | - |
| R5 | Eval-ledger row + changelog entry | fn-100-interview-question-rounds-frontier.2 | - |
| R6 | CHANGELOG Unreleased entry (create heading) | fn-100-interview-question-rounds-frontier.2 | - |
| R7 | Gates green | fn-100-interview-question-rounds-frontier.2 | - |
| R8 | doc-aware.md per-turn throttles redefined per-round | fn-100-interview-question-rounds-frontier.1 | - |
| R9 | Edit C: R-IDs quoted in full in question bodies | fn-100-interview-question-rounds-frontier.1 | - |
| R10 | teams.md + strategy.md per-turn lines updated to per-round | fn-100-interview-question-rounds-frontier.2 | - |
| R11 | flow-next.dev interview page + build green (changelog deferred to release) | fn-100-interview-question-rounds-frontier.3 | - |
| R12 | Async fact-scout mode (Edit D + mirror + docs + ledger addendum) | fn-100-interview-question-rounds-frontier.4 | - |

## Edge Cases & Constraints

- Frontier larger than 4: split across consecutive calls labeled as parts of one round; each call still blocks individually, but no model adaptation pass runs between parts.
- Round-depth counting: depth = length of the unblocked-by chain (rounds down one branch). Sibling questions unblocked by the same answer land in the same round and share one depth level.
- One-off checkpoint questions (scope selection, code-mismatch, write-back consent, mark-ready) sit OUTSIDE the rounds protocol: standalone single questions, never labeled "Round N", never counted against round depth or the doc-aware budget mechanics beyond their own sections' rules.
- Codex mirror: sync-codex.sh rewrites AskUserQuestion invocations to the plain-text numbered-prompt instruction; the rounds wording must survive that transform reading naturally (numbered questions per round is a natural fit). Keep any live-ask phrasing on one physical line (R2-injection hazard).
- The 4-round depth cap replaces the old 4-turn depth cap with equivalent intent; the example flow must show the prune announcement at a round opener.

## Testing

- Diff-inspection against R1/R2 verbatim blocks.
- `scripts/sync-codex.sh` run clean; mirror diff shows only the interview skill change.
- Full unit + smoke suite green (dual-copy invariant untouched, but run anyway per repo gate).

## Appendix: eval data for the R5 ledger task (source of truth for results.tsv row + changelog entry)

Method: fn-84.3 protocol on `optimization/interview/` - sonnet question-emission runs on the 4 frozen fixtures (arm-neutral instruction: emit each AskUserQuestion call you would make, in order, dependencies annotated), blind fable judges per run for E4/E5, host-scored E1-E3, plus a rounds-specific host check (frontier partition: no question grouped in a round with its own open prerequisite). Baseline arm = current live prose; rounds arm = live prose with the Question Order mutation. Date 2026-07-18.

First pass, N=2 per arm per fixture (E4/E5 verdicts per rep):

| fixture | baseline E4 | baseline E5 | rounds-v1 E4 | rounds-v1 E5 |
|---|---|---|---|---|
| I1 thin | FAIL, FAIL | PASS, PASS | FAIL, FAIL | FAIL, FAIL |
| I2 foreign | FAIL, PASS | PASS, PASS | PASS, PASS | PASS, PASS |
| I3 override | PASS, PASS | PASS, PASS | PASS, FAIL | PASS, PASS |
| I4 restraint | PASS, PASS | PASS, PASS | PASS, PASS | PASS, PASS |

Accuracy E1-E3: 12/12 on every rep of both arms. Partition: correct on all rounds runs. I4 restraint: rounds asked 1 question vs baseline 2, both with explicit settled ledgers. I1 rounds-v1 E5 failure mechanism: draft rule "never hold a frontier question back" licensed cosmetic follow-up questions into round 2; judges scored them padding.

Fix: "a frontier slot is earned" rule (v2) - NFR probes always qualify, cosmetics fold into options or a stated write-back default. I1 re-run at N=3 under v2: E4 PASS 3/3 (baseline was 0/2), E5 PASS 3/3, partition correct, freed slots went to substantive probes (hybrid change detection with scale rationale, repo-size question, Windows/SIGTERM nuance, retry-exhaustion chain). Guard reps I3/I4 under v2 (N=1): I4 PASS/PASS (1 question; found a genuine R1-vs-R4 contract gap in the fixture no other run surfaced); I3 E5 PASS with boundaries intact, E4 FAIL attributable to documented judge-counting noise on that fixture (append-perf crediting + an R-ID-gap probe no run in any arm ever asked), content matching the passing baseline reps.

Async fact-scout eval (2026-07-18, for R12; same fixtures, investigation UNFROZEN against the live repo, host-scored vs objective answer keys - fable judges deliberately not used this round since the discriminating dimension was factual grounding, which the keys settle objectively):

- Arms: inline (interviewer investigates itself; 5 runs, 96-136k tok each) vs scout-assisted two-phase (phase-1 brief + pre-fact round, background fact-scout, phase-2 rounds from digest).
- As first tested with fastest-tier (haiku) scouts: FAILED the pre-registered bar. Both I1 haiku scouts missed the load-bearing fact (live task status resides in the git-common-dir flow-state StateStore, not .flow/tasks - definition status is a legacy mirror), so both phase-2 cells never asked the highest-stakes data-source question the inline runs led with at [high]; one phase-1 run emitted no brief at all (its cell degraded safely - honest "investigation owed" flags - but hollow).
- Tier probe: a sonnet scout on the identical brief found the storage split completely (RUNTIME_FIELDS merge-shadow, legacy-mirror fallback) at similar cost (62k vs 44-49k tok). Re-running phase 2 for both I1 cells with the sonnet digest recovered the data-source question, led at [high] with correct premise, in both - plus correct pruning (race question dropped via the atomicity fact; mechanism folded to an interval question). Granular briefs also mattered: the 11-item I3 brief drove the scout arm's best cell (rivaling inline); coarse briefs underperformed.
- Cost honesty: the scout arm saves NO total tokens (150-190k vs 96-136k inline); its wins are latency-hiding (the scout runs while the user answers - by construction) and halving the interviewer's own context growth. Restraint held (the thorough fixture's phase 2 asked zero further questions).
- Shipped guardrails follow directly: sonnet-minimum scout tier with escalation, brief-is-the-contract with granular gated lookups, no-brief-no-deferral, digest spot-verification before [high] recommendations, silent-degradation forbidden.

Efficiency: adaptation checkpoints collapse from one per call to one per round (emission: 1-3 rounds vs 2-4 sequential calls). That checkpoint reduction is the measured, structural win; live-host turn/latency/token effects are platform-dependent and get validated in dogfood after ship, not claimed from the eval. Verdict: accuracy floor holds, quality >= baseline with the v2 wording, adaptation checkpoints reduced; shipped via this spec. E5 remains an advisory-noise eval at low N per the fn-84 ledger; the accuracy floor plus E4 plus the partition check are the hard guards.

Numeric mapping for the results.tsv row (columns: experiment / accuracy_score / accuracy_max / quality_score / quality_max / tokens_before / tokens_after / runs / model / status / description). The row records the SHIPPED v2 wording ONLY - v2 observations across all four fixtures (v1 rounds and baseline reps stay in the changelog entry prose as comparison context, never in the row):

- experiment=3; accuracy_score=12; accuracy_max=12 (E1-E3 held on every v2 rep: I1 x3, I2 x1, I3 x1, I4 x1).
- quality_score=7; quality_max=8 - per-fixture from v2 observations only: I1 2/2 (N=3, E4+E5 all PASS), I2 2/2 (v2 rep: E4 PASS 5/6 gaps + E5 PASS), I3 1/2 (guard rep: E5 PASS, E4 FAIL on judge counting - noted as documented noise in the changelog entry), I4 2/2 (guard rep).
- tokens_before / tokens_after: measured by task .1 IMMEDIATELY before and after applying Edits A/B/C, same command both times, on the technical-scope loaded set: `cat plugins/flow-next/skills/flow-next-interview/SKILL.md plugins/flow-next/skills/flow-next-interview/questions-shared.md plugins/flow-next/skills/flow-next-interview/questions-technical.md | wc -c` divided by 4 (the repo's chars/4 tok-equiv convention, as in fn-99's CHANGELOG). Record both numbers; the delta isolates fn-100's edits. The fn-84 figure 12314 is historical context only (different file state) - name it in the changelog entry, never in the row's columns.
- runs=6 (v2 emissions only: 3 + 1 + 1 + 1); model=sonnet; status=shipped; description: one line - frontier-rounds Question Order mutation (v2 earned-slot wording), blind fable E4/E5 judges, v2-only observations, shipped via fn-100.
