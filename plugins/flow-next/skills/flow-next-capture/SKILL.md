---
name: flow-next-capture
description: Synthesize the current conversation context into a flow-next spec at `.flow/specs/<spec-id>.md` via `flowctl spec create --plan-file` — agent-native, source-tagged, with a saved-spec summary and editor follow-up. Triggers on /flow-next:capture, "capture spec", "lock down what we discussed", "make a spec from this conversation", "convert conversation to spec". Optional `mode:autofix` token runs without questions and requires `--yes` to write. Optional `--rewrite <spec-id>` overwrites an existing spec; `--from-compacted-ok` overrides the incomplete-evidence refusal after compaction; `--override-strategy` proceeds despite a contradiction with an active STRATEGY.md track (and prompts to record the override as a decision); `--no-plan` sets the spec-level `no_plan` field after the write (explicit opt-in on a user invocation, never inferred there); `from:flow` marks a run dispatched by `/flow-next:flow`, where capture applies the shared plan-versus-no-plan rule and sets the field itself when the rule resolves to direct.
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task
---

# /flow-next:capture — agent-native conversation → spec

A discussion (or a `/flow-next:prospect` survivor) often holds a complete spec that never gets written down, and the next session loses it. Capture is the synthesis step: the host agent extracts the user's turns, drafts a spec against the resolved template, **tags only what it paraphrased or inferred** (`[paraphrase]` / `[inferred]` / `[strategy:<track>]`; the user's verbatim words stay untagged), writes it through flowctl, prints a compact summary, and offers the saved file in the editor ([docs/read-back.md](../../docs/read-back.md)). The capture request authorizes the write; substantive choices still get short questions. No Python synthesizer, no model subprocess.

flowctl supplies thin plumbing (`spec create`, `spec set-plan`, `spec set-branch`, `memory search`) plus the `chart link-spec` callback after a chart-briefing capture. Capture never writes chart files or a chart's `ready` flag; chart never writes `.flow/specs`.

Clear ideas and finished chart briefings route here; capture never manufactures a chart for clear work. Unsure: `/flow-next:flow --explain`.

**Read [workflow.md](workflow.md) for the phases and [phases.md](phases.md) for the source tags.** Branch-specific machinery lives in `references/*.md`, loaded only when its gate fires.

Read [working-rules.md](../../references/working-rules.md) first unless you already have this run; it holds for every step of this skill.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected).
workflow.md's Preamble defines `$FLOWCTL`; later blocks (there and in `phases.md`) use it.

**Inline skill (no `context: fork`)** — `AskUserQuestion` must stay reachable across phases; subagents cannot call blocking question tools.

## Mode Detection

Parse `$ARGUMENTS` for the literal tokens `mode:autofix` and `from:flow` and the flags `--rewrite <spec-id>`, `--from-compacted-ok`, `--yes`, `--override-strategy`, `--no-plan`. Strip recognized tokens; the remainder is ignored (the conversation is the input).

```bash
RAW_ARGS="$ARGUMENTS"
MODE="interactive"
REWRITE_TARGET=""
FROM_COMPACTED_OK=0
COMMIT_YES=0
OVERRIDE_STRATEGY=0

if [[ "$RAW_ARGS" == *"mode:autofix"* ]]; then
  MODE="autofix"
  RAW_ARGS="${RAW_ARGS//mode:autofix/}"
fi

if [[ "$RAW_ARGS" =~ --rewrite[[:space:]]+([^[:space:]]+) ]]; then
  REWRITE_TARGET="${BASH_REMATCH[1]}"
  RAW_ARGS="${RAW_ARGS//--rewrite ${REWRITE_TARGET}/}"
fi

if [[ "$RAW_ARGS" == *"--from-compacted-ok"* ]]; then
  FROM_COMPACTED_OK=1
  RAW_ARGS="${RAW_ARGS//--from-compacted-ok/}"
fi

# --yes (autofix write gate), --override-strategy, --no-plan and from:flow
# authorize durable writes, so they are EXACT-token matches: lookalikes
# ("--yesterday", "--no-planning", "from:flowchart") stay in the remainder.
NO_PLAN_OPT=0
FROM_FLOW=0
CLEANED_ARGS=""
for TOK in $RAW_ARGS; do
  if [ "$TOK" = "--yes" ]; then
    COMMIT_YES=1
  elif [ "$TOK" = "--override-strategy" ]; then
    OVERRIDE_STRATEGY=1
  elif [ "$TOK" = "--no-plan" ]; then
    NO_PLAN_OPT=1
  elif [ "$TOK" = "from:flow" ]; then
    FROM_FLOW=1
  else
    CLEANED_ARGS="$CLEANED_ARGS $TOK"
  fi
done
RAW_ARGS="$CLEANED_ARGS"

if [ "$MODE" = "autofix" ]; then
  echo "GATE ACTIVE — STOP. Read references/autofix-mode.md before continuing."
fi   # default branch: bare no-op — NO link, NO read path
```

