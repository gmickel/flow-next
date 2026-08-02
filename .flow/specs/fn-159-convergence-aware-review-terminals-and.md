# fn-159 Convergence-aware review terminals and per-surface blocking calibration

## Goal & Context
<!-- scope: business -->

The deterministic review cap (fn-90/fn-131) counts dispatches, and a dispatch counter cannot distinguish a genuinely stuck review loop from one converging in severity while each fix surfaces one more small finding. Field evidence, 2026-08-02 session (flow-next repo): three plan reviews hit the cap at 4 with only trivial residue left — fn-155 (findings 8→7→3→3, then human reset → SHIP on the next round, having burned 4 rounds at an identical head SHA), fn-153 (severity P0→P1→P2, reset → SHIP), fn-156 (4 findings → 1 stale-prose finding, capped). Meanwhile flow-swarm shows the opposite tail: fn-147 hit the cap on 3 of 4 tasks, round 3's fix introduced a fresh P0, and when the budget ran out six findings were applied by the conductor and shipped **with no re-review** (`SHIP_WITH_CONDUCTOR_FIXES`) — cap exhaustion produced an unreviewed ship, which is worse than an early escalation.

The interim mitigation (already in tree, uncommitted): `MAX_REVIEW_ITERATIONS` default raised 4→8. The docstring names this spec's work as the real fix: a convergence-aware terminal built from the structured findings the system already persists (fn-136), plus an explicit escalate-to-human path, plus per-surface blocking calibration so trivial plan-prose residue stops consuming rounds at all.

The system already produces the convergence signal on every round — per-finding severity, confidence, classification (introduced/pre_existing), status (fixed/not_fixed/withdrawn), and cross-round lineage via `priorFindingId`/`supersedesReceiptId`, schema-validated in receipts — and then ignores it: the cap logic never reads it, and the ratchet's memory is a raw prose blob truncated at 8000 chars.

Second calibration problem: one severity vocabulary and blocking contract is applied to three surfaces doing different jobs. Plan review blocks on prose self-consistency that cannot cause a bad downstream outcome; impl review can re-litigate settled plan decisions; the land-loop PR bot (a black box we cannot re-prompt) gets zero scope guidance in its trigger comment and its prose findings can gate a merge that impl review already passed.

## Architecture & Data Models
<!-- scope: technical -->

All flowctl changes are zero-judgment plumbing (hash comparison, JSON walks over already-validated receipt data, fixed threshold rules) — consistent with the "flowctl grows only under burden of proof" principle. No new LLM calls anywhere. Every new mechanism can only END a loop earlier (early escalate, forced terminal); nothing can grant, refund, or extend rounds.

**Components touched:**

1. **Dispatch guard (flowctl)** — in `enforce_and_increment_review_cap()` (flowctl.py ~9427): before reserving a round, compare a content hash of the reviewed artifact against the hash recorded at the last consumed verdict for the same counter scope. Plan/completion reviews hash the spec markdown body (plus task files for plan reviews); impl reviews hash the diff content. Unchanged hash → refuse with a distinct non-retryable message (no round consumed, not exit 4 — a new stanza telling the caller to change the artifact, pass `--force`, or escalate). `--force` dispatches and consumes normally. The artifact hash is recorded per attempt in `review_attempts` rows (new `artifact_sha256` field, additive).
2. **Stall detector (flowctl)** — same call site, after the hash guard: walk the receipt findings lineage (current receipt + archived generations) for the counter scope and exit `REVIEW_CAP_EXIT_CODE` (4) with the existing `ESCALATE:` marker plus a stall sub-reason when any deterministic rule fires. Rules (evaluated only when ≥2 verdict-bearing rounds with schemaVersion-1 findings exist; absent/legacy findings → detector inert, cap-only behavior):
   - **Persistent not-fixed:** the same finding `id`/`priorFindingId` chain carries `status: not_fixed` across 2 consecutive verdict rounds.
   - **Flat trajectory:** across the last 2 consecutive verdict rounds, max open severity did not strictly decrease AND open-finding count did not strictly decrease.
   - **Regressing fixes:** a new `classification: introduced` finding at ≥P1 appears in each of 2 consecutive verdict rounds.
