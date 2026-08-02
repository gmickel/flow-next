---
title: "CODEX_HOME rewrite: both spellings, actionable prose, quoting, sorted-hash idemp"
date: "2026-08-02"
track: bug
category: build-errors
module: scripts/sync-codex.sh
tags: [codex, installer, generated-artifacts, shell-quoting, idempotency]
problem_type: build-error
symptoms: Alternate Codex home silently reaches back into the primary ~/.codex; guard reports success
root_cause: "Home-path substitution treated as uniform: one spelling grepped, actionable prose classified as narrative, expansion left unquoted"
resolution_type: fix
---

## Problem
Replacing a hardcoded `$HOME/.codex` with `${CODEX_HOME:-$HOME/.codex}` across a
generated artifact tree looks like a blanket substitution. It is not. Two classes
of occurrence break in different ways, and a guard that only counts shell blocks
misses both.

## What Didn't Work
1. Grepping one spelling. The generator also emitted the TILDE form
   (`~/.codex/templates/...`, `~/.codex/scripts`) at a separate rewrite site,
   reaching files the `$HOME/.codex` inventory never listed. Worse, those tilde
   paths sat inside double quotes (`cp "~/.codex/..."`), where `~` does not
   expand at all - a latent bug predating the change.
2. Splitting occurrences into "executable" and "narrative" by whether they sit
   in a fenced bash block. Prose can be actionable: "add to `~/.codex/config.toml`"
   and "detect `~/.codex/agents/<file>`" are instructions an operator or agent
   follows, so under an alternate home they point at the wrong file while the
   guard reports success.
3. Rewriting the expansion without quoting it. `bash ${CODEX_HOME:-$HOME/.codex}/x.sh`
   word-splits on a home containing spaces; the old literal happened not to.

## Solution
- Rewrite BOTH spellings at every generator site, and prefer `$HOME` over `~`
  so the path survives quoting.
- Classify by *actionability*, not by syntax. Executable paths and actionable
  instructions get the runtime form; only genuinely descriptive mentions
  ("default `~/.codex`", "a pure `~/.codex` install") stay literal, under a
  narrow explicit allowlist.
- Quote every generated expansion, and prove it with an install into a
  directory whose name contains a space.
- Add a fail-closed guard over the whole installed surface (skills, agents,
  references, templates) that rejects any non-allowlisted primary-home
  reference. Prove existing guards still bite by deliberately reverting a
  rewrite rule and confirming a non-zero sync exit, then restoring it.

## Prevention
- Byte-idempotency of a generator must be hashed with a SORTED file listing.
  `find <dir> -type f -exec shasum {} + | shasum` is order-sensitive: ignored
  `__pycache__` / temp files churn directory entry order between runs and
  produce three different hashes for byte-identical content.
- A "nothing was written to the real home" claim needs a scoped before/after
  listing over the installer-owned paths only. A whole-home listing is polluted
  by the live CLI's own logs, session rollouts, and model cache.
- Test fixtures that redirect `HOME` must also scrub inherited `CODEX_HOME`
  (or the equivalent home-override variable) the moment the code under test
  starts honoring it - otherwise the suite installs into a developer's real home.