| Mode | When | Behavior |
|------|------|----------|
| **Interactive** (default) | User is at the terminal | Asks on duplicates and must-ask cases; writes the spec, shows its summary, offers the editor; no generic write approval |
| **Autofix** (`mode:autofix`) | Batch or scripted invocation | No questions; every ask becomes exit 2; writes only with `--yes` |

When the sentinel prints, read [references/autofix-mode.md](references/autofix-mode.md) before Phase 0; it owns the per-phase autofix rules. On the interactive path, read nothing.

## Questions (interactive only)

Interactive capture follows the working rules' attended contract, plus:

- Use `AskUserQuestion` (load it with `ToolSearch` `select:AskUserQuestion` if needed); plain-text numbered options only when the tool is unreachable. Never skip a question silently.
- The body leads with the recommendation, a one-sentence reason, and a confidence tier (`[high]` / `[judgment-call]` / `[your-call]`; before asking, read [references/confidence-tiers.md](references/confidence-tiers.md)). Option labels stay neutral and state their consequence.
- Plain language: one sentence of stakes, everyday words, a short gloss for any needed term (`R-ID`, `[inferred]`).
- Never ask for facts the conversation already gave. Phase 3 asks only its must-ask cases; other `[inferred]` content surfaces in the summary instead.

## Forbidden behaviors

These protect spec trust:

- **Unstated technology.** "Needs persistence" is fine; "uses PostgreSQL" needs the user to have said it. Capture writes intent; plan writes implementation.
- **Unmarked invention.** An untagged line claims to be the user's words and must be findable in the evidence; every paraphrase or fill-in carries its tag, and `[inferred]` criteria surface in the summary for the user to keep, edit, or drop. Saving never upgrades a tag.
- **Process fences as spec content.** New-vs-rewrite decisions, ready-marking, "do not implement", and the duplicate-scan outcome are capture's lifecycle, never spec body or `## Boundaries` lines, and never evidence lines. Boundaries hold only product constraints a worker could get wrong.
- **Coordinates in the spec body.** State contracts (types, signatures, behaviors, invariants), not code snippets, file paths, or line numbers, unless the exact location is itself the decision. Paths belong in plan's task specs.
- **Silent overwrite.** Replacing a spec needs `--rewrite <spec-id>`; otherwise Phase 0's duplicate branch decides.
- **Acting without its own consent.** Never auto-split (the user picks), never mark ready or add glossary terms without their separate questions (autofix writes neither; seeding an empty glossary is `/flow-next:prime`'s job), never treat a saved spec as implementation consent, and never admit a draft/stale briefing silently or treat a forced draft chart briefing as final (the override names the D-IDs and reads back the risk).
- **Committing.** Capture never stages or commits; the user owns when `.flow/` changes land.
- **`context: fork`.** Blocking questions must stay reachable.

## Workflow

Execute [workflow.md](workflow.md) in order:

The spec at `.flow/specs/<spec-id>.md` is the deliverable. Autofix without `--yes` prints the draft summary and exits 0 with no spec allocated.
