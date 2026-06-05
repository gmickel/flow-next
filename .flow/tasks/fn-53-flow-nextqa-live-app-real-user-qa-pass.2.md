---
satisfies: [R1, R4, R5, R6]
---

## Description
Add the findings + verdict half of the skill: structured P0/P1/P2 findings with evidence, the YES/NO verdict-as-receipt (with the four-outcome matrix), and the bug-memory feed with dedup. The verdict must rest on captured evidence, never on agent narration.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-qa/workflow.md` (findings + verdict phases), `plugins/flow-next/skills/flow-next-qa/references/bug-filing.md`

## Approach
- **Findings (R4):** each finding carries persona, steps-to-reproduce (runnable cold), expected vs actual, severity (P0/P1/P2), and evidence pointers (console verbatim last ~30 lines, screenshot path under `.flow/tmp/`, full URL incl. query string, server/DB row for write side-effects). File immediately on FAIL. Reproduce-before-file (twice) to defend against agentic non-determinism.
- **Verdict receipt (R6):** write the receipt JSON **directly** (the make-pr pattern — QA has no backend subprocess, so NOT the impl-review `flowctl <backend> validate --receipt` path). Schema (see the spec's Architecture → Receipt schema): `type: qa_verdict`, `id`, `mode`, `verdict ∈ {SHIP,NEEDS_WORK,MAJOR_RETHINK}`, `qa_outcome ∈ {SHIP,NEEDS_WORK,NA,BLOCKED}`, `blocked_reason?`/`na_reason?`, `open_p0p1[]`, `timestamp`. Path = `REVIEW_RECEIPT_PATH`/`--receipt` else `.flow/review-receipts/qa-<spec-id>.json` (committed); `mkdir -p` the parent.
- **Four-outcome matrix → enum projection:** the Ralph guard validates ONLY `verdict ∈ {SHIP,NEEDS_WORK,MAJOR_RETHINK}`, so the four outcomes live in `qa_outcome` and `verdict` is the projection — `SHIP` (all pass, zero open P0/P1, coverage complete) →`SHIP`; `NEEDS_WORK` (any open P0/P1 OR incomplete R-ID coverage) →`NEEDS_WORK`; **`BLOCKED`** (no live deploy/driver) →`NEEDS_WORK`; **`NA`** (no driveable user-visible AC) →`SHIP` with `na_reason`. Single open P0 = NO; don't downgrade P0→P1 to avoid stopping; BLOCKED ≠ FAIL.
- **Bug-memory feed (R5):** `flowctl memory add --track bug --category {ui|runtime-errors|integration|...}` with the built-in overlap check (NEVER `--no-overlap-check`); surface "matches existing entry X" instead of re-filing; no-op cleanly when `memory.enabled` is false. Note the promote-to-spec path (compose from `spec create`/`capture`).
- **R1 completion:** PASS is gated on captured evidence; reading source to assert PASS is forbidden.

## Investigation targets
**Required:**
- `plugins/flow-next/scripts/hooks/ralph-guard.py:331` (`validate_receipt_data`), `:616` (`parse_receipt_path`) — receipt validation + the `SHIP/NEEDS_WORK/MAJOR_RETHINK` enum
- `plugins/flow-next/docs/flowctl.md:981-1007` — receipt schema `{type,id,mode,verdict,...}`
- `plugins/flow-next/docs/memory-schema.md:27-41, 86-105` — bug track schema + `memory add` overlap dedup
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md` — direct receipt-write + R-ID-table pattern

**Optional:**
- `~/repos/rayfernando-skills/plugins/running-bug-review-board/skills/running-bug-review-board/references/bug-filing.md` — evidence-rule + taxonomy source (lean borrow)

## Key context
- `.flow/review-receipts/` is committed; `.flow/tmp/` is gitignored (evidence home). There is NO generic `flowctl receipt write` helper — compose the JSON.
- GitHub Eng: agent self-reported success ≈82% vs structural evidence ≈100% — so the verdict MUST cite captured artifacts, not narration.

## Acceptance
- [ ] Findings are structured P0/P1/P2 with persona, repro, expected/actual, and evidence pointers; filed immediately on FAIL
- [ ] Verdict receipt (`type: qa_verdict`) written to the caller path or `.flow/review-receipts/qa-<spec-id>.json`; carries `qa_outcome` + the enum-projected `verdict`; passes `ralph-guard` validation
- [ ] Four-outcome matrix enforced via `qa_outcome` (SHIP / NEEDS_WORK / NA / BLOCKED) with the documented `verdict` projection (BLOCKED→NEEDS_WORK, NA→SHIP); incomplete coverage = NO; single P0 = NO; BLOCKED ≠ FAIL
- [ ] A test (`test_qa_receipt.py`) with **four receipt fixtures** (one per `qa_outcome`) asserts each projects to a `verdict` that passes `ralph-guard` `validate_receipt_data`; hermetic, Windows-portable
- [ ] Findings feed `memory add --track bug` WITH overlap dedup; no-op when memory disabled
- [ ] PASS is evidence-gated; source-only PASS is forbidden (R1)

## Done summary
Filled the /flow-next:qa skill's Phase 5 (file) and Phase 6 (verdict): structured P0/P1/P2 findings (persona, cold repro, expected-vs-actual, evidence pointers under .flow/tmp/, reproduce-twice) feeding `memory add --track bug` with overlap dedup and a clean no-op when memory is disabled; a `type: qa_verdict` receipt carrying the four-outcome `qa_outcome` (SHIP/NEEDS_WORK/NA/BLOCKED) projected to the ralph-guard verdict enum (BLOCKED->NEEDS_WORK, NA->SHIP), written JSON-safely via python3/json.dump. Added references/bug-filing.md (lean BRB-discipline borrow) and a hermetic, Windows-portable test_qa_receipt.py with four fixtures asserting each outcome projects to a guard-valid verdict (validate_receipt_data + validate_receipt_file). impl-review (RP) SHIP after fixing a heredoc JSON-escaping bug + empty-mode field.
## Evidence
- Commits: d119e8d, f262f72, 4edaccbcce8ddf9ddc1fb5781da62db562115e9a
- Tests: python3 -m unittest plugins.flow-next.tests.test_qa_receipt -q (12 tests OK), python3 -m unittest discover -s plugins/flow-next/tests -q (986 tests OK, 2 skipped), end-to-end: workflow Phase 6.3 python3 json.dump writer produces valid JSON for all 4 qa_outcomes incl. hostile blocked_reason (quote+backslash+newline); validates via ralph-guard
- PRs: