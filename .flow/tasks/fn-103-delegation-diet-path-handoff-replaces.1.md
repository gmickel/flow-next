---
satisfies: [R1, R2, R3, R5]
---

## Description

The core surgery: codex-delegation.md sheds its composition layer, worker.md's delegation touchpoints go path-handoff, the R2 grep-gate machine-checks rail survival.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md`, `plugins/flow-next/agents/worker.md`, `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/docs/flowctl.md` (one line), codex mirror (regen)

1. **Grep-gate FIRST (R2):** before editing, record sha256 of the rail sections of codex-delegation.md (gates L63-256, invocation L259-340, launch/poll L342-423, classification/safety L500-668, circuit-breaker/ralph L670-877 - re-anchor exact boundaries at edit time). After all edits, assert: the load-bearing strings survive (`--ignore-user-config`, `--dangerously-bypass-approvals-and-sandbox`, `-s workspace-write`, `--output-schema`, `FLOW_DELEGATE_CODEX=1`, `rollback_and_disable`, `finish_locally`, `consecutive_failures`, `files_modified`, `git status --porcelain`) AND the kept rail sections hash-match except where the vocabulary sweep touched them (list; each deviation in evidence). Record the assertion commands + outcomes in evidence.
2. **Template swap (R1):** replace L473-499 (the 8-section composed template) with the fixed path-handoff template from the spec: read `.flow/tasks/<id>.md` + `.flow/specs/<spec>.md`; implement exactly that task; allowed-file list lifted from the task's Files line minus orchestrator-owned artifacts (mirror, `.flow/bin` dual-copies); constraints paragraph unchanged; verify clause WITH the exhaustive-tests sentence ("Where the task enumerates test cases, edge cases, or a fail-closed matrix, write ONE test per named case - exhaustive, never representative; a named case without a test is an incomplete implementation."); output contract unchanged. Filling it = 3 slots (task id, spec id, file list) - state that explicitly.
3. **Batching supersede (R3):** delete/replace L456-472 (unit selection, <=5 units) with one-run-per-task; `prompt-batch-1.md`/`result-batch-1.json` naming survives verbatim (n always 1).
4. **Vocabulary sweep (R3):** per-batch effort table KEPT (risk-keyed, works at n=1) but renamed per-run; phases.md L276 + L332 ("all units were trivial" -> "task ran standard"); worker.md Phase 6 return-bucket wording ~L460-470; docs/flowctl.md L688 delegateEffort entry.
5. **worker.md compose step (L136-142):** rewrite to fill-3-slots + one run per task. **R5 valve at the gate (L130-134):** if the task file does not name its files and acceptance, OR the post-filter allowed list is empty, do not delegate - implement in-session; no DELEGATION_* lines (existing standard bucket, counter untouched); phases.md's DELEGATE flags are provisional - worker owns the final call (add one clarifying sentence at phases.md's flag-injection site).
6. **Invocation argv byte-identical** - ralph-guard's is_canonical_codex_delegation predicate must keep passing; NO ralph-guard.py edit, NO RALPH_GUARD_VERSION bump. Verify by grepping the canonical invocation block unchanged.
7. sync-codex.sh x2, idempotent, guards green; full unittest suite green pre+post (gate diet applies - honor receipts, classify).

## Acceptance
- [ ] R1: fixed template in place, 3-slot fill, exhaustive-tests sentence verbatim
- [ ] R2: grep-gate assertions recorded in evidence, all rail strings + section hashes accounted for
- [ ] R3: batching superseded, vocabulary sweep complete (zero surviving "units were trivial"/"per-batch" outside historical notes), before/after line counts recorded
- [ ] R5 (worker side): valve prose at the gate incl. empty-allow-list clause + provisional-flags sentence in phases.md
- [ ] Suite green; mirror idempotent x2

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
