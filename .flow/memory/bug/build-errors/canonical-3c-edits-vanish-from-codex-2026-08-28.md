---
title: Canonical 3c edits vanish from Codex mirror via stale SECTION3C heredoc
date: "2026-08-28"
track: bug
category: build-errors
module: scripts/sync-codex.sh
tags: [fn-208, sync-codex, codex-mirror, section3c, dispatch-template, codex-review]
problem_type: build-error
symptoms: Mirror regenerated green but lacked new FORBIDDEN/TIMEBOX dispatch fields
root_cause: SECTION3C heredoc wholesale-replaces canonical 3c; unedited heredoc = silent stale mirror at exit 0
resolution_type: fix
---

## Problem
fn-208.2 added FORBIDDEN and TIMEBOX lines to the canonical work phases.md 3c worker dispatch template. The Codex mirror regenerated at exit 0 without them: sync-codex.sh replaces the whole canonical 3c section with the hardcoded SECTION3C heredoc, so any canonical 3c edit not repeated in the heredoc vanishes silently. Codex-review round 1 flagged it as P1 (Codex workers would receive neither the scope ban nor the runtime cap).

## What Didn't Work
Trusting the two green sync-codex.sh runs plus the mirror diff as proof of propagation - the stale heredoc is itself the generator, so its output looked consistent.

## Solution
Added both dispatch lines to the SECTION3C heredoc in scripts/sync-codex.sh, and a hard-fail guard in the same phases block asserting both field literals survive in the mirror phases.md (fix content or extend SECTION3C, never relax the guard).

## Prevention
Any canonical edit inside work phases.md 3c must land in the SECTION3C heredoc in the same commit (documented in CLAUDE.md checklist item 5a, now also machine-guarded for the dispatch fields). When adding a load-bearing literal to a section a sync transform rewrites wholesale, add its grep guard alongside.
