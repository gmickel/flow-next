# fn-88-orchestration-usability-usagemd Orchestration usability: usage.md steering recipes + optional setup routing scaffold

## Goal & Context

flow-next 2.7.2 shipped the orchestration & model-routing reference (`plugins/flow-next/docs/orchestration.md` + flow-next.dev `/orchestration/`): the two routing methodologies (deterministic parameters vs prompted orchestration), the CLI-agent bridge, the CLAUDE.md model-routing table, loop chaining. That documentation lives *outside the repo a user is working in*. At use time, the host agent reads `.flow/usage.md` and the project's `CLAUDE.md`/`AGENTS.md` — and today neither says a word about steering other harnesses or routing models. A user (or their host agent) currently has to already know the review-backend registry, `work.delegate*` keys, or the plugin's doc tree to run the orchestration patterns.

Why now: frontier-orchestrator + cheap-implementer routing is the dominant power-user pattern of mid-2026 (orchestrate on the frontier model; implement via `codex exec` on an existing ChatGPT sub; review cross-family via `cursor-agent`/codex). flow-next is unusually good at this because skills are host-executed prompts — prompted orchestration works today with zero code. This spec is purely a **discoverability** close, deliberately low-effort: put copy-paste steering recipes where agents already look, and offer — opt-in, at setup time — to scaffold the model-routing example into the project's instruction file. The key message carries over from the docs: defaults are pre-tuned and require none of this; steering is a capability, not a prerequisite.

**Intent (load-bearing, user decision 2026-07-05):** the scaffold ships a **full, opinionated orchestration example** — a scores table (cost / intelligence / taste, higher = better) over the models reachable via Claude-native tiers + `codex` CLI + `cursor-agent`, how-to-apply rules, and explicit flow-next wiring — because a filled-in example the user can *react to* beats an empty template they must author. The authority problem is solved at the **read-back moment**: setup shows exactly what it will write and invites the user to overwrite freely ("these scores are starting opinions — re-rank them to what you actually pay for and prefer; this section is yours now"). Maximally agentic by default; the user edits it down, not up. Two truth-guards stay: rows for CLIs the reachability probes did not find are written **commented-out/annotated** (never a silently active route to a missing binary), and the delegation consent gate is never pre-set. Dogfood-and-tweak is the explicit plan — the shipped opinions get revised from real use.

**Scope split (user-confirmed):** the usage.md section is **unconditional** (ships with the template, installed everywhere); only the CLAUDE.md/AGENTS.md scaffold is the opt-in ceremony step.

## Overview & Approach

Two touch points, no new subsystems. Both ride existing, verified machinery (research pass 2026-07-05):

1. **`plugins/flow-next/skills/flow-next-setup/templates/usage.md`** — new `## Orchestration & model steering` section (~40–60 lines; top-level insert AFTER the `## Common Commands` fence closes — `Config`/`Checkpoint` are comments INSIDE that bash fence, never an insertion anchor; fences must stay balanced). **Short *agentic* instructions for driving the other harnesses headlessly** — written for the host agent to execute, distilled from what the project already documents (`codex-delegation.md`, the cursor backend wrappers, review-backend registry) and corrected against current official CLI docs:
   - `codex exec "<self-contained prompt>"` — **defaults to a read-only sandbox**; implementation needs explicit `--sandbox workspace-write` (`--full-auto` is deprecated); capture the result via `-o/--output-last-message <path>`, never stdout scraping; **redirect stdin from `/dev/null`** when spawning from another agent (known indefinite-hang bug on inherited non-TTY stdin); no recursive delegation (`agents.max_depth=1`). Investigation mode: `codex exec -s read-only`.
   - `cursor-agent -p "<prompt>" --model <id>` — headless print mode; **`--force` required to actually apply edits** (else proposed-only); headless auth via `CURSOR_API_KEY`; model IDs are volatile — verify via `--list-models`.
   - Self-contained-prompt discipline: full context in, digest back, the delegate never touches git.
   - Harness-relative wording: from Claude Code, `codex exec`/`cursor-agent` are the bridges; from Codex, `claude -p` / `cursor-agent` are.
   - Plus the flow-next shortcuts that package the same bridges: `delegate:codex` quickstart, `review.backend` one-liners incl. per-task `review:` override; 2–3 prompted-orchestration examples (per-item complexity routing, conditional escalation); link to `docs/orchestration.md` + `https://flow-next.dev/orchestration/`.
   - Pure template content — flowctl setup already copies it. **Dogfood parity**: `test_dogfood_template_parity.py` asserts repo-root `.flow/usage.md` ≡ the template byte-for-byte — both files change in the same commit.

