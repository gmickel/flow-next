# Claude Code Project Guide

This repo ships the **flow-next** Claude Code plugin — a spec-driven, zero-dependency workflow for AI-assisted SDLC, with a bundled `flowctl` Python CLI and autonomous Ralph mode. First-class on Claude Code, OpenAI Codex, Factory Droid, Cursor, xAI Grok Build, and OpenCode (canonical sentence lives in [`plugins/flow-next/docs/platforms.md`](plugins/flow-next/docs/platforms.md) — edit there, restate verbatim). The repo IS flow-next.

The repo's strategic intent and canonical vocabulary live at the repo root:

- [`STRATEGY.md`](STRATEGY.md) — target problem, approach, who it's for, key metrics, active tracks
- [`GLOSSARY.md`](GLOSSARY.md) — vocabulary dictionary: the load-bearing terms (Spec, Task, R-ID, Receipt, Gate, plan-sync, ...) with the synonyms to avoid. Deeper concepts live in [`plugins/flow-next/docs/README.md`](plugins/flow-next/docs/README.md); the retired long-form text is archived at [`agent_docs/archive/GLOSSARY-full.md`](agent_docs/archive/GLOSSARY-full.md)

Every other detail is in a focused file you should consult when relevant — see "Where to look" below.

## Stack and tooling

- Python 3.11+ (flowctl), Node ecosystem optional (TUI uses `bun`).
- `jq` and `gh` are required for review-subsystem and PR plumbing.
- Package manager: pick one and stay with it per project. `pnpm` for the TUI.
- Pre-commit / lint: `biome` is the source of truth for the TUI; flowctl uses pure-stdlib Python.
- **Python lint: `ruff`, pinned.** Run `uvx ruff@0.16.0 check .` before opening a PR — CI runs the same pinned version and will fail the build otherwise. No install step; `uvx` fetches it. **Keep the pin in step** with `.github/workflows/test-flow-next.yml`: ruff 0.16 moved its default rule set from 59 to 413, so an unpinned upgrade is an unannounced CI break.
  - `ruff.toml` is correctness-only (pyflakes, bugbear, pylint errors, a few bug-pattern/security rules) and documents why each notable rule is *excluded*. Style rules are deliberately out of scope. **Do not add a rule to make a diff pass, and do not remove one to make a diff pass** — if a rule is wrong for this repo, say so in the config next to the exclusion, with the evidence.
  - Never `--fix` into `.flow/` or `plugins/flow-next/codex/`; both are generated copies and are excluded for that reason. `--unsafe-fixes` is not used.
  - **The gate is code quality only — it must never change a prompt.** Never select a rule that can rewrite string contents (ISC, Q, UP032, COM, W291, D). `tests/test_prompt_text_pinned.py` pins every embedded prompt constant and on-disk prompt template by SHA-256; a lint or refactor pass that alters prompt text fails there. Changing a prompt on purpose is fine — update the hash in the same commit and say what changed and why. **A hash update with no prompt rationale in the commit message is the thing that check exists to catch.**
  - **Prompt-size ratchets and evidence-ledger live-file freezes were deliberately removed (2026-08-07). Never reintroduce one.** No frozen char/token ceilings, no stored-hash pins of live skill prose, no sentence-level prose assertions in tests. Prose growth is judged via `.flow/criteria.md` G1; test shape is governed by G2; invariants are enforced behaviorally (the fn-169 no-embed test that drives the real dispatch path is the model - text pins watched that decision get undone twice); deliberate-change detection is `test_prompt_text_pinned.py` only.
  - Embedded `*_FALLBACK` constants are not all the same kind. The four extracted review prompts are byte-identical mirrors of their templates (fn-112.3, guarded by `test_review_prompt_template_parity`). `VALIDATOR_TEMPLATE_FALLBACK` and `DEEP_PASSES_FALLBACK` are hand-written **condensations** authored that way in #118 — shorter on purpose, for installs with no template on disk. Do not "sync" them; that is not drift.

## Architecture: agentic vs deterministic (READ BEFORE PLANNING NEW FEATURES)

