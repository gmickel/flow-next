# Worker anchor bundle — fn-81-skill-runtime-token-plumbing-single.2 (spec fn-81-skill-runtime-token-plumbing-single)

Verbatim outputs of the worker Phase-1 re-anchor reads, fixed order, no filtering or truncation. The bundle is a floor, not a ceiling — memory keyword-search and every further read remain available.

===== [1/11] task_show: `flowctl show fn-81-skill-runtime-token-plumbing-single.2 --json` =====
{
  "success": true,
  "assignee": "gordon.mickel@gmail.com",
  "claim_note": "",
  "claimed_at": "2026-07-02T07:19:56.676730Z",
  "created_at": "2026-07-02T06:33:46.735888Z",
  "depends_on": [
    "fn-81-skill-runtime-token-plumbing-single.1"
  ],
  "id": "fn-81-skill-runtime-token-plumbing-single.2",
  "priority": null,
  "spec": "fn-81-skill-runtime-token-plumbing-single",
  "spec_path": ".flow/tasks/fn-81-skill-runtime-token-plumbing-single.2.md",
  "status": "done",
  "title": "Review-backend plumbing: RP file composition, single-entry responses, fix-loop cap + staging guards",
  "updated_at": "2026-07-02T08:08:39.668186Z",
  "evidence": {
    "commits": [
      "76a8a161f0e1",
      "23797981045b26a0d6ded979dae472d0dc48305a"
    ],
    "prs": [],
    "tests": [
      "uv run --with pytest python3 -m pytest plugins/flow-next/tests/ -q (1393 passed, 2 skipped, 164 subtests \u2014 run pre- and post-fix)",
      "bash scripts/sync-codex.sh x2 (idempotent, validators green; mirror regenerated locally, restored, NOT committed \u2014 fn-81.4 owns regen)",
      "grep -rn '\\[PASTE' plugins/flow-next/skills/ \u2192 empty",
      "grep sweep /tmp/review-prompt.md|/tmp/re-review.md|/tmp/updated-plan.md|/tmp/export-prompt.md|/tmp/completion-review-prompt.md in canonical skills \u2192 zero hits",
      "live snapshot-staging pipeline test in scratch git repo (modified/untracked/deleted/renamed staged; pre-dirty + pre-untracked excluded)",
      "RP impl-review verdict: SHIP (1 fix round; R8/R9/R10/R11/R13 all met, Unaddressed R-IDs: [])"
    ]
  },
  "impl": null,
  "review": null,
  "sync": null,
  "epic": "fn-81-skill-runtime-token-plumbing-single"
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
  "status": "open",
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
  "updated_at": "2026-07-02T09:21:53.369178Z",
  "tasks": [
    {
      "id": "fn-81-skill-runtime-token-plumbing-single.1",
      "title": "Single-emission spec writes: capture + interview (early proof point)",
      "status": "done",
      "priority": null,
      "depends_on": []
    },
    {
      "id": "fn-81-skill-runtime-token-plumbing-single.2",
      "title": "Review-backend plumbing: RP file composition, single-entry responses, fix-loop cap + staging guards",
      "status": "done",
      "priority": null,
      "depends_on": [
        "fn-81-skill-runtime-token-plumbing-single.1"
      ]
    },
    {
      "id": "fn-81-skill-runtime-token-plumbing-single.3",
      "title": "Round-trip eliminations: plan, deps, make-pr, tracker-sync, config-get sweep, prime prose",
      "status": "done",
      "priority": null,
      "depends_on": [
        "fn-81-skill-runtime-token-plumbing-single.1"
      ]
    },
    {
      "id": "fn-81-skill-runtime-token-plumbing-single.4",
      "title": "Final gate: mirror parity, smoke + pytest, CHANGELOG Unreleased, optimization-log",
      "status": "done",
      "priority": null,
      "depends_on": [
        "fn-81-skill-runtime-token-plumbing-single.1",
        "fn-81-skill-runtime-token-plumbing-single.2",
        "fn-81-skill-runtime-token-plumbing-single.3"
      ]
    }
  ],
  "ready": false
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
On branch fn-83-work-loop-speed-conservative-plan-sync
You are in a sparse checkout with 100% of tracked files present.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   .flow/specs/fn-83-work-loop-speed-conservative-plan-sync.json
	modified:   .flow/specs/fn-83-work-loop-speed-conservative-plan-sync.md
	modified:   .flow/tasks/fn-83-work-loop-speed-conservative-plan-sync.4.json
	modified:   .flow/tasks/fn-83-work-loop-speed-conservative-plan-sync.4.md
	modified:   plugins/flow-next/scripts/flowctl.py

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	.flow/tasks/fn-83-work-loop-speed-conservative-plan-sync.6.json
	.flow/tasks/fn-83-work-loop-speed-conservative-plan-sync.6.md
	optimization/worker-anchor/
	plugins/flow-next/tests/test_anchor_bundle.py

no changes added to commit (use "git add" and/or "git commit -a")

===== [6/11] git_log: `git log -5 --oneline` =====
7d628564 chore(flow): close fn-83.2 — done summary + evidence
c0477c32 feat(eval): plan-sync gate corpus — frozen real-agent answer key + zero-false-skip CI check (fn-83.2)
43264e13 chore(flow): close fn-83.1 — done summary + evidence
5993c446 feat(flowctl): plan-sync-probe — fail-open drift lattice, planSync.gate config, gate ledger
23ab917d chore(flow): plan fn-83 (5 tasks, plan-review SHIP r3) + FLOW-29 link

===== [7/11] git_branch: `git rev-parse --abbrev-ref HEAD` =====
fn-83-work-loop-speed-conservative-plan-sync

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
      "path": "/Users/gordon/work/flow-next/GLOSSARY.md",
      "entries": [
        {
          "term": "Spec",
          "definition": "The central artefact of flow-next: a specification at `.flow/specs/<id>.md` (markdown body) plus `.flow/specs/<id>.json` (metadata sidecar, post-1.0). Reviewable on its own; cross-model-reviewed; verifiable against prior handovers; frozen at handover. Replaces the term *epic* from the 0.x line.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Ready",
          "definition": "A human-owned boolean on the spec record (default `false`, toggled via `flowctl spec ready` / `spec unready`) marking a spec complete enough to hand to an agent \u2014 the entry gate autonomous loops consume. Orthogonal to `status` (`open|done`): a ready spec stays `open` through planning and work. Human-owned or tracker-projected (`tracker.readyState` pulls the configured tracker state onto the local flag, one-way), never agent-inferred. Opt-in and invisible until adopted: the flag is written lazily, non-adopters see no badge, prompts, or warnings anywhere.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Task",
          "definition": "An execution unit under a spec, sized to fit one `/flow-next:work` iteration (~100k tokens fresh context). Tasks declare dependencies (`requires:`) and may declare which spec acceptance criteria they advance (`satisfies: [R1, R3]`). Implemented by a worker subagent with re-anchored context.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "R-ID",
          "definition": "A numbered acceptance criterion in a spec, format `**R1:** ...`, `**R2:** ...`. Renumber-forbidden after the first review cycle: deletions leave gaps, new criteria take the next unused number. R-IDs are the load-bearing identity of a requirement across the spec, the tasks that satisfy it, the commits that reference it, and the PR body coverage table.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Handover object",
          "definition": "A named, reviewable artefact that carries context across a step in the agentic SDLC. flow-next defines six handover states: the spec at business-layer completion (#1) and at full completion (#2) \u2014 both the **same** `.flow/specs/<spec-id>.md` file at successive layers, NOT two separate specs \u2014 then the implementation plan (#3), the working implementation (#4), the cross-model code review (#5), and the PR-as-cognitive-aid (#6). Each is reviewable on its own, cross-model-verified, and frozen at handover. The chain of handovers replaces the standups / refinement / design-review touchpoints that pre-agentic Agile relied on.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Re-anchoring",
          "definition": "Re-reading the spec, the task, and `git log` since branch base before each task starts. Counters context drift in long-running agent sessions per Anthropic guidance. Worker subagents re-anchor on every iteration; `/flow-next:work` re-anchors every loop turn.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Cross-model review",
          "definition": "A different model reviews the artefact produced by the first model. Applied at every handover. Backends: RepoPrompt (rp), Codex CLI (codex), GitHub Copilot CLI (copilot), Cursor `cursor-agent` CLI (cursor). The disagreement surface between writing model and reviewing model is where the gaps live.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Feature map",
          "definition": "The `.clawpatch/features/*.json` index produced by `clawpatch map` and consumed by flow-next scouts via `flowctl repo-map`. Semantic feature slices across ~20 languages/frameworks (Zod-validated upstream, `schemaVersion: 1`). Wrapped by the opt-in `/flow-next:map` skill; flow-next core (flowctl) never imports or requires clawpatch \u2014 when `.clawpatch/` is absent, scouts gracefully fall back to grep/glob.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "features_anchored",
          "definition": "Optional scout output field listing feature slices from the feature map that overlap the current scope. Emitted by `repo-scout` and `context-scout` when `.clawpatch/features/*.json` is present; omitted when absent. Each entry carries a `last_mapped` timestamp so downstream skills can flag staleness (informational signal, not a block).",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Receipt",
          "definition": "A JSON artefact that gates Ralph state transitions. `flowctl impl-review` writes a receipt at `.flow/review-receipts/<branch>.json` with verdict (`SHIP` / `NEEDS_WORK` / `MAJOR_RETHINK`), confidence anchors, introduced vs pre-existing finding counts, and the deferred / suppressed counts. Ralph reads receipts to decide loop progression.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Worker subagent",
          "definition": "A subagent dispatched by `/flow-next:work` to implement a single task with fresh context. Re-anchors the spec + task + git state, implements the task, records evidence (commits + tests + done summary), and exits. The fresh context per task is what enables N tasks to run in parallel without context-bleed.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Carmack-level review",
          "definition": "The strict cross-model review tier flow-next runs by default. References John Carmack review standard. Five confidence anchors (0/25/50/75/100) gate findings; `<75` suppressed except P0 @ 50+; introduced vs pre-existing classification means only introduced findings count toward the verdict.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Triage skip",
          "definition": "A deterministic whitelist pre-check that returns `SHIP` without invoking a review backend, for trivial diffs: lockfile-only / docs-only / release-chore / generated-file-only. `flowctl triage-skip` is the helper. On by default in Ralph mode; opt-out via `--no-triage` or `FLOW_RALPH_NO_TRIAGE=1`.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "PR-as-cognitive-aid",
          "definition": "A structured PR body synthesizing nine flow-next state streams (spec with R-IDs, per-task done summary + evidence commits, decisions / bug / architecture-patterns memory, glossary changes, strategy alignment, deferred review findings, the diff itself) into a reviewable artefact. Body sections: TL;DR, R-ID coverage table, Critical changes, Decisions, Memory, Glossary/strategy deltas, Open items, Where to look. Produced by `/flow-next:make-pr`.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Ralph",
          "definition": "The flow-next hardened autonomous harness. External shell loop drives fresh Claude / Codex sessions per task with cross-model review gates, hook-enforced guardrails (ralph-guard / DCG), and receipt-based proof-of-work. Consumes **fully planned** specs only \u2014 it iterates plan-review -> work -> impl-review -> spec-completion-review until the spec ships or the iteration cap is hit; it never runs the planning fan-out (planning stays with the human or pilot). Differentiator from `ralph-wiggum`-style open-loop autonomous agents. The default autonomy path is the pilot + land pipeline; reach for Ralph when a run outlasts a session or prose guardrails aren't enough \u2014 Ralph owns the loop in a shell script, pilot hands the loop to the host's `/loop` / `/goal` primitives.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Pilot",
          "definition": "The single-tick build-loop conductor (`/flow-next:pilot`): one tick advances one ready spec by one pipeline stage (plan / plan-review / work / `[optional qa]` / make-pr \u2014 see [QA stage](#qa-stage-pipelineqa)) and ends with a terminal `PILOT_VERDICT` line; the host's `/loop` or `/goal` owns iteration. Signals autonomy to sub-skills via the `mode:autonomous` token + `FLOW_AUTONOMOUS=1` env (distinct from `FLOW_RALPH`; never activates ralph-guard). Selection consumes the fn-58 `ready` gate; two healthy no-advance ticks clear the spec's `ready` flag (don't-thrash). The default `ready` mode selects only already-ready specs; the opt-in [backlog mode](#backlog-mode-pilotautonomy) widens it to the whole open backlog.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Backlog mode (`pilot.autonomy`)",
          "definition": "Pilot's opt-in wide-autonomy behavior (fn-68), gated by config `pilot.autonomy \u2208 {ready (default), backlog}` (per-run override `--backlog` / `--auto`; with the gate off, pilot is byte-for-byte unchanged and `references/backlog-mode.md` is never even read). A backlog tick **enumerates the full open set** \u2014 flow specs (`flowctl ready --all`) **plus** tracker issues at the promoted lane (`listOpenIssues`, unioned in by the skill) \u2014 selects the top **dep-ordered** actionable item, runs the [triage stage](#triage-stage-backlog-mode) in front of pilot's existing pipeline, and either advances it one stage (`plan \u2192 plan-review \u2192 work \u2192 [qa] \u2192 make-pr`) or parks it behind an [async question](#ask-stage--question-valve). It is a **leftward extension of the same single-tick conductor**, not a new skill or altitude: one `/loop`/`/goal` target, one verdict grammar, one mental model; the host primitive still owns repetition. The consent boundary moves from *before* the loop to *inside the loop, on block* \u2014 but the load-bearing boundaries hold: it **never authors a spec** (a thin/missing spec is surfaced as a \"run `/flow-next:capture` or `/flow-next:interview`\" gap, never auto-written), **never sets the `ready` flag** (promotion is the human's board act), and **never merges** (land stays human-gated). Readiness is the human's **explicit signal** (the fn-58 ready gate set OR tracker status exactly at `tracker.readyState`), never an agent-inferred completeness score \u2014 un-promoted backlog items are skipped silently.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Triage stage (backlog mode)",
          "definition": "The classify-and-route stage backlog mode runs **in front of** pilot's existing `classify`, on the selected item only. It reads the spec **agentically** (the host's judgment, never a flowctl-computed `triageClass`) and routes by *explicit state first*: **workable** (ready signal + complete spec) \u2192 select-and-advance (pilot's existing path); **ready-but-thin / ready-but-ambiguous** (signal present, spec missing or too thin to act on) \u2192 [`ask`](#ask-stage--question-valve) (kick back with the gap, never build, never auto-author); **dep-unsatisfied** \u2192 `BLOCKED <id> by <dep>` (a state-changing surface of the dep wait); **needs a human decision** \u2192 `ask`. A *live* triage always lands on a **state-changing terminal** (`ADVANCED` / `ASKED` / `BLOCKED` / `NEEDS_HUMAN`) so an item can never re-select forever; `TRIAGED <id> <class>` is **diagnostic / `--dry-run` only**. `needs-spec` is always a *promoted* item missing a workable spec \u2014 never an un-promoted idea, which is simply skipped.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Ask stage / question valve",
          "definition": "Backlog mode's **async human-in-the-loop valve** \u2014 \"stuck\" becomes a question, not a stall, and never an interactive `AskUserQuestion`. When it cannot safely proceed, the `ask` stage writes each Open Question behind a **stable anchor** `<!-- flow-next:question id=<hash> status=open -->` (`id` hashes **stable fields only** \u2014 `subjectId` + blocked-stage + reason code + question slug; the free-prose reason is *outside* the hash so rephrasing never duplicates) and surfaces it where the item lives: a **spec-backed** item parks via the spec's `## Open Questions` section **and** a projected tracker comment; a **tracker-only** item (no spec) parks in the tracker comment alone. Projection is transport-blind across GitHub / GitLab / Jira / Linear via tracker-sync's adapter; no transport \u21d2 spec-only (when a spec exists) + a one-line \"enable X to mirror\" note, never a block. Selection **skips any item carrying a `status=open` parked question**, so it is never re-picked. A human answer (flipping the spec anchor to `status=answered`, or a tracker reply carrying `<!-- flow-next:answer id=<hash> -->` matched by `id`) makes the next tick re-triage and proceed. Terminal verdict: `ASKED <id> (<n>)` \u2014 a durable park.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Decision log (`pilot-log`)",
          "definition": "The per-tick **factory-metrics substrate** backlog mode writes (fn-68) via `flowctl pilot-log append --id <id> --action <triaged|advanced|asked|blocked|needs-human> --stage <stage|-> [--cost-tokens <n>]`, summarized by `flowctl pilot-log summary --json` \u2192 `{tick, id, action, stage, costTokens}` rows. The action enum is **aligned to the verdict grammar**; token cost is **host-reported** (omitted/null when unavailable) \u2014 flowctl only stores the row, never measures cost. Rows yield the efficiency readout (% moved with no question / one async answer / parked, and cost per change) and are the substrate a future self-improvement-synthesis spec mines. Stored under `.flow/pilot-runs/` (a sync-runs-style dir, auto-gitignored) \u2014 deliberately **NOT** any `receipts/` path the ralph-guard validates.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Land",
          "definition": "The cadence-tick ship loop (`/flow-next:land`): one tick discovers the open PRs the build loop authored (spec `branch_name` match AND the make-pr breadcrumb \u2014 both signals required), walks each through the gate tree (CI tri-state over ALL checks, patience window anchored to the last push, resolve-pr convergence, `land.reviewSignal`), and takes at most one action class per PR \u2014 CI fix, resolve dispatch, mechanical rebase, or the gated explicit merge (`gh pr merge --squash --match-head-commit`, never `--auto`) plus the post-merge tail (spec close \u2192 tracker touchpoint \u2192 release-follow). The one confined exception to the no-auto-merge rule; `/loop`-shaped where pilot is `/goal`-shaped. Ends with a terminal `LAND_VERDICT` line.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "QA stage (`pipeline.qa`)",
          "definition": "The optional live-app QA pass `/flow-next:qa`, graduated into a config-gated pilot stage (`pipeline.qa`, default **off**). When on, pilot runs one live pass over the complete build at all-tasks-done \u2014 `plan -> plan-review -> work -> **qa** -> make-pr` \u2014 driving the app the dev already has running during `work`. **Evidence-aware** (subtracts only AC a deterministic re-runnable check already proved; always live-runs every runtime / UI / integration criterion because the worker's self-report is narration, not captured evidence), **surfaced not blocking** (routes on `qa_outcome`, NOT the Ralph-guard `verdict` projection \u2014 `SHIP`/`NA`/`BLOCKED` advance, `NEEDS_WORK` still advances to the **draft** PR with findings in a `## Live QA` section + the bug-memory track + a tracker comment), and **augments, never replaces** CI / staging / manual QA. Net-new is one config-key default plus additive `qa_verdict` receipt fields (`head_sha` / `rid_coverage` / `open_p0p1`) \u2014 no new flowctl subcommand, no persisted test-case artefact. Idempotent per branch head via the receipt's `head_sha`. See `skills/flow-next-qa/SKILL.md` (fn-72).",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Verdict",
          "definition": "The structured tick outcome a loop skill prints for transcript-blind drivers, always the last line of a tick. Pilot: `PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason=\"<one line>\"`; [backlog mode](#backlog-mode-pilotautonomy) **adds `ASKED <id> (<n>)`** (a durable park) and keeps every existing terminal verbatim (drivers grep `DEFERRED_TO_LAND` for the land hand-off, stop on `NO_WORK`); `TRIAGED <id> <class>` is diagnostic / `--dry-run` only, never a live terminal. Land: `LAND_VERDICT=<MERGED|RELEASED|FIXING_CI|AWAITING_REVIEW|RESOLVING|BLOCKED|NEEDS_HUMAN|NO_WORK> prs=<n> pr=<deciding-pr-url|-> reason=\"<one line>\"` (tick verdict = worst severity across PRs). Autonomous resolve-pr runs end with `RESOLVE_PR_VERDICT=<RESOLVED|PENDING|NEEDS_HUMAN> threads=<n> fixed=<n> needs_human=<n>`, which land gates on. Distinct from a review receipt (Ralph's file-based proof-of-work): a verdict lives in the conversation output because `/goal` validators read the transcript, never the filesystem.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Spec-as-PR",
          "definition": "A team workflow where the spec is opened as a draft PR for review BEFORE any code lands. Reviewing a 50-line spec is higher-leverage than reviewing a 500-line implementation. Once merged, the spec is frozen on main; implementation PRs reference the merged spec.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Frozen-at-handover",
          "definition": "The R-ID invariant. Once a spec has been reviewed once, R5 means the same thing forever. A reviewer reading R5 in a six-month-old commit, a new team member reading R5 in the spec, and `/flow-next:make-pr` emitting R5 coverage all refer to the same acceptance criterion. Renumber-forbidden after first review cycle.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "flow-swarm",
          "definition": "An in-progress companion product to flow-next that reads `.flow/specs/` directly to coordinate parallel agents across worktrees and consume `/flow-next:make-pr` output. The on-disk layout flow-swarm expects is what fn-43 (epic->spec rename) produces. Reference target for the v1.0 migration carrot.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Tracker",
          "definition": "An external issue tracker (Linear, GitHub Issues, GitLab, or Jira) that flow-next *projects* a spec to via `/flow-next:tracker-sync`. The tracker is a **co-editable mirror** \u2014 body, status, and comments sync two-way \u2014 but it is **projection, not coordination**: the `.flow/specs/<id>.md` spec stays the source of truth and the quality layer, and the tracker never drives flow state or spawns agents. Distinct from `/flow-next:sync` (plan-sync). Contrast OpenAI Symphony, where the tracker *is* the control plane.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "merge-base snapshot",
          "definition": "The common-ancestor body the tracker-sync 3-way merge compares against \u2014 a **paired** snapshot taken at the last sync point: both a flow-form body and a tracker-form body, plus content hashes (the echo fence). Stored in the spec-JSON `tracker` block (`mergeBaseFlow` / `mergeBaseTracker` / `baseHashFlow` / `baseHashTracker`) and written atomically as a unit (a one-sided update is rejected, so neither half pins to a stale sync point). Advances with `lastSyncedAt` on a real reconcile, never on a no-op echo.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "discovery ceremony",
          "definition": "The detect \u2192 surface \u2192 ask \u2192 never-assume flow `/flow-next:tracker-sync` runs before enabling the bridge. It probes six signals (Linear MCP, `LINEAR_API_KEY`, GitHub auth, GitLab auth/`GITLAB_TOKEN`, Jira REST + token \u2014 `JIRA_BASE_URL` plus Cloud `JIRA_EMAIL`+`JIRA_API_TOKEN` or DC/Server `JIRA_PAT`), surfaces what is present *and* absent, asks the user, and writes `tracker.*` config **only on confirmation**, with provenance. No signal \u21d2 nothing written; the bridge stays off. Resolution model is env > config > ask (mirrors `flowctl review-backend`).",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "tracker-key handle",
          "definition": "A tracker identifier (e.g. `WOR-17`) used as a **resolvable flow id**, the hybrid id model. **Tracker-first** specs are canonically `wor-17-slug` (tasks `wor-17-slug.M`); bare `wor-17` / `wor-17.M` resolve as aliases. **Flow-first** specs keep `fn-NN-slug` and store `WOR-17` in `tracker.identifier` as a resolvable display alias. Resolution is case-insensitive (`show wor-17`, `work wor-17` resolve); the native `fn-` scheme is reserved (`fn-N` allocation counts `fn-*` only); one tracker team per repo; **ids never rename** on link.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "dependency projection",
          "definition": "Tracker-sync's projection of a spec's local `depends_on_epics` edges into **tracker issue relations** (fn-64) \u2014 a `depends_on_epics` edge between two linked specs becomes a **blocked-by** relation between their issues (Linear native relations / GitHub native dependencies / GitLab native `is_blocked_by` issue links / Jira native \"is blocked by\" issue links \u2014 directional and universally available, no licence gate, no `flow:deps` block \u2014 else, for GitHub's reduced rung and GitLab on every tier, a provenance-fenced `<!-- flow:deps -->` body block). The relations counterpart to body/status/comments sync: projection, not coordination \u2014 flow stays authoritative, the tracker never declares deps back. Runs through the transport-blind `projectDepRelations` hook + the normalized `setIssueRelation` / `listIssueRelations` adapter pair; idempotent via read-before-write. No transitive/graph expansion \u2014 only direct edges project.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "provenance ledger",
          "definition": "The per-spec `depRelations` list (in the `.flow/specs/<id>.json` `tracker` block, atomic write) that records **which** dependency relations tracker-sync created \u2014 so projection is idempotent and removals are provably-ours-only. Each entry is `{key, dep_spec, from_tracker_id, to_tracker_id, type, source, updatedAt}`, where `key` is an opaque hash of the directed issue pair (never a raw issue key inline \u2014 trackers auto-linkify keys even inside HTML comments). A relation **not** in the ledger (native trackers) / **outside** the `<!-- flow:deps -->` fenced block (GitHub's fenced fallback; GitLab's block on every tier) is never removed: a human's manual relation is safe by construction. Mirrors the merge-base hash-provenance shape, minus its paired-snapshot constraint.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "completed-blocker rule",
          "definition": "The tracker-sync semantics for a dependency whose **local** dep spec is `done` (\u2192 its issue Done/Closed): the projected blocked-by relation stays **visible** on the tracker (preserving the real historical ordering on the board) but does **NOT** feed back into Flow `ready=true` gating \u2014 readiness already treats done deps as satisfied, and dependency projection must not regress that. Keys off the *local* dep-spec status (flow is authoritative), never a remote fetch.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "render lens",
          "definition": "A regenerable human-review artifact (HTML) derived from a markdown source of truth; never the storage format, always re-derivable. flow-next ships two: the spec artifact and the PR artifact, both living at fixed deterministic paths under `.flow/artifacts/<spec-id>/` (never timestamped \u2014 Lavish keys annotation sessions on the absolute path). Every lens is self-contained single-file HTML (inline CSS/JS, zero external requests), carries a staleness stamp in its footer, and is never parsed back as state \u2014 regeneration always overwrites the same file.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "HTML artifact mode",
          "definition": "The opt-in feature (2.0.0+) that makes participating skills (capture, plan, make-pr) emit render lenses alongside their markdown output. Activated via `flowctl config set artifacts.html.enabled true` (OFF by default, offered once by `/flow-next:setup`); when active, skills load the shared disclosure reference at `plugins/flow-next/references/html-artifacts.md` \u2014 the single carrier of all generation rules and the anti-slop design contract. With the mode off, skills load nothing extra: zero token cost, zero behavior change. Markdown and tracker-sync remain the sole source of truth.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "spec artifact",
          "definition": "The spec's render lens at `.flow/artifacts/<spec-id>/spec.html`. ONE generation pathway with state-dependent rendering: spec-only view before tasks exist (capture workflow \u00a75.10 \u2014 the business-review surface) and the added plan layer (task dependency DAG with critical path, R-ID \u2192 task coverage matrix) once tasks exist (plan Step 8.5 \u2014 after the refinement loop exits). Links back from the spec markdown via the idempotent `<!-- flow-next:artifact-link -->` marker line (replaced in place, repo-relative target). The only artifact that enters the Lavish annotate loop.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "PR artifact",
          "definition": "The PR's render lens at `.flow/artifacts/<spec-id>/pr.html`, emitted by `/flow-next:make-pr` Phase 1.5. A **read-only review instrument**: diff-derived (never from commit messages), verified against the spec's R-ID export before publishing \u2014 mismatches render as visibly flagged rows, warn-in-artifact, never blocking. Committed narrowly (`chore(flow): pr artifact <spec-id>`, artifact file only) so the PR body's SHA-pinned blob link resolves; never enters the annotate loop \u2014 review conversation belongs to the code host.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Lavish (lavish-axi)",
          "definition": "An optional detect-on-PATH companion (npm: `lavish-axi`) for annotating spec artifacts in the browser \u2014 never wrapped, bundled, or required (same shape as clawpatch/`/flow-next:map`). Feedback is pull-only and session-spanning: annotations queue in the global `~/.lavish-axi/state.json` (not per-workspace), survive agent death, and any later agent session drains them via the `lavish-axi poll` CLI, mapping each annotation to a markdown-source edit followed by lens regeneration. Sessions key on the absolute artifact path (different worktrees = separate sessions); the local server idle-stops after ~30 min and `lavish-axi <file>` resumes it \u2014 absence or idle-stop is invisible because the artifact is a self-contained static page. Autonomous contexts never open a session and never poll.",
          "avoid": [],
          "relates_to": []
        }
      ],
      "count": 38
    }
  ],
  "file_count": 1,
  "total_terms": 38
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/backlog-select-must-not-drop-a-dep-2026-06-27.md"
    },
    {
      "entry_id": "bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05",
      "title": "Codex mirror audit must verify R2 block lands before a COMPLETE sentence, not ju",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-qa/references/qa-discipline.md",
      "tags": [
        "sync-codex",
        "codex",
        "mirror",
        "fn-53",
        "AskUserQuestion",
        "plain-text-numbered-prompt",
        "mid-sentence-injection",
        "multi-line-ask",
        "tool-rewrites",
        "audit",
        "review-feedback"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/codex-mirror-smoke-docs-miss-composed-2026-05-18.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/docs-activation-command-for-string-enum-2026-06-05.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/env-marker-gate-must-scan-the-namespace-2026-06-04.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/fn-44-review-cycle-lessons-2026-05-21.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/id-grammar-widening-must-cover-the-full-2026-06-03.md"
    },
    {
      "entry_id": "bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12",
      "title": "Lavish interactive-only gate must check MODE var AND env markers in-snippet",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-capture/workflow.md",
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11.md"
    },
    {
      "entry_id": "bug/build-errors/optional-side-effect-snippets-need-2026-06-12",
      "title": "Optional side-effect snippets need guarded git steps; check-ignore the exact fil",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-make-pr/workflow.md",
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/optional-side-effect-snippets-need-2026-06-12.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/policy-claim-inversion-sweep-all-2026-06-18.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/r2-ask-block-mis-injected-into-negation-2026-06-27.md"
    },
    {
      "entry_id": "bug/build-errors/r2-ask-block-must-never-anchor-in-2026-06-10",
      "title": "R2 ask-block must never anchor in autonomous hard-error prose; mode-rename sweep",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-make-pr/workflow.md",
      "tags": [
        "fn-59",
        "sync-codex",
        "codex-mirror",
        "R2-injection",
        "is_negative_context",
        "autonomous",
        "FLOW_AUTONOMOUS",
        "make-pr",
        "review-feedback"
      ],
      "date": "2026-06-10",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/r2-ask-block-must-never-anchor-in-2026-06-10.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/skill-adding-version-bump-leaves-stale-2026-06-05.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26.md"
    },
    {
      "entry_id": "bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10",
      "title": "Skill prose must match real flowctl surfaces (fields, status enums, subcommands)",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-pilot/workflow.md",
      "tags": [
        "fn-59",
        "pilot",
        "skill-authoring",
        "flowctl-json",
        "task-status",
        "rp-review",
        "fn-68",
        "backlog-mode",
        "safety-gates",
        "dry-run",
        "review-feedback",
        "fn-82",
        "skill-prose",
        "dedupe",
        "progressive-disclosure"
      ],
      "date": "2026-06-10",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/status-policy-map-needs-a-matching-2026-06-18.md"
    },
    {
      "entry_id": "bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18",
      "title": "sync-codex.sh tool-substitution needs prose surgery + context-aware injection",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh",
      "tags": [
        "sync-codex",
        "codex",
        "mirror",
        "fn-45",
        "AskUserQuestion",
        "tool-rewrites",
        "injection",
        "markdown-tables",
        "fenced-code-blocks",
        "fn-50",
        "FLOWCTL",
        "prelude",
        "agents",
        "scouts",
        "symmetry-gap",
        "R2-injection",
        "is_negative_context",
        "fn-55",
        "plain-text-numbered-prompt",
        "reference-doc"
      ],
      "date": "2026-05-18",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/template-rewrite-env-var-cascade-2026-05-09.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/test-failures/archaeology-fn-strip-can-over-strip-a-2026-07-02.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/test-failures/final-gate-grep-for-a-forbidden-token-2026-07-02.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/test-failures/rename-smoke-rewire-variable-form-cli-2026-05-09.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/test-failures/test-fixtures-must-mirror-upstream-zod-2026-05-26.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/test-failures/test-production-path-not-parallel-construction-2026-05-21.md"
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
        "review-feedback"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/runtime-errors/flowctl-on-disk-per-key-counter-count-2026-06-27.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/runtime-errors/who-wins-ladder-must-check-the-2026-06-03.md"
    },
    {
      "entry_id": "bug/performance/linear-graphql-every-nodes-connection-2026-06-03",
      "title": "Linear GraphQL: every {nodes} connection needs first: \u2014 incl. workflowStates/tea",
      "track": "bug",
      "category": "performance",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/linear-graphql.md",
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/performance/linear-graphql-every-nodes-connection-2026-06-03.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/security/rollback-path-sanitizer-must-not-2026-06-05.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/security/shell-command-allowlist-gates-must-2026-06-05.md"
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
        "fn-74"
      ],
      "date": "2026-06-29",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/adding-a-review-backend-sweep-all-2026-06-29.md"
    },
    {
      "entry_id": "bug/integration/adding-a-tracker-to-tracker-sync-sweep-2026-06-28",
      "title": "Adding a tracker to tracker-sync: sweep WHOLE tree + read adapter ref for dep-pr",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync",
      "tags": [
        "tracker-sync",
        "gitlab",
        "fn-69",
        "doc-sweep",
        "flow:deps",
        "dependency-projection",
        "impl-review",
        "jira",
        "fn-70",
        "per-adapter-fidelity",
        "adapter-ref-crosscheck"
      ],
      "date": "2026-06-28",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/adding-a-tracker-to-tracker-sync-sweep-2026-06-28.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/byte-for-byte-spec-contract-branch-2026-07-01.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/ceremony-validation-must-read-persisted-2026-06-28.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/drop-receipt-to-break-codex-2026-05-09.md"
    },
    {
      "entry_id": "bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17",
      "title": "gh api -f stringifies numeric body fields (issue_id) \u2192 GitHub 422; use -F",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/github.md",
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/heredoc-built-json-breaks-on-free-form-2026-06-05.md"
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
        "cross-model-review"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/markerstruct-field-semantics-must-2026-06-27.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/rp-builder-file-slices-cause-false-2026-06-10.md"
    },
    {
      "entry_id": "bug/integration/set-tracker-id-rejected-github-n-2026-06-03",
      "title": "set-tracker-id rejected GitHub",
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/set-tracker-id-rejected-github-n-2026-06-03.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/skill-bash-blocks-re-declare-every-2026-07-02.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/trackers-auto-linkify-issue-key-2026-06-03.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/data/fence-preserving-writer-needs-fence-2026-07-02.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/data/migrationrollback-cli-10-review-cycle-2026-05-08.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/data/paired-snapshot-setter-must-write-both-2026-06-03.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/ui/flow-nextdev-docs-page-needs-2026-06-03.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/knowledge/workflow/final-integration-tasks-need-wider-impl-2026-05-26.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/knowledge/decisions/factory-droid-platform-status-2026-05-2026-05-25.md"
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
      "path": "/Users/gordon/work/flow-next/.flow/memory/knowledge/decisions/tracker-sync-is-projection-not-2026-06-01.md"
    }
  ],
  "legacy": [],
  "count": 55,
  "status": "active"
}

===== [11/11] dependencies: ids, titles, statuses, done summaries =====
- fn-81-skill-runtime-token-plumbing-single.1 [done] — Single-emission spec writes: capture + interview (early proof point)
    Converted capture (Phase 4→5) and interview (all three Write-Refined-Spec branches) to the single-emission write pattern: draft body Written ONCE via the Write tool to a literal unique path (render = read-back), Edit-tool revisions with a mandatory full-file Read before each re-approval, flowctl consumes `spec set-plan/set-acceptance/set-spec --file <literal path>` — the `$SPEC_BODY` heredoc re-emission and fixed `/tmp/spec.md`/`/tmp/acc.md`/`/tmp/desc.md` paths are gone. Capture's tracker gate reads `tracker.perEvent.capture` once (LEAF pattern); interview's duplicate spec fetch collapsed onto the Detect-Input-Type read. Canonical files only; local sync-codex.sh validation run passed (mirror regen deferred to fn-81.4). RP impl-review: SHIP (first pass).

