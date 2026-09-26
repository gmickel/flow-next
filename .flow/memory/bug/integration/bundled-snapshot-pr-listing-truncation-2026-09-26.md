---
title: "Bundled snapshot PR listing: truncation and partial history on reselected rows"
date: "2026-09-26"
track: bug
category: integration
module: plugins/flow-next/scripts/flowctl.py
tags: [pilot, snapshot, gh, pr-probe]
problem_type: integration
symptoms: "flow --auto hop fails closed on 1000+ PR repos, or a deferred-then-reselected candidate routes to make-pr despite a merged/closed PR"
root_cause: one repo-wide PR listing replaced per-branch probes; non-selected rows kept open-only history without a completeness flag
resolution_type: fix
related_to: [bug/integration/backend-special-case-in-a-shared-helper-2026-09-05, bug/integration/drop-receipt-to-break-codex-2026-05-09, bug/integration/headless-review-backend-error-envelope-2026-09-05, bug/integration/set-tracker-id-rejected-github-n-2026-06-03]
---

## Problem
Bundling several per-candidate reads into one snapshot (fn-259 `pilot snapshot`) replaced a per-branch `gh pr list --head <branch> --state all` with one repo-wide listing. The first version listed all PRs (`--state all --limit 1000`) and failed closed at 1000 rows, so any repo with 1000+ PRs would end every hop NEEDS_HUMAN. Narrowing the listing to open PRs plus a full-history probe for the selected branch then left the other candidates with open-only observations that still produced definitive lifecycle decisions; auto.md lets the host defer the selected spec and continue over the same snapshot, so a later candidate with a merged or closed-unmerged PR could route to make-pr.

## What Didn't Work
One all-state listing (truncates on large repos) and open-only observations without a completeness marker (silent partial history).

## Solution
`pilot_snapshot` in plugins/flow-next/scripts/flowctl.py: one open-state listing for selection, a `--head --state all` probe for the selected branch only, `pr.history_complete` on every observation, no route decision from an incomplete observation, and auto.md refreshes a reselected candidate with `pilot snapshot --spec <id>` before classifying it.

## Prevention
When a bundle replaces per-item probes with one listing, check the listing's truncation bound against real repo sizes and mark every field computed from partial data as partial; a consumer that can pick a non-default row must be tested against that row, not only the default selection.
