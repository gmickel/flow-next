---
satisfies: [R19]
---

## Description
Non-CI agentic eval harness: judgment-layer classification eval with rubric + provenance.

**Size:** S | **Files:** `optimization/prime/` (runner, rubric, expectation rows, README)

## Approach
- Pinned harness protocol (round 3): runner = `claude -p` headless (fallback `codex exec` when claude unavailable; unavailable-backend = skip with note, never fail); prompt assembled from classification.md judgment rules + the emitter's JSON for the fixture + a bounded fixture file listing; fixture roots exposed via tmpdir paths in the prompt (model never touches the live workspace); structured output captured via a JSON schema (five axes + confidence + would-ask list + playbook choice); per-run retries (1) and timeout; deterministic scorer compares against expectation rows; results land as `optimization/prime/results/<fixture>-<model>-<date>.json` with model/version/effort provenance; task 9 runs exactly `python3 optimization/prime/run_agentic_eval.py --all` (name pinned here).
- Define: the runner invocation, model/version provenance capture, the pass rubric, and the blocking threshold (what must hold before ship - consumed by task 9).
- Real-repo baselines: sanitized metadata snapshots committed as fixture projections (never live-repo CI dependencies); provenance recorded per run.

## Key context
- Never claim prose-contract tests prove judgment (round-2 finding); this harness is the judgment oracle.

## Acceptance
- [ ] Runner + rubric + blocking threshold documented and executable locally
- [ ] Provenance (model/version/date) recorded in every result file
- [ ] Real-repo expectations run from committed sanitized snapshots, not live paths

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
