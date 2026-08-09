# Overview

Two integrity gaps in the make-pr/validate surface, from issues #301 and #302 (sn-furali 2026-08-08 batch): coverage conflates "planned" with "evidenced" so a plan-gate PR reports 0% and make-pr aborts with advice that cannot be followed; and evidence commit SHAs are never re-checked after history rewrites, so validate stays green while every recorded SHA is orphaned (measured 15/15 on one spec after a mandatory rebase).

**Evidence standing: reporter-verified at 3.16.3 with quoted guards and a measured orphaning run; accumulation logic and validate confirmed unchanged on main. No new evals.**

## Goal & Context

Make the coverage payload answer both real questions (declared at the plan gate, evidenced at the merge gate) instead of conflating them, and give `validate` a read-only finding for evidence commits no longer reachable from HEAD, so a rebase cannot silently void a PR's evidence links.

## Architecture & Data Models

1. **Declared vs evidenced (#301):** `export-cognitive-aid` accumulates a second set from all tasks' `satisfies` irrespective of status and exposes `undeclared_r_ids` alongside the existing `uncovered_r_ids`. Existing field keeps its name and meaning; nothing reading it today changes. make-pr's unrenderable-abort re-keys on *undeclared* coverage (the condition it was meant to catch); at a plan gate the body renders "claimed by fn-N.M, not yet evidenced" per criterion instead of a false 0%.
2. **Evidence reachability (#302):** a `flowctl validate` finding distinguishing three states per `evidence.commits[]` entry: reachable from HEAD (fine), present-but-orphaned (finding: remappable), not a commit in this repo (ignore - tracker UUIDs and foreign SHAs are legitimate; 7 of 22 hex tokens in the reporter's run were of that kind). Verdict only, no auto-rewrite: a wrong remap is worse than a stale link.
3. **Batched git calls (perf constraint):** one `git cat-file --batch-check` over all recorded tokens plus one membership pass (single `git rev-list` set or grouped `merge-base` over the existing few), never a per-SHA spawn loop. The land loop calls validate repeatedly; per-SHA spawns would regress the fn-109 class of wins.

## Edge Cases & Constraints

- Plan-gate state (all tasks todo, all satisfies declared) must render, not abort; a genuinely unassigned criterion must be visible as undeclared at plan time.
- Merge-gate semantics unchanged: evidenced coverage still counts done tasks only. Loosening to todo tasks was considered and rejected in the issue; agreed.
- The existing `merge-base --is-ancestor` in the payload guards gate-receipt reuse; do not entangle the two.
- make-pr must not render an evidence link for an orphaned SHA without marking it; exact rendering (omit vs annotate) is the implementer's call, abort is not acceptable.
- Post-capture drift (2026-08-09, branch-disclosure refactor): make-pr's prose is split across reached-path files. Contract over location: the abort to re-key is the unrenderable condition (empty goal-and-context with no done summaries) on the universal rendering path, and the coverage line renders from `tasks_summary.uncovered_r_ids`; re-key on undeclared coverage wherever the condition lives. New prose-contract fixtures pin content + reachability, never bare location (standing pin-shape rule). Concrete anchors: task 2.

## Acceptance Criteria

- **R1:** Payload exposes `undeclared_r_ids` computed from all tasks' `satisfies` regardless of status; existing `uncovered_r_ids` semantics byte-identical. Errors: none.
- **R2:** make-pr renders a plan-gate body (all tasks todo, full declaration) with per-criterion claimed-not-evidenced status, and aborts only when coverage is undeclared. The #301 abort repro no longer aborts.
- **R3:** `validate` reports orphaned evidence commits (present in object store, not ancestors of HEAD) as findings; unreachable non-commit tokens are ignored; reachable commits are silent. The #302 three-state table is the contract.
- **R4:** validate's reachability pass uses batched git plumbing: at most a constant number of git spawns regardless of commit count. Errors: a repo where batch-check is unavailable falls back gracefully, never crashes validate.
- **R5:** No automatic rewriting of recorded SHAs anywhere. Errors: none.
- **R6:** Mirrors, dual flowctl copies, docs (flowctl.md validate section, make-pr skill reference), CHANGELOG Unreleased crediting @sn-furali. Errors: parity red blocks merge.

## Boundaries

- No new commands; findings ride the existing `validate` output shape.
- No remap/fixer, no `--fix` flag.
- No change to evidence-json schema.
- Version bump deferred to the batched release.

## Decision Context

The batching requirement is an explicit R-ID because the naive per-SHA implementation (2 spawns x N commits inside a land-loop-called verb) is the obvious delegated implementation and would claw back fn-109-class performance; writing the constraint into acceptance keeps it through delegation. #302's third state (foreign hex tokens) is load-bearing: a checker that flags them corrupts exactly the evidence the record exists to hold, so ignore-on-cat-file-miss is contract, not leniency.