2. **`plugins/flow-next/skills/flow-next-setup/`** — one new optional ceremony question offering the **orchestration example scaffold**. Slots into the existing single grouped `AskUserQuestion` flow (workflow.md Step 6d, follow its existing grouping/chunking mechanics) with processing in Step 7 **after** the existing Docs-block processing (same target file is touched twice in one run — sequential, re-read from disk, never interleaved). The scaffold content lives in a new **`templates/model-routing-snippet.md`** (single source; sibling of `claude-md-snippet.md`):
   - **Scores table** — `model | cost | intelligence | taste` (higher = better) over: the session/frontier model, `gpt-5.5` via codex CLI, `composer-2.5` via cursor-agent, a fast Claude tier — framed "cost reflects what you actually pay (existing subscriptions), not list price" + explicit re-rank invitation.
   - **How-to-apply rules** — defaults-not-limits + standing permission to escalate (always included; judge the output, not the price tag); intelligence > taste > cost for anything that ships; bulk/mechanical implementation → gpt-5.5; user-facing work needs taste ≥ threshold; reviews cross-family; **graceful degrade**: a routed CLI that fails at use time (missing, unauthenticated, errors) → report unavailable and fall back to the session model — never block.
   - **flow-next wiring** — names the concrete surfaces each rule drives: the `/flow-next:work` worker + `delegate:codex`; `plan-review`/`impl-review`/`spec-completion-review` via `review.backend` (codex / cursor:composer-2.5 / per-task `review:`); scouts (Bash-capable, no Edit/Write) may shell out to `cursor-agent` for bulk reads; the thin-wrapper pattern for reaching gpt-5.5 *inside* subagent workflows (cheap low-effort wrapper agent writes a self-contained codex prompt, runs `codex exec` via Bash, returns the digest).
   - **Truth annotations (probe sentinels)** — reuse the existing `HAVE_CODEX`/`HAVE_CURSOR` probes (workflow.md:359-362). The template puts every CLI-dependent route on its **own line, prefixed with a probe sentinel** (`<!-- probe:codex -->` / `<!-- probe:cursor -->`); composition is a **deterministic line transform** — a failing probe comments out exactly its sentinel-tagged lines and appends "not detected on this machine — uncomment after installing". Mechanically testable for all four HAVE_CODEX×HAVE_CURSOR states.
   - **Write mechanics** — marker-fenced `<!-- flow-next:model-routing:start -->` / `<!-- flow-next:model-routing:end -->` (colon-namespaced family, matching `flow-next:artifact-link`), with a provenance line ("scaffolded by /flow-next:setup — edit freely; re-run setup to regenerate"; the invocation syntax is composed per platform at write time — `/flow-next:setup` vs `$flow-next-setup`, the same split the snippet templates already encode). Reuses the Docs-block idiom verbatim: no marker → append; marker present → byte-compare vs the **current composed canonical (today's probe state)** → identical = silent no-op (no mtime bump); different = `Keep mine (Recommended)` / `Overwrite with canonical` / `skip` — a probe-state change since the last scaffold (e.g. cursor-agent installed later) counts as canonical drift and surfaces the same question, never a silent rewrite. Marker presence IS the re-run state — no new config key.
   - **Read-back — would-write path only.** Order: resolve target → compose → inspect marker + byte-compare FIRST; identical to current canonical = silent no-op (end, nothing shown — R11). Only when a write would happen (no marker, or Overwrite chosen on drift) is the full composed block shown with options `write` / `skip` immediately before the write; after writing, one confirmation line invites free editing. Never a silent write — and never a redundant read-back on an unchanged re-run.
   - **Target file — deterministic ladder, independent of whether the Docs question fired:** (1) the user answered the Docs question this run → mirror that choice (incl. "Both" → same block to both files); (2) Docs skipped/current → the file(s) already carrying the `BEGIN FLOW-NEXT` docs marker (marker in both → Both); (3) neither → the platform-default mapping (existing Droid-with-Claude and Cursor buckets in workflow.md 6b). **Shim guard (exact patterns):** a target whose only non-empty content line matches `@<path>.md` or `See[:] <path>.md` (case-insensitive, repo-relative) is a shim — follow the pointer when the file exists in-repo, else report + skip; anything else is a normal file. Never turn a shim into a mixed file.
   - **Delegation option** — the question's option set is frozen: `scaffold` / `scaffold + enable codex delegation` (shown only when `HAVE_CODEX=1`; sets `work.delegate codex` via existing config machinery) / `skip` (default). `work.delegateConsent` is NEVER pre-set — the first-use consent gate stays live.

Cross-platform: canonical skill prose uses `AskUserQuestion`; `sync-codex.sh` copies `templates/` wholesale and its catch-all rewrite rules transform the ceremony prose automatically (verified sync-codex.sh:140, :186, rules A–L) — **no new sync machinery**. Note Claude Code does not natively read AGENTS.md — the platform mapping (which already encodes this) is reused, not re-derived.

## API Contracts

- No new flowctl commands or config keys. Existing surfaces referenced verbatim: `work.delegate*`, `review.backend`, per-task `review:`, `spec set-backend`.
- New marker pair `<!-- flow-next:model-routing:start -->` / `<!-- flow-next:model-routing:end -->` — line-based, fence-agnostic (the block contains a markdown table; removal and byte-compare operate on marker lines, never on content parsing).
- `/flow-next:uninstall` (commands/flow-next/uninstall.md — a command file, not a skill dir) removes exactly the marker-fenced block. **Damaged-marker algorithm (deterministic):** exactly one start marker AND exactly one end marker AND start precedes end → remove inclusive; any other state (zero or multiple of either, out of order) → report and leave untouched.

## Edge Cases & Constraints

- Re-run setup after scaffold exists: byte-compare idiom (above) — pristine block silently no-ops; user-customized block gets the Keep-mine question; refresh = choose Overwrite. No mtime bump on identical content (workflow.md discipline).
- Existing user-authored routing section WITHOUT our markers (heading overlap): append our fenced block anyway is WRONG — detect an existing `## Picking models` / model-routing-shaped heading and route to augment-or-skip with a read-back, never duplicate.
- Non-interactive / Ralph / autonomous setup → the ceremony question is skipped silently (default skip); setup must never block.
- Codex mirror must not mention `AskUserQuestion` (existing sync-codex catch-all handles it; never hand-edit `codex/`).
- CLI present-but-unauthenticated: probe stays `command -v` (cheap, deterministic); the runtime failure mode is covered by the block's graceful-degrade rule, not deeper probes.
- Model names and scores are volatile opinions: provenance line + re-rank invitation; read-back frames the block as an editable starting point. Dogfood-and-tweak revises shipped opinions from real use.
- Both-probes-fail → all cross-CLI rows/rules written commented-out with install notes (or ceremony recommends skip); never a silently active route to an unreachable CLI.
- The scaffold block is always-loaded context in every future session of the target repo: hard budget **≤ ~45 lines**. The usage.md section budget stays ≤ ~60 lines.
- CHANGELOG.md currently has no `## Unreleased` header — create it (batched-release rule; no version bump, no `bump.sh`).
- Tasks are SERIALIZED .1 → .2 → .3 → .4 (dependency chain): all four regenerate `plugins/flow-next/codex/**` and .2/.4 both touch `docs/orchestration.md` — serialization removes the parallel-mirror conflict; each task still regenerates the mirror for its own commit.
- File-collision watch (no dependency edges): fn-85 Tier-C setup prose trim and fn-76 smart model resolution both touch `flow-next-setup` files when planned — fn-88 lands first; they rebase. (fn-74's setup edits are already merged; its leftover branch is stale — flagged to user, not a task.)

## Quick commands

```bash
# Gate (all tasks): full suite + smoke + dogfood parity
python3 -m pytest plugins/flow-next/tests -q
bash plugins/flow-next/scripts/smoke_test.sh          # run from OUTSIDE the repo dir
python3 -m pytest plugins/flow-next/tests/test_dogfood_template_parity.py -q

# After ANY canonical skill/template edit — regenerate the Codex mirror
./scripts/sync-codex.sh

# Verify the scaffold block parses + probes behave (manual smoke)
grep -c 'flow-next:model-routing' plugins/flow-next/skills/flow-next-setup/templates/model-routing-snippet.md
```

## Strategy Alignment

Active tracks served by this plan:
- **Cross-platform parity** — the ceremony question rides the existing sync-codex AskUserQuestion transform; templates mirror wholesale; harness-relative bridge recipes are written for all first-class hosts.
- **Ralph autonomous mode** — the scaffolded routing rules are exactly what pilot/land/Ralph read from CLAUDE.md every tick; the non-interactive skip + never-pre-set-consent guards keep the autonomy consent boundary intact.
- **Spec-driven team patterns** — the routing block is a handover object for the whole team: one member scaffolds it, every member's sessions inherit the same routing policy.

## Acceptance Criteria

- **R1:** `templates/usage.md` gains `## Orchestration & model steering`: agentic headless-bridge instructions — `codex exec` (read-only default sandbox called out, `--sandbox workspace-write` for implementation, `-o` output capture, stdin `</dev/null` guard, self-contained-prompt discipline, digest-back, never-touches-git) and `cursor-agent` (`-p`, `--force` to apply edits, `CURSOR_API_KEY`, volatile model IDs via `--list-models`), harness-relative wording — plus `delegate:codex` quickstart, `review.backend` one-liners + per-task `review:` example, ≥2 prompted-orchestration examples (per-item complexity routing; conditional escalation), links to `docs/orchestration.md` and `https://flow-next.dev/orchestration/`; section ≤ ~60 lines, inserted as a top-level section AFTER the `## Common Commands` fence closes — markdown fences remain balanced.
- **R2:** Setup ceremony gains one optional question (joining the existing grouped-question mechanics) offering the model-routing scaffold; frozen options `scaffold` / `scaffold + enable codex delegation` (only when `HAVE_CODEX=1`) / `skip` (default); non-interactive/headless paths skip silently.
- **R3:** On any would-write path (fresh scaffold, or Overwrite chosen on drift) the composed block (probes applied) is shown in FULL before writing (options `write`/`skip`) — the identical-no-op path shows nothing (compare before read-back); the write lands between explicit start/end markers with a provenance line whose invocation syntax is platform-correct (`/flow-next:setup` vs `$flow-next-setup`); a post-write confirmation invites free editing. Never a silent write.
- **R4:** Block content is the full opinionated example — scores table (cost/intelligence/taste) + how-to-apply rules + flow-next surface wiring (worker/`delegate:codex`, review backends incl. per-task `review:`, scouts-may-shell-out-to-cursor-agent, thin-wrapper pattern for gpt-5.5 inside subagents) + graceful-degrade rule — single-sourced in `templates/model-routing-snippet.md`. The escalation rule is always included. Every CLI-dependent route sits on its own sentinel-prefixed line (`<!-- probe:codex -->` / `<!-- probe:cursor -->`); probe-failed CLI lines appear only commented-out with an install note.
- **R5:** `scripts/sync-codex.sh` regenerates cleanly: ceremony question rendered via the plain-text numbered-prompt transform, no `AskUserQuestion` mention in the mirror, full validation suite green.
- **R6:** `/flow-next:uninstall` removes the marker-fenced block via the deterministic damaged-marker algorithm (exactly-one-start + exactly-one-end + ordered → remove inclusive; else report + untouched).
- **R7:** Repo-local: `docs/orchestration.md` gains the "in your repo" pointer (usage.md section + setup step) and the CHANGELOG entry is staged under a new `## Unreleased` header (no version bump — batched release per CLAUDE.md). Downstream (separate repo, executed at the batched release): the CHANGELOG Unreleased entry carries an explicit `Downstream (at release):` line naming the flow-next.dev orchestration-page + skills/setup-page pointer edits — the tracked handoff artifact for the release walk.
- **R8:** Tests, all deterministic: (a) prose-contract tests on workflow.md — headless-skip rule present, frozen option strings present, "never pre-set `work.delegateConsent`" present, scaffold processing ordered after the Docs block; (b) probe-composition tests — template sentinel shape asserted + a reference line-transform validates all four HAVE_CODEX×HAVE_CURSOR states leave no active route to a failed-probe CLI; (c) uninstall marker-removal incl. every damaged-marker no-op case, PLUS prose-contract assertions on `uninstall.md` itself (both marker strings present, exactly-one-start/end + ordered rule stated, damaged states report-and-leave-untouched stated, report line extended). Prose-only review is NOT acceptable coverage for any of these. `smoke_test.sh` + full pytest green.
- **R9:** Delegation opt-in may set `work.delegate codex` but never pre-sets `work.delegateConsent` (first-use consent gate verified still live).
- **R10:** Probe-annotation invariant: rules/rows referencing a CLI that failed `command -v` at scaffold time are commented-out with an install note — no silently active route to an unreachable CLI. Enforced structurally: one route per line, probe sentinels (`<!-- probe:codex -->` / `<!-- probe:cursor -->`), composition = deterministic line transform.
- **R11:** Re-run idempotency: marker presence is the state — byte-compare against the CURRENT composed canonical (today's probe state); identical = silent no-op (no mtime bump); different (user edits OR probe-state drift) = `Keep mine (Recommended)` / `Overwrite with canonical` / `skip`; no new config key.
- **R12:** Target-file resolution is the deterministic ladder: Docs answer this run (incl. Both) → existing `BEGIN FLOW-NEXT` marker location(s) → platform-default mapping (Droid-with-Claude / Cursor buckets). Shim guard uses the exact patterns (`@<path>.md` / `See[:] <path>.md`, single non-empty content line, repo-relative, target must exist) — follow or report + skip, never a mixed file.
- **R13:** The scaffold block is ≤ ~45 lines including markers and provenance.
- **R14:** Repo-root `.flow/usage.md` is updated byte-identically in the same commit as `templates/usage.md` (`test_dogfood_template_parity.py` green).
- **R15:** `docs/orchestration.md` "Durable routing" section stops re-embedding the full example: trimmed illustrative excerpt + cross-link to `templates/model-routing-snippet.md` as the canonical scaffold (R17 cross-link discipline).

## Boundaries

Out of scope, deliberately: no routing engine or automatic model switching; no new flowctl commands or config keys; no conditionals added to any other skill (work/pilot/review skills unchanged); no per-skill model parameters; no new review-backend registry rungs (a `fable` reviewer stays a prompted arrangement, not a rung); no CI enforcement of routing; no changes to the Codex-mirror model mapping; no deeper-than-`command -v` CLI health probes; flow-next.dev docs-site edits land in that repo at ship time (tracked as R7's downstream half, not a task file here).

## Decision Context

Three alternatives rejected. (a) A new `/flow-next:orchestrate` skill — adds command surface for what prompting already does; the 2.7.2 doc proves the host executes routing policy from plain instructions. (b) Routing conditionals inside each skill honoring a config table — high maintenance across 28 skills, contradicts the skill-driven architecture rule (host agent is the intelligence), and prompted orchestration already reaches everything it would add. (c) Docs-only status quo — use-time discoverability is zero; agents read `.flow/usage.md` and instruction files, not the plugin's doc tree. usage.md is the lowest-effort surface agents already read every session; setup is the one moment flow-next already writes instruction files with consent machinery in place, so the scaffold rides existing rails. Marker-fencing follows the proven augment/uninstall-safety pattern rather than heading-heuristics.

The scaffold's shape went through two design rounds. Round 1 rejected copying the docs' example verbatim over the *fake-authority* concern: an instruction-file routing section executes as user authority, so pre-filled content risks asserting policy the user never stated and routing to CLIs that aren't installed. Round 2 (a rules-only, no-scores, generated-from-answers block) was then overturned by user decision (2026-07-05): a **full opinionated example with scores** is deliberately chosen because a filled-in table the user can react to and edit beats an empty one they must author — maximal agentic leverage by default, dogfood-and-tweak after. The authority concern is resolved at the mandatory **read-back**: setup shows the exact block and invites overwrite, which *is* the moment the content becomes the user's policy. The two guards that survive from round 1 — probe-annotation (no silently active route to a missing CLI) and never pre-setting delegation consent — cover the two failure modes prompting can't fix after the fact. The flow-next wiring block is the differentiator over generic field examples: it names the exact surfaces (worker, review backends, scouts, thin-wrapper) each rule drives, so the host can execute the policy without archaeology.

Plan-time resolutions (gap analysis 2026-07-05): marker-presence-as-state chosen over a new config key (one less surface, matches the Docs-block idiom); target-file resolution delegated to the existing Docs-ceremony mapping rather than a new platform table (single source for a solved problem); `command -v`-only probes kept with runtime graceful-degrade in the block itself (deeper auth probes are slow, flaky, and still race first use); the docs' inline example de-embedded in favor of the template file (R17 — two independently drifting "opinionated tables" was the alternative).

## Early proof point

Task fn-88.2 (the canonical `model-routing-snippet.md` template) validates the core bet: that the full opinionated example — scores + rules + flow-next wiring + graceful degrade + annotations — fits ≤ ~45 always-loaded lines and reads as executable policy. If it can't hit budget without losing the wiring, re-evaluate the scaffold shape (split into block + on-demand reference) before building the ceremony around it.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | usage.md orchestration section (bridge recipes + shortcuts + examples) | fn-88.1 | — |
| R2  | Optional ceremony question, frozen options, headless skip | fn-88.3 | — |
| R3  | Pre-write read-back + marker write + post-write invitation | fn-88.3 | — |
| R4  | Opinionated block content, single-sourced template | fn-88.2 | — |
| R5  | sync-codex mirror clean | fn-88.1–.4 (each regen) + fn-88.4 (final) | — |
| R6  | Uninstall marker removal | fn-88.4 | — |
| R7  | Docs pointer + CHANGELOG Unreleased + downstream handoff line | fn-88.4 (repo-local half + handoff line) | flow-next.dev edits execute at the batched release, driven by the handoff line |
| R8  | Test coverage (ceremony skip, probes, uninstall) | fn-88.4 | — |
| R9  | Delegation opt-in sets work.delegate only, never consent | fn-88.3 | — |
| R10 | Probe-annotation invariant | fn-88.2 (template comments) + fn-88.3 (probe wiring) | — |
| R11 | Re-run idempotency via marker byte-compare | fn-88.3 | — |
| R12 | Target-file resolution (Docs mapping, Both, shim guard) | fn-88.3 | — |
| R13 | Block ≤ ~45 lines | fn-88.2 | — |
| R14 | Dogfood parity same-commit | fn-88.1 | — |
| R15 | orchestration.md de-embed + cross-link | fn-88.2 | — |
