---
name: flow-next-map
description: Wrap `clawpatch map` to produce a semantic feature index of the repo (~20 languages, persisted at `.clawpatch/features/*.json`). Detects install, runs `clawpatch init` when `.clawpatch/` absent, invokes provider-free `clawpatch map --source heuristic` by default; `--source auto|agent` flows through as passthrough. Opt-in enrichment — scouts and prime read the resulting index, but flowctl never depends on clawpatch.
user-invocable: false
allowed-tools: Read, Bash, Grep, Glob, Write, Edit
---

# /flow-next:map — wrap `clawpatch map` for a semantic feature index

**Read [workflow.md](workflow.md) for full phase-by-phase execution.**

Wrap the upstream [`clawpatch`](https://github.com/openclaw/clawpatch) CLI's `map` subcommand. Default invocation is provider-free (`--source heuristic`) — zero LLM calls, zero API spend, deterministic mapper. Output lands at `.clawpatch/features/*.json` (Zod-validated upstream, `schemaVersion: 1`). Scout enrichment and the `/flow-next:prime` DE7 nudge land in fn-50.2–.5; this skill is the install/init/invoke surface.

**Role**: thin shell-out wrapper. flowctl never imports or requires clawpatch; the skill is the only flow-next surface that touches it.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**Inline skill (no `context: fork`)** — the map skill is fully non-interactive: install detection, version-range guard, `clawpatch init`, `.clawpatch/.gitignore` skeleton, and `clawpatch map` invocation all proceed without prompting the user. No blocking-question tool is required or used.

## Input

Arguments: `$ARGUMENTS`

Format: `[--source <heuristic|auto|agent>] [-- <extra clawpatch args>]`

- **Default** (no args) → `clawpatch map --source heuristic` (provider-free, deterministic). Heuristic targets conventional app/framework layouts; unconventional repos (CLI tools, plugins, markdown/docs-heavy, non-standard monorepos) may map to 0 features — Phase 5 surfaces a `--source=auto|agent` suggestion when that happens.
- `--source auto|agent` → passthrough to clawpatch; user must have `CLAWPATCH_PROVIDER` configured for these paths (clawpatch's own concern, not ours).
- `--` → terminator; tokens after flow to `clawpatch map` (e.g. `--since-ref origin/main`, `--paths src/`).

**Passthrough boundary.** The slash-command host delivers `$ARGUMENTS` as a single string; the skill word-splits on whitespace. Passthrough is therefore **token-level (whitespace-separated), not full shell-verbatim** — tokens containing literal spaces or shell metacharacters that require shell quoting will not survive. Globs (`*`, `?`) are protected from expansion (`set -f` before the parse) so they reach clawpatch untouched. Users needing complex quoting should run `clawpatch map` directly.

The skill does NOT proxy flow-next's review backend config (rp / codex / copilot / none) into clawpatch. clawpatch's provider matrix (codex / acpx / claude / cursor / grok / opencode / pi) is orthogonal.

## Version pin

```
SUPPORTED_CLAWPATCH=">=0.4.0 <0.5.0"
```

Single source of truth for the supported clawpatch range. Workflow Phase 1 parses `clawpatch --version` with a tolerant `(\d+\.\d+\.\d+)` regex and compares against this range. **Outside-range → warn one line to stderr and degrade (continue). Never block.** Re-verify on each clawpatch minor release.

clawpatch is pre-1.0 (v0.4.0, 2026-05-22; weekly minor releases). The README forecasts breaking changes between minor releases — tolerant parsing matters.

## Ralph-block (R13) — runs first, before everything else

`/flow-next:map` requires a user at the terminal for the install-prompt and init-prompt branches. Autonomous loops cannot install global npm packages or accept interactive consent. Decline-to-run when Ralph signals are set.

```bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
  if [[ -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
    TRIGGER="REVIEW_RECEIPT_PATH"
  else
    TRIGGER="FLOW_RALPH"
  fi
  echo "Error: /flow-next:map declines under Ralph ($TRIGGER set); rerun interactively." >&2
  exit 2
fi
```

**Decline-to-run only.** The skill MUST NOT write anything to `$REVIEW_RECEIPT_PATH` — that file belongs to the upstream review caller; writing there would corrupt unrelated receipts. The skill exits at line 1 of the workflow under Ralph; install/init paths are unreachable.

No env-var opt-in. Ralph never installs global tools or accepts interactive consent.

## Workflow

Execute the phases in [workflow.md](workflow.md) in order:

0. **Pre-flight + config-state echo (R12)** — one four-line block: clawpatch version + `--source`, `CLAWPATCH_PROVIDER` env (or `"none"`), flow-next review backend (informational only), `.clawpatch/` last-mapped timestamp (or `"absent"`).
1. **Install detection (R1, R11)** — `command -v clawpatch` + `clawpatch --version`. Missing → print `pnpm add -g clawpatch` install instructions verbatim and exit 1. When `pnpm bin -g` exits 0 but `command -v clawpatch` still empty, also print the PNPM_HOME `bin/` hint (run `pnpm setup`, re-source shell rc). **No auto-install.**
2. **Version-range guard (R10)** — parse `clawpatch --version` with `(\d+\.\d+\.\d+)`; compare against `SUPPORTED_CLAWPATCH`. Outside range → one-line stderr warning naming expected vs found and continue (degrade — never block).
3. **Init (R2)** — when `.clawpatch/` absent, run `clawpatch init` first. After clawpatch creates `.clawpatch/project.json` + `.clawpatch/config.json`, write a self-contained `.clawpatch/.gitignore` skeleton (skill owns this write — STRATEGY zero-dep means flowctl never references clawpatch).
4. **Map invocation (R1)** — `clawpatch map --source <SOURCE> [extra passthrough]`. Default `<SOURCE>` is `heuristic` (always passed explicitly — never rely on clawpatch's default in case upstream changes it). clawpatch streams stdout live; the skill does not buffer.
5. **Result summary** — print path to `.clawpatch/features/`, count of feature files, last-mapped timestamp; suggest `flowctl repo-map list` (lands in fn-50.2) and the `/flow-next:plan` / `/flow-next:capture` paths that consume it.

## Sharing contract — local-only by design

The `.clawpatch/.gitignore` skeleton this skill writes is `*` + `!.gitignore` — **everything under `.clawpatch/` is git-ignored; only the `.gitignore` itself is tracked**. The feature index is local-per-developer, not committed.

This is a deliberate design choice for a pre-1.0 mapper:

- **No PR review noise** from regenerated feature data on every `clawpatch map` run.
- **No merge conflicts** on `features/*.json` when two branches mapped at different SHAs.
- **No coupling of PR review to mapper-output drift** as clawpatch schema bumps land (weekly minor releases at the time of writing).
- **Onboarding cost is low** — `--source heuristic` is a fast filesystem walk; new contributors regenerate locally in seconds.

Teams that want a shared, in-repo feature index can edit `.clawpatch/.gitignore` directly (e.g. `!features/`, `!project.json`, ignore only `.cache/` and `*.log`). The skill is idempotent and won't clobber a customized `.gitignore` on re-run. **This is unsupported** — be prepared for review noise and merge conflicts; document the choice in your team's `CLAUDE.md` / `AGENTS.md`. See [flow-next.dev/skills/map](https://flow-next.dev/skills/map/) for the full trade-off table.

## Forbidden

- **Auto-installing clawpatch.** The skill detects and instructs; users install with their own permission. Global npm installs are user-consent territory.
- **Proxying flow-next's review backend into `CLAWPATCH_PROVIDER`.** Orthogonal matrices. clawpatch users configure clawpatch directly.
- **Auto-upgrading `--source` to `auto` or `agent` when heuristic coverage looks weak.** Users opt up explicitly via `--source`.
- **Touching the repo `.gitignore`.** The `.clawpatch/.gitignore` skeleton is self-contained inside `.clawpatch/` so a full deletion of that directory removes both data and ignore rules in one step.
- **Writing to `$REVIEW_RECEIPT_PATH` from the Ralph-block path** — see R13 above. The receipt belongs to the upstream review caller; the Ralph branch is decline-to-run, not a receipt producer.
- **Importing or requiring clawpatch from flowctl.** flowctl never references this skill or clawpatch — uninstall promise (`rm -rf .flow/`) stays intact and zero-dep STRATEGY track is preserved.
- **Network calls beyond what clawpatch itself does.** The wrap is local-only; clawpatch's network behavior is upstream's concern.
- **Running under Ralph** — hard-blocked by R13 above.

## Pre-check: local setup version

Same pattern as `/flow-next:prospect` / `/flow-next:capture` — non-blocking notice when `.flow/meta.json` `setup_version` lags the plugin version:

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
