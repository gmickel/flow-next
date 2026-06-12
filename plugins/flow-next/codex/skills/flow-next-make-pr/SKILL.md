---
name: flow-next-make-pr
description: Render a cognitive-aid PR body from flow-next state and open via gh. Triggers on /flow-next:make-pr with optional spec id and flags (--draft, --ready, --no-mermaid, --base <ref>, --memory, --dry-run). Auto-detects spec from current branch when no id given. NOT Ralph-blocked — autonomous loops can surface a draft PR for human review.
user-invocable: false
allowed-tools: Read, Bash, Grep, Glob, Write, Edit, Task
---

# /flow-next:make-pr — PR-as-cognitive-aid

A reviewable PR body is itself an artefact: it lets a human decide *where to focus* before skimming the diff. flow-next already collects every input that body needs — the spec with R-IDs, per-task done summaries and evidence commits, decisions / bug / architecture-patterns memory entries, glossary changes, strategy alignment, deferred review findings, the git diff itself. This skill stitches those into a structured body, optionally adds mermaid diagrams for module-boundary changes, and pushes via `gh pr create`.

The host agent (Claude Code / Codex / Droid) reads the structured payload from `flowctl spec export-cognitive-aid` and synthesizes the body directly. **Every claim in the body must trace to a structured field in the export payload — never fabricate file paths, SHAs, R-ID attributions, or "why" reasoning.** Unknown attribution is honest ("uncovered" / "unclear") rather than invented. The host is competent at "what looks important here?" given the rich input; no second-model review pass is needed (the structured payload does the heavy lifting).

flowctl provides only thin plumbing: `flowctl spec export-cognitive-aid <spec-id> --base <ref> --json` aggregates the inputs into a single JSON payload (Task 1 of this spec). The skill renders the body, then pushes and creates the PR **directly — no confirm prompt** (invoking make-pr is the intent; the body is deterministic; the default is a reversible draft). `--dry-run` prints the body without creating; `--ready`/`--draft` set draft state.

**Read [workflow.md](workflow.md) for the full phase-by-phase execution. Read [phases.md](phases.md) for the per-phase Done-when checklists. Read [mermaid-rules.md](mermaid-rules.md) before emitting any mermaid codefence — it defines reserved words, escape patterns, shape selection, and the pre-emission validation checklist.**

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md` / `phases.md`) use `$FLOWCTL`:

```bash
FLOWCTL="$HOME/.codex/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**Inline skill (no `context: fork`)** — `plain-text numbered prompt` must stay reachable for the **Phase 0** info prompts (resolve a missing base ref / undetected spec id — never a confirm gate). Subagents can't call plain-text numbered prompts (Claude Code issues #12890, #34592). There is **no Phase 4 confirm prompt** — make-pr creates the PR directly.

## Mode Detection

Parse `$ARGUMENTS` as a flag list. Recognized flags: `--draft`, `--ready`, `--no-mermaid`, `--memory`, `--dry-run`, `--base <ref>` (consumes the next token), and the literal token `mode:autonomous`. Strip recognized tokens; the remainder (if any) is the optional spec id.

```bash
RAW_ARGS="$ARGUMENTS"
DRAFT_FORCE="auto" # auto | draft | ready
NO_MERMAID=0
WRITE_MEMORY=0
DRY_RUN=0
BASE_REF=""
SPEC_ID=""
AUTONOMOUS=0

# Tokenize and walk the argument list. The loop handles both `--base=<ref>`
# and space-separated `--base <ref>` via a PREV token holder. Deliberately NO
# bash positional parameters here — the host's argument interpolation rewrites
# positional tokens inside skill code blocks (pilot dogfood finding, 1.13.0).
PREV=""
for ARG in $RAW_ARGS; do
 case "$PREV" in
 --base) BASE_REF="$ARG"; PREV=""; continue ;;
 esac
 case "$ARG" in
 --draft) DRAFT_FORCE="draft" ;;
 --ready) DRAFT_FORCE="ready" ;;
 --no-mermaid) NO_MERMAID=1 ;;
 --memory) WRITE_MEMORY=1 ;;
 --dry-run) DRY_RUN=1 ;;
 --base) PREV="$ARG" ;;
 --base=*) BASE_REF="${ARG#--base=}" ;;
 mode:autonomous) AUTONOMOUS=1 ;;
 -*) echo "Unknown flag: $ARG" >&2; exit 2 ;;
 *) SPEC_ID="$ARG" ;;
 esac
done
[[ -n "$PREV" ]] && { echo "Flag $PREV given without a value" >&2; exit 2; }

# Secondary signal: process-level autonomous driver (env survives only
# within one process tree; the token is the primary, prose-safe carrier).
if [[ "${FLOW_AUTONOMOUS:-}" == "1" ]]; then
 AUTONOMOUS=1
fi
```

