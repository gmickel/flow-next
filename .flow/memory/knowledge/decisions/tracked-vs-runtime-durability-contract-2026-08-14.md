---
title: "Tracked-vs-runtime durability contract - done crosses it, validate respects it"
date: "2026-08-14"
track: knowledge
category: decisions
module: plugins/flow-next/scripts/flowctl.py
tags: [durability, flow-state, status-source, validate, fn-192]
applies_when: "Tracked-vs-runtime durability contract - done crosses it, validate respects it"
decision_status: accepted
related_to: [knowledge/decisions/review-stall-detection-reads-resolution-2026-08-05]
---

Tracked files (.flow/specs, .flow/tasks) hold definition + narrative receipts; runtime state (git common-dir) holds lifecycle status and never travels with git. `flowctl done` is the ONE command that writes both classes in a single call - the receipt is tracked, the status is runtime. Encoded in fn-192: validate downgrades committed-snapshot status mismatches to warnings unless the snapshot carries real progress markers (committed_status_is_authoritative - content-based, because key-presence cannot distinguish legacy repos from fresh clones: RUNTIME_FIELDS keys exist in every modern sidecar); done/block report modified_paths and warn when the receipt dirties a tracked file. Never move state between durability classes; never stage/commit from flowctl (--stage/--amend rejected: index races across wave workers sharing a common dir, amend re-orphans the just-recorded evidence SHA).
