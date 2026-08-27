# Issue sweep: skipped review status, land tail, export roster, OpenCode closers

## Conversation Evidence

> user (turn 1): "check out all new issues on github and verify their validity and if they match our strategy, capture a spec with any that we should fix/implement, then plan that spec with opus 5 medium and review it gpt 5.6 sol medium"

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 60% [user], 40% [paraphrase] -->

Triage of every currently open GitHub issue on this repo (2026-08-26). The ask is to keep only reports that are valid in current source and that fit STRATEGY.md, then lock those into one spec so they can be planned and reviewed.

Eight open issues existed. Four are in scope here (verified, strategy-aligned, no existing spec). Four are parked: already tracked, complementary to an open spec, or a larger design than this sweep.

**In scope (verified):**

- **#371** — A 3g policy skip leaves `completion_review_status` as `unknown`. Every gate treats that as “nobody looked”: the merge-evidence projection refuses `--to done`, `flowctl next --require-completion-review` re-queues the excused review, pilot re-routes the spec to `work` every tick (a livelock this planning pass found), the Ralph completion gate never terminates, and audits cannot tell excused from unreviewed. The skip itself is correct; only the persisted value is missing.
- **#367** — Land’s post-merge tail `git add`s an auto-ignored receipt directory in the same `&&` as the spec sidecar. The add fails, the sync-state commit never lands, and the sidecar is left staged or unstaged depending on whether the receipt dir exists.
- **#366** — Work and work-rolling accept `--review=export`, then dispatch impl-review, which has no export workflow that can emit SHIP. The run dead-ends.
- **#364** — OpenCode closers print `/flow-next:<name>` while that host’s invocable form is flat `/flow-next-<name>`. The user cannot run what the closer prints.

## Architecture & Data Models
<!-- scope: technical -->

Four independent workstreams, one review surface (same shape as prior issue sweeps):

1. **Excused completion-review status** — add a distinct persisted member (`not_required`) meaning “policy excused this review.” The 3g skip writes it. Every gate — projection, scheduler, pilot routing, Ralph completion — reads one shared satisfying-member set and treats it as terminal-permitting / satisfied. It is not `ship` (no review ran) and not `unknown` (a decision was recorded). The CLI must accept the member before any prose writes it.
2. **Land tail pathspec** — the tracked sidecar commit is independent of the ignored receipt directory. Missing or ignored receipt paths must not abort or half-stage the sidecar commit.
3. **Impl-review roster** — work and work-rolling accept only review modes impl-review can actually run to a verdict. `export` stays a plan-review one-off if that path already exists; it is not a work impl-review mode.
4. **OpenCode closer spelling** — closer output that names an invocable command uses the host’s form. OpenCode is the flat hyphen form; other hosts keep the colon form they already document.

## API Contracts
<!-- scope: technical -->

