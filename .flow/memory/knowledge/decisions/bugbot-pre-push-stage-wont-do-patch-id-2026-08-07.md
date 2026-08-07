---
title: "Bugbot pre-push stage: won't-do - patch-ID dedup falsified live"
date: "2026-08-07"
track: knowledge
category: decisions
module: review
tags: [bugbot, cursor, review-backends]
applies_when: "Bugbot pre-push stage: won't-do - patch-ID dedup falsified live"
---

## Problem
fn-167 proposed a Bugbot pre-push review pilot stage, premised on Cursor Bugbot's documented patch-ID dedup: review locally via /review-bugbot, and the later PR review skips as already-reviewed - relocating the review pre-push at no extra cost.

## What was chosen
CLOSED WON'T-DO after a live smoke (2026-08-07, gmickel/flow-next, PRs #297/#298) falsified the premise BEFORE any code: marking an identical-diff PR ready produced a FRESH full Bugbot review (4 findings re-found) - no skip comment, no empty incremental - despite same commit SHA, Once-Per-PR trigger, Incremental Review on. Pre-push + PR = double billing from the same usage pool.

## Why
Without dedup, the stage duplicates the existing cursor review backend (fn-74) at the same per-review price, plus a dashboard dependency. Secondary measured facts, kept for future Bugbot questions: (1) draft PRs get ZERO Bugbot coverage with Review-Draft-PRs off - autonomous forced-draft output is never reviewed until a human marks ready; (2) local /review-bugbot quality is good (3/3 planted bugs + 1 bonus, ~25s/31-line diff); (3) the reviewer reads EVERYTHING in the diff and reasons about intent - a deliberate-bug banner yields ZERO findings across 3 models, and metadata files in the diff contaminate reviews (never put flow-next metadata inside reviewed changes); (4) repo-level trigger mode (auto vs manual) silently voids passive observations - record it alongside account settings in any future smoke.
