---
satisfies: [R8, R9]
---

## Description

`flowctl anchor <task-id> [--json|--md]` — the single-call worker anchor bundle — plus its two proofs: the deterministic superset test and the comprehension-equivalence eval (`optimization/worker-anchor/`). Depends on fn-83.1 (same flowctl.py file + shared argparse registration block — sequential to avoid merge churn).

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_anchor_bundle.py` (new), `optimization/worker-anchor/` (new)

## Approach

- **Bundle content (verbatim RAW OUTPUTS, no filtering, no truncation):** the exact outputs of every command worker.md Phase 1 currently runs — `show <TASK_ID> --json` (raw JSON), `cat <TASK_ID>`, `show <SPEC_ID> --json` (raw JSON), `cat <SPEC_ID>` (FULL body), `git status` + `git log -5 --oneline` + branch, `config get memory.enabled`, `glossary list --json`, `memory list` index (when enabled) — plus dependency tasks' ids/titles/statuses/done-summaries. Superset test compares these EXACT artifacts, not paraphrases. Clone/refactor the section-assembly + helpers from `cmd_spec_export_cognitive_aid` (flowctl.py:14845-15025) and the fn-79 fence-aware extractors — do NOT re-implement parsing.
- `--md` = worker-facing render (clear section headers, same order every run); `--json` = machine form. Pure read; deterministic ordering; slug/short id resolution via the existing resolver.
- **Superset test (deterministic):** fixture spec+task; assert every artifact worker.md Phase 1 currently reads (worker.md:21-68 — show/cat task+spec output fields, git status/log, memory.enabled, glossary list, memory list) is present verbatim (or strictly richer) in the bundle. This test is the guardrail future edits run against.
- **Comprehension-equivalence eval (`optimization/worker-anchor/`):** ≥3 frozen real tasks (varied size — pick from fn-64/fn-74/fn-81 history, freeze copies); K binary anchor-comprehension questions per task (state the acceptance criteria ids; name the files to touch; state the boundaries; state dep status; name relevant requirement contents; ≥1 question answerable ONLY from a spec section OUTSIDE the task's satisfies list). Committed ANSWER KEY; grading against the key (bundle-vs-statusquo agreement is NOT the metric — both-wrong must fail). Two runs per task per grading subagent: (a) given ONLY the bundle `--md`, (b) given ONLY the status-quo read outputs. Fixed recorded grading model. Merge gate: bundle score ≥ status-quo AND ≥ key threshold on every question set. Standard harness layout (README, evals, results.tsv) per optimization/ conventions.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:14845-15025` — export section assembly to clone
- `plugins/flow-next/agents/worker.md:21-111` — Phase 1 + 1.5 read list (the superset target)
- `plugins/flow-next/scripts/flowctl.py:5141-5300` — fence-aware helpers
- `optimization/capture/README.md` — harness layout conventions

## Key context

Bundle is a FLOOR: worker keeps memory keyword-search and read-more freedom (worker.md wiring is fn-83.4 — this task ships the command + proofs only). Never host-precomputed: the command exists for the worker to call at its own Phase 1 (point-in-time semantics unchanged).

## Acceptance

- [ ] `flowctl anchor` implemented (full-body verbatim bundle, deterministic order, --json/--md), pure stdlib 3.8+
- [ ] Superset test green and committed as a standing guardrail
- [ ] Comprehension eval green: answer-key graded, ≥3 frozen tasks, non-satisfies question included, bundle ≥ status-quo AND ≥ threshold; harness committed with results.tsv rows
- [ ] Full pytest + smoke green

## Done summary
Implemented `flowctl anchor <task-id> [--json|--md]` — the single-call worker anchor bundle delivering the verbatim outputs of every worker Phase-1 re-anchor read (show/cat task+spec, git status/log/branch, memory.enabled, glossary, memory index) plus dependency ids/titles/statuses/done-summaries, verbatim-by-construction via captured production cmd_* stdout. Shipped both proofs: the deterministic superset test (tests/test_anchor_bundle.py, byte-for-byte vs the production CLI wire form) and the comprehension-equivalence eval (optimization/worker-anchor/: 3 frozen real tasks S/M/L, 7 key-graded binary questions each incl. a non-satisfies-section question, recorded model claude-sonnet-5 — MERGE GATE PASS, bundle 7/7 ≥ statusquo 7/7 on every set). RP impl-review: SHIP (first pass, 0 findings).
## Evidence
- Commits: 792dda15fca9969ccb04ed3580f48b5f519c05d4
- Tests: uv run --with pytest python -m pytest plugins/flow-next/tests/ -q (1512 passed, 2 skipped, 256 subtests), uv run --with pytest python -m pytest plugins/flow-next/tests/test_anchor_bundle.py -q (21 passed, 20 subtests), (cd $(mktemp -d) && bash plugins/flow-next/scripts/smoke_test.sh) (138 passed, 0 failed), python3 optimization/worker-anchor/run_eval.py (MERGE GATE PASS: bundle 7/7 >= statusquo 7/7 on all 3 sets, model claude-sonnet-5)
- PRs: