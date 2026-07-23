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
STATUS_JSON=$("$FLOWCTL" strategy status --json 2>/dev/null) || STATUS_JSON=
if ! printf '%s' "$STATUS_JSON" | jq -e '
  type == "object"
  and (.exists | type == "boolean")
  and (.husk | type == "boolean")
  and (.sections_filled as $n
    | ($n | type) == "number"
    and ($n | floor) == $n
    and $n >= 0
    and $n <= 7)
  and (.total_sections as $n
    | ($n | type) == "number"
    and ($n | floor) == $n
    and $n >= 5
    and $n <= 7)
  and (.sections_filled <= .total_sections)
  and (.last_updated == null or (.last_updated | type == "string"))
  and (.file_path == null or (.file_path | type == "string"))
  and (.generator == null or (.generator | type == "string"))
  and (.generator_match | type == "boolean")
  and (.husk == ((.exists == true) and (.sections_filled == 0)))
  and (.generator_match == (.generator == "flow-next-strategy"))
' >/dev/null 2>&1; then
  echo "[STRATEGY: unable to classify STRATEGY.md safely — leaving it unchanged]" >&2
  exit 0
fi
EXISTS=$(printf '%s' "$STATUS_JSON" | jq -r '.exists')
HUSK=$(printf '%s' "$STATUS_JSON" | jq -r '.husk')
SECTIONS_FILLED=$(printf '%s' "$STATUS_JSON" | jq -r '.sections_filled')
GENERATOR_MATCH=$(printf '%s' "$STATUS_JSON" | jq -r '.generator_match')
FILE_PATH=$(printf '%s' "$STATUS_JSON" | jq -r '.file_path // empty')
```

JSON fields (frozen by Task 1):

- `exists` (bool) — file present
- `husk` (bool) — `exists: true` AND `sections_filled == 0`
- `sections_filled` (int) — populated required + included optional-section count (0-7)
- `total_sections` (int) — 5 required + populated optional sections (5-7)
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

Announce the selected path, then load exactly one direct workflow reference:

- First-run: say `Strategy doc not found — let's write it.`, then read and follow `references/first-run.md`.
- Update: say `Found existing strategy — let's review and update.`, then read and follow `references/update.md`.

Do not read the unselected workflow. A foreign file stays entirely in Phase 0.4
unless the user confirms `rewrite`; confirmed rewrite selects the first-run
workflow. Any state not matched by the table is unsafe to classify: leave the
file unchanged and exit 0 with the same safe-classification stderr line from
Phase 0.2.

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
- **Inventing flowctl subcommands** — The supported read surface is `"$FLOWCTL" strategy {status,read}` only. The skill writes the file directly via `Write`; no strategy add/list command exists.

## Output rules

The deliverable is the written `STRATEGY.md` itself. Surface to chat:

- One-line path announcement at Phase 0 (walk-up subdir or file state).
- Per-section interview Q&A (the agent's questions; user's answers).
- Final draft read-back in Phase 1.5 / 2.4.
- One-paragraph downstream handoff at Phase 3.

No internal summary printed at exit beyond the Phase 3 handoff line. The file IS the report.
