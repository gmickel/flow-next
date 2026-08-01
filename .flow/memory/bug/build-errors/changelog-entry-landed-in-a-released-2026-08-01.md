---
title: "Changelog entry landed in a released section, not Unreleased"
date: "2026-08-01"
track: bug
category: build-errors
module: CHANGELOG.md
tags: [changelog, release, docs]
problem_type: build-error
symptoms: New '## Unreleased' entry appears under the latest released version heading
root_cause: "Insertion point located by '### ' subsection grep; a released '## [x.y.z]' heading sat between Unreleased and that subsection"
resolution_type: fix
related_to: [bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11, bug/build-errors/skill-adding-version-bump-leaves-stale-2026-06-05]
---

## Problem
A worker appended an `## Unreleased` CHANGELOG entry that actually landed inside
the most recent RELEASED version section (`## [flow-next 3.13.1]`), retroactively
attributing unreleased work to a shipped release. The impl review caught it (P1).

## What Didn't Work
Locating the insertion point by grepping `^### ` (the subsection headings) and
assuming the first `### Changed` belonged to `## Unreleased`. It did not - a
released `## [flow-next X.Y.Z]` heading sat between them. Reading only the first
~30 lines of CHANGELOG.md reinforced the wrong mental model, because `## Unreleased`
appears at the top and its own subsections (Fixed/Added) are far down the file.

## Solution
Grep `^## ` FIRST to get the version-section boundaries, then place the entry
inside the `## Unreleased` span - adding a `### Changed` subsection under it when
Unreleased has none yet. Verified by re-grepping `^## |^### ` and confirming the
new bullet sits before the first `## [flow-next ...]` line.

## Prevention
Before editing CHANGELOG.md, run `grep -n '^## ' CHANGELOG.md | head -5` and
anchor the edit to the line range between `## Unreleased` and the next `## [`.
Never anchor a changelog edit on a `### ` heading alone.
