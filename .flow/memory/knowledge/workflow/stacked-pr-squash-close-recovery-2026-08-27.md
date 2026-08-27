---
title: Squash-merging a stacked PR's base permanently closes the stacked PR - rebase + successor PR is the recovery
date: "2026-08-27"
track: knowledge
category: workflow
module: land
tags: [stacked-prs, squash-merge, land, gh, rebase, delete-branch, github-behavior]
applies_when: Opening a PR whose base is another PR's feature branch, or landing the base PR of a stack with squash + --delete-branch
---

Observed live landing fn-205/fn-206 (PRs #372/#373, 2026-08-27): `gh pr merge <base-pr> --squash --delete-branch` deleted the base feature branch, and GitHub **closed the stacked PR (#373) permanently** instead of retargeting it. A closed PR whose base branch is gone can neither be reopened (`reopenPullRequest: Could not open the pull request`) nor retargeted (`Cannot change the base branch of a closed pull request`). GitHub's auto-retarget only fires in narrower conditions than people assume; do not rely on it.

Squash also orphans the stack's history: the stacked branch still contains the base branch's pre-squash commits, so after the base merges, the stacked PR's diff-vs-main would double-count everything even if it had survived.

## Recovery that works (measured)

1. Rebase the stacked branch onto merged main: `git rebase --onto main <old-fork-point>` — expect conflicts ONLY in generated files (MANIFEST.json etc.); take either side per pick and regenerate once at the end (`gen_tracker_manifest.py`, `sync-codex.sh` twice), commit the regen as a fixup.
2. Force-push with lease; open a **successor PR** against main (the old PR number is lost — link it with "Supersedes #N" in the body).
3. Squash-orphaned bookkeeping follows: task evidence commits and rebaseline-evidence baseline SHAs recorded on the stack point at commits the squash removed — repoint receipts at the squash SHA and regenerate evidence against a reachable baseline (codex flagged all three on #374).

## Avoiding it next time

- Prefer landing the base and only THEN building the dependent branch off main, when timing allows.
- If stacking is worth it, plan the successor-PR step as part of the land sequence rather than discovering it; the PR-body cognitive aid and thread history carry over via the Supersedes link.
- Related GitHub sharp edge from the same run: a comma list after one closing keyword ("Fixes #A, #B, #C") auto-closes only #A — each issue needs its own keyword ("Fixes #A, fixes #B, fixes #C").
