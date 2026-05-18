# Codex plain-text fallback for AskUserQuestion in sync mirror

## Overview

`request_user_input` errors outside Plan mode in Codex — confirmed in Codex Desktop Default mode AND Codex CLI (openai/codex#10384, #11536, #12694, all closed without resolution as of Feb 2026 Codex 0.93 / GPT-5.2). Error string: `request_user_input is unavailable in code mode`. fn-37 wired `sync-codex.sh` to rewrite canonical `AskUserQuestion` → `request_user_input` in the Codex mirror (lines 510-514) — that rewrite breaks every interactive flow-next skill on Codex outside Plan mode.

Fix: replace `scripts/sync-codex.sh` Stage 3 sed block with a Python heredoc that rewrites canonical `AskUserQuestion` invocations into a plain-text numbered-prompt instruction in the Codex mirror. Instruction tells the Codex agent: print options as `1..N`, append a final `N+1. Other — type your own answer` to simulate `AskUserQuestion`'s freeform input, then **stop and wait for the user's next message**. Codex mirror never mentions `request_user_input`. Add sync-validation guards (mirror existing `askq_refs` pattern at line 833) that fail if `request_user_input` survives into the mirror.

## Quick commands

```bash
# Regenerate Codex mirror with new transform
./scripts/sync-codex.sh

# Validation guards run inside sync-codex.sh; standalone check:
grep -rE '`request_user_input`|request_user_input tool|request_user_input\(|MUST use `request_user_input`|ONLY ask via `request_user_input`' plugins/flow-next/codex/skills/ | grep -v '/templates/'
# Expected: no output

# Manual smoke (R8) — Codex Desktop Default + Codex CLI:
#   1. Open the marketplace repo (with .flow/epics/ present) in Codex Desktop
#   2. /flow-next:setup → confirm numbered plain-text consent prompt + Other-option, no request_user_input call
#   3. Repeat on Codex CLI

# Re-run existing smoke after sync
bash plugins/flow-next/scripts/smoke_test.sh
bash plugins/flow-next/scripts/audit_smoke_test.sh
bash plugins/flow-next/scripts/prospect_smoke_test.sh
bash plugins/flow-next/scripts/ralph_smoke_test.sh
```

## Goal & Context
<!-- scope: business -->

`request_user_input` is unavailable outside Plan mode in Codex (confirmed: Desktop Default mode AND CLI). The tool appears in the tool list but errors on call. fn-37 (done) wired the Codex mirror via `sync-codex.sh` to rewrite `AskUserQuestion` → `request_user_input` — that rewrite is wrong outside Plan mode, which is the common case.

Fix: `sync-codex.sh` transforms canonical `AskUserQuestion` usage into an explicit plain-text numbered-prompt instruction in the Codex mirror. The mirror tells the agent: print options as a numbered list (1..N) with a final `Other — type your own answer` option to simulate `AskUserQuestion`'s freeform input, then stop and wait for the user's next reply. The Codex mirror never calls `request_user_input`. Behavior is uniform across Codex Default + Plan + CLI; no runtime mode detection.

## Boundaries

- Not adding runtime mode detection. Uniform plain-text behavior on Codex regardless of mode.
- Not keeping `request_user_input` as a viable path on Codex. The Codex mirror never calls it.
- Not touching Claude Code canonical — `AskUserQuestion` stays the canonical for Claude.
- Not touching agent-internal auto-fix loops where "Never use AskUserQuestion in this loop" is by design — `flow-next-impl-review/SKILL.md:325`, `workflow.md:1056`; `flow-next-plan-review/SKILL.md:179`, `workflow.md:379`; `flow-next-spec-completion-review/SKILL.md:161`, `workflow.md:574`. Token rewrite still applies; semantic stays ("Never use the plain-text numbered prompt in this loop").
- Not bumping minor. Sync-mirror correction is patch (1.1.1 → 1.1.2).
- Not adding new flowctl subcommands. All work is in `scripts/sync-codex.sh` + minor canonical prose adjustments.

## Strategy Alignment

Active tracks served by this plan:
- **Cross-platform parity** — restores the "first-class on Codex" guarantee. The current sync rewrite breaks every interactive skill in Codex Default mode + CLI; fn-45 closes the gap without forking canonical.
- **v1.0 vocabulary stability** — keeps canonical `AskUserQuestion` as the single source of truth for Claude; sync-time transform owns the platform difference, so canonical prose stays stable.

## Decision Context

- **Plain-text everywhere on Codex** over Plan-mode-only structured prompt: simpler, no runtime mode detection. Plan-mode users see plain text too — acceptable because Plan mode is rare and uniformity beats fragile branching.
- **Sync-time transform** over runtime fallback prose: canonical stays clean (Claude path is the primary); the platform difference lives in one place (`sync-codex.sh`). Future Codex Default-mode-compatible primitives become a single-file change.
- **`N+1. Other — type your own answer`** simulates `AskUserQuestion`'s freeform-input affordance. Matches user phrasing verbatim (fn-45 conversation turn 2).
- **Python heredoc** over sed for the substantive substitution: sed cannot reliably insert multi-line replacement text across macOS BSD + GNU sed; the existing Stage 1 (breadcrumb strip) and Stage 2 (ToolSearch strip) already use Python heredoc for the same reason. New Stage 3 follows the same pattern.
- **Validation guards in sync** over post-hoc smoke: future regressions where canonical adds a new hard mandate without considering Codex surface at sync time, not in user-facing failures.
- **"Stop and wait for the user's next message"** in the substituted instruction — explicit halt verb (Codex Default mode keeps going by default; openai/codex#11536 confirms). "Render → print" because "render" can be interpreted as "set up for later"; "print" means output now.
- **Preserve frontmatter `allowed-tools:` listings unchanged.** Codex reads `agents/openai.yaml` for the contract; the SKILL.md frontmatter `allowed-tools: request_user_input` lines are harmless residue. Stripping them is a separate concern; not in this spec's scope.

## Acceptance Criteria

- **R1:** `scripts/sync-codex.sh` Stage 3 (lines 510-514: the 3-line sed block rewriting `` `AskUserQuestion` ``, `AskUserQuestion tool`, bare `AskUserQuestion`) replaced with a Python heredoc that rewrites canonical `AskUserQuestion` invocations into the plain-text numbered-prompt instruction described in R2. Stage 1 (breadcrumb strip, lines 396-418) and Stage 2 (ToolSearch strip, lines 423-507) are preserved unchanged — they expect the canonical `AskUserQuestion` token and run before the new transform.
- **R2:** Substituted instruction text reads substantively: "**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer." Distinct re.sub patterns handle the four canonical surface forms (inline-backticked invocation, ToolSearch-prefixed invocation, hard mandate, one-question-at-a-time mandate). Longest-most-specific patterns run first.
- **R3:** Hard mandates in canonical that survive sync — "**CRITICAL**: You MUST use the `AskUserQuestion` tool", "ONLY ask questions via AskUserQuestion tool calls", "MUST use `AskUserQuestion` tool" — become "**CRITICAL**: You MUST ask via the plain-text numbered prompt described above" or equivalent in the Codex mirror. Canonical Claude Code prose unchanged. Auto-fix-loop mandates ("Never use AskUserQuestion in this loop") survive untouched semantically (token rewritten to "plain-text numbered prompt"; "Never use" intent preserved).
- **R4:** Destructive / irreversible / external actions (`.flow/epics` → `.flow/specs` migration in setup; capture rewrite/supersede; make-pr push + `gh pr create`; interview rewrite; audit cleanup) include an explicit `abort` option in their numbered prompt. Skills exit cleanly on `abort` choice — no default action without explicit user reply. Verify by reading the post-sync Codex mirror for each affected skill.
- **R5:** `flow-next-setup/workflow.md` preserves existing config when set; folds unset optional config into one grouped numbered prompt or skips with a "configure later via …" summary line; preserves repo-custom docs (no clobber of customized CLAUDE.md / AGENTS.md / .flow/usage.md sections).
- **R6:** `scripts/sync-codex.sh` validation block adds new guards immediately after the existing `askq_refs` guard at line 838 that fail when the Codex mirror contains `` `request_user_input` ``, `request_user_input tool`, `request_user_input(`, "MUST use `request_user_input`", or "ONLY ask via `request_user_input`". Guards follow the existing pattern: `var_refs=$( { grep -rE '<patterns>' "$CODEX_DIR/skills/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | wc -l | tr -d ' ')`; print offending file:line on failure; increment `errors` counter.
- **R7:** `CLAUDE.md` line 63 "Blocking-question tool" cross-platform row updated to document the new contract: canonical writes `AskUserQuestion`; sync transforms to plain-text numbered prompt (with `N+1. Other — type your own answer` final option) for Codex. `agent_docs/adding-skills.md` step 3 parenthetical updated. `scripts/sync-codex.sh` Stage 3 comment block (line 386: `# --- TOOL NAMES: AskUserQuestion → request_user_input (Codex native) ---`) updated to document the new transform contract.
- **R8:** `agent_docs/local-dev.md` gains a "Codex plain-text prompt smoke" subsection (insert after line 59, before "RP gotchas") documenting the manual verification: run `/flow-next:setup` on Codex Desktop Default mode AND Codex CLI in a repo with `.flow/epics/`, confirm numbered plain-text consent prompt with `Other — type your own answer` as final option, confirm no `request_user_input` call attempt.
- **R9:** `./scripts/sync-codex.sh` runs cleanly with the new transform + new guards; Codex mirror regenerated; existing smoke scripts (`smoke_test.sh`, `audit_smoke_test.sh`, `prospect_smoke_test.sh`, `ralph_smoke_test.sh`) stay green. `CHANGELOG.md` gains `[flow-next 1.1.2]` entry above `[flow-next 1.1.1]` summarizing the transform + guards.

## Early proof point

Task `fn-45.1` validates the core approach: the sync-codex.sh transform produces clean plain-text numbered-prompt output across the 30 mirror files AND the new validation guards pass. If the transform produces malformed mirror prose (e.g. broken table cells in `flow-next-prime/pillars.md:219`, broken anti-mandate negation in `flow-next-plan/SKILL.md:118` and `flow-next-ralph-init/SKILL.md:37`) or breaks existing smoke scripts, re-evaluate the Python-vs-sed split and the regex surface coverage before continuing with tasks fn-45.2, fn-45.3, fn-45.4.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | sync-codex.sh Stage 3 transform replacement | fn-45.1 | — |
| R2  | Substituted plain-text instruction phrasing | fn-45.1 | — |
| R3  | Soften hard mandates in mirror; preserve auto-fix mandates | fn-45.1 | — |
| R4  | Destructive-action abort option | fn-45.2 | — |
| R5  | Setup preserve-existing config | fn-45.3 | — |
| R6  | Validation guards in sync | fn-45.1 | — |
| R7  | CLAUDE.md row + sync-codex.sh comment + adding-skills.md | fn-45.1 (sync-codex.sh comment), fn-45.4 (CLAUDE.md + adding-skills.md) | — |
| R8  | Manual smoke + local-dev.md entry | fn-45.4 | — |
| R9  | Regen + smoke green + CHANGELOG | fn-45.1 (regen + smoke), fn-45.4 (CHANGELOG) | — |

## References

- `scripts/sync-codex.sh:386-517` — current 3-stage transform pipeline (Python preflight + sed final pass)
- `scripts/sync-codex.sh:510-514` — Stage 3 sed block to replace (R1)
- `scripts/sync-codex.sh:826-839` — existing `askq_refs` validation block; new R6 guards land at ~line 840
- `scripts/sync-codex.sh:818-885` — validation-guard pattern precedent (`task_refs`, `ddd_refs`, `alias_refs`)
- Surface forms (R2): `flow-next-capture/workflow.md:135-160` (options-list shape), `flow-next-strategy/SKILL.md:18,111-121` (fallback prose), `flow-next-interview/SKILL.md:217,221,235` (hard mandate + ONLY-via)
- Hard-mandate sites lacking fallback (R3): `flow-next-setup/workflow.md:61,374`; `flow-next-prime/workflow.md:194,306` + `SKILL.md:109`; `flow-next-interview/SKILL.md:217,221`; `flow-next-resolve-pr/workflow.md:393`; `flow-next-impl-review/walkthrough.md:40,237`
- Auto-fix-loop sites (R3 boundary): `flow-next-impl-review/SKILL.md:325`, `workflow.md:1056`; `flow-next-plan-review/SKILL.md:179`, `workflow.md:379`; `flow-next-spec-completion-review/SKILL.md:161`, `workflow.md:574`
- Destructive-action sites (R4): `flow-next-setup/workflow.md:61` (migration consent); `flow-next-capture/workflow.md:195,412,481,569` (rewrite/supersede/override); `flow-next-make-pr/phases.md:127`, `workflow.md` (push + PR create); `flow-next-interview` (rewrite); `flow-next-audit` (cleanup)
- Anti-mandate sites (verify transform doesn't mangle): `flow-next-plan/SKILL.md:117` (`do NOT use AskUserQuestion tool`); `flow-next-ralph-init/SKILL.md:37` (`do NOT use AskUserQuestion tool`); `flow-next-prime/pillars.md:219` + `SKILL.md:97` (table cells `✅ Fixes offered via AskUserQuestion`)
- Excluded templates (R6 guard exclusion): `flow-next-ralph-init/templates/watch-filter.py:47` (`"AskUserQuestion": "❓"` — intentional dict key)
- `CLAUDE.md:63` — "Blocking-question tool" cross-platform row (R7)
- `CLAUDE.md:27` — skill-architecture prose mentioning `AskUserQuestion` (R7 — verify parenthetical needs update)
- `agent_docs/adding-skills.md:9` — skill-author checklist step 3 (R7)
- `agent_docs/local-dev.md:36-59` — smoke-test section; R8 entry lands after line 59 before "RP gotchas" at line 61
- `CHANGELOG.md:5` — 1.1.1 entry; R9 entry lands above
- Prior art: fn-37 (done) — `[flow-next 0.37.1]` introduced the `AskUserQuestion → request_user_input` rewrite this spec replaces; recorded as `flowctl spec add-dep`
- OpenAI Codex evidence: openai/codex#10384, #11536, #12694 (all closed; `request_user_input` Plan-mode-only)
- `.flow/memory/knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30.md` — planning convention for any sync-codex.sh change
- Community precedent: `sanchomuzax/AskUserQuestion-tool-for-Codex` (numbered options + parse-then-resume pattern)

## Conversation Evidence

> user (turn 1, part 1): "Codex Default mode, `request_user_input` exists in the tool list but errors when called: request_user_input is unavailable in Default mode"
> user (turn 1, part 2): "It appears only Plan mode supports that structured multi-choice prompt"
> user (turn 1, part 3): "this is not just flow-next-setup. Multiple Codex skills still hard-require `request_user_input`"
> user (turn 1, part 4): "Never silently skip a required question"
> user (turn 1, part 5): "For destructive/irreversible/external actions, require explicit user consent: .flow/epics → .flow/specs migration, overwrite/rewrite generated docs/specs, cleanup/rename/delete, push, create PR, star repo"
> user (turn 1, part 6): "For non-critical setup preferences: Preserve existing config. Skip unset optional config or ask plain chat only if needed. Preserve repo-custom docs"
> user (turn 1, part 7): "Update scripts/sync-codex.sh if needed so generated Codex mirrors do not contain hard request_user_input mandates without fallback"
> user (turn 2): "request_user_input is unavaialable in codex if not in plan mood. i've confirmed in codex desktop and codex cli, so we need to adapt the script to tell codex to provide the questions in normal plain text, ie. numbered list with a 4th option something else, type your own answer bla, like to simulate it"
