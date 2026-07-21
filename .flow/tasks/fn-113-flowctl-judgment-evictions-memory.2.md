# fn-113-flowctl-judgment-evictions-memory.2 Memory-add overlap eviction (caller decides, --update explicit)

## Description
Memory-add overlap auto-routing eviction: caller decides, flowctl reports.

**Size:** M
**Files:** both flowctl.py copies, plugins/flow-next/tests/test_memory_add.py, caller skill prose (capture, qa, make-pr, interview, audit, worker)

### Approach

- Current behavior (locate by symbol; audit refs flowctl.py:8522/8571/9077-9090): memory add computes a 0-4 token/tag overlap score and score>=3 silently UPDATES the existing entry. Change: memory add ALWAYS creates unless the caller passes explicit `--update <id>`; the response always emits `matches` (with scores, as retrieval signal) so the CALLING SKILL decides update-vs-create. Drop the auto-update branch; keep the scoring as the matches signal.
- `--update <id>`: validates the id exists, updates that entry (same merge semantics the auto-branch used), still emits matches.
- Re-pin test_memory_add.py overlap cases (~25 refs) to the new contract: high-overlap input WITHOUT --update creates a new entry AND surfaces the match; --update path updates.
- Caller skills: wherever prose said "memory add may auto-merge/dedupe", reword to the new contract - the skill reads `matches` and either re-runs with --update or accepts the create. Keep edits minimal and grep-driven; list every file you touched.
- Dual-copy; sync-codex x2. NO git commands, no em dashes.

### Acceptance

- [ ] memory add never mutates an existing entry without explicit --update <id>; matches always emitted with scores
- [ ] test_memory_add.py re-pinned and green; focused: --pattern "test_memory*.py"
- [ ] Caller skill prose updated (list in summary); sync-codex idempotent; dual-copy identical

## Acceptance
- [ ] TBD

## Done summary
memory add never mutates without explicit --update <id>: auto-update branch evicted, overlap scoring retained as the matches retrieval signal (always emitted, best-first, with scores), --update resolves the id and applies the same merge semantics the auto-branch used (tag union, ## Update section, last_updated). Moderate-overlap related_to auto-link kept - additive metadata, not the judged mutation the spec evicts. test_memory_add.py re-pinned to 24 tests; memory suite 8 files / 138 tests green. Caller prose: worker Phase 4.5, qa workflow + bug-filing, make-pr failure wording, memory-migrate phases + workflow (idempotency now matches + --update); capture/interview/audit audited - no auto-merge prose existed. Host review: live-exercised all three paths in a scratch repo (created / created-with-matches / updated with ## Update section); delegate doubts accepted with reasons (orphan-sibling risk inherent to caller-decides, matches is the mitigation; --update without category guard = explicit caller intent). Transport note: implemented via the direct grok-4.5 CLI bridge (cursor quota exhausted at .1; same model family+tier, reasoning-effort high). Full parallel suite green; dual-copy identical; sync-codex x2.
## Evidence
- Commits: 8e7dd55f864ca006b303ee5805317ba1a8dcc71c
- Tests: python3 scripts/run_tests_parallel.py (full suite green, see log), test_memory*.py 8 files / 138 tests green, host live exercise: create -> overlap-create+matches -> explicit update (scratch repo)
- PRs: