---
name: flow-next-capture
description: Synthesize the current conversation context into a flow-next spec at `.flow/specs/<spec-id>.md` via `flowctl spec create + spec set-plan` — agent-native, source-tagged, with mandatory read-back before write. Triggers on /flow-next:capture, "capture spec", "lock down what we discussed", "make a spec from this conversation", "convert conversation to spec". Optional `mode:autofix` token runs without questions and requires `--yes` to commit. Optional `--rewrite <spec-id>` overwrites an existing spec; `--from-compacted-ok` overrides the incomplete-evidence refusal after compaction; `--override-strategy` proceeds despite a contradiction with an active STRATEGY.md track (and prompts to record the override as a decision).
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task
---

# /flow-next:capture — agent-native conversation → spec

A free-form discussion (or a `/flow-next:prospect` survivor) frequently produces enough material for a complete spec, but stops short of the formal `flowctl spec create` + `spec set-plan` heredoc documented in `CLAUDE.md`. Without an explicit synthesis step, that context decays — the next session loses the conversation, the spec never lands, and the user re-explains the same idea to `/flow-next:plan`.

This skill IS the synthesis. The host agent (Claude Code / Codex / Droid) extracts the recent user turns, drafts a CLAUDE.md-shaped spec with **per-line source tags** (`[user]` / `[paraphrase]` / `[inferred]` / `[strategy:<track>]`), **prints the full draft as ordinary markdown then issues a short approval ask** (print-then-ask — never embed multi-paragraph drafts in `AskUserQuestion` bodies), and only then writes the spec via existing flowctl plumbing. There is no Python synthesizer, no codex / copilot subprocess, no fast-model classifier. The host agent is already an LLM and does the work directly.

flowctl provides thin spec plumbing (`spec create`, `spec set-plan`, optional `spec set-branch`, `memory search` for duplicate detection) plus the chart handoff callback (`chart link-spec`) after a successful chart-briefing capture. Capture never writes chart files and never mutates a chart's `ready` flag; chart never writes `.flow/specs`.

### Routing boundary (fn-135 / guide matrix)

Clear meaningful ideas and finished chart briefings route **here** - to capture (or direct spec authoring). Capture does **not** manufacture a chart for clear work. When intent and boundaries are already stateable, skip chart (`signal absent`). After a structured brief lands, narrow or skip interview only once read-back proves no material gaps - never pre-skip interview on hope. Unsure: `/flow-next:guide`.

**Read [workflow.md](workflow.md) for the full phase-by-phase execution. Read [phases.md](phases.md) for the source-tag taxonomy and confidence tiers.** Path-specific machinery lives in `references/*.md`, loaded only when the gate at its branch point fires — a run that never takes a branch never pays for it.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md` / `phases.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**Inline skill (no `context: fork`)** — `AskUserQuestion` must stay reachable across phases. Subagents can't call blocking question tools (Claude Code issues #12890, #34592). Phase 0 (duplicate detection) and Phase 4 (read-back loop) both require user choice in interactive mode. (sync-codex.sh rewrites this to a plain-text numbered prompt in the Codex mirror.)

## Mode Detection

Parse `$ARGUMENTS` for the literal token `mode:autofix` and the flags `--rewrite <spec-id>`, `--from-compacted-ok`, `--yes`, `--override-strategy`. Strip recognized tokens; whatever remains is treated as freeform context (ignored — the conversation is the input, not `$ARGUMENTS`).

```bash
RAW_ARGS="$ARGUMENTS"
MODE="interactive"
REWRITE_TARGET=""
FROM_COMPACTED_OK=0
COMMIT_YES=0
OVERRIDE_STRATEGY=0

# Mode token
if [[ "$RAW_ARGS" == *"mode:autofix"* ]]; then
  MODE="autofix"
  RAW_ARGS="${RAW_ARGS//mode:autofix/}"
fi

# --rewrite <id>
if [[ "$RAW_ARGS" =~ --rewrite[[:space:]]+([^[:space:]]+) ]]; then
  REWRITE_TARGET="${BASH_REMATCH[1]}"
  RAW_ARGS="${RAW_ARGS//--rewrite ${REWRITE_TARGET}/}"
fi

# --from-compacted-ok
if [[ "$RAW_ARGS" == *"--from-compacted-ok"* ]]; then
  FROM_COMPACTED_OK=1
  RAW_ARGS="${RAW_ARGS//--from-compacted-ok/}"
fi

# --yes (autofix commit gate)
if [[ "$RAW_ARGS" == *"--yes"* ]]; then
  COMMIT_YES=1
  RAW_ARGS="${RAW_ARGS//--yes/}"
fi

# --override-strategy (Phase 5.0 strategy-contradiction override)
if [[ "$RAW_ARGS" == *"--override-strategy"* ]]; then
  OVERRIDE_STRATEGY=1
  RAW_ARGS="${RAW_ARGS//--override-strategy/}"
fi

if [ "$MODE" = "autofix" ]; then
  echo "GATE ACTIVE — STOP. Read references/autofix-mode.md before continuing."
fi   # default branch: bare no-op — NO link, NO read path
```

| Mode | When | Behavior |
|------|------|----------|
| **Interactive** (default) | User is at the terminal | Phase 0 asks on duplicate detection; Phase 3 asks on must-ask ambiguities; Phase 4 print-then-ask read-back (full draft as ordinary markdown, then short blocking-question tool) — write only on `approve` |
| **Autofix** (`mode:autofix`) | Batch usage from another skill / scripted invocation | No user questions; every "ask" branch becomes exit 2; Phase 4 Writes the draft once and requires `--yes` to reach the `.flow/` write |

When the sentinel above prints, read [references/autofix-mode.md](references/autofix-mode.md) before Phase 0 — it owns the per-phase autofix rules (Phase 0 hard-errors, Phase 3 exits, §4.4 read-back substitute, split / glossary / readiness behavior). On the default interactive path, read nothing.

## Ralph-block (R13) — runs first, before everything else

`/flow-next:capture` requires conversation context + user confirmation. Autonomous loops have neither. Hard-error with exit 2 when running under Ralph.

```bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
  echo "Error: /flow-next:capture requires conversation context + a user at the terminal; not compatible with Ralph mode (REVIEW_RECEIPT_PATH or FLOW_RALPH detected)." >&2
  exit 2
fi
```

No env-var opt-in. Ralph never decides direction.

## Interaction Principles (interactive mode only)

In autofix mode, skip user questions entirely and apply the rules in the autofix reference.

In interactive mode:

- Ask **one question at a time** via `AskUserQuestion` (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded). Fall back to numbered options in plain text only if the tool is unreachable or errors. Never silently skip the question.
- **Lead with the recommended option** and a one-sentence rationale, followed by a confidence marker — `[high]` / `[judgment-call]` / `[your-call]`. The body carries the recommendation; option labels stay neutral so the user isn't anchored on the option text itself. (See [phases.md](phases.md) §Confidence tiers.) **Exception — the Phase 4 read-back never recommends `approve` while unverified `[inferred]` items exist** (no self-blessing; workflow.md §4.2).
- **Plain language, explained answers** (same contract as the interview skill, eval-validated): open with one sentence of stakes; everyday words; a needed term of art gets a ≤1-clause plain gloss at first use; no unexplained acronyms or tool shorthand (`R-ID`, `[inferred]` get translated when user-facing); option descriptions state their consequence ("Choose this if…"). Priorities, not length caps — trim repetition and background, never required content.
- Prefer **multiple choice** when natural options exist (Phase 0 duplicate decision; Phase 4 approve/edit/abort).
- **Do not ask the user for facts** they already gave you in conversation — Phase 1 extracts evidence first; Phase 3 asks only on the three hard-error must-ask cases plus genuinely missing context that can't be inferred.

The goal is automated synthesis with human oversight on judgment calls — not a question for every section.

## Forbidden behaviors (R10)

