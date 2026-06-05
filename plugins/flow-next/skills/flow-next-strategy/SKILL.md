---
name: flow-next-strategy
description: "Create or maintain `STRATEGY.md` — the product's target problem, our approach, who it's for, key metrics, and tracks of work. Use when starting a new product, updating direction, or when prompts like 'write our strategy', 'update the roadmap', 'what are we working on', or 'set up the strategy doc' come up. Also fires when `/flow-next:prospect`, `/flow-next:plan`, `/flow-next:interview`, or `/flow-next:capture` need upstream grounding and no strategy doc exists yet."
user-invocable: false
allowed-tools: AskUserQuestion, Read, Write, Bash
---

# /flow-next:strategy — repo-root STRATEGY.md anchor

`flow-next-strategy` produces and maintains `STRATEGY.md` — a short, durable anchor at the repo root (peer of `README.md` / `GLOSSARY.md`) that captures what the product is, who it serves, how it succeeds, and where the team is investing. Downstream skills (`/flow-next:prospect`, `/flow-next:plan`, `/flow-next:interview`, `/flow-next:capture`, `/flow-next:sync`) read it as grounding when `sections_filled >= 1`.

The document is short and structured on purpose. Good answers to a handful of sharp questions produce a better strategy than any amount of prose. This skill asks those questions, pushes back on weak answers, and writes the doc.

**Note: The current year is 2026.** Use this when dating the strategy document.

## Preamble

flowctl is **bundled — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Interaction Method

Default to `AskUserQuestion` (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded). Fall back to numbered options in chat only when the tool is unreachable in the harness or the call errors — never silently skip the question. (sync-codex.sh rewrites this to a plain-text numbered prompt in the Codex mirror.)

