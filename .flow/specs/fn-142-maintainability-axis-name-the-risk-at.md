# fn-142 Maintainability axis: name the risk at plan review, scope the claim honestly

**Depends on fn-159 (convergence-aware review terminals).** This spec adds a NEW class of finding to plan review, which is the exact stage that capped three times in one session (2026-08-02) on residue findings. fn-159 repairs how plan-review findings terminate; shipping this first would add fuel to the loop fn-159 exists to fix. The ordering is deliberate, not incidental - the non-blocking contract in R6 is prose asking a reviewer to restrain itself, and it should land on top of a terminal that can already tell convergence from churn.


## Goal & Context
<!-- scope: business -->

The pipeline proves bounded correctness. No stage asks whether a change left the codebase as changeable as it found it, and test suites structurally cannot see that. [SlopCodeBench](https://arxiv.org/html/2603.24755v1) (Orlanski et al., Mar 2026) measured the gap: across 11 models and 93 checkpoints of an agent extending **its own** prior code, no agent solved a single problem end-to-end, best strict pass 17.2% collapsing to 0.5% by the final checkpoint, structural erosion rising in 80% of trajectories and verbosity in 89.8%, and agent code sitting 2.2x more verbose than 48 maintained human repositories with the gap widening every iteration while the human repositories stay flat.

The same study rules out the obvious fix. Quality-aware prompts (anti-slop, plan-first) cut *initial* verbosity 33-35% and changed the per-checkpoint decay slope not at all, improved no pass-rate subtype (paired Wilcoxon, all p > 0.05), and cost up to 48% more. So "instruct the implementer better" is not the answer.

There is exactly one place in the pipeline where a model reasoning about structure is both legitimate and cheap: **plan review, before code exists.** Reasoning about a design is a different task from grading a diff, and every structural decision skipped there gets made implicitly during code review, at the most expensive possible moment to change your mind. That is move one.

Move two is honesty. Until measurement lands (fn-143), "Agents generate. Flow-Next proves." needs its scope attached: it proves the change does what was asked. It does not prove the codebase stayed changeable. Saying so is more credible than the unbounded version, and it is true today.

Both moves are prose. No code, no schema, no metric.

## Architecture & Data Models
<!-- scope: technical -->

**Plan review gains a required Maintainability section.** Three named questions, each demanding a concrete answer or an explicit "none identified":

1. **Change amplification** - what plausible future requirement makes this edit happen in more than one place?
2. **Dependency direction** - does the plan preserve the intended direction, or introduce a back-edge?
3. **Complexity concentration** - does the plan add branching to an already-hot function rather than distributing it?

**Where the output lands.** Two places, neither of which is a new canonical spec section:

- The **plan-review verdict artifact** on disk carries the structured block (it is already the reasoning record for that stage).
- A short pointer lands in the spec's existing `## Decision Context`, so a reader at merge sees the named risk without opening the verdict.

Deliberately *not* a new canonical section: adding one means touching `SPEC.md`, capture, interview and plan consumers, plus a migration for in-flight specs. The value here is the question being asked, not a new slot to file it in.

**Copy surfaces for move two:** `plugins/flow-next/skills/flow-next-plan-review/`, the repo README, `plugins/flow-next/docs/`, flow-next.dev `strategy/verification-spine` and `proof/faq`, and the vault Messaging Library. One sentence, identical everywhere.

## API Contracts
<!-- scope: technical -->

Plan-review verdict gains an advisory `maintainability` block:

```
maintainability:
  change_amplification: <concrete future edit that lands in >1 place> | null
  dependency_direction: ok | back-edge | n/a
  complexity_concentration: <named function/module> | null
  risks: [<one line each, concrete>]
```

**Verdict contract, and it is the load-bearing part.** A maintainability finding MAY contribute to `NEEDS_WORK` only when the reviewer names a concrete future edit that lands in more than one place, or a named back-edge, or a named function absorbing the new branching. A generic "this could be cleaner" MUST NOT produce `NEEDS_WORK` and MUST NOT block SHIP. An unfalsifiable blocker degrades into ceremony, and the round would be consumed for nothing.

**Claim contract for move two** (verbatim across surfaces, so the surfaces cannot drift): the pipeline proves the change does what was asked and records what it did; it does not prove the codebase stays maintainable.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Token cost.** The plan-review reached-path ratchet will flag the added prose. Maintainer decision (Gordon, 27 Jul 2026): prose that buys real quality earns its tokens - do not strip value elsewhere purely to pay the ratchet. Keep the section tight enough to be read, not tight enough to be useless.
- **Must not become a lint or a score.** No numbers, no thresholds, no pass/fail on structure. Deterministic measurement is fn-143's job and is advisory even there.
- **Must not overclaim.** Nothing in the copy may assert that the pipeline prevents maintainability decay. The measured finding is that prompts do not change the slope; this spec buys the risk being *named early*, nothing more.
- **Multi-harness.** The section must work on RepoPrompt, Codex, Copilot and Cursor review backends - no host-specific formatting, no Claude-only affordances.
- **Backward compatibility.** In-flight specs with no `maintainability` block in an older verdict remain valid; absence reads as "not asked", never as "no risk".
- **No canonical-section migration.** `SPEC.md` and the capture/interview/plan consumers stay untouched.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The plan-review skill carries a required Maintainability section with the three named questions, each requiring a concrete answer or an explicit "none identified".
- **R2:** Reviewer output records concrete risks; a generic "could be cleaner" is explicitly documented as out of scope for this section.
- **R3:** A maintainability finding alone cannot produce `NEEDS_WORK` unless it names a concrete future edit landing in more than one place, a named back-edge, or a named function absorbing new branching.
- **R4:** Named risks appear in the plan-review verdict artifact on disk AND as a pointer in the spec's `## Decision Context`.
- **R5:** No new canonical spec section; `SPEC.md`, capture, interview and plan templates are unchanged (verified by diff).
- **R6:** flow-next.dev `strategy/verification-spine` states what the spine does *not* prove, using the claim contract sentence verbatim.
- **R7:** The same sentence appears in the repo README and `plugins/flow-next/docs/`, byte-identical to R6 (verified by grep).
- **R8:** A FAQ entry cross-links the limit, and the existing "just tell it to write clean code" entry points at it.
- **R9:** No shipped copy claims the pipeline prevents, stops, or fixes maintainability decay (verified by grep for the claim verbs).
- **R10:** A plan review run on a real spec produces the section and demonstrates R3's discipline (advisory when generic, contributing when concrete) - evidence captured from an actual run, not asserted.
- **R11:** Downstream chain walked per project convention: repo docs, flow-next.dev (build green), AI x SDLC guide where it touches, vault Messaging Library + Release Timeline beat.

## Boundaries
<!-- scope: business -->

- **No metric computation, no evidence-JSON change, no per-module store.** That is fn-143 and it can ship independently.
- **No canary routing / weak-model extension test.** Parked as fn-144, deliberately deferred as too complex for users right now.
- **No public readiness-trigger page and no benchmark commitment.** Considered and declined (Gordon, 27 Jul 2026) - we are not publishing a threshold or maintaining a leaderboard.
- **No merge gate, no dashboard, no quality score.** Nothing here produces a number a manager can set a target against.
- **No new vocabulary.** GLOSSARY is untouched; "maintainability" and "change amplification" are borrowed industry terms, not coinages.

## Decision Context
<!-- scope: both -->

**Why plan review rather than implementation review or the implementer prompt.** Measured: prompt-side quality pressure moves the intercept, not the slope, and costs more. Structural quality is decided at design time, so the only intervention with leverage is one that happens before code exists. This is also the one task where a model is on solid ground - reasoning forward about a design, rather than grading a diff, which the paper's own logic says a model cannot do reliably (a model that could spot bad structure would have written good structure).

**Why record rather than gate.** Neither model judgement nor static metrics have an established link to "this codebase is easy to change". A gate we cannot falsify becomes ceremony that consumes review rounds, and the review-round economics are already tight. Recording puts the risk in front of the human at merge, which is where the judgement legitimately sits.

**Why ship the honest sentence now instead of waiting for fn-143.** The limit is true today, and stating a limit we are actively closing reads as confidence, not weakness. When fn-143 lands, the sentence narrows from "does not prove" to "records the delta" - honest sequencing, not churn.

**Rejected: a new `## Maintainability` canonical section.** Cost is a template migration across four consumers plus in-flight specs, and the payoff is a filing slot. The question being asked is what has value; `Decision Context` already exists for exactly this kind of reasoning record.

**Rejected: making the section optional.** An optional structural question is not asked, which is the current state and the reason this spec exists.

**Source:** [[Agentic SDLC - SlopCodeBench (Orlanski et al., Mar 2026)]] and [[Agentic SDLC - Why Software Factories Fail (Horthy, Jul 2026)]] in the vault; paper at arXiv 2603.24755v1; Horthy's series at `humanlayer/advanced-context-engineering-for-coding-agents/wsff.md`.
