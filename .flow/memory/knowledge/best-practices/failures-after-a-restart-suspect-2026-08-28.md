---
title: "Failures after a restart: suspect persistent state before code"
date: "2026-08-28"
track: knowledge
category: best-practices
module: .flow
tags: [fn-208, debugging, persistent-state, state-validation]
applies_when: "Failures after a restart: suspect persistent state before code"
---

## Problem
A behavior that worked before a restart fails after one, and the instinct is to bisect code. In this repo the code rarely changed across the restart - the state on disk did.

## Solution
When a failure appears after a restart, resume, or new session, suspect persistent state before code: config files, caches, locks, serialized state (`.flow/tmp/*`, ledgers, receipts, snapshot files). Clear or inspect the suspect state first; if clearing it restores behavior, the fix is state validation at read time (schema check, staleness check, ownership check), not a code change at the failure site.

## Prevention
Any component that persists state across sessions validates it on load. This repo is unusually disk-stateful (ledgers, claims, receipts, tmp snapshots), so "worked yesterday, fails today, code unchanged" is a state-shaped symptom by default.
