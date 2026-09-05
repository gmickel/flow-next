---
satisfies: [R1, R2, R3, R4]
---
# fn-224-refactorpython-remove-dead-paths-and.1 Review and simplify Python with regression evidence

## Description
Review core CLI, review dispatch, tracker integration, supporting tools, and test/evaluation infrastructure using GPT-6 Astra subagents. Implement only grounded deletions, simplifications, and reproduced fixes. Files: Python production code and focused tests; generated manifests/mirror only through generators. Record accepted/rejected findings and run focused suites plus python3 scripts/run_tests_parallel.py and uvx ruff@0.16.0 check .

## Acceptance
R1-R4 satisfied; Python changes preserve public contracts and prompt bytes, reproduced bugs have regression coverage, full repository checks pass, required generated artifacts are idempotent. G1/G2 apply.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
