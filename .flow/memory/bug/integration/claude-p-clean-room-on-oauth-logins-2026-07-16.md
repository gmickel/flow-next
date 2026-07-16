---
title: "claude -p clean-room on OAuth logins: --setting-sources project,local; --bare an"
date: "2026-07-16"
track: bug
category: integration
module: agent_docs/guidance-eval/runner.sh
tags: [claude-cli, clean-room, eval-harness, oauth, setting-sources, bare, fn-99]
problem_type: integration
symptoms: claude -p --bare and CLAUDE_CONFIG_DIR-isolated runs return 'Not logged in' on OAuth-only machines; non-isolated runs leak the global CLAUDE.md into scratch repos
root_cause: "--bare is API-key-only auth (skips keychain); OAuth state lives in the config dir, so a fresh CLAUDE_CONFIG_DIR discards the login"
resolution_type: workaround
---

## Problem
Standing eval methodology (memory note usage-md-guidance-eval-2026-07-15, fn-99 spec) bound `claude -p --bare` as the clean-room mechanism. On an OAuth/keychain login (no ANTHROPIC_API_KEY), `--bare` returns "Not logged in" - it authenticates STRICTLY via ANTHROPIC_API_KEY/apiKeyHelper and skips keychain reads. A fresh per-run CLAUDE_CONFIG_DIR also drops the login (auth state lives in the config dir, NOT at account level). Meanwhile a non-isolated `claude -p` from any scratch dir provably loads the user's global ~/.claude/CLAUDE.md (probe reported the owner block verbatim), confounding whatever guidance arm is under test.

## What Didn't Work
- `claude -p --bare` on OAuth-only machines: "Not logged in" (haiku + sonnet, claude 2.1.210).
- `CLAUDE_CONFIG_DIR=<fresh>`: also "Not logged in".

## Solution
Default config dir (keeps OAuth) + `--setting-sources project,local` (+ `--no-session-persistence`). Auth probe: returns OK. Leak probe: a planted project CLAUDE.md (unique codename) IS loaded; the global CLAUDE.md content (owner name/contact, workspace paths, tool conventions) is NOT. Residual: the account email remains visible (OAuth session identity) - document it, it carries no guidance content. Implemented in agent_docs/guidance-eval/runner.sh; probe transcripts in that README's threat model; fn-99 R4 amended accordingly.

## Prevention
Before trusting ANY claude-subprocess isolation recipe: run the auth probe (`claude -p "reply exactly OK" <flags>`) and the leak probe (planted project CLAUDE.md with a unique marker; ask the agent to enumerate its loaded instructions; require marker present + global content absent). Record both transcripts next to the eval results.
