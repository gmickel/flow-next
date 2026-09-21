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

## Superseded by the chain rules (updated 2026-09-20)

The manual successor-PR playbook above records the earlier incident. Dependent specs build as **chains** and use native stacks where supported:

- `flowctl spec chain <id>` decides when a dependent spec may start (parent not landed at the base, all tasks done, branch on origin; linear only). Work branches from the parent's remote tip; make-pr targets the parent's branch and links a GitHub stack. Rules: `plugins/flow-next/skills/flow-next-make-pr/workflow.md` §0.3, `flow-next-work/phases.md` Phase 2.
- Land links open children into a native stack before merging and merges only the lowest open layer, one layer per run. GitHub retargets and rebases stack children. Land never deletes a branch while an open PR targets it and never rebases, force-pushes, or retargets a child.
- Without stacks, a conflicted child needs a separately authorized manual single-layer rebase after the parent merges. Follow `plugins/flow-next/docs/troubleshooting.md` §"Land on a chain"; inspect the parent's pre-merge tip, rebase only the child, and re-read its checks and reviews before landing.
- The merged-parent window before a child has a PR is make-pr's rebase-onto from the detected boundary (create run only), so no successor PR is needed.

## Avoiding it next time

- Do not hand-build a dependent PR on a feature branch outside the chain rules; let work and make-pr build it, then land each lowest open layer.
- Related GitHub sharp edge from the same run: a comma list after one closing keyword ("Fixes #A, #B, #C") auto-closes only #A — each issue needs its own keyword ("Fixes #A, fixes #B, fixes #C").
