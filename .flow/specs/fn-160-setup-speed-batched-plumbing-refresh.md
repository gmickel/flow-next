# fn-160-setup-speed-batched-plumbing-refresh Setup speed: batched plumbing, refresh fast path, per-platform workflow split

## Goal & Context

`/flow-next:setup` is really slow in practice — worst in copy mode on a Codex host — and the copy-mode upgrade path (re-run setup per repo after every plugin update) feels like massive friction. [user]

Analysis of the current skill (2026-08-02 session) attributes the wall clock to four compounding costs, none of which is the questions themselves: [inferred]

1. **Context bulk.** The setup workflow document is ~75KB (~30k tokens) and must be read before step 1. It embeds all five platform variants of the Review and Docs questions plus multi-paragraph detection-rationale archaeology, so every host reads ~5x what one platform needs. [inferred]
2. **Subprocess churn.** ~7 separate raw config-get probes plus ~13 config-set calls, plus init / sync-active / setup-block / verify / stamp invocations — each a separate Python spawn and a separate agent tool-call round-trip. [inferred]
3. **Live LLM probes in the model-pins ceremony.** Foreground `codex exec` accept-probes (20s timeout each), `copilot -p "/model"`, `cursor-agent --list-models` run on every re-run, with no staleness gate on `models.verifiedAt`. [inferred]
4. **Codex ask serialization.** The mirror's plain-text numbered prompts are stop-and-wait; the asks outside the grouped 6d prompt (mode gate, SPEC.md offer, usage.md compare, HTML follow-up, model-pins propose, routing refresh, docs overwrite) can add up to ~8 blocking round-trips per run. [inferred]

Hard constraint: optimize without removing any question or any explanation — every existing ask and its rationale stays reachable. [user]

## Architecture & Data Models

Direction (details to `/flow-next:plan`): [inferred]

- Move mechanical batches into thin flowctl plumbing per the repo's skill/plumbing split: one detection read-out command, batched config writes, and a deterministic refresh command that re-copies snapshots + re-applies docs blocks + restamps the version.
- Split the monolithic workflow document: a slim core plus per-platform question/prose references loaded only after `PLATFORM` resolves (same conditional-reference pattern the skill already uses for model-routing and Ralph). Detection-fixture rationale moves to a reference consulted only when detection misbehaves.
- The Codex mirror keeps its numbered-prompt rewrite; consolidation only regroups asks where ordering already permits.

## API Contracts

Left to plan. Candidate surface (names not final): `flowctl setup detect --json` (single detection/probe read-out), a multi-key `flowctl config set` form, `flowctl setup refresh` (or a `--refresh` skill argument). [inferred]

## Edge Cases & Constraints

- The refresh fast path must honor the existing customization sentinels: pristine/kept docs blocks refresh or stay silently; only a genuinely ambiguous block (`ask` action) may prompt. [inferred]
- A model-pins staleness gate must never skip a first-ever pin write (no `models.verifiedAt` on disk = ceremony still offered), and an explicit user request must always be able to force a refresh. [inferred]
- Per-platform splitting must survive `sync-codex.sh` regeneration and its idempotency/validation guards. [inferred]
- Plugin-mode (fn-121) semantics, consent gates, mode-transition table, and the stamp-last invariant are behavior-frozen — restructuring must not alter what any run writes or asks, only how fast it gets there. [inferred]

## Acceptance Criteria

- **R1:** A single deterministic flowctl call returns everything Step 6a currently gathers piecemeal (platform inputs, raw config values, tracker-active, criteria existence, CLI detection), replacing the per-key probe fences. [inferred]
- **R2:** Step 7's config persistence lands in at most 1-2 flowctl invocations instead of one spawn per answer. [inferred]
- **R3:** A refresh fast path exists for copy-mode upgrades: one invocation re-copies bin/templates/tracker snapshots, re-applies marker-scoped docs blocks, verifies the tracker package, and restamps `setup_version` — asking zero questions unless a docs block is genuinely customized-ambiguous. [user: upgrade friction is the complaint; mechanism inferred]
- **R4:** The mandatory pre-read for a setup run shrinks substantially (target: the resolved platform reads well under half of today's ~75KB), with platform-specific question sets and detection archaeology moved to conditionally-loaded references. [inferred]
- **R5:** The model-pins ceremony gates its live CLI probes on staleness: fresh `models.verifiedAt` (within the existing ~90-day window) skips probes and the ask on routine re-runs, with an explicit opt-in to force a refresh; first-run behavior unchanged. [inferred]
- **R6:** On the Codex mirror, blocking plain-text round-trips per fresh copy-mode run are reduced by regrouping asks where step ordering permits, without dropping or merging away any question's content. [inferred]
- **R7:** No question, option, recommendation, or explanation is removed: every ask reachable today remains reachable with equivalent copy, and all consent gates (overwrite, mode transition, Ralph, delegation) fire under the same conditions. [user]
- **R8:** Existing setup-related tests, prompt-hash pins where applicable, and the sync-codex idempotency guards stay green; mirror regenerated twice with no diff churn. [inferred]

## Boundaries

- No question or explanation removal — this is a latency/friction change, not a ceremony diet. [user]
- No change to what setup decides or writes: same config keys, same stamps, same consent semantics. [inferred]
- No redesign of the model-pins ceremony's judging content — only when it runs. [inferred]
- Cursor/Grok/Droid host behavior contracts unchanged. [inferred]

## Decision Context

The user's complaint has two heads: raw slowness (worst on Codex copy mode) and the upgrade treadmill. The refresh fast path (R3) attacks the treadmill directly and is the highest-value single change; the plumbing batching (R1/R2) and doc split (R4) attack per-run latency; the staleness gate (R5) removes the single slowest step (live LLM probes) from routine runs. Prose trimming alone was rejected as the primary lever because the user explicitly protects questions and explanations — the wins must come from plumbing, conditional loading, and gating instead. [paraphrase]

Process note: this spec and its plan land directly on main (via an isolated worktree) so the in-flight agent on `chore/review-cap-8` is not disturbed; implementation happens later on its own branch. [user]

## Conversation Evidence

- "can we optimize flow-next:setup more? not remove questions or explanations but right now it's really slow for some reason, especially copy mode in codex" [user]
- "it's annoying to upgrade which seems like massive friction to me" [user]
- "dont disturb the agents working on this branch as you analyse" [user]
- "get it onto main without disturbing the agent, then plan it" [user]
- Agent analysis accepted for capture: 75KB workflow pre-read; ~20+ serial flowctl spawns; live `codex exec`/`copilot`/`cursor-agent` probes in ceremony 6e on every re-run; ~8 blocking numbered-prompt waits on Codex; upgrade re-run re-walks the full ceremony to perform a mechanical re-copy. [inferred]