Ask one question at a time. **Free-form responses for the substantive sections** (Target problem / Our approach / Who it's for / Key metrics / Tracks). **Single-select with lead-with-recommendation only for routing decisions** (which section to revisit, include this optional section, foreign-file resolution).

## Focus Hint

<focus_hint> #$ARGUMENTS </focus_hint>

Interpret any argument as an optional focus: a section name to revisit (`metrics`, `approach`, `tracks`, `problem`, `persona`, `milestones`, `not-working-on`) or a scope hint. With no argument, proceed open-ended and let the file state decide the path.

## Core Principles

1. **Anchor, not plan.** Strategy is what the product is and why. Features belong in `/flow-next:prospect`; tasks belong in specs and `/flow-next:plan`. Do not let either creep into the doc.
2. **Rigor in the questions, not the headings.** The section headers are plain English. The interview questions enforce strategy discipline (`references/interview.md`).
3. **Short is a feature.** The template is constrained. Adding sections costs more than it looks like. Push back on expansion.
4. **Durable across runs.** This skill is rerunnable. On a second run it updates in place, preserves what is working, and only challenges sections that look stale or weak.
5. **Survives `.flow/` wipe.** `STRATEGY.md` lives at repo root, never under `.flow/`. The project's strategy belongs to the project, not flow-next (R18 invariant from the 0.39.0 glossary epic).

## Pre-check: local setup version

Same pattern as `/flow-next:plan` and `/flow-next:audit` — non-blocking notice when `.flow/meta.json` `setup_version` lags the plugin version:

```bash
if [[ -f .flow/meta.json ]]; then
  SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
  PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
  PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
  if [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
    echo "Plugin updated to v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts (current: v${SETUP_VER})." >&2
  fi
fi
```

## Execution Flow

### Phase 0: Route by file state

**0.1 — Ralph block (R17)**

`/flow-next:strategy` is exploratory and human-in-the-loop. Autonomous loops have no business deciding repo strategy. Hard-error with exit 2 when running under Ralph.

```bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
  echo "[STRATEGY: user-triggered only — Ralph cannot run /flow-next:strategy]" >&2
  exit 2
fi
```

No env-var opt-in. Ralph never decides direction.

**0.2 — Read file state**

```bash
STATUS_JSON=$("$FLOWCTL" strategy status --json)
EXISTS=$(printf '%s' "$STATUS_JSON" | jq -r '.exists')
HUSK=$(printf '%s' "$STATUS_JSON" | jq -r '.husk')
SECTIONS_FILLED=$(printf '%s' "$STATUS_JSON" | jq -r '.sections_filled')
GENERATOR_MATCH=$(printf '%s' "$STATUS_JSON" | jq -r '.generator_match')
FILE_PATH=$(printf '%s' "$STATUS_JSON" | jq -r '.file_path // empty')
```

JSON fields (frozen by Task 1):

- `exists` (bool) — file present
- `husk` (bool) — `exists: true` AND `sections_filled == 0`
- `sections_filled` (int) — populated required-section count (0-5)
- `total_sections` (int) — always 5 (the 5 required)
- `last_updated` (str|null) — ISO date from frontmatter
- `file_path` (str|null) — absolute path of resolved STRATEGY.md
- `generator` (str|null) — frontmatter `generator` value
- `generator_match` (bool) — `generator == "flow-next-strategy"`

**0.3 — Subdirectory walk-up surfacing (R16)**

If `file_path` is set and differs from `${PWD}/STRATEGY.md`, surface one line in chat before any question fires:

```
Using repo-root STRATEGY.md at <file_path>.
```

This is the only line printed before routing — keep the noise floor low.

**0.4 — Foreign-file resolution (R15)**

If `exists: true` AND `generator_match: false`, do not write. Fire `AskUserQuestion`:

- `body`: "Found a STRATEGY.md at `<file_path>` not generated by flow-next-strategy (generator: `<generator or "missing">`). Recommended: `keep` — do not overwrite a hand-written or external-tool strategy doc. Confidence: [your-call] — your project, your call."
- `options`:
  - `keep` → exit 0 with one-line stdout: `Keeping existing STRATEGY.md unchanged.`
  - `migrate` → exit 0 with stderr: `Multi-format migration deferred to v2. Either delete or rename the file, then re-run /flow-next:strategy to bootstrap from scratch.`
  - `rewrite` → second confirmation `AskUserQuestion`:
    - `body`: "Confirm destructive overwrite? The existing file at `<file_path>` will be replaced. Recommended: `cancel`. Confidence: [your-call]."
    - `options`: `confirm-overwrite` → proceed to Phase 1 first-run interview; `cancel` → exit 0.

Single-select `AskUserQuestion`, lead-with-recommendation, neutral option labels.

**0.5 — Routing**

After Ralph block, walk-up surfacing, and foreign-file resolution:

| State | Route |
|-------|-------|
| `exists: false` | Phase 1 (first-run interview) |
| `exists: true` AND `husk: true` AND `generator_match: true` | Phase 1 (first-run; husk was probably an aborted run) |
| `exists: true` AND `husk: false` AND `generator_match: true` | Phase 2 (section-revisit update) |

Announce path in one line: `Strategy doc not found — let's write it.` or `Found existing strategy — let's review and update.`

### Phase 1: First-run interview

**1.1 — Load interview rules (non-optional)**

```text
Read `references/interview.md`.
```

This load is non-optional. The pushback rules, anti-pattern examples, and quality bar for each section live there. Improvising from memory produces a passive transcription instead of a strategy doc.

**1.2 — Run the interview in section order**

For each of the 5 required sections (in order: `Target problem` → `Our approach` → `Who it's for` → `Key metrics` → `Tracks`), follow the per-section rule in `references/interview.md`:

- Ask the **opening question** verbatim from the references file.
- Evaluate the answer against the **strong-answer signature**.
- If the answer falls into a named anti-pattern, push back with the **sharper follow-up** — quoting the user's words back at them, NOT paraphrasing. Anti-pattern label names (`vanity`, `fluff`, `feature-list`, etc.) are internal-only — never appear in question bodies.
- **2 rounds maximum.** After round 2, capture the user's words verbatim and append the HTML comment `<!-- worth revisiting -->` to the section body. Do not let the interview spiral.
- Use **free-form responses** — no menu options, no recommendation in the question body.

**1.3 — Per-section atomic writes**

After each section is captured, build the partial draft and write to `STRATEGY.md` via `Write` tool **before the next question fires**. `last_updated` bumps on every save. No draft state file. Mid-flow abandonment leaves a partially-populated file readable on disk; resume is via Phase 0 → Phase 2 routing.

The partial-draft shape: frontmatter + H1 + the captured section(s) + placeholder bodies (`_Not yet captured._`) for unfilled required sections. Optional sections are absent until Phase 1.4.

**1.4 — Optional sections (gated by routing question)**

After all 5 required sections land, ask once per optional section whether to include it. **Routing question** with lead-with-recommendation:

For `Milestones`:

- `body`: "Do you want a `Milestones` section? It's only worth adding if there are externally visible dated anchors — launches, fundraises, conferences, renewals. Recommended: `skip` — internal schedules don't belong here. Confidence: [your-call]."
- `options`: `include`, `skip`.

For `Not working on`:

- `body`: "Do you want a `Not working on` section? Only useful for things the team keeps being tempted by — a clarity tool, not a backlog. Recommended: `skip` — most repos don't need it. Confidence: [your-call]."
- `options`: `include`, `skip`.

A `Marketing` section is **deliberately not offered** — over-rotated for OSS-tools repos.

If `include`, run the per-section interview from `references/interview.md` (same 2-round-cap rule), then atomic-write that section. If `skip`, omit the section entirely from the file (do not leave an empty header).

**1.5 — Mandatory read-back before final commit**

After all sections captured (required + any included optional), run:

```bash
"$FLOWCTL" strategy read --json
```

Show the final draft body in chat. Offer one round of edits via `AskUserQuestion`:

- `body`: "Draft complete. <N>-section strategy doc, <last_updated>. Recommended: `commit` — the draft reflects the captured answers verbatim. Confidence: [judgment-call]."
- `options`: `commit`, `edit-section`, `abandon`.

On `edit-section`, ask which section via single-select (5 required + included optional names), re-run the per-section interview, atomic-write, return to read-back.

On `commit`, the file is already on disk (per-section atomic writes) — this is a confirmation step, not a new write. Acknowledge with one stdout line: `Strategy doc written to <file_path>. last_updated: <date>.`

On `abandon`, leave the file as-is (partially populated is fine), exit 0.

### Phase 2: Update run (file exists, generator matches)

**2.1 — Summarize current state**

Read the existing `STRATEGY.md` via `flowctl strategy read --json` and summarize current state in 3-5 lines so the user sees what's on file. Surface section names + 1-line excerpts.

If the focus-hint argument names a specific section, jump to that section. Otherwise, fire the routing question.

**2.2 — Section-revisit routing question (lead-with-recommendation)**

Build the option list dynamically:

- For each of the 5 required sections + included optional sections, check the body for `<!-- worth revisiting -->` markers (priority candidates).
- Sections with no marker but visibly weak content (≤1 short sentence, or contains placeholder-shaped text) join the priority list.
- Sections that look strong fall to the bottom.

`AskUserQuestion`:

- `body`: "Which section to revisit? <priority sections listed first>. Recommended: `<top priority section>` — it carries a `<!-- worth revisiting -->` marker from a previous run [if applicable]. Confidence: [judgment-call] — your judgment on what feels stale."
- `options`: section names + `done` (no further changes).

**2.3 — Per-section re-interview**

For the chosen section, re-run the per-section interview from `references/interview.md` — full pushback, NOT a rubber-stamp. After capture, atomic-write that section's new body. Untouched sections preserved byte-identical (verified by `git diff --unified=0` if questioned). `last_updated` bumps to today's ISO date.

**2.4 — Loop or exit**

After a section is updated, return to the routing question — user can revisit another section or pick `done`. On `done`, run the read-back step (Phase 1.5 logic) once for confirmation, then exit.

### Phase 3: Downstream handoff

After writing (first-run or update), surface the file's role to the user in one paragraph:

- If `.flow/specs/` is empty (and any legacy `.flow/epics/` is also empty) AND `.flow/prospects/` is empty: `Strategy doc written. Next, /flow-next:prospect [optional focus] generates ranked candidate ideas grounded in the strategy you just captured.`
- If `.flow/` is populated: `Strategy doc written. Downstream skills (/flow-next:prospect, /flow-next:plan, /flow-next:interview, /flow-next:capture, /flow-next:sync) will read STRATEGY.md as grounding on next invocation.`

One paragraph max. No follow-up questions.

## What this skill does not do

- Does not update the issue tracker or reconcile in-flight work. Strategy is the doc; execution lives in specs, tasks, and `/flow-next:plan`.
- Does not write product requirements or implementation plans — those are `/flow-next:capture` and `/flow-next:plan`.
- Does not compute metric values. It records *which* metrics matter and where they live, not what they read today.
- Does not create per-subdirectory STRATEGY.md files. Strategy is repo-wide by Rumelt's definition; cascading strategies re-introduce the "is for everyone, is for no one" problem.
- Does not migrate hand-written or CE-format STRATEGY.md files. v1 ships sentinel-based foreign-file refusal; multi-format migration is a v2 problem.
- Does not delete the file when all sections are removed. Last-section deletion leaves a husk (`# <name> Strategy` H1 + frontmatter) on disk — file never deleted (R23 invariant, mirrors `render_glossary_file`).

## Forbidden

- **Running under Ralph** — hard-block via the Phase 0.1 guard.
- **Setting `context: fork`** — `AskUserQuestion` must stay reachable across phases.
- **Inline cross-platform tool tables** in prose (multi-platform listings naming the tool primitive on each harness). Canonical files use Claude-native names only; sync-codex.sh handles the Codex rewrite.
- **Lead-with-recommendation on substance questions** — problem / approach / persona / metrics / tracks get free-form, no recommendation, no menu. Recommendation primes the user out of their own language. Routing questions only.
- **Leaking anti-pattern names** to the user. `vanity` / `fluff` / `feature-list` / `goal-stated-as-problem` are internal labels for formulating sharper follow-ups.
- **Auto-overwriting a foreign-file STRATEGY.md** — Phase 0.4 always asks. v1's stance is refusal; user can rename or delete to bootstrap.
- **Writing more than 4 sentences per section** (except Tracks, where each track has its own short block). The post-write checklist in `references/strategy-template.md` catches this.
- **Adding sections beyond the locked 5 + 2 optional**. CE's `Marketing` section is dropped on purpose; do not re-introduce it. Section order is locked.
- **Inventing flowctl subcommands** — Task 1 ships `flowctl strategy {status,read,list}` only. Skill writes the file directly via `Write` tool; no `flowctl strategy add` exists.

## Output rules

The deliverable is the written `STRATEGY.md` itself. Surface to chat:

- One-line path announcement at Phase 0 (walk-up subdir or file state).
- Per-section interview Q&A (the agent's questions; user's answers).
- Final draft read-back in Phase 1.5 / 2.4.
- One-paragraph downstream handoff at Phase 3.

No internal summary printed at exit beyond the Phase 3 handoff line. The file IS the report.
