## Conversation Evidence

> user (turn — 3-part decomposition): "so this would be a 3 parter perhaps, 1. wrap clawpatch map including the install etc. in a new flow-next:map skill 2. scouts can use the map as additional help for context gathering? agents.md/claude.md perhaps too a short mention of the map 3. prime could suggest using it if a similar map doesn't exist?"

> user (turn — capture command): "capture as fn-50 off main then get back to fn-49"

> earlier in session (paraphrased from clawpatch deep-dive in `~/work/agent-scripts/autoreview-analysis.md` §6.5): clawpatch is openclaw's flagship review-and-patch CLI (667⭐, 99 forks). Its `map` command walks the repo via `src/detect.ts` (~61 KB) to produce semantic feature slices across ~20 languages/frameworks — npm bins, Next.js routes, Python packages, Flask/FastAPI/Django, Rails, Laravel, JVM (Gradle/Maven), .NET, Go, Rust, C/C++, SwiftPM, Elixir Phoenix. Output persists under `.clawpatch/features/*.json` and is consumed by `clawpatch review` and `clawpatch fix`. Standalone Node 22+ CLI, MIT, installable via `pnpm add -g clawpatch`.

## Goal & Context
<!-- Source-tag breakdown: 55% [user], 45% [paraphrase] -->

flow-next's scouts (`repo-scout`, `context-scout`) currently derive "what's in this codebase" via ad-hoc grep + glob during `/flow-next:plan` and `/flow-next:capture`. [paraphrase] When a richer pre-computed feature index exists, scouts could anchor R-IDs and decision-context references to concrete semantic boundaries rather than re-deriving them from raw text. [user] (turn — "additional help for context gathering")

openclaw/clawpatch already does this work in a battle-tested 20-language mapper. [paraphrase] Wrapping it (not porting it) gives flow-next that signal cheaply via a new skill that calls clawpatch CLI through a thin shell-out. [user] (turn — "wrap clawpatch map ... in a new flow-next:map skill")

The key constraint: this must remain an **opt-in convenience**, not a flow-next core dependency. Users who don't install clawpatch see no change in behavior; users who do install it get scout enrichment for free. [user] (turn — "if a similar map doesn't exist") / [paraphrase]

## Architecture & Data Models
<!-- Source-tag breakdown: 100% [paraphrase] -->

Three independent surfaces, sequenced so Part 1 unlocks Parts 2 and 3:

**Part 1 — `/flow-next:map` skill (foundational):**
- New skill in `plugins/flow-next/skills/flow-next-map/`. Wraps the `clawpatch` CLI via shell-out, similar to how `/flow-next:resolve-pr` wraps `gh`.
- Install handling: detect via `which clawpatch` + `clawpatch doctor`; if missing, surface `pnpm add -g clawpatch` instructions and exit cleanly. **No auto-install** — Node toolchain is the user's choice.
- Init handling: if `.clawpatch/` is absent, the skill runs `clawpatch init` first (one less manual step). Writes a `.clawpatch/.gitignore` skeleton (or a `.clawpatch/` entry in repo `.gitignore` — implementer picks) so machine-generated map data isn't accidentally committed.
- New flowctl reader: thin `flowctl repo-map list / show / since-ref` subcommands that parse `.clawpatch/features/*.json` and return structured output for scouts to consume. **No state duplication into `.flow/`** — feature data ages with code, not with flow-next state.

**Part 2 — Scout enrichment + agents.md/CLAUDE.md mention:**
- `repo-scout.md` and `context-scout.md` (under `plugins/flow-next/agents/`) gain a `.clawpatch/features/` read step: when present, parse feature index; when absent, fall back to current grep/glob flow. **Scouts must remain useful without the map** — the fallback contract is load-bearing.
- Scout output schema gains an optional `features_anchored: [...]` field. Downstream consumers (`/flow-next:plan`, `/flow-next:capture`) read it if present, ignore it if absent.
- `CLAUDE.md` (root) and `plugins/flow-next/skills/flow-next-setup/templates/{claude-md-snippet,agents-md-snippet}.md` gain a one-paragraph optional-add under "Where to look" describing `/flow-next:map` as an optional discoverability aid. Not a setup step; surface as recommended-but-not-required.

