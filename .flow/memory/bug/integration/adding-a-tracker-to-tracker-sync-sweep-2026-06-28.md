---
title: "Adding a tracker to tracker-sync: sweep WHOLE tree + read adapter ref for dep-pr"
date: "2026-06-28"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-tracker-sync
tags: [tracker-sync, gitlab, fn-69, doc-sweep, flow:deps, dependency-projection, impl-review]
problem_type: integration
symptoms: "impl-review NEEDS_WORK x5: stale Linear/GitHub-only enumerations in ~12 secondary files + flow:deps framed as GitLab-degrade-only when GitLab carries it on every tier"
root_cause: "Swept only the spec's named-file list (not the whole plugin tree) + copied GitHub's fenced-block-FALLBACK mental model onto GitLab, which carries the block on every tier"
resolution_type: fix
related_to: [bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17, bug/integration/markerstruct-field-semantics-must-2026-06-27, bug/integration/rp-builder-file-slices-cause-false-2026-06-10, bug/integration/set-tracker-id-rejected-github-n-2026-06-03, bug/integration/trackers-auto-linkify-issue-key-2026-06-03]
---

## Problem
Adding GitLab as a third tracker (fn-69) required a full doc sweep of every
"Linear/GitHub" supported-tracker enumeration AND extending the per-adapter
dependency-projection prose. Two classes of miss surfaced in impl-review:

1. **Incomplete enumeration sweep.** The named-file sweep (docs/tracker-sync.md,
   flowctl.md, skills.md, teams.md, README.md, GLOSSARY.md) missed ~12 secondary
   surfaces: docs/README.md transport-ladder row, root README teams snippet, the
   Linear-Diffs "GitHub tracker" note, setup usage.md template + .flow/usage.md +
   workflow.md (`type ∈ {linear,github}`), work/SKILL.md active predicate,
   pilot/backlog-mode.md adapter set, the SKILL.md + command frontmatter
   descriptions, adapter-interface marker-vocabulary, and steps.md list-open
   label semantics.

2. **A real semantic correctness bug.** GitLab carries the `<!-- flow:deps -->`
   body block on EVERY tier (native is_blocked_by AND degraded relates_to) — it
   is the durable direction/provenance source even when the board-visible native
   link exists. Initial fix-round prose framed the block as "body-fallback only"
   (GitHub-native-unavailable OR GitLab Free/personal), which would lead an agent
   to WIPE the block on a Premium/Ultimate GitLab native-link project. This same
   wrong framing had to be corrected across ~7 surfaces (body-merge.md, steps.md
   x2, adapter-interface.md x2, SKILL.md, docs/tracker-sync.md, GLOSSARY.md).

## What Didn't Work
- A `grep` of only the spec's NAMED sweep files. The stale enumerations live in
  ~20 files, not 6 — secondary surfaces (setup templates, the active-predicate
  enum in work/SKILL.md, command/skill frontmatter descriptions, the installed
  .flow/usage.md copy) are all user/agent-facing and equally stale.
- Copying the GitHub adapter's "fenced-block FALLBACK" mental model onto GitLab.
  GitLab is NOT GitHub: GitHub writes the block only when native deps are
  unavailable; GitLab writes it on EVERY tier. The adapter reference (gitlab.md
  §writeIssue/§Relation transport, "always carry it") is authoritative — read it
  before paraphrasing the dependency-projection semantics into other files.

## Solution
- Sweep with a BROAD regex across the WHOLE plugin tree (skills + docs +
  commands + templates + the installed .flow/ copies + root README/GLOSSARY),
  not just the spec's named-file list. Pattern set: `Linear/GitHub`,
  `Linear or GitHub`, `Linear first, GitHub next`, `∈ {linear,github}`,
  `{linear,github}`, `Linear-vs-GitHub`, `Linear + GitHub`. Exclude the codex/
  mirror (derived) and the RELEASED CHANGELOG headings (frozen point-in-time).
- For the flow:deps semantics, the canonical framing is "GitHub's fenced fallback
  (native deps unavailable) AND GitLab on every tier (durable direction source
  alongside the native link, sole record on the degrade)". Preserve the block on
  every body write for ANY adapter that carries it.

## Prevention
- When adding tracker N to tracker-sync, sweep the WHOLE plugin tree with the
  broad enumeration regex above — the spec's named-file list is a floor, not a
  ceiling. The installed `.flow/usage.md` and setup `templates/usage.md` are easy
  to miss (two copies). Skill/command frontmatter `description:` lines and the
  `tracker.type ∈ {...}` active-predicate enums are also routinely missed.
- Per-adapter dependency-projection prose is NOT copy-paste from github.md.
  Read the new adapter's reference (gitlab.md) for whether the block is
  fallback-only (GitHub) or all-tier (GitLab) BEFORE paraphrasing it elsewhere —
  the "fallback" framing is GitHub-specific and wrong for GitLab.
