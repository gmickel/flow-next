# Codebase feature map: /flow-next:map skill + scout enrichment + prime nudge

## Conversation Evidence

> user (turn — 3-part decomposition): "so this would be a 3 parter perhaps, 1. wrap clawpatch map including the install etc. in a new flow-next:map skill 2. scouts can use the map as additional help for context gathering? agents.md/claude.md perhaps too a short mention of the map 3. prime could suggest using it if a similar map doesn't exist?"

> user (turn — capture command): "capture as fn-50 off main then get back to fn-49"

> earlier in session (paraphrased from clawpatch deep-dive in `~/work/agent-scripts/autoreview-analysis.md` §6.5): clawpatch is openclaw's flagship review-and-patch CLI (669⭐, 99 forks at plan time; v0.4.0 2026-05-22). `clawpatch map` walks the repo via `src/detect.ts` (~61 KB) to produce semantic feature slices across ~20 languages/frameworks. Output persists at `.clawpatch/features/*.json` (Zod-validated, `schemaVersion: 1`). Standalone Node 22+ CLI, MIT, installable via `pnpm add -g clawpatch`.

## Overview

Wrap openclaw/clawpatch's `clawpatch map` CLI in a new `/flow-next:map` skill, enrich `repo-scout` + `context-scout` to read the resulting feature index, and add one soft sub-criterion to `/flow-next:prime` surfacing the map as a discoverability nudge. Opt-in convenience throughout — `flowctl` core never imports or requires clawpatch; scouts remain useful without `.clawpatch/`.

## Goal & Context

flow-next's scouts (`repo-scout`, `context-scout`) currently derive "what's in this codebase" via ad-hoc grep + glob during `/flow-next:plan` and `/flow-next:capture`. When a richer pre-computed feature index exists, scouts can anchor R-IDs and decision-context references to concrete semantic boundaries rather than re-deriving them from raw text.

openclaw/clawpatch already does this work in a battle-tested 20-language mapper. Wrapping it (not porting it) gives flow-next that signal cheaply via a new skill that calls clawpatch CLI through a thin shell-out.

The key constraint: this must remain an **opt-in convenience**, not a flow-next core dependency. Users who don't install clawpatch see no change in behavior; users who do install it get scout enrichment for free.

## Architecture & Data Models

Three independent surfaces, sequenced so Part 1 unlocks Parts 2 and 3:

