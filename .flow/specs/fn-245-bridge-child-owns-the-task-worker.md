# Bridge child owns the task: worker bridge path, fan-out license restored, July codex caveats retired

## Conversation Evidence

Source: this session, following issue #431 / PR #436 (merged 2026-09-14), the colleague's PR #437 (not adopted), the fan-out probe in `~/work/.e-eval-ws/fanout-probe-20260914`, and the upstream repro of openai/codex#33267 on codex-cli 0.153.4.

1. [user] "when i say fan out here, i'm talking about the owning subagent fanning out for parallezation on its own as prompted in our worker skill, not plan or rolling worker deterministic fan outs"
2. [user] "i KNOW that it works in host, ie. claude code with a claude code worker that then fans out"
3. [user] "i am not looking to use his PR, i'm looking for the best way to fix this if this is indeed a problem"
4. [user] "our benches/evals showed that the no-plan works and results in higher quality IF there is a clear owner end to end, and this is why the bridge agent should be doing the fan out?"
5. [user] "we are agreed that we need to make sure it is the bridge child that fans out and we know how to achieve this, and this matches your 3 fixes?"
6. [user] "perhaps an addition to the strategy document? so we don't 'widen' this again by accident should be part of this?"
7. [user] "we don't want to limit all other harnesses cos of codex so this would be great"
8. [user] "is the bug actually fixed, cos that would mean we can safely do all of this with more confidence"
9. [paraphrase] Findings established in session: the Claude worker never consults the implementer tier (probe cell A: routing block pinning gpt-6-astra, worker implemented on the session model, zero bridge calls, no fallback notice); the #436 long-task brief says "never spawn another agent or bridge", a widening of the original "never spawns a bridge of its own" that appears in no requirement; the widening came from the July flat-child caveats in the usage guide and the codex reach page, which trace to openai/codex#33267; that bug does not reproduce on codex-cli 0.153.4 with gpt-6-astra (issue's own minimal repro 3/3 clean, 17 exec-originated spawning runs and 23 spawning child threads with zero decode errors); Codex-host implementer children do fan out natively; open spec fn-98 still carries the undone R2 (retire the July "subagent model steering is unreliable" caveats).

Strategic context (STRATEGY.md): approach "the artifact is the contract"; design principle "remember the bitter lesson"; tracks Ralph autonomous mode, Cross-platform parity, Self-improving through normal work.

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 55% [paraphrase], 30% [user], 15% [inferred] -->

The direct route rests on one owner seeing the whole task end to end and deciding its own delegation (evidence 4). In host that holds: the Claude worker is the owner and fans out under the judicious-subagent license (evidence 2). When a project's routing block pins the implementer tier to a model reached only by CLI bridge, the owner should be the bridged child, and today it is not. Two defects break it. First, nothing in the worker consults the implementer tier, so the tier is silently ignored and the session model implements (evidence 9). Second, the long-task brief shipped in #436 forbids the child from spawning any agent, a clause no requirement asked for; the worker generalized the July "keep the child flat" caveats into a never-list, and three checks let it through (evidence 9).

The fix keeps ownership with the implementer wherever it runs (evidence 1, 5): the worker gains a thin bridged path that hands the task to the child and reviews its commit range; the brief clause reverts to banning only a nested bridge and the license passes through to the child; the July codex caveats, including fn-98's undone R2, become dated watches with the measured evidence, because the upstream bug does not reproduce on the current CLI (evidence 8). A strategy principle and a standing criterion make the next accidental narrowing a review finding rather than a memory (evidence 6). No other harness is limited because of Codex (evidence 7).

## Architecture & Data Models
<!-- scope: technical -->

Prose only. No hook, guard, flowctl subcommand, or config key. Surfaces:

