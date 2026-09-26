# Worker anchor bundle - fn-81-skill-runtime-token-plumbing-single.2 (spec fn-81-skill-runtime-token-plumbing-single)

Each section is the verbatim output of the command it is labeled with, in fixed order, untruncated. The bundle is a floor, not a ceiling - memory keyword-search and every further read remain available.

===== [1/11] task_show: `flowctl show fn-81-skill-runtime-token-plumbing-single.2 --json` =====
{
  "success": true,
  "assignee": null,
  "claim_note": "",
  "claimed_at": null,
  "created_at": "2026-07-02T06:33:46.735888Z",
  "depends_on": [
    "fn-81-skill-runtime-token-plumbing-single.1"
  ],
  "id": "fn-81-skill-runtime-token-plumbing-single.2",
  "priority": null,
  "spec": "fn-81-skill-runtime-token-plumbing-single",
  "spec_path": ".flow/tasks/fn-81-skill-runtime-token-plumbing-single.2.md",
  "status": "todo",
  "title": "Review-backend plumbing: RP file composition, single-entry responses, fix-loop cap + staging guards",
  "updated_at": "2026-07-02T06:48:16.437743Z",
  "impl": null,
  "review": null,
  "sync": null,
  "status_source": "committed"
}

===== [2/11] task_md: `flowctl cat fn-81-skill-runtime-token-plumbing-single.2` =====
---
satisfies: [R8, R9, R10, R11, R13]
---

## Description

Fix the review-backend plumbing: (a) file composition replaces content-re-typing placeholder heredocs at all four RP prompt-assembly sites + export-context; (b) RP review responses enter context exactly once in ALL three handlers (impl-review, spec-completion-review, plan-review); (c) fix-loop iteration cap (counter + break/escalate) in the backend-agnostic common loop with codex/copilot/cursor backend files deferring to it; (d) snapshot-scoped staging instead of `git add -A` in both RP fix loops; (e) unique temp paths per the path-persistence rule. CANONICAL FILES ONLY — mirror regen is fn-81.4's. Depends on fn-81.1 (proof point).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-plan-review/{workflow.md,SKILL.md}`, `plugins/flow-next/skills/flow-next-impl-review/{workflow-rp.md,workflow-common.md,workflow-codex.md,workflow-copilot.md,workflow-cursor.md,SKILL.md}`, `plugins/flow-next/skills/flow-next-spec-completion-review/workflow-rp.md`, `plugins/flow-next/skills/flow-next-export-context/SKILL.md`

## Approach

- **File composition (spec §Approach 2):** per site — `PROMPT_FILE=<literal unique path>`; `$FLOWCTL rp prompt-get ... > "$PROMPT_FILE"`; static criteria appended via quoted heredoc; `$FLOWCTL show <id> >> "$PROMPT_FILE"`. Sites: plan-review workflow.md:305-325, impl-review workflow-rp.md:85-109, spec-completion-review workflow-rp.md:88-112, export-context SKILL.md:82-93 (prompt-get at :82 is a bare print — redirect it). Scalar placeholders (`[SPEC_ID]`, `[BRANCH_NAME]`, `[USER'S FOCUS AREAS]`) may remain; content-re-typing placeholders (`[PASTE ...]`, `[PASTE SPEC]`) may not.
- **Single-entry responses (spec §Approach 3), ALL THREE handlers:** impl-review workflow-rp.md:191-192, spec-completion-review's rp response handling, AND plan-review workflow.md:383-397 — redirect chat-send stdout to a unique response file, Read it once (parse + fix-loop context), verdict/tally extraction greps the file. Do NOT just delete echoes — command substitution hides stdout; the file+Read IS the single entry.
- **Cap hoist:** counter + break-to-escalation in the backend-agnostic Fix Loop (impl-review SKILL.md:333-362 and/or workflow-common.md); `workflow-codex.md:39-44` ("Repeat until SHIP"), `workflow-copilot.md`, `workflow-cursor.md` updated to defer to the bounded common loop; rp behavior preserved (workflow-rp.md:332). Default 3, `MAX_REVIEW_ITERATIONS` env honored. Escalation on cap: surface findings + stop (matches rp). Enumeration sweep (`grep -rniE 'rp.{0,3}codex.{0,3}copilot|review.backend'` — include cursor in the check; memory entry adding-a-review-backend-sweep-all) so no doc/table implies rp-only.
- **Snapshot-scoped staging (both rp fix loops — impl-review workflow-rp.md:341, completion-review workflow-rp.md:449):** record `git status --porcelain` BEFORE the fix; after the fix, diff the snapshots and stage ONLY paths that changed between them (modified, untracked, deleted, renamed all covered). If a fixer-modified path was ALREADY dirty pre-fix, do NOT stage it — surface the collision and defer/escalate that finding (never sweep pre-existing hunks). Mirrors land's staging discipline.
- **Unique temp paths** per the path-persistence rule for every path touched here: review prompt files, `/tmp/re-review.md` (impl-review-rp:362, completion-rp:470, plan-review:488), `/tmp/updated-plan.md` (plan-review SKILL.md:257, workflow.md:450), `/tmp/export-prompt.md`, `/tmp/completion-review-prompt.md`. Re-review sends reference the same literal paths established earlier in the flow.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-impl-review/workflow-rp.md:85-200,330-370,440-460` — prompt build, response capture, fix loop, re-review
- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md:333-362` + `workflow-common.md` — backend-agnostic fix loop (cap landing zone)
- `plugins/flow-next/skills/flow-next-impl-review/workflow-codex.md` + `workflow-copilot.md` + `workflow-cursor.md` — per-backend loops that must defer to the common cap
- `plugins/flow-next/skills/flow-next-spec-completion-review/workflow-rp.md:88-112,440-475`
- `plugins/flow-next/skills/flow-next-plan-review/workflow.md:300-397,440-495`
- `.flow/memory/` entry `adding-a-review-backend-sweep-all-2026-06-29` — enumeration sweep checklist

**Optional:**
- `plugins/flow-next/skills/flow-next-land/workflow.md` — staging discipline to mirror

## Key context

RP keeps parallel rubric copies in skill markdown — this task changes PLUMBING (assembly/response/loop mechanics), never rubric CONTENT. Depends on fn-81.1: reuse its literal-path and single-entry conventions verbatim.

## Acceptance

- [ ] `grep -rn '\[PASTE' plugins/flow-next/skills/` empty; remaining bracket placeholders verified scalar-only (list them in the summary)
- [ ] RP review responses enter context exactly once in all three handlers; fix loops + tallies function from the response files
- [ ] All four backends bounded: common-loop counter + break + escalation, default 3; codex/copilot/cursor files defer to it; enumeration sweep results in summary
- [ ] Both rp fix loops use snapshot-scoped staging (porcelain before/after) with the pre-dirty-path defer rule; no `git add -A` remains in either file
- [ ] All touched temp paths unique per the path-persistence rule; canonical-only diff (no mirror commit)

