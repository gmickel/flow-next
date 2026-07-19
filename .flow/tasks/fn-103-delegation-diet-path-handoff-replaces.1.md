---
satisfies: [R1, R2, R3, R5]
---

## Description

The core surgery: codex-delegation.md sheds its composition layer, worker.md's delegation touchpoints go path-handoff, the R2 grep-gate machine-checks rail survival.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md`, `plugins/flow-next/agents/worker.md`, `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/docs/flowctl.md` (one line), `plugins/flow-next/tests/test_codex_delegation_classify.py` (prose-contract assertions), codex mirror (regen)

1. **Grep-gate FIRST (R2), machine-valid:** hash only IMMUTABLE rail fragments - the fenced `codex exec` invocation block, the result-schema JSON block, the classify-result action table rows, the rollback command block, the ralph-guard amendment block. sha256 each fragment pre-edit; post-edit the same extraction must hash-match EXACTLY (zero unaccounted diff inside protected fragments). Prose OUTSIDE the fragments may change only via the explicit substitution allowlist: `per-batch`->`per-run`, `batch's`->`run's`, `all units were trivial`->`task ran standard`, plus the two deleted sections (template L473-499, batching L456-472). Load-bearing string assertions on the whole file: `--ignore-user-config`, `--dangerously-bypass-approvals-and-sandbox`, `-s workspace-write`, `--output-schema`, `FLOW_DELEGATE_CODEX=1`, `rollback_and_disable`, `finish_locally`, `consecutive_failures`, `files_modified`, `git status --porcelain`. Record commands + outcomes in evidence.
2. **Template swap (R1):** replace L473-499 (the 8-section composed template) with the fixed path-handoff template from the spec: read `.flow/tasks/<id>.md` + `.flow/specs/<spec>.md`; implement exactly that task; allowed-file list lifted from the task's Files line minus orchestrator-owned artifacts (mirror, `.flow/bin` dual-copies); constraints paragraph unchanged; verify clause WITH the exhaustive-tests sentence ("Where the task enumerates test cases, edge cases, or a fail-closed matrix, write ONE test per named case - exhaustive, never representative; a named case without a test is an incomplete implementation."); output contract unchanged. Filling it = 3 slots (task id, spec id, file list) - state that explicitly.
3. **Batching supersede (R3):** delete/replace L456-472 (unit selection, <=5 units) with one-run-per-task; `prompt-batch-1.md`/`result-batch-1.json` naming survives verbatim (n always 1).
4. **Vocabulary sweep (R3), EXACT scope:** the sweep covers THIS task's file set only - codex-delegation.md (effort table KEPT, risk-keyed, renamed per-run), worker.md (compose step + Phase 6 return bucket), phases.md (L276 escalation comment + L332 trivial-bucket), docs/flowctl.md L688. EXEMPT: flowctl.py (zero code changes stands - its inert `per-batch` comments are out of scope), historical CHANGELOG/memory entries. The repo-wide final grep gate lives in task .2 (which owns the remaining docs); this task's acceptance greps run over its own file set.
5. **worker.md compose step (L136-142):** rewrite to fill-3-slots + one run per task. **R5 valve at the gate (L130-134):** if the task file does not name its files and acceptance, OR the post-filter allowed list is empty, do not delegate - implement in-session; no DELEGATION_* lines (existing standard bucket, counter untouched); phases.md's DELEGATE flags are provisional - worker owns the final call (add one clarifying sentence at phases.md's flag-injection site).
6. **Invocation argv byte-identical** - ralph-guard's is_canonical_codex_delegation predicate must keep passing; NO ralph-guard.py edit, NO RALPH_GUARD_VERSION bump. Verify by grepping the canonical invocation block unchanged.
7. **Prose-contract tests updated:** `test_codex_delegation_classify.py` currently pins the 8-tag template (`<patterns>` at ~L639), the section heading "Orchestration split / batching / ..." (~L627), and per-task max-5 batching (~L655). Rewrite those assertions to pin the NEW contract: fixed 3-slot template present, exhaustive-tests sentence verbatim, one-run-per-task stated, `<patterns>`/`<approach>` ABSENT, R5 valve present in worker.md, provisional-flags sentence in phases.md, canonical invocation block unchanged. Keep every classify-result/rollback test untouched.
8. sync-codex.sh x2, idempotent, guards green; full unittest suite green pre+post (gate diet applies - honor receipts, classify).

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