- `completion_review_status` gains exactly one new allowed member, **pinned at plan as `not_required`** (see Decision Context for why not `skipped`). No schema alias was reserved; there is no JSON-schema surface for this field, and the published config schema is unaffected. Writers: the 3g skip path (via `spec set-completion-review-status`) and that command directly.
- **One satisfaction predicate, not N comparisons.** The satisfying set is `{ship, not_required}`, declared once and consumed by every gate. Two questions that today's `== ship` conflates are separated: *is the completion-review requirement satisfied* (both members) and *did a review actually run* (`ship` alone). Any unrecognized or absent value reads as `unknown` and satisfies nothing — fail closed, and no migration of existing files.
- `completion_reviewed_at` keeps its current unconditional stamp and means "when this status was written", not "when a review ran". Provenance of a real review is `ship`.
- Land tail: the sync-state step never names an ignored path in a `git add` pathspec. The tail's existing shape is preserved — two file-scoped `.flow` commits (close, then sync state) riding step 4's single push under the `TAIL_BASE_OID`-guarded rollback. Receipts stay untracked; a sidecar with nothing to commit is success, not failure.
- Work option parsing: accepted impl-review modes match the executable impl-review backends. `--review=export` is rejected or remapped to a documented manual path before dispatch, never sent to impl-review.
- Closers (capture Phase 6 including rewrite/split footers; plan next-steps menu and recommendation line; work's ship footer; any other skill closer that prints a copy-pasteable `/flow-next…` command): OpenCode prints the flat form. The colon form stays the canonical default when the host is indeterminate, and the Codex mirror's actionable-invocation transform must still rewrite every closer literal it rewrites today.

## Edge Cases & Constraints
<!-- scope: technical -->

- Writing `ship` on skip is forbidden — that would claim a review happened.
- Re-deriving the skip from task count + R-ID coverage at each reader is forbidden — that reimplements policy and will drift.
- `git add -f` on the receipt directory is not the #367 fix: a missing pathspec still fails and still aborts the chain.
- Do not change the ignore set; receipts remain runtime artifacts.
- Measured git behavior the fix must respect: `git add <tracked> <exactly-named-ignored-dir>` exits 1 **and leaves the tracked file staged** (the half-staged residue); `git add <tracked> <nonexistent>` exits 128 with nothing staged; `--ignore-missing` is only legal with `--dry-run`. Avoidance (never pass an ignored path) is race-free; recovery-by-unstaging is not.
- OpenCode detection uses the existing ownership-manifest / installer signal; do not invent a new host probe. Codex mirror stays colon-form (`$flow-next-` rewrite is a separate existing transform).
- **Mirror-transform coupling (silent failure class):** the planned five files' sixteen literals are exactly the ones the Codex sync rewrites with anchored per-pattern substitutions (four files in the `:389-427` loop, `phases.md` via a one-off sed at `:538`), and the hard-fail guard at `sync-codex.sh:2174` covers only the `Recommended next:` shape. Rewording a literal without updating its anchor leaves the mirror on the colon form at exit 0. A closer reword and its transform update are one atomic change. Verification (2026-08-27) widened the inventory: make-pr's success footer (`create-and-finalize.md:419-420,543,550-551`), interview's suggest-next block (`SKILL.md:446-450`) and `references/write-back.md:154,165,217,244`, prospect's closer/menu (`workflow.md:764,810,825-826`), chart's capture handoff (`references/briefing-and-reopen.md:45`, `references/chart-mode.md:78,162`), audit's remediation line (`SKILL.md:81,121`, `workflow.md:73,538`), and guide's routing matrix (`SKILL.md:43-53`) also print copy-pasteable `/flow-next:` commands — and NONE of those literals are in the mirror's invocation rewrites today, i.e. they are already wrong on Codex. R6 covers them: one host-form clause per file, plus extending the sync transform and its guard to the newly covered files.
- **Ordering is load-bearing for the status member:** if the 3g prose writes the new token before the CLI accepts it, the skip goes from a silent no-op to a hard parser failure (exit 2) — strictly worse than the bug. Plumbing lands first; the reverse order is inert.
- Old spec files need no migration: an absent field is already backfilled to `unknown`, and `unknown` satisfies nothing. An older reader meeting the new value degrades to "review still due" (non-terminal), which is the safe direction.
- Verification correction (2026-08-27): the prose-diet pin (`test_skill_prose_diet.py:307-315`) covers **plan-review's** export string, not impl-review's. Nothing pins impl-review's own parser lines (`flow-next-impl-review/SKILL.md:37,50`), which accept `--review=export` with no workflow behind it — the actual dead-end site, still directly reachable after the work-side fix. R5 therefore drops `export` from impl-review's accepted modes too (same fail-closed message naming `/flow-next:plan-review --review=export`). Plan-review files stay untouched; no export workflow is implemented.
- G1: prefer replacing the broken pathspec / roster line over adding paragraphs. G2: tests assert status members, projection rows, add/commit behavior, reader classification, and parser rejection — not skill prose wording.
- A new `.flow/config.json` key is out of scope; if plan later needs one, the published schema must move in the same change.

## Quick commands

```bash
# Status member + projection + scheduler (workstream 1 plumbing)
cd plugins/flow-next/tests && python3 -m unittest test_tracker_status test_task_inventory test_review_convergence_journal -q

# Land tail pathspec (workstream 2)
cd plugins/flow-next/tests && python3 -m unittest test_land_config test_flow_gitignore -q

# Review roster (workstream 3)
cd plugins/flow-next/tests && python3 -m unittest test_backend_spec test_skill_prose_diet -q

# OpenCode closer spelling + mirror transform (workstream 4)
cd plugins/flow-next/tests && python3 -m unittest test_install_opencode test_prompt_text_pinned -q
```

## Acceptance Criteria
<!-- scope: both -->

- **R1:** After a 3g policy skip, `completion_review_status` is a persisted value that is neither `unknown` nor `ship`, written by the skip itself. `completion_reviewed_at` means "when this status was written", never "a review ran" — `ship` remains the only claim that a review happened. Errors: the skip writes the value only from `unknown`, so a spec already carrying `needs_work` / `needs_human` is never silently upgraded to satisfied; a CLI rejection of the token surfaces as a stage failure, not a silent no-op. `[paraphrase]` `[strategy:Ralph autonomous mode]`
- **R2:** With review configured, merged + spec `done` + that skipped value projects to terminal `done` (not `in_review`), so `--to done` is not refused for a deliberately excused review. The tracker terminal label stays `done`; `verified` remains reachable from `ship` alone. Errors: `unknown` still refuses; `needs_work` / `needs_human` still refuse; a non-merged PR evidence still refuses regardless of the new value. `[paraphrase]` `[strategy:Tracker determinism]`
- **R3:** `flowctl next --require-completion-review` treats the skipped value as satisfied and does not emit `needs_completion_review` for that spec. Errors: `unknown` still requests the review; `needs_work` / `needs_human` still request it. `[paraphrase]`
- **R4:** Land’s post-merge sync-state commit always commits the spec sidecar when the touchpoint edited it, whether the receipt directory is present-and-ignored or absent. The ignored receipts are not staged. The tail's existing two file-scoped `.flow` commits, single push, and `TAIL_BASE_OID`-guarded rollback are preserved. Errors: no ignored path is ever passed to `git add` (avoidance, not recovery), so the sidecar is never left staged-uncommitted and the commit is never skipped; a sidecar the touchpoint did not change is success (nothing to commit), not a reported failure; a re-entered tail (`resume-tail`) over an already-committed sidecar is likewise success. `[paraphrase]` `[strategy:Ralph autonomous mode]`
- **R5:** Work and work-rolling no longer dispatch impl-review with `--review=export`. The accepted roster is stated once and agrees with the review-mode enum work already hands to its workers; work-rolling inherits it by pointer rather than restating it. Errors: an explicit export request fails closed at option-parse time with a message that export is not an impl-review backend (naming the manual path), never a mid-dispatch escalation. The dead-end closes at both mouths: work's advertised surfaces (SKILL.md roster, setup-questions tip, and the `commands/work.md` argument-hint) and impl-review's own accepted-modes lines all drop `export`; plan-review's export mode stays untouched as the named manual path. `[paraphrase]`
- **R6:** On OpenCode, every closer that prints an invocable flow-next command uses the flat `/flow-next-<name>` form; Claude/Cursor/Droid/Grok closers keep the documented colon form. Errors: no host prints a command the user cannot invoke on that host; an indeterminate host prints the canonical colon form; the Codex mirror still rewrites every closer literal it rewrites today, with its hard-fail guard green (a reworded literal whose transform anchor no longer matches is a failure of this criterion, even though the sync exits 0). `[paraphrase]` `[strategy:Cross-platform parity]`
- **R7:** Every gate that keys on `completion_review_status` decides through ONE explicit allow-set of satisfying members rather than its own `!= ship` check: the merge-evidence projection, the `--require-completion-review` scheduler, pilot's stage routing, the Ralph completion gate, the status-sync doctrine table, and spec-completion-review's own idempotent-terminal checkpoint (`SKILL.md:132`) all agree. make-pr's `== needs_work` open-items predicates are member-safe by construction (verify, don't edit). A test enumerates every known member and pins each gate's classification, so a future member cannot silently default. Errors: an unrecognized or absent value reads as `unknown` and satisfies no gate (fail closed); a satisfied gate never implies a review ran.