**Part 1 — `/flow-next:map` skill (foundational):**
- New skill at `plugins/flow-next/skills/flow-next-map/`. Wraps the `clawpatch` CLI via shell-out — mirrors the `/flow-next:resolve-pr`-wraps-`gh` precedent.
- Install detection: `command -v clawpatch` + `clawpatch --version`. When missing, print upstream-canonical install instructions (`pnpm add -g clawpatch`) verbatim and exit cleanly. **No auto-install.** When pnpm is present but `command -v clawpatch` returns empty after install, print PNPM_HOME `bin/` hint (#1 install failure mode per pnpm v11 changes).
- Version-range guard: skill prose carries a single-source `SUPPORTED_CLAWPATCH` range (initial: `>=0.4.0 <0.5.0`). Outside-range invocations emit one-line stderr warning naming expected vs found, degrade to fallback (still parse `features/*.json`, skip CLI-flag-specific paths), never block.
- Init handling: when `.clawpatch/` is absent, run `clawpatch init` first. Write `.clawpatch/.gitignore` skeleton (self-contained — directory-local file so a full deletion of `.clawpatch/` removes both data and ignore rules in one step).
- **Default `clawpatch map` invocation is provider-free** — `--source heuristic` deterministic mapper, zero LLM calls. `--source auto|agent` is passthrough; the skill MUST NOT require a clawpatch provider configured for default invocation. Skill does NOT proxy flow-next's review backend config (rp/codex/copilot/none) — clawpatch's provider matrix is orthogonal.
- Config-state echo: skill prints active `--source` + `CLAWPATCH_PROVIDER` (if set, else "none/heuristic") + flow-next review backend (informational) on entry header.
- Ralph-block: skill exits cleanly under `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` — install/init interactive prompts make Ralph compat impossible.

**Part 1b — `flowctl repo-map` reader subcommands:**
- New `flowctl repo-map list / show / since-ref` parse `.clawpatch/features/*.json` and return text + `--json`. State location is native `.clawpatch/`; no duplication into `.flow/`.
- These readers BYPASS the `ensure_flow_exists()` guard — they gate on `.clawpatch/` presence instead, returning `count: 0` cleanly when absent so prime's detection check works without special-casing.
- `schemaVersion: 1` enforced; unknown versions emit one-line stderr diagnostic + skip with clean exit; never abort `list`.

**Part 2 — Scout enrichment + agents.md/CLAUDE.md mention:**
- `repo-scout.md` and `context-scout.md` (under `plugins/flow-next/agents/`) gain a `.clawpatch/features/` read step (via `flowctl repo-map list --json` — centralizes schema check). When `.clawpatch/` absent, fall back to current grep/glob flow. **Scouts must remain useful without the map** — fallback contract is load-bearing.
- Scout output schema gains an optional `features_anchored: [...]` field. **Scouts emit the field; downstream skills (`/flow-next:plan`, `/flow-next:capture`) consume scout output as-is in fn-50.** Explicit downstream field handling is future work, tracked separately — not part of this spec.
- Root `CLAUDE.md` AND `plugins/flow-next/skills/flow-next-setup/templates/{claude-md-snippet,agents-md-snippet}.md` gain a one-paragraph optional-add under "Where to look" describing `/flow-next:map` as a discoverability aid. Setup-template changes propagate to existing user repos via the fn-45.3 byte-compare gate — author with tight byte discipline (gate is byte-for-byte including whitespace).

**Part 3 — Prime sub-criterion (discoverability nudge):**
- `/flow-next:prime` (`plugins/flow-next/skills/flow-next-prime/pillars.md`) adds one sub-criterion under **Pillar 5 (Dev Environment)** as criterion ID **`DE7`**: *"Codebase feature map present? — `/flow-next:map` recommended for richer scope anchoring (optional)"*. Pillar 5 is the canonical name (current `pillars.md`); the original capture-time prose calling it "agent-readiness" is the broader Pillars 1-5 group label, not the Pillar 5 name.
- Detection: `[[ -d .clawpatch ]]` + `flowctl repo-map list --count` returning > 0.
- Reporting: soft ❌ (informational, not scored as a hard miss — mirrors the DC7 "informational" precedent at `pillars.md:87`). Surface `/flow-next:map` as actionable suggestion in `Top Recommendations`. **No auto-run.**
- Pillar count stays at 8; **DE7 is informational** (mirrors DC7); **scored criteria stay at 48** (DC7 + DE7 both informational, excluded from baseline); **total criteria become 48 → 49** with DE7 added.

**Cross-platform + release plumbing:** clawpatch requires Node 22+ (pnpm-installable). Skill works on macOS / Linux / Windows / WSL wherever the host shell can resolve `clawpatch`. Skill registration includes (in fn-50.6): `scripts/sync-codex.sh` REQUIRED_OPENAI_YAML_SKILLS entry, `plugin.json` description skill-count bump (23 → 24), `plugins/flow-next/commands/flow-next/map.md` slash-command shim, root README skill table entry, `CHANGELOG.md` entry **staged under `## [Unreleased]`**, and `flow-next.dev` docs-site page (`src/content/docs/skills/map.mdx`) + nav entry + changelog highlight staged under the unreleased section. **Version bumps (`flow-next.dev` `package.json`, `FLOW_NEXT_VERSION`, dated `[flow-next X.Y.Z]` block, plugin.json `version`) are deferred to release-cut — NOT in fn-50.6.**

## Edge Cases & Constraints

- **Zero-deps STRATEGY.md track preservation.** The wrap is a skill convenience, NOT a flowctl core dependency. flowctl never imports or requires clawpatch. The skill itself is the only surface that touches clawpatch. Uninstall promise stays intact — removing `.flow/` removes flow-next; removing `.clawpatch/` removes the map; nothing entangled.
- **No provider required for the default path.** `clawpatch init` and `clawpatch map --source heuristic` are fully deterministic — zero LLM calls, zero API spend, zero review-backend dependency. The `--source auto/agent` provider-backed paths are opt-in within the opt-in.
- **Scout fallback is non-negotiable.** Verification is two-layered (running scout subagents in CI is out of scope): (a) a **static contract test** parses both scout `agents/*.md` files and asserts the fallback prose + schema documentation are present, plus `flowctl repo-map list --json` against a `.clawpatch/`-less fixture returns `count:0` cleanly; (b) a **manual smoke** runs `/flow-next:plan` against a no-`.clawpatch/` repo and confirms scout output is produced cleanly with no `features_anchored` field, logged in the implementing task's Done summary.
- **Schema versioning.** `.clawpatch/features/*.json` carries `schemaVersion: 1`. Readers refuse non-1 with diagnostic — clawpatch is pre-1.0, README forecasts breaking changes between minor releases.
- **clawpatch version pin.** Single source of truth in skill prose (`SUPPORTED_CLAWPATCH=">=0.4.0 <0.5.0"`). Outside-range = warn + degrade, never block. Re-verify on each clawpatch minor.
- **PNPM_HOME PATH pitfall.** pnpm v11 moved global binaries to `$PNPM_HOME/bin/`; users upgrading from pnpm 10 without running `pnpm setup` get the install but no PATH entry. Skill's missing-binary branch detects pnpm-installed-but-not-on-PATH and prints the PNPM_HOME hint.
- **Node 20 user with clawpatch installed.** clawpatch's own `engines.node: ">=22"` triggers the error; skill propagates clawpatch's diagnostic verbatim. No skill-side Node probe.
- **Empty features dir / unparseable JSON.** `flowctl repo-map list` returns `count: 0` on empty; per-file parse errors emit one-line stderr warning and skip without aborting the list.
- **Non-git repo.** clawpatch's `--skip-git-repo-check` is upstream's concern. Skill warns that git-ref features (`since-ref`) unavailable in non-git; default `list/show` still work.
- **Long-running map.** clawpatch streams stdout live (filesystem walk on large repos). Skill does not buffer; no skill-side timeout. Ctrl+C kills cleanly via subprocess group.
- **No opt-out for prime nudge by design.** The soft ❌ format IS the opt-out — informational only, never a blocker. If users object, revisit in a follow-up spec.
- **Map staleness.** `.clawpatch/features/*.json` ages with the code. Scout output includes an optional `features_anchored.last_mapped` timestamp; scouts warn (do not refuse) when stale.
- **No spec linkage shoehorn.** Feature anchors enrich scope; they do NOT replace R-IDs, acceptance criteria, or spec structure. flow-next stays spec-first.
- **`.clawpatch/` ignored at directory level.** Not appended to repo `.gitignore` (decision: cleaner uninstall — directory deletion takes everything with it).
- **fn-48 sequencing.** Hard precondition: fn-48's PR merges before fn-50 implementation work begins. Skill author must follow fn-48's consolidated FLOWCTL prelude + post-split resolve-pr structure.

## Acceptance Criteria

- **R1:** New `/flow-next:map` skill exists at `plugins/flow-next/skills/flow-next-map/`. Detects `clawpatch` via `command -v clawpatch` + `clawpatch --version`. When missing, prints `pnpm add -g clawpatch` install instructions verbatim and exits cleanly (no auto-install). **Default invocation passes `--source heuristic` (provider-free) and works without any clawpatch provider configured**; `--source auto|agent` is exposed as passthrough.
- **R2:** Skill runs `clawpatch init` automatically when `.clawpatch/` is absent and writes a `.clawpatch/.gitignore` skeleton (self-contained inside `.clawpatch/`; repo `.gitignore` not touched).
- **R3:** New `flowctl repo-map list / show / since-ref` subcommands read native `.clawpatch/features/*.json` and return text + `--json`. State location is native `.clawpatch/`; no duplication into `.flow/`. Readers BYPASS the `ensure_flow_exists()` guard — gate on `.clawpatch/` presence instead; return `count: 0` with exit 0 when absent.
- **R4:** `repo-scout` and `context-scout` agents call `flowctl repo-map list --json` when `.clawpatch/` is present and emit an optional `features_anchored: [...]` field in their structured output. Field includes `last_mapped` timestamp for staleness awareness. The field is purely additive scout-level enrichment in this spec — downstream skills (`/flow-next:plan`, `/flow-next:capture`) consume scout output as-is and gain no explicit `features_anchored` handling in fn-50. Future work may wire downstream consumers explicitly; tracked separately.
- **R5:** **Fallback contract (load-bearing):** scouts remain useful and produce structured output with the current grep/glob flow when `.clawpatch/` is absent. The `features_anchored` field is omitted or empty in that case. Verified via a two-layer approach (running scout subagents in CI is out of scope): (a) **static contract test** at `plugins/flow-next/tests/test_scout_fallback_contract.py` asserts the fallback prose + `features_anchored` schema documentation are present in both `agents/*.md` files and that `flowctl repo-map list --json` against a `.clawpatch/`-less fixture returns `count:0` cleanly; `plugins/flow-next/tests/scout-fallback.sh` is a thin bash wrapper that invokes the Python test for uniform test-runner entry; (b) **manual smoke** running `/flow-next:plan` against this no-`.clawpatch/` repo confirms scout output produced cleanly with no `features_anchored` field, logged in the implementing task's Done summary.
- **R6:** Root `CLAUDE.md` AND `plugins/flow-next/skills/flow-next-setup/templates/{claude-md-snippet,agents-md-snippet}.md` gain a one-paragraph optional-add under "Where to look" mentioning `/flow-next:map` as a discoverability aid. The two setup-template files are byte-identical to the same canonical snippet text (modulo `/flow-next:map` vs `$flow-next-map` syntax for CLAUDE/AGENTS convention); fn-45.3 byte-compare gate propagates on next `/flow-next:setup` in user repos.
- **R7:** `/flow-next:prime` adds exactly one sub-criterion under **Pillar 5 (Dev Environment)** as criterion ID **`DE7`**: *"Codebase feature map present? — `/flow-next:map` recommended for richer scope anchoring (optional)"*. Detection: `[[ -d .clawpatch ]]` + `flowctl repo-map list --count` > 0. Reporting: soft ❌ (informational, not a hard miss); surfaces `/flow-next:map` in Top Recommendations. **No auto-run.** **DE7 is informational** (mirrors the DC7 pattern at `pillars.md:87`): pillar count stays at 8, **scored criteria stay at 48** (DC7 + DE7 both informational, excluded from baseline), and **total criteria become 48 → 49** with DE7 added.
- **R8:** Cross-platform parity verified: skill works on macOS, Linux, and Windows (including WSL) wherever Node 22+ is available, matching `plugins/flow-next/docs/platforms.md`. Platforms.md gains an "Optional skill requirements" paragraph for the Node 22+ requirement, scoped to `/flow-next:map` only.
- **R9:** `flowctl repo-map *` readers refuse `.clawpatch/features/*.json` entries with `schemaVersion != 1`, emit a one-line stderr diagnostic naming expected vs found version, and skip the offending file (never abort the full `list`). Unparseable JSON triggers the same skip-with-diagnostic path.
- **R10:** Skill carries a single-source `SUPPORTED_CLAWPATCH` version range (initial value `>=0.4.0 <0.5.0`) in skill prose. When `clawpatch --version` falls outside, skill prints a one-line stderr warning naming expected vs found and continues (degrades — never blocks).
- **R11:** Missing-binary branch (R1) probes pnpm-installed-but-not-on-PATH (`pnpm bin -g` exit-0 + `command -v clawpatch` exit non-zero) and prints PNPM_HOME `bin/` setup hint (run `pnpm setup`, re-source shell rc) when divergence detected.
- **R12:** Skill prints active config state on entry header (one block, four lines): clawpatch version + `--source`, `CLAWPATCH_PROVIDER` env (or "none"), flow-next review backend (informational), `.clawpatch/` last-mapped timestamp (or "absent").
- **R13:** Skill exits cleanly under Ralph (`FLOW_RALPH=1` OR `REVIEW_RECEIPT_PATH` set) with non-zero exit code and a one-line stderr diagnostic naming the trigger var. The skill **does NOT write to `$REVIEW_RECEIPT_PATH`** — the receipt belongs to whatever upstream review is using it; the Ralph-block is decline-to-run only, not a receipt producer. No `AskUserQuestion` blocks fire under Ralph — install/init prompts are unreachable.
- **R14:** `flow-next-map` registered in `scripts/sync-codex.sh` REQUIRED_OPENAI_YAML_SKILLS array; Codex mirror regenerated cleanly under `plugins/flow-next/codex/`; `plugins/flow-next/commands/flow-next/map.md` slash-command shim exists.
- **R15:** Release plumbing complete (this task lands the artefacts; version bumps are deliberately deferred to release-cut, NOT in this task): (a) `plugin.json` description string **skill-count bumped `23 → 24`**; scored-criterion count stays `48` (DE7 informational); description prose may add "(+1 informational)" if needed for clarity, (b) `marketplace.json` description re-checked, (c) root `README.md` skill table row added (or "Optional / enrichment" subsection if introduced), (d) CHANGELOG entry under `## [Unreleased]` (NOT under a specific version block — release skill cuts the version), (e) `~/work/flow-next.dev` updates: new `src/content/docs/skills/map.mdx`, nav entry in `src/lib/site.ts` Skills → Maintenance group. **Out of scope for this task:** flow-next.dev `FLOW_NEXT_VERSION` + `package.json` version bumps and dated `[flow-next X.Y.Z]` changelog block — those happen at release-cut time after fn-50 merges, not in fn-50.6 itself. Docs-site changelog "highlight" entry is staged under an Unreleased section for the release cut to date-and-version.

## Boundaries

In scope:
- The new `/flow-next:map` skill (Part 1).
- `flowctl repo-map list/show/since-ref` reader subcommands (Part 1b).
- Scout-level integration of the map for `repo-scout` and `context-scout` (Part 2).
- The single `DE7` sub-criterion addition to `/flow-next:prime` (Part 3).
- agents.md / CLAUDE.md / setup-template prose updates surfacing the skill.
- Cross-platform parity + release-plumbing + Codex-mirror sync.

Out of scope (the explicit non-goals):
- **Porting clawpatch's mapper into flowctl Python.** The wrap is the architectural choice. (See `~/work/agent-scripts/autoreview-analysis.md` §6.5.9 for the porting-vs-wrapping trade-off.)
- **Replacing flow-next's spec-first scope model.** Feature anchors enrich `Where to look`, `Investigation targets`, and Critical changes; they do NOT replace R-IDs, acceptance criteria, or spec structure.
- **Auto-running `/flow-next:map`** from prime, capture, plan, or work. The user invokes it. Prime surfaces a suggestion; no other skill triggers a run.
- **Make-pr / resolve-pr feature-anchored output.** Documented as future-work in `~/work/agent-scripts/autoreview-analysis.md` §6.5; not part of this spec.
- **Memory category for features.** Tempting (`knowledge/features/<name>.md`) but over-engineering. Scouts consume the map ephemerally; no new memory category.
- **Multi-mapper abstraction.** Only clawpatch today. If a second mapper appears later, the skill can grow a `--provider` flag then.
- **CI/CD integration of `/flow-next:map`.** `clawpatch ci` exists upstream but is the user's CI choice.
- **Wiring `--source agent` into flow-next's review backend resolution.** clawpatch's provider matrix (codex/acpx/claude/cursor/grok/opencode/pi) is orthogonal to flow-next's review backend config. The skill exposes `--source` as passthrough; users configure clawpatch's provider directly via `CLAWPATCH_PROVIDER` env or its own config.
- **Auto-upgrade to `--source auto` when deterministic coverage is "weak."** Skill stays heuristic-by-default; users opt up explicitly.
- **Opt-out flag for the prime nudge.** Soft ❌ informational format IS the opt-out by design.

## Decision Context

### Motivation

Prioritization: Part 1 (skill wrap) unlocks Parts 2 (scout enrichment) and 3 (prime nudge); Parts 2 and 3 can land in parallel after Part 1. The skill wrap is the highest-leverage step because every downstream consumer needs the same `clawpatch` plumbing — building it once at the skill layer prevents N consumers from each shelling out to clawpatch ad-hoc.

Why wrap rather than port: clawpatch's `src/detect.ts` is ~61 KB of detector code across ~20 languages, actively iterated (11 days old at spec time, 9 open issues, 99 forks). Porting that into flowctl Python would be a multi-week effort that immediately starts diverging from upstream. The wrap is ~200-300 lines of skill + flowctl reader code and stays in sync automatically.

Why opt-in (not flowctl core): STRATEGY.md commits to "zero external dependencies" and the uninstall promise (removing `.flow/` takes flow-next with it). Folding clawpatch into flowctl as a hard dep would break both. The opt-in skill framing — user chooses to install clawpatch, scouts gracefully degrade without it — preserves both invariants while still delivering the enrichment when it's available.

Why prime nudge is soft (not blocker): the map is genuinely optional. A repo without `.clawpatch/` is still agent-ready by every other prime criterion. The nudge is a discoverability surface, not a quality gate.

### Decision lock-ins (planner picks, not implementer)

1. **`.clawpatch/.gitignore` is self-contained** (not repo `.gitignore` append). Cleaner uninstall: deleting `.clawpatch/` removes both data and ignore rules.
2. **Scouts call `flowctl repo-map list --json`**, not direct JSON parse. Centralizes schema-version check.
3. **Version-pin constant lives in skill prose** (`SUPPORTED_CLAWPATCH=">=0.4.0 <0.5.0"`). Single source. flowctl reader stays version-agnostic; skill is the gate.
4. **Test strategy: checked-in fixtures.** `plugins/flow-next/tests/fixtures/clawpatch-map/` carries valid + invalid + stale fixture files; tests never shell `clawpatch`. CI doesn't need Node 22+.
5. **R6 + R1 land together** (same PR or strict ordering). Avoids dead-reference window where CLAUDE.md mentions a non-existent skill.

## Strategy Alignment

Active tracks served by this spec:
- **Spec-driven team patterns** — scout enrichment makes R-ID anchoring and `Investigation targets` sharper at the spec-authoring stage. Better feature visibility → tighter spec scope → less drift downstream.
- **Cross-platform parity** — the wrap mechanism matches the existing platform matrix. Adds a Node 22+ requirement only for users who opt into the skill.

No drift flagged.

## Quick commands

```bash
# Hard precondition: fn-48 PR merged first.

# Part 1 — skill smoke (after R1/R2 land):
/flow-next:map                                            # detect + init + map (interactive default)
/flow-next:map --source=auto                              # opt-in provider path
.flow/bin/flowctl repo-map list --json                    # read parsed feature index
.flow/bin/flowctl repo-map show --feature <id> --json     # inspect one feature
.flow/bin/flowctl repo-map since-ref origin/main --json   # features touched since ref

# Part 2 — scout integration verify:
bash plugins/flow-next/tests/scout-fallback.sh             # smoke fixture-based fallback contract

# Part 3 — prime sub-criterion verify:
/flow-next:prime    # Pillar 5 should show: "DE7: Codebase feature map present? ❌ — /flow-next:map recommended (optional)"

# Release plumbing:
bash scripts/sync-codex.sh                                 # regenerate Codex mirror
cd ~/work/flow-next.dev && pnpm build                      # docs-site gate
```

## Early proof point

**Task fn-50.1** (skill scaffold + install detection + init + provider-free map invocation) validates the core wrap-clawpatch approach end-to-end. If install detection + map invocation + `.clawpatch/.gitignore` can't be done cleanly via skill bash with graceful degradation, the whole opt-in-skill architecture needs reconsideration. If fn-50.1 fails, re-evaluate the wrap-vs-port trade-off before continuing.

## Requirement coverage

| R-ID | Task(s) |
|------|---------|
| R1  | fn-50.1 |
| R2  | fn-50.1 |
| R3  | fn-50.2 |
| R4  | fn-50.3 |
| R5  | fn-50.3 |
| R6  | fn-50.4 |
| R7  | fn-50.5 |
| R8  | fn-50.6 |
| R9  | fn-50.2 |
| R10 | fn-50.1 |
| R11 | fn-50.1 |
| R12 | fn-50.1 |
| R13 | fn-50.1 |
| R14 | fn-50.6 |
| R15 | fn-50.6 |
