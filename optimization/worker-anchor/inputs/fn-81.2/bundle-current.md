# Worker anchor bundle - fn-81-skill-runtime-token-plumbing-single.2 (spec fn-81-skill-runtime-token-plumbing-single)

Verbatim outputs of the worker Phase-1 re-anchor reads, fixed order, no filtering or truncation. The bundle is a floor, not a ceiling - memory keyword-search and every further read remain available.

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
  "tracker": {
    "baseHashFlow": "16ff0a0ee9094c3483a1cf27edb9f37bccce65441c7630905718fbfc35d14f58",
    "baseHashTracker": "910649d96e862228fc8cbf0212e6e9fdafcbd1b7fbfd3b37e4b4378857e328f1",
    "depRelations": [],
    "id": "588e86be-739d-48a0-8117-bf63c22f7ccb",
    "identifier": "FLOW-27",
    "lastSyncedAt": "2026-07-02T06:54:10.491769Z",
    "mergeBaseFlow": "# fn-81 Skill runtime token plumbing: single-emission writes, round-trip elimination, fix-loop guards\n\n## Overview\n\nFlow-next skills re-emit large content (spec bodies, review handoffs, PR bodies) multiple times per run and make redundant CLI round-trips. Fleet survey (2026-07-02, all 28 skills) + scout verification quantified the pattern; this spec fixes the runtime plumbing. Skill-markdown-only \u2014 no flowctl CLI changes (`--file <path>` / `--file -` already supported everywhere).\n\nGoals: token efficiency AND speed WITHOUT quality loss. Read-backs stay mandatory and user-authoritative. Methodology anchor: `agent_docs/optimizing-skills.md`.\n\n## Quick commands\n\n```bash\nbash scripts/sync-codex.sh                    # regen mirror + byte-parity guards (run twice: idempotent)\ngit diff --stat plugins/flow-next/codex/      # confirm mirror delta is expected\n(cd \"$(mktemp -d)\" && bash /Users/gordon/work/flow-next/plugins/flow-next/scripts/smoke_test.sh)  # smoke REFUSES to run from the plugin repo \u2014 run from any other cwd\npython3 -m pytest plugins/flow-next/tests/ -q # incl. mirror-parity tests\n```\n\n## Approach \u2014 the three patterns\n\n**1. Single-emission write (capture, interview).** A drafted body is materialized exactly once. The skill writes the draft ONCE via the Write tool \u2014 the tool render IS the user-visible read-back \u2014 revises via Edit-tool deltas, and hands flowctl the file path. Key facts (verified): bash vars do NOT survive across tool calls (capture `workflow.md:707-709` states this \u2014 today the agent re-authors `$SPEC_BODY` into the Phase 5 heredoc; the file-based pattern removes exactly that); sync-codex does NOT rewrite Write/Edit mentions (both platforms understand them; Codex `apply_patch` on a NEW file shows full content).\n\n**Path persistence rule (vars die across tool calls \u2014 applies to the draft path itself):** the draft path is NOT a shell variable. The agent composes a literal unique path (`${TMPDIR:-/tmp}/flow-<skill>-draft-<spec-id>-<agent-chosen 4-char suffix>.md`), uses that literal in the Write call AND in the later `spec set-plan <id> --file <literal path>` call \u2014 the path lives in agent context, never in shell state. mktemp is reserved for paths created and consumed within one bash block.\n\n**Read-back contract preserved** (capture \u00a74.2, `workflow.md:505-521`, `:559`, `:576`): full draft visible in the Write render immediately above the question; the `AskUserQuestion` body carries the summary payload (R-ID list, `[inferred]` tally, diff-of-changed-sections on rewrite) and points to the render; frozen `approve`/`edit`/`abort` options and the 3-edit-cycle cap unchanged. **Autofix (`--yes`): the Write render IS the single full emission** \u2014 it replaces the stdout print-substitute (no separate print, no second read-back; `--yes` consents on the render). Long renders collapse in the terminal \u2014 the question body must say the full draft is in the Write render above (expandable). **Edit-cycle read-back rule:** an Edit render shows only the delta, which is NOT a full read-back \u2014 after each edit cycle, Read the full draft file BEFORE re-asking approval (that Read render is the mandatory full read-back for that cycle; one full emission per edit cycle, same cost as today's re-show \u2014 no regression, no double-authoring). The Read also satisfies Edit's read-before-edit requirement for the next cycle.\n\n**2. File composition for assembled prompts (RP backends, export-context).** Replace heredocs with content-re-typing placeholders (`[PASTE HANDOFF HERE]`, `[PASTE flowctl show OUTPUT]`, `[PASTE SPEC]`) with deterministic file composition \u2014 no shell-var interpolation (vars die across tool calls; unquoted heredocs are injection surfaces for content containing `$`/backticks/`EOF`):\n\n```bash\nPROMPT_FILE=\"${TMPDIR:-/tmp}/flow-review-prompt-<spec-id>-<suffix>.md\"   # literal path, agent context\n$FLOWCTL rp prompt-get --window \"$W\" --tab \"$T\" > \"$PROMPT_FILE\"   # captured, never re-typed\ncat >> \"$PROMPT_FILE\" <<'EOF_CRITERIA'\n<static review criteria \u2014 quoted heredoc, no expansion>\nEOF_CRITERIA\n$FLOWCTL show \"$ID\" >> \"$PROMPT_FILE\"                              # appended, never re-typed\n```\n\nScalar placeholders the agent fills inline (`[SPEC_ID]`, `[BRANCH_NAME]`, `[USER'S FOCUS AREAS]`) are fine \u2014 they are cheap value substitutions, not content re-typing. The acceptance gate distinguishes the two: zero content-re-typing placeholders may remain; scalar slots are allowed.\n\n**3. Single-entry review responses (ALL RP review-response handlers).** `RESPONSE=$(flowctl rp chat-send ...)` + `echo` is how the response enters context at all (command substitution hides stdout) \u2014 the echo is NOT pure waste. Reframe: the response enters context exactly ONCE \u2014 redirect chat-send stdout to a unique response file, Read it once (that is the parse + fix-loop context), run verdict/tally extraction via grep/awk against the file; no second full-body emission. Applies uniformly to impl-review, spec-completion-review, AND plan-review RP handlers (one convention, no per-skill exceptions).\n\n## Boundaries / non-goals\n\n- No flowctl Python behavior changes; no new flags, commands, or skills.\n- Prompt-content trims / progressive-disclosure gating are fn-82, not here (fn-82 rebases onto this).\n- land, drive, strategy, sync, ralph-init: surveyed clean \u2014 out of scope. resolve-pr is IN scope for exactly one mechanical fix (R7 double config-get, `workflow.md:422-423`) \u2014 its heredoc/jq flows are clean.\n- Do NOT \"fix\" deliberate re-probes: land `workflow.md:473` (fn-66 R3, fresh merge-evidence probe by design); pilot's pre/post-dispatch `gh pr list` pair.\n- No weakening of read-back content: summary-only read-backs rejected (Decision context).\n- Docs-site: no user-facing behavior change \u2192 changelog only at batched release.\n\n## Strategy Alignment\n\nActive tracks served by this plan:\n- **Ralph autonomous mode** \u2014 hot-path skills (plan, impl-review, work, capture) run per-tick/per-task in the pilot+land loop; every eliminated re-emission multiplies across autonomous runs. Bounded fix-loops on ALL backends (R10) harden the don't-thrash discipline.\n- **Cross-platform parity** \u2014 the Write/Edit-based patterns are verified against the sync-codex rewrite pipeline (no Write/Edit rewrites exist; mirror regenerated once, in the final task).\n- **Self-improving through normal work** \u2014 survey findings + kept levers land in `agent_docs/optimization-log.md` per its append-a-row convention.\n\n## Decision context\n\n- Write-tool-as-read-back chosen over (a) summary-only read-back \u2014 weakens the user-authoritative fidelity contract on accuracy-critical spec writes; (b) flowctl display helper \u2014 the cost is agent re-AUTHORING tokens, not file mechanics.\n- File composition chosen over unquoted-heredoc var interpolation for R8: vars don't survive across tool calls (gap analysis), and interpolating untrusted reviewer/spec content is a command-injection surface. `>`/`>>` redirection + quoted-heredoc static blocks is deterministic and injection-free.\n- R9 reframed after gap analysis: the echo is the single entry of the response into context today \u2014 the fix is \"exactly once via file + Read\", not deletion. Review round 1 extended it uniformly to all three RP response handlers.\n- make-pr \u00a74.6b kept as a conditional gate (it exists to catch hand-rolled `gh pr create` bypassing \u00a74.6a, per `workflow.md:1550-1557`) + a cheap local grep assertion \u2014 not deleted.\n- Interview correction (survey group C): its write step is already single-emission at the heredoc; interview's real items are the heredoc\u2192Write-tool swap (consistency + edit-cycle delta cheapness), unique paths, and the duplicate spec fetch.\n- **Mirror regeneration is serialized into the final task** (review round 1): tasks 1-3 edit canonical files only and MAY run `sync-codex.sh` locally to validate, but the regenerated `plugins/flow-next/codex/` tree is committed once, in fn-81.4 \u2014 avoids inter-task mirror conflicts.\n- **Task ordering enforces the early proof point** (review round 1): fn-81.2 and fn-81.3 depend on fn-81.1 so the Write-render read-back pattern is validated before other skills adopt its conventions.\n\n## Acceptance Criteria\n\n- **R1:** capture Phase 4\u21925 emits the spec body once: draft Written to a literal unique path per the path-persistence rule (render = read-back), `AskUserQuestion` body carries summary payload + points to the render, approved content consumed via `spec set-plan --file <literal path>` \u2014 no verbatim heredoc re-emission. Approve/edit/abort semantics, 3-cycle cap, and Phase-5 anchor-file ordering unchanged; in autofix the Write render replaces the stdout print (single emission). **Each edit cycle Reads the full draft file before re-approval** (full read-back per cycle; also satisfies Edit's read-before-edit requirement).\n- **R2:** interview's three write branches (new-idea / existing-spec / task) use the Write-tool + `--file <literal path>` pattern with unique paths per the path-persistence rule; the duplicate spec fetch is collapsed (fetch once at Detect Input Type `SKILL.md:202-203`, reuse at write-back `:730`); the edit-cycle Read rule applies.\n- **R3:** tracker-sync reconcile passes the just-written `.flow/specs/<id>.md` as `set-merge-base --flow-file` (`references/body-merge.md:264-273`; call sites `steps.md:296,334,380`); merged flow body no longer re-emitted to `/tmp/merged-flow.md`; tracker half keeps a unique temp file.\n- **R4:** plan drops the post-write `show`+`cat` (`steps.md:487-491`) and the duplicate `show --json` (`:70` vs `:77` \u2014 capture once, reuse); the Step 7 fix-loop re-anchor (`:528,:536`) is retained; verified pilot parses flowctl state, not plan's removed stdout.\n- **R5:** make-pr \u00a74.6b live-body refetch fires only when the \u00a74.6a local append did not run (hand-rolled-create bypass case); the happy path keeps a cheap local assertion (grep `$REF` in `$BODY_FILE`) instead of the full `gh pr view` round-trip.\n- **R6:** deps gathers `specs_json` once and reuses it \u2014 the two byte-identical heavy loops (`SKILL.md:52-54`, `:82-84`) become one.\n- **R7:** every tracker perEvent gate reads its config leaf exactly once via the `LEAF=$(...)` pattern (`flow-next-work/SKILL.md:184-190` is canonical): capture `workflow.md:786-787`, plan `steps.md:506-508` (Step 6.5), work `phases.md:211-212,303-304,423-425`, resolve-pr `workflow.md:422-423`; final sweep: every `config get tracker.perEvent` hit in `plugins/flow-next/skills/` uses the single-fetch shape.\n- **R8:** all four RP prompt-assembly sites + export-context build prompts by file composition \u2014 zero content-re-typing placeholders remain (`grep -rn '\\[PASTE' plugins/flow-next/skills/` empty; remaining bracket placeholders verified scalar-only: id/branch/focus values, never multi-line content): plan-review `workflow.md:305-325`, impl-review `workflow-rp.md:85-109`, spec-completion-review `workflow-rp.md:88-112`, export-context `SKILL.md:82-93`.\n- **R9:** RP review responses enter context exactly once in ALL three handlers (impl-review, spec-completion-review, plan-review): chat-send stdout \u2192 unique response file \u2192 single Read; verdict/tallies grep the file; no duplicate full-body emissions. Fix loops still receive full findings context.\n- **R10:** fix-loop iteration cap (`MAX_REVIEW_ITERATIONS`, default 3) with an actual counter + break/escalate lives in the backend-agnostic common fix loop (impl-review `SKILL.md:333-362` / `workflow-common.md`) and the per-backend files defer to it \u2014 `workflow-codex.md` (\":39-44 Repeat until SHIP\"), `workflow-copilot.md`, `workflow-cursor.md` each updated to reference the bounded common loop; rp keeps behavior (`workflow-rp.md:332`). Enumeration sweep run (`grep -rniE 'rp.{0,3}codex.{0,3}copilot|review.backend'` + cursor) so no doc/table still implies rp-only.\n- **R11:** both RP fix loops replace `git add -A` (impl-review `workflow-rp.md:341`, spec-completion-review `workflow-rp.md:449`) with snapshot-scoped staging: record `git status --porcelain` before the fix, diff it after, stage ONLY paths that changed between snapshots (covering modified, untracked, deleted, renamed). If a fixer-modified path was ALREADY dirty before the fix, do NOT stage it \u2014 surface the collision and defer/escalate that finding (path-level staging cannot separate pre-existing hunks; never sweep them in).\n- **R12:** prime's scout-model prose matches agent frontmatter ground truth re-verified at implementation time (currently 7 haiku: tooling/env/testing/build/observability/security/workflow; 2 sonnet: claude-md, docs-gap): fix `SKILL.md:88`, `:137` header, `workflow.md:5`.\n- **R13:** every touched temp path is unique per the path-persistence rule (literal agent-composed path across tool calls; mktemp within one block); final gate greps each known fixed path individually: `/tmp/spec.md`, `/tmp/acc.md`, `/tmp/desc.md`, `/tmp/review-prompt.md`, `/tmp/re-review.md`, `/tmp/updated-plan.md`, `/tmp/export-prompt.md`, `/tmp/completion-review-prompt.md`, `/tmp/merged-flow.md` \u2014 zero hits in canonical skills.\n- **R14:** tasks 1-3 edit canonical files only (local `sync-codex.sh` validation allowed, mirror not committed); fn-81.4 regenerates the mirror ONCE (run twice \u2014 idempotent), commits it, and runs the full gate: smoke from a non-repo cwd (`(cd \"$(mktemp -d)\" && bash .../smoke_test.sh)`) + `python3 -m pytest plugins/flow-next/tests/` green.\n- **R15:** CHANGELOG gains a `## Unreleased` section (does not exist yet \u2014 create it) with this spec's entry per house style; `agent_docs/optimization-log.md` gains a row with the COMPUTED count of removed re-emissions/round-trips (count them during implementation; never a placeholder); NO version bump (batched-release rule).\n\n## Early proof point\n\nTask fn-81.1 validates the core approach (Write-tool-as-read-back preserves the capture read-back contract end-to-end, including the edit-cycle Read rule). **fn-81.2 and fn-81.3 depend on fn-81.1** \u2014 if the render/read-back pattern fails, re-evaluate pattern 1 (fall back to read-back-in-question + single heredoc) before any other skill adopts it.\n\n## Requirement coverage\n\n| Req | Description | Task(s) | Gap justification |\n|-----|-------------|---------|-------------------|\n| R1  | capture single-emission + edit-cycle Read | fn-81.1 | \u2014 |\n| R2  | interview single-emission + dedupe fetch | fn-81.1 | \u2014 |\n| R3  | tracker-sync merge-base path | fn-81.3 | \u2014 |\n| R4  | plan post-write + dup show | fn-81.3 | \u2014 |\n| R5  | make-pr \u00a74.6b gate | fn-81.3 | \u2014 |\n| R6  | deps single gather | fn-81.3 | \u2014 |\n| R7  | config-get single-fetch sweep (incl. plan 6.5) | fn-81.1 (capture site), fn-81.3 (rest) | \u2014 |\n| R8  | RP file-composition, no content re-typing | fn-81.2 | \u2014 |\n| R9  | single-entry responses, all 3 RP handlers | fn-81.2 | \u2014 |\n| R10 | fix-loop cap all backends (incl. cursor file) | fn-81.2 | \u2014 |\n| R11 | snapshot-scoped staging in rp fix loops | fn-81.2 | \u2014 |\n| R12 | prime model prose | fn-81.3 | \u2014 |\n| R13 | unique temp paths + fixed-path greps | fn-81.1, fn-81.2, fn-81.3, gate in fn-81.4 | \u2014 |\n| R14 | canonical-only tasks; mirror + full gate in .4 | fn-81.4 | \u2014 |\n| R15 | CHANGELOG Unreleased + computed optimization-log row | fn-81.4 | \u2014 |\n",
    "mergeBaseTracker": "## Overview\n\nFlow-next skills re-emit large content (spec bodies, review handoffs, PR bodies) multiple times per run and make redundant CLI round-trips. Fleet survey (2026-07-02, all 28 skills) + scout verification quantified the pattern; this spec fixes the runtime plumbing. Skill-markdown-only \u2014 no flowctl CLI changes (`--file <path>` / `--file -` already supported everywhere).\n\nGoals: token efficiency AND speed WITHOUT quality loss. Read-backs stay mandatory and user-authoritative. Methodology anchor: `agent_docs/optimizing-skills.md`.\n\n## Quick commands\n\n```bash\nbash scripts/sync-codex.sh                    # regen mirror + byte-parity guards (run twice: idempotent)\ngit diff --stat plugins/flow-next/codex/      # confirm mirror delta is expected\n(cd \"$(mktemp -d)\" && bash /Users/gordon/work/flow-next/plugins/flow-next/scripts/smoke_test.sh)  # smoke REFUSES to run from the plugin repo \u2014 run from any other cwd\npython3 -m pytest plugins/flow-next/tests/ -q # incl. mirror-parity tests\n```\n\n## Approach \u2014 the three patterns\n\n**1. Single-emission write (capture, interview).** A drafted body is materialized exactly once. The skill writes the draft ONCE via the Write tool \u2014 the tool render IS the user-visible read-back \u2014 revises via Edit-tool deltas, and hands flowctl the file path. Key facts (verified): bash vars do NOT survive across tool calls (capture `workflow.md:707-709` states this \u2014 today the agent re-authors `$SPEC_BODY` into the Phase 5 heredoc; the file-based pattern removes exactly that); sync-codex does NOT rewrite Write/Edit mentions (both platforms understand them; Codex `apply_patch` on a NEW file shows full content).\n\n**Path persistence rule (vars die across tool calls \u2014 applies to the draft path itself):** the draft path is NOT a shell variable. The agent composes a literal unique path (`${TMPDIR:-/tmp}/flow-<skill>-draft-<spec-id>-<agent-chosen 4-char suffix>.md`), uses that literal in the Write call AND in the later `spec set-plan <id> --file <literal path>` call \u2014 the path lives in agent context, never in shell state. mktemp is reserved for paths created and consumed within one bash block.\n\n**Read-back contract preserved** (capture \u00a74.2, `workflow.md:505-521`, `:559`, `:576`): full draft visible in the Write render immediately above the question; the `AskUserQuestion` body carries the summary payload (R-ID list, `[inferred]` tally, diff-of-changed-sections on rewrite) and points to the render; frozen `approve`/`edit`/`abort` options and the 3-edit-cycle cap unchanged. **Autofix (**`--yes`**): the Write render IS the single full emission** \u2014 it replaces the stdout print-substitute (no separate print, no second read-back; `--yes` consents on the render). Long renders collapse in the terminal \u2014 the question body must say the full draft is in the Write render above (expandable). **Edit-cycle read-back rule:** an Edit render shows only the delta, which is NOT a full read-back \u2014 after each edit cycle, Read the full draft file BEFORE re-asking approval (that Read render is the mandatory full read-back for that cycle; one full emission per edit cycle, same cost as today's re-show \u2014 no regression, no double-authoring). The Read also satisfies Edit's read-before-edit requirement for the next cycle.\n\n**2. File composition for assembled prompts (RP backends, export-context).** Replace heredocs with content-re-typing placeholders (`[PASTE HANDOFF HERE]`, `[PASTE flowctl show OUTPUT]`, `[PASTE SPEC]`) with deterministic file composition \u2014 no shell-var interpolation (vars die across tool calls; unquoted heredocs are injection surfaces for content containing `$`/backticks/`EOF`):\n\n```bash\nPROMPT_FILE=\"${TMPDIR:-/tmp}/flow-review-prompt-<spec-id>-<suffix>.md\"   # literal path, agent context\n$FLOWCTL rp prompt-get --window \"$W\" --tab \"$T\" > \"$PROMPT_FILE\"   # captured, never re-typed\ncat >> \"$PROMPT_FILE\" <<'EOF_CRITERIA'\n<static review criteria \u2014 quoted heredoc, no expansion>\nEOF_CRITERIA\n$FLOWCTL show \"$ID\" >> \"$PROMPT_FILE\"                              # appended, never re-typed\n```\n\nScalar placeholders the agent fills inline (`[SPEC_ID]`, `[BRANCH_NAME]`, `[USER'S FOCUS AREAS]`) are fine \u2014 they are cheap value substitutions, not content re-typing. The acceptance gate distinguishes the two: zero content-re-typing placeholders may remain; scalar slots are allowed.\n\n**3. Single-entry review responses (ALL RP review-response handlers).** `RESPONSE=$(flowctl rp chat-send ...)` + `echo` is how the response enters context at all (command substitution hides stdout) \u2014 the echo is NOT pure waste. Reframe: the response enters context exactly ONCE \u2014 redirect chat-send stdout to a unique response file, Read it once (that is the parse + fix-loop context), run verdict/tally extraction via grep/awk against the file; no second full-body emission. Applies uniformly to impl-review, spec-completion-review, AND plan-review RP handlers (one convention, no per-skill exceptions).\n\n## Boundaries / non-goals\n\n* No flowctl Python behavior changes; no new flags, commands, or skills.\n* Prompt-content trims / progressive-disclosure gating are fn-82, not here (fn-82 rebases onto this).\n* land, drive, strategy, sync, ralph-init: surveyed clean \u2014 out of scope. resolve-pr is IN scope for exactly one mechanical fix (R7 double config-get, `workflow.md:422-423`) \u2014 its heredoc/jq flows are clean.\n* Do NOT \"fix\" deliberate re-probes: land `workflow.md:473` (fn-66 R3, fresh merge-evidence probe by design); pilot's pre/post-dispatch `gh pr list` pair.\n* No weakening of read-back content: summary-only read-backs rejected (Decision context).\n* Docs-site: no user-facing behavior change \u2192 changelog only at batched release.\n\n## Strategy Alignment\n\nActive tracks served by this plan:\n\n* **Ralph autonomous mode** \u2014 hot-path skills (plan, impl-review, work, capture) run per-tick/per-task in the pilot+land loop; every eliminated re-emission multiplies across autonomous runs. Bounded fix-loops on ALL backends (R10) harden the don't-thrash discipline.\n* **Cross-platform parity** \u2014 the Write/Edit-based patterns are verified against the sync-codex rewrite pipeline (no Write/Edit rewrites exist; mirror regenerated once, in the final task).\n* **Self-improving through normal work** \u2014 survey findings + kept levers land in `agent_docs/optimization-log.md` per its append-a-row convention.\n\n## Decision context\n\n* Write-tool-as-read-back chosen over (a) summary-only read-back \u2014 weakens the user-authoritative fidelity contract on accuracy-critical spec writes; (b) flowctl display helper \u2014 the cost is agent re-AUTHORING tokens, not file mechanics.\n* File composition chosen over unquoted-heredoc var interpolation for R8: vars don't survive across tool calls (gap analysis), and interpolating untrusted reviewer/spec content is a command-injection surface. `>`/`>>` redirection + quoted-heredoc static blocks is deterministic and injection-free.\n* R9 reframed after gap analysis: the echo is the single entry of the response into context today \u2014 the fix is \"exactly once via file + Read\", not deletion. Review round 1 extended it uniformly to all three RP response handlers.\n* make-pr \u00a74.6b kept as a conditional gate (it exists to catch hand-rolled `gh pr create` bypassing \u00a74.6a, per `workflow.md:1550-1557`) + a cheap local grep assertion \u2014 not deleted.\n* Interview correction (survey group C): its write step is already single-emission at the heredoc; interview's real items are the heredoc\u2192Write-tool swap (consistency + edit-cycle delta cheapness), unique paths, and the duplicate spec fetch.\n* **Mirror regeneration is serialized into the final task** (review round 1): tasks 1-3 edit canonical files only and MAY run `sync-codex.sh` locally to validate, but the regenerated `plugins/flow-next/codex/` tree is committed once, in fn-81.4 \u2014 avoids inter-task mirror conflicts.\n* **Task ordering enforces the early proof point** (review round 1): fn-81.2 and fn-81.3 depend on fn-81.1 so the Write-render read-back pattern is validated before other skills adopt its conventions.\n\n## Acceptance Criteria\n\n- [ ] **R1:** capture Phase 4\u21925 emits the spec body once: draft Written to a literal unique path per the path-persistence rule (render = read-back), `AskUserQuestion` body carries summary payload + points to the render, approved content consumed via `spec set-plan --file <literal path>` \u2014 no verbatim heredoc re-emission. Approve/edit/abort semantics, 3-cycle cap, and Phase-5 anchor-file ordering unchanged; in autofix the Write render replaces the stdout print (single emission). **Each edit cycle Reads the full draft file before re-approval** (full read-back per cycle; also satisfies Edit's read-before-edit requirement).\n- [ ] **R2:** interview's three write branches (new-idea / existing-spec / task) use the Write-tool + `--file <literal path>` pattern with unique paths per the path-persistence rule; the duplicate spec fetch is collapsed (fetch once at Detect Input Type `SKILL.md:202-203`, reuse at write-back `:730`); the edit-cycle Read rule applies.\n- [ ] **R3:** tracker-sync reconcile passes the just-written `.flow/specs/<id>.md` as `set-merge-base --flow-file` (`references/body-merge.md:264-273`; call sites `steps.md:296,334,380`); merged flow body no longer re-emitted to `/tmp/merged-flow.md`; tracker half keeps a unique temp file.\n- [ ] **R4:** plan drops the post-write `show`+`cat` (`steps.md:487-491`) and the duplicate `show --json` (`:70` vs `:77` \u2014 capture once, reuse); the Step 7 fix-loop re-anchor (`:528,:536`) is retained; verified pilot parses flowctl state, not plan's removed stdout.\n- [ ] **R5:** make-pr \u00a74.6b live-body refetch fires only when the \u00a74.6a local append did not run (hand-rolled-create bypass case); the happy path keeps a cheap local assertion (grep `$REF` in `$BODY_FILE`) instead of the full `gh pr view` round-trip.\n- [ ] **R6:** deps gathers `specs_json` once and reuses it \u2014 the two byte-identical heavy loops (`SKILL.md:52-54`, `:82-84`) become one.\n- [ ] **R7:** every tracker perEvent gate reads its config leaf exactly once via the `LEAF=$(...)` pattern (`flow-next-work/SKILL.md:184-190` is canonical): capture `workflow.md:786-787`, plan `steps.md:506-508` (Step 6.5), work `phases.md:211-212,303-304,423-425`, resolve-pr `workflow.md:422-423`; final sweep: every `config get tracker.perEvent` hit in `plugins/flow-next/skills/` uses the single-fetch shape.\n- [ ] **R8:** all four RP prompt-assembly sites + export-context build prompts by file composition \u2014 zero content-re-typing placeholders remain (`grep -rn '\\[PASTE' plugins/flow-next/skills/` empty; remaining bracket placeholders verified scalar-only: id/branch/focus values, never multi-line content): plan-review `workflow.md:305-325`, impl-review `workflow-rp.md:85-109`, spec-completion-review `workflow-rp.md:88-112`, export-context `SKILL.md:82-93`.\n- [ ] **R9:** RP review responses enter context exactly once in ALL three handlers (impl-review, spec-completion-review, plan-review): chat-send stdout \u2192 unique response file \u2192 single Read; verdict/tallies grep the file; no duplicate full-body emissions. Fix loops still receive full findings context.\n- [ ] **R10:** fix-loop iteration cap (`MAX_REVIEW_ITERATIONS`, default 3) with an actual counter + break/escalate lives in the backend-agnostic common fix loop (impl-review `SKILL.md:333-362` / `workflow-common.md`) and the per-backend files defer to it \u2014 `workflow-codex.md` (\":39-44 Repeat until SHIP\"), `workflow-copilot.md`, `workflow-cursor.md` each updated to reference the bounded common loop; rp keeps behavior (`workflow-rp.md:332`). Enumeration sweep run (`grep -rniE 'rp.{0,3}codex.{0,3}copilot|review.backend'` + cursor) so no doc/table still implies rp-only.\n- [ ] **R11:** both RP fix loops replace `git add -A` (impl-review `workflow-rp.md:341`, spec-completion-review `workflow-rp.md:449`) with snapshot-scoped staging: record `git status --porcelain` before the fix, diff it after, stage ONLY paths that changed between snapshots (covering modified, untracked, deleted, renamed). If a fixer-modified path was ALREADY dirty before the fix, do NOT stage it \u2014 surface the collision and defer/escalate that finding (path-level staging cannot separate pre-existing hunks; never sweep them in).\n- [ ] **R12:** prime's scout-model prose matches agent frontmatter ground truth re-verified at implementation time (currently 7 haiku: tooling/env/testing/build/observability/security/workflow; 2 sonnet: claude-md, docs-gap): fix `SKILL.md:88`, `:137` header, `workflow.md:5`.\n- [ ] **R13:** every touched temp path is unique per the path-persistence rule (literal agent-composed path across tool calls; mktemp within one block); final gate greps each known fixed path individually: `/tmp/spec.md`, `/tmp/acc.md`, `/tmp/desc.md`, `/tmp/review-prompt.md`, `/tmp/re-review.md`, `/tmp/updated-plan.md`, `/tmp/export-prompt.md`, `/tmp/completion-review-prompt.md`, `/tmp/merged-flow.md` \u2014 zero hits in canonical skills.\n- [ ] **R14:** tasks 1-3 edit canonical files only (local `sync-codex.sh` validation allowed, mirror not committed); fn-81.4 regenerates the mirror ONCE (run twice \u2014 idempotent), commits it, and runs the full gate: smoke from a non-repo cwd (`(cd \"$(mktemp -d)\" && bash .../smoke_test.sh)`) + `python3 -m pytest plugins/flow-next/tests/` green.\n- [ ] **R15:** CHANGELOG gains a `## Unreleased` section (does not exist yet \u2014 create it) with this spec's entry per house style; `agent_docs/optimization-log.md` gains a row with the COMPUTED count of removed re-emissions/round-trips (count them during implementation; never a placeholder); NO version bump (batched-release rule).\n\n## Early proof point\n\nTask fn-81.1 validates the core approach (Write-tool-as-read-back preserves the capture read-back contract end-to-end, including the edit-cycle Read rule). **fn-81.2 and fn-81.3 depend on fn-81.1** \u2014 if the render/read-back pattern fails, re-evaluate pattern 1 (fall back to read-back-in-question + single heredoc) before any other skill adopts it.\n\n## Requirement coverage\n\n| Req | Description | Task(s) | Gap justification |\n| -- | -- | -- | -- |\n| R1 | capture single-emission + edit-cycle Read | fn-81.1 | \u2014 |\n| R2 | interview single-emission + dedupe fetch | fn-81.1 | \u2014 |\n| R3 | tracker-sync merge-base path | fn-81.3 | \u2014 |\n| R4 | plan post-write + dup show | fn-81.3 | \u2014 |\n| R5 | make-pr \u00a74.6b gate | fn-81.3 | \u2014 |\n| R6 | deps single gather | fn-81.3 | \u2014 |\n| R7 | config-get single-fetch sweep (incl. plan 6.5) | fn-81.1 (capture site), fn-81.3 (rest) | \u2014 |\n| R8 | RP file-composition, no content re-typing | fn-81.2 | \u2014 |\n| R9 | single-entry responses, all 3 RP handlers | fn-81.2 | \u2014 |\n| R10 | fix-loop cap all backends (incl. cursor file) | fn-81.2 | \u2014 |\n| R11 | snapshot-scoped staging in rp fix loops | fn-81.2 | \u2014 |\n| R12 | prime model prose | fn-81.3 | \u2014 |\n| R13 | unique temp paths + fixed-path greps | fn-81.1, fn-81.2, fn-81.3, gate in fn-81.4 | \u2014 |\n| R14 | canonical-only tasks; mirror + full gate in .4 | fn-81.4 | \u2014 |\n| R15 | CHANGELOG Unreleased + computed optimization-log row | fn-81.4 | \u2014 |\n\n",
    "url": "https://linear.app/gmickel/issue/FLOW-27"
  },
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