- **Tech-stack mentions the user did not state.** "Needs persistence" is fine; "uses PostgreSQL" needs the user to have said PostgreSQL. Defer technology choices to `/flow-next:plan` (spec-kit convention — capture writes intent, plan writes implementation).
- **Inventing acceptance criteria not in conversation.** Every acceptance criterion must be source-tagged; pure `[inferred]` criteria must surface at Phase 4 read-back so the user can reject them.
- **Code snippets or specific file paths in the spec body.** Those belong in `/flow-next:plan` task specs after research lands. Capture's output is a high-level spec, not an implementation guide.
- **Silent overwrite of an existing spec.** Idempotency requires `--rewrite <spec-id>` (R8). Without it, Phase 0 conflict-detection branches into extend / supersede / proceed-anyway.
- **Auto-splitting a spec that has 8+ acceptance criteria.** Phase 4 surfaces the option to split; the user decides. Never auto-action a split.
- **Setting `context: fork`** — blocking-question tools must stay reachable.
- **Calling `flowctl spec create` before Phase 4 approval.** Phase 5 is the only write phase.
- **Writing glossary terms without consent, or in autofix mode.** Term-adds require the Phase 4.2 `Glossary?` approval; autofix prints suggestions only (`--yes` consents to the spec write, not to vocabulary changes). The gate is husk-aware (`glossary list --json` `total_terms > 0`) — seeding an empty glossary is `/flow-next:prime`'s job, never capture's.
- **Marking a spec ready without consent, in autofix, or outside the target-aware readiness predicate.** Readiness is the human's gate — capture never infers it.
- **Treating a forced draft chart briefing as final, or admitting a draft/stale briefing silently.** Fail closed; the override requires named D-IDs + a risk read-back.
- **Using `git add -A` from this skill.** When committing the new spec, stage only the JSON sidecar (`.flow/specs/<id>.json`) + `.flow/specs/<id>.md` (and `.flow/meta.json` if the next-id counter mutated). Other working-tree changes are not capture's concern.

## Workflow

Execute the phases in [workflow.md](workflow.md) in order. Each phase's detail — including which branch gate loads which reference — lives there; this index is navigation only:

0. **Pre-flight** — duplicate detection (spec-title overlap + `flowctl memory search`), compaction relevance check, idempotency (never a silent overwrite), plus the strategy / duplicate-branch / chart-briefing / rewrite gates.
1. **Extract conversation evidence** — a verbatim `## Conversation Evidence` block FIRST (~30 lines of raw user quotes); spec sections refer to evidence by line, not from agent memory.
2. **Source-tagged synthesis** — draft each section against the canonical template at [`plugins/flow-next/templates/spec.md`](../../templates/spec.md) (per R17 — cross-link, never re-embed the section list inline), tagging **only acceptance criteria and prose capture newly authors**; route explicit biz-context signals (nine R24 categories) and compute `BIZ_SIGNAL_CATEGORIES` for Phase 6.
3. **Must-ask cases (R9)** — ambiguous title / untestable acceptance / scope-conflict; interactive asks one at a time, autofix exits 2.
4. **Read-back loop (mandatory, even in autofix)** — Write the full draft ONCE to a literal path, print it as ordinary markdown, then a SHORT `AskUserQuestion`; never `Recommended: approve` while unverified `[inferred]` items remain.
5. **Write via flowctl** — `spec create` → parse `id` → `spec set-plan <id> --file <literal draft path>` (consumes the §4.1 draft file — no heredoc re-authoring); R-IDs allocate sequentially from R1.
6. **Suggested next step** — `Spec captured at .flow/specs/<id>.md.` plus the mandatory `Tracker sync:` slot and `/flow-next:plan` / `/flow-next:interview` hints; the R25 business-pass suggestion fires at `1 <= BIZ_SIGNAL_CATEGORIES < 3`.

## Output rules

The new spec is the deliverable — it lives in `.flow/specs/<spec-id>.md` after Phase 5. Standard output also receives:

- The full draft (Phase 4) — interactive: printed as ordinary markdown then a short approval ask (print-then-ask); autofix: Written to the §4.1 path with summary payload on stdout. Edit cycles reprint the revised draft before each short re-ask.
- The created spec id + spec path (Phase 5).
- The next-step footer (Phase 6).

Autofix mode without `--yes` produces a draft + the "rerun with --yes" hint and exits 0 — no write happens, no spec is allocated.
