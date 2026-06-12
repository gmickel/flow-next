# Optional HTML artifact mode: spec & PR render lenses

> HTML render lens: [.flow/artifacts/fn-62-optional-html-artifact-mode-spec-pr/spec.html](../artifacts/fn-62-optional-html-artifact-mode-spec-pr/spec.html) — regenerable, markdown is the record; GitHub shows raw source, open locally in a browser to render. <!-- flow-next:artifact-link -->

## Conversation Evidence

> user (turn 1): "i am considering html artifacts for the SPEC and the PR, look at ALL of this research"
> user (turn 1): "lavish looks especially interesting for the spec html artifact, not sure if we can wrap, don't really like more dependencies, but consider it"
> user (turn 1): "this would be an optional html mode, when activated (via setup/config) the corresponding skills can load a progressively disclosed file for generating plans and prs as beautifully rendered html pages that provide MAX usability in terms of legibility, diagrams, everything great. this will stop us bogging down flow-next for users that want to stick to default markdown for everything."
> user (turn 1): "in addition markdown/tracker-sync will 100% stay the source of truth, all html outputs, even when activated are addition artifacts to assist the human, both pos/pms/devs etc, ofc the markdown spec and make-pr stuff can link to these new html artifacts (not sure how to show them on github though)"
> user (turn 1): "The goal of all of this and this fits our strategy is to make the human touchpoints (spec review, plan review, diff review as efficient and DX friendly as possible)"
> user (turn 1): "this would result in a new mainline feature of flow-next to be surfaced as such on the flow-next.dev landing page and in the relevant sections such as the SPECS section, TEAMS, REVIEW etc and a new page something like SPECS/visual aids, review/visual aids or something better."
> user (turn 1): "I also thing that some of the main STRATEGY pages on flow-next.dev need a full pass, ie. the new autonomous stuff is missing, and a general perfect description of the entire pipleine (unless i missed it), there should be a page STRATEGY/pipeline perhaps?"
> user (turn 1): "before writing this spec or capturing it etc, lets decide on a path and smoke test it by using previous specs/prs and generating such artifacts to see how useful it all is, i'm optimistic"
> user (turn 2): "install lavish-axi for me (obviously we would document this and mention it during setup if the user opts in to html mode)"
> user (turn 3): "also the next release version will be 2.0.0 to symbolise the large leaps we've made"
> user (turn 3): "this may need updated too if we're updating the pipeline diagrams etc, as an aside for this spec" [re: flow-next.dev Introduction page pipeline narrative]
> user (turn 3): "does it make sense to only do the spec/plan via lavish, i mean the agentic editing of a PR doesnt make sense does it?"
> user (turn 3): "will we offer only the spec or the spec + plan (tasks), i tend to now think of the plan as implementation detail but could be useful for users not doing autonomous work? i think it would be the same pathway, we would just generate the html using information from the spec and/or the spec + tasks probably?"
> user (turn 4): "the lavish editor is definitely a large boon that we should document as optional but useful for specs, so lavish is a go as an optional dep"
> user (turn 4): "how does it connect to the agent, will this work if the claude code/codex session is no longer running etc"
> [context: smoke test 2026-06-12 — two artifacts generated from real history (fn-52 spec visualizer with interactive task DAG + R-ID matrix; PR #171 review instrument with churn map + review checklist), verified rendering + Lavish annotate-loop round-trip. Research: Anthropic "unreasonable effectiveness of HTML", Kun Chen 40-PRs/day artifact-review workflow, diff-derived-PR-body consensus, self-contained single-file contract.]

## Goal & Context
<!-- scope: business -->
<!-- Source-tag breakdown: 75% [user] / 25% [paraphrase] -->

flow-next's human touchpoints — spec review, plan review, diff review — are markdown-only today. This feature adds an **optional HTML artifact mode**: when activated via setup/config, the corresponding skills load a progressively disclosed reference file and generate beautifully rendered, self-contained HTML pages alongside their markdown output — maximum usability in legibility, diagrams, and review ergonomics, for POs/PMs/devs alike. Markdown (and tracker-sync) stays 100% the source of truth; every HTML output is an *additional* regenerable artifact — a **render lens**, never the record. Users who stick with default markdown see zero change — the mode existing must not bog down flow-next for them. Goal (strategy-aligned): make the human touchpoints as efficient and DX-friendly as possible. Validated by smoke test on real history before speccing — both artifact shapes (spec visualizer, PR review instrument) proved materially better review surfaces than their markdown sources.

## Architecture & Data Models
<!-- scope: technical -->

- **Activation:** an artifacts/html config block in `.flow/` config, written by the setup ceremony; OFF by default. When off, skills load nothing extra (zero token cost, zero behavior change).
- **Progressive disclosure:** one shared reference file (design system + generation rules + per-artifact-type guidance) loaded by participating skills only when the mode is active. Carries an explicit anti-slop design contract (own palette/typography rules, no CDN fonts, no external requests).
- **Spec artifact — one pathway, state-dependent rendering:** generated from the spec (and tasks when present). Pre-plan → spec-only view (thesis, acceptance criteria, boundaries, decision context) for business review; post-plan → same generator adds the plan layer (task dependency DAG with critical path, R-ID→task coverage matrix). The plan is implementation detail but stays valuable for non-autonomous users — free, since it is the same pathway reading the same flowctl export.
- **PR artifact — read-only review instrument:** derived from the diff (never commit messages), verified against the spec's R-ID export before publishing; churn grouped by review intent (canonical vs generated-mirror vs mechanical), R-ID→evidence table, where-to-look checklist.
- **Lavish integration (optional, detect-best-available):** `lavish-axi` is never required. When on PATH and the session is interactive, spec/plan artifacts open as a Lavish session — annotations map to edits of the markdown source of truth, then the lens regenerates. Architecture verified: standalone local server, state in `~/.lavish-axi/state.json`, agent side is pull-only (`lavish-axi poll` CLI subprocess, no MCP) — feedback is session-spanning and survives agent death; any later session drains the queue. Autonomous/Ralph contexts never poll (never block on a human).
- Canonical skill files use Claude-native tool names; the sync script handles the Codex mirror, per repo convention.

**Implementation anchors (from planning research — repo-scout):**
- Config plumbing is **already generic**: `set_config` (`flowctl.py:1342`) creates intermediate dicts for unknown dot-paths; `deep_merge` (`flowctl.py:1200`) preserves unknown keys. The ONE flowctl edit is an `artifacts` default block in `get_default_config` (`flowctl.py:1124`, follow the `work`/`land` block precedent at `:1145`/`:1164`). Setup detects *unset* keys via `--raw` reads (`flowctl.py:5401`).
- Setup ceremony hook points: question list at `skills/flow-next-setup/workflow.md:378` (Step 6d, include-only-if-unset pattern), config writes at `:523` (Step 7).
- PR-lens hook: `make-pr` Phase 1 already calls `flowctl spec export-cognitive-aid` (`workflow.md:285`; impl `flowctl.py:14234`) — the R-ID/diff payload the PR lens consumes; emit the artifact after Phase 1, inject the body link before Phase 4's `gh pr create` (`phases.md:11`). Absolute-URL rule for body links at `workflow.md:420-435`.
- Spec-lens hooks: capture Phase 5 post-write (`skills/flow-next-capture/workflow.md:590`); plan Step 8 (`skills/flow-next-plan/steps.md:538`).
- Detect-on-PATH precedent: `skills/flow-next-map/SKILL.md:76` (`command -v` + version warn + install-instructions-never-auto-install); cross-skill reference-file precedent: qa loads drive's files by repo-relative path (`skills/flow-next-qa/SKILL.md:86-87`).
- Codex mirror: `sync-codex.sh:133-136` copies whole skill dirs; a neutral `plugins/flow-next/references/` location needs a sibling `cp -R` (templates precedent at `:141-145`). Keep the disclosure file tool-name-agnostic so no rewrite pass applies (avoids the R2 ask-block injection class — see memory `r2-ask-block-must-never-anchor-in-2026-06-10`).
- Generated-dir precedent: `.gitignore` already ignores `.flow/receipts/` + `.flow/tmp/`.

## Edge Cases & Constraints
<!-- scope: technical -->

- **GitHub cannot render committed HTML** and rejects .html PR attachments — markdown spec/PR bodies link to the artifacts with local-open guidance (optional third-party raw-preview link); do not over-engineer hosting. [user: "not sure how to show them on github though"]
- **Self-contained or nothing:** zero external requests (fonts included) — the artifact must open identically from disk, in Lavish, in CI archives, and printed. Lavish's portability guarantee depends on this.
- **Lavish absence/death is invisible:** no lavish on PATH → plain open; server idle-stop → artifact still renders as a static page. Never a hard dependency, never an error path.
- **Autonomous discipline:** pilot/Ralph runs may generate artifacts but never open polls; at most a receipt note that a session has pending prompts.
- **Stale-lens risk:** artifacts regenerate at their lifecycle touchpoints; an artifact is never parsed back as state (one-way derivation). Every artifact carries a staleness stamp in its footer (source spec `updated_at` + git commit at render time) so a reader can tell when the lens lags the markdown.
- **Artifact paths are fixed and deterministic (planning addition):** `.flow/artifacts/<spec-id>/spec.html` and `.flow/artifacts/<spec-id>/pr.html` — never timestamped. Lavish sessions key on the ABSOLUTE file path; a moving path orphans the annotation queue. Worktree caveat (documented, accepted): different worktrees = different absolute paths = different Lavish sessions.
- **Link strategy follows ignore-status (planning addition):** artifacts are committed by default (so make-pr blob links resolve on the remote); a project that gitignores `.flow/artifacts/` gets local-open guidance only — the skill checks `git check-ignore` before choosing. Never emit a blob link that 404s.
- **DAG rendering discipline (planning addition — research flags hand-laid SVG coordinates as the top quality risk):** task graphs render as a layered CSS-grid/flex layout (columns = dependency depth) with edges drawn by a small inlined deterministic JS pass that reads node positions from the DOM at load — never hand-typed SVG coordinates. Above ~20 nodes, collapse to lane/group rendering.
- **R-ID verification mismatch (PR lens):** when the diff and the spec's R-ID export disagree, the artifact renders the discrepancy visibly (a flagged row) — warn-in-artifact, never block make-pr.
- **localStorage in artifacts is try-wrapped** progressive enhancement (works on file://, may be blocked elsewhere); artifacts stay fully readable without it.
- **make-pr artifact side-effect discipline (review addition):** `--dry-run` writes NO artifact (or temp-only, discarded); committed-mode stages ONLY `.flow/artifacts/<spec-id>/pr.html` (never `git add -A`) with a fixed `chore(flow): pr artifact <spec-id>` commit before `gh pr create`; artifact-generation failure is non-fatal (skip the body link, one stderr note); the Ralph stdout contract (`PR_URL=<url>` only) is untouched — all artifact messaging goes to stderr.
- **Artifact link idempotency (review addition):** the artifact link line in spec markdown is replaced in place on every regeneration — never duplicated across repeated capture/plan runs.
- **Spec-lens timing in plan (review addition):** the artifact generates AFTER plan's Step 8 refinement loop exits (or regenerates after any Step 8 mutation) so the lens never renders a task graph the user is still editing.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** HTML artifact mode is opt-in via setup/config, OFF by default. With the mode off, participating skills load no disclosure/reference file, write no artifacts, open no Lavish sessions, and add no behavior-visible output or steps — the only addition is the config-gate check itself in skill prose; the heavy disclosure file incurs zero token cost when off. [user]/[paraphrase]
- **R2:** When active, participating skills load a progressively disclosed shared reference file carrying the generation rules and an explicit anti-slop design system (own typography/palette; no CDN fonts; no purple-gradient defaults). [user]/[paraphrase]
- **R3:** Markdown and tracker-sync remain the sole source of truth; every HTML output is an additional regenerable artifact, never parsed back as state. [user]
- **R4:** Spec artifact uses ONE generation pathway with state-dependent rendering: spec-only before tasks exist; spec+plan layer (task DAG, R-ID coverage matrix) once tasks exist. [user]/[paraphrase]
- **R5:** PR artifact is diff-derived (never from commit messages) and verified against the spec's R-ID export before publishing; it is a read-only review instrument. [user]/[paraphrase]
- **R6:** All artifacts are self-contained single-file HTML — inline CSS/JS, zero external requests, print-friendly. [paraphrase]
- **R7:** Lavish (`lavish-axi`) ships as an optional dependency: detected on PATH, never required; when present + interactive, spec/plan artifacts open as Lavish sessions and annotation feedback maps to markdown-source edits followed by lens regeneration. [user]
- **R8:** The PR artifact never enters the annotate-edit loop; autonomous/Ralph contexts never run a Lavish poll. [user]/[paraphrase]
- **R9:** The setup ceremony, when the user opts into HTML mode, documents and offers the lavish-axi install (including the session-spanning feedback model and idle-stop/resume behavior). [user]
- **R10:** Markdown spec and make-pr output link to their HTML artifacts; the GitHub display limitation is documented with local-open guidance. [user]
- **R11:** Artifacts live in a dedicated regenerable location under `.flow/`, commit-or-gitignore per project. [inferred]
- **R12:** flow-next.dev surfaces this as a mainline feature: landing page, SPECS/TEAMS/REVIEW sections, a new visual-aids page (both navbars), changelog entry, build gate green. [user]
- **R13:** flow-next.dev strategy/pipeline pass ships in the same workstream: a pipeline page (e.g. STRATEGY/pipeline), the missing autonomy-suite content, and the Introduction page's pipeline narrative updated to match. [user]
- **R14:** Released as **2.0.0** — repo docs, Codex mirror regen, manifest/version lockstep, CHANGELOG. [user]

## Boundaries
<!-- scope: business -->

- **Fully opt-in** — markdown-only users see zero new steps, zero new prerequisites, zero token overhead (preserves the zero-dep base contract). [user]
- HTML is NOT a storage format and never becomes one — no state lives in artifacts. [user]
- Lavish is NOT wrapped, bundled, or required — detect-on-PATH only (same shape as clawpatch//flow-next:map). [user]
- PR-artifact annotations → GitHub review comments / resolve-pr input: explicitly OUT of scope (plausible future increment). [paraphrase]
- Review-report artifacts (impl-review / plan-review / qa findings as HTML) are a later increment, not this spec. [inferred]
- The codex-apop delegation hardening idea is deliberately deferred behind this feature ("bigger bang for our buck"). [user]

## Strategy Alignment

- **Spec-driven team patterns** — directly serves the human-touchpoint efficiency thesis; gives POs/PMs a first-class review surface. [strategy:Spec-driven team patterns]
- **Ralph autonomous mode** — artifacts generate in loops but never block them; Lavish feedback is session-spanning, matching re-anchoring. [strategy:Ralph autonomous mode]
- **Cross-platform parity** — canonical Claude-native files, Codex mirror via the sync script. [strategy:Cross-platform parity]

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
Make spec review, plan review, and diff review as efficient and DX-friendly as possible — the human touchpoints are where flow-next's quality discipline meets actual people [user]. Research convergence (Anthropic's HTML-as-default push, the 40-PRs/day artifact-review workflow, the diff-derived PR-body consensus) plus a successful smoke test on real history (fn-52 spec, PR #171) justify a mainline feature, prioritized over the codex delegation hardening ("bigger bang for our buck") [user]. The leap is release-worthy: 2.0.0 [user].

### Implementation Tradeoffs
**Lavish: detect, don't wrap** [user: "lavish is a go as an optional dep"] — its portable-artifacts guarantee means plain self-contained HTML gets the annotate loop for free when present; wrapping would add a Node dependency to the zero-dep base for no gain. Verified pull-only architecture (CLI long-poll, global state file, no MCP) keeps coupling at zero and makes feedback session-spanning. **One artifact pathway, not two** [user] — spec-vs-plan is a rendering question (what state exists), not a product question; avoids a config axis. **Annotate loop scoped to spec/plan** [user: "agentic editing of a PR doesnt make sense"] — a PR artifact derives from an immutable diff; GitHub already owns review comments; duplicating that surface creates a sync problem.

**Planning decisions (added at /flow-next:plan):**
- **No new slash command.** Auto-regen rides the existing lifecycle skills (capture, plan, make-pr); ad-hoc regeneration (hand edits, post-interview) is conversational — the host agent regenerates on request using the disclosure file. Keeps the skill surface flat per repo rule.
- **Interview integration is OUT of v1** — capture/plan cover the state-change touchpoints; conversational regen covers the interview flow more cleanly than wiring the lens into a fourth skill.
- **Artifacts committed by default** (setup offers gitignore); the commit-default is what makes make-pr blob links work for remote reviewers.
- **`planSync.crossEpic` alias removal rides the 2.0.0 release task** as its own breaking-change CHANGELOG line + regression-test update — a documented 1.x deprecation promise (`flowctl.py:5114-5130`), kept visible, not folded silently into the bump.
- **No deterministic Python renderer** — generation is the host agent reading the disclosure file (agentic-vs-deterministic rule); flowctl's only contribution is the config default block.
- **Release task runs LAST (review fix):** the 2.0.0 release (fn-62.6) depends on the flow-next.dev tasks (.7, .8) because the release procedure requires the docs-site changelog + version bump before the tag — task order is .5 → .7 → .8 → .6.

## Quick commands

```bash
# Activation (after fn-62.1):
.flow/bin/flowctl config get artifacts.html.enabled --json     # default: false
.flow/bin/flowctl config set artifacts.html.enabled true

# Smoke: with the mode ON, /flow-next:plan <spec> should emit
#   .flow/artifacts/<spec-id>/spec.html  (self-contained; zero external requests)
grep -c 'http' .flow/artifacts/<spec-id>/spec.html   # only repo/tracker links, no asset URLs

# Lavish (optional, when installed):
command -v lavish-axi && lavish-axi .flow/artifacts/<spec-id>/spec.html
```

## Early proof point

Task fn-62.2 (the disclosure reference file) validated through fn-62.3's first real regeneration is the core bet: a fresh agent session reading ONLY the disclosure file must reproduce the smoke-test house style (instrument-panel design, layered DAG, source-tag chips, staleness stamp, zero external requests) for fn-62 itself — matching the hand-built artifacts in ~/Documents/flow-next-artifact-smoke/ in quality without having seen them. If the output drifts sloppy or inconsistent, fix the reference file's rules/examples/checklist BEFORE building the PR lens (fn-62.4) and docs (fn-62.5+).

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | Opt-in config, OFF default, no observable change when off (no reference load / artifacts / sessions / output) | fn-62.1 | — |
| R2  | Progressively disclosed reference file + anti-slop design system | fn-62.2 | — |
| R3  | Markdown/tracker-sync sole source of truth; artifacts regenerable, never parsed back | fn-62.2 (contract), fn-62.3 (enforced at touchpoints) | — |
| R4  | One spec-artifact pathway, state-dependent rendering | fn-62.3 | — |
| R5  | PR artifact diff-derived + R-ID-verified, read-only | fn-62.4 | — |
| R6  | Self-contained single-file HTML, zero external requests, print-friendly | fn-62.2 | — |
| R7  | Lavish optional dep: detect-on-PATH, annotate→markdown-edit→regenerate loop | fn-62.2 (detection block), fn-62.3 (session open + poll) | — |
| R8  | PR artifact never in annotate loop; autonomous never polls | fn-62.3, fn-62.4 | — |
| R9  | Setup ceremony documents/offers lavish-axi on HTML opt-in | fn-62.1 | — |
| R10 | Spec + PR markdown link artifacts; GitHub limitation documented | fn-62.3 (spec links), fn-62.4 (PR links), fn-62.5 (docs) | — |
| R11 | Dedicated regenerable `.flow/artifacts/` location, commit-or-gitignore | fn-62.1 | — |
| R12 | flow-next.dev mainline surfacing (landing, sections, visual-aids page, both navbars, changelog) | fn-62.7 | — |
| R13 | flow-next.dev strategy/pipeline pass (pipeline page, autonomy content, Introduction) | fn-62.8 | — |
| R14 | 2.0.0 release: repo docs, Codex mirror regen, version lockstep, CHANGELOG | fn-62.5 (repo docs), fn-62.6 (release) | — |