- The worker agent definition gains a bridged-implementer path gated on the implementer tier resolving to a CLI-reached model per the harness reach page. Shape: keep Phase 0 and 1 and the persisted base commit; skip Phase 1.5 and any worker-side scouting; compose a pointer prompt (task id, spec and task paths, the spec's resolved-research section when present, the project instruction file) followed by the usage guide's long-task brief verbatim plus the judicious-subagent license verbatim; run the bridge as one foreground call from the asserted repo root at the commit-permitting sandbox; on return commit any dirty remainder, review base..HEAD against the acceptance criteria and Phase 2's rules, run the focused gates, continue at Phase 3. The worker's own TIMEBOX is never copied into the brief. No worker-side parallel bridge calls and no per-child worktree integration: parallelization is the child's.
- The work skill's step 3c gains one paragraph stating the worker bridges and the conductor never does; the Codex mirror generator carries the same paragraph (its 3c has dropped the implementer-tier paragraph since the tiers release).
- The long-task brief in the usage guide: the never clause reads "never spawn another bridge"; the brief carries the license sentence so the child holds it.
- The two flat-child caveats (usage guide self-bridge line, codex reach page shell-out row) and fn-98's R2 surfaces (codex reach page in-host row, orchestration and platforms notes, the setup model-routing snippet, the site's model-routing caveat) become dated watch lines: what was measured, on which codex version, with the upstream issue named.
- STRATEGY.md design principles gain "The owner holds the license"; `.flow/criteria.md` gains a G-ID that completion review judges on every spec.
- The stage-line convention records the tier resolution on the bridged path and the child's delegation count from its digest, so a reviewer sees who implemented and whether the child delegated without reading codex rollouts.
- One bug memory entry records the widening and its prevention rule.

## API Contracts
<!-- scope: technical -->

Pointer-prompt contract: identities and rails only (task id, paths, instruction file, brief, license); no restated spec content. Brief never-list, exactly: never push; never rebase, amend, or rewrite history; never change scope; never issue a review verdict; never spawn another bridge. Return condition: return only when the scope is done or blocked. Stage line on the bridged path: `stage: implement - ran (model: <what ran>; delegated: <n>)` or `skipped(reach: <model> unreachable, session model used)`.

## Edge Cases & Constraints
<!-- scope: technical -->

