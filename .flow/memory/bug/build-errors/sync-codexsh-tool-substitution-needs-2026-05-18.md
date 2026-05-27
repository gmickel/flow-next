---
title: sync-codex.sh tool-substitution needs prose surgery + context-aware injection
date: "2026-05-18"
track: bug
category: build-errors
module: scripts/sync-codex.sh
tags: [sync-codex, codex, mirror, fn-45, AskUserQuestion, tool-rewrites, injection, markdown-tables, fenced-code-blocks, fn-50, FLOWCTL, prelude, agents, scouts, symmetry-gap]
problem_type: build-error
symptoms: "Codex impl-review NEEDS_WORK cycles: injection inside tables/code-blocks, contradictions with auto-fix mandates, structured-tool prose surviving token rewrite, anti-patterns inverted on Codex"
root_cause: "Token-only AskUserQuestion → plain-text-prompt rewrite leaves Claude-specific structured-tool prose (multiSelect, blocking-question, JSON questions array, deferred-tool schema-loader) intact, and 'first non-negative occurrence' injection lands inside tables, code blocks, and deterministic Ralph branches"
resolution_type: fix
last_updated: "2026-05-26"
---

## Problem

fn-45.1 replaced `scripts/sync-codex.sh` Stage 3 sed rewrite (canonical `AskUserQuestion` → `request_user_input`) with a Python heredoc that rewrites canonical Claude `AskUserQuestion` invocations into a plain-text numbered-prompt instruction for the Codex mirror. Initial implementation went through 4 codex impl-review NEEDS_WORK cycles before SHIPping. The transform contract is more subtle than "swap tokens".

## What Didn't Work

**Naive injection of the R2 instruction block at "first non-negative occurrence"**:
- Landed in markdown table rows (broke `flow-next-interview/questions-shared.md` + `prime/pillars.md` tables)
- Landed inside fenced bash code blocks (split `make-pr/workflow.md` line 111 example)
- Landed in deterministic Ralph-mode prose (e.g. "Phase 4 skips the ... preview entirely") and "What X is NOT" reference bullets (e.g. `capture/phases.md`)
- Landed before "Never use ... in this loop" auto-fix-loop mandates — direct contradiction

**Token-only rewrites left semantic landmines**:
- "DO NOT output questions as text" / "DO NOT list questions in your response" interview anti-patterns: these guarded against AskUserQuestion-era plain-text output, but on Codex plain-text IS the contract — direct contradiction with R2 instruction
- "Anti-pattern (WRONG)" block in `interview/SKILL.md` showed a literal "Question 1:" numbered prompt as WRONG — but that IS the correct pattern on Codex
- "multiSelect: true" directive, "Build the questions array", "blocking question tool" — Claude AskUserQuestion JSON-shape references that don't exist on Codex
- "deferred tool — call to load its schema" prose meaningless on Codex (no schema)
- "The tool provides an interactive UI" framing misleading for plain text

**ToolSearch stripper ordering bug**:
- Generic `Call/call \`ToolSearch\` ...` regex ran BEFORE the more specific `If <X>'s schema isn't loaded ..., call \`ToolSearch\` ...` regex
- The generic regex ate the suffix, leaving dangling fragment "If plain-text numbered prompt's schema isn't loaded on Claude Code," with no completing clause

## Solution

**Strict active-ask anchoring** (`scripts/sync-codex.sh` Stage 3 injection block):
- New `ACTIVE_ASK_VERBS` regex requires anchor lines to contain a verb signaling an actual user-facing ask ("Ask", "Use", "Default to", "Render", "Format the question", "Surface", "Fire", "Present", "Show", "Call", "Invoke", "via plain-text numbered prompt", "MUST ask|use")
- `is_negative_context()` catches "Never use", "do NOT use", "skips the ... preview", "no plain-text ... call", "without prompt call", "It|This|That is not" patterns
- `is_table_line()` skips lines starting with `|` or `|-` (markdown tables)
- Anchor-finder tracks fenced-code-block state — no injection inside ``` ... ``` regions

**Comprehensive structured-tool prose rewrites**:
- 12 explicit re.sub patterns covering: `multiSelect: true` directive, `Build the questions array`, `built questions array`, `blocking question tool` + multi-line bold + hyphenated variants, `platform blocking question tool`, `Per-finding blocking question`, `the (platform) blocking tool`, `via (a|the)? blocking question`, bold `**blocking question**`, bare `blocking question`, `no blocking tool is available/reachable`, `blocking prompt`, `the platform's question tool`, `deferred tool — call ...`, `The tool provides an interactive UI`

**Interview anti-pattern surgery**:
- Strip `- DO NOT output questions as text` and `- DO NOT list questions in your response` bullets entirely
- Strip the inverted `**Anti-pattern (WRONG)**: \n``` Question 1: ... ``` \n **Correct pattern**:` block
- Rewrite "per tool call" → "per prompt turn", "tool call(s)" → "prompt turn(s)"

