---
name: flow-next-prospect
description: Generate ranked candidate ideas grounded in the repo, upstream of /flow-next:plan. Triggers on /flow-next:prospect with an optional focus hint (concept, path, constraint, or volume).
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task
---

# Prospect — upstream-of-plan idea generation

**Read [workflow.md](workflow.md) for full phase-by-phase execution.**

Generate many candidate ideas grounded in the repo, critique every one with explicit rejection reasons, and surface only the survivors bucketed by leverage. Output is a ranked artifact under `.flow/prospects/<slug>-<date>.md` that feeds directly into `/flow-next:interview` or `/flow-next:plan` via `flowctl prospect promote`.

**Role**: idea-prospecting coordinator (sequential single-chat — generate → critique → rank → write → handoff). Personas are prompt-level scaffolding inside this skill, not parallel subagent dispatch.

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
```

**Inline skill (no `context: fork`)** — keeps `AskUserQuestion` available throughout. Subagents can't call blocking question tools (Claude Code issues #12890, #34592), and Phases 0 + 6 both require user choice. (sync-codex.sh rewrites `AskUserQuestion` to `request_user_input` in the Codex mirror.)

## Input

Arguments: `$ARGUMENTS`

Format: `[focus hint]` — freeform single string. Optional. May be:

- **Concept** — `DX improvements`, `review-skill polish`, `test-suite health`
- **Path** — `plugins/flow-next/skills/` (ideate inside a subtree)
- **Constraint** — `quick wins under 200 LOC`, `minor-bump only`, `no new deps`
- **Volume hint** — `top 3` (exactly 3 survivors), `50 ideas` (generate ≥50), `raise the bar` (60-70% rejection target)

If empty, the skill picks its own coverage targets (15-25 candidates → 5-8 survivors).

## Ralph-block (R8)

`/flow-next:prospect` is exploratory and human-in-the-loop. Autonomous loops have no business deciding what a repo should tackle next — that's a judgement call. Hard-error with exit 2 when running under Ralph.

```bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
  echo "Error: /flow-next:prospect requires a user at the terminal; not compatible with Ralph mode (REVIEW_RECEIPT_PATH or FLOW_RALPH detected)." >&2
  exit 2
fi
```

No env-var opt-in. Ralph never decides direction.

## Workflow

Execute the phases in [workflow.md](workflow.md) in order:

0. **Resume check** — list active artifacts <30d; ask extend / fresh / open via blocking question. Corrupt artifacts surfaced but never offered for extension.
1. **Ground** — scan repo with graceful degradation: git log (30d), open epics, CHANGELOG top, memory matches, memory audit (if present). Emit a structured 30-50 line snapshot — titles + tags only, never raw bodies.
2. **Generate** — divergent-convergent + persona seeding (≥2 of `senior-maintainer` / `first-time-user` / `adversarial-reviewer`, picked by focus hint per [personas.md](personas.md)). One divergent prompt; no self-judging.
3. **Critique** — separate prompt pass that does NOT see the focus hint or persona texts; rejection floor ≥40% (≥60% under `raise the bar`); fixed taxonomy (`duplicates-open-epic | out-of-scope | insufficient-signal | too-large | backward-incompat | other`); floor violation surfaces blocking question with frozen options `regenerate | loosen-floor | ship-anyway`.
4. **Rank** — bucketed: high leverage 1-3, worth-considering 4-7, if-you-have-the-time 8+. Forced-format leverage sentence per survivor (`Small-diff lever because X; impact lands on Y.`); no numeric scores.
5. **Write artifact** — atomic write-then-rename to `.flow/prospects/<slug>-<date>.md` via `flowctl.write_prospect_artifact`. Same-day collisions suffix with `-2`, `-3`. Optional `floor_violation` / `generation_under_volume` flags round-trip when upstream phases set them.
6. **Handoff** — blocking prompt for promote / interview / skip via the platform's question tool; frozen numbered-options fallback when no blocking tool is available.

Phases 0-6 are implemented. Promote command + list/read/archive land in tasks 4-5.

## Pre-check: local setup version

Same pattern as `/flow-next:plan` — non-blocking notice when `.flow/meta.json` `setup_version` lags the plugin version:

```bash
if [[ -f .flow/meta.json ]]; then
  SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
  PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
  [[ -f "$PLUGIN_JSON" ]] || PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.factory-plugin/plugin.json"
  PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
  if [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
    echo "Plugin updated to v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts (current: v${SETUP_VER})." >&2
  fi
fi
```

## Forbidden

- Running under Ralph — hard-block via the guard above.
- Setting `context: fork` — blocking question tools must stay reachable.
- Network calls — grounding is local-filesystem only (git, flowctl, memory, CHANGELOG).
- Writing to `.flow/epics/` directly — only `flowctl prospect promote` may do that.
- Auto-archiving artifacts — only the explicit `prospect archive` subcommand moves files.
- Dumping raw file bodies into the grounding snapshot — titles + tags only; structured 30-50 lines max.
