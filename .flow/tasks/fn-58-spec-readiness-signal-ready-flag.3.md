---
satisfies: [R5, R6, R7]
---

## Description

The prompting layer: capture + interview offer a consent-gated "mark ready?" at end of authoring, capture --rewrite resets readiness with an announcement, and plan gains the adoption-gated soft-check.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-capture/workflow.md` (+ SKILL.md/phases.md touch-ups), `plugins/flow-next/skills/flow-next-interview/SKILL.md`, `plugins/flow-next/skills/flow-next-plan/steps.md` (+ SKILL.md)

## Approach

Per spec §Resolved at planning:
- **capture (R5)**: mirror the fn-57.7 glossary consent shape exactly — post-approve follow-up `AskUserQuestion` (§4.2 :503-527 region, "only when user picked approve"; frozen options; default keep-draft) + the write in the §5.8 post-write section (`$FLOWCTL spec ready "$SPEC_ID"`). **Combined visibility predicate (resolves R5/R7): the prompt appears IFF readiness is adopted (≥1 ready spec) AND `tracker.readyState` is NOT configured.** Non-adopters see no prompt anywhere (adoption enters via `flowctl spec ready` / ceremony / prime); tracker-authoritative repos never get a local mark-ready offer (one-way pull). Autofix mode never writes (prints a suggestion only). Ralph-block already upstream — unreachable under Ralph.
- **capture --rewrite reset**: in the §5.3 rewrite branch (:685-693), call `$FLOWCTL spec unready "$REWRITE_TARGET"` unconditionally (idempotent no-op for never-ready specs per .1) and add ONE announcement line to the post-write summary: "spec rewritten — readiness reset to draft (re-bless when ready)". Announce, never confirm (POLA; --rewrite already carried the consent).
- **interview (R5)**: same optional prompt just before `## Completion` (:824 region), same combined visibility predicate (adopted AND no `readyState`), same default keep-draft. Interview NEVER auto-resets `ready` on refinement (it edits in place — resolved decision).
- **plan soft-check (R6/R7)**: in steps.md Step 1 right after spec resolution (:68-72, the `show --json` already carries `ready` after .1) and BEFORE the scout fan-out (warn before expensive research). **Adoption gate** (net-new, model on the STRATEGY husk-vs-presence guard :80-95): fire only when `ready == false` AND readiness is in use (any spec has ready true — `specs --json` + jq — OR `tracker.readyState` non-null). Interactive: one lead-with-recommendation question, default proceed (non-destructive). **Options split by mode:** no `tracker.readyState` → proceed / mark-ready-then-proceed / abort; `readyState` configured → proceed / abort / update-the-tracker-state-then-rerun — NEVER offer local mark-ready when the tracker is authoritative (one-way pull). Non-interactive/Ralph (net-new detection — `FLOW_RALPH`/`REVIEW_RECEIPT_PATH` env, same probe as other skills): auto-proceed + one stderr log line, never block.

## Investigation targets

**Required:**
- `.flow/specs/fn-58-spec-readiness-signal-ready-flag.md` §Resolved at planning
- `plugins/flow-next/skills/flow-next-capture/workflow.md:503-527, 685-693, 753-763` — the fn-57.7 consent shape + rewrite branch + post-write writes
- `plugins/flow-next/skills/flow-next-plan/steps.md:68-95` — Step 1 + the STRATEGY husk-guard to model the adoption gate on
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:797-824` — write-back + Completion region

**Optional:**
- `plugins/flow-next/skills/flow-next-capture/SKILL.md:85-96` — Ralph-block (confirm prompts sit downstream)

## Acceptance

- [ ] capture offers mark-ready post-approve ONLY when adopted (≥1 ready spec) AND no `tracker.readyState` (default keep-draft), writes via `spec ready` in §5.8; autofix never writes
- [ ] `--rewrite` resets readiness via idempotent `unready` + one announcement line; no extra confirm
- [ ] interview offers the same optional prompt; never auto-resets on refinement
- [ ] plan warns only when adoption-gate passes AND spec unready; default proceed; option set splits by tracker mode (local mark-ready never offered when `readyState` configured); non-interactive auto-proceeds with a log line
- [ ] Zero behavior change for non-adopters: no readiness adopted in repo → no prompts AND no warnings anywhere (capture, interview, plan)

## Done summary
Retroactive tidy (2026-08-04): the feature this task describes shipped long ago but the task record was never closed when the parent spec closed — surfaced by the closed-parent orphan rule in `flowctl brief` (3.15.0). Evidence of existence: capture/interview mark-ready prompts and plan-side readiness soft-check (fn-58) are in the shipped skills. No new work performed; this receipt closes the stale record.
## Evidence
- Commits:
- Tests:
- PRs: