---
satisfies: [R2, R10, R12]
---
# fn-130-reached-path-skill-prompt-optimization.12 Gate Pilot backlog-only branches

## Description
Apply one conservative Pilot cold-branch extraction: move only backlog-only grammar/context behind the selected backlog route. Preserve verdict, strike, safety, receipt, failure, tracker, and autonomous conductor semantics at every consuming action site.

**Size:** S
**Files:** `plugins/flow-next/skills/flow-next-pilot/**`; existing Pilot optimization assets/tests; `optimization/reached-path/pilot-*`; corresponding Codex mirror.

### Approach
- Verify task input hashes match `V1/B1`; compare candidates only against `B1`.
- Move only backlog-only grammar/context into a direct reference selected by backlog mode.
- Keep common verdict/strike/safety instructions beside every phase that consumes them.
- Score the mutation independently; retain the candidate as a discard if any frozen grammar or terminal behavior changes.
- Recheck dormant fn-61 before edits; its verdict changes take precedence.

### Frozen fixtures
- ready normal; no-ready; backlog off; backlog on; blocked; deferred; strike escalation; failure; dry-run; tracker relations; autonomous restrictions.

### Investigation targets
**Required**
- `plugins/flow-next/skills/flow-next-pilot/SKILL.md:110-189` — backlog/verdict contract.
- `plugins/flow-next/tests/test_pilot_backlog_mirror_safety.py:84-390` — canonical/mirror safety matrix.
- fn-85 frozen Pilot conductor grammar.

**Optional**
- fn-61 Pilot/Land spec for overlapping files/semantics.

## Acceptance
- [ ] Task input hashes match `V1/B1`; Pilot has an independent `B1`/candidate ledger and every candidate can be kept or discarded without affecting Strategy or Make PR.
- [ ] Normal paths avoid backlog-only material; backlog paths retain complete selected backlog instructions.
- [ ] Verdict, strike, relation, receipt, dry-run, failure, tracker, and autonomous safety behavior match `B1` at all consuming action sites.
- [ ] Existing and new route assertions pass on canonical and Codex mirror; fn-61 status is rechecked.
- [ ] Reached-path improvement and every discard reason are recorded without claiming unmeasured wall-time gains.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
