---
name: flow-next-qa
description: Live-app real-user QA pass derived from the spec. Drives the running app via flow-next-drive, derives scenarios from the spec's AC / R-IDs / boundaries, files structured P0/P1/P2 findings with evidence, and ends with a YES/NO ship verdict receipt. Triggers on /flow-next:qa with a spec id. Runs user-invoked OR as the optional `pipeline.qa` pilot stage (default off). Augments — never replaces — CI/staging/manual QA. FORBIDDEN from marking PASS by reading source — the verdict rests on captured evidence from the live app, never on agent narration.
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task
---

# /flow-next:qa — live-app real-user QA pass

flow-next's review surface today is all static: `impl-review`, `spec-completion-review`, `quality-auditor`, `code-review`. Nothing drives the *running* app like an unforgiving real user. `/flow-next:qa` fills that gap — it drives the deployed app (via **fn-51 flow-next-drive**), files structured P0/P1/P2 findings with evidence, and ends with a YES/NO ship verdict emitted as a proof-of-work receipt.

**Augments, never replaces.** QA is the cheap *first* live pass — the app already runs on the dev's machine during `work`, so run an initial agentic pass over the complete build before a human opens the PR. Like everything in flow-next it **reduces human work agentically and surfaces problems to humans**; it does **not** stand in for CI/staging QA or manual QA, which still happen downstream. Findings are advisory: they ride the draft PR + the bug-memory track, and the human reviewer + the land gate decide.

**Two entry points, one skill.** Run it user-invoked (you remember to), or wire it into the autonomous build loop as the **optional `pipeline.qa` pilot stage** (default **off**; `flowctl config set pipeline.qa on`). When on, [`/flow-next:pilot`](../flow-next-pilot/SKILL.md) inserts a `qa` stage at the **all-tasks-done** juncture — one live pass over the complete build, just before make-pr (`plan → plan-review → work → qa → make-pr`). The stage is evidence-aware (it leans on what `work` already verified) and autonomy-safe (`SHIP`/`NA`/`BLOCKED` advance; `NEEDS_WORK` still advances to the draft PR and surfaces its findings — QA never hard-blocks the loop). See [`docs/ralph.md`](../../docs/ralph.md) and [`flowctl.md`](../../docs/flowctl.md) (`pipeline.qa` config row).

**Prerequisite - `/flow-next:prime` gates the recommendation.** Prime's QA-readiness line is the upstream signal for turning `pipeline.qa` on: it recommends enabling this stage ONLY when the repo reaches operability tier 3 AND the DR-core prerequisites pass (seeded data, documented dev login, a drivable surface, readable runtime evidence). If prime reports "QA stage would fail here" or "not applicable to this shape", the app cannot be driven yet - fix the named prerequisites (or leave the stage off) rather than wiring in a stage that BLOCKs every run.

The differentiator vs spec-less QA tools is **the spec is the source of intent**: flow-next derives test scenarios directly from the spec — acceptance criteria → scenarios, R-IDs → coverage, boundaries → what NOT to test, decision context → expected behavior. The host already encodes intent instead of reconstructing it. The QA discipline (P0/P1/P2 taxonomy, evidence rules, session hygiene) is a lean borrow from Ray Fernando's `running-bug-review-board` skill (Apache-2.0 — credited in CHANGELOG); flow-next stays lean (no 18-reference port, ≤500-line skill cap).

**Read [workflow.md](workflow.md) for the full phase-by-phase execution** (discover → derive → prepare → execute → file → verdict).

## The hard rule — PASS is forbidden from source inspection

**QA must NEVER mark PASS (SHIP) by reading source code.** A live-app QA pass is the gap that all other flow-next review already covers statically. The verdict rests on **captured evidence from the running app** — screenshots, console dumps, observed state — never on agent narration, never on "the code looks correct", never on inferring behavior from the diff. If no live app is reachable (no deploy or no driver), the outcome is **BLOCKED** (could not verify), not PASS. This rule is load-bearing — it is what makes the skill a real-user QA pass rather than a second static review.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md`) use `$FLOWCTL`. Subagents that run in fresh context fall back to the repo-local copy:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Pre-check: Local setup version

Compare `.flow/meta.json` `setup_version` to the plugin version; on mismatch, escalate once per plugin version. Fail-open throughout: a missing `jq`, `.flow/meta.json`, or plugin manifest silently continues.

```bash
SETUP_MODE=$(jq -r '.setup_mode // empty' .flow/meta.json 2>/dev/null)
SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
VERSION_ACK=$(jq -r '.version_ack // empty' .flow/meta.json 2>/dev/null)
if [[ "$SETUP_MODE" == "plugin" ]]; then
  # fn-121 plugin mode: no local copies exist to go stale - the version compare is
  # moot. Check only the CLAUDE.md snippet contract (sentinel vs the plugin's
  # expected v1; keep the literal in sync with SNIPPET_SCHEMA_VERSION in flowctl.py).
  SNIP_ACK=$(jq -r '.snippet_ack // empty' .flow/meta.json 2>/dev/null)
  SNIP_VER=$(grep -m1 -o 'flow-next:snippet:v[0-9]*' CLAUDE.md 2>/dev/null | grep -o '[0-9]*$')
  if [[ "${SNIP_VER:-missing}" != "1" ]]; then
    if [[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_AUTONOMOUS:-}" == "1" || "${ARGUMENTS:-}" == *mode:autonomous* \
          || "$SNIP_ACK" == "1" ]]; then
      echo "CLAUDE.md flow-next snippet contract v${SNIP_VER:-missing} != plugin v1. Refresh via /flow-next:setup or the interactive ask." >&2
    else
      echo "FLOW_SNIPPET_ASK ${SNIP_VER:-missing} 1"
    fi
  fi
elif [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
  if [[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" \
        || "${FLOW_AUTONOMOUS:-}" == "1" || "${ARGUMENTS:-}" == *mode:autonomous* \
        || "$VERSION_ACK" == "$PLUGIN_VER" ]]; then
    echo "Local setup v${SETUP_VER} differs from plugin v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts." >&2
  else
    echo "FLOW_SETUP_ASK ${SETUP_VER} ${PLUGIN_VER}"
  fi
fi
```

If the block printed a `FLOW_SNIPPET_ASK` line (plugin mode only; suppressed to the stderr note under the autonomy markers above), before proceeding ask the user with AskUserQuestion (the CLAUDE.md flow-next snippet block is on an older contract than this plugin version; refresh the marker block?), offering exactly the options **Refresh now**, **Remind me next version**, **Skip this run**, then continue the skill whichever is chosen:
- **Refresh now**: run `"${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl" setup-block apply --file CLAUDE.md --template "${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/skills/flow-next-setup/templates/claude-md-snippet-plugin.md" --json`; if it returns `action: ask`, re-run as `setup-block resolve` with the same `--file`/`--template` plus `--choice overwrite --json` - this question WAS the consent. Marker-bounded: content outside the block is never touched.
- **Remind me next version**: record the acknowledgement so this contract version is not re-asked (fail-open: on any error, continue anyway):
  ```bash
  rm -f .flow/meta.json.tmp && jq '.snippet_ack = "1"' .flow/meta.json > .flow/meta.json.tmp && mv .flow/meta.json.tmp .flow/meta.json
  ```
- **Skip this run**: continue without writing anything; the next invocation asks again.

If the block printed a `FLOW_SETUP_ASK` line, before proceeding ask the user with AskUserQuestion (local setup differs from the plugin; refresh now?), offering exactly the options **Refresh now**, **Remind me next version**, **Skip this run**, then continue the skill whichever is chosen:
- **Refresh now**: pause and have the user run `/flow-next:setup` in this session (do not run setup yourself), then continue once it finishes.
- **Remind me next version**: record the acknowledgement so this version is not re-asked (only a later plugin version re-arms it), then continue. Run this self-contained write (fail-open: on any error, continue anyway):
  ```bash
  PJ="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
  PV=$(jq -r '.version' "$PJ" 2>/dev/null)
  [[ -n "$PV" && "$PV" != "null" ]] && rm -f .flow/meta.json.tmp && jq --arg v "$PV" '.version_ack = $v' .flow/meta.json > .flow/meta.json.tmp && mv .flow/meta.json.tmp .flow/meta.json
  ```
- **Skip this run**: continue without writing anything; the next invocation asks again.

Any other output (the one-line differs notice, or nothing) is non-blocking: continue.

**Inline skill (no `context: fork`)** — runs on the host agent, not a forked subagent, because the **prepare** phase must ask the user for undocumented facts (target URL / test account — info-only, never a confirm gate) and a forked subagent cannot ask the user back (Claude Code issues #12890, #34592). The host asks via `AskUserQuestion`. (sync-codex.sh rewrites any `AskUserQuestion` to a plain-text numbered prompt in the Codex mirror.)

## Mode Detection

Parse `$ARGUMENTS`. The first non-flag token is the spec id (required). The value-taking caller overrides the downstream phases honor — `--target <url>` (Phase 3.1), `--receipt <path>` (Phase 6.3), and `--base <ref>` (§1.2 base-branch override) — **must consume their operand here** (both `--flag value` and `--flag=value` forms, mirroring make-pr's `--base`), or the operand falls through to the `*)` arm and is mis-assigned as `SPEC_ID` (Phase 1 then rejects the URL/path as "Not a spec"). They populate `QA_TARGET_URL` / `QA_RECEIPT_OVERRIDE` / `QA_BASE_REF` — the exact variables Phases 3.1 / 6.3 / §1.2 read. Other flags (viewport, autonomy) are reserved for later tasks; the skeleton shifts them harmlessly.

```bash
RAW_ARGS="$ARGUMENTS"
SPEC_ID=""

# The loop handles both `--flag=value` and space-separated `--flag value`
# forms via a PREV token holder. No bash positional parameters here — the
# host's argument interpolation rewrites positional tokens inside skill code
# blocks (pilot dogfood finding, 1.13.0).
PREV=""
for ARG in $RAW_ARGS; do
  case "$PREV" in
    --target)  QA_TARGET_URL="$ARG"; PREV=""; continue ;;        # Phase 3.1 caller override
    --receipt) QA_RECEIPT_OVERRIDE="$ARG"; PREV=""; continue ;;  # Phase 6.3 receipt path
    --base)    QA_BASE_REF="$ARG"; PREV=""; continue ;;          # §1.2 base-branch override
  esac
  case "$ARG" in
    --target|--receipt|--base) PREV="$ARG" ;;
    --target=*)  QA_TARGET_URL="${ARG#--target=}" ;;        # Phase 3.1 caller override
    --receipt=*) QA_RECEIPT_OVERRIDE="${ARG#--receipt=}" ;; # Phase 6.3 receipt path
    --base=*)    QA_BASE_REF="${ARG#--base=}" ;;            # §1.2 base-branch override
    mode:autonomous) QA_AUTONOMOUS=1 ;;                     # strip the literal token (see "Autonomous mode" below)
    -*) echo "Unknown flag: $ARG (reserved for a later task)" >&2 ;;
    *)  [[ -z "$SPEC_ID" ]] && SPEC_ID="$ARG" ;;
  esac