===== [5/11] git_status: `git status` =====
On branch fn-258-smaller-default-outputs-and-bundles
Your branch is ahead of 'origin/main' by 1 commit.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   agent_docs/adding-skills.md
	modified:   optimization/worker-anchor/run_eval.py
	modified:   plugins/flow-next/agents/repo-scout.md
	modified:   plugins/flow-next/agents/spec-scout.md
	modified:   plugins/flow-next/agents/worker.md
	modified:   plugins/flow-next/codex/agents/repo-scout.toml
	modified:   plugins/flow-next/codex/agents/spec-scout.toml
	modified:   plugins/flow-next/codex/agents/worker.toml
	modified:   plugins/flow-next/codex/docs/flow-next/flowctl.md
	modified:   plugins/flow-next/codex/docs/flow-next/glossary.md
	modified:   plugins/flow-next/codex/skills/flow-next-capture/workflow.md
	modified:   plugins/flow-next/codex/skills/flow-next-features/SKILL.md
	modified:   plugins/flow-next/codex/skills/flow-next-impl-review/workflow-codex.md
	modified:   plugins/flow-next/codex/skills/flow-next-impl-review/workflow-host.md
	modified:   plugins/flow-next/codex/skills/flow-next-impl-review/workflow-rp.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/SKILL.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-claude.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-codex.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-copilot.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-cursor.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-host.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-rp.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan/references/selected-review.md
	modified:   plugins/flow-next/codex/skills/flow-next-refine/references/pass-business.md
	modified:   plugins/flow-next/codex/skills/flow-next-resolve-pr/SKILL.md
	modified:   plugins/flow-next/codex/skills/flow-next-resolve-pr/workflow.md
	modified:   plugins/flow-next/codex/skills/flow-next-setup/templates/agents-md-snippet.md
	modified:   plugins/flow-next/codex/skills/flow-next-setup/templates/claude-md-snippet.md
	modified:   plugins/flow-next/codex/skills/flow-next-setup/workflow.md
	modified:   plugins/flow-next/codex/skills/flow-next-spec-completion-review/workflow-host.md
	modified:   plugins/flow-next/codex/skills/flow-next-spec-completion-review/workflow-rp.md
	modified:   plugins/flow-next/codex/skills/flow-next-tracker-sync/references/adapter-interface.md
	modified:   plugins/flow-next/codex/skills/flow-next-tracker-sync/references/body-merge.md
	modified:   plugins/flow-next/codex/skills/flow-next-tracker-sync/references/comments-sync.md
	modified:   plugins/flow-next/codex/skills/flow-next-tracker-sync/references/status-sync.md
	modified:   plugins/flow-next/codex/skills/flow-next-work/SKILL.md
	modified:   plugins/flow-next/codex/skills/flow-next-work/phases.md
	modified:   plugins/flow-next/codex/skills/flow-next-work/references/host-deferred-review.md
	modified:   plugins/flow-next/codex/skills/flow-next/SKILL.md
	modified:   plugins/flow-next/commands/audit.md
	modified:   plugins/flow-next/commands/capture.md
	modified:   plugins/flow-next/commands/chart.md
	modified:   plugins/flow-next/commands/features.md
	modified:   plugins/flow-next/commands/flow.md
	modified:   plugins/flow-next/commands/impl-review.md
	modified:   plugins/flow-next/commands/land.md
	modified:   plugins/flow-next/commands/make-pr.md
	modified:   plugins/flow-next/commands/map.md
	modified:   plugins/flow-next/commands/memory-migrate.md
	modified:   plugins/flow-next/commands/plan-review.md
	modified:   plugins/flow-next/commands/plan.md
	modified:   plugins/flow-next/commands/prime.md
	modified:   plugins/flow-next/commands/prose.md
	modified:   plugins/flow-next/commands/prospect.md
	modified:   plugins/flow-next/commands/qa.md
	modified:   plugins/flow-next/commands/ralph-init.md
	modified:   plugins/flow-next/commands/refine.md
	modified:   plugins/flow-next/commands/resolve-pr.md
	modified:   plugins/flow-next/commands/setup.md
	modified:   plugins/flow-next/commands/spec-completion-review.md
	modified:   plugins/flow-next/commands/strategy.md
	modified:   plugins/flow-next/commands/sync.md
	modified:   plugins/flow-next/commands/tracker-sync.md
	modified:   plugins/flow-next/commands/uninstall.md
	modified:   plugins/flow-next/commands/visual.md
	modified:   plugins/flow-next/commands/work.md
	modified:   plugins/flow-next/docs/flowctl.md
	modified:   plugins/flow-next/docs/glossary.md
	modified:   plugins/flow-next/scripts/flowctl.py
	modified:   plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json
	modified:   plugins/flow-next/skills/flow-next-capture/workflow.md
	modified:   plugins/flow-next/skills/flow-next-features/SKILL.md
	modified:   plugins/flow-next/skills/flow-next-flow/auto.md
	modified:   plugins/flow-next/skills/flow-next-flow/references/backlog-mode.md
	modified:   plugins/flow-next/skills/flow-next-flow/references/gate-selection.md
	modified:   plugins/flow-next/skills/flow-next-flow/references/plan-vs-no-plan.md
	modified:   plugins/flow-next/skills/flow-next-flow/references/route-matrix.md
	modified:   plugins/flow-next/skills/flow-next-flow/references/tail.md
	modified:   plugins/flow-next/skills/flow-next-flow/workflow.md
	modified:   plugins/flow-next/skills/flow-next-impl-review/workflow-codex.md
	modified:   plugins/flow-next/skills/flow-next-impl-review/workflow-host.md
	modified:   plugins/flow-next/skills/flow-next-impl-review/workflow-rp.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/SKILL.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-claude.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-codex.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-copilot.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-cursor.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-host.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow.md
	modified:   plugins/flow-next/skills/flow-next-plan/references/selected-review.md
	modified:   plugins/flow-next/skills/flow-next-refine/SKILL.md
	modified:   plugins/flow-next/skills/flow-next-refine/references/pass-business.md
	modified:   plugins/flow-next/skills/flow-next-resolve-pr/SKILL.md
	modified:   plugins/flow-next/skills/flow-next-resolve-pr/workflow.md
	modified:   plugins/flow-next/skills/flow-next-setup/templates/agents-md-snippet.md
	modified:   plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md
	modified:   plugins/flow-next/skills/flow-next-setup/workflow.md
	modified:   plugins/flow-next/skills/flow-next-spec-completion-review/workflow-host.md
	modified:   plugins/flow-next/skills/flow-next-spec-completion-review/workflow-rp.md
	modified:   plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md
	modified:   plugins/flow-next/skills/flow-next-tracker-sync/references/body-merge.md
	modified:   plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md
	modified:   plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md
	modified:   plugins/flow-next/skills/flow-next-work/SKILL.md
	modified:   plugins/flow-next/skills/flow-next-work/phases.md
	modified:   plugins/flow-next/skills/flow-next-work/references/host-deferred-review.md
	modified:   plugins/flow-next/skills/flow-next-work/references/rolling-scheduler.md
	modified:   plugins/flow-next/skills/flow-next-work/references/wave-join.md
	modified:   plugins/flow-next/skills/flow-next/SKILL.md
	modified:   plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-capture-brief.json
	modified:   plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-chart.json
	modified:   plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-interview.json
	modified:   plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-skip-chart-clear.json
	modified:   plugins/flow-next/tests/test_anchor_bundle.py
	modified:   plugins/flow-next/tests/test_flow_merge_destination.py
	modified:   plugins/flow-next/tests/test_parallel_work_prose.py
	modified:   plugins/flow-next/tests/test_pilot_chain_stages.py
	modified:   plugins/flow-next/tests/test_precheck_mode_contract.py
	modified:   plugins/flow-next/tests/test_review_convergence_cap.py
	modified:   plugins/flow-next/tests/test_setup_snippet_lockstep.py
	modified:   scripts/sync-codex.sh

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	optimization/worker-anchor/gen_fn258_inputs.py
	optimization/worker-anchor/inputs/fn-64.3/bundle-current.md
	optimization/worker-anchor/inputs/fn-64.3/bundle-lean.md
	optimization/worker-anchor/inputs/fn-74.2/bundle-current.md
	optimization/worker-anchor/inputs/fn-74.2/bundle-lean.md
	plugins/flow-next/codex/skills/flow-next-tracker-sync/references/chart-subjects.md
	plugins/flow-next/skills/flow-next-tracker-sync/references/chart-subjects.md
	plugins/flow-next/tests/test_glossary_match.py
	plugins/flow-next/tests/test_skill_id_invocations.py

