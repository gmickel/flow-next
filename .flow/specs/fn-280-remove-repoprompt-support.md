# Remove RepoPrompt support

## Goal & Context

RepoPrompt was deprecated in 7.1.0 and leaves in 8.0.0: the `rp` review backend, `/flow-next:export-context`, and everything flowctl does to find and drive a RepoPrompt window. This spec removes it completely and is built first of the three 8.0.0 specs, because it is almost pure deletion and shrinks the review surface the agentic-review spec then has to cover. [paraphrase]

The removal must leave every remaining review path working exactly as before (codex, host, claude, copilot, cursor) on every harness flow-next supports (Claude Code, Codex, Cursor, Droid, Grok Build, OpenCode), and must add no new machinery. [paraphrase] A project that still names RepoPrompt somewhere is told so in one line rather than having review switch off silently. [paraphrase]

<!-- Source: 60% user / 25% [paraphrase] / 15% [inferred] -->

## Architecture & Data Models

- **What goes.** The `rp` backend everywhere a backend is named (registry, accepted values, the generated config schema, per-task and per-spec review selection, the `--review` flag, env override), the RepoPrompt CLI discovery and window/workspace/chat plumbing in flowctl and its `rp` command group, the RepoPrompt eligibility probes that skills run before choosing a backend, setup's RepoPrompt option and its tool probe, the export-context skill and plan review's export mode built on it, the RepoPrompt review workflows in the impl, plan and completion review skills, the worker's `rp` review mode, and the RepoPrompt-only tests, fixtures and CI shell sections. [paraphrase]
- **What stays, reworded only.** The review-round and review-artifact commands are shared with host review; they keep their behaviour and lose their RepoPrompt wording, and their backend argument stops defaulting to `rp`. [paraphrase]
- **One value renamed.** A QA receipt written from a payload file records a mode that today reads `rp` but means "receipt-driven", not RepoPrompt; it gets a name that does not mention RepoPrompt. [paraphrase]
- **Generated surfaces.** The Codex mirror, the flowctl help text and the config schema are regenerated from the changed sources, never hand-edited. [paraphrase]

## API Contracts

- Accepted review backends after this change: `codex`, `host`, `claude`, `copilot`, `cursor` (plus `none` where it is accepted today). `rp` and `export` are no longer accepted anywhere a backend or review mode is named. [paraphrase]
- The stale-value notice is one line on stderr naming that RepoPrompt was removed in 8.0.0 and the backends that remain, printed once per invocation that reads the stale value. [inferred]
- Skill count: 29 skills everywhere the count is stated. [paraphrase]

## Edge Cases & Constraints

- Receipts already on disk with `mode: "rp"` (QA and review receipts) must keep reading wherever receipts are read today, including the PR briefing and review history. [paraphrase]
- An existing install that still has the export-context skill loses it through each installer's existing stale-skill cleanup (the Codex retire step, the OpenCode manifest, the Cursor snapshot, plugin updates on Claude Code, Droid and Grok); no new cleanup code. [paraphrase]
- Tests that used `rp` only as a stand-in for shared behaviour (round caps, journals, findings parsing, receipts) move to a remaining backend; they are not deleted. [paraphrase]
- Memory entries and changelog history that mention RepoPrompt stay as history. [inferred]

## Acceptance Criteria

- **R1:** No surface accepts or offers RepoPrompt: `rp` is absent from the backend registry, accepted values, generated config schema, setup's menus on every platform variant, command argument hints, skill prose, the worker agent, docs and glossary (changelog history excepted), and flowctl has no `rp` command group. Errors: a stale `rp` in config, the review env override, a task's review field, a spec's default review or `--review=rp` → the one-line notice, and review then behaves as "no reviewer configured" with that notice shown; never a crash and never a silent skip. [paraphrase]
- **R2:** `/flow-next:export-context` and plan review's export mode are removed, and no skill offers or accepts `export` as a review mode. Errors: `--review=export` → the same one-line notice as R1. [paraphrase]
- **R3:** Host review keeps working unchanged: the shared review-round and review-artifact commands behave as before, with RepoPrompt wording removed and no `rp` default. Errors: no error surface beyond today's. [paraphrase]
- **R4:** The QA receipt's receipt-driven mode is renamed away from `rp`, and every receipt on disk with `mode: "rp"` (QA or review) still reads everywhere receipts are read today. Errors: no error surface beyond today's. [paraphrase]
- **R5:** Parity: every harness's installed surface (Claude Code, Codex, Cursor, Droid, Grok Build, OpenCode) carries no RepoPrompt option after install or update, the Codex mirror is regenerated with no RepoPrompt text, and an existing install drops export-context through the installers' existing cleanup. Errors: no error surface beyond the installers' existing ones. [paraphrase]
- **R6:** The skill count reads 29 in every manifest, doc and help text that states it. Errors: no error surface. [paraphrase]
- **R7:** RepoPrompt-only tests, fixtures and CI shell sections are deleted; tests that used `rp` as a stand-in for shared behaviour run on a remaining backend and pass; the full suite, smoke suites, Codex mirror check, doc-anchor check and help-text check pass. Errors: no error surface. [paraphrase]
- **R8:** The 8.0.0 changelog states that RepoPrompt and export-context are gone and which reviewers remain; downstream properties (flow-next.dev, the AI x SDLC guide, mickel.tech) drop their RepoPrompt mentions at release. Errors: no error surface. [paraphrase]
- **R9:** Measured with the fn-271 harness on one review case against 7.1.2: no wall-clock or quality regression. Errors: a regression blocks the change until explained or fixed. [paraphrase]

## Boundaries

- No replacement for export-context's "export the context for an external model" flow. [inferred]
- No change to how the remaining backends review; retiring `review.backend` itself is a later 8.0.0 spec. [paraphrase]
- MergeFoundry is not a constraint; it adapts after 8.0.0 lands. [paraphrase]
- No new machinery. [paraphrase]

## Decision Context

RepoPrompt was announced as deprecated in 7.1.0 with removal in 8.0.0. [paraphrase] It is built first because removal is mostly deletion (about a thousand lines of flowctl, six skill files, its tests) and leaves fewer review paths for the agentic-review work to handle. [paraphrase] Export-context is dropped rather than rebuilt on another tool because it existed to export a RepoPrompt context and nobody asked for a replacement. [inferred] A stale `rp` value produces a notice and continues as "no reviewer configured" rather than failing the run, so an upgraded project keeps working while it is told what changed. [inferred]

## Strategy Alignment

- Serves the approach's "zero external dependencies": RepoPrompt was a macOS-only external tool the base install never needed. [inferred]
- Serves "Cross-platform parity": one less backend that only worked on one platform. [strategy:Cross-platform parity]

## Strategy Conflicts

None.
