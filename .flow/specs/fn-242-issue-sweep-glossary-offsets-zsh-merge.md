# Issue sweep: glossary offsets, zsh merge, todo/backlog status

## Conversation Evidence

> user: "fix the easy ones first, direct fix, impl-review via codex in gpt-6-astra when done, small review though, no release yet as another agent is doing a release"

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 50% [user], 50% [paraphrase] -->

Triage of the nine open GitHub issues on 2026-09-13 against 5.2.0 found four reproducible, small, single-context defects. Three are in this spec; #391 (spec-only PR counted as merge evidence) needs a design choice and #411 (land worktree safety) is a larger change, so both stay out. #368, #369, #370, #89 are parked on prior maintainer replies (fn-204, fn-61) and are not recaptured. `[paraphrase]`

**In scope (all reproduced on main at bcbfbe5e):**

- **#408** — `parse_glossary_file` computes the `_Avoid_` and `_Relates to_` match offsets against `body`, then applies both removals cumulatively to the shrinking string. The second removal cuts the wrong window, so `glossary add` corrupts every existing entry carrying both lines, and the corruption compounds on each subsequent add. `render(parse(text)) == text` fails for such an entry today. `[user]`
- **#406** — Land's merge step builds `MERGE_CMD="${FLOW_PR_MERGE_CMD:-gh pr merge}"` and invokes `$MERGE_CMD ...` unquoted, relying on bash word-splitting. Under zsh (macOS default; Claude Code's Bash tool may run the login shell) the whole string is one command name and the merge fails with exit 127. `[user]`
- **#375** — On a GitHub/GitLab tracker, `capture` labels the issue `status:backlog`; `plan` then pushes with flow=`todo` (all tasks todo) and `decide()` has no rule for `{flow: todo, tracker: backlog, requested: todo}`, so every planned spec's push receipt records `status conflict (unmapped)`. The error text and docs steer users to `perTracker.statusMap`, which only Jira/Linear providers read. `[user]`

## Architecture & Data Models
<!-- scope: technical -->

Three independent one-file fixes, one review surface (same shape as prior issue sweeps):

1. **Glossary parse** (`scripts/flowctl.py`, `parse_glossary_file`): apply the `_Avoid_` / `_Relates to_` removals in descending offset order so an earlier removal cannot invalidate a later match's offsets. Round-trip property holds for entries with both lines.
2. **Land merge command** (`skills/flow-next-land/workflow.md` merge block, plus the Codex mirror via `sync-codex.sh`): build the merge command as an array so the invocation is shell-agnostic. Keep the "never eval'd" contract and the `FLOW_PR_MERGE_CMD` override semantics.
3. **Status policy** (`scripts/flowctl_tracker/status/policy.py`, `decide()`): `flow=todo` and `tracker=backlog` are agreeing early states; a requested `todo` (or `backlog`) against that pair is a `noop` at the tracker's current slot. `status-sync.md` states that `perTracker.statusMap` is read by the Jira and Linear providers only.

## API Contracts
<!-- scope: technical -->

- `parse_glossary_file` output is unchanged for entries carrying zero or one metadata line. For entries with both, `definition` no longer contains any `_Relates to_` / `_Avoid_` fragment, and `render_glossary_file(parse_glossary_file(t)) == t` for the canonical rendering.
- Land merge: `FLOW_PR_MERGE_CMD` keeps its documented contract (whitespace-split into argv, never eval'd; the PR number and flags are appended as separate args). The captured `MERGE_ERR` / `MERGE_RC` handling that follows is untouched.
- `decide()`: exactly one new early-ladder rule: `flow_norm == "todo" and tracker_norm == "backlog"` with `requested_to in ("todo", "backlog")` returns `Decision("noop", target_slot=tracker_norm)`. No other row of the table changes; `conflictTiebreak` semantics are untouched. The tracker label stays `status:backlog` (backlog remains the single "not started" bucket the readiness projection already assumes).

## Edge Cases & Constraints
<!-- scope: technical -->

- Glossary: an entry whose `_Relates to_` precedes `_Avoid_` (hand-authored order) must also parse cleanly; sort by offset, do not assume render order.
- Land: the bash fence must stay bash-and-zsh safe without `eval`; the Codex mirror must be regenerated (`sync-codex.sh`) and stay idempotent. Do not touch any other fence in that file.
- Status: a requested `in_progress` or `done` against `{todo, backlog}` is not covered by the new rule and keeps its existing behaviour. A task-less spec (`flow=backlog`) already noops and must keep doing so.
- Tests assert behaviour (parse output, round-trip, `decide()` kinds), not prose wording. A regression test per fix.
- No config schema change. No release in this change: another agent owns the current release; do not bump versions or add a versioned changelog heading. Add the three fixes under `## Unreleased` in `CHANGELOG.md` crediting the reporters (flecamos for #408, TechupBusiness for #406, TechupBusiness for #375).

## Quick commands

```bash
python3 scripts/run_tests_parallel.py
zsh -c 'MERGE_CMD=(${=FLOW_PR_MERGE_CMD:-gh pr merge}); print -l -- "${MERGE_CMD[@]}"'
bash scripts/sync-codex.sh --check 2>/dev/null || bash scripts/sync-codex.sh
```

## Acceptance Criteria

- **R1:** Parsing a glossary entry that carries both `_Avoid_` and `_Relates to_` yields a clean definition and the correct lists, in either line order; `render(parse(t)) == t` for the canonical rendering; a regression test covers it. (#408)
- **R2:** The land merge fence invokes the merge command in a form that works under both bash and zsh without `eval`, preserving the `FLOW_PR_MERGE_CMD` override; the Codex mirror is regenerated and `sync-codex.sh` is idempotent. (#406)
- **R3:** `decide()` returns `noop` for `{flow: todo, tracker: backlog}` with a requested `todo` or `backlog` under every `conflictTiebreak`; existing rows are unchanged; a regression test covers the new rule; `status-sync.md` notes that `statusMap` is Jira/Linear-only. (#375)
- **R4:** `CHANGELOG.md` gains three `Fixed` entries under `## Unreleased` crediting the reporters; no version bump.