| Flag | Effect |
|------|--------|
| `--draft` | Force draft PR regardless of open-items count or Ralph context. |
| `--ready` | Force non-draft PR. Conflicts with `--draft` (last flag wins; surface the conflict). |
| `--no-mermaid` | Skip Phase 3 entirely. Mermaid prose summaries are also skipped. |
| `--memory` | After PR creation, write a `knowledge/architecture-patterns/` memory entry summarizing what shipped. Idempotent — rerun adds no second entry for the same spec id. |
| `--dry-run` | Skip Phase 4 entirely. Render body to stdout. Useful for inspection or `… --dry-run \| pbcopy`. |
| `--base <ref>` | Override base-branch detection cascade. Useful when the team's default branch is `develop`, etc. |
| `mode:autonomous` | Autonomous mode: Phase 0 info prompts hard-error instead of asking; draft forced. Sets `AUTONOMOUS=1` only — NEVER `RALPH`. Also derived from `FLOW_AUTONOMOUS=1`. |

Ralph mode (`FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` set) is detected separately in workflow.md §0.0 — the skill is **not** Ralph-blocked. Under Ralph the skill hard-errors instead of asking the Phase 0 info prompts, forces `--draft`, and emits the PR URL to stdout. (The PR is created directly in both modes — the only difference is forced-draft + no Phase 0 prompts under Ralph.) Autonomous mode is a SEPARATE flag: `AUTONOMOUS=1` derives only from the `mode:autonomous` token or `FLOW_AUTONOMOUS=1` and never sets `RALPH`. Under `RALPH || AUTONOMOUS` the Phase 0 info prompts hard-error and `--draft` is forced (`--ready` ignored with a note); the `PR_URL=` stdout contract and all receipt/harness semantics remain Ralph-only.

## Interaction Principles

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

- Ask **one question at a time** via `plain-text numbered prompt`. Never silently skip the question.
- Lead with the **recommended option** and a one-sentence rationale.
- **No confirm gate.** make-pr opens the PR without asking. Phase 0 asks *only* to resolve info it cannot derive (no `--base` and no detection match; no spec detected) — never "do you want to create it?". Not-all-tasks-done warns and proceeds (the open items make it a draft). Skip questions when context resolves cleanly.
- **Ralph and autonomous modes skip all questions.** Detect both once at Phase 0 and route deterministically; a genuinely unanswerable gap hard-errors with a clear message (NEEDS_HUMAN-style) instead of hanging on a prompt.

## Hallucination guardrails

The body is synthesized from the export payload. Every claim must trace to a structured field. The skill explicitly forbids:

- **Inventing file paths.** Only paths returned by `git diff --name-status` (via the `diff.files` array) appear in Critical Changes / Where to look. No "I think there's also a config file" content.
- **Fabricating commit SHAs.** SHAs come from `tasks[].evidence[].commits` and `git log --oneline base..HEAD` only.
- **Guessing R-ID coverage.** Coverage is computed from task `satisfies` frontmatter and commit-message R-ID references. Uncovered R-IDs get a ⚠️ flag, never a confident attribution.
- **Inventing "why" reasoning.** Decision context comes from `memory.decisions[]` entries' bodies. If no decision entry exists for a change, the body says so explicitly rather than narrating a plausible-sounding rationale.
- **Quoting raw diff content.** The body talks ABOUT the diff (paths, churn, modules). Never includes code snippets — privacy + secret-leakage risk; GitHub renders the actual diff below the body.
- **Synthesizing review findings.** Findings come from `reviews.deferred[]` and `reviews.suppressed_count`. The body never editorializes severity or fabricates findings.
- **Generating fictitious memory IDs.** When the body references memory entries (decisions / bugs / patterns), the IDs come from the export payload — never interpolated.
- **Synthesizing strategy alignment.** Strategy section content comes verbatim from `strategy.tracks[]` and the spec's `## Strategy Alignment` block. The body never invents alignment claims.
- **Inventing glossary terms.** Glossary section content comes from `glossary.changes[]`. New terms / renamed terms are surfaced only if the export reports them.
- **Hallucinating mermaid relationships.** Diagram nodes + edges come from real cross-module imports detected via `git diff` analysis (Phase 3 details in the mermaid-rules.md ref file). The skill never adds "I think module X also imports Y" edges.

When data is missing, the body says so honestly (e.g. `*No decision-track memory entries for this spec. Surface decisions in PR review comments if needed.*`) rather than confabulating content. **Honest "unclear" beats plausible "wrong".**

## Forbidden