## Boundaries
<!-- scope: business -->

- **#89** Ralph scope isolation — already tracked on fn-61; not recaptured. `[user]` (parked by prior maintainer replies and fn-199)
- **#369 / #370** actor uniqueness (claim refusal seam; worktree-kit surface-only print) — complementary to open fn-204 (per-run claim identity), not this spec. Do not implement a Kit-written `FLOW_ACTOR`. `[paraphrase]`
- **#368** portable land ledger / multi-host budgets — valid report; option 1 (portable store) is a larger design than this sweep. Option 2 (document one land host per checkout) may land as a docs sentence in the land skill if it costs no new machinery; no committed ledger, no tracker-carried land state. `[paraphrase]`
- No hosted/SaaS land state. `[strategy:approach]`
- No new slash command. `[strategy:Ralph autonomous mode]`
- No version bump (batched releases). `[inferred]`
- Do not implement an impl-review export workflow. `[inferred]`
- Do not write `ship` on a policy skip. `[paraphrase]`
- The Ralph completion prompt template's own "backend is `none` → write `ship`" line is the same anti-pattern but a different trigger; explicitly **out of scope** here (it would also require a same-commit prompt-hash update with its own rationale). Its reader-side gate is in scope under R7.
- Deduping the three near-identical verdict→status maps belongs to open spec fn-190; this spec adds no fourth copy and does not perform that dedup.
- No flowctl staging or amending for the land tail — a prior accepted decision rejects `--stage`/`--amend`, so the fix stays in land's skill prose.
- No new flowctl command or flag for host-form command spelling; the closer fix is skill prose.