3. **NEEDS_HUMAN verdict** — added to the verdict grammar as a fourth terminal (`SHIP | NEEDS_WORK | MAJOR_RETHINK | NEEDS_HUMAN`; completion review gains it as a third: `SHIP | NEEDS_WORK | NEEDS_HUMAN`). Parsed by the existing last-`<verdict>`-tag rule (the sanctioned edge — no new parse surface). A delivered NEEDS_HUMAN consumes its round, is recorded on the receipt and `review_attempts`, and the review command exits 4 with a distinct marker line (`ESCALATE: reviewer requested human review`) so pilot/land/Ralph route it through their existing ESCALATE→NEEDS_HUMAN handling with zero driver changes. Prompt guidance (all surfaces): emit NEEDS_HUMAN when the remaining disagreement is a design judgment call or the artifact needs a decision only a human can make — never as a soft NEEDS_WORK.
4. **Ratchet reads structured findings** — `build_convergence_ratchet_block()` (~9588) consumes `findings.items` (ordinal, severity, classification, title, file:line, status) from the prior receipt instead of the 8000-char prose slice; renders a compact numbered list the re-reviewer must account for item-by-item. Prose-blob path retained as a labeled fallback for legacy receipts only. The injection-neutralization and data-not-instructions guards keep their current semantics.
5. **Per-surface calibration (prompt templates + fallbacks; hash-pinned)** —
   - **Plan review:** outcome-anchored severity definitions (P0 = following the plan produces a wrong or impossible implementation; P1 = material ambiguity likely to mislead a competent implementer; P2/P3 = consistency/polish — never blocking). Add the confidence-suppression gate plan review currently lacks (drop <75, P0 exempt at 50+ — parity with impl/completion). Blocking findings must name the concrete bad downstream outcome they prevent; ratchet rule 2 for plan-kind reviews tightens to require it ("introduced by the fixes" alone no longer suffices below that bar — the test is "could a competent implementer following this plan produce the wrong artifact?").
   - **Impl review:** a "plan is settled" clause — findings that re-litigate a decision recorded in the spec's `## Decision Context` (or `.flow/memory/knowledge/decisions/`) are FYI, never blocking (mirrors pr-comment-resolver.md:67).
   - **Completion review:** inherits the plan-surface severity definitions (it reviews spec-vs-implementation, same prose-residue exposure).
6. **Bot-surface bounding (docs + skill prose; the bot itself is a black box)** —
   - `land.reviewTrigger` documentation gains a recommended trigger text that scopes the pass (integration effects, the assembled diff as a narrative, regressions the per-task reviews structurally could not see; spec/doc-prose findings welcome as FYI, not merge-gating). Config default stays `""`.
   - resolve-pr triage gains one classification rule: on a code PR, a finding about spec/doc prose is fix-or-record (spec-touchup commit or reasoned FYI reply + resolve) but never merge-gating; a prose finding that reveals the code does the wrong thing is a code finding and blocks normally. The resolver states which class it assigned in its reply.
7. **Reset-verb guarding** — `review-rounds reset` and `spec reset-review-rounds` added to the Ralph guard blocklist (constraint: the agent must never extend or reset its own gate — today held only by prose convention); autonomous skills (pilot, land, work, ralph loop prose) state reset is human-only.

**Data flow:** reviewer emits per-finding structured data (existing fn-136 path) → receipt persists it (existing) → flowctl reads it at the next dispatch for guard/detector decisions (new) → drivers see only the existing exit codes and markers.

## API Contracts

- `enforce_and_increment_review_cap()` / the `review-rounds increment` CLI: new refusal stanza for unchanged-artifact (non-retryable text, exit code distinct from 4 — reuse exit 2 semantics is wrong; introduce no new exit code: print the stanza and exit 4 **only** for cap/stall/NEEDS_HUMAN terminals; the unchanged-artifact refusal exits with a dedicated message under the existing generic error path exit 1, explicitly marked `NOT_RETRYABLE: artifact unchanged since last verdict` so drivers do not loop). `--force` flag on the increment/dispatch surface.
- `review_attempts` row gains additive optional `artifact_sha256` (string). No schema break; existing readers ignore it.
- Verdict grammar: `NEEDS_HUMAN` accepted by the verdict parser on all backends; receipts record it verbatim in the existing `verdict` field. Exit codes 2/3/4/5 unchanged in meaning; 4 gains two new marker variants (`ESCALATE: review loop stalled (<rule>)`, `ESCALATE: reviewer requested human review`) alongside the existing cap marker.
- No `.flow/config.json` key additions or renames (no schema regen needed).

## Edge Cases & Constraints