**ToolSearch stripper reorder + belt-and-suspenders**:
- Move `If <X>'s schema isn't loaded ..., call \`ToolSearch\` ...` regex BEFORE generic `Call/call \`ToolSearch\` ...` regex
- Add fallback regex that strips dangling `If <X>'s schema isn't loaded on Claude Code,` fragments (no completing clause)

**Breadcrumb-strip newline tolerance**:
- Change `r' *\(sync-codex\.sh rewrites...'` to `r' *\(sync-codex\.sh\s+rewrites...'` so multi-line parentheticals are handled

## Prevention

- **Sync mirror review tasks should be run through Codex impl-review specifically.** RP/Claude can't see Codex-specific contract violations as easily — the Codex reviewer immediately flagged contradictions like "DO NOT output as text" + "ask in plain text".
- **For any tool-substitution sync rewrite**, write rewrite-then-eat-residue patterns. Token substitution alone leaves semantic landmines:
  - prose describing the OLD tool's API (multiSelect, JSON questions array, blocking-question framing)
  - anti-patterns guarding against output styles that are now the contract
  - "deferred tool" / "load its schema" mechanisms that don't exist on the new platform
- **Test injection logic across context types**: markdown tables, fenced code blocks, bullet lists describing "what X is", "what X is NOT", and Ralph/deterministic branches. The "first match" anchor is brittle.
- **Strip-and-regex order matters when patterns overlap**: longer-specific stripper must run BEFORE shorter-generic stripper. Add belt-and-suspenders regex for dangling fragments when the order assumption is fragile.
- **Verify byte-identical idempotency on every transform change** (`find codex -type f -name '*.md' -exec md5sum {} + | sort | md5sum` before/after second run).

## Update 2026-05-26

## Problem

`scripts/sync-codex.sh` had two parallel transformation pipelines for the Codex mirror — one for skills (`.md` files copied wholesale) and one for agents (`.md` parsed into `.toml` developer_instructions). The skill pipeline at line ~183 correctly rewrote `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl` → `$HOME/.codex/scripts/flowctl` and injected a local fallback. The agent pipeline did NOT — it just copied the body verbatim into the TOML triple-quoted string.

fn-50.3 added `repo-map list --json` probes to `repo-scout.md` and `context-scout.md` (Step 0 — pre-computed feature index). Those probes use the canonical `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` form. In Claude/Droid this resolves correctly; in Codex, NEITHER env var is set, so the expansion produces `/scripts/flowctl` — broken path. The probe failed silently and the scouts silently lost their map enrichment on Codex.

`worker.toml` had the same latent bug in its memory-capture block (fn-50.6 reviewer auto-capture template).

## What Didn't Work

Catching this via existing R6 / R30 / R17 sync validators — those guards check for forbidden VOCABULARY (`AskUserQuestion`, `epic*` aliases, DDD jargon), not broken PATHS in agent bodies. The validators ran clean while the bug was live in the mirror.

## Solution

Mirror the skill-side rewrite in the agent generator at `scripts/sync-codex.sh:~1272` (right before the backslash escape for TOML triple-quoting):

```bash
body="$(echo "$body" | sed -E 's|\$\{DROID_PLUGIN_ROOT:-\$\{CLAUDE_PLUGIN_ROOT\}\}/scripts/flowctl|$HOME/.codex/scripts/flowctl|g')"
body="$(echo "$body" | awk '
  /^[[:space:]]*FLOWCTL="\$HOME\/\.codex\/scripts\/flowctl"[[:space:]]*$/ {
    print
    indent = ""
    i = 1
    while (i <= length($0) && substr($0, i, 1) ~ /[[:space:]]/) {
      indent = indent substr($0, i, 1)
      i++
    }
    printf "%s[ -x \"$FLOWCTL\" ] || FLOWCTL=\".flow/bin/flowctl\"\n", indent
    next
  }
  { print }
')"
```

POSIX awk only — `match($0, regex, arr)` 3-arg is gawk-only and breaks on macOS. The leading-whitespace detection loop preserves indentation so embedded bash blocks stay aligned.

Idempotent across consecutive syncs (md5sum-of-md5sums stable).

Caught by Codex impl-review run with `--base <branch-from-main>` instead of `--base <task-base>` — the wider scope let the reviewer see ALL the canonical agents that fn-50.3 had modified and notice the mirror missed the rewrite.

## Prevention

**Symmetry rule for sync-codex.sh**: whenever a transformation is needed on Codex mirror SKILLS, audit whether the same transformation is needed on Codex mirror AGENTS. The two pipelines are parallel, not unified — and silently diverge.

**Validation gap**: add a sync-codex.sh guard that fails if any `plugins/flow-next/codex/agents/*.toml` body still contains `DROID_PLUGIN_ROOT` or `CLAUDE_PLUGIN_ROOT` outside the documented Codex-mirror exception sites. The skill-side has similar guards; agents had none.

**Review-scope discipline**: scoped impl-review (`--base <prior-commit>`) is the default for incremental tasks, but for final-integration tasks like fn-50.6 (release plumbing, cross-cutting changes), re-run with `--base <branch-from-main>` so the reviewer audits the whole feature surface. Otherwise the reviewer can't see whether the canonical sources the mirror depends on actually exist on the branch.