## Decision Context
<!-- scope: both -->

- One spec, four workstreams: same ceremony as prior field-report sweeps; none of the four blocks another. `[inferred]`
- Drop `--review=export` from work rather than build an export backend: the owner’s issue already named both options; dropping makes parser and dispatcher agree with the smallest surface. `[inferred]`
- **Token pinned as `not_required`, overriding capture's tentative `skipped`.** Both alternatives capture recorded as rejected stay rejected (`ship`, and infer-at-read-time). The deciding argument is which question the field answers: after R2/R3/R7 the value means "the completion-review requirement is permanently satisfied" — an affirmative claim — whereas `skipped` states that an action did not happen, which is exactly the reading that produced today's four-reader bug, and matches the CI convention where skipped means "outcome unknown, do not count as passing". The run-scoped 3g stage line keeps the word "skipped" verbatim; two tokens for two different questions is the fix, not an inconsistency. Reversible before implementation — worth a reviewer's confirmation.
- Corrected from capture: the land tail already produces **two** file-scoped `.flow` commits sharing one push, and its rollback is range-based against `TAIL_BASE_OID` (a test explicitly bans the `HEAD^` form). So a two-statement add-then-commit inside the sync-state step is rollback-safe by construction, and "must stay one commit" is not a real constraint.
- The `--to done` refusal lives entirely in the projection's merged-and-done row; the label selector that chooses `verified` vs `done` is a separate reader and deliberately stays `ship`-only.
- Pilot's stage routing is a fourth reader that no captured criterion covered: left alone it re-routes a policy-skipped spec to `work` every tick, which re-skips and ends the tick — a cross-tick livelock that only exits via the no-advance strike path. Hence R7 rather than treating reader closure as implementation detail. `[plan]`
- Closer fix shape: state the host-form invariant once per closer surface and let the existing mirror transform carry Codex; rejected as overkill a flowctl-printed invocation helper (new CLI surface for a prose problem) and a per-host enumeration table in every closer (races the next host).
- Verification pass (2026-08-27, pre-work): all four issues reproduce at f21ac86b. Two plan corrections folded in: the impl-review prose boundary rested on a misattributed test pin (now dropped — impl-review's parser loses `export` too), and the closer inventory was under-enumerated (widened; the extra surfaces were already broken on Codex, whose transform never covered them). Import-direction early proof point pre-answered: flowctl.py treats `flowctl_tracker` as optionally absent (lazy imports + sys.path fallback + graceful degrade, e.g. `flowctl.py:1903-1913`, `:39155-39166`) and argparse `choices` builds at parse time, so a module-scope shared import is unsafe — expect the canonical literal in `flowctl.py`, a mirrored declaration in the tracker package, and a parity test pinning them equal. `[plan]`
- #368 portable home deferred: “everything in the repo” does not require committing the current git-common-dir scratch file; inventing a new durable store is a later spec. `[inferred]`

## Strategy Alignment

- Ralph autonomous mode: land tail + completion-review readers in the ship loop.
- Tracker determinism: projection row for the new status is plumbing, not a skill judgment.
- Cross-platform parity: OpenCode closer spelling.
- Approach: no hosted land state; flowctl only for the status member and projection/scheduler predicates.

## Early proof point

Task fn-205-issue-sweep-skipped-review-status-land.1 validates the core approach: one declared satisfying-member set drives the projection and the scheduler, and a member-enumeration test pins every gate's classification. If that predicate cannot be shared across the CLI and the tracker package without an import inversion (forcing two mirrored copies plus a parity test), re-evaluate the "one allow-set" shape before the reader-closure task fn-205-issue-sweep-skipped-review-status-land.3 spreads it into skill prose.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | 3g skip persists `not_required`; timestamp semantics | fn-205-issue-sweep-skipped-review-status-land.2 | — |
| R2 | Merged + done + `not_required` projects terminal `done` | fn-205-issue-sweep-skipped-review-status-land.1 | — |
| R3 | `next --require-completion-review` treats it as satisfied | fn-205-issue-sweep-skipped-review-status-land.1 | — |
| R4 | Land sync-state commit survives ignored/absent receipts | fn-205-issue-sweep-skipped-review-status-land.4 | — |
| R5 | `--review=export` off work/work-rolling roster, fails closed | fn-205-issue-sweep-skipped-review-status-land.2 | — |
| R6 | OpenCode closers print the flat invocable form | fn-205-issue-sweep-skipped-review-status-land.5 | — |
| R7 | One allow-set across every gate + enumeration test | fn-205-issue-sweep-skipped-review-status-land.1, fn-205-issue-sweep-skipped-review-status-land.3 | — |

