---
title: A new create input must reach the create-first retry key and record
date: "2026-11-16"
track: bug
category: integration
module: plugins/flow-next/scripts/flowctl_tracker/lifecycle/verbs.py
tags: [tracker, create-first, retry-key, idempotency]
problem_type: integration
symptoms: retry with the same title and body under another parent linked the earlier issue
root_cause: "retry identity hashed type, title and body only; put dropped the stored input"
resolution_type: fix
---

## Problem
Adding an optional creation input (a parent issue) to tracker create-first left the retry identity unchanged. The create-first key hashes type, title and body only, so the same work captured under a different parent resolved to the earlier recovery record, and both `tracker create-first` and the skill's `sync create-first-get` recovery path linked an issue created under the wrong parent. `sync create-first-put` also rewrote the record from its arguments and dropped the input the verb had stored.

## What Didn't Work
A mismatch refusal inside `tracker create-first` alone: the documented recovery path reads the record through `sync create-first-get` and links the hit without calling the verb, so the check never ran there.

## Solution
Fold the new input into the key itself (appended only when present, so existing keys are unchanged) in both key implementations, expose it on `sync create-first-key`, keep the verb's mismatch refusal as a backstop, and make `create-first-put` preserve the recorded value like it preserves `specId`.

## Prevention
When a create input changes what gets created, ask what identifies a retry of that create: every key, record and reader of the recovery record (verb, get/put helpers, skill prose) must agree. Test the same content under two values of the new input and assert two keys.