## Done summary
Fixed the review-backend plumbing across the RP review skills (canonical files only; mirror regen deferred to fn-81.4). All four RP prompt-assembly sites + export-context now build prompts by deterministic file composition (`rp prompt-get`/`flowctl show`/`flowctl cat` captured via redirection into literal unique prompt files; zero `[PASTE ...]` content-re-typing placeholders remain — surviving bracket slots are scalar-only: [SPEC_ID], [BRANCH_NAME], [LIST TASK IDs], [LIST CHANGED FILES], [COMMIT SUMMARY], [USER'S FOCUS AREAS]). RP review responses now enter context exactly once in all three handlers (impl-review, spec-completion-review, plan-review): chat-send stdout redirects to a unique response file, Read once; verdict + receipt tallies grep the file. The fix-loop iteration cap (MAX_REVIEW_ITERATIONS, default 3, counter + break + escalate) is hoisted into the backend-agnostic fix loops of impl-review/plan-review/spec-completion-review SKILL.md with workflow-codex/copilot/cursor deferring to it (rp behavior preserved; plan-review's RP loop gains the previously-missing cap). Both RP fix loops replace `git add -A` with snapshot-scoped staging (porcelain pre/post set-diff staging only fixer-touched paths; pre-dirty collision rule defers findings whose paths were already dirty — pipeline validated live incl. modified/untracked/deleted/renamed/space-in-name). All touched temp paths unique per the path-persistence rule (review prompts, responses, re-review, updated-plan, export-prompt, snapshots, flowctl-reference examples). Enumeration sweep run: no doc implies the cap or backends are rp-only (pre-existing ralph.md backend-enum drift noted, out of scope). RP impl-review: NEEDS_WORK (send blocks borrowed $PROMPT_FILE across tool-call boundary — fixed by re-declaring both literal paths per block) then SHIP; pitfall captured to memory.
## Evidence
- Commits: 76a8a161f0e1, 23797981045b26a0d6ded979dae472d0dc48305a
- Tests: uv run --with pytest python3 -m pytest plugins/flow-next/tests/ -q (1393 passed, 2 skipped, 164 subtests — run pre- and post-fix), bash scripts/sync-codex.sh x2 (idempotent, validators green; mirror regenerated locally, restored, NOT committed — fn-81.4 owns regen), grep -rn '\[PASTE' plugins/flow-next/skills/ → empty, grep sweep /tmp/review-prompt.md|/tmp/re-review.md|/tmp/updated-plan.md|/tmp/export-prompt.md|/tmp/completion-review-prompt.md in canonical skills → zero hits, live snapshot-staging pipeline test in scratch git repo (modified/untracked/deleted/renamed staged; pre-dirty + pre-untracked excluded), RP impl-review verdict: SHIP (1 fix round; R8/R9/R10/R11/R13 all met, Unaddressed R-IDs: [])
- PRs:

===== [3/11] spec_show: `flowctl show fn-81-skill-runtime-token-plumbing-single --json` =====
{
  "success": true,
  "branch_name": "fn-81-skill-runtime-token-plumbing-single",
  "completion_review_status": "ship",
  "completion_reviewed_at": "2026-07-02T09:21:53.368897Z",
  "created_at": "2026-07-02T06:11:49.004568Z",
  "default_impl": null,
  "default_review": null,
  "default_sync": null,
  "depends_on_epics": [],
  "id": "fn-81-skill-runtime-token-plumbing-single",
  "next_task": 1,
  "plan_review_status": "ship",
  "plan_reviewed_at": "2026-07-02T06:53:46.806067Z",
  "spec_path": ".flow/specs/fn-81-skill-runtime-token-plumbing-single.md",
  "status": "done",
  "title": "Skill runtime token plumbing: single-emission writes, round-trip elimination, fix-loop guards",
  "updated_at": "2026-07-10T12:44:03.099004Z",
  "plan_review_rounds": 0,
  "impl_review_rounds": {},
  "tasks": [
    {
      "id": "fn-81-skill-runtime-token-plumbing-single.1",
      "title": "Single-emission spec writes: capture + interview (early proof point)",
      "status": "todo",
      "status_source": "committed",
      "implicit_owner": false,
      "priority": null,
      "depends_on": []
    },
    {
      "id": "fn-81-skill-runtime-token-plumbing-single.2",
      "title": "Review-backend plumbing: RP file composition, single-entry responses, fix-loop cap + staging guards",
      "status": "todo",
      "status_source": "committed",
      "implicit_owner": false,
      "priority": null,
      "depends_on": [
        "fn-81-skill-runtime-token-plumbing-single.1"
      ]
    },
    {
      "id": "fn-81-skill-runtime-token-plumbing-single.3",
      "title": "Round-trip eliminations: plan, deps, make-pr, tracker-sync, config-get sweep, prime prose",
      "status": "todo",
      "status_source": "committed",
      "implicit_owner": false,
      "priority": null,
      "depends_on": [
        "fn-81-skill-runtime-token-plumbing-single.1"
      ]
    },
    {
      "id": "fn-81-skill-runtime-token-plumbing-single.4",
      "title": "Final gate: mirror parity, smoke + pytest, CHANGELOG Unreleased, optimization-log",
      "status": "todo",
      "status_source": "committed",
      "implicit_owner": false,
      "priority": null,
      "depends_on": [
        "fn-81-skill-runtime-token-plumbing-single.1",
        "fn-81-skill-runtime-token-plumbing-single.2",
        "fn-81-skill-runtime-token-plumbing-single.3"
      ]
    }
  ],
  "ready": false,
  "no_plan": false
}

===== [4/11] spec_md: `flowctl cat fn-81-skill-runtime-token-plumbing-single` =====
# fn-81 Skill runtime token plumbing: single-emission writes, round-trip elimination, fix-loop guards

## Overview

Flow-next skills re-emit large content (spec bodies, review handoffs, PR bodies) multiple times per run and make redundant CLI round-trips. Fleet survey (2026-07-02, all 28 skills) + scout verification quantified the pattern; this spec fixes the runtime plumbing. Skill-markdown-only — no flowctl CLI changes (`--file <path>` / `--file -` already supported everywhere).

Goals: token efficiency AND speed WITHOUT quality loss. Read-backs stay mandatory and user-authoritative. Methodology anchor: `agent_docs/optimizing-skills.md`.

## Quick commands

```bash
bash scripts/sync-codex.sh                    # regen mirror + byte-parity guards (run twice: idempotent)
git diff --stat plugins/flow-next/codex/      # confirm mirror delta is expected
(cd "$(mktemp -d)" && bash /Users/gordon/work/flow-next/plugins/flow-next/scripts/smoke_test.sh)  # smoke REFUSES to run from the plugin repo — run from any other cwd
python3 -m pytest plugins/flow-next/tests/ -q # incl. mirror-parity tests
```

## Approach — the three patterns

**1. Single-emission write (capture, interview).** A drafted body is materialized exactly once. The skill writes the draft ONCE via the Write tool — the tool render IS the user-visible read-back — revises via Edit-tool deltas, and hands flowctl the file path. Key facts (verified): bash vars do NOT survive across tool calls (capture `workflow.md:707-709` states this — today the agent re-authors `$SPEC_BODY` into the Phase 5 heredoc; the file-based pattern removes exactly that); sync-codex does NOT rewrite Write/Edit mentions (both platforms understand them; Codex `apply_patch` on a NEW file shows full content).

**Path persistence rule (vars die across tool calls — applies to the draft path itself):** the draft path is NOT a shell variable. The agent composes a literal unique path (`${TMPDIR:-/tmp}/flow-<skill>-draft-<spec-id>-<agent-chosen 4-char suffix>.md`), uses that literal in the Write call AND in the later `spec set-plan <id> --file <literal path>` call — the path lives in agent context, never in shell state. mktemp is reserved for paths created and consumed within one bash block.

**Read-back contract preserved** (capture §4.2, `workflow.md:505-521`, `:559`, `:576`): full draft visible in the Write render immediately above the question; the `AskUserQuestion` body carries the summary payload (R-ID list, `[inferred]` tally, diff-of-changed-sections on rewrite) and points to the render; frozen `approve`/`edit`/`abort` options and the 3-edit-cycle cap unchanged. **Autofix (`--yes`): the Write render IS the single full emission** — it replaces the stdout print-substitute (no separate print, no second read-back; `--yes` consents on the render). Long renders collapse in the terminal — the question body must say the full draft is in the Write render above (expandable). **Edit-cycle read-back rule:** an Edit render shows only the delta, which is NOT a full read-back — after each edit cycle, Read the full draft file BEFORE re-asking approval (that Read render is the mandatory full read-back for that cycle; one full emission per edit cycle, same cost as today's re-show — no regression, no double-authoring). The Read also satisfies Edit's read-before-edit requirement for the next cycle.

**2. File composition for assembled prompts (RP backends, export-context).** Replace heredocs with content-re-typing placeholders (`[PASTE HANDOFF HERE]`, `[PASTE flowctl show OUTPUT]`, `[PASTE SPEC]`) with deterministic file composition — no shell-var interpolation (vars die across tool calls; unquoted heredocs are injection surfaces for content containing `$`/backticks/`EOF`):

```bash
PROMPT_FILE="${TMPDIR:-/tmp}/flow-review-prompt-<spec-id>-<suffix>.md"   # literal path, agent context
$FLOWCTL rp prompt-get --window "$W" --tab "$T" > "$PROMPT_FILE"   # captured, never re-typed
cat >> "$PROMPT_FILE" <<'EOF_CRITERIA'
<static review criteria — quoted heredoc, no expansion>
EOF_CRITERIA
$FLOWCTL show "$ID" >> "$PROMPT_FILE"                              # appended, never re-typed
```

Scalar placeholders the agent fills inline (`[SPEC_ID]`, `[BRANCH_NAME]`, `[USER'S FOCUS AREAS]`) are fine — they are cheap value substitutions, not content re-typing. The acceptance gate distinguishes the two: zero content-re-typing placeholders may remain; scalar slots are allowed.

**3. Single-entry review responses (ALL RP review-response handlers).** `RESPONSE=$(flowctl rp chat-send ...)` + `echo` is how the response enters context at all (command substitution hides stdout) — the echo is NOT pure waste. Reframe: the response enters context exactly ONCE — redirect chat-send stdout to a unique response file, Read it once (that is the parse + fix-loop context), run verdict/tally extraction via grep/awk against the file; no second full-body emission. Applies uniformly to impl-review, spec-completion-review, AND plan-review RP handlers (one convention, no per-skill exceptions).

## Boundaries / non-goals

- No flowctl Python behavior changes; no new flags, commands, or skills.
- Prompt-content trims / progressive-disclosure gating are fn-82, not here (fn-82 rebases onto this).
- land, drive, strategy, sync, ralph-init: surveyed clean — out of scope. resolve-pr is IN scope for exactly one mechanical fix (R7 double config-get, `workflow.md:422-423`) — its heredoc/jq flows are clean.
- Do NOT "fix" deliberate re-probes: land `workflow.md:473` (fn-66 R3, fresh merge-evidence probe by design); pilot's pre/post-dispatch `gh pr list` pair.
- No weakening of read-back content: summary-only read-backs rejected (Decision context).
- Docs-site: no user-facing behavior change → changelog only at batched release.

## Strategy Alignment

Active tracks served by this plan:
- **Ralph autonomous mode** — hot-path skills (plan, impl-review, work, capture) run per-tick/per-task in the pilot+land loop; every eliminated re-emission multiplies across autonomous runs. Bounded fix-loops on ALL backends (R10) harden the don't-thrash discipline.
- **Cross-platform parity** — the Write/Edit-based patterns are verified against the sync-codex rewrite pipeline (no Write/Edit rewrites exist; mirror regenerated once, in the final task).
- **Self-improving through normal work** — survey findings + kept levers land in `agent_docs/optimization-log.md` per its append-a-row convention.

## Decision context

- Write-tool-as-read-back chosen over (a) summary-only read-back — weakens the user-authoritative fidelity contract on accuracy-critical spec writes; (b) flowctl display helper — the cost is agent re-AUTHORING tokens, not file mechanics.
- File composition chosen over unquoted-heredoc var interpolation for R8: vars don't survive across tool calls (gap analysis), and interpolating untrusted reviewer/spec content is a command-injection surface. `>`/`>>` redirection + quoted-heredoc static blocks is deterministic and injection-free.
- R9 reframed after gap analysis: the echo is the single entry of the response into context today — the fix is "exactly once via file + Read", not deletion. Review round 1 extended it uniformly to all three RP response handlers.
- make-pr §4.6b kept as a conditional gate (it exists to catch hand-rolled `gh pr create` bypassing §4.6a, per `workflow.md:1550-1557`) + a cheap local grep assertion — not deleted.
- Interview correction (survey group C): its write step is already single-emission at the heredoc; interview's real items are the heredoc→Write-tool swap (consistency + edit-cycle delta cheapness), unique paths, and the duplicate spec fetch.
- **Mirror regeneration is serialized into the final task** (review round 1): tasks 1-3 edit canonical files only and MAY run `sync-codex.sh` locally to validate, but the regenerated `plugins/flow-next/codex/` tree is committed once, in fn-81.4 — avoids inter-task mirror conflicts.
- **Task ordering enforces the early proof point** (review round 1): fn-81.2 and fn-81.3 depend on fn-81.1 so the Write-render read-back pattern is validated before other skills adopt its conventions.

## Acceptance Criteria

- **R1:** capture Phase 4→5 emits the spec body once: draft Written to a literal unique path per the path-persistence rule (render = read-back), `AskUserQuestion` body carries summary payload + points to the render, approved content consumed via `spec set-plan --file <literal path>` — no verbatim heredoc re-emission. Approve/edit/abort semantics, 3-cycle cap, and Phase-5 anchor-file ordering unchanged; in autofix the Write render replaces the stdout print (single emission). **Each edit cycle Reads the full draft file before re-approval** (full read-back per cycle; also satisfies Edit's read-before-edit requirement).
- **R2:** interview's three write branches (new-idea / existing-spec / task) use the Write-tool + `--file <literal path>` pattern with unique paths per the path-persistence rule; the duplicate spec fetch is collapsed (fetch once at Detect Input Type `SKILL.md:202-203`, reuse at write-back `:730`); the edit-cycle Read rule applies.
- **R3:** tracker-sync reconcile passes the just-written `.flow/specs/<id>.md` as `set-merge-base --flow-file` (`references/body-merge.md:264-273`; call sites `steps.md:296,334,380`); merged flow body no longer re-emitted to `/tmp/merged-flow.md`; tracker half keeps a unique temp file.
- **R4:** plan drops the post-write `show`+`cat` (`steps.md:487-491`) and the duplicate `show --json` (`:70` vs `:77` — capture once, reuse); the Step 7 fix-loop re-anchor (`:528,:536`) is retained; verified pilot parses flowctl state, not plan's removed stdout.
- **R5:** make-pr §4.6b live-body refetch fires only when the §4.6a local append did not run (hand-rolled-create bypass case); the happy path keeps a cheap local assertion (grep `$REF` in `$BODY_FILE`) instead of the full `gh pr view` round-trip.
- **R6:** deps gathers `specs_json` once and reuses it — the two byte-identical heavy loops (`SKILL.md:52-54`, `:82-84`) become one.
- **R7:** every tracker perEvent gate reads its config leaf exactly once via the `LEAF=$(...)` pattern (`flow-next-work/SKILL.md:184-190` is canonical): capture `workflow.md:786-787`, plan `steps.md:506-508` (Step 6.5), work `phases.md:211-212,303-304,423-425`, resolve-pr `workflow.md:422-423`; final sweep: every `config get tracker.perEvent` hit in `plugins/flow-next/skills/` uses the single-fetch shape.
- **R8:** all four RP prompt-assembly sites + export-context build prompts by file composition — zero content-re-typing placeholders remain (`grep -rn '\[PASTE' plugins/flow-next/skills/` empty; remaining bracket placeholders verified scalar-only: id/branch/focus values, never multi-line content): plan-review `workflow.md:305-325`, impl-review `workflow-rp.md:85-109`, spec-completion-review `workflow-rp.md:88-112`, export-context `SKILL.md:82-93`.
- **R9:** RP review responses enter context exactly once in ALL three handlers (impl-review, spec-completion-review, plan-review): chat-send stdout → unique response file → single Read; verdict/tallies grep the file; no duplicate full-body emissions. Fix loops still receive full findings context.
- **R10:** fix-loop iteration cap (`MAX_REVIEW_ITERATIONS`, default 3) with an actual counter + break/escalate lives in the backend-agnostic common fix loop (impl-review `SKILL.md:333-362` / `workflow-common.md`) and the per-backend files defer to it — `workflow-codex.md` (":39-44 Repeat until SHIP"), `workflow-copilot.md`, `workflow-cursor.md` each updated to reference the bounded common loop; rp keeps behavior (`workflow-rp.md:332`). Enumeration sweep run (`grep -rniE 'rp.{0,3}codex.{0,3}copilot|review.backend'` + cursor) so no doc/table still implies rp-only.
- **R11:** both RP fix loops replace `git add -A` (impl-review `workflow-rp.md:341`, spec-completion-review `workflow-rp.md:449`) with snapshot-scoped staging: record `git status --porcelain` before the fix, diff it after, stage ONLY paths that changed between snapshots (covering modified, untracked, deleted, renamed). If a fixer-modified path was ALREADY dirty before the fix, do NOT stage it — surface the collision and defer/escalate that finding (path-level staging cannot separate pre-existing hunks; never sweep them in).
- **R12:** prime's scout-model prose matches agent frontmatter ground truth re-verified at implementation time (currently 7 haiku: tooling/env/testing/build/observability/security/workflow; 2 sonnet: claude-md, docs-gap): fix `SKILL.md:88`, `:137` header, `workflow.md:5`.
- **R13:** every touched temp path is unique per the path-persistence rule (literal agent-composed path across tool calls; mktemp within one block); final gate greps each known fixed path individually: `/tmp/spec.md`, `/tmp/acc.md`, `/tmp/desc.md`, `/tmp/review-prompt.md`, `/tmp/re-review.md`, `/tmp/updated-plan.md`, `/tmp/export-prompt.md`, `/tmp/completion-review-prompt.md`, `/tmp/merged-flow.md` — zero hits in canonical skills.
- **R14:** tasks 1-3 edit canonical files only (local `sync-codex.sh` validation allowed, mirror not committed); fn-81.4 regenerates the mirror ONCE (run twice — idempotent), commits it, and runs the full gate: smoke from a non-repo cwd (`(cd "$(mktemp -d)" && bash .../smoke_test.sh)`) + `python3 -m pytest plugins/flow-next/tests/` green.
- **R15:** CHANGELOG gains a `## Unreleased` section (does not exist yet — create it) with this spec's entry per house style; `agent_docs/optimization-log.md` gains a row with the COMPUTED count of removed re-emissions/round-trips (count them during implementation; never a placeholder); NO version bump (batched-release rule).

## Early proof point

Task fn-81.1 validates the core approach (Write-tool-as-read-back preserves the capture read-back contract end-to-end, including the edit-cycle Read rule). **fn-81.2 and fn-81.3 depend on fn-81.1** — if the render/read-back pattern fails, re-evaluate pattern 1 (fall back to read-back-in-question + single heredoc) before any other skill adopts it.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | capture single-emission + edit-cycle Read | fn-81.1 | — |
| R2  | interview single-emission + dedupe fetch | fn-81.1 | — |
| R3  | tracker-sync merge-base path | fn-81.3 | — |
| R4  | plan post-write + dup show | fn-81.3 | — |
| R5  | make-pr §4.6b gate | fn-81.3 | — |
| R6  | deps single gather | fn-81.3 | — |
| R7  | config-get single-fetch sweep (incl. plan 6.5) | fn-81.1 (capture site), fn-81.3 (rest) | — |
| R8  | RP file-composition, no content re-typing | fn-81.2 | — |
| R9  | single-entry responses, all 3 RP handlers | fn-81.2 | — |
| R10 | fix-loop cap all backends (incl. cursor file) | fn-81.2 | — |
| R11 | snapshot-scoped staging in rp fix loops | fn-81.2 | — |
| R12 | prime model prose | fn-81.3 | — |
| R13 | unique temp paths + fixed-path greps | fn-81.1, fn-81.2, fn-81.3, gate in fn-81.4 | — |
| R14 | canonical-only tasks; mirror + full gate in .4 | fn-81.4 | — |
| R15 | CHANGELOG Unreleased + computed optimization-log row | fn-81.4 | — |

===== [5/11] git_status: `git status --short --branch` =====
## fn-258-smaller-default-outputs-and-bundles...origin/main [ahead 1]
 M agent_docs/adding-skills.md
 M optimization/worker-anchor/run_eval.py
 M plugins/flow-next/agents/repo-scout.md
 M plugins/flow-next/agents/spec-scout.md
 M plugins/flow-next/agents/worker.md
 M plugins/flow-next/codex/agents/repo-scout.toml
 M plugins/flow-next/codex/agents/spec-scout.toml
 M plugins/flow-next/codex/agents/worker.toml
 M plugins/flow-next/codex/docs/flow-next/flowctl.md
 M plugins/flow-next/codex/docs/flow-next/glossary.md
 M plugins/flow-next/codex/skills/flow-next-capture/workflow.md
 M plugins/flow-next/codex/skills/flow-next-features/SKILL.md
 M plugins/flow-next/codex/skills/flow-next-impl-review/workflow-codex.md
 M plugins/flow-next/codex/skills/flow-next-impl-review/workflow-host.md
 M plugins/flow-next/codex/skills/flow-next-impl-review/workflow-rp.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/SKILL.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-claude.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-codex.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-copilot.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-cursor.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-host.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-rp.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow.md
 M plugins/flow-next/codex/skills/flow-next-plan/references/selected-review.md
 M plugins/flow-next/codex/skills/flow-next-refine/references/pass-business.md
 M plugins/flow-next/codex/skills/flow-next-resolve-pr/SKILL.md
 M plugins/flow-next/codex/skills/flow-next-resolve-pr/workflow.md
 M plugins/flow-next/codex/skills/flow-next-setup/templates/agents-md-snippet.md
 M plugins/flow-next/codex/skills/flow-next-setup/templates/claude-md-snippet.md
 M plugins/flow-next/codex/skills/flow-next-setup/workflow.md
 M plugins/flow-next/codex/skills/flow-next-spec-completion-review/workflow-host.md
 M plugins/flow-next/codex/skills/flow-next-spec-completion-review/workflow-rp.md
 M plugins/flow-next/codex/skills/flow-next-tracker-sync/references/adapter-interface.md
 M plugins/flow-next/codex/skills/flow-next-tracker-sync/references/body-merge.md
 M plugins/flow-next/codex/skills/flow-next-tracker-sync/references/comments-sync.md
 M plugins/flow-next/codex/skills/flow-next-tracker-sync/references/status-sync.md
 M plugins/flow-next/codex/skills/flow-next-work/SKILL.md
 M plugins/flow-next/codex/skills/flow-next-work/phases.md
 M plugins/flow-next/codex/skills/flow-next-work/references/host-deferred-review.md
 M plugins/flow-next/codex/skills/flow-next/SKILL.md
 M plugins/flow-next/commands/audit.md
 M plugins/flow-next/commands/capture.md
 M plugins/flow-next/commands/chart.md
 M plugins/flow-next/commands/features.md
 M plugins/flow-next/commands/flow.md
 M plugins/flow-next/commands/impl-review.md
 M plugins/flow-next/commands/land.md
 M plugins/flow-next/commands/make-pr.md
 M plugins/flow-next/commands/map.md
 M plugins/flow-next/commands/memory-migrate.md
 M plugins/flow-next/commands/plan-review.md
 M plugins/flow-next/commands/plan.md
 M plugins/flow-next/commands/prime.md
 M plugins/flow-next/commands/prose.md
 M plugins/flow-next/commands/prospect.md
 M plugins/flow-next/commands/qa.md
 M plugins/flow-next/commands/ralph-init.md
 M plugins/flow-next/commands/refine.md
 M plugins/flow-next/commands/resolve-pr.md
 M plugins/flow-next/commands/setup.md
 M plugins/flow-next/commands/spec-completion-review.md
 M plugins/flow-next/commands/strategy.md
 M plugins/flow-next/commands/sync.md
 M plugins/flow-next/commands/tracker-sync.md
 M plugins/flow-next/commands/uninstall.md
 M plugins/flow-next/commands/visual.md
 M plugins/flow-next/commands/work.md
 M plugins/flow-next/docs/flowctl.md
 M plugins/flow-next/docs/glossary.md
 M plugins/flow-next/scripts/flowctl.py
 M plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json
 M plugins/flow-next/skills/flow-next-capture/workflow.md
 M plugins/flow-next/skills/flow-next-features/SKILL.md
 M plugins/flow-next/skills/flow-next-flow/auto.md
 M plugins/flow-next/skills/flow-next-flow/references/backlog-mode.md
 M plugins/flow-next/skills/flow-next-flow/references/gate-selection.md
 M plugins/flow-next/skills/flow-next-flow/references/plan-vs-no-plan.md
 M plugins/flow-next/skills/flow-next-flow/references/route-matrix.md
 M plugins/flow-next/skills/flow-next-flow/references/tail.md
 M plugins/flow-next/skills/flow-next-flow/workflow.md
 M plugins/flow-next/skills/flow-next-impl-review/workflow-codex.md
 M plugins/flow-next/skills/flow-next-impl-review/workflow-host.md
 M plugins/flow-next/skills/flow-next-impl-review/workflow-rp.md
 M plugins/flow-next/skills/flow-next-plan-review/SKILL.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-claude.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-codex.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-copilot.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-cursor.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-host.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow.md
 M plugins/flow-next/skills/flow-next-plan/references/selected-review.md
 M plugins/flow-next/skills/flow-next-refine/SKILL.md
 M plugins/flow-next/skills/flow-next-refine/references/pass-business.md
 M plugins/flow-next/skills/flow-next-resolve-pr/SKILL.md
 M plugins/flow-next/skills/flow-next-resolve-pr/workflow.md
 M plugins/flow-next/skills/flow-next-setup/templates/agents-md-snippet.md
 M plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md
 M plugins/flow-next/skills/flow-next-setup/workflow.md
 M plugins/flow-next/skills/flow-next-spec-completion-review/workflow-host.md
 M plugins/flow-next/skills/flow-next-spec-completion-review/workflow-rp.md
 M plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md
 M plugins/flow-next/skills/flow-next-tracker-sync/references/body-merge.md
 M plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md
 M plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md
 M plugins/flow-next/skills/flow-next-work/SKILL.md
 M plugins/flow-next/skills/flow-next-work/phases.md
 M plugins/flow-next/skills/flow-next-work/references/host-deferred-review.md
 M plugins/flow-next/skills/flow-next-work/references/rolling-scheduler.md
 M plugins/flow-next/skills/flow-next-work/references/wave-join.md
 M plugins/flow-next/skills/flow-next/SKILL.md
 M plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-capture-brief.json
 M plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-chart.json
 M plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-interview.json
 M plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-skip-chart-clear.json
 M plugins/flow-next/tests/test_anchor_bundle.py
 M plugins/flow-next/tests/test_flow_merge_destination.py
 M plugins/flow-next/tests/test_parallel_work_prose.py
 M plugins/flow-next/tests/test_pilot_chain_stages.py
 M plugins/flow-next/tests/test_precheck_mode_contract.py
 M plugins/flow-next/tests/test_review_convergence_cap.py
 M plugins/flow-next/tests/test_setup_snippet_lockstep.py
 M scripts/sync-codex.sh
?? optimization/worker-anchor/gen_fn258_inputs.py
?? optimization/worker-anchor/inputs/fn-64.3/bundle-current.md
?? optimization/worker-anchor/inputs/fn-64.3/bundle-lean.md
?? optimization/worker-anchor/inputs/fn-74.2/bundle-current.md
?? optimization/worker-anchor/inputs/fn-74.2/bundle-lean.md
?? optimization/worker-anchor/inputs/fn-81.2/bundle-current.md
?? plugins/flow-next/codex/skills/flow-next-tracker-sync/references/chart-subjects.md
?? plugins/flow-next/skills/flow-next-tracker-sync/references/chart-subjects.md
?? plugins/flow-next/tests/test_glossary_match.py
?? plugins/flow-next/tests/test_skill_id_invocations.py

===== [6/11] git_log: `git log -5 --oneline` =====
c13a4d52 chore(flow): record fn-258 direct route and mint the owner task
e5535836 Correctness and hygiene sweep (audit wave 3) (#472)
b4c980af Unattended-run correctness fixes (audit wave 1) (#470)
9509a2cf Test suite and CI wall-clock (audit wave 2) (#471)
b334b5d7 chore(flow-next): bump version to 6.0.2

===== [7/11] git_branch: `git rev-parse --abbrev-ref HEAD` =====
fn-258-smaller-default-outputs-and-bundles

===== [8/11] memory_enabled: `flowctl config get memory.enabled --json` =====
{
  "success": true,
  "key": "memory.enabled",
  "value": true
}

===== [9/11] glossary: `flowctl glossary list --json --match "<task title + description>"` =====
{
  "success": true,
  "groups": [
    {
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/GLOSSARY.md",
      "entries": [
        {
          "term": "Spec",
          "definition": "The unit of intent: `.flow/specs/<id>.md` (body) + `.flow/specs/<id>.json` (metadata sidecar). Reviewable on its own, cross-model reviewed, frozen at handover. One spec is a stream of work, not a sprint item \u2014 it holds acceptance criteria (R-IDs), not a to-do list.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Task, R-ID, Chart",
          "avoid": [
            "epic",
            "ticket",
            "story",
            "PRD",
            "requirements doc"
          ],
          "relates_to": [
            "Task",
            "R-ID",
            "Chart"
          ]
        },
        {
          "term": "Wave",
          "definition": "A set of tasks whose dependencies are all satisfied at the same point \u2014 the parallel candidates `/flow-next:plan` reports. A wave is a scheduling fact derived from the dependency graph, not a time box and not a mandate to share one checkout: parallel workers get isolated workspaces and the conductor joins the wave before review.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Task",
          "avoid": [
            "sprint",
            "phase",
            "batch",
            "iteration"
          ],
          "relates_to": [
            "Task"
          ]
        },
        {
          "term": "Chart",
          "definition": "Optional pre-capture decision mapping (`/flow-next:chart`) for one idea too large or unclear to capture in a single session: decisions (`D1`, `D2`, ...) under `.flow/charts/`, exiting as a briefing package for `/flow-next:capture`. Chart makes an effort understandable enough to plan; plan decomposes work already understood; prospect ranks plural candidate ideas. Never writes a spec, never sets `ready`.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Spec, Task",
          "avoid": [
            "discovery doc",
            "RFC",
            "design doc",
            "plan",
            "prospect"
          ],
          "relates_to": [
            "Spec",
            "Task"
          ]
        },
        {
          "term": "Spine",
          "definition": "The always-loaded body of a `SKILL.md` under branch disclosure: the universal path every run needs, with branch-only content read from `references/*.md` at the branch point. A reference is the cold-path file; the spine is the hot path. Safety nets and every-run contracts stay in the spine by rule.",
          "avoid": [
            "prompt",
            "main file",
            "header",
            "preamble"
          ],
          "relates_to": []
        },
        {
          "term": "Hop",
          "definition": "One route-run-re-evaluate cycle of `/flow-next:flow`: classify the item from the routing reference, run the routed stage, verify from observed state, record the outcome. Under `--auto` every hop ends with committed receipts, one evidence echo, one `stage: <name> - ran | skipped(<reason>) | failed(<reason>)` line, and a ledger write, so a run that dies mid-way resumes from disk on the next invocation; nothing is resumed from transcript. The hop is the handover unit between the driver and the pipeline.",
          "avoid": [
            "step",
            "iteration",
            "turn"
          ],
          "relates_to": [
            "Driver",
            "Tick",
            "Long-horizon run"
          ]
        }
      ],
      "count": 5
    }
  ],
  "file_count": 1,
  "total_terms": 5
}

===== [10/11] memory_index: `flowctl memory list` =====
bug/build-errors/
  detectvalidate-must-require-specs-dir-2026-05-08 — "detect/validate must require SPECS_DIR even when EPICS_DIR present" (module: plugins/flow-next/scripts/flowctl.py)
  template-rewrite-env-var-cascade-2026-05-09 — "Env-var cascade in templates + canonical config.env knob alignment" (module: plugins/flow-next/skills/flow-next-ralph-init/templates, config.env, ralph.sh)
  abort-option-copy-must-reflect-pre-2026-05-18 — "Abort-option copy must reflect pre-prompt state mutations (idempotent != no chan" (module: plugins/flow-next/skills/flow-next-setup/workflow.md)
  codex-mirror-smoke-docs-miss-composed-2026-05-18 — "Codex mirror smoke docs miss composed transform output (abort + Other)" (module: agent_docs/local-dev.md)
  fn-44-review-cycle-lessons-2026-05-21 — "fn-44 review-cycle lessons (10+ NEEDS_WORK rounds across 4 tasks)" (module: plugins/flow-next/skills/flow-next-interview, plugins/flow-next/skills/flow-next-capture, plugins/flow-next/scripts/flowctl.py, scripts/sync-codex.sh, plugins/flow-next/templates/spec.md)
  scout-fallback-prose-drifted-from-specs-2026-05-26 — "Scout fallback prose drifted from spec's decision-lock command shape" (module: plugins/flow-next/agents/context-scout.md)
  skill-bash-set-arguments-cant-honor-2026-05-26 — "Skill bash `set -- $ARGUMENTS` can't honor 'verbatim' passthrough" (module: plugins/flow-next/skills/flow-next-map/workflow.md)
  id-grammar-widening-must-cover-the-full-2026-06-03 — "Id-grammar widening must cover the FULL command surface, not just named commands" (module: plugins/flow-next/scripts/flowctl.py)
  env-marker-gate-must-scan-the-namespace-2026-06-04 — "Env-marker gate must scan the namespace, not a fixed var list" (module: plugins/flow-next/skills/flow-next-work/references/codex-delegation.md)
  docs-activation-command-for-string-enum-2026-06-05 — "Docs activation command for string-enum config knob used bool true instead of th" (module: plugins/flow-next/docs/flowctl.md, .flow/usage.md)
  sed-piped-default-masks-empty-source-2026-06-05 — "sed-piped default masks empty source: || fallback never fires" (module: plugins/flow-next/skills/flow-next-qa/workflow.md)
  skill-adding-version-bump-leaves-stale-2026-06-05 — "Skill-adding version bump leaves stale skill/command counts in JSON manifest des" (module: plugins/flow-next/.claude-plugin/plugin.json, .claude-plugin/marketplace.json, plugins/flow-next/.codex-plugin/plugin.json)
  mirror-regen-exposes-latent-canonical-2026-06-11 — "Mirror regen exposes latent canonical gaps: path rewrites, .flow persistence, di" (module: scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-land/workflow.md)
  skill-workflow-snippets-must-enforce-2026-06-11 — "Skill workflow snippets must enforce what the prose mandates (vars, gates, dispa" (module: plugins/flow-next/skills/flow-next-land/workflow.md)
  embedded-self-check-greps-in-reference-2026-06-12 — "Embedded self-check greps in reference docs need POSIX classes + whitespace tole" (module: plugins/flow-next/references/html-artifacts.md)
  lavish-interactive-only-gate-must-check-2026-06-12 — "Lavish interactive-only gate must check MODE var AND env markers in-snippet" (module: plugins/flow-next/skills/flow-next-capture/references/html-lens.md)
  optional-side-effect-snippets-need-2026-06-12 — "Optional side-effect snippets need guarded git steps; check-ignore the exact fil" (module: plugins/flow-next/skills/flow-next-make-pr/html-lens.md)
  policy-claim-inversion-sweep-all-2026-06-18 — "Policy-claim inversion: sweep ALL surfaces (both ceremony copies, docs, CLI head" (module: plugins/flow-next/skills/flow-next-tracker-sync/steps.md)
  status-policy-map-needs-a-matching-2026-06-18 — "Status-policy map needs a matching reconcile-loop branch per rung (map ≠ write)" (module: plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md)
  backlog-select-must-not-drop-a-dep-2026-06-27 — "Backlog SELECT must not drop a dep-blocked item to NO_WORK — it routes to BLOCKE" (module: plugins/flow-next/skills/flow-next-pilot/references/backlog-mode.md)
  r2-ask-block-mis-injected-into-negation-2026-06-27 — "R2 ask-block mis-injected into negation-only autonomy prose on mirror regen" (module: scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-pilot, plugins/flow-next/skills/flow-next-tracker-sync/steps.md)
  verdict-tasks-must-rewrite-not-banner-a-2026-07-03 — "Verdict tasks must rewrite, not banner, a sibling task's flipped scope" (module: .flow/tasks)
  eval-ledger-feature-rows-must-disclaim-2026-07-18 — "Eval-ledger feature rows must disclaim the optimization ratchet + reconcile deno" (module: optimization/interview)
  unit-rename-substitution-broke-trigger-2026-07-18 — "Unit-rename substitution broke trigger thresholds (turns->rounds, fn-100)" (module: plugins/flow-next/skills/flow-next-interview/references/doc-aware.md)
  grep-c-prints-0-and-exits-1-echo-0-2026-07-24 — "grep -c prints 0 AND exits 1: || echo 0 yields a two-line count" (module: plugins/flow-next/skills/flow-next-audit/workflow.md)
  changelog-entry-landed-in-a-released-2026-08-01 — "Changelog entry landed in a released section, not Unreleased" (module: CHANGELOG.md)
  codex-home-rewrite-both-spellings-2026-08-02 — "CODEX_HOME rewrite: both spellings, actionable prose, quoting, sorted-hash idemp" (module: scripts/sync-codex.sh)
  concurrent-gating-draws-soft-terms-2026-08-21 — "Concurrent gating draws + soft terms falsify a 'frozen' eval pre-registration" (module: agent-evals/studies/rolling-frontier-2026-08)
  concurrent-loop-skill-prose-linear-2026-08-22 — "Concurrent-loop skill prose: linear checklist + non-blocking claims contradict" (module: plugins/flow-next/skills/flow-next-work-rolling/references/rolling-scheduler.md)
  canonical-3c-edits-vanish-from-codex-2026-08-28 — "Canonical 3c edits vanish from Codex mirror via stale SECTION3C heredoc" (module: scripts/sync-codex.sh)
  prose-tick-lock-claim-before-read-2026-08-28 — "Prose tick lock: claim before read, serialized reap, liveness refresh, persisted" (module: plugins/flow-next/skills/flow-next-land/workflow.md)
  delegating-cli-wrapper-inherits-2026-08-30 — "Delegating CLI wrapper inherits delegate guards, prints, truncation, races" (module: plugins/flow-next/scripts/flowctl.py)
  skill-flag-gating-a-durable-write-needs-2026-08-31 — "Skill flag gating a durable write needs exact-token parse, not substring" (module: plugins/flow-next/skills/flow-next-capture/SKILL.md)
  implementer-brief-widened-never-list-2026-09-14 — "Implementer brief widened never-list past the spec; child lost its fan-out" (module: plugins/flow-next/templates/usage.md)

bug/data/
  migrationrollback-cli-10-review-cycle-2026-05-08 — "Migration/rollback CLI: 10 review-cycle pitfalls (fn-43.3)" (module: plugins/flow-next/scripts/flowctl.py)
  paired-snapshot-setter-must-write-both-2026-06-03 — "Paired-snapshot setter must write both halves atomically (merge base)" (module: plugins/flow-next/scripts/flowctl.py)
  fence-preserving-writer-needs-fence-2026-07-02 — "Fence-preserving writer needs fence-aware readers/validators (write/read parity)" (module: plugins/flow-next/scripts/flowctl.py)
  yaml-frontmatter-writer-unescaped-2026-07-24 — "YAML frontmatter writer: unescaped newlines lose the entry; frontmatter-only wri" (module: plugins/flow-next/scripts/flowctl.py)
  adding-a-key-to-a-content-hash-orphans-2026-08-01 — "Adding a key to a content hash orphans records the old binary wrote" (module: plugins/flow-next/scripts/flowctl.py)
  docs-for-a-hash-identity-fix-inherit-2026-08-01 — "Docs for a hash-identity fix inherit the hash's precision" (module: plugins/flow-next/docs/flowctl.md)
  relaxing-a-validator-must-only-admit-2026-09-26 — "Relaxing a validator must only admit values the writer round-trips" (module: plugins/flow-next/scripts/flowctl.py)

bug/integration/
  drop-receipt-to-break-codex-2026-05-09 — "Drop receipt to break codex confabulation in long review fix loops" (module: plugins/flow-next/scripts/flowctl.py)
  set-tracker-id-rejected-github-n-2026-06-03 — "set-tracker-id rejected GitHub #N identifiers (Linear-only handle validator)" (module: plugins/flow-next/scripts/flowctl.py)
  trackers-auto-linkify-issue-key-2026-06-03 — "Trackers auto-linkify issue-key substrings inside markers (even in HTML comments" (module: plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md)
  heredoc-built-json-breaks-on-free-form-2026-06-05 — "Heredoc-built JSON breaks on free-form interpolated values" (module: skills/flow-next-qa/workflow.md)
  rp-builder-file-slices-cause-false-2026-06-10 — "RP builder file slices cause false-positive 'missing docs' review findings" (module: plugins/flow-next/skills/flow-next-impl-review)
  gh-api-f-stringifies-numeric-body-2026-06-17 — "gh api -f stringifies numeric body fields (issue_id) → GitHub 422; use -F" (module: plugins/flow-next/scripts/flowctl_tracker/)
  markerstruct-field-semantics-must-2026-06-27 — "Marker/struct-field semantics must update the PRODUCER adapter contract, not jus" (module: plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md)
  ceremony-validation-must-read-persisted-2026-06-28 — "Ceremony validation must read PERSISTED config, not re-race env; don't collapse " (module: plugins/flow-next/skills/flow-next-tracker-sync/steps.md)
  adding-a-review-backend-sweep-all-2026-06-29 — "Adding a review backend: sweep ALL enumeration sites (config table, stage list, " (module: plugins/flow-next/docs, plugins/flow-next/scripts/flowctl.py)
  byte-for-byte-spec-contract-branch-2026-07-01 — "Byte-for-byte spec contract: branch prose into variants, don't annotate shared l" (module: plugins/flow-next/skills/flow-next-plan-review/SKILL.md)
  skill-bash-blocks-re-declare-every-2026-07-02 — "Skill bash blocks: re-declare EVERY literal path per block (vars die across tool" (module: plugins/flow-next/skills)
  spec-named-config-keys-must-be-checked-2026-07-15 — "Spec-named config keys must be checked against shipped surface; cross-family is" (module: plugins/flow-next/skills/flow-next-setup/workflow.md)
  claude-p-clean-room-on-oauth-logins-2026-07-16 — "claude -p clean-room on OAuth logins: --setting-sources project,local; --bare an" (module: agent_docs/guidance-eval/runner.sh)
  path-handoff-template-id-slots-must-use-2026-07-19 — "Path-handoff template id slots must use canonical ids, not aliases" (module: plugins/flow-next/skills/flow-next-work/references/codex-delegation.md)
  summary-sinks-for-repeatable-mixed-2026-07-19 — "Summary sinks for repeatable mixed-outcome events need per-event lines, not one " (module: plugins/flow-next/skills/flow-next-work/phases.md)
  skill-fence-consolidation-6-contract-2026-07-20 — "Skill-fence consolidation: 6 contract regressions (var-atomicity, symlink, dry-r" (module: plugins/flow-next/skills)
  caller-facade-guards-must-cover-retro-2026-07-29 — "Caller facade guards must cover retro-fire paths" (module: plugins/flow-next/skills/flow-next-capture/workflow.md)
  caller-fakes-must-enforce-lifecycle-2026-07-29 — "Caller fakes must enforce lifecycle facade input contracts" (module: plugins/flow-next/tests/test_tracker_caller_execution.py)
  caller-oracle-must-preserve-historical-2026-07-29 — "Caller oracle must preserve historical quirks and exact observations" (module: plugins/flow-next/tests/test_tracker_caller_oracle.py)
  tracker-ownership-rewrites-require-2026-07-29 — "Tracker ownership rewrites require adjacent fidelity sweeps" (module: plugins/flow-next/docs/tracker-sync.md)
  head-bound-html-artifacts-must-not-2026-07-30 — "Head-bound HTML artifacts must not stale their own input" (module: plugins/flow-next/skills/flow-next-make-pr/html-lens.md)
  land-evidence-field-defaulted-to-off-on-2026-08-19 — "land evidence field defaulted to 'off' on configured-but-not-due paths" (module: plugins/flow-next/skills/flow-next-land/workflow.md)
  installer-must-own-what-it-deletes-2026-08-21 — "(no title)" (module: scripts/install-codex.sh, scripts/sync-codex.sh)
  scheduler-prose-asserted-wrong-config-2026-08-22 — "Scheduler prose asserted wrong config default; slot-hold drain rules deadlock" (module: plugins/flow-next/skills/flow-next-work-rolling/references/rolling-scheduler.md)
  backend-special-case-in-a-shared-helper-2026-09-05 — "Backend special-case in a shared helper is an enumeration site too" (module: plugins/flow-next/scripts/flowctl.py)
  ci-path-classification-must-include-2026-09-05 — "CI path classification must include rename sources" (module: scripts/ci/classify_changes.py)
  cross-family-review-claims-key-on-the-2026-09-05 — "Cross-family review claims key on the writer's model family, never the host name" (module: plugins/flow-next/docs)
  headless-review-backend-error-envelope-2026-09-05 — "Headless review backend: error-envelope text must never ride the output slot" (module: plugins/flow-next/scripts/flowctl.py)
  forwarded-license-carried-the-wrong-2026-09-14 — "Forwarded license carried the wrong holder's commit contract into the bridged ch" (module: plugins/flow-next/agents/worker.md)
  plan-review-criteria-edits-must-also-2026-09-14 — "Plan-review criteria edits must also sweep workflow-rp.md (CE summary + Classic " (module: plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md)

bug/performance/
  linear-graphql-every-nodes-connection-2026-06-03 — "Linear GraphQL: every {nodes} connection needs first: — incl. workflowStates/tea" (module: plugins/flow-next/scripts/flowctl_tracker/wire/linear.py)

bug/runtime-errors/
  who-wins-ladder-must-check-the-2026-06-03 — "Who-wins ladder must check the collision case before single-field rules" (module: plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md)
  flowctl-on-disk-per-key-counter-count-2026-06-27 — "flowctl on-disk per-key counter: count by stored key + lock + coerce sort" (module: plugins/flow-next/scripts/flowctl.py)
  bash-deadline-watchdogs-orphaned-sleep-2026-07-16 — "Bash deadline watchdogs: orphaned sleep holds pipes; group-kill via setsid, not " (module: agent_docs/guidance-eval/runner.sh)
  forced-color-git-grep-output-defeats-2026-07-19 — "Forced-color git grep output defeats regex post-filter (SGR escapes)" (module: plugins/flow-next/scripts/flowctl.py)
  glob-walk-file-loads-need-lstat-screen-2026-07-19 — "Glob-walk file loads need lstat screen + RecursionError; revalidate TTL post-sta" (module: plugins/flow-next/scripts/flowctl.py)
  empty-value-semantics-leak-null-in-2026-07-20 — "Empty-value semantics leak: {} -> null in snapshot config reads; empty file -> T" (module: plugins/flow-next/scripts/flowctl.py)
  structured-review-parsers-must-2026-07-30 — "Structured review parsers must distinguish invalid from absent" (module: plugins/flow-next/scripts/flowctl.py)
  same-owner-alias-re-registration-must-2026-08-02 — "Same-owner alias re-registration must harden a weak claim, not no-op" (module: plugins/flow-next/scripts/flowctl.py)
  one-shot-keyed-to-an-earlier-captured-2026-08-19 — "One-shot keyed to an earlier-captured SHA: re-validate after the claim, release " (module: plugins/flow-next/skills/flow-next-land/workflow.md)
  land-chain-fences-a-failed-read-is-2026-09-13 — "Land chain fences: a failed read is never permission; write multi-layer records " (module: plugins/flow-next/skills/flow-next-land/workflow.md)
  skill-fences-that-degrade-only-without-2026-09-13 — "Skill fences that degrade only without set -e: masked failures in make-pr chain " (module: plugins/flow-next/skills/flow-next-make-pr/create-and-finalize.md)

bug/security/
  rollback-path-sanitizer-must-not-2026-06-05 — "Rollback path-sanitizer must not trim/rewrite bytes; guard git clean against emp" (module: plugins/flow-next/scripts/flowctl.py)
  shell-command-allowlist-gates-must-2026-06-05 — "Shell-command allowlist gates must tokenize argv, not substring-match" (module: plugins/flow-next/scripts/hooks/ralph-guard.py)
  managed-review-transport-must-bound-2026-09-08 — "Managed review transport must bound time and protect scoped credentials" (module: plugins/flow-next/scripts/flowctl.py)
  guard-matcher-narrowing-missed-shell-2026-09-25 — "Guard matcher narrowing missed shell control words and split redirect words" (module: plugins/flow-next/scripts/hooks/ralph-guard.py)

bug/test-failures/
  rename-smoke-rewire-variable-form-cli-2026-05-09 — "Smoke discipline: variable-form CLI, hermetic env, line-level guard scope" (module: plugins/flow-next/scripts)
  test-production-path-not-parallel-construction-2026-05-21 — "Test the production path, not a parallel construction" (module: plugins/flow-next/tests, plugins/flow-next/scripts/flowctl.py)
  test-fixtures-must-mirror-upstream-zod-2026-05-26 — "Test fixtures must mirror upstream Zod enum, not concept" (module: plugins/flow-next/tests/fixtures/clawpatch-map, plugins/flow-next/scripts/flowctl.py)
  archaeology-fn-strip-can-over-strip-a-2026-07-02 — "Archaeology fn-strip can over-strip a test-pinned canonical breadcrumb" (module: plugins/flow-next/skills/flow-next-tracker-sync/steps.md)
  final-gate-grep-for-a-forbidden-token-2026-07-02 — "Final-gate grep for a forbidden token hits the prohibition prose that bans it" (module: plugins/flow-next/skills/flow-next-impl-review)
  test-asserted-a-public-envelope-that-2026-08-01 — "Test asserted a public envelope that never carried the field" (module: plugins/flow-next/tests/test_chart_briefing.py)
  test-runner-timeout-must-kill-a-process-2026-08-04 — "Test-runner timeout must kill a process TREE whose identity outlives the shard" (module: scripts/run_tests_parallel.py)
  two-independent-resolve-calls-faked-a-2026-08-04 — "Two independent resolve() calls faked a path escape on Windows" (module: plugins/flow-next/scripts/flowctl_tracker/lifecycle/helpers.py)
  windows-83-path-test-failures-were-2026-08-04 — "Windows '8.3 path' test failures were cp1252 fixtures + unguarded geteuid" (module: plugins/flow-next/tests/test_normalize_section_content.py)
  flag-substring-assertion-passes-when-a-2026-09-23 — "Flag substring assertion passes when a longer sibling flag is present" (module: plugins/flow-next/tests/test_spec_id_routing_prose.py)

bug/ui/
  flow-nextdev-docs-page-needs-2026-06-03 — "flow-next.dev docs page needs registering in BOTH astro sidebar + site.ts navGro" (module: src/lib/site.ts)

knowledge/best-practices/
  scb-benchmark-proof-fn-163164-2026-08-04 — "SCB benchmark proof: fn-163/164 eliminated ceremony as a cost factor"
  windows-path-shims-cannot-observe-2026-08-11 — "Windows PATH shims cannot observe subprocess spawns (CreateProcess skips PATHEXT" (module: plugins/flow-next/tests)
  failures-after-a-restart-suspect-2026-08-28 — "Failures after a restart: suspect persistent state before code" (module: .flow)

knowledge/conventions/
  unattended-detection-uses-the-full-2026-09-26 — "Unattended detection uses the full autonomy marker namespace" (module: skills)

knowledge/decisions/
  factory-droid-platform-status-2026-05-2026-05-25 — "Factory Droid platform status — 2026-05" (module: plugins/flow-next/docs/platforms.md)
  tracker-sync-is-projection-not-2026-06-01 — "Tracker sync is projection, not coordination (Linear-first)" (module: strategy)
  plan-sync-skip-gate-not-viable-2026-07-03 — "A deterministic plan-sync skip-gate is not viable — do not re-attempt" (module: plugins/flow-next/skills/flow-next-work/phases.md)
  composed-brief-deleted-path-handoff-2026-07-19 — "Composed brief deleted: path-handoff replaces it (fn-103 eval)" (module: plugins/flow-next/skills/flow-next-work/references/codex-delegation.md)
  review-stall-detection-reads-resolution-2026-08-05 — "Review stall detection reads resolution; the trend heuristics are deleted (fn-168)" (module: plugins/flow-next/scripts/flowctl.py)
  bugbot-pre-push-stage-wont-do-patch-id-2026-08-07 — "Bugbot pre-push stage: won't-do - patch-ID dedup falsified live" (module: review)
  pilot-strike-recovery-is-a-cli-verb-not-2026-08-11 — "Pilot strike recovery is a CLI verb, not board-native transition detection" (module: plugins/flow-next/skills/flow-next-pilot)
  ralph-guard-reverts-its-delegation-2026-08-14 — "Ralph guard reverts its delegation amendment; bridge safety is prose-only" (module: plugins/flow-next/scripts/hooks/ralph-guard.py)
  tracked-vs-runtime-durability-contract-2026-08-14 — "Tracked-vs-runtime durability contract - done crosses it, validate respects it" (module: plugins/flow-next/scripts/flowctl.py)

knowledge/workflow/
  audit-sync-codexsh-during-planning-for-2026-04-30 — "Audit sync-codex.sh during planning for Codex mirror impact" (module: planning)
  final-integration-tasks-need-wider-impl-2026-05-26 — "Final-integration tasks need wider impl-review base" (module: review)
  pr-bot-review-loops-do-not-converge-2026-08-04 — "(no title)" (module: review-subsystem)
  split-pr-at-second-adjacent-surface-finding-2026-08-21 — "(no title)" (module: review)
  stacked-pr-squash-close-recovery-2026-08-27 — "Squash-merging a stacked PR's base permanently closes the stacked PR - rebase + successor PR is the recovery" (module: land)
  harness-capability-claims-verify-at-the-2026-08-28 — "Harness capability claims: verify at the installer, not the generator" (module: platforms)
  github-rulesets-need-an-admin-bypass-or-2026-09-11 — "GitHub rulesets need an admin bypass or spec-only commits stall" (module: ci)

===== [11/11] dependencies: ids, titles, statuses, done summaries =====
- fn-81-skill-runtime-token-plumbing-single.1 [todo] - Single-emission spec writes: capture + interview (early proof point)
    Converted capture (Phase 4→5) and interview (all three Write-Refined-Spec branches) to the single-emission write pattern: draft body Written ONCE via the Write tool to a literal unique path (render = read-back), Edit-tool revisions with a mandatory full-file Read before each re-approval, flowctl consumes `spec set-plan/set-acceptance/set-spec --file <literal path>` — the `$SPEC_BODY` heredoc re-emission and fixed `/tmp/spec.md`/`/tmp/acc.md`/`/tmp/desc.md` paths are gone. Capture's tracker gate reads `tracker.perEvent.capture` once (LEAF pattern); interview's duplicate spec fetch collapsed onto the Detect-Input-Type read. Canonical files only; local sync-codex.sh validation run passed (mirror regen deferred to fn-81.4). RP impl-review: SHIP (first pass).