**Part 3 — Prime sub-criterion (discoverability nudge):**
- `/flow-next:prime` (`plugins/flow-next/skills/flow-next-prime/`) adds one sub-criterion under Pillar 5 (agent-readiness): *"Codebase feature map present? — `/flow-next:map` recommended for richer scope anchoring (optional)"*.
- Detection: `[[ -d .clawpatch ]]` + `flowctl repo-map list --count` returning > 0.
- Reporting: soft ❌ (not a blocker) → surface `/flow-next:map` as the actionable suggestion in the prime report. **No auto-run** — prime stays read-only on this dimension.
- Prime's "fix agent-readiness only" rule already permits this — the surfaced suggestion is documentation, not mutation.

Cross-platform: clawpatch requires Node 22+ (pnpm-installable). Same matrix as flow-next's Copilot Windows path (works on macOS / Linux / Windows / WSL wherever a Node toolchain is available). Mirror in `plugins/flow-next/docs/platforms.md` if needed.

## Edge Cases & Constraints
<!-- Source-tag breakdown: 100% [paraphrase] -->

- **Zero-deps STRATEGY.md track preservation.** The wrap is a skill convenience, NOT a flowctl core dependency. flowctl never imports or requires clawpatch. The skill itself is the only surface that touches clawpatch. Uninstall promise stays intact — `rm -rf .flow/` removes flow-next; `rm -rf .clawpatch/` removes the map; nothing entangled.
- **Scout fallback is non-negotiable.** A scout that depends on `.clawpatch/` being present is broken on every project where the user hasn't opted into the map. Fallback paths must be tested explicitly, not assumed.
- **Upstream maintenance risk.** clawpatch is 11 days old at spec time (created 2026-05-15). The wrap should pin a tested version range in skill prose, surface the version mismatch when `clawpatch --version` returns something outside the range. If clawpatch ever rebrands or goes unmaintained, removing the skill is a clean revert (no flow-next core code depends on it).
- **`.clawpatch/.gitignore` vs repo `.gitignore`.** Implementer choice — both work. Document the choice in the skill prose so users know where to look if files surprise them.
- **Map staleness.** `.clawpatch/features/*.json` ages with the code. The skill should surface "last mapped: <timestamp>" in its status output; scouts that read stale data should warn (or auto-suggest re-mapping if the diff since last map is large).
- **No spec linkage shoehorn.** Feature anchors enrich scope; they do NOT replace R-IDs, acceptance criteria, or spec structure. flow-next stays spec-first; the map is supplementary context, not a competing scope model.
- **`/flow-next:prime` pillar count.** Currently 8 pillars / 48 criteria. This adds one sub-criterion under Pillar 5 — 8 pillars / 49 criteria. No pillar restructure.

## Acceptance Criteria
<!-- Source-tag breakdown: 40% [user], 60% [paraphrase] -->

- **R1:** New `/flow-next:map` skill exists at `plugins/flow-next/skills/flow-next-map/`. Detects `clawpatch` availability via `which clawpatch` + `clawpatch doctor`. When missing, prints `pnpm add -g clawpatch` install instructions and exits cleanly (no auto-install). [user] (turn — "wrap clawpatch map including the install etc.") / [paraphrase]
- **R2:** Skill runs `clawpatch init` automatically when `.clawpatch/` is absent and writes a `.clawpatch/.gitignore` skeleton (or appends a `.clawpatch/` entry to repo `.gitignore` — implementer choice, documented in skill prose). [paraphrase]
- **R3:** New `flowctl repo-map list / show / since-ref` subcommands read native `.clawpatch/features/*.json` and return structured output (text + `--json`). State location is native `.clawpatch/`; no duplication into `.flow/`. [user] (turn — "thin reader") / [paraphrase]
- **R4:** `repo-scout` and `context-scout` agents read `.clawpatch/features/` when present and emit an optional `features_anchored: [...]` field in their structured output. Downstream consumers (`/flow-next:plan`, `/flow-next:capture`) read the field if present, ignore it if absent. [user] (turn — "scouts can use the map") / [paraphrase]
- **R5:** **Fallback contract (load-bearing):** scouts remain useful and produce structured output with the current grep/glob flow when `.clawpatch/` is absent. The `features_anchored` field is omitted or empty in that case. Verified by a smoke test that runs scouts against a project without `.clawpatch/`. [user] (turn — "additional help for context gathering" implies non-mandatory) / [paraphrase]
- **R6:** Root `CLAUDE.md` AND `plugins/flow-next/skills/flow-next-setup/templates/{claude-md-snippet,agents-md-snippet}.md` gain a one-paragraph optional-add under "Where to look" (or equivalent section) mentioning `/flow-next:map` as a discoverability aid. Setup-template changes propagate to existing user repos via the fn-45.3 byte-compare gate. [user] (turn — "agents.md/claude.md perhaps too a short mention") / [paraphrase]
- **R7:** `/flow-next:prime` adds exactly one sub-criterion under Pillar 5 (agent-readiness): *"Codebase feature map present? — `/flow-next:map` recommended for richer scope anchoring (optional)"*. Detection: `[[ -d .clawpatch ]]` + `flowctl repo-map list --count` > 0. Reporting: soft ❌ surfaces `/flow-next:map` as the actionable suggestion. **No auto-run.** Prime's pillar count stays at 8; criterion count becomes 49. [user] (turn — "prime could suggest using it if a similar map doesn't exist") / [paraphrase]
- **R8:** Cross-platform parity verified: the skill works on macOS, Linux, and Windows (including WSL) wherever Node 22+ is available, matching the documented matrix in `plugins/flow-next/docs/platforms.md`. [paraphrase]

## Boundaries
<!-- Source-tag breakdown: 70% [user], 30% [paraphrase] -->

In scope:
- The new `/flow-next:map` skill (Part 1).
- Scout-level integration of the map for `repo-scout` and `context-scout` (Part 2).
- The single sub-criterion addition to `/flow-next:prime` (Part 3).
- agents.md / CLAUDE.md / setup-template prose updates surfacing the skill.

Out of scope (the explicit non-goals):
- **Porting clawpatch's mapper into flowctl Python.** The wrap is the architectural choice — ~weeks-to-months port + ongoing maintenance burden + divergence from upstream would all defeat the "cheap opt-in convenience" framing. [paraphrase] (See `~/work/agent-scripts/autoreview-analysis.md` §6.5.9 for the porting-vs-wrapping trade-off.)
- **Replacing flow-next's spec-first scope model.** Feature anchors enrich `Where to look`, `Investigation targets`, and Critical changes sections; they do NOT replace R-IDs, acceptance criteria, or spec structure. flow-next stays spec-first. [paraphrase]
- **Auto-running `/flow-next:map`** from prime, capture, plan, or work. The user invokes it. Prime surfaces a suggestion; no other skill triggers a run. [user] (turn — "prime could suggest using it") / [paraphrase]
- **Make-pr / resolve-pr integration.** Feature-anchored Critical changes and feature-clustered resolve-pr cluster analysis are documented as future-work in `~/work/agent-scripts/autoreview-analysis.md` §6.5; not part of this spec. Land scout enrichment first; downstream consumers come later.
- **Memory category for features.** Tempting (`knowledge/features/<name>.md`) but over-engineering. Scouts consume the map ephemerally; no new memory category. [paraphrase]
- **Multi-mapper abstraction.** Only clawpatch today. If a second mapper appears later (e.g. a Tree-sitter-based native flow-next mapper), the skill can grow a `--provider` flag then. Not now. [paraphrase]
- **CI/CD integration of `/flow-next:map`.** `clawpatch ci` exists upstream but is the user's CI choice, not flow-next's concern.

