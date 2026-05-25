---
name: flow-next-capture
description: Synthesize the current conversation context into a flow-next spec at `.flow/specs/<spec-id>.md` via `flowctl spec create + spec set-plan` — agent-native, source-tagged, with mandatory read-back before write. Triggers on /flow-next:capture, "capture spec", "lock down what we discussed", "make a spec from this conversation", "convert conversation to spec". Optional `mode:autofix` token runs without questions and requires `--yes` to commit. Optional `--rewrite <spec-id>` overwrites an existing spec; `--from-compacted-ok` overrides the compaction-detection refusal; `--override-strategy` proceeds despite a contradiction with an active STRATEGY.md track (and prompts to record the override as a decision).
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task
---

# /flow-next:capture — agent-native conversation → spec

A free-form discussion (or a `/flow-next:prospect` survivor) frequently produces enough material for a complete spec, but stops short of the formal `flowctl spec create` + `spec set-plan` heredoc documented in `CLAUDE.md`. Without an explicit synthesis step, that context decays — the next session loses the conversation, the spec never lands, and the user re-explains the same idea to `/flow-next:plan`.

This skill IS the synthesis. The host agent (Claude Code / Codex / Droid) extracts the recent user turns, drafts a CLAUDE.md-shaped spec with **per-line source tags** (`[user]` / `[paraphrase]` / `[inferred]`), shows the full draft back via `AskUserQuestion`, and only then writes the spec via existing flowctl plumbing. There is no Python synthesizer, no codex / copilot subprocess, no fast-model classifier. The host agent is already an LLM and does the work directly.

flowctl provides only thin spec plumbing (`spec create`, `spec set-plan`, optional `spec set-branch`, `memory search` for duplicate detection). No new flowctl subcommands.

