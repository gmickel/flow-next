---
name: flow-next-capture
description: Synthesize the current conversation context into a flow-next spec at `.flow/specs/<spec-id>.md` via `flowctl spec create + spec set-plan` — agent-native, source-tagged, with mandatory read-back before write. Triggers on /flow-next:capture, "capture spec", "lock down what we discussed", "make a spec from this conversation", "convert conversation to spec". Optional `mode:autofix` token runs without questions and requires `--yes` to commit. Optional `--rewrite <spec-id>` overwrites an existing spec; `--from-compacted-ok` overrides the incomplete-evidence refusal after compaction; `--override-strategy` proceeds despite a contradiction with an active STRATEGY.md track (and prompts to record the override as a decision).
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task
---

# /flow-next:capture — agent-native conversation → spec

A free-form discussion (or a `/flow-next:prospect` survivor) frequently produces enough material for a complete spec, but stops short of the formal `flowctl spec create` + `spec set-plan` heredoc documented in `CLAUDE.md`. Without an explicit synthesis step, that context decays — the next session loses the conversation, the spec never lands, and the user re-explains the same idea to `/flow-next:plan`.

This skill IS the synthesis. The host agent (Claude Code / Codex / Droid) extracts the recent user turns, drafts a CLAUDE.md-shaped spec with **per-line source tags** (`[user]` / `[paraphrase]` / `[inferred]`), **prints the full draft as ordinary markdown then issues a short approval ask** (print-then-ask — never embed multi-paragraph drafts in `AskUserQuestion` bodies), and only then writes the spec via existing flowctl plumbing. There is no Python synthesizer, no codex / copilot subprocess, no fast-model classifier. The host agent is already an LLM and does the work directly.

flowctl provides only thin spec plumbing (`spec create`, `spec set-plan`, optional `spec set-branch`, `memory search` for duplicate detection). No new flowctl subcommands.