no changes added to commit (use "git add" and/or "git commit -a")

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

===== [9/11] glossary: `flowctl glossary list --json` =====
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
          "term": "Task",
          "definition": "An execution unit under a spec (`fn-N.M`), sized to one `/flow-next:work` iteration (~100k tokens of fresh context). Declares `requires:` dependencies and optionally the R-IDs it `satisfies:`. Implemented by a worker subagent, never by the conductor directly.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Spec, Wave",
          "avoid": [
            "subtask",
            "ticket",
            "issue",
            "story"
          ],
          "relates_to": [
            "Spec",
            "Wave"
          ]
        },
        {
          "term": "R-ID",
          "definition": "A numbered acceptance criterion in a spec, written `**R1:** ...`. Renumber-forbidden after the first review cycle: deletions leave gaps, new criteria take the next unused number. The load-bearing identity of a requirement across the spec, the tasks that satisfy it, the commits, and the PR coverage table. `G1`, `G2` in `.flow/criteria.md` are the same grammar lifted to project scope. An R-ID is judged against evidence at review; it is never required to pre-exist as an executable test (the ATDD contract, which flow-next deliberately does not adopt).\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Spec, Task",
          "avoid": [
            "AC-1",
            "requirement #1",
            "renumbering",
            "req id"
          ],
          "relates_to": [
            "Spec",
            "Task"
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
          "term": "Receipt",
          "definition": "A JSON artefact on disk that proves a step happened and gates the next one \u2014 review receipts under `.flow/review-receipts/`, green receipts under `.flow/tmp/green-receipts/`, QA verdict receipts. A receipt is a file; a verdict is the terminal line a loop skill prints into the transcript for its driver (`PILOT_VERDICT=`, `LAND_VERDICT=`). Never use one word for the other.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Gate, Review backend",
          "avoid": [
            "report",
            "log",
            "verdict",
            "summary"
          ],
          "relates_to": [
            "Gate",
            "Review backend"
          ]
        },
        {
          "term": "Gate",
          "definition": "A pass/fail check the workflow refuses to proceed past \u2014 the repo's full local quality gate (lint, typecheck, tests, docs) run before handoff, plus the review and readiness gates in the pipeline. A green receipt is the proof one exact gate command passed at one exact commit; `flowctl gate check` decides whether that proof still applies. Gates are local and fail-closed; CI is a separate surface.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Receipt",
          "avoid": [
            "check",
            "hook",
            "CI",
            "guardrail"
          ],
          "relates_to": [
            "Receipt"
          ]
        },
        {
          "term": "Anchor",
          "definition": "Re-reading the spec, the task, and git state before work continues, so long sessions do not drift. `flowctl anchor <task-id>` is the per-task bundle a worker reads every iteration; `flowctl brief` is the cold-session equivalent. Not `/flow-next:prime`, which assesses whether a repo is ready for agents at all.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Task, Spec",
          "avoid": [
            "context refresh",
            "priming",
            "warm-up",
            "reload"
          ],
          "relates_to": [
            "Task",
            "Spec"
          ]
        },
        {
          "term": "plan-sync",
          "definition": "`/flow-next:sync` \u2014 the internal pass that updates *downstream task specs* after implementation drift, inside `.flow/`. Do not confuse it with tracker-sync (`/flow-next:tracker-sync`), which projects a spec *outward* to Linear / GitHub / GitLab / Jira and reconciles body, status, and comments. Bare \"sync\" is ambiguous and should not be used for either.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Spec, Task",
          "avoid": [
            "sync",
            "tracker-sync",
            "resync"
          ],
          "relates_to": [
            "Spec",
            "Task"
          ]
        },
        {
          "term": "Review backend",
          "definition": "The engine that performs a cross-model review: `rp` (RepoPrompt), `codex`, `copilot`, `cursor`, `claude`, `host`, or `none`, resolved by the `review.backend` grammar (env > per-spec/task > config). The backend is the review *mechanism*, distinct from the model it happens to run and from the reviewing agent's findings.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Receipt",
          "avoid": [
            "judge",
            "provider",
            "model"
          ],
          "relates_to": [
            "Receipt"
          ]
        },
        {
          "term": "Memory",
          "definition": "Categorized durable learnings under `.flow/memory/` \u2014 `bug/<category>/` and `knowledge/<category>/` entries with YAML frontmatter, searched via `flowctl memory search`. Memory is audited, superseded, and graduated into gates; it is not a scratchpad and not a substitute for docs or code comments.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Gate",
          "avoid": [
            "notes",
            "scratchpad",
            "context files",
            "learnings dump"
          ],
          "relates_to": [
            "Gate"
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
          "term": "Tier",
          "definition": "What kind of model a job wants: `reviewer`, `implementer`, `fast scout`, `thinking scout`, or unset (the session model). A tier binds a model to a stage's execution, never to which stages run \u2014 which stages run is decided by what you invoked. The four names are a user-facing interface defined in exactly one place, [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants); an unrecognized name is treated as unset with one advisory.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Reach, Review backend",
          "avoid": [
            "pin",
            "model tier",
            "capability level",
            "role map"
          ],
          "relates_to": [
            "Reach",
            "Review backend"
          ]
        },
        {
          "term": "Reach",
          "definition": "How the active harness obtains a model for a tier: the in-session model, an in-host subagent, shelling out to another CLI, or not available. Documented once per harness under [`plugins/flow-next/docs/reach/`](plugins/flow-next/docs/reach/README.md) and never inside a skill \u2014 a skill asks for a tier and names no spawn primitive, CLI flag, or vendor path. An undetectable harness resolves to the generic page and says so.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Tier",
          "avoid": [
            "dispatch mechanism",
            "availability",
            "probe"
          ],
          "relates_to": [
            "Tier"
          ]
        },
        {
          "term": "Reviewer tier",
          "definition": "The tier for anything grading work someone else produced. The only tier carrying a family rule: a reviewer from the writer's own family is not an independent verdict. The rule is advice, not enforcement \u2014 the receipt records what ran, and nothing fails closed on it. Canonical definition: [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants).\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Tier, Review backend",
          "avoid": [
            "grader",
            "review model",
            "critic"
          ],
          "relates_to": [
            "Tier",
            "Review backend"
          ]
        },
        {
          "term": "Implementer tier",
          "definition": "The tier for work handed to another harness \u2014 plan on the session model, implement somewhere cheaper or faster. Absent, the session model implements. Canonical definition: [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants).\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Tier, Task",
          "avoid": [
            "bridged worker",
            "executor"
          ],
          "relates_to": [
            "Tier",
            "Task"
          ]
        },
        {
          "term": "Fast scout tier",
          "definition": "The tier for mechanical inventory scanning, where the cheapest model is the correct one. Canonical definition: [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants).\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Tier",
          "avoid": [
            "cheap tier",
            "scanner model",
            "fast model",
            "low tier"
          ],
          "relates_to": [
            "Tier"
          ]
        },
        {
          "term": "Thinking scout tier",
          "definition": "The tier for analysis that degrades badly on a fast model \u2014 requirement analysis and pattern judgment, not scans. Canonical definition: [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants).\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Tier",
          "avoid": [
            "judgment tier",
            "smart scout",
            "intelligent scout",
            "deep scout"
          ],
          "relates_to": [
            "Tier"
          ]
        },
        {
          "term": "Emission point",
          "definition": "A named step in a skill or agent where durable user-facing prose is drafted (make-pr body rendering, tracker-sync comment composition, capture/refine/plan spec prose, chart briefings, strategy sections, qa finding bodies, land verdict output, prospect candidates, prime glossary definitions, audit memory entries, worker done summaries, resolve-pr replies, changelog entries). Emission points cite the prose contract by path, passing the identity and never a copied payload.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "No-plan route",
          "definition": "Execution through `/flow-next:work <spec-id> --no-plan`, the default route for a ready cohesive spec and a capable coding agent. Plan is chosen only on a positive signal; the signals and the exclusions are in [`plan-vs-no-plan.md`](plugins/flow-next/skills/flow-next-flow/references/plan-vs-no-plan.md). Work records the accepted choice and creates one implicit owner task covering every spec R-ID. Resume and `flow --auto` continuation retain that route. Separate task planning and its automatic plan review are omitted; explicit spec/design review, configured implementation review, coverage, completion-review policy and opt-in QA retain their contracts.",
          "avoid": [
            "plan-less mode",
            "skip-plan flag",
            "zero-task execution"
          ],
          "relates_to": [
            "Spec",
            "Task",
            "R-ID"
          ]
        },
        {
          "term": "Feature map",
          "definition": "The committed user-POV directory (`.flow/features/`) recording how a user reaches and drives each user-facing feature, consumed by QA/drive for navigation; distinct from the code-POV `/flow-next:map` index.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Doctor",
          "definition": "The one read-only health check a drive-capable run performs before driving an instance (right build, owned port, valid auth), answering \"is this instance worth driving\".",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Routing reference",
          "definition": "The set of six small reference files the flow skill owns under `plugins/flow-next/skills/flow-next-flow/references/`, one per routing rule, progressively disclosed through step-scoped conditional pointers so the agent reads only the files the current step needs: `route-matrix.md`, `spec-count.md`, `plan-vs-no-plan.md`, `gate-selection.md`, `prototype-before-ask.md`, and `tail.md`. Each opens with a decision record. Flow, `flow --explain`, `flow --auto`, capture's closer, plan's next-steps menu, and work's zero-task ask read the same files. The same directory also holds two gated auto-only references (`backlog-mode.md`, `qa-stage.md`) that `auto.md` reads under `--backlog` and the QA gate; they are workflow, not routing rules, and carry no decision record.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Driver",
          "definition": "The thing that invokes the unattended conductor and owns repetition: a human running `/flow-next:flow --auto` once per item, a host loop primitive (`/loop`, `/goal`, `cron`) running `flow --auto --tick`, or Ralph (the deprecated repo-local hardened harness). Attended `/flow-next:flow` stops at the next human decision; `flow --auto` stops at the next decision that needs a human and reports it as a verdict. Drivers are never recursively nested. The confined composition exception is flow invoking one land tick as its authorized landing stage for the selected spec and PR. Attended flow refuses under any autonomy marker, `flow --auto` refuses under Ralph, and land never dispatches a second driver.",
          "avoid": [
            "mode",
            "conductor mode",
            "autopilot"
          ],
          "relates_to": [
            "Routing reference",
            "Hop",
            "Tick",
            "Long-horizon run",
            "Pilot"
          ]
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
        },
        {
          "term": "Tick",
          "definition": "Exactly one hop of `flow --auto`, selected with `--tick`. The run classifies, dispatches one stage, verifies, records, and stops with the verdict line. A landing hop consumes at most one land tick. The portable floor for hosts without stable long sessions, run under the host's loop primitive (`/loop 30m /flow-next:flow --auto --tick`). What a `/flow-next:pilot` invocation was.",
          "avoid": [
            "pilot tick",
            "single-stage run"
          ],
          "relates_to": [
            "Hop",
            "Long-horizon run",
            "Driver",
            "Pilot"
          ]
        },
        {
          "term": "Long-horizon run",
          "definition": "The default shape of `flow --auto`: one invocation drives one ready item hop after hop until a terminal (a PR exists, deferred to land, asked, blocked, needs human, no work). With `--until=merge`, it can continue through land ticks and external waits until the selected PR is confirmed merged, or an existing stop condition applies. The verdict line names every dispatched stage in order joined by `+` (`stage=work+qa+make-pr`) and carries the last hop's verdict. One item per run; the next invocation selects the next item.",
          "avoid": [
            "multi-stage tick",
            "chained tick",
            "autopilot run"
          ],
          "relates_to": [
            "Hop",
            "Tick",
            "Verdict line"
          ]
        },
        {
          "term": "Verdict line",
          "definition": "The terminal line every `flow --auto` run and every `/flow-next:land` tick prints last, for the driver to read: `PILOT_VERDICT=<ADVANCED|ASKED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason=\"<one line>\"` and `LAND_VERDICT=...`. The `PILOT_VERDICT` name is kept unchanged across the pilot retirement so existing drivers keep parsing; `TRIAGED` appears under `--explain` and `--dry-run` only. Under a merge destination, the reason and observed evidence distinguish landing progress, external waiting, blockage, confirmed merge, and any tracker touchpoint failure; the original `LAND_VERDICT` is retained in the evidence.",
          "avoid": [
            "exit status",
            "summary line",
            "result banner"
          ],
          "relates_to": [
            "Driver",
            "Long-horizon run",
            "Tick"
          ]
        },
        {
          "term": "Pilot",
          "definition": "The deprecated alias for `/flow-next:flow --auto --tick`. Its `/flow-next:pilot` command is removed; the `flow-next-pilot` skill stub remains until the next release and maps `--spec <id>` to the positional id, passes `--backlog`, `--dry-run`, `--review`, `--research`, `--depth` through, prints one deprecation line to stderr, and behaves byte-for-byte as the tick. The spelling survives in config keys (`pilot.autonomy`, `pilot.gateClasses`), flowctl verbs (`flowctl pilot strikes`, `flowctl pilot-log`), the ledger and decision-log paths (`.flow/pilot-runs/`), and the `PILOT_VERDICT` name; those are not renamed.",
          "avoid": [
            "the pilot skill",
            "pilot loop",
            "build-loop conductor"
          ],
          "relates_to": [
            "Tick",
            "Driver",
            "Verdict line"
          ]
        },
        {
          "term": "Variant",
          "definition": "One worked route through the pipeline menu, named by its driving signal in `docs/pipeline-variations.md` and matched by a row of the route matrix: epic, feature with known requirements, no-plan, small task, bug or defect, refactoring, performance, hill climb, investigation, prototype, and docs or chore. Every variant keeps the same evidence, gate, and receipt contract; they differ only in which unknown they pay to convert.",
          "avoid": [
            "pipeline mode",
            "preset",
            "template pipeline"
          ],
          "relates_to": [
            "Routing reference",
            "No-plan route"
          ]
        },
        {
          "term": "Prototype-before-ask",
          "definition": "Classify a fork before asking the user. An answer observable by running something (behavior, output, timing, layout) is settled by a prototype or experiment. Only a product or preference call no experiment can settle becomes a question.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Refine",
          "definition": "The `/flow-next:refine` skill (`flow-next-refine`, renamed from `interview` in the flow release). A deep question pass over a spec, task, or spec file under a `business`, `technical`, or `both` scope, or the read-first research pass under `--scope=research`.",
          "avoid": [
            "interview skill",
            "interview command"
          ],
          "relates_to": []
        },
        {
          "term": "Research pass",
          "definition": "`/flow-next:refine --scope=research`: asks nothing; runs the read-only docs, practice, docs-gap, and memory scouts (github when gated on) and writes one `## Resolved via Research` section with a sub-block per scout and a source on every line. Skipped, with the reason printed, when the section or plan's scout findings already exist; `--force` reruns. Plan writes the same section when its research scouts run, so the pass never runs twice.",
          "avoid": [],
          "relates_to": [
            "Read-first signal",
            "Refine"
          ]
        },
        {
          "term": "Read-first signal",
          "definition": "The positive signal on the route matrix's ready-spec row: the spec names a library or API the repo does not already use. It sends the spec through the research pass before work on either route and is satisfied by a `## Resolved via Research` section or a plan that ran the scouts.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Why-scout",
          "definition": "The read-only agent for rationale questions. It anchors on `git blame` and the PRs behind the commits, reads the tracker thread through access the session already has, then the bug and decision memory tracks, and tiers each finding `direct`, `supported`, `inferred`, or `unknown`; the caller may not rewrite a tier. Named by the route matrix's investigation row for why questions.",
          "avoid": [],
          "relates_to": [
            "Thinking scout tier"
          ]
        },
        {
          "term": "Chain",
          "definition": "A dependent PR whose base is the parent spec's branch instead of the default branch (fn-152). Exists on any code host because it is only a branch and a base ref. A dependent spec is chain-eligible when its parent is open with every task done and its branch on origin, judged by `flowctl spec chain`, the one predicate every consumer calls; work then branches from the parent's remote tip and make-pr targets the parent's branch. Chains are linear: one open parent, one child at a time.",
          "avoid": [
            "stacked branch",
            "dependent branch",
            "branch-on-branch"
          ],
          "relates_to": [
            "Stack",
            "Layer",
            "Frontier",
            "Spec"
          ]
        },
        {
          "term": "Stack",
          "definition": "GitHub's server-side object over a chain: the linked PRs, the stack map in the merge box, sequential merge, and auto-retarget of the layers above a merged one. An enhancement of a chain, present only when the host is GitHub and make-pr's link call succeeded; on any other host, or after a failed link, the PR stands as a plain chain layer. Never a local file: the gh-stack extension is not required or read.",
          "avoid": [
            "gh-stack",
            "stacked diff",
            "Graphite stack"
          ],
          "relates_to": [
            "Chain",
            "Layer",
            "Frontier"
          ]
        },
        {
          "term": "Layer",
          "definition": "One PR in a chain or stack. The bottom layer is the open layer whose base is the chain's base branch (the default branch, or the branch a human chose); every other layer's base is the branch of the layer below it, so a reviewer sees only that layer's own diff.",
          "avoid": [
            "sub-PR",
            "child PR",
            "stacked PR"
          ],
          "relates_to": [
            "Chain",
            "Stack",
            "Frontier"
          ]
        },
        {
          "term": "Frontier",
          "definition": "The bottom open layer of a chain or stack, the only one that can merge next. Land merges at most one frontier per tick, from the bottom up; a human merging from GitHub's stack UI does the same. Distinct from the task frontier `flowctl ready` reports inside one spec.",
          "avoid": [
            "head of the stack",
            "top layer",
            "mergeable PR"
          ],
          "relates_to": [
            "Chain",
            "Stack",
            "Layer"
          ]
        }
      ],
      "count": 39
    }
  ],
  "file_count": 1,
  "total_terms": 39
}