flow-next is a **skill-driven plugin running inside an agentic coding environment** (host platforms: Claude Code, Codex, Factory Droid, Cursor - see the roster below). The host agent IS the intelligence. Default to skill-based architecture; reach for deterministic Python in flowctl only when there's a real reason.

### When to use a SKILL (the default)

A workflow that walks files, makes per-item judgments, investigates code, composes multi-step actions where each depends on prior context, asks the user on ambiguous cases, and could reasonably be invoked via `/flow-next:<command>`.

→ **Build it as a skill.** The host agent reads the skill workflow file, executes via existing Read/Grep/Glob/Edit/Write tools, dispatches subagents via the platform primitive (`Agent`/`Task` in Claude, `spawn_agent` in Codex), asks via `AskUserQuestion`. Canonical files use Claude-native tool names; `sync-codex.sh` rewrites for the Codex mirror.

**Do not spawn `codex`/`copilot`/other LLMs via subprocess from inside flowctl when invoked from a skill.** The host agent is already an LLM running the skill — there is no need for a second one.

**Implementation offload is prose-routed, not packaged (flow-98 decision).** The `work.delegate*` subsystem is gone: bridging implementation to a second CLI (`codex exec`, `cursor-agent`, `claude -p`, `grok`) is a routing decision the host reads from the model-routing section in `CLAUDE.md` / `AGENTS.md` plus the bridge recipes in `flowctl usage`, and it is **host-orchestrated implementation-offload, never a judgment hand-off**: the bridged child writes code while the host keeps git, judgment, and the verdict. Nothing about that route licenses spawning an LLM for judgment from inside flowctl. See [`docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#implementation-offload-the-bridge-route).

### When to use DETERMINISTIC flowctl Python

Mechanical operations needing to work without an agent in the loop: Ralph hooks (PreToolUse / Stop / SubagentStop matchers), receipts (review / walkthrough / ralph_blocked), schema validation, atomic file writes, git plumbing, the triage-skip whitelist, the review-subsystem backend dispatch (`flowctl rp`, `flowctl review-backend`).

→ **Build it in flowctl Python.** Pure plumbing, no intelligence required.

### The common pattern: SKILL + thin flowctl plumbing

Most features look like this. Skill drives the workflow; flowctl provides atomic helpers the skill calls. Examples: `/flow-next:prospect` skill + `flowctl prospect list/read/promote`. `/flow-next:audit` skill + `flowctl memory mark-stale`.

**Split rule:** flowctl owns "set this field" / "validate this schema" / "atomic-write this file" / "list these things." Skill owns "read this and judge" / "compose multi-step decision flow" / "ask user when unsure" / "dispatch subagents."

### How to spot a mistake

Symptoms suggesting deterministic when you should build skill-based:
- Writing regex to extract "code references" from prose → host agent can read prose
- Building a stoplist of common English words → host agent knows English
- Spawning `codex --exec` to make judgments → host agent makes judgments
- Parsing structured-verdict YAML from an LLM response → host agent's own structured output
- Building a deterministic "fallback" engine for when LLM unavailable → host agent is always available
- Weighted scoring math substituting for "is this still relevant?" → host agent answers directly
- **Embedding content into a prompt that the agent could fetch itself** → pass an identity (a SHA range, a path), not a payload
- **Writing a fitter / truncator / budget constant for a prompt payload** → the payload is the bug; a fitter is the symptom. Genuine *transport* limits (an argv cap) stay, and are named as transport
- **Enumerating the ways something could be done wrong** (writer APIs, path spellings, command shapes) → an enumeration is a race against the next spelling; put the invariant where it is true by construction

If three or more apply, stop and convert to a skill. The deterministic path is harder to maintain, more brittle, and produces worse output.

**Sanctioned carve-out (subprocess LLM judgment):** do not "fix" these licensed cases when the symptom list matches. Review-backend dispatch and the triage-skip judge may spawn a subprocess LLM for judgment. Rationale: cross-model verdicts about pipeline-written code must not be self-issued by the host.

## Cross-platform patterns

**HOST PLATFORM ROSTER (memorize - do not forget any of these when building features):**

| Host | Mechanism | Consumes |
|---|---|---|
| Claude Code | canonical plugin (`.claude-plugin/`) | canonical files as-is |
| Codex | pre-built mirror at `plugins/flow-next/codex/`, regenerated by `scripts/sync-codex.sh` | REWRITTEN copies (tool names, ask fallback, dispatch phrases) |
| Factory Droid | auto-translates the Claude plugin format on install | canonical files as-is (`DROID_PLUGIN_ROOT` alias) |
| Cursor | RECOMMENDED: team-marketplace repo import (root `.cursor-plugin/marketplace.json`); fallback: `scripts/install-cursor.sh` / `.ps1` (blanket rsync to `~/.cursor/plugins/local/`, excludes codex/ + tests/); manifest at `plugins/flow-next/.cursor-plugin/plugin.json` | canonical files AS-IS - no rewrite pass exists |
| Grok Build | reads the Claude plugin format directly (compat, verified) | canonical files as-is |
| OpenCode | installer scatter (`scripts/install-opencode.sh` -> `~/.config/opencode/`; skills as-is, support dirs `scripts/`+`templates/`+`references/`+`docs/` at the config root — plugin-root geometry, so relative docs links resolve; generated agents/commands; setup detects via the ownership manifest) | canonical files + support dirs + generated glue |

**Architectural rule:** canonical skill files use Claude-native tool names; `sync-codex.sh` rewrites them in the Codex mirror. Skill prose stays concrete; cross-platform maintenance lives in one place — the sync script. Cursor/Droid/Grok get NO rewrite pass, so anything Claude-specific in canonical prose must either work there or carry an explicit portable-host clause.

**Checklist when adding/editing skills, agents, or hooks (walk ALL of it):**

1. Run `./scripts/sync-codex.sh` TWICE (idempotency) and commit the mirror diff with the canonical change. Its validation guards must stay green; new Claude-only phrases (tool dispatches, model-name examples) may need a new transform + hard-fail guard (pattern: the fn-100 Explore-dispatch and scout-tier rules).
2. Claude BUILTIN references (`Explore`, `general-purpose`, `AskUserQuestion`, model names) are invisible to the Cursor/Droid/OpenCode consumers (all three read canonical prose as-is) - every such reference needs a portable-host fallback clause in the canonical prose (generic read-only dispatch with Edit/Write disallowed; plain-text numbered-prompt fallback for asks) or graceful degradation stated inline.
3. Plugin-root env vars: Cursor and Grok expose NONE - every bash preamble carries the three rungs in order: `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl`, then the plugin root derived from the skill's own SKILL.md absolute path (two levels up), then the legacy `.flow/bin/flowctl` backstop. Setup copies nothing into a repo; on Claude Code bare `flowctl` also resolves via bin-PATH injection in plain Bash ONLY - never in skill prose.
4. No plugin-level hooks (`plugins/flow-next/hooks/` is gone): Ralph registration is agent-driven via `/flow-next:ralph-init` (merge fingerprinted entries into project settings per host). Guard matchers stay Claude-schema (`PreToolUse`/`Stop`, `Bash|Execute` shell + file-tool set); works on Claude Code + Droid, NOT Cursor (different hook events) - never assume the guard fires there.
5. Installers need no enumeration updates for SKILLS (Cursor installers blanket-copy; the codex mirror is a full regen; the OpenCode installer blanket-scatters) - with two exceptions: (a) the codex mirror's `phases.md` 3c is a HARDCODED heredoc in `sync-codex.sh` (`SECTION3C`), so canonical 3c edits must land in the heredoc too or the mirror goes silently stale at exit 0; (b) a new AGENT (or new agent-frontmatter key) must extend the closed allowlist in `plugins/flow-next/scripts/lib/opencode_generate.py` — it fails loudly (`GenerateError`) at OpenCode install otherwise. `plugins/flow-next/docs/platforms.md` DOES need a note when host behavior differs.
   **Validate at the CONSUMER's layout, not the producer's** (PR #363 lesson: three review rounds came from checking only the repo tree while the real consumer is the installed `$CODEX_HOME` — shallower, partial, different invocation syntax). `sync-codex.sh` now carries hard-fail guards for the whole class: mirror docs-link resolution, the installed-docs link-universe closure (resolve on disk or absolute URL), and actionable-invocation rewrites (`/flow-next:` → `$flow-next-`). A canonical edit that adds a docs link or a user-copyable command is covered by those guards — **a guard failure is load-bearing; fix the content or extend the transform, never relax the guard.**
6. `agents/*.md` model fields are family aliases resolved by the host; on non-Claude hosts they map to host defaults - never version-pin, and never assume a specific tier is honored off Claude Code.

- **Variable references** — bash fallback: `FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"`. Droid sets `DROID_PLUGIN_ROOT` and also exposes `CLAUDE_PLUGIN_ROOT` as an alias (per Factory docs, "Alias for `${DROID_PLUGIN_ROOT}` (Claude Code compatibility)"). The fallback order is conservative but correct on both platforms. *(Last verified against Factory docs 2026-05-25 — fn-48.2.)*
- **Hook matchers** — regex OR: `"matcher": "Bash|Execute"` (Claude `Bash`, Droid `Execute` — Factory hooks-reference 2026-05-25 still lists `Execute` as canonical and `Bash` as not recognized).
- **Agent permissions** — `disallowedTools` blacklist (not `tools` whitelist). Tool names differ across platforms; blacklist works because both understand `Edit`, `Write`, `Task`. Read-only agents deny all three — `Task` because a spawned writing subagent is an escape hatch out of read-only; writing agents deny only the subset they must not use (plan-sync: `Write, Bash`; worker and pr-comment-resolver: none). `Task` is subagent dispatch (renamed Agent in Claude Code v2.1.63), not a planning tool.
- **Plugin paths** — flow-next is a Claude-first plugin; use `${PLUGIN_ROOT}/.claude-plugin/plugin.json` directly. Droid auto-translates Claude Code plugin format on install (Factory docs: "Droid is compatible with plugins built for Claude Code… the plugin format is interoperable"), so a `.factory-plugin/plugin.json` fallback is **not** needed for Claude-first plugins like flow-next. Native Droid-first plugins (e.g. Factory-AI/factory-plugins marketplace) ship `.factory-plugin/plugin.json`; we don't.
- **Blocking-question tool** — every interactive skill MUST use the platform's blocking primitive. Canonical writes `AskUserQuestion`; `sync-codex.sh` transforms canonical invocations into a plain-text numbered-prompt instruction (with `N+1. Other — type your own answer` as the final option) for the Codex mirror — the mirror never mentions `request_user_input` (Plan-mode-only per openai/codex#10384/#11536/#12694; closed without resolution as of Feb 2026). Droid (currently) sees the canonical name. Always bare `AskUserQuestion` in canonical files; an optional parenthetical breadcrumb noting the rewrite is fine.
- **Subagent dispatch** — canonical writes `Task` with `subagent_type: Explore`; sync rewrites to `spawn_agent`. Read-only enforcement via `disallowedTools: Edit, Write, Task`.

## Editing rules

- Keep prompts concise and direct.
- Avoid feature flags or backwards-compatibility scaffolding (plugins are pre-1.0 except flow-next 1.0+).
- Do not add extra commands / agents / skills unless explicitly requested.
- For pure docs / agent_docs / README changes, do NOT bump the plugin version.
- **Skill prose changes are reviewed against the skill's conduct checklist** in [`agent_docs/conduct/`](agent_docs/conduct/README.md): load it when a PR or change touches a skill's prose and use its items as the review criteria. The checklists are review rubrics, not handoff ceremony — no dogfood run or per-item pass/fail record is required to merge.
- **Recorded decisions are settled.** A decision recorded in a spec's Decision Context, or ruled by the maintainer on the PR, is not up for re-litigation: reviewers (human or bot) may note disagreement as FYI, never as a merge-gating finding. Re-raising a recorded decision as blocking is itself a review defect. The maintainer decides when a change lands; process-compliance observations (missing ceremony, checklist records, dogfood runs) are never merge-gating.
- **Docs-tree changes still run the FULL gate here — the classifier's tier-B verdict is not a licence to skip it.** `flowctl gate classify` calls `agent_docs/**`, `plugins/flow-next/docs/**.md`, and root `README*`/`GLOSSARY.md`/`CHANGELOG.md` docs-only (lint/format only), but this repo's unit suite pins content in every one of them — conduct checklists, prose contracts, dictionary shape — so a "docs-only" edit can break a pin. Run `python3 scripts/run_tests_parallel.py` before handing off. This is the conductor-instructions half of the documented remedy for the classifier's known fail-open (see "Known fail-open" in [`plugins/flow-next/docs/flowctl.md`](plugins/flow-next/docs/flowctl.md)); the CI half is the `paths:` filter in `.github/workflows/test-flow-next.yml`, pinned by `test_ci_trigger_coverage`.
- **Version bumps are batched, not per-spec.** When implementing a spec, land the code + docs + an `## Unreleased` CHANGELOG entry (repo + docs-site), but do NOT run `scripts/bump.sh` or touch the version manifests / `FLOW_NEXT_VERSION`. The release + version-number decision is made separately, later, across several accumulated specs — to avoid version churn. Spec/task acceptance that says "bump to X.Y.Z" means *stage under `## Unreleased`*; the actual bump happens at the batched release.

## PR workflow

- **PRs derived from a flow-next spec** → use `/flow-next:make-pr <spec-id>`. It generates a cognitive-aid PR body (R-ID coverage table, critical-changes summary, decision context, "where to look") from the spec export. Never hand-write a body when a spec exists — the skill carries discipline the manual version drifts away from.
- **Chore PRs without a spec** (version bumps, small mechanical fixes, CHANGELOG-only changes, third-party-reported regressions) — write the body manually but match the make-pr structure: short summary + What changed + Verification + Version note (or "no version bump per CLAUDE.md docs-only rule" if applicable). Don't open bare-body PRs.
- **Review feedback on any PR** → `/flow-next:resolve-pr` (auto-detects PR from current branch). Resolves threads via dispatched resolver agents, validates combined state, replies + resolves via GraphQL. Bounded at 2 fix-verify cycles before escalation.
- **No direct `gh pr merge` from skills.** Merge is a human decision; do it explicitly when the PR is ready. Sole confined exception: the opt-in `/flow-next:land` ship loop merges explicitly (`--squash --match-head-commit`, never `--auto`) after its full gate tree passes — that license is bounded to land and extends to no other skill.

## Docs site

- A public docs site exists at **`https://flow-next.dev`** (source repo `~/work/flow-next.dev`). User-facing changes — behavior, commands, setup, public vocabulary, README, release notes — should be reflected there in the same workstream. **The detailed update/release workflow for the docs site, and the maintainer's other downstream/narrative properties, live in the maintainer's *private* config — not this committed file** (they reference maintainer-local repos/paths that other contributors don't have).
- **Both changelogs are user-facing release surfaces** (`CHANGELOG.md` becomes the GitHub release body; flow-next.dev is the shorter public story). Write user-outcome-first, machinery last; the full ordering rules, hard rejection test, and examples live in [`agent_docs/releasing.md`](agent_docs/releasing.md) - follow them for every entry.

## Where to look

| For | Look at |
|---|---|
| Plugin overview + install + 5-command quick start | [`README.md`](README.md) (root) — canonical entry point |
| Full doc index (subsystem + workflow references) | [`plugins/flow-next/docs/README.md`](plugins/flow-next/docs/README.md) |
| Spec-driven team workflow + handover objects | [`plugins/flow-next/docs/teams.md`](plugins/flow-next/docs/teams.md) |
| Build-loop conductor (`/flow-next:pilot` — single-tick spec-to-PR pipeline; host `/loop`/`/goal` drives) | [`plugins/flow-next/skills/flow-next-pilot/SKILL.md`](plugins/flow-next/skills/flow-next-pilot/SKILL.md) |
| Ralph autonomous mode internals | [`plugins/flow-next/docs/ralph.md`](plugins/flow-next/docs/ralph.md) |
| Orchestration & model routing (steering tiers, review-backend precedence, the bridge route for implementation offload, CLAUDE.md model tables, pilot+land chaining) | [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md) |
| Full `flowctl` CLI reference | [`plugins/flow-next/docs/flowctl.md`](plugins/flow-next/docs/flowctl.md) |
| `.flow/` directory layout + spec-first task model | [`plugins/flow-next/docs/architecture.md`](plugins/flow-next/docs/architecture.md) |
| Memory schema (bug/knowledge tracks, audit lifecycle) | [`plugins/flow-next/docs/memory-schema.md`](plugins/flow-next/docs/memory-schema.md) |
| Tracker-sync bridge (projection model, hybrid ids, deterministic `flowctl tracker` transport; `/flow-next:tracker-sync` ≠ `/flow-next:sync`) | [`plugins/flow-next/docs/tracker-sync.md`](plugins/flow-next/docs/tracker-sync.md) |
| Live-app QA (`/flow-next:qa` — opt-in; drives the running app, never passes by reading source) | [`plugins/flow-next/skills/flow-next-qa/SKILL.md`](plugins/flow-next/skills/flow-next-qa/SKILL.md) |
| Opinionated agent-readiness assessment (`/flow-next:prime` - classify, operability verdict, ranked next-actions) | [`plugins/flow-next/skills/flow-next-prime/SKILL.md`](plugins/flow-next/skills/flow-next-prime/SKILL.md) |
| Compact markdown digest of a spec, task, diff, or the current topic (`/flow-next:visual` — the light register below the HTML lenses) | [`plugins/flow-next/skills/flow-next-visual/SKILL.md`](plugins/flow-next/skills/flow-next-visual/SKILL.md) |
| Reply-prose discipline (`/flow-next:prose` — the agent drafts substantial chat replies under the artifact prose contract; also invocable with a draft) | [`plugins/flow-next/skills/flow-next-prose/SKILL.md`](plugins/flow-next/skills/flow-next-prose/SKILL.md) |
| HTML artifact mode (opt-in render lenses under `.flow/artifacts/`) | [`plugins/flow-next/docs/html-artifacts.md`](plugins/flow-next/docs/html-artifacts.md) |
| Cross-platform install matrix (Claude / Codex / Droid / OpenCode) | [`plugins/flow-next/docs/platforms.md`](plugins/flow-next/docs/platforms.md) |
| Codebase feature map (optional) | [`plugins/flow-next/skills/flow-next-map/`](plugins/flow-next/skills/flow-next-map/) — `/flow-next:map` wraps `clawpatch map` |
| Troubleshooting + uninstall | [`plugins/flow-next/docs/troubleshooting.md`](plugins/flow-next/docs/troubleshooting.md) |
| Canonical spec-template scaffold (single source of truth — section list, scope-owner annotations, `## Decision Context` flat-vs-H3 conditional; a repo-root `SPEC.md` overrides it per project) | [`plugins/flow-next/templates/spec.md`](plugins/flow-next/templates/spec.md) |
| Setup internals (copy-less install, per-artifact resolution chains, snippet/marker invariants) | [`agent_docs/setup.md`](agent_docs/setup.md) |
| Adding a new `/flow-next:<name>` skill | [`agent_docs/adding-skills.md`](agent_docs/adding-skills.md) |
| Cutting a release | [`agent_docs/releasing.md`](agent_docs/releasing.md) |
| Writing docs (repo docs + flow-next.dev): capability framing, page shape, anchors as contracts | [`agent_docs/writing-docs.md`](agent_docs/writing-docs.md) |
| Prose contract for agent-emitted artifacts (the rules every durable emission surface drafts under - PR bodies, specs and plans, tracker and PR comments, strategy and briefing sections, memory and glossary entries, done summaries, changelogs; cited by path at each emission point) | [`plugins/flow-next/docs/prose.md`](plugins/flow-next/docs/prose.md) |
| Local plugin dev + smoke tests + Ralph e2e | [`agent_docs/local-dev.md`](agent_docs/local-dev.md) |
| Optimizing a skill/agent prompt (token/accuracy, eval-driven) | [`agent_docs/optimizing-skills.md`](agent_docs/optimizing-skills.md) |
| Per-skill conduct checklists (review rubric for skill-prose changes) | [`agent_docs/conduct/README.md`](agent_docs/conduct/README.md) |
| Repo strategy + active tracks | [`STRATEGY.md`](STRATEGY.md) |
| Vocabulary dictionary (terms + banned synonyms) | [`GLOSSARY.md`](GLOSSARY.md) · archived long-form: [`agent_docs/archive/GLOSSARY-full.md`](agent_docs/archive/GLOSSARY-full.md) |
| Repo structure | `.claude-plugin/marketplace.json` (Claude); `.agents/plugins/marketplace.json` (Codex); `plugins/flow-next/.claude-plugin/plugin.json`, `plugins/flow-next/.codex-plugin/plugin.json`; Codex pre-built mirror at `plugins/flow-next/codex/` (regenerated by `scripts/sync-codex.sh`) |

Optional: `/flow-next:map` wraps [openclaw/clawpatch](https://github.com/openclaw/clawpatch)'s `clawpatch map` command to build a semantic feature index under `.clawpatch/features/*.json`. When present, `repo-scout` uses it to anchor R-IDs and `Investigation targets` to concrete codebase regions. Provider-free by default; install via `pnpm add -g clawpatch` (Node 22+).

> The legacy `flow` plugin was removed in flow-next 1.0.2 (see CHANGELOG). To browse the old code: `git show 0a45aff:plugins/flow/README.md` or `git checkout 0a45aff -- plugins/flow/`. It was never tagged as a release.

## Repo metadata

- Author: Gordon Mickel (gordon@mickel.tech)
- Homepage: https://mickel.tech
- Marketplace: https://github.com/gmickel/flow-next

<!-- BEGIN FLOW-NEXT -->
<!-- flow-next:snippet:v1 -->
## Flow-Next

This project uses Flow-Next for ALL task tracking. `flowctl` comes from the flow-next plugin install — every flow-next skill resolves it itself, and on Claude Code it is also on PATH. Do NOT create markdown TODOs or use TodoWrite. Cold session: `flowctl brief` first — one bounded call (specs, ready tasks, memory); go deeper with `show`/`cat`/`anchor <task-id>`.

- Lifecycle: `flowctl list` / `show fn-N.M` / `start fn-N.M` / `done fn-N.M --summary-file s.md --evidence-json e.json` (e.json: `{"commits": ["<sha>"], "tests": ["<cmd>"], "prs": []}`)
- BEFORE any other flowctl operation, or when unsure of a flag: run `flowctl usage` (CLI cheatsheet + orchestration recipes) or `flowctl --help`.
- BEFORE bridging work to another model/CLI (`codex exec`, `cursor-agent`, `claude -p`, `grok`) or picking an implementation/review model: run `flowctl usage` and follow "Orchestration & model steering" exactly.
- Creating a spec: write it directly — `/flow-next:plan` is task breakdown only. `flowctl spec create --title "Short title" --plan-file plan.md --json`, then `/flow-next:plan <spec-id>`. Scaffold cascade (first match wins): `SPEC.md` -> `spec.md` -> bundled template.
- Substantial replies (reports, reviews, multi-section answers): invoke `/flow-next:prose` BEFORE drafting — the artifact prose contract applies to chat replies too. Short conversational turns skip it.
- If `flowctl` is not found: your shell lacks the plugin's `scripts/` dir on PATH (only Claude Code injects it). Resolve it the way the skills do - the plugin install's `scripts/flowctl` (Claude/Droid: plugin-root env var; Codex: `${CODEX_HOME:-$HOME/.codex}/scripts/flowctl`; Cursor/Grok: two levels above any flow-next SKILL.md) - or update/reinstall the flow-next plugin. A repo with no `.flow/` yet: run `/flow-next:setup`.

**This repo's own additions (maintainer notes, not part of the shipped snippet):**

- **`done` writes the receipt into the TRACKED task file AFTER your commit** — stage/commit the path it reports under `modified_paths` (fn-192 / #346).
- **Bulk task creation:** `flowctl task create --spec <spec-id> --from-json tasks.json --json` (`[{"title": ..., "description": ..., "acceptance": ..., "deps": [1], "satisfies": ["R1"]}]`); the granular verbs remain for edits.
- **Standing criteria:** if the repo has a `.flow/criteria.md` (G-IDs), reference relevant G-IDs in spec prose — NEVER restate a standing criterion as an R-ID (a copy freezes while criteria.md evolves and gets judged twice).
- **Spec Quick commands:** list FOCUSED suites for the feature's files (e.g. `cd plugins/flow-next/tests && python3 -m unittest test_config_snapshot test_task_create_files -q`). That is what workers baseline and verify per task. The FULL suite runs ONCE at the final gate (work Phase 4 / completion review): `python3 scripts/run_tests_parallel.py` (serial fallback `--serial`) **plus `uvx ruff@0.16.0 check .`** — both must be green before a PR. Do not put the full discover/parallel command on every task's Quick commands.
- **When a change touches `flowctl.py` or `flowctl_tracker/`**, the final gate also needs `python3 scripts/gen_tracker_manifest.py` (the manifest pins every shipped member) and `./scripts/sync-codex.sh` twice (idempotency). Skipping either fails `test_tracker_distribution` rather than producing a useful error. There is no repo-local copy to propagate to: `plugins/flow-next/scripts/` is the single source.
- **When a change adds, renames, or retypes a `.flow/config.json` key**, the published schema must learn it in the same change: extend the TABLE in `scripts/gen_flow_config_schema.py` (or the drift-test allowlist for machine-written keys), regenerate the committed artifact by running that script, and keep `test_flow_config_schema_drift` green (fn-138).
- `.flow/memory/` — categorized learnings from past work (`bug/<category>/`, `knowledge/<category>/`; YAML frontmatter: track, category, module, tags, status). Search via `flowctl memory search <q>` — relevant when implementing or debugging in modules with documented prior art.
<!-- END FLOW-NEXT -->

<!-- flow-next:model-routing:start -->
## Model routing

_Scaffolded by `/flow-next:setup` as an example, then edited. This section is yours: the model ids are properties of your account and your harness, so keep them current against what your CLIs actually serve — ask a harness for its list rather than trusting this block._

Grammar: `<tier>: <model>` or `<tier>: <model> at <effort>`. An absent tier means the session model; an unparseable line is ignored. Tier meanings: [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants). How this harness reaches one: [`plugins/flow-next/docs/reach/`](plugins/flow-next/docs/reach/README.md).

```
reviewer: gpt-5.6-sol at high
implementer: gpt-5.6-terra at medium
fast scout: haiku-4.5
thinking scout: sonnet-5
```

Resolution at every dispatch site, highest first: an explicit instruction in the moment, then this block, then the agent definition's own default, then the session model. A model this harness cannot reach falls back to the session model, says so once, and continues — routing never fails closed, and nothing here is validated.

How to apply — defaults, not limits. Unless prompted otherwise, route work as you judge best; no permission needed, and an explicit user instruction always overrides this block. Standing permission to escalate: if a cheaper model misses the bar, rerun on a smarter one without asking. Judge the output, not the price tag.

- Unset is the doctrine, not an omission: planning, capture, interview, requirement analysis, every verdict, and the worker run on the session model. Never delegate judgment.
- The session model here is opus-5 at MEDIUM effort for conducting and implementing; escalate to fable-5 when a problem is genuinely frontier-hard rather than raising opus-5's effort.
- Anything user-facing (UI, copy, API design) stays on the session model even when it looks mechanical.
- Reviews prefer a different family than the writer — uncorrelated blind spots. Advice, not enforcement: the receipt records what actually ran.
- Autonomous loops never call a bridge CLI raw — wrap it in a thin fast-tier subagent that runs the bridge in the FOREGROUND and self-heals environment failures only, never judgment. Recipes: `flowctl usage` § Orchestration & model steering.
<!-- flow-next:model-routing:end -->
