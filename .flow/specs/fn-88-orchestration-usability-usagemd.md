# fn-88-orchestration-usability-usagemd Orchestration usability: usage.md steering recipes + optional setup routing scaffold

## Goal & Context

flow-next 2.7.2 shipped the orchestration & model-routing reference (`plugins/flow-next/docs/orchestration.md` + flow-next.dev `/orchestration/`): the two routing methodologies (deterministic parameters vs prompted orchestration), the CLI-agent bridge, the CLAUDE.md model-routing table, loop chaining. That documentation lives *outside the repo a user is working in*. At use time, the host agent reads `.flow/usage.md` and the project's `CLAUDE.md`/`AGENTS.md` — and today neither says a word about steering other harnesses or routing models. A user (or their host agent) currently has to already know the review-backend registry, `work.delegate*` keys, or the plugin's doc tree to run the orchestration patterns.

Why now: frontier-orchestrator + cheap-implementer routing is the dominant power-user pattern of mid-2026 (orchestrate on the frontier model; implement via `codex exec` on an existing ChatGPT sub; review cross-family via `cursor-agent`/codex). flow-next is unusually good at this because skills are host-executed prompts — prompted orchestration works today with zero code. This spec is purely a **discoverability** close, deliberately low-effort: put copy-paste steering recipes where agents already look, and offer — opt-in, at setup time — to scaffold the model-routing table into the project's instruction file. The key message carries over from the docs: defaults are pre-tuned and require none of this; steering is a capability, not a prerequisite.

## Architecture & Data Models

Two touch points, no new subsystems:

1. **`plugins/flow-next/skills/flow-next-setup/templates/usage.md`** — new `## Orchestration & model steering` section (~40–60 lines, budget-conscious: usage.md is installed per-repo and read often). Contents: `delegate:codex` quickstart, `review.backend` one-liners incl. per-task `review:` override, one direct CLI-bridge example each for `codex exec` and `cursor-agent` (harness-relative wording — from Claude Code, `codex exec` is the bridge; from Codex, `claude -p` / `cursor-agent` are), 2–3 prompted-orchestration examples (per-item complexity routing, conditional escalation), and a link to `docs/orchestration.md` + `https://flow-next.dev/orchestration/`. Pure template content — flowctl setup already copies it; no skill-logic change for this half.

2. **`plugins/flow-next/skills/flow-next-setup/`** — one new optional ceremony step: offer to append a commented model-routing scaffold to the platform-correct instruction file (`CLAUDE.md` on Claude Code, `AGENTS.md` on Codex/Droid), following the create-or-augment pattern established by /flow-next:prime (fn-88 P4–P7 batch, 2.7.0). Scaffold = the copy-paste block from `docs/orchestration.md` (ranking table with role-label framing + how-to-apply rules incl. standing permission to escalate). Single-sourced in one template file under the setup skill's `templates/`; `docs/orchestration.md` links to it rather than duplicating (R17 cross-link discipline).

Cross-platform: canonical skill prose uses `AskUserQuestion`; `sync-codex.sh`'s existing numbered-prompt transform covers the new ceremony question; no new sync machinery.

## API Contracts

- No new flowctl commands or config keys. Existing surfaces referenced verbatim: `work.delegate*`, `review.backend`, per-task `review:`, `spec set-backend`.
- The scaffold block appended to the instruction file is fenced with explicit markers (shape decided at plan time, e.g. `<!-- flow-next:model-routing:start -->` / `:end`) so augment, refresh, and uninstall are deterministic.
- `/flow-next:uninstall` removes exactly the marker-fenced block and nothing else.

## Edge Cases & Constraints

- Existing user-authored routing section in CLAUDE.md/AGENTS.md (heading or marker match) → offer augment or skip; never duplicate, never overwrite; mandatory read-back before any write (capture/prime discipline).
- Non-interactive / Ralph / headless setup → the ceremony step is skipped silently (default No); setup must never block autonomously.
- Codex mirror must not mention `AskUserQuestion` (existing R-guards); validation suite must pass.
- Model names are volatile: the scaffold writes durable role labels with placeholder model rows and a comment telling the user to re-rank — never presents the shipped rankings as maintained truth.
- Token budget: usage.md section links to the full doc, never embeds it (R17); target ≤ ~60 lines.
- Uninstall must not touch user edits outside the markers, including edits *inside* a partially-hand-modified block (if markers are damaged, report and skip rather than guess).

## Acceptance Criteria

- **R1:** `templates/usage.md` gains `## Orchestration & model steering`: `delegate:codex` quickstart, `review.backend` one-liners + per-task `review:` example, one direct `codex exec` bridge example, one `cursor-agent` bridge example (harness-relative wording), ≥2 prompted-orchestration examples (per-item complexity routing; conditional escalation), links to `docs/orchestration.md` and `https://flow-next.dev/orchestration/`; section ≤ ~60 lines.
- **R2:** Setup ceremony gains one optional step offering the model-routing scaffold append to the platform-correct instruction file; default is skip; non-interactive/headless paths skip silently.
- **R3:** Scaffold is appended between explicit start/end markers; existing-section detection (marker or heading) routes to augment-or-skip; mandatory read-back before write.
- **R4:** Scaffold content is single-sourced in one setup template file; `docs/orchestration.md` cross-links it; content keeps role-label durability framing + the standing-permission-to-escalate rule.
- **R5:** `scripts/sync-codex.sh` regenerates cleanly: ceremony question rendered via the plain-text numbered-prompt transform, no `AskUserQuestion` mention in the mirror, full validation suite green.
- **R6:** `/flow-next:uninstall` removes the marker-fenced block exactly; damaged/missing markers → report and leave untouched.
- **R7:** `docs/orchestration.md` + the flow-next.dev orchestration page gain "in your repo" pointers (usage.md section + setup step); CHANGELOG entry staged under `## Unreleased` (no version bump — batched release per CLAUDE.md).
- **R8:** Tests: setup ceremony default-skip covered; template copy/render covered; uninstall marker-removal covered (extend existing setup/uninstall test surfaces; `smoke_test.sh` + unittest green).

## Boundaries

Out of scope, deliberately: no routing engine or automatic model switching; no new flowctl commands or config keys; no conditionals added to any other skill (work/pilot/review skills unchanged); no per-skill model parameters; no new review-backend registry rungs (a `fable` reviewer stays a prompted arrangement, not a rung); no CI enforcement of routing; no changes to the Codex-mirror model mapping.

## Decision Context

Three alternatives rejected. (a) A new `/flow-next:orchestrate` skill — adds command surface for what prompting already does; the 2.7.2 doc proves the host executes routing policy from plain instructions. (b) Routing conditionals inside each skill honoring a config table — high maintenance across 28 skills, contradicts the skill-driven architecture rule (host agent is the intelligence), and prompted orchestration already reaches everything it would add. (c) Docs-only status quo — use-time discoverability is zero; agents read `.flow/usage.md` and instruction files, not the plugin's doc tree. usage.md is the lowest-effort surface agents already read every session; setup is the one moment flow-next already writes instruction files with consent machinery in place, so the scaffold rides existing rails. Marker-fencing follows the proven augment/uninstall-safety pattern rather than heading-heuristics. Single-sourcing the scaffold under setup's templates (with docs linking in) was chosen over duplicating the block in `docs/orchestration.md` to satisfy R17 and keep one edit point when model generations rotate.
