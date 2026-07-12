---
satisfies: [R19]
---

## Description
Non-CI agentic eval harness: judgment-layer classification eval with rubric + provenance.

**Size:** S | **Files:** `optimization/prime/` (runner, rubric, expectation rows, README)

## Approach
- Pinned harness protocol (round 3): runner = `claude -p` headless (fallback `codex exec` when claude unavailable; unavailable-backend = skip with note, never fail); prompt assembled from classification.md judgment rules + the emitter's JSON for the fixture + a bounded fixture file listing; fixture roots ENFORCED-isolated, not just asserted (final review round): runner executes in a temporary cwd containing copied projections only, read-only/sandbox mode flags on the backend invocation, no network, no live-repo paths in env or prompt, minimal environment, explicit timeout + process-tree termination, post-run filesystem-diff assertion, and a malicious-fixture test proving the runner cannot read or modify a sentinel outside the fixture root; structured output captured via a JSON schema (five axes + confidence + would-ask list + playbook choice); per-run retries (1) and timeout; deterministic scorer compares against expectation rows; results land as `optimization/prime/results/<fixture>-<model>-<date>.json` with model/version/effort provenance; task 9 runs exactly `python3 optimization/prime/run_agentic_eval.py --all` (name pinned here).
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