- Tier resolves to the session model or an in-host subagent model: the bridged path is inert; the standard phases run unchanged. [inferred]
- Named model unreachable from this harness: fall back to the session model and say so once, per the reach-page rule; the stage line records it. [inferred]
- Sandbox denies commits: the child reports it in its digest; the worker commits the remainder before range review. [paraphrase]
- Under PARALLEL_WAVE or host-deferred review the path changes only who wrote the code; handover and deferral contracts stand. [inferred]
- Upstream openai/codex#33267 remains open for codex 0.144 to 0.145 with the gpt-5.6 family and one Desktop provider-migration case; the watch line names that scope so a reader on an older build knows the risk. [paraphrase]
- The frozen guidance-eval arm under `agent_docs/guidance-eval/arms/` is a baseline snapshot and is not edited. [paraphrase]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The worker agent definition carries a bridged-implementer path with the shape in Architecture: gated on the tier resolution, keeps Phase 0 and 1 and the base, skips Phase 1.5 and worker-side scouting, composes pointer prompt plus brief plus license, runs one foreground bridge call, commits any dirty remainder, reviews base..HEAD, runs focused gates, continues at Phase 3; TIMEBOX never copied. Errors: unreachable model falls back to the session model with one notice; sandbox-denied commit handled by the dirty-tree commit; no other error surface. [paraphrase]
- **R2:** The work skill's step 3c states the worker bridges and the conductor never does, and the Codex mirror's 3c carries both the implementer-tier paragraph and this one; the mirror regenerates idempotently. Errors: none beyond the mirror parity check. [paraphrase]
- **R3:** The long-task brief's never clause reads "never spawn another bridge" and the brief carries the judicious-subagent license verbatim, so a bridged child holds the same delegation license as the in-host worker; the no-plan route's license text names the owner as its holder wherever the owner runs. Errors: none. [user]
- **R4:** The two flat-child caveats are rewritten as dated watch lines naming openai/codex#33267, the measured result (minimal repro clean on codex-cli 0.153.4 with gpt-6-astra; zero decode errors across the September spawning runs), and the older-build scope where the bug is reported. Errors: none. [paraphrase]
- **R5:** fn-98's R2 is delivered here: every surface still saying Codex subagent model steering is unreliable (codex reach page in-host row, orchestration and platforms notes, setup model-routing snippet, site model-routing caveat) states fn-98's measured facts instead (steering works on both paths since 0.146.0; a role's sandbox_mode is not enforced; the two dispatch gotchas; the model-selection precedence). fn-98 is closed with a pointer to this spec; its R5 to R9 remain out of scope and are noted as such in the close summary. Errors: none. [paraphrase]
- **R6:** The worker's done summary on the bridged path carries the stage line from API Contracts with the model that ran and the child's delegation count from its digest; the standard path is unchanged. Errors: a digest without a delegation count records `delegated: unknown`. [inferred]
- **R7:** STRATEGY.md design principles gain "The owner holds the license": whoever implements owns delegation; wrappers, scouts, and conductors never fan out on the implementer's behalf; safety rules bound push, history rewrite, scope, verdict, and nested bridges, never the owner's own delegation; anchored to #436 and the September no-plan owner screens. Errors: none. [user]
- **R8:** `.flow/criteria.md` gains the next G-ID: a change to any implementer brief, worker dispatch prose, or subagent license keeps the owner's delegation intact and names the owner explicitly; a never-list is diffed clause by clause against the spec. Errors: none. [user]
- **R9:** A bug memory entry records the #436 widening: symptom, the three checks that missed it, root cause (July caveat promoted to policy), prevention rule. Errors: none. [inferred]
- **R10:** CHANGELOG Unreleased entry names the worker path, the license restoration, the retired caveats, and fn-98's fold, referencing #431, #436, and #437's diagnosis with credit. The site's work page, model-routing guide, cookbook entry, and landing card are updated in the downstream release walk. Errors: none. [inferred]
- **R11:** No reach page other than codex changes; Cursor, Droid, Grok Build, and Claude Code carry no new restriction. No hook, flowctl code, or config key is added. Errors: none. [user]

## Boundaries
<!-- scope: business -->

- No worker-side parallel bridge calls, per-child worktrees, or branch integration in the worker; delegation belongs to the child. [user]
- The never clauses other than the bridge one are unchanged: never push, never rebase or rewrite history, never decide scope, never issue a verdict. [paraphrase]
- fn-98's R5 to R9 (the Codex read-only guarantee) stay out of scope. [paraphrase]
- No new eval ships in this spec; the owner-serial versus owner-delegating study is a follow-up under agent-evals. [paraphrase]
- Closing PR #437 and replying on #431 are external communications that wait for the maintainer's go. [inferred]
- The frozen guidance-eval baseline arm is not edited. [paraphrase]

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
<!-- scope: business -->

The direct route's premise is a single owner with the whole task and its own delegation judgment; the September screens were built on it and the no-plan owner protocol says the owner may delegate. A bridged child that cannot delegate is not an owner, and a wrapper that fans out around it is delegation by someone with no stake in the result. The #436 widening shows narrowing happens in ordinary careful work, so the guard belongs in strategy and standing criteria, not in memory. [paraphrase]

### Implementation Tradeoffs
<!-- scope: technical -->

PR #437's diagnosis is adopted; its shape is not: it moves fan-out to the Claude worker as parallel bridge calls with per-child worktrees, inherits the agent-spawn ban, and adds integration machinery to an always-loaded prompt. Folding fn-98's R2 in rather than depending on it avoids two mirror regenerations and two site walks for one class of stale caveat. The caveats become watches rather than deletions because the upstream issue is still open for older builds. [paraphrase]

## Parked unknowns

- Whether a bridged child fans out on a real-sized task, and whether that improves quality over a serial owner: unresolved by the probe (tiny task, serial in every draw). Resolves through the follow-up eval, not through this spec.