===== [10/11] memory_index: `flowctl memory list --json` =====
{
  "success": true,
  "entries": [
    {
      "entry_id": "bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18",
      "title": "Abort-option copy must reflect pre-prompt state mutations (idempotent != no chan",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-setup/workflow.md",
      "tags": [
        "fn-45",
        "abort-option",
        "setup-skill",
        "copy-drift",
        "codex-review",
        "user-consent"
      ],
      "date": "2026-05-18",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18.md"
    },
    {
      "entry_id": "bug/build-errors/backlog-select-must-not-drop-a-dep-2026-06-27",
      "title": "Backlog SELECT must not drop a dep-blocked item to NO_WORK \u2014 it routes to BLOCKE",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-pilot/references/backlog-mode.md",
      "tags": [
        "fn-68",
        "pilot",
        "backlog-mode",
        "skill-authoring",
        "select-vs-triage",
        "terminal-grammar",
        "rp-review",
        "review-feedback"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/backlog-select-must-not-drop-a-dep-2026-06-27.md"
    },
    {
      "entry_id": "bug/build-errors/canonical-3c-edits-vanish-from-codex-2026-08-28",
      "title": "Canonical 3c edits vanish from Codex mirror via stale SECTION3C heredoc",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh",
      "tags": [
        "fn-208",
        "sync-codex",
        "codex-mirror",
        "section3c",
        "dispatch-template",
        "codex-review"
      ],
      "date": "2026-08-28",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/canonical-3c-edits-vanish-from-codex-2026-08-28.md"
    },
    {
      "entry_id": "bug/build-errors/changelog-entry-landed-in-a-released-2026-08-01",
      "title": "Changelog entry landed in a released section, not Unreleased",
      "track": "bug",
      "category": "build-errors",
      "module": "CHANGELOG.md",
      "tags": [
        "changelog",
        "release",
        "docs"
      ],
      "date": "2026-08-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/changelog-entry-landed-in-a-released-2026-08-01.md"
    },
    {
      "entry_id": "bug/build-errors/codex-home-rewrite-both-spellings-2026-08-02",
      "title": "CODEX_HOME rewrite: both spellings, actionable prose, quoting, sorted-hash idemp",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh",
      "tags": [
        "codex",
        "installer",
        "generated-artifacts",
        "shell-quoting",
        "idempotency"
      ],
      "date": "2026-08-02",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/codex-home-rewrite-both-spellings-2026-08-02.md"
    },
    {
      "entry_id": "bug/build-errors/codex-mirror-smoke-docs-miss-composed-2026-05-18",
      "title": "Codex mirror smoke docs miss composed transform output (abort + Other)",
      "track": "bug",
      "category": "build-errors",
      "module": "agent_docs/local-dev.md",
      "tags": [
        "sync-codex",
        "codex",
        "mirror",
        "fn-45",
        "smoke-docs",
        "AskUserQuestion",
        "abort-option"
      ],
      "date": "2026-05-18",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/codex-mirror-smoke-docs-miss-composed-2026-05-18.md"
    },
    {
      "entry_id": "bug/build-errors/concurrent-gating-draws-soft-terms-2026-08-21",
      "title": "Concurrent gating draws + soft terms falsify a 'frozen' eval pre-registration",
      "track": "bug",
      "category": "build-errors",
      "module": "agent-evals/studies/rolling-frontier-2026-08",
      "tags": [
        "fn-203",
        "eval-design",
        "pre-registration",
        "wall-clock",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-08-21",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/concurrent-gating-draws-soft-terms-2026-08-21.md"
    },
    {
      "entry_id": "bug/build-errors/concurrent-loop-skill-prose-linear-2026-08-22",
      "title": "Concurrent-loop skill prose: linear checklist + non-blocking claims contradict",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-work-rolling/references/rolling-scheduler.md",
      "tags": [
        "fn-203",
        "work-rolling",
        "scheduler",
        "event-driven",
        "plan-sync-barrier",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-08-22",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/concurrent-loop-skill-prose-linear-2026-08-22.md"
    },
    {
      "entry_id": "bug/build-errors/delegating-cli-wrapper-inherits-2026-08-30",
      "title": "Delegating CLI wrapper inherits delegate guards, prints, truncation, races",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-212",
        "memory-upsert",
        "delegation",
        "codex-review",
        "review-feedback",
        "concurrency"
      ],
      "date": "2026-08-30",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/delegating-cli-wrapper-inherits-2026-08-30.md"
    },
    {
      "entry_id": "bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08",
      "title": "detect/validate must require SPECS_DIR even when EPICS_DIR present",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-43",
        "rename",
        "detect",
        "validate",
        "write-location",
        "backward-compat",
        "deprecation",
        "env-vars",
        "acceptance-criteria",
        "review-feedback"
      ],
      "date": "2026-05-08",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08.md"
    },
    {
      "entry_id": "bug/build-errors/docs-activation-command-for-string-enum-2026-06-05",
      "title": "Docs activation command for string-enum config knob used bool true instead of th",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/docs/flowctl.md, .flow/usage.md",
      "tags": [
        "fn-55",
        "work.delegate",
        "config-enum",
        "docs-drift",
        "activation-predicate",
        "codex-delegation",
        "review-feedback"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/docs-activation-command-for-string-enum-2026-06-05.md"
    },
    {
      "entry_id": "bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12",
      "title": "Embedded self-check greps in reference docs need POSIX classes + whitespace tole",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/references/html-artifacts.md",
      "tags": [
        "fn-62",
        "reference-doc",
        "grep",
        "portability",
        "bsd-grep",
        "self-check",
        "copy-paste-blocks",
        "review-feedback"
      ],
      "date": "2026-06-12",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12.md"
    },
    {
      "entry_id": "bug/build-errors/env-marker-gate-must-scan-the-namespace-2026-06-04",
      "title": "Env-marker gate must scan the namespace, not a fixed var list",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-work/references/codex-delegation.md",
      "tags": [
        "fn-55",
        "skill-prose-gate",
        "env-markers",
        "opencode",
        "platform-gate",
        "codex-delegation"
      ],
      "date": "2026-06-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/env-marker-gate-must-scan-the-namespace-2026-06-04.md"
    },
    {
      "entry_id": "bug/build-errors/eval-ledger-feature-rows-must-disclaim-2026-07-18",
      "title": "Eval-ledger feature rows must disclaim the optimization ratchet + reconcile deno",
      "track": "bug",
      "category": "build-errors",
      "module": "optimization/interview",
      "tags": [
        "fn-100",
        "eval-ledger",
        "ratchet",
        "denominator-reconciliation",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-07-18",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/eval-ledger-feature-rows-must-disclaim-2026-07-18.md"
    },
    {
      "entry_id": "bug/build-errors/fn-44-review-cycle-lessons-2026-05-21",
      "title": "fn-44 review-cycle lessons (10+ NEEDS_WORK rounds across 4 tasks)",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-interview, plugins/flow-next/skills/flow-next-capture, plugins/flow-next/scripts/flowctl.py, scripts/sync-codex.sh, plugins/flow-next/templates/spec.md",
      "tags": [
        "fn-44",
        "scope-flag",
        "impl-review",
        "codex-review",
        "json-contract",
        "html-comments",
        "r17-cross-link",
        "r21-drift-guard",
        "merge-contract",
        "auxiliary-sections",
        "scoped-diff",
        "relative-paths",
        "codex-mirror"
      ],
      "date": "2026-05-21",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/fn-44-review-cycle-lessons-2026-05-21.md"
    },
    {
      "entry_id": "bug/build-errors/grep-c-prints-0-and-exits-1-echo-0-2026-07-24",
      "title": "grep -c prints 0 AND exits 1: || echo 0 yields a two-line count",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-audit/workflow.md",
      "tags": [
        "bash",
        "skill-prose",
        "grep",
        "shell-pitfall"
      ],
      "date": "2026-07-24",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/grep-c-prints-0-and-exits-1-echo-0-2026-07-24.md"
    },
    {
      "entry_id": "bug/build-errors/id-grammar-widening-must-cover-the-full-2026-06-03",
      "title": "Id-grammar widening must cover the FULL command surface, not just named commands",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-52",
        "tracker-sync",
        "id-resolution",
        "canonicalizer",
        "enumeration",
        "impl-review",
        "case-rule",
        "validator-separation",
        "sync-receipt",
        "sync-defer",
        "final-integration",
        "merge-base"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/id-grammar-widening-must-cover-the-full-2026-06-03.md"
    },
    {
      "entry_id": "bug/build-errors/implementer-brief-widened-never-list-2026-09-14",
      "title": "Implementer brief widened never-list past the spec; child lost its fan-out",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/templates/usage.md",
      "tags": [
        "fn-245",
        "fn-244",
        "bridge",
        "long-task-brief",
        "never-list",
        "delegation",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-09-14",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/implementer-brief-widened-never-list-2026-09-14.md"
    },
    {
      "entry_id": "bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12",
      "title": "Lavish interactive-only gate must check MODE var AND env markers in-snippet",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-capture/references/html-lens.md",
      "tags": [
        "fn-62",
        "lavish",
        "skill-authoring",
        "safety-gates",
        "review-feedback",
        "html-artifacts"
      ],
      "date": "2026-06-12",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12.md"
    },
    {
      "entry_id": "bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11",
      "title": "Mirror regen exposes latent canonical gaps: path rewrites, .flow persistence, di",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "fn-60",
        "sync-codex",
        "codex-mirror",
        "land",
        "flow-persistence",
        "tracker-dispatch",
        "ledger",
        "review-feedback",
        "release"
      ],
      "date": "2026-06-11",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11.md"
    },
    {
      "entry_id": "bug/build-errors/optional-side-effect-snippets-need-2026-06-12",
      "title": "Optional side-effect snippets need guarded git steps; check-ignore the exact fil",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-make-pr/html-lens.md",
      "tags": [
        "fn-62",
        "make-pr",
        "html-artifacts",
        "skill-authoring",
        "set-e",
        "check-ignore",
        "review-feedback"
      ],
      "date": "2026-06-12",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/optional-side-effect-snippets-need-2026-06-12.md"
    },
    {
      "entry_id": "bug/build-errors/policy-claim-inversion-sweep-all-2026-06-18",
      "title": "Policy-claim inversion: sweep ALL surfaces (both ceremony copies, docs, CLI head",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/steps.md",
      "tags": [
        "fn-66",
        "tracker-sync",
        "ceremony-duplicate",
        "dispatch-grammar",
        "docs-parity",
        "steps.md",
        "SKILL.md"
      ],
      "date": "2026-06-18",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/policy-claim-inversion-sweep-all-2026-06-18.md"
    },
    {
      "entry_id": "bug/build-errors/prose-tick-lock-claim-before-read-2026-08-28",
      "title": "Prose tick lock: claim before read, serialized reap, liveness refresh, persisted",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "fn-208",
        "land",
        "concurrency",
        "ledger",
        "skill-prose",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-08-28",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/prose-tick-lock-claim-before-read-2026-08-28.md"
    },
    {
      "entry_id": "bug/build-errors/r2-ask-block-mis-injected-into-negation-2026-06-27",
      "title": "R2 ask-block mis-injected into negation-only autonomy prose on mirror regen",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-pilot, plugins/flow-next/skills/flow-next-tracker-sync/steps.md",
      "tags": [
        "fn-68",
        "sync-codex",
        "codex-mirror",
        "pilot",
        "backlog-mode",
        "tracker-sync",
        "AskUserQuestion",
        "R2-injection",
        "is_negative_context",
        "autonomy",
        "review-feedback"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/r2-ask-block-mis-injected-into-negation-2026-06-27.md"
    },
    {
      "entry_id": "bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26",
      "title": "Scout fallback prose drifted from spec's decision-lock command shape",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/agents/context-scout.md",
      "tags": [
        "fn-50",
        "clawpatch",
        "scouts",
        "decision-lock-in",
        "flag-drift",
        "codex-review"
      ],
      "date": "2026-05-26",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26.md"
    },
    {
      "entry_id": "bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05",
      "title": "sed-piped default masks empty source: || fallback never fires",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-qa/workflow.md",
      "tags": [
        "fn-53",
        "skill-bash",
        "base-ref-detection",
        "branch-match",
        "sed-exit-code",
        "make-pr-pattern",
        "codex-review"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05.md"
    },
    {
      "entry_id": "bug/build-errors/skill-adding-version-bump-leaves-stale-2026-06-05",
      "title": "Skill-adding version bump leaves stale skill/command counts in JSON manifest des",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/.claude-plugin/plugin.json, .claude-plugin/marketplace.json, plugins/flow-next/.codex-plugin/plugin.json",
      "tags": [
        "fn-53",
        "version-bump",
        "bump.sh",
        "skill-count",
        "manifest",
        "marketplace",
        "codex-mirror",
        "docs-drift",
        "release"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/skill-adding-version-bump-leaves-stale-2026-06-05.md"
    },
    {
      "entry_id": "bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26",
      "title": "Skill bash `set -- $ARGUMENTS` can't honor 'verbatim' passthrough",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-map/workflow.md",
      "tags": [
        "fn-50",
        "skill-bash",
        "argument-parsing",
        "set-minus-f",
        "codex-review",
        "passthrough",
        "clawpatch-wrap"
      ],
      "date": "2026-05-26",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26.md"
    },
    {
      "entry_id": "bug/build-errors/skill-flag-gating-a-durable-write-needs-2026-08-31",
      "title": "Skill flag gating a durable write needs exact-token parse, not substring",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-capture/SKILL.md",
      "tags": [
        "fn-214",
        "skill-bash",
        "argument-parsing",
        "capture",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-08-31",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/skill-flag-gating-a-durable-write-needs-2026-08-31.md"
    },
    {
      "entry_id": "bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11",
      "title": "Skill workflow snippets must enforce what the prose mandates (vars, gates, dispa",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "fn-60",
        "land",
        "skill-authoring",
        "codex-review",
        "safety-gates",
        "review-feedback"
      ],
      "date": "2026-06-11",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11.md"
    },
    {
      "entry_id": "bug/build-errors/status-policy-map-needs-a-matching-2026-06-18",
      "title": "Status-policy map needs a matching reconcile-loop branch per rung (map \u2260 write)",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md",
      "tags": [
        "fn-66",
        "tracker-sync",
        "status",
        "reconcile",
        "who-wins",
        "in-review",
        "merge-evidence",
        "rp-review"
      ],
      "date": "2026-06-18",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/status-policy-map-needs-a-matching-2026-06-18.md"
    },
    {
      "entry_id": "bug/build-errors/template-rewrite-env-var-cascade-2026-05-09",
      "title": "Env-var cascade in templates + canonical config.env knob alignment",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-ralph-init/templates, config.env, ralph.sh",
      "tags": [
        "template",
        "ralph",
        "config-env",
        "env-var-cascade",
        "review-feedback"
      ],
      "date": "2026-05-09",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/template-rewrite-env-var-cascade-2026-05-09.md"
    },
    {
      "entry_id": "bug/build-errors/unit-rename-substitution-broke-trigger-2026-07-18",
      "title": "Unit-rename substitution broke trigger thresholds (turns->rounds, fn-100)",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-interview/references/doc-aware.md",
      "tags": [
        "interview",
        "rounds",
        "doc-aware",
        "thresholds",
        "spec-contract",
        "impl-review",
        "fn-100"
      ],
      "date": "2026-07-18",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/unit-rename-substitution-broke-trigger-2026-07-18.md"
    },
    {
      "entry_id": "bug/build-errors/verdict-tasks-must-rewrite-not-banner-a-2026-07-03",
      "title": "Verdict tasks must rewrite, not banner, a sibling task's flipped scope",
      "track": "bug",
      "category": "build-errors",
      "module": ".flow/tasks",
      "tags": [
        "fn-83",
        "plan-sync-gate",
        "task-marking",
        "verdict",
        "workflow"
      ],
      "date": "2026-07-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/verdict-tasks-must-rewrite-not-banner-a-2026-07-03.md"
    },
    {
      "entry_id": "bug/test-failures/archaeology-fn-strip-can-over-strip-a-2026-07-02",
      "title": "Archaeology fn-strip can over-strip a test-pinned canonical breadcrumb",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/steps.md",
      "tags": [
        "fn-82",
        "archaeology",
        "fn-strip",
        "sync-codex",
        "mirror",
        "test-pinned",
        "allowlist",
        "final-gate"
      ],
      "date": "2026-07-02",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/archaeology-fn-strip-can-over-strip-a-2026-07-02.md"
    },
    {
      "entry_id": "bug/test-failures/final-gate-grep-for-a-forbidden-token-2026-07-02",
      "title": "Final-gate grep for a forbidden token hits the prohibition prose that bans it",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/skills/flow-next-impl-review",
      "tags": [
        "acceptance-gates",
        "grep",
        "spec-authoring",
        "fn-81",
        "review-feedback",
        "rp-slices"
      ],
      "date": "2026-07-02",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/final-gate-grep-for-a-forbidden-token-2026-07-02.md"
    },
    {
      "entry_id": "bug/test-failures/flag-substring-assertion-passes-when-a-2026-09-23",
      "title": "Flag substring assertion passes when a longer sibling flag is present",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/tests/test_spec_id_routing_prose.py",
      "tags": [
        "prose-test",
        "cli-flags",
        "false-green"
      ],
      "date": "2026-09-23",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/flag-substring-assertion-passes-when-a-2026-09-23.md"
    },
    {
      "entry_id": "bug/test-failures/rename-smoke-rewire-variable-form-cli-2026-05-09",
      "title": "Smoke discipline: variable-form CLI, hermetic env, line-level guard scope",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/scripts",
      "tags": [
        "smoke",
        "env-hermeticity",
        "variable-form-cli",
        "line-level-guard",
        "review-feedback"
      ],
      "date": "2026-05-09",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/rename-smoke-rewire-variable-form-cli-2026-05-09.md"
    },
    {
      "entry_id": "bug/test-failures/test-asserted-a-public-envelope-that-2026-08-01",
      "title": "Test asserted a public envelope that never carried the field",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/tests/test_chart_briefing.py",
      "tags": [
        "chart",
        "test-design",
        "review-feedback",
        "api-surface",
        "scope"
      ],
      "date": "2026-08-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/test-asserted-a-public-envelope-that-2026-08-01.md"
    },
    {
      "entry_id": "bug/test-failures/test-fixtures-must-mirror-upstream-zod-2026-05-26",
      "title": "Test fixtures must mirror upstream Zod enum, not concept",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/tests/fixtures/clawpatch-map, plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-50",
        "clawpatch",
        "zod-schema",
        "fixture-drift",
        "confidence-enum",
        "codex-review",
        "duck-typing"
      ],
      "date": "2026-05-26",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/test-fixtures-must-mirror-upstream-zod-2026-05-26.md"
    },
    {
      "entry_id": "bug/test-failures/test-production-path-not-parallel-construction-2026-05-21",
      "title": "Test the production path, not a parallel construction",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/tests, plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "testing",
        "production-form",
        "mock-patch",
        "argparse-two-token",
        "routing-table",
        "dual-emit",
        "review-feedback"
      ],
      "date": "2026-05-21",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/test-production-path-not-parallel-construction-2026-05-21.md"
    },
    {
      "entry_id": "bug/test-failures/test-runner-timeout-must-kill-a-process-2026-08-04",
      "title": "Test-runner timeout must kill a process TREE whose identity outlives the shard",
      "track": "bug",
      "category": "test-failures",
      "module": "scripts/run_tests_parallel.py",
      "tags": [
        "windows",
        "subprocess",
        "process-group",
        "job-object",
        "timeout",
        "ci",
        "test-runner"
      ],
      "date": "2026-08-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/test-runner-timeout-must-kill-a-process-2026-08-04.md"
    },
    {
      "entry_id": "bug/test-failures/two-independent-resolve-calls-faked-a-2026-08-04",
      "title": "Two independent resolve() calls faked a path escape on Windows",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/scripts/flowctl_tracker/lifecycle/helpers.py",
      "tags": [
        "windows",
        "flake",
        "path-safety",
        "tracker",
        "concurrency"
      ],
      "date": "2026-08-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/two-independent-resolve-calls-faked-a-2026-08-04.md"
    },
    {
      "entry_id": "bug/test-failures/windows-83-path-test-failures-were-2026-08-04",
      "title": "Windows '8.3 path' test failures were cp1252 fixtures + unguarded geteuid",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/tests/test_normalize_section_content.py",
      "tags": [
        "fn-120",
        "windows",
        "encoding",
        "cp1252",
        "utf-8",
        "8.3-short-path",
        "geteuid",
        "skipif",
        "json-stdout"
      ],
      "date": "2026-08-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/windows-83-path-test-failures-were-2026-08-04.md"
    },
    {
      "entry_id": "bug/runtime-errors/bash-deadline-watchdogs-orphaned-sleep-2026-07-16",
      "title": "Bash deadline watchdogs: orphaned sleep holds pipes; group-kill via setsid, not ",
      "track": "bug",
      "category": "runtime-errors",
      "module": "agent_docs/guidance-eval/runner.sh",
      "tags": [
        "bash",
        "timeout",
        "process-group",
        "setsid",
        "watchdog",
        "eval-harness",
        "fn-99"
      ],
      "date": "2026-07-16",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/bash-deadline-watchdogs-orphaned-sleep-2026-07-16.md"
    },
    {
      "entry_id": "bug/runtime-errors/empty-value-semantics-leak-null-in-2026-07-20",
      "title": "Empty-value semantics leak: {} -> null in snapshot config reads; empty file -> T",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "config-snapshot",
        "empty-values",
        "truthiness",
        "fn-110"
      ],
      "date": "2026-07-20",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/empty-value-semantics-leak-null-in-2026-07-20.md"
    },
    {
      "entry_id": "bug/runtime-errors/flowctl-on-disk-per-key-counter-count-2026-06-27",
      "title": "flowctl on-disk per-key counter: count by stored key + lock + coerce sort",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-68",
        "pilot-log",
        "tick-counter",
        "race-condition",
        "flock",
        "rp-review",
        "review-feedback",
        "fn-102",
        "gate-diet",
        "path-normalization",
        "fail-open",
        "codex-review"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/flowctl-on-disk-per-key-counter-count-2026-06-27.md"
    },
    {
      "entry_id": "bug/runtime-errors/forced-color-git-grep-output-defeats-2026-07-19",
      "title": "Forced-color git grep output defeats regex post-filter (SGR escapes)",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "git",
        "subprocess",
        "regex",
        "export",
        "ansi"
      ],
      "date": "2026-07-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/forced-color-git-grep-output-defeats-2026-07-19.md"
    },
    {
      "entry_id": "bug/runtime-errors/glob-walk-file-loads-need-lstat-screen-2026-07-19",
      "title": "Glob-walk file loads need lstat screen + RecursionError; revalidate TTL post-sta",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "gate",
        "green-receipt",
        "fail-closed",
        "fifo",
        "json"
      ],
      "date": "2026-07-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/glob-walk-file-loads-need-lstat-screen-2026-07-19.md"
    },
    {
      "entry_id": "bug/runtime-errors/land-chain-fences-a-failed-read-is-2026-09-13",
      "title": "Land chain fences: a failed read is never permission; write multi-layer records ",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "fn-149",
        "land",
        "chains",
        "stacks",
        "cascade",
        "skill-prose",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-09-13",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/land-chain-fences-a-failed-read-is-2026-09-13.md"
    },
    {
      "entry_id": "bug/runtime-errors/one-shot-keyed-to-an-earlier-captured-2026-08-19",
      "title": "One-shot keyed to an earlier-captured SHA: re-validate after the claim, release ",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "fn-200",
        "land",
        "one-shot",
        "concurrency",
        "claim-dir",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-08-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/one-shot-keyed-to-an-earlier-captured-2026-08-19.md"
    },
    {
      "entry_id": "bug/runtime-errors/same-owner-alias-re-registration-must-2026-08-02",
      "title": "Same-owner alias re-registration must harden a weak claim, not no-op",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "chart",
        "aliases",
        "two-pass-validation",
        "flowctl"
      ],
      "date": "2026-08-02",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/same-owner-alias-re-registration-must-2026-08-02.md"
    },
    {
      "entry_id": "bug/runtime-errors/skill-fences-that-degrade-only-without-2026-09-13",
      "title": "Skill fences that degrade only without set -e: masked failures in make-pr chain ",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/skills/flow-next-make-pr/create-and-finalize.md",
      "tags": [
        "set-e",
        "bash-fence",
        "fixtures",
        "make-pr",
        "chain",
        "stack"
      ],
      "date": "2026-09-13",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/skill-fences-that-degrade-only-without-2026-09-13.md"
    },
    {
      "entry_id": "bug/runtime-errors/structured-review-parsers-must-2026-07-30",
      "title": "Structured review parsers must distinguish invalid from absent",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-136",
        "review-findings",
        "fail-closed",
        "parser",
        "impl-review"
      ],
      "date": "2026-07-30",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/structured-review-parsers-must-2026-07-30.md"
    },
    {
      "entry_id": "bug/runtime-errors/who-wins-ladder-must-check-the-2026-06-03",
      "title": "Who-wins ladder must check the collision case before single-field rules",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md",
      "tags": [
        "fn-52",
        "tracker-sync",
        "who-wins",
        "status",
        "deadlock",
        "conflictTiebreak",
        "ordering",
        "impl-review"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/who-wins-ladder-must-check-the-2026-06-03.md"
    },
    {
      "entry_id": "bug/performance/linear-graphql-every-nodes-connection-2026-06-03",
      "title": "Linear GraphQL: every {nodes} connection needs first: \u2014 incl. workflowStates/tea",
      "track": "bug",
      "category": "performance",
      "module": "plugins/flow-next/scripts/flowctl_tracker/wire/linear.py",
      "tags": [
        "fn-52",
        "tracker-sync",
        "linear",
        "graphql",
        "rate-limit",
        "complexity",
        "connection",
        "first",
        "impl-review"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/performance/linear-graphql-every-nodes-connection-2026-06-03.md"
    },
    {
      "entry_id": "bug/security/guard-matcher-narrowing-missed-shell-2026-09-25",
      "title": "Guard matcher narrowing missed shell control words and split redirect words",
      "track": "bug",
      "category": "security",
      "module": "plugins/flow-next/scripts/hooks/ralph-guard.py",
      "tags": [
        "ralph-guard",
        "shell-parsing",
        "bypass"
      ],
      "date": "2026-09-25",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/security/guard-matcher-narrowing-missed-shell-2026-09-25.md"
    },
    {
      "entry_id": "bug/security/managed-review-transport-must-bound-2026-09-08",
      "title": "Managed review transport must bound time and protect scoped credentials",
      "track": "bug",
      "category": "security",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "managed-review",
        "transport",
        "credentials"
      ],
      "date": "2026-09-08",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/security/managed-review-transport-must-bound-2026-09-08.md"
    },
    {
      "entry_id": "bug/security/rollback-path-sanitizer-must-not-2026-06-05",
      "title": "Rollback path-sanitizer must not trim/rewrite bytes; guard git clean against emp",
      "track": "bug",
      "category": "security",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-55",
        "codex-delegation",
        "rollback",
        "git-clean",
        "path-sanitization",
        "review-feedback"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/security/rollback-path-sanitizer-must-not-2026-06-05.md"
    },
    {
      "entry_id": "bug/security/shell-command-allowlist-gates-must-2026-06-05",
      "title": "Shell-command allowlist gates must tokenize argv, not substring-match",
      "track": "bug",
      "category": "security",
      "module": "plugins/flow-next/scripts/hooks/ralph-guard.py",
      "tags": [
        "fn-55",
        "ralph-guard",
        "codex-delegation",
        "shlex",
        "allowlist",
        "bypass",
        "security",
        "review-feedback"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/security/shell-command-allowlist-gates-must-2026-06-05.md"
    },
    {
      "entry_id": "bug/integration/adding-a-review-backend-sweep-all-2026-06-29",
      "title": "Adding a review backend: sweep ALL enumeration sites (config table, stage list, ",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/docs, plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "review-backend",
        "enumeration-drift",
        "docs-sweep",
        "cursor",
        "fn-74",
        "claude",
        "fn-221"
      ],
      "date": "2026-06-29",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/adding-a-review-backend-sweep-all-2026-06-29.md"
    },
    {
      "entry_id": "bug/integration/backend-special-case-in-a-shared-helper-2026-09-05",
      "title": "Backend special-case in a shared helper is an enumeration site too",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "review-backend",
        "claude",
        "enumeration-sweep",
        "fn-221",
        "tracker-manifest"
      ],
      "date": "2026-09-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/backend-special-case-in-a-shared-helper-2026-09-05.md"
    },
    {
      "entry_id": "bug/integration/byte-for-byte-spec-contract-branch-2026-07-01",
      "title": "Byte-for-byte spec contract: branch prose into variants, don't annotate shared l",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-plan-review/SKILL.md",
      "tags": [
        "fn-78",
        "skill-prose",
        "review-feedback",
        "rp-eligibility",
        "byte-for-byte"
      ],
      "date": "2026-07-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/byte-for-byte-spec-contract-branch-2026-07-01.md"
    },
    {
      "entry_id": "bug/integration/caller-facade-guards-must-cover-retro-2026-07-29",
      "title": "Caller facade guards must cover retro-fire paths",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-capture/workflow.md",
      "tags": [
        "fn-141",
        "tracker-sync",
        "facade",
        "retro-fire",
        "oracle"
      ],
      "date": "2026-07-29",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/caller-facade-guards-must-cover-retro-2026-07-29.md"
    },
    {
      "entry_id": "bug/integration/caller-fakes-must-enforce-lifecycle-2026-07-29",
      "title": "Caller fakes must enforce lifecycle facade input contracts",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/tests/test_tracker_caller_execution.py",
      "tags": [
        "fn-141",
        "tracker-sync",
        "caller-harness",
        "facade",
        "impl-review"
      ],
      "date": "2026-07-29",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/caller-fakes-must-enforce-lifecycle-2026-07-29.md"
    },
    {
      "entry_id": "bug/integration/caller-oracle-must-preserve-historical-2026-07-29",
      "title": "Caller oracle must preserve historical quirks and exact observations",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/tests/test_tracker_caller_oracle.py",
      "tags": [
        "fn-141",
        "tracker-sync",
        "oracle",
        "impl-review"
      ],
      "date": "2026-07-29",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/caller-oracle-must-preserve-historical-2026-07-29.md"
    },
    {
      "entry_id": "bug/integration/ceremony-validation-must-read-persisted-2026-06-28",
      "title": "Ceremony validation must read PERSISTED config, not re-race env; don't collapse ",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/steps.md",
      "tags": [
        "tracker-sync",
        "jira",
        "fn-70",
        "discovery-ceremony",
        "readyState",
        "persisted-config",
        "authScheme",
        "rp-review"
      ],
      "date": "2026-06-28",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/ceremony-validation-must-read-persisted-2026-06-28.md"
    },
    {
      "entry_id": "bug/integration/ci-path-classification-must-include-2026-09-05",
      "title": "CI path classification must include rename sources",
      "track": "bug",
      "category": "integration",
      "module": "scripts/ci/classify_changes.py",
      "tags": [
        "ci",
        "git",
        "renames",
        "path-classification"
      ],
      "date": "2026-09-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/ci-path-classification-must-include-2026-09-05.md"
    },
    {
      "entry_id": "bug/integration/claude-p-clean-room-on-oauth-logins-2026-07-16",
      "title": "claude -p clean-room on OAuth logins: --setting-sources project,local; --bare an",
      "track": "bug",
      "category": "integration",
      "module": "agent_docs/guidance-eval/runner.sh",
      "tags": [
        "claude-cli",
        "clean-room",
        "eval-harness",
        "oauth",
        "setting-sources",
        "bare",
        "fn-99"
      ],
      "date": "2026-07-16",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/claude-p-clean-room-on-oauth-logins-2026-07-16.md"
    },
    {
      "entry_id": "bug/integration/cross-family-review-claims-key-on-the-2026-09-05",
      "title": "Cross-family review claims key on the writer's model family, never the host name",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/docs",
      "tags": [
        "review-backend",
        "claude",
        "cross-family",
        "docs",
        "fn-221"
      ],
      "date": "2026-09-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/cross-family-review-claims-key-on-the-2026-09-05.md"
    },
    {
      "entry_id": "bug/integration/drop-receipt-to-break-codex-2026-05-09",
      "title": "Drop receipt to break codex confabulation in long review fix loops",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "review",
        "codex",
        "confabulation",
        "receipt",
        "fn-43"
      ],
      "date": "2026-05-09",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/drop-receipt-to-break-codex-2026-05-09.md"
    },
    {
      "entry_id": "bug/integration/forwarded-license-carried-the-wrong-2026-09-14",
      "title": "Forwarded license carried the wrong holder's commit contract into the bridged ch",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/agents/worker.md",
      "tags": [
        "fn-245",
        "bridge",
        "worker",
        "phase-1b",
        "license",
        "dispatch-field",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-09-14",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/forwarded-license-carried-the-wrong-2026-09-14.md"
    },
    {
      "entry_id": "bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17",
      "title": "gh api -f stringifies numeric body fields (issue_id) \u2192 GitHub 422; use -F",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/scripts/flowctl_tracker/",
      "tags": [
        "fn-64",
        "tracker-sync",
        "github",
        "gh-api",
        "rest",
        "422",
        "issue-dependencies"
      ],
      "date": "2026-06-17",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17.md"
    },
    {
      "entry_id": "bug/integration/head-bound-html-artifacts-must-not-2026-07-30",
      "title": "Head-bound HTML artifacts must not stale their own input",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-make-pr/html-lens.md",
      "tags": [
        "fn-136",
        "make-pr",
        "html",
        "currentness",
        "semantic-carrier",
        "impl-review"
      ],
      "date": "2026-07-30",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/head-bound-html-artifacts-must-not-2026-07-30.md"
    },
    {
      "entry_id": "bug/integration/headless-review-backend-error-envelope-2026-09-05",
      "title": "Headless review backend: error-envelope text must never ride the output slot",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "review-backend",
        "claude",
        "transport",
        "verdict-channel",
        "fn-221"
      ],
      "date": "2026-09-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/headless-review-backend-error-envelope-2026-09-05.md"
    },
    {
      "entry_id": "bug/integration/heredoc-built-json-breaks-on-free-form-2026-06-05",
      "title": "Heredoc-built JSON breaks on free-form interpolated values",
      "track": "bug",
      "category": "integration",
      "module": "skills/flow-next-qa/workflow.md",
      "tags": [
        "json",
        "shell",
        "receipt",
        "escaping",
        "skill-authoring"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/heredoc-built-json-breaks-on-free-form-2026-06-05.md"
    },
    {
      "entry_id": "bug/integration/installer-must-own-what-it-deletes-2026-08-21",
      "title": "",
      "track": "bug",
      "category": "integration",
      "module": "scripts/install-codex.sh, scripts/sync-codex.sh",
      "tags": [
        "installer",
        "ownership",
        "namespace",
        "data-loss",
        "codex",
        "mirror"
      ],
      "date": "2026-08-21",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/installer-must-own-what-it-deletes-2026-08-21.md"
    },
    {
      "entry_id": "bug/integration/land-evidence-field-defaulted-to-off-on-2026-08-19",
      "title": "land evidence field defaulted to 'off' on configured-but-not-due paths",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "land",
        "evidence",
        "report-vocabulary"
      ],
      "date": "2026-08-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/land-evidence-field-defaulted-to-off-on-2026-08-19.md"
    },
    {
      "entry_id": "bug/integration/markerstruct-field-semantics-must-2026-06-27",
      "title": "Marker/struct-field semantics must update the PRODUCER adapter contract, not jus",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md",
      "tags": [
        "fn-68",
        "tracker-sync",
        "adapter-interface",
        "marker",
        "comments-sync",
        "listComments",
        "question-valve",
        "nine-method",
        "cross-model-review",
        "fn-141",
        "facade",
        "comments",
        "prose-teardown"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/markerstruct-field-semantics-must-2026-06-27.md"
    },
    {
      "entry_id": "bug/integration/path-handoff-template-id-slots-must-use-2026-07-19",
      "title": "Path-handoff template id slots must use canonical ids, not aliases",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-work/references/codex-delegation.md",
      "tags": [
        "fn-103",
        "codex-delegation",
        "path-handoff",
        "alias-resolution",
        "prose-contract",
        "review-feedback"
      ],
      "date": "2026-07-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/path-handoff-template-id-slots-must-use-2026-07-19.md"
    },
    {
      "entry_id": "bug/integration/plan-review-criteria-edits-must-also-2026-09-14",
      "title": "Plan-review criteria edits must also sweep workflow-rp.md (CE summary + Classic ",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md",
      "tags": [
        "plan-review",
        "repoprompt",
        "prompt-pins",
        "codex-review"
      ],
      "date": "2026-09-14",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/plan-review-criteria-edits-must-also-2026-09-14.md"
    },
    {
      "entry_id": "bug/integration/rp-builder-file-slices-cause-false-2026-06-10",
      "title": "RP builder file slices cause false-positive 'missing docs' review findings",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-impl-review",
      "tags": [
        "rp",
        "impl-review",
        "builder-slices",
        "false-positive",
        "select-get",
        "review-feedback"
      ],
      "date": "2026-06-10",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/rp-builder-file-slices-cause-false-2026-06-10.md"
    },
    {
      "entry_id": "bug/integration/scheduler-prose-asserted-wrong-config-2026-08-22",
      "title": "Scheduler prose asserted wrong config default; slot-hold drain rules deadlock",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-work-rolling/references/rolling-scheduler.md",
      "tags": [
        "fn-203",
        "work-rolling",
        "planSync",
        "config-defaults",
        "deadlock",
        "skill-prose"
      ],
      "date": "2026-08-22",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/scheduler-prose-asserted-wrong-config-2026-08-22.md"
    },
    {
      "entry_id": "bug/integration/set-tracker-id-rejected-github-n-2026-06-03",
      "title": "set-tracker-id rejected GitHub #N identifiers (Linear-only handle validator)",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-52",
        "tracker-sync",
        "github",
        "identifier",
        "validator",
        "smoke-test"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/set-tracker-id-rejected-github-n-2026-06-03.md"
    },
    {
      "entry_id": "bug/integration/skill-bash-blocks-re-declare-every-2026-07-02",
      "title": "Skill bash blocks: re-declare EVERY literal path per block (vars die across tool",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills",
      "tags": [
        "path-persistence",
        "skill-authoring",
        "rp-review",
        "fn-81"
      ],
      "date": "2026-07-02",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/skill-bash-blocks-re-declare-every-2026-07-02.md"
    },
    {
      "entry_id": "bug/integration/skill-fence-consolidation-6-contract-2026-07-20",
      "title": "Skill-fence consolidation: 6 contract regressions (var-atomicity, symlink, dry-r",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills",
      "tags": [
        "skill-prose",
        "fences",
        "dry-run",
        "symlink-safety",
        "fn-110"
      ],
      "date": "2026-07-20",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/skill-fence-consolidation-6-contract-2026-07-20.md"
    },
    {
      "entry_id": "bug/integration/spec-named-config-keys-must-be-checked-2026-07-15",
      "title": "Spec-named config keys must be checked against shipped surface; cross-family is",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-setup/workflow.md",
      "tags": [
        "fn-97",
        "config-contract",
        "spec-amendment",
        "cross-family-review",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-07-15",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/spec-named-config-keys-must-be-checked-2026-07-15.md"
    },
    {
      "entry_id": "bug/integration/summary-sinks-for-repeatable-mixed-2026-07-19",
      "title": "Summary sinks for repeatable mixed-outcome events need per-event lines, not one ",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-work/phases.md",
      "tags": [
        "prose-contract",
        "summary-template",
        "gate-diet",
        "fn-102",
        "review-finding"
      ],
      "date": "2026-07-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/summary-sinks-for-repeatable-mixed-2026-07-19.md"
    },
    {
      "entry_id": "bug/integration/tracker-ownership-rewrites-require-2026-07-29",
      "title": "Tracker ownership rewrites require adjacent fidelity sweeps",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/docs/tracker-sync.md",
      "tags": [
        "fn-141",
        "tracker-sync",
        "docs-contract",
        "provider-fidelity",
        "impl-review"
      ],
      "date": "2026-07-29",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/tracker-ownership-rewrites-require-2026-07-29.md"
    },
    {
      "entry_id": "bug/integration/trackers-auto-linkify-issue-key-2026-06-03",
      "title": "Trackers auto-linkify issue-key substrings inside markers (even in HTML comments",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md",
      "tags": [
        "fn-52",
        "tracker-sync",
        "linear",
        "marker",
        "dedup",
        "linkify",
        "smoke-test"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/trackers-auto-linkify-issue-key-2026-06-03.md"
    },
    {
      "entry_id": "bug/data/adding-a-key-to-a-content-hash-orphans-2026-08-01",
      "title": "Adding a key to a content hash orphans records the old binary wrote",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fingerprint",
        "idempotence",
        "upgrade-compat",
        "golden-fixture",
        "chart"
      ],
      "date": "2026-08-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/adding-a-key-to-a-content-hash-orphans-2026-08-01.md"
    },
    {
      "entry_id": "bug/data/docs-for-a-hash-identity-fix-inherit-2026-08-01",
      "title": "Docs for a hash-identity fix inherit the hash's precision",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/docs/flowctl.md",
      "tags": [
        "chart",
        "fingerprint",
        "changelog",
        "docs-pin",
        "review-feedback"
      ],
      "date": "2026-08-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/docs-for-a-hash-identity-fix-inherit-2026-08-01.md"
    },
    {
      "entry_id": "bug/data/fence-preserving-writer-needs-fence-2026-07-02",
      "title": "Fence-preserving writer needs fence-aware readers/validators (write/read parity)",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-79",
        "task-sections",
        "fenced-code",
        "markdown-parsing",
        "cursor-review"
      ],
      "date": "2026-07-02",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/fence-preserving-writer-needs-fence-2026-07-02.md"
    },
    {
      "entry_id": "bug/data/migrationrollback-cli-10-review-cycle-2026-05-08",
      "title": "Migration/rollback CLI: 10 review-cycle pitfalls (fn-43.3)",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-43",
        "migration",
        "rollback",
        "lockfile",
        "sentinel",
        "atomic-write",
        "crash-recovery",
        "cross-platform",
        "review-feedback"
      ],
      "date": "2026-05-08",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/migrationrollback-cli-10-review-cycle-2026-05-08.md"
    },
    {
      "entry_id": "bug/data/paired-snapshot-setter-must-write-both-2026-06-03",
      "title": "Paired-snapshot setter must write both halves atomically (merge base)",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-52",
        "tracker-sync",
        "merge-base",
        "3-way-merge",
        "invariant",
        "setter",
        "impl-review"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/paired-snapshot-setter-must-write-both-2026-06-03.md"
    },
    {
      "entry_id": "bug/data/relaxing-a-validator-must-only-admit-2026-09-26",
      "title": "Relaxing a validator must only admit values the writer round-trips",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-257",
        "memory",
        "frontmatter",
        "validation",
        "round-trip"
      ],
      "date": "2026-09-26",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/relaxing-a-validator-must-only-admit-2026-09-26.md"
    },
    {
      "entry_id": "bug/data/yaml-frontmatter-writer-unescaped-2026-07-24",
      "title": "YAML frontmatter writer: unescaped newlines lose the entry; frontmatter-only wri",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "memory",
        "yaml",
        "frontmatter",
        "round-trip"
      ],
      "date": "2026-07-24",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/yaml-frontmatter-writer-unescaped-2026-07-24.md"
    },
    {
      "entry_id": "bug/ui/flow-nextdev-docs-page-needs-2026-06-03",
      "title": "flow-next.dev docs page needs registering in BOTH astro sidebar + site.ts navGro",
      "track": "bug",
      "category": "ui",
      "module": "src/lib/site.ts",
      "tags": [
        "flow-next.dev",
        "docs-site",
        "starlight",
        "navigation",
        "navGroups",
        "DocsRail",
        "fn-52"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/ui/flow-nextdev-docs-page-needs-2026-06-03.md"
    },
    {
      "entry_id": "knowledge/conventions/unattended-detection-uses-the-full-2026-09-26",
      "title": "Unattended detection uses the full autonomy marker namespace",
      "track": "knowledge",
      "category": "conventions",
      "module": "skills",
      "tags": [
        "autonomy",
        "mode:autonomous",
        "tracker-sync",
        "flow-auto",
        "defer"
      ],
      "date": "2026-09-26",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/conventions/unattended-detection-uses-the-full-2026-09-26.md"
    },
    {
      "entry_id": "knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30",
      "title": "Audit sync-codex.sh during planning for Codex mirror impact",
      "track": "knowledge",
      "category": "workflow",
      "module": "planning",
      "tags": [
        "sync-codex",
        "codex",
        "planning",
        "mirror",
        "validation",
        "subagents",
        "tool-rewrites",
        "openai-yaml"
      ],
      "date": "2026-04-30",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30.md"
    },
    {
      "entry_id": "knowledge/workflow/final-integration-tasks-need-wider-impl-2026-05-26",
      "title": "Final-integration tasks need wider impl-review base",
      "track": "knowledge",
      "category": "workflow",
      "module": "review",
      "tags": [
        "fn-50",
        "impl-review",
        "review-scope",
        "final-task",
        "multi-task-spec",
        "base-commit",
        "merge-base",
        "codex"
      ],
      "date": "2026-05-26",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/final-integration-tasks-need-wider-impl-2026-05-26.md"
    },
    {
      "entry_id": "knowledge/workflow/github-rulesets-need-an-admin-bypass-or-2026-09-11",
      "title": "GitHub rulesets need an admin bypass or spec-only commits stall",
      "track": "knowledge",
      "category": "workflow",
      "module": "ci",
      "tags": [
        "github",
        "rulesets",
        "ci",
        "flow-state"
      ],
      "date": "2026-09-11",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/github-rulesets-need-an-admin-bypass-or-2026-09-11.md"
    },
    {
      "entry_id": "knowledge/workflow/harness-capability-claims-verify-at-the-2026-08-28",
      "title": "Harness capability claims: verify at the installer, not the generator",
      "track": "knowledge",
      "category": "workflow",
      "module": "platforms",
      "tags": [
        "scouts",
        "opencode",
        "installers",
        "negative-claims"
      ],
      "date": "2026-08-28",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/harness-capability-claims-verify-at-the-2026-08-28.md"
    },
    {
      "entry_id": "knowledge/workflow/pr-bot-review-loops-do-not-converge-2026-08-04",
      "title": "",
      "track": "knowledge",
      "category": "workflow",
      "module": "review-subsystem",
      "tags": [
        "bot-review",
        "land",
        "convergence",
        "triage",
        "severity-inflation"
      ],
      "date": "2026-08-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/pr-bot-review-loops-do-not-converge-2026-08-04.md"
    },
    {
      "entry_id": "knowledge/workflow/split-pr-at-second-adjacent-surface-finding-2026-08-21",
      "title": "",
      "track": "knowledge",
      "category": "workflow",
      "module": "review",
      "tags": [
        "resolve-pr",
        "land",
        "scope",
        "review-rounds",
        "pr-hygiene"
      ],
      "date": "2026-08-21",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/split-pr-at-second-adjacent-surface-finding-2026-08-21.md"
    },
    {
      "entry_id": "knowledge/workflow/stacked-pr-squash-close-recovery-2026-08-27",
      "title": "Squash-merging a stacked PR's base permanently closes the stacked PR - rebase + successor PR is the recovery",
      "track": "knowledge",
      "category": "workflow",
      "module": "land",
      "tags": [
        "stacked-prs",
        "squash-merge",
        "land",
        "gh",
        "rebase",
        "delete-branch",
        "github-behavior"
      ],
      "date": "2026-08-27",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/stacked-pr-squash-close-recovery-2026-08-27.md"
    },
    {
      "entry_id": "knowledge/best-practices/failures-after-a-restart-suspect-2026-08-28",
      "title": "Failures after a restart: suspect persistent state before code",
      "track": "knowledge",
      "category": "best-practices",
      "module": ".flow",
      "tags": [
        "fn-208",
        "debugging",
        "persistent-state",
        "state-validation"
      ],
      "date": "2026-08-28",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/best-practices/failures-after-a-restart-suspect-2026-08-28.md"
    },
    {
      "entry_id": "knowledge/best-practices/scb-benchmark-proof-fn-163164-2026-08-04",
      "title": "SCB benchmark proof: fn-163/164 eliminated ceremony as a cost factor",
      "track": "knowledge",
      "category": "best-practices",
      "module": "",
      "tags": [
        "fn-163",
        "fn-164",
        "fn-165",
        "slopcodebench",
        "benchmark"
      ],
      "date": "2026-08-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/best-practices/scb-benchmark-proof-fn-163164-2026-08-04.md"
    },
    {
      "entry_id": "knowledge/best-practices/windows-path-shims-cannot-observe-2026-08-11",
      "title": "Windows PATH shims cannot observe subprocess spawns (CreateProcess skips PATHEXT",
      "track": "knowledge",
      "category": "best-practices",
      "module": "plugins/flow-next/tests",
      "tags": [
        "windows",
        "ci",
        "subprocess",
        "spawn-count",
        "git-shim"
      ],
      "date": "2026-08-11",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/best-practices/windows-path-shims-cannot-observe-2026-08-11.md"
    },
    {
      "entry_id": "knowledge/decisions/bugbot-pre-push-stage-wont-do-patch-id-2026-08-07",
      "title": "Bugbot pre-push stage: won't-do - patch-ID dedup falsified live",
      "track": "knowledge",
      "category": "decisions",
      "module": "review",
      "tags": [
        "bugbot",
        "cursor",
        "review-backends"
      ],
      "date": "2026-08-07",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/bugbot-pre-push-stage-wont-do-patch-id-2026-08-07.md"
    },
    {
      "entry_id": "knowledge/decisions/composed-brief-deleted-path-handoff-2026-07-19",
      "title": "Composed brief deleted: path-handoff replaces it (fn-103 eval)",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/skills/flow-next-work/references/codex-delegation.md",
      "tags": [
        "fn-103",
        "codex-delegation",
        "path-handoff",
        "eval",
        "delegation",
        "bitter-lesson"
      ],
      "date": "2026-07-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/composed-brief-deleted-path-handoff-2026-07-19.md"
    },
    {
      "entry_id": "knowledge/decisions/factory-droid-platform-status-2026-05-2026-05-25",
      "title": "Factory Droid platform status \u2014 2026-05",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/docs/platforms.md",
      "tags": [
        "droid",
        "factory-ai",
        "cross-platform",
        "fn-48",
        "interop",
        "plugin-root",
        "hooks",
        "Execute"
      ],
      "date": "2026-05-25",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/factory-droid-platform-status-2026-05-2026-05-25.md"
    },
    {
      "entry_id": "knowledge/decisions/pilot-strike-recovery-is-a-cli-verb-not-2026-08-11",
      "title": "Pilot strike recovery is a CLI verb, not board-native transition detection",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/skills/flow-next-pilot",
      "tags": [
        "pilot",
        "strikes",
        "tracker-sync",
        "readyState",
        "fn-184"
      ],
      "date": "2026-08-11",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/pilot-strike-recovery-is-a-cli-verb-not-2026-08-11.md"
    },
    {
      "entry_id": "knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03",
      "title": "A deterministic plan-sync skip-gate is not viable \u2014 do not re-attempt",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/skills/flow-next-work/phases.md",
      "tags": [
        "plan-sync",
        "work-loop",
        "gate",
        "eval",
        "fn-83",
        "drift",
        "determinism",
        "shelved"
      ],
      "date": "2026-07-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03.md"
    },
    {
      "entry_id": "knowledge/decisions/ralph-guard-reverts-its-delegation-2026-08-14",
      "title": "Ralph guard reverts its delegation amendment; bridge safety is prose-only",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/scripts/hooks/ralph-guard.py",
      "tags": [
        "flow-98",
        "ralph-guard",
        "codex-delegation",
        "safety",
        "deprecation"
      ],
      "date": "2026-08-14",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/ralph-guard-reverts-its-delegation-2026-08-14.md"
    },
    {
      "entry_id": "knowledge/decisions/review-stall-detection-reads-resolution-2026-08-05",
      "title": "Review stall detection reads resolution; the trend heuristics are deleted (fn-168)",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-168",
        "fn-159",
        "review-convergence",
        "stall-detection",
        "ratchet-prompt",
        "findings-lineage",
        "inference-vs-evidence"
      ],
      "date": "2026-08-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/review-stall-detection-reads-resolution-2026-08-05.md"
    },
    {
      "entry_id": "knowledge/decisions/tracked-vs-runtime-durability-contract-2026-08-14",
      "title": "Tracked-vs-runtime durability contract - done crosses it, validate respects it",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "durability",
        "flow-state",
        "status-source",
        "validate",
        "fn-192"
      ],
      "date": "2026-08-14",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/tracked-vs-runtime-durability-contract-2026-08-14.md"
    },
    {
      "entry_id": "knowledge/decisions/tracker-sync-is-projection-not-2026-06-01",
      "title": "Tracker sync is projection, not coordination (Linear-first)",
      "track": "knowledge",
      "category": "decisions",
      "module": "strategy",
      "tags": [
        "strategy-override",
        "tracker-sync",
        "linear"
      ],
      "date": "2026-06-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/tracker-sync-is-projection-not-2026-06-01.md"
    }
  ],
  "legacy": [],
  "count": 118,
  "status": "active"
}

===== [11/11] dependencies: ids, titles, statuses, done summaries =====
- fn-81-skill-runtime-token-plumbing-single.1 [todo] - Single-emission spec writes: capture + interview (early proof point)
    Converted capture (Phase 4→5) and interview (all three Write-Refined-Spec branches) to the single-emission write pattern: draft body Written ONCE via the Write tool to a literal unique path (render = read-back), Edit-tool revisions with a mandatory full-file Read before each re-approval, flowctl consumes `spec set-plan/set-acceptance/set-spec --file <literal path>` — the `$SPEC_BODY` heredoc re-emission and fixed `/tmp/spec.md`/`/tmp/acc.md`/`/tmp/desc.md` paths are gone. Capture's tracker gate reads `tracker.perEvent.capture` once (LEAF pattern); interview's duplicate spec fetch collapsed onto the Detect-Input-Type read. Canonical files only; local sync-codex.sh validation run passed (mirror regen deferred to fn-81.4). RP impl-review: SHIP (first pass).