done
[[ -n "$PREV" ]] && echo "Flag $PREV given without a value (ignored)" >&2
# Secondary autonomy signal: the FLOW_AUTONOMOUS=1 env var (process-level drivers
# like the pilot stage). Either signal flips QA_AUTONOMOUS on.
[[ "${FLOW_AUTONOMOUS:-}" == "1" ]] && QA_AUTONOMOUS=1
export QA_TARGET_URL QA_RECEIPT_OVERRIDE QA_BASE_REF QA_AUTONOMOUS   # carry the resolved overrides + autonomy into workflow.md (Phases 3.1 / 6.3 / §1.2 + the preamble)
```

When `SPEC_ID` is empty, the **discover** phase resolves it (branch-match, or by asking the user via `AskUserQuestion` as an info prompt) — never silently default.

## Autonomous mode (mode:autonomous / FLOW_AUTONOMOUS)

`QA_AUTONOMOUS=1` (set above from the literal `mode:autonomous` token — stripped, same shape as plan's autonomous branch — or the `FLOW_AUTONOMOUS=1` env var) means **ask NO questions**. This is the signal the pilot QA stage passes so the build loop can't hang on an `AskUserQuestion`. The workflow honors it **at the preamble, before any prompt path** (workflow.md "Autonomous-mode gate") — not in the post-verdict preflight, because the early phases (1.1 spec id, 1.2 base, 3.1 target, 3.2 accounts) all prompt.

Under `QA_AUTONOMOUS=1`:
- **Ask NO questions anywhere.** Every `AskUserQuestion` info-prompt path becomes a deterministic branch: resolve from spec / config / env, else surface a limitation — never prompt.
- **Undocumented target URL / required accounts / no reachable local app / undetermined spec id ⇒ emit a `BLOCKED` `qa_verdict` + clean exit** (the §6.3 writer), never an interactive prompt and never a hang.
- **Autonomy ≠ Ralph.** Neither `mode:autonomous` nor `FLOW_AUTONOMOUS` activates ralph-guard hooks or any receipt-path gate — they gate **question suppression** only. Ralph (`FLOW_RALPH=1` / `REVIEW_RECEIPT_PATH`) is the separate, additive signal detected in Phase A; the two compose (a pilot run may be autonomous-but-not-Ralph).

Ralph mode (`FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` set) is detected in workflow.md §AUTONOMY — the skill is **aware but not Ralph-blocked** (R11). Ralph independently suppresses prompts too (Phase A), so a Ralph run is implicitly autonomous; `QA_AUTONOMOUS` covers the non-Ralph autonomous caller (the pilot stage).

## fn-51 consumption — a read-and-drive contract, NOT a callable API

A skill is not a function. QA does **NOT** "call" flow-next-drive. The host agent **reads fn-51's workflow + references and executes the universal driving flow itself** — `observe → snapshot fresh refs → act → verify → capture`. fn-51 owns the driver ladder and all actuation prose; QA owns scenario authoring, evidence capture, and the verdict. **Never duplicate CDP / agent-browser / Computer-Use prose here** — point at fn-51's references:

- Surface detection + universal flow + the web/native ladder: `plugins/flow-next/skills/flow-next-drive/SKILL.md`
- Driver command detail (per rung): `plugins/flow-next/skills/flow-next-drive/references/` (`agent-browser.md`, `chrome-devtools-mcp.md`, `playwright.md`, `computer-use.md`, …)

Per scenario, record an **evidence tuple**: `{driver_rung, target_url, viewport, screenshot_path, console_path}`. fn-51's SKILL.md (`:83`) explicitly defers the QA workflow — scenario authoring, bug filing, verdict — downstream to this skill; the seam is designed, QA orchestrates and fn-51 actuates.

## Forbidden

- **Marking PASS / SHIP from source inspection.** See "The hard rule" above. PASS requires captured live-app evidence; no live app → BLOCKED, never PASS.
- **Re-implementing driving.** QA consumes fn-51 via the read-and-drive contract; it never reimplements CDP / agent-browser / Computer Use, and never duplicates fn-51's ladder prose.
- **Inventing findings or evidence.** Every finding cites real captured evidence (screenshot / console / URL). No "I think this might be broken" without a reproduction.
- **Ralph-blocking the skill.** QA is aware of Ralph but is not a hard Ralph-block (R11). Do NOT add a `FLOW_RALPH`/`REVIEW_RECEIPT_PATH` exit-2 guard at the top of the skill.

## Workflow

Execute the phases in [workflow.md](workflow.md) in order:

1. **discover** — resolve the spec id (arg / branch-match / info prompt); pull the cognitive-aid payload.
2. **derive** — AC → scenarios, R-IDs → coverage spine, boundaries → exclusions, decision context → expected behavior.
3. **prepare** — target URL, test accounts, session hygiene, device matrix.
4. **execute** — drive the live app via the fn-51 read-and-drive contract; capture the evidence tuple per scenario.
5. **file** — structured P0/P1/P2 findings with evidence; feed the bug memory track.
6. **verdict** — YES/NO ship verdict + open P0/P1 list; emit the `qa_verdict` receipt.
