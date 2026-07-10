# fn-94 Document subagent thin-wrapper pattern for headless harness bridges (tracking + isolation)

> **Status: stub — low priority.** Deliberately queued after the current spec backlog (fn-89, fn-93 follow-ups, etc.). Refine via `/flow-next:interview` before planning.

## Goal & Context

The orchestration guidance (`.flow/usage.md` § "Orchestration & model steering", `plugins/flow-next/docs/orchestration.md`, and the `/flow-next:setup` CLAUDE.md model-routing scaffold) shows headless CLI bridges (`codex exec`, `cursor-agent`, `claude -p`) invoked as **bare Bash calls from the host session**. That works, but the host harness treats the bridge run as an opaque shell command: no per-run progress entry, no background-task tracking, the full bridge transcript/output lands in the host's main context, and parallel bridge runs are indistinguishable blobs.

Wrapping the bridge call in a **subagent** (Claude `Task`/`Agent`, Codex `spawn_agent`) fixes all of that for free: the harness tracks the subagent as a first-class unit of work (visible, backgroundable, individually labeled), the wrapper composes the self-contained prompt and runs the bridge over Bash inside its own context, and only the digest returns to the host. The setup scaffold already hints at this ("Reach gpt-5.5 inside a subagent (thin-wrapper): a cheap wrapper writes a self-contained prompt, runs `codex exec` over Bash, returns the digest") — but it's one throwaway line, not a documented recipe, and usage.md's bridge section doesn't mention it at all.

This spec elevates the thin-wrapper subagent pattern to a first-class documented recipe across the orchestration docs.

## Architecture & Data Models

Docs-only change (no flowctl/plugin code expected). Surfaces to touch:

- `.flow/usage.md` § "Orchestration & model steering" — add a short "wrap bridges in a subagent for tracking" recipe next to the bare-Bash bridge examples. NOTE: usage.md is generated/copied by setup — find the canonical source in the plugin (`plugins/flow-next/...`) and edit there; `.flow/usage.md` in this repo is the setup-managed copy.
- `plugins/flow-next/docs/orchestration.md` — a proper subsection: when to bare-Bash (single quick call) vs when to thin-wrap (long-running impl, parallel fan-out, anything you want tracked/backgrounded); example wrapper prompt shape.
- `/flow-next:setup` model-routing scaffold — expand/clarify the existing thin-wrapper line so it links the concept.
- Cross-platform: canonical files use Claude-native `Task` naming; `sync-codex.sh` rewrite to `spawn_agent` must hold (check the sync script handles any new prose).

Open question for interview: should any skill (work delegate:codex path?) itself adopt the wrapper, or is this purely user-facing orchestration guidance? Initial position: docs-only; skills unchanged.

## API Contracts

None (prose/docs). The "contract" is the documented wrapper shape: wrapper subagent receives task context → composes self-contained prompt → runs bridge CLI via Bash (with the existing stdin/output-capture rules: `</dev/null`, `-o out.md`, never stdout-scrape) → returns digest only.

## Edge Cases & Constraints

- Subagent nesting limits: a wrapper subagent spawning `codex exec` is Bash-from-subagent, fine; but document that the delegate CLI must never recursively delegate (existing rule holds).
- Ralph/pilot autonomous contexts: wrapper pattern must not conflict with subagent budget/caps in those loops.
- Codex-mirror parity: `sync-codex.sh` tool-name rewrites for any canonical prose added.
- Keep the zero-quality-loss prose discipline: recipes concise, no duplication between usage.md and orchestration.md (usage.md gets the short form + link; orchestration.md the full treatment).

## Acceptance Criteria

- **R1:** `.flow/usage.md` orchestration section (via its canonical plugin source) documents the thin-wrapper subagent recipe alongside the bare-Bash bridges, with a one-line when-to-use discriminator.
- **R2:** `plugins/flow-next/docs/orchestration.md` gains a subsection covering: why (harness tracking, context isolation, parallel labeling), when bare-Bash suffices, an example wrapper dispatch.
- **R3:** Setup's CLAUDE.md model-routing scaffold thin-wrapper line is consistent with the new docs (same vocabulary, links where possible).
- **R4:** Codex mirror regenerated (`sync-codex.sh`) with correct tool-name rewrites; docs-site (`flow-next.dev` orchestration page) updated in the same workstream.
- **R5:** No behavior/code changes to skills or flowctl; no version bump (docs-only rule) unless scope grows during interview.

## Boundaries

- OUT: changing `/flow-next:work` delegate:codex internals or any skill to auto-wrap bridges.
- OUT: new flowctl config keys, agents, or skills.
- OUT: MCP-based bridge transports; this is about the existing Bash CLI bridges.
- OUT: prescribing model choices — the pattern is model-agnostic plumbing guidance.

## Decision Context

Why now (loosely): multi-model orchestration usage is growing (fn-88 dogfood runs drove codex/cursor/claude -p bridges heavily) and bare-Bash bridge runs are the least observable part of those sessions — a long `codex exec` looks like a hung shell command. The subagent wrapper is zero-new-machinery (platform primitives already exist, scaffold already hints it) — this is purely closing a documentation gap. Alternative rejected for now: building tracked-bridge support into flowctl (deterministic wrapper script + receipts) — heavier, and the host harness already provides tracking via subagents; revisit only if docs-level guidance proves insufficient.

Priority: **low** — explicitly sequenced after the current backlog; no urgency, no user-reported pain yet.