## Decision Context

### Motivation
<!-- Source-tag breakdown: 50% [user], 50% [paraphrase] -->

Prioritization: Part 1 (skill wrap) unlocks Parts 2 (scout enrichment) and 3 (prime nudge); Parts 2 and 3 can land in parallel after Part 1. [user] (turn — "3 parter") The skill wrap is the highest-leverage step because every downstream consumer needs the same `clawpatch` plumbing — building it once at the skill layer prevents N consumers from each shelling out to clawpatch ad-hoc.

Why wrap rather than port: clawpatch's `src/detect.ts` is ~61 KB of detector code across ~20 languages, actively iterated (11 days old at spec time, 9 open issues, 99 forks). Porting that into flowctl Python would be a multi-week effort that immediately starts diverging from upstream. The wrap is ~200-300 lines of skill + flowctl reader code and stays in sync automatically. [paraphrase]

Why opt-in (not flowctl core): STRATEGY.md commits to "zero external dependencies" and the `rm -rf .flow/` uninstall promise. [user] (the strategy track) Folding clawpatch into flowctl as a hard dep would break both. The opt-in skill framing — user chooses to install clawpatch, scouts gracefully degrade without it — preserves both invariants while still delivering the enrichment when it's available. [paraphrase]

Why prime nudge is soft (not blocker): the map is genuinely optional. A repo without `.clawpatch/` is still agent-ready by every other prime criterion — scouts work, planning works, work works, review works. The prime nudge is a discoverability surface, not a quality gate. [user] (turn — "could suggest") / [paraphrase]

## Strategy Alignment

Active tracks served by this spec:
- **Spec-driven team patterns** — scout enrichment makes R-ID anchoring and `Investigation targets` sharper at the spec-authoring stage. Better feature visibility → tighter spec scope → less drift downstream.
- **Cross-platform parity** — the wrap mechanism matches the existing platform matrix (macOS / Linux / Windows / WSL wherever the host toolchain is available). Adds a Node 22+ requirement only for users who opt into the skill.

No drift flagged.

## Quick commands

```bash
# Part 1 — skill smoke (after fn-50 lands):
/flow-next:map                                           # detect + init + map (interactive)
.flow/bin/flowctl repo-map list --json                  # read parsed feature index
.flow/bin/flowctl repo-map show --feature <id> --json   # inspect one feature
.flow/bin/flowctl repo-map since-ref origin/main --json # features touched since ref

# Part 2 — scout integration verify:
# Run /flow-next:plan against a project WITH .clawpatch/ → confirm scout output has features_anchored
# Run /flow-next:plan against a project WITHOUT .clawpatch/ → confirm scout output unchanged (no features_anchored field)

# Part 3 — prime sub-criterion verify:
/flow-next:prime    # Pillar 5 should show: "Codebase feature map present? ❌ — /flow-next:map recommended (optional)"
```

---

## Requirement coverage

| R-ID | Task(s) |
|------|---------|
| R1 | fn-N.M (TBD — populate via /flow-next:plan) |
| R2 | fn-N.M (TBD — populate via /flow-next:plan) |
| R3 | fn-N.M (TBD — populate via /flow-next:plan) |
| R4 | fn-N.M (TBD — populate via /flow-next:plan) |
| R5 | fn-N.M (TBD — populate via /flow-next:plan) |
| R6 | fn-N.M (TBD — populate via /flow-next:plan) |
| R7 | fn-N.M (TBD — populate via /flow-next:plan) |
| R8 | fn-N.M (TBD — populate via /flow-next:plan) |