**Read [workflow.md](workflow.md) for the full phase-by-phase execution. Read [phases.md](phases.md) for the must-ask cases lookup, source-tag taxonomy, confidence tiers, and forbidden-behaviors list.**

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
```

| Mode | When | Behavior |
|------|------|----------|
| **Interactive** (default) | User is at the terminal | Phase 0 asks on duplicate detection; Phase 3 asks on must-ask ambiguities; Phase 4 print-then-ask read-back (full draft as ordinary markdown, then short blocking-question tool) — write only on `approve` |
| **Autofix** (`mode:autofix`) | Batch usage from another skill / scripted invocation | No user questions. Phase 0 hard-errors on duplicates / relevant evidence made incomplete by compaction without explicit overrides. Historical compaction signals alone do not block. Phase 3 must-ask cases hard-error (autofix can't ask). Phase 4 Writes the full draft once + prints the summary tally to stdout (autofix path unchanged). **Writes to `.flow/` ONLY when `--yes` is also passed**; without `--yes`, exit 0 with "draft written; rerun with --yes to commit" |

### Autofix mode rules

- **No user questions.** Never call the blocking-question tool.
- **Phase 0 hard-errors:** duplicate detected → list overlapping spec IDs to stderr, exit 2 unless `--rewrite <id>` was passed; relevant capture evidence is missing / truncated / summary-only after compaction → exit 2 unless `--from-compacted-ok` was passed. A historical compaction marker or system-summary block alone is advisory and does not block.
- **Phase 3 must-ask hard-errors:** ambiguous title / untestable acceptance / scope-conflict-with-existing-spec → exit 2 with which case fired and why. Autofix cannot resolve must-ask cases.
- **Phase 4 single emission, no `.flow/` write.** Full draft Written once to the §4.1 draft file (all sections + R-IDs); summary payload (`[inferred]` tally + 8+ acceptance suggestion if applicable) printed to stdout. Without `--yes`, exit 0 with the "rerun with --yes" hint. With `--yes`, proceed to Phase 5 write. (Autofix has no interactive print-then-ask; `--yes` is the consent substitute.)
- **Phase 5 commits identically to interactive once it runs.**
- **Readiness never written.** The mark-ready write (workflow.md §5.9) is interactive-consent-only; autofix prints a footer suggestion at most (and only when readiness is adopted, no `tracker.readyState`, and the spec was written). The `--rewrite` readiness reset (§5.3) still runs — it is idempotent plumbing, not a consent question.

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
- **Using `git add -A` from this skill.** When committing the new spec, stage only the JSON sidecar (`.flow/specs/<id>.json`) + `.flow/specs/<id>.md` (and `.flow/meta.json` if the next-id counter mutated). Other working-tree changes are not capture's concern.

## Workflow

Execute the phases in [workflow.md](workflow.md) in order:

0. **Pre-flight** — duplicate detection (scan `.flow/specs/` + `flowctl memory search` on extracted keywords); compaction relevance check (refuse only when the evidence needed for this capture is missing / truncated / summary-only, not merely because history contains a compaction signal); idempotency (refuse silent overwrite without `--rewrite`).
1. **Extract conversation evidence** — build a verbatim `## Conversation Evidence` block FIRST (raw quotes from recent user turns, capped ~30 lines). Spec sections refer to it by line, not from agent memory.
2. **Source-tagged synthesis** — draft each section with per-line tags (`[user]` / `[paraphrase]` / `[inferred]`). Apply the canonical template at [`plugins/flow-next/templates/spec.md`](../../templates/spec.md) (per R17 — cross-link, never re-embed the section list inline). At runtime the template is resolved via the 4-tier discovery cascade — first match wins: `<repo_root>/SPEC.md` → `<repo_root>/spec.md` → `.flow/templates/spec.md` → bundled `${PLUGIN_ROOT}/templates/spec.md`. The bundled file is the canonical source of truth; earlier tiers are user-customized overrides. Route explicit biz-context signals (nine SIGNAL CATEGORIES per fn-44 R24, only `[user]` / `[paraphrase]` tags) to their destinations; sections without conversation signal stay absent. Compute `BIZ_SIGNAL_CATEGORIES` (0..9) for Phase 6's R25 dispatch.
3. **Must-ask cases (R9)** — interactive only; autofix exits 2 if any fire. Hard-error conditions: ambiguous title / untestable acceptance / scope-conflict. Optional ambiguities use lead-with-recommendation + confidence tier.
4. **Read-back loop (mandatory, even in autofix)** — Write the full draft ONCE to a literal unique path (workflow.md §4.1). **Interactive print-then-ask (R13):** print the FULL draft markdown (and rewrite-mode diff when applicable) as an ordinary assistant message FIRST, then issue a SHORT `AskUserQuestion` — one-line pointer + compact `[inferred]` tally/warnings + options only; never embed multi-paragraph drafts, diffs, or criteria lists in the ask body (they render as collapsed plain text). Never `Recommended: approve` while unverified `[inferred]` items exist (workflow.md §4.2). Interactive: `approve` / `edit` / `abort`; edit cycles revise via Edit + full-file Read + **reprint the revised draft** before each short re-ask. When 8+ acceptance criteria: include `consider splitting?` as an option (R11). When the glossary is populated (`total_terms > 0`) and the conversation surfaced new project vocabulary: surface term-add proposals + a consent question after approve (workflow.md §2.7 / §4.2; writes land in §5.8). With no `tracker.readyState`, a new capture in a repo with adopted local readiness offers one `Mark ready?` question; a rewrite offers it only when the target itself was ready before the rewrite. An unrelated ready spec never prompts on a draft rewrite. The copy explains Pilot/autonomous eligibility; default keep-draft (workflow.md §4.2; write lands in §5.9). Autofix: prints summary payload to stdout; requires `--yes` to commit; term proposals print as suggestions, never written; readiness never written (autofix path unchanged).
5. **Write via flowctl** — `flowctl spec create --title "..." --json` → parse `id` → `flowctl spec set-plan <id> --file <literal draft path> --json` (consumes the §4.1 draft file — no heredoc re-authoring). Optional `flowctl spec set-branch` if user named one. Capture creates fresh specs; allocate R-IDs sequentially from R1. `--rewrite` resets readiness via idempotent `spec unready` (§5.3); consented mark-ready lands via `spec ready` (§5.9). When `artifacts.html.enabled` is true, Phase 5 closes by regenerating the spec render lens at `.flow/artifacts/<id>/spec.html` per the shared disclosure reference ([`plugins/flow-next/references/html-artifacts.md`](../../references/html-artifacts.md)) and replacing the spec's artifact link line in place (workflow.md §5.10); the Phase 6 footer then names the artifact path. With the mode off/unset there is zero artifact-related behavior or output.
6. **Suggested next step** — print `Spec captured at .flow/specs/<id>.md.` plus `/flow-next:plan <id>` and `/flow-next:interview <id>` next-step hints. The R25 business-pass suggestion fires when the captured conversation names 1-2 distinct R24 signal categories (the same `1 <= n < 3` rule), agent-judged. When it fires, append the `/flow-next:interview --scope=business` suggestion line.

## Output rules

The new spec is the deliverable — it lives in `.flow/specs/<spec-id>.md` after Phase 5. Standard output also receives:

- The full draft (Phase 4) — interactive: printed as ordinary markdown then a short approval ask (print-then-ask); autofix: Written to the §4.1 path with summary payload on stdout. Edit cycles reprint the revised draft before each short re-ask.
- The created spec id + spec path (Phase 5).
- The next-step footer (Phase 6).

Autofix mode without `--yes` produces a draft + the "rerun with --yes" hint and exits 0 — no write happens, no spec is allocated.
