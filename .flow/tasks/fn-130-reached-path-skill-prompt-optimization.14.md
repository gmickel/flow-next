# fn-130-reached-path-skill-prompt-optimization.14 Close completion-review evidence gaps

## Description
Close the three completion-review evidence gaps without changing shipped skill
behavior: retain authenticated Prime baseline/candidate outcomes, run the Plan
Review risky/clean/user-edited corpus through a real backend, and execute paired
B1/candidate Plan emissions including the sealed holdout.

## Acceptance
- [ ] Prime retains sanitized, authenticated, nonzero-usage B1 and candidate results for all seven fixtures.
- [ ] Plan Review retains real-backend risky, clean, and user-edited baseline/candidate verdict evidence.
- [ ] Plan retains paired B1/candidate P1–P5 emissions and scored zero-loss results.
- [ ] Evidence records model/CLI/date/source hashes and keeps answer keys out of subject prompts.
- [ ] Fleet evidence and optimization logs point to the durable artifacts without overstating proof.
- [ ] Focused and full gates pass before re-review.

## Quick commands

```bash
python3 optimization/prime/run_agentic_eval.py --self-test
python3 optimization/reached-path/plan_review_real_eval.py --help
python3 optimization/plan/run_fn130_agentic_eval.py --help
python3 -m unittest -q test_fn130_evidence_harnesses test_prime_eval test_reached_path_harness test_review_prompt_template_parity
python3 scripts/run_tests_parallel.py
```

## Done summary
Retained authenticated B1/candidate Prime evidence, real-backend Plan Review corpus verdicts, and paired Plan emissions with independent scoring; added fail-closed harness regressions and updated closure ledgers.
## Evidence
- Commits: 89af4a78
- Tests: python3 -m unittest -q test_fn130_evidence_harnesses test_prime_eval test_reached_path_harness test_review_prompt_template_parity, python3 scripts/run_tests_parallel.py (2291 run, 3 skipped, 0 failures/errors), bash /Users/gordon/work/flow-next/plugins/flow-next/scripts/smoke_test.sh from /tmp (136 passed, 0 failed), scripts/sync-codex.sh twice (28 skills, 22 agents, idempotent)
- PRs: