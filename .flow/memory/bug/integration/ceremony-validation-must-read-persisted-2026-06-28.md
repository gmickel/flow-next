---
title: "Ceremony validation must read PERSISTED config, not re-race env; don't collapse "
date: "2026-06-28"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-tracker-sync/steps.md
tags: [tracker-sync, jira, fn-70, discovery-ceremony, readyState, persisted-config, authScheme, rp-review]
problem_type: integration
symptoms: Jira readiness re-raced env for auth + wrote unvalidated readyState when creds present but baseUrl/projectKey missing
root_cause: Validation snippet re-derived a once-persisted decision at runtime + collapsed spec-first-floor with config-error into one accept-on-faith branch
resolution_type: fix
related_to: [bug/integration/adding-a-tracker-to-tracker-sync-sweep-2026-06-28, bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17, bug/integration/markerstruct-field-semantics-must-2026-06-27, bug/integration/set-tracker-id-rejected-github-n-2026-06-03, bug/integration/trackers-auto-linkify-issue-key-2026-06-03]
---

## Problem
A discovery-ceremony bash snippet (host-agent prose in steps.md) that VALIDATES a
just-persisted config value re-derived the transport shape at runtime instead of
reading the values the ceremony had just persisted. The Jira readiness branch (1)
re-raced env (`if [ -n "$JIRA_PAT" ] ... else basic`) instead of branching on the
persisted `tracker.perTracker.authScheme`, violating R5's "decided once at
ceremony, persisted, not re-inferred"; and (2) collapsed two distinct outcomes
into one `else`: "no creds (spec-first floor)" and "creds present but
baseUrl/projectKey unconfigured (config error)" both hit the accept-on-faith path,
so a config gap silently wrote an UNVALIDATED `tracker.readyState` that empties the
promoted lane.

## What Didn't Work
First fix only addressed the env re-race (read persisted authScheme, branch on
cloud-basic/bearer-pat). It kept a single `if [creds AND base AND projKey]` ...
`else READY_OK=1`, which the reviewer caught: creds present + missing config still
fell through to the faith path and wrote an unvalidated value.

## Solution
Three-way branch + a separate write-gate (steps.md Jira readiness):
- `CRED_OK=0` (no creds for the persisted scheme) → spec-first floor, faith/skip.
- creds present BUT baseUrl/projectKey missing → config error, surface + NEVER write.
- creds + config present → validate the status against the project's statuses.
The `config set tracker.readyState` is gated on BOTH `READY_OK` && `READY_WRITE`,
and the config-error path sets `READY_WRITE=0`, so an unvalidated value can never
persist. Resolution mirrors runtime: `baseUrl = JIRA_BASE_URL || config`,
projectKey/authScheme/apiVersion/sslVerify from config, creds from env per scheme.

## Prevention
- When a ceremony PERSISTS a decision (auth scheme, transport, api version), any
  later validation/use in the SAME prose must READ the persisted value, never
  re-probe env/state — the persist exists precisely to stop re-racing. Grep the
  snippet for `if [ -n "$ENV_VAR" ]` shapes that duplicate a decided config key.
- A validation gate must not collapse "cannot validate (floor)" with "should
  validate but config is broken". Enumerate the outcomes; gate the write on an
  explicit "we actually validated" flag, not the absence of an error.
- For a multi-tracker ceremony, mirror the runtime resolution order (`env > config`)
  in the validation snippet so config-first setups are actually exercised.
