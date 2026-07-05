---
satisfies: [R1, R2, R4, R6, R7, R9, R10, R11, R12]
---

# make-pr/capture/interview/plan/resolve-pr/qa touchpoints + joins + event-tag fixes

## Description

Size: M
Files:
- `plugins/flow-next/skills/flow-next-make-pr/create-and-finalize.md` (§5.6 dispatch + §5.7 join)
- `plugins/flow-next/skills/flow-next-capture/workflow.md` (5.7 dispatch + Phase 6 join)
- `plugins/flow-next/skills/flow-next-interview/SKILL.md` (tracker-sync block + event tag)
- `plugins/flow-next/skills/flow-next-plan/steps.md` (Step 6.5 + event tag)
- `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md` (Phase 9.5 + event tag)
- `plugins/flow-next/skills/flow-next-qa/workflow.md` (A.3 explicit dispatch + event tag)
- Regenerate `plugins/flow-next/codex/`

Rewire the remaining six lifecycle touchpoints to the `tracker-runner`, add the make-pr §5.7 + capture Phase 6 pre-audit joins, and fix the four missing/placeholder `event:` tags (R9) that today's audit can't clear.

## Approach

1. **make-pr §5.6 (state-shaped, awaited — R2).** In `create-and-finalize.md` §5.6 (:527-583, dispatch at :542-545) change the inline `skill: flow-next-tracker-sync (operation: reconcile <spec-id>, event: makePr)` to an AWAITED `Task flow-next:tracker-runner` (`operation: reconcile <spec-id>`, `event: makePr`, `DISPATCH: forked`). Keep ALL the fn-66 `reconcile`-not-`push` doctrine + per-tracker branching comments verbatim (they document the op, which is unchanged). Do NOT touch §4.6a (:240-267) — that is inline flowctl body-ref probing, NOT a fork candidate.
2. **make-pr §5.7 join (R4).** In §5.7 (:587-609, check at :596) add a pre-check step: await the outstanding makePr dispatch for `$SPEC_ID` before `sync check`. Retro-fire-once + summary slot unchanged. Preserve the `PR_URL=<url>` sole-stdout invariant (Ralph → stderr). Add the IDENTICAL compaction fallthrough note as work Phase 5 (.2 Step 5): on compaction/resume with unknown handles, fall through to `sync check` semantics — receipts on disk are the truth, not the ledger.
3. **capture 5.7 + Phase 6 join (R2, R4).** In `capture/workflow.md` 5.7 (:788-805, dispatch at :798) change to an AWAITED runner dispatch (`operation: <leaf> <SPEC_ID>`, `event: capture`, `DISPATCH: forked`). In Phase 6 (:855-882, check at :871) await the outstanding dispatch before `sync check`, and add the IDENTICAL compaction fallthrough note as work Phase 5 (.2 Step 5): on compaction/resume with unknown handles, fall through to `sync check` semantics — receipts on disk are the truth, not the ledger. Capture is Ralph-blocked/interactive — the host-side ask-after-join (R6) applies on genuine conflict.
4. **interview (state-shaped, awaited — R2) + event tag (R9).** In `interview/SKILL.md` (:462-479, dispatch at :472) change to an AWAITED runner dispatch AND add the missing `event: interview` tag: `operation: <leaf> <spec-id>, event: interview, DISPATCH: forked`.
5. **plan (state-shaped, awaited — R2) + event tag (R9).** In `plan/steps.md` Step 6.5 (:531-548, dispatch at :541) change to an AWAITED runner dispatch AND add the missing `event: plan` tag.
6. **resolve-pr Phase 9.5 (isolated-but-awaited — R1, R10) + event tag (R9).** In `resolve-pr/workflow.md` Phase 9.5 (:437-455, dispatch at :449) change to an isolated-but-AWAITED runner dispatch AND add the missing `event: resolvePr` tag: `operation: comment <spec-id>, event: resolvePr, DISPATCH: forked`. No end-of-run check exists here (verified) → awaited, not fire-and-forget.
7. **qa A.3 (isolated-but-awaited — R1, R10) + explicit block + event tag (R9).** In `qa/workflow.md` A.3 (:590-604, `:` placeholder at :602) REPLACE the bare `:` placeholder with an EXPLICIT dispatch block: an isolated-but-AWAITED `Task flow-next:tracker-runner` (`operation: comment <spec-id>, event: qa, DISPATCH: forked`). Keep the "comment is the only sensible verb" doctrine. No end-of-run check exists → awaited.
8. **inline hatch (R5 consumer) + timeout (R12).** Each gate honors `tracker.dispatch` (inline restores today's behavior byte-identical); document the 10-min await bound → errored-on-timeout at each awaited site. Reference the .1 capability gate + leaf; do not re-derive.
9. Regenerate the Codex mirror; confirm rewrites + guard + mirror-parity test pass. The `Task flow-next:tracker-runner` tokens introduced across these six skills are covered by the GLOBAL sync-codex sweep landed in .1 — add NO new per-file rewrite rule; just regenerate + verify the guard/mirror-parity are green.

## Investigation targets

Required:
- `plugins/flow-next/skills/flow-next-make-pr/create-and-finalize.md:527-609` (§5.6 dispatch + §5.7 join; §4.6a is OUT of scope)
- `plugins/flow-next/skills/flow-next-capture/workflow.md:788-805` + `:855-882`
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:462-479`; `plugins/flow-next/skills/flow-next-plan/steps.md:531-548`
- `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md:437-455`; `plugins/flow-next/skills/flow-next-qa/workflow.md:590-604`
- `plugins/flow-next/agents/tracker-runner.md` (the .1 contract)

Optional:
- `plugins/flow-next/skills/flow-next-tracker-sync/steps.md:11-15` (the `comment` op + event-tag contract the dispatches rely on)

## Key context

- Only make-pr and capture have end-of-run `sync check` sites among these six → only they get pre-audit joins (R4). resolve-pr, qa, interview, plan have NO check (verified) — resolve-pr/qa are comment-shaped so they run isolated-but-awaited; interview/plan are state-shaped so awaited anyway.
- make-pr §5.6 uses `reconcile` (not `push`) deliberately (fn-66 — body-preserving 3-way merge). The op is UNCHANGED; only its execution site moves to the runner. Keep every `reconcile`-vs-`push` comment.
- The four `event:` tag fixes (R9) are tiny but load-bearing: without them the end-of-run audit can never clear those events (untagged receipt never clears a lifecycle event — steps.md:15). qa's `:` placeholder violates the "explicit blocks, never `:` placeholders" memory constraint — make it explicit.
- capture is Ralph-blocked (interactive only); interview/plan/make-pr/resolve-pr/qa can run autonomous — the DISPATCH: forked queue gate (from .1) covers both.
- Regenerating the mirror is required; do NOT bump version.

## Acceptance

- [ ] make-pr §5.6 is an AWAITED runner dispatch (reconcile, event: makePr); §4.6a untouched; §5.7 awaits before `sync check` with the compaction fallthrough note; `PR_URL=` stdout invariant preserved.
- [ ] capture 5.7 is an AWAITED runner dispatch (event: capture); Phase 6 awaits before `sync check` with the compaction fallthrough note.
- [ ] interview + plan are AWAITED runner dispatches AND now carry `event: interview` / `event: plan`.
- [ ] resolve-pr 9.5 is an isolated-but-AWAITED runner dispatch carrying `event: resolvePr`.
- [ ] qa A.3's `:` placeholder is replaced with an EXPLICIT isolated-but-AWAITED runner dispatch carrying `event: qa`.
- [ ] Every rewritten gate honors `tracker.dispatch inline` (byte-identical inline fallback); 10-min await bound documented per site.
- [ ] Codex mirror regenerated; `Task flow-next:` guard + `test_tracker_sync_mirror_parity.py` green; `uvx pytest plugins/flow-next/tests -q` green.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