- **Ralph-blocking the skill.** This skill IS the autonomous-loop terminus per spec R24. Detect Ralph but proceed (with `--draft` forced). Do NOT add a `FLOW_RALPH`/`REVIEW_RECEIPT_PATH` exit-2 guard at the top of the skill.
- **Re-adding a confirm gate.** make-pr creates the PR without prompting; do NOT reintroduce a "create / dry-run / abort" `plain-text numbered prompt` before push. The escape hatch is `--dry-run`, not a question.
- **Pushing or creating PRs in `--dry-run` mode.** Phase 4 short-circuits before any `git push` or `gh pr create`. The body lands on stdout only.
- **Squashing the existing-PR check.** A bare `gh pr view --json url 2>/dev/null` returns rc=0 for CLOSED and MERGED PRs as readily as OPEN. Filter `.state == "OPEN"` via `jq` (validated empirically during fn-42 spike). Closed/merged PRs on a reused branch must NOT trigger refusal.
- **Manual `git push` workflows when `gh` is missing.** When `gh` isn't installed or authenticated, surface the install / `gh auth login` instructions and exit. Don't try to fall back to half-baked PR creation.
- **Writing memory entries without `--memory`.** Default off. The user opts in for structurally-significant specs — every-PR memory inflation is the failure mode this gate prevents.
- **Quoting raw diff content in the body.** See hallucination guardrails — the body describes the diff, never copies code.
- **Calling `gh pr merge`.** Out of scope. The skill creates and exits; merge is a human decision.
- **`git add -A` (or any broad stage) for the PR-artifact commit.** Phase 1.5 stages exactly `.flow/artifacts/<spec-id>/pr.html` with the fixed message `chore(flow): pr artifact <spec-id>` — unrelated working-tree changes are not make-pr's concern.
- **Opening a Lavish session or running `lavish-axi poll` from make-pr.** The PR artifact is a read-only review instrument — no annotate loop, interactive or autonomous. Review conversation belongs to the code host.
- **Emitting an artifact blob link that can 404.** Gitignored `.flow/artifacts/` → local-open guidance only; committed mode links only after the narrow artifact commit landed on the branch being pushed.

## Pre-check: local setup version

Same pattern as `/flow-next:plan` and `/flow-next:audit` — non-blocking notice when `.flow/meta.json` `setup_version` lags the plugin version:

```bash
if [[ -f .flow/meta.json ]]; then
 SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
 PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/.codex-plugin/plugin.json"
 PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
 if [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
 echo "Plugin updated to v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts (current: v${SETUP_VER})." >&2
 fi
fi
```

## Workflow

Execute the phases in [workflow.md](workflow.md) in order:

0. **Pre-flight** — `gh` installed + authenticated; resolve spec id (arg or branch-match); base-branch detection cascade; branch validity (HEAD ahead of base); all tasks `done` (warn + proceed as draft if not — no prompt; Ralph exits 2); existing-PR refusal filtered on `.state == "OPEN"`. Detects Ralph environment for downstream phases.
1. **Gather inputs** — single call to `flowctl spec export-cognitive-aid <spec-id> --base <ref> --json`; parse the structured payload (spec / tasks / memory / glossary / strategy / diff / reviews).
1.5. **HTML render lens (opt-in)** — only when `artifacts.html.enabled` is true AND not `--dry-run`: generate `.flow/artifacts/<spec-id>/pr.html` (read-only review instrument per the shared disclosure reference [`plugins/flow-next/references/html-artifacts.md`](../../references/html-artifacts.md) §5 — diff-derived, R-ID-verified with flagged mismatch rows), commit it narrowly (`chore(flow): pr artifact <spec-id>`, artifact file only) when `.flow/artifacts/` is tracked, and record the render-lens line for the body summary block. Never opens a Lavish session or polls (interactive AND autonomous). Failure is non-fatal — one stderr note, PR proceeds. With the mode off/unset there is zero artifact-related behavior or output beyond the single config read.
2. **Render body** — TL;DR, R-ID coverage table, Critical changes, Decisions made, Memory left behind, Glossary/strategy notes, Open items, Where to look, footer breadcrumb. Sections without content are omitted (never empty placeholder headings).
3. **Mermaid generation** — gated by 5 trigger conditions (cross-module imports, public interface changes, new/removed top-level dirs, high fan-out spec). Hard caps: 3 diagrams, 12 nodes, 25 edges, 12K characters. Each codefence preceded by a 3-5 sentence plain-language prose summary (load-bearing for forges that don't render mermaid). Validates each codefence against the [`mermaid-rules.md`](mermaid-rules.md) §6 checklist (reserved words, escape patterns, no emoji / MathJax, no inheritance cycles) before emitting. Skipped under `--no-mermaid` or when no triggers fire / a skip rule applies (pure-additive single-module diff <50 LOC, flat-layout repo).
4. **Push + create PR** — `git push -u origin HEAD`, then `gh pr create --title --body`. Draft when `OPEN_ITEMS_COUNT > 0` OR Ralph OR `--draft`; ready when `--ready`. `--dry-run` short-circuits before push.
5. **Output + footer** — emit PR URL on success; print breadcrumb (`Generated by /flow-next:make-pr from <spec-id> against <base>`); optionally write `knowledge/architecture-patterns/` memory entry under `--memory`.