- **Hard constraints preserved (load-bearing, from fn-90/fn-131 history):** (1) the implementing agent can never reset or extend its own gate — all new mechanisms are shorten-only, and the reset verbs get guard-blocked; (2) a delivered verdict is never re-framed as a transport failure; (3) the cap can never be disabled or set to zero; (4) every round is a real dispatch with real cost — the stall detector exists precisely to claw back the doubled worst case of the 4→8 raise; (5) exit codes 2/3/4/5 keep their meanings for autonomous drivers.
- **Runaway proof:** worst case remains exactly `MAX_REVIEW_ITERATIONS` real dispatches. The detector and NEEDS_HUMAN only terminate earlier. Transport refunds (fn-131) unchanged.
- **Reviewer gaming:** the reviewer could skew severities/statuses to keep rounds alive, but it has no self-grant path — it emits data; flowctl applies fixed rules; extension is bounded by the hard cap regardless. The reviewer is cross-model (not self-assessment) and its per-finding claims are auditable in receipts.
- **Detector false positives:** rules require 2 consecutive qualifying rounds; a loop that would have self-resolved at round 5 escalating at round 3 is acceptable (human sees a converged-except-residue state and resets — the fn-155 outcome, minus 2 wasted dispatches). Legacy/absent structured findings → detector inert; behavior degrades to today's cap-only semantics, never to a false stall.
- **Missing/stale receipt:** ratchet already silently degrades to a blind fresh review; the structured path must keep that degradation but log it (labeled fallback), since a blind re-review while the counter ticks reopens fn-90 root cause #2.
- **Prompt-text discipline:** every prompt change updates the SHA-256 pins in `test_prompt_text_pinned.py` in the same commit with rationale; embedded `*_FALLBACK` constants for the four extracted review prompts stay byte-identical to templates (`test_review_prompt_template_parity`); `VALIDATOR_TEMPLATE_FALLBACK`/`DEEP_PASSES_FALLBACK` are deliberate condensations — do not sync.
- **Cross-platform:** `./scripts/sync-codex.sh` twice (idempotency); canonical prose stays portable (no Claude-only references without fallback clauses); flowctl propagation to `.flow/bin/` + tracker manifest + parity tests per CLAUDE.md final-gate rules.
- **No-sidecar reviews stay uncapped** (standalone/branch reviews) — out of scope to change; the guard/detector require a sidecar and are inert without one.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** flowctl refuses to dispatch a re-review when the reviewed artifact's content hash equals the hash at the last consumed verdict for the same counter scope; the refusal consumes no round, is marked non-retryable, and `--force` overrides (consuming normally). `review_attempts` rows record `artifact_sha256`.
- **R2:** flowctl exits 4 with `ESCALATE: review loop stalled (<rule>)` when, over 2 consecutive verdict rounds with schemaVersion-1 findings, any of: the same finding chain stays `not_fixed`; max open severity AND open count both fail to strictly decrease; or a new `introduced` ≥P1 finding appears in each round. Absent/legacy findings leave behavior identical to today.
- **R3:** `NEEDS_HUMAN` is a parseable terminal verdict on all four backends and the host path; it consumes its round, lands on the receipt, and the review command exits 4 with `ESCALATE: reviewer requested human review`. pilot, land, and Ralph handle it via their existing ESCALATE routing with no driver code changes.
- **R4:** the convergence ratchet block renders prior findings from structured `findings.items` (numbered, with severity/classification/status) when schemaVersion-1 findings exist, with the prose blob as labeled legacy fallback; injection-neutralization behavior is preserved and covered by tests.
- **R5:** the plan-review prompt defines P0–P3 in downstream-outcome terms, carries the confidence-suppression gate (drop <75, P0 exempt at 50+), and requires blocking findings to name the concrete bad outcome; plan-kind ratchet rule 2 requires the same. The fn-156-class finding (true self-contradiction, no downstream consequence) is non-blocking under the new text; the fn-153-class finding (plan makes a task impossible) blocks.
- **R6:** the impl-review prompt states that findings re-litigating a recorded Decision Context decision are FYI, never blocking.
- **R7:** resolve-pr triage classifies spec/doc-prose findings on code PRs as fix-or-record (never merge-gating), with the prose-reveals-behavior-gap carve-out treated as a code finding; the resolver's reply names the class.
- **R8:** land docs (`flowctl.md` land config section + land skill references) document a recommended `land.reviewTrigger` text that scopes the bot pass and declares prose findings FYI; the config default remains `""`.
- **R9:** `review-rounds reset` and `spec reset-review-rounds` are in the Ralph guard blocklist; pilot/land/ralph skill prose states counter reset is human-only.
- **R10:** the uncommitted 4→8 default raise ships with this spec: an `## Unreleased` CHANGELOG entry states the raise and its rationale (interim headroom for converging tails; the detector claws back stuck-loop cost), and all user-facing docs state 8 consistently. No version bump (batched-release rule).
- **R11:** full gate green: focused suites per task, full parallel suite + `uvx ruff@0.16.0 check .` at the final gate, prompt-hash pins updated with rationale, flowctl propagated to `.flow/bin/`, tracker manifest regenerated, `sync-codex.sh` run twice with mirror diff committed.
- **R12:** STRATEGY.md's Ralph track sentence on quality discipline is extended to name convergence-aware review terminals (trajectory-based early escalation + reviewer-emitted NEEDS_HUMAN) as part of the invariant; no other strategy edits.
- **R13:** downstream chain walked in the same workstream per the maintainer's downstream-properties instructions: flow-next.dev docs pages for review caps/land/orchestration updated, docs-site changelog entry staged, AI×SDLC guide checked for touched pages, vault notes (Autonomy / Release Timeline) updated.

