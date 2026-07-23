# Sealed P5 — no-code permit-intake architecture

This fixture was frozen before the Plan prompt candidate was authored. The
subject receives only this file plus the Plan prompt files. It never receives
`oracle.md`.

## Request

Plan a no-code permit-intake workflow for a small municipality. Residents
submit applications and attachments through Fillout. Airtable is the system of
record. Make validates submissions, routes them to Planning or Public Works,
and sends status notifications. Staff need an approval queue and an auditable
handoff between departments.

The plan must cover the architecture and implementation tasks, not implement
the workflow. Include a Mermaid diagram only if the Plan rules call for one.

## Frozen research bundle

- Fillout can create Airtable records and upload attachments, but attachment
  URLs should be copied into the system of record before temporary links
  expire.
- Airtable automations have run limits and weak cross-step error recovery.
  Use Make for validation, routing, retries, and notifications.
- Make scenarios should be idempotent. Use the Fillout submission ID as the
  external key and record the last successful stage in Airtable.
- Keep resident PII out of Make execution logs where possible. Store the
  minimum routing payload and link back to Airtable.
- Planning and Public Works use separate views but share one application
  status vocabulary: `submitted`, `needs-info`, `in-review`, `approved`,
  `rejected`.
- The audit trail must retain submission, routing, department decision, and
  notification timestamps.
- Pilot rollout: one permit type, five staff users, manual rollback to the
  current email intake for two weeks.

## Requirements

- R1: Capture a resident submission and attachments without duplicate
  applications when Fillout retries.
- R2: Route by permit type to the correct department queue.
- R3: Use one shared status vocabulary across both departments.
- R4: Record the four audit timestamps from the research bundle.
- R5: Protect resident PII in automation logs.
- R6: Pilot one permit type with an explicit rollback path.

## Branch matrix

Score the same planning judgment under these independent route inputs:

| Route | Off input | On input |
|---|---|---|
| Tracker | bridge inactive / `perEvent.plan` unset | bridge active / `perEvent.plan=push` |
| HTML | `artifacts.html.enabled=false` | `artifacts.html.enabled=true` |
| Review | review choice `none` | review choice `host` |
