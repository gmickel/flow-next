---
name: flow-next-qa
description: Live-app real-user QA pass derived from the spec. Drives the running app via flow-next-drive, derives scenarios from the spec's AC / R-IDs / boundaries, files structured P0/P1/P2 findings with evidence, and ends with a YES/NO ship verdict receipt. Triggers on /flow-next:qa with a spec id. FORBIDDEN from marking PASS by reading source — the verdict rests on captured evidence from the live app, never on agent narration.
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task
---

# /flow-next:qa — live-app real-user QA pass

flow-next's review surface today is all static: `impl-review`, `spec-completion-review`, `quality-auditor`, `code-review`. Nothing drives the *running* app like an unforgiving real user. `/flow-next:qa` fills that gap — it drives the deployed app (via **fn-51 flow-next-drive**), files structured P0/P1/P2 findings with evidence, and ends with a YES/NO ship verdict emitted as a proof-of-work receipt.

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

**Inline skill (no `context: fork`)** — `AskUserQuestion` must stay reachable for the **prepare** phase info prompts (resolve an undocumented target URL / test account — never a confirm gate). Subagents can't call blocking question tools (Claude Code issues #12890, #34592). (sync-codex.sh rewrites any `AskUserQuestion` to a plain-text numbered prompt in the Codex mirror.)

## Mode Detection

Parse `$ARGUMENTS`. The first non-flag token is the spec id (required). Flags are reserved for downstream tasks (target URL override, viewport selection, autonomy); the skeleton recognizes only the spec id and surfaces an info prompt when it is missing.

```bash
RAW_ARGS="$ARGUMENTS"
SPEC_ID=""

set -- $RAW_ARGS
while [[ $# -gt 0 ]]; do
  case "$1" in
    --) shift; break ;;
    -*) echo "Unknown flag: $1 (reserved for a later task)" >&2; shift ;;
    *)  [[ -z "$SPEC_ID" ]] && SPEC_ID="$1"; shift ;;
  esac
done
```

When `SPEC_ID` is empty, the **discover** phase resolves it (branch-match or an `AskUserQuestion` info prompt) — never silently default.

Ralph mode (`FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` set) is detected in workflow.md §AUTONOMY — the skill is **aware but not Ralph-blocked** (R11). The deep autonomy routing (autonomous when target URL + accounts are configured; receipt path resolution) is owned by a downstream task; the skeleton only lays the section anchor.

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
3. **prepare** — target URL, test accounts, session hygiene, device matrix. *(Owned by a downstream task; section anchor laid here.)*
4. **execute** — drive the live app via the fn-51 read-and-drive contract; capture the evidence tuple per scenario. *(Owned by a downstream task; section anchor laid here.)*
5. **file** — structured P0/P1/P2 findings with evidence; feed the bug memory track. *(Owned by a downstream task.)*
6. **verdict** — YES/NO ship verdict + open P0/P1 list; emit the `qa_verdict` receipt. *(Owned by a downstream task.)*

This task (fn-53.1) stands up the **skeleton** (all six phase anchors) plus the working **discover** and **derive** phases, and proves the thesis end-to-end (derive ≥1 scenario → dispatch through the fn-51 contract → record an evidence tuple, or a BLOCKED proof receipt when no live target exists). Phases 3-6 are filled by serial downstream tasks editing their own disjoint section anchors.