## Boundaries
<!-- scope: business -->

- **Do NOT shrink or demote impl review.** flow-swarm evidence: impl review produced P0s on 6 of 9 receipted tasks and catches fix-induced regressions across rounds; the PR bot found zero issues on fully impl-reviewed PRs. The surfaces are complementary; only blocking calibration changes.
- **No reviewer-decides-budget designs.** The reviewer emits data and terminal verdicts only; round arithmetic stays in flowctl. No "should this get another round?" question to any model.
- **No new LLM calls, no new subprocess judges.** Guard and detector are pure plumbing.
- **No new exit codes; no changes to 2/3/4/5 semantics.** Drivers must not need code changes.
- **Completion review keeps sharing the plan counter.** A split is cheap but unproven need — out of scope.
- **No-sidecar (standalone) reviews stay uncapped** — separate concern.
- **No flow-swarm repo changes.** The land-bypass/manual-merge hygiene there is operator follow-up, not flow-next code.
- **No per-surface rubric rewrites.** The 8 numbered criteria per surface already diverge fully; only severity definitions, gates, and blocking contracts change.
- **The cap itself stays count-based and enabled.** No trajectory rule may raise, refund, or disable it.
- **No changes to the fn-131 transport-refund machinery.**

## Strategy Alignment

- **"Remember the bitter lesson":** the detector is an unattended-trust rail (bounded loops, receipts-driven), the explicitly sanctioned category — not quality compensation for a weak model. The calibration changes state the bar in general sentences inside existing prompts rather than adding scaffolding.
- **"flowctl grows only under burden of proof":** hash comparison, lineage walks, fixed thresholds — zero judgment, must work with no agent in the loop (Ralph). Everything that reads-and-weighs (what severity a finding deserves, whether prose misleads) stays with the reviewing/host models.
- **"Receipts are the portable product boundary":** the terminal consumes the fn-136 structured findings exactly as a downstream product would — versioned, additive, labeled fallback — proving the contract on our own machinery first.
- **Ralph track:** strengthens the "multi-model review at every handover / don't-thrash reflexes" invariant with a trajectory-aware stop and a first-class human-escalation path.

## Strategy Conflicts

None identified. The one candidate — "agentically decide whether things are converging" — was resolved in favor of deterministic trajectory rules precisely because a model-judged budget would violate the unattended-trust rail principle; the agentic element survives only as the reviewer's NEEDS_HUMAN verdict, which is shorten-only.

## Decision Context

Why trajectory-augmented count cap over the alternatives. **Raise-to-8 alone** doubles the worst case on stuck specs and was explicitly labeled interim in the docstring that shipped it. **Replace count with model-judged convergence** violates the load-bearing constraint that the agent can never extend its own gate, and asking the reviewer "another round?" gives it a budget decision it has no business owning. **Refund fix-induced-residue rounds** makes the classifier the loophole that swallows the cap — rejected; residue headroom comes from the raised cap, and trivial residue is instead prevented from blocking at all via the plan-surface outcome test. The chosen design keeps every fn-90/fn-131 property (deterministic counter, transport refunds, distinct exit codes, ESCALATE-not-retry) and adds only shorten-only terminals computed by flowctl from reviewer-emitted structured data — the reviewer is cross-model so the signal is not self-assessment, and it cannot self-grant because it never touches arithmetic. Per-surface divergence is deliberately confined to severity definitions and blocking contracts because the evidence showed the rubrics already diverge (0 of 8 numbered criteria shared) and the observed failures were calibration failures: plan reviews blocking on outcome-free prose (fn-155/153/156), impl review lacking a settled-plan clause, and the un-promptable PR bot being over-weighted in flow-next (prose findings gating merges) while structurally ignored in flow-swarm (17/23 reviews post-merge). The bot stays a bounded-and-filtered safety net: scope via the trigger comment we control, blocking-ness via resolve-pr triage we control.

---

**Spec Quick commands:** `cd plugins/flow-next/tests && python3 -m unittest test_review_convergence_cap test_host_review_backend test_prompt_text_pinned -q`. Full gate once at completion: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .` + flowctl propagation + `./scripts/sync-codex.sh` ×2.