**Read [workflow.md](workflow.md) for the full phase-by-phase execution. Read [phases.md](phases.md) for the must-ask cases lookup, source-tag taxonomy, confidence tiers, and forbidden-behaviors list.**

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md` / `phases.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
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
```

| Mode | When | Behavior |
|------|------|----------|
| **Interactive** (default) | User is at the terminal | Phase 0 asks on duplicate detection; Phase 3 asks on must-ask ambiguities; Phase 4 read-back via blocking-question tool — write only on `approve` |
| **Autofix** (`mode:autofix`) | Batch usage from another skill / scripted invocation | No user questions. Phase 0 hard-errors on duplicates / compaction without explicit overrides. Phase 3 must-ask cases hard-error (autofix can't ask). Phase 4 prints full draft + tally to stdout. **Writes ONLY when `--yes` is also passed**; without `--yes`, exit 0 with "draft printed; rerun with --yes to commit" |

### Autofix mode rules

- **No user questions.** Never call the blocking-question tool.
- **Phase 0 hard-errors:** duplicate detected → list overlapping spec IDs to stderr, exit 2 unless `--rewrite <id>` was passed; compaction detected → exit 2 unless `--from-compacted-ok` was passed.
- **Phase 3 must-ask hard-errors:** ambiguous title / untestable acceptance / scope-conflict-with-existing-spec → exit 2 with which case fired and why. Autofix cannot resolve must-ask cases.
- **Phase 4 print-only.** Full draft printed to stdout (frontmatter + all sections + R-IDs + `[inferred]` tally + 8+ acceptance suggestion if applicable). Without `--yes`, exit 0 with the "rerun with --yes" hint. With `--yes`, proceed to Phase 5 write.
- **Phase 5 commits identically to interactive once it runs.**

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

In autofix mode, skip user questions entirely and apply the rules above.

In interactive mode:

- Ask **one question at a time** via `AskUserQuestion` (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded). Fall back to numbered options in plain text only if the tool is unreachable or errors. Never silently skip the question.
- **Lead with the recommended option** and a one-sentence rationale, followed by a confidence marker — `[high]` / `[judgment-call]` / `[your-call]`. The body carries the recommendation; option labels stay neutral so the user isn't anchored on the option text itself. (See [phases.md](phases.md) §Confidence tiers.)
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
- **Using `git add -A` from this skill.** When committing the new spec, stage only the JSON sidecar (`.flow/specs/<id>.json` post-1.0; `.flow/epics/<id>.json` on alias-mode 0.x repos that haven't migrated yet) + `.flow/specs/<id>.md` (and `.flow/meta.json` if the next-id counter mutated). Other working-tree changes are not capture's concern.

## Pre-check: local setup version

Same pattern as `/flow-next:audit` and `/flow-next:prospect` — non-blocking notice when `.flow/meta.json` `setup_version` lags the plugin version:

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

## Workflow

Execute the phases in [workflow.md](workflow.md) in order:

0. **Pre-flight** — duplicate detection (scan `.flow/specs/` + `.flow/epics/` for legacy alias-mode repos + `flowctl memory search` on extracted keywords); compaction detection (scan transcript for truncation markers); idempotency (refuse silent overwrite without `--rewrite`).
1. **Extract conversation evidence** — build a verbatim `## Conversation Evidence` block FIRST (raw quotes from recent user turns, capped ~30 lines). Spec sections refer to it by line, not from agent memory.
2. **Source-tagged synthesis** — draft each section with per-line tags (`[user]` / `[paraphrase]` / `[inferred]`). Apply the canonical template at [`plugins/flow-next/templates/spec.md`](../../templates/spec.md) (per R17 — cross-link, never re-embed the section list inline). At runtime the template is resolved via the 4-tier discovery cascade — first match wins: `<repo_root>/SPEC.md` → `<repo_root>/spec.md` → `.flow/templates/spec.md` → bundled `${PLUGIN_ROOT}/templates/spec.md`. The bundled file is the canonical source of truth; earlier tiers are user-customized overrides. Route explicit biz-context signals (nine SIGNAL CATEGORIES per fn-44 R24, only `[user]` / `[paraphrase]` tags) to their destinations; sections without conversation signal stay absent. Compute `BIZ_SIGNAL_CATEGORIES` (0..9) for Phase 6's R25 dispatch.
3. **Must-ask cases (R9)** — interactive only; autofix exits 2 if any fire. Hard-error conditions: ambiguous title / untestable acceptance / scope-conflict. Optional ambiguities use lead-with-recommendation + confidence tier.
4. **Read-back loop (mandatory, even in autofix)** — show full draft + R-ID list + `[inferred]` tally via `AskUserQuestion` (interactive) or print to stdout (autofix). Interactive: `approve` / `edit` / `abort`. When 8+ acceptance criteria: include `consider splitting?` as an option (R11). Autofix: requires `--yes` to commit.
5. **Write via flowctl** — `flowctl spec create --title "..." --json` → parse `id` → `flowctl spec set-plan <id> --file - --json <<heredoc>`. Optional `flowctl spec set-branch` if user named one. Capture creates fresh specs; allocate R-IDs sequentially from R1.
6. **Suggested next step** — print `Spec captured at .flow/specs/<id>.md.` plus `/flow-next:plan <id>` and `/flow-next:interview <id>` next-step hints. When `BIZ_SIGNAL_CATEGORIES` triggers `flowctl scope suggest` (R25 fire/no-fire threshold lives in flowctl — skill never re-implements the math inline), append the `/flow-next:interview --scope=business` suggestion line.

## Output rules

The new spec is the deliverable — it lives in `.flow/specs/<spec-id>.md` after Phase 5. Standard output also receives:

- The full draft (Phase 4) — interactive shows it inside the read-back; autofix prints it as the report.
- The created spec id + spec path (Phase 5).
- The next-step footer (Phase 6).

Autofix mode without `--yes` produces a draft + the "rerun with --yes" hint and exits 0 — no write happens, no spec is allocated.
