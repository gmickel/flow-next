---
satisfies: [R11, R12, R13, R24, R25, R41, R45, R49, R50, R51]
---
# fn-135-chart-decision-map-discovery-for.3 Build versioned briefing and capture handoff

## Description
### Objective

Implement the immutable briefing package and attributable capture handoff. Separate deterministic emission from agent judgment: chart proposes/clusters and obtains confirmation; flowctl validates and publishes the confirmed proposal. Keep chart/B-ID/cluster/D-ID evidence provenance distinct from acceptance-criterion author tags.

### Exact files

- `plugins/flow-next/scripts/flowctl.py` — add briefing validation/emission/versioning and idempotent `chart link-spec`.
- `plugins/flow-next/skills/flow-next-capture/SKILL.md` — detect chart briefing inputs, preserve chart/B-ID/cluster/D-ID evidence and approved asset references, run normal read-back consent, tag only newly authored acceptance criteria under the existing capture contract, and call link-spec only after each successful spec creation.
- `plugins/flow-next/skills/flow-next-capture/workflow.md` and `phases.md` — add the briefing ingestion/callback and retry-recovery path at the existing evidence and write phases.
- `plugins/flow-next/tests/test_chart_briefing.py` — new completion, forced-draft, versioning, partial-capture, stale-link, shared-context, rollback, and create-before-link recovery suite.
- `plugins/flow-next/tests/test_capture_chart_handoff.py` — new prompt/workflow contract test covering provenance separation and fn-148 non-preemption.

### Investigation targets

- Reuse capture's acceptance-criterion source tagging, duplicate detection, read-back approval, `spec create`, and `spec set-plan` ownership around `flow-next-capture/SKILL.md:10-16,121-134`. Chart must never write `.flow/specs`.
- Re-read landed fn-147 before editing capture/interview-adjacent prose. Its four tags describe who grounded a newly written acceptance criterion; never apply them to chart facts, D-ID records, assets, or briefing evidence, and never retag an existing criterion.
- Re-read fn-148's final report and the current spec template before implementation. Adopt verified/inferred fact guidance only if the preregistered result was CONFIRMED, the human approved its ready-to-apply diff, and that diff has landed. A planned, null, or inconclusive outcome changes nothing in this task.
- The proposal file is an agent-produced deterministic input: one or more clusters, one-line rationale per boundary, D-ID membership, and shared-context D-IDs. Flowctl validates complete/non-conflicting membership before publication.
- Store immutable briefing ids (`B1`, `B2`, ...). `--force` produces an explicitly draft briefing listing every open/claimed/parked item and leaves the chart open.
- Fingerprint normalized proposal plus chart revision. Identical retry returns the existing B-ID; changed proposal or later revision allocates the next B-ID.
- First non-draft briefing transitions `open -> done`. Done/abandoned charts reject mutation until `chart reopen --reason` records the transition and marks earlier briefings/spec links stale.
- `produced_specs[]` records a stable `{briefing,cluster,spec,decisions,status}` identity idempotently. Capture decline records nothing. Partial multi-spec capture records only successes and can resume.
- Journal the handoff across `spec create`, `spec set-plan`, and `chart link-spec`, or provide an equivalent durable retry key. A retry after interruption discovers and links the already-created spec for that B-ID/cluster rather than minting another.
- Ordinary capture refuses draft or stale B-IDs. An explicit risk override names unresolved/invalidated D-IDs and requires read-back; it never converts a forced draft into a final briefing.
- Later supersession marks affected links stale; never rewrite a prior briefing or spec.

### Required behavior and examples

- A complete chart defaults to one proposed cluster. “Show me one spec versus two” may produce two clusters, but the skill must read back rationale and shared context before passing the proposal file to flowctl.
- `flowctl chart briefing fn-N --proposal-file proposal.json --json` refuses any open decision, including blocked/claimed, or parked question.
- A forced draft names unresolved items and cannot be treated by capture as ready without a fresh explicit read-back.
- A stale B-ID is rejected by default; an override read-back names the superseding D-IDs and leaves the stale state visible in the resulting provenance.
- If the user declines capture after reading B1, fn-N remains resumable and has no false `produced_specs[]` entry.
- If spec one succeeds and spec two fails, only the first link exists; rerun creates/links the second without duplicating the first.
- If the process stops after `spec create` or `spec set-plan` but before `chart link-spec`, retry locates and links that same spec using the B-ID/cluster identity.
- A D-ID shared by two clusters is preserved as shared context in both handoffs but becomes an acceptance requirement only where capture's read-back confirms the target spec needs that guarantee.
- Repeating the same confirmed proposal on the same chart revision returns B1; a changed split after audited reopen becomes B2.

### Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_chart_briefing test_capture_chart_handoff -q
```

### Non-goals

- No silent clustering algorithm in flowctl.
- No automatic `ready` mutation and no direct chart-to-spec write.
- No chart fact/decision source-tag grammar and no unapproved fn-148 intervention.
## Acceptance
- Briefing eligibility checks all open/blocked/claimed decisions plus parked questions; empty frontier alone cannot pass.
- Confirmed proposals validate cluster coverage, rationale, shared context, and assets before immutable/versioned publication.
- Forced briefings are draft-only, list unresolved state, and leave the chart open.
- First non-draft briefing sets done; later mutation requires audited reopen and stales prior links. Identical briefing fingerprints reuse the B-ID, changed inputs allocate the next.
- Capture preserves chart/B-ID/cluster/D-ID evidence references, then applies the settled four-tag grammar only to acceptance criteria it newly authors; existing criteria are never retagged and D-ID evidence is not relabelled as `[user]`.
- Draft/stale admission fails closed by default and explicit overrides read back the exact risk without promoting a forced draft.
- Capture decline, create-before-link interruption, and partial multi-spec failure remain resumable; stable handoff identity prevents duplicate specs, `link-spec` is idempotent, and later supersession marks affected links stale.
- Shared-context D-IDs remain attributable without silently duplicating acceptance requirements across output specs.
- No verified/inferred fact or decision grammar is introduced unless a CONFIRMED, human-approved fn-148 change has already landed.
- Focused commands pass: `cd plugins/flow-next/tests && python3 -m unittest test_chart_briefing test_capture_chart_handoff -q`.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
