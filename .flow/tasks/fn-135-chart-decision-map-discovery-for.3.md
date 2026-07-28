---
satisfies: [R11, R12, R13, R24, R25, R41, R45]
---
# fn-135-chart-decision-map-discovery-for.3 Build versioned briefing and capture handoff

## Description
### Objective

Implement the immutable briefing package and source-tagged capture handoff. Separate deterministic emission from agent judgment: chart proposes/clusters and obtains confirmation; flowctl validates and publishes the confirmed proposal.

### Exact files

- `plugins/flow-next/scripts/flowctl.py` — add briefing validation/emission/versioning and idempotent `chart link-spec`.
- `plugins/flow-next/skills/flow-next-capture/SKILL.md` — detect chart briefing inputs, preserve their source tags/assets, run normal read-back consent, and call link-spec only after each successful spec creation.
- `plugins/flow-next/skills/flow-next-capture/workflow.md` and `phases.md` — add the briefing ingestion/callback path at the existing evidence and write phases.
- `plugins/flow-next/tests/test_chart_briefing.py` — new completion, forced-draft, versioning, partial-capture, stale-link, and rollback suite.
- `plugins/flow-next/tests/test_capture_chart_handoff.py` — new prompt/workflow contract test.

### Investigation targets

- Reuse capture's source tagging, duplicate detection, read-back approval, `spec create`, and `spec set-plan` ownership around `flow-next-capture/SKILL.md:10-16,121-134`. Chart must never write `.flow/specs`.
- The proposal file is an agent-produced deterministic input: one or more clusters, one-line rationale per boundary, D-ID membership, and shared-context D-IDs. Flowctl validates complete/non-conflicting membership before publication.
- Store immutable briefing ids (`B1`, `B2`, ...). `--force` produces an explicitly draft briefing listing every open/claimed/parked item and leaves the chart open.
- Fingerprint normalized proposal plus chart revision. Identical retry returns the existing B-ID; changed proposal or later revision allocates the next B-ID.
- First non-draft briefing transitions `open -> done`. Done/abandoned charts reject mutation until `chart reopen --reason` records the transition and marks earlier briefings/spec links stale.
- `produced_specs[]` records `{briefing,spec,decisions,status}` idempotently. Capture decline records nothing. Partial multi-spec capture records only successes and can resume.
- Later supersession marks affected links stale; never rewrite a prior briefing or spec.

### Required behavior and examples

- A complete chart defaults to one proposed cluster. “Show me one spec versus two” may produce two clusters, but the skill must read back rationale and shared context before passing the proposal file to flowctl.
- `flowctl chart briefing fn-N --proposal-file proposal.json --json` refuses any open decision, including blocked/claimed, or parked question.
- A forced draft names unresolved items and cannot be treated by capture as ready without a fresh explicit read-back.
- If the user declines capture after reading B1, fn-N remains resumable and has no false `produced_specs[]` entry.
- If spec one succeeds and spec two fails, only the first link exists; rerun creates/links the second without duplicating the first.
- Repeating the same confirmed proposal on the same chart revision returns B1; a changed split after audited reopen becomes B2.

### Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_chart_briefing test_capture_chart_handoff -q
```

### Non-goals

- No silent clustering algorithm in flowctl.
- No automatic `ready` mutation and no direct chart-to-spec write.
## Acceptance
- Briefing eligibility checks all open/blocked/claimed decisions plus parked questions; empty frontier alone cannot pass.
- Confirmed proposals validate cluster coverage, rationale, shared context, and assets before immutable/versioned publication.
- Forced briefings are draft-only, list unresolved state, and leave the chart open.
- First non-draft briefing sets done; later mutation requires audited reopen and stales prior links. Identical briefing fingerprints reuse the B-ID, changed inputs allocate the next.
- Capture consumes briefings as source-tagged evidence, preserves normal read-back/duplicate handling, and never lets chart write a spec or set readiness.
- Capture decline and partial multi-spec failure remain resumable; `link-spec` is idempotent and later supersession marks affected links stale.
- Focused commands pass: `cd plugins/flow-next/tests && python3 -m unittest test_chart_briefing test_capture_chart_handoff -q`.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
