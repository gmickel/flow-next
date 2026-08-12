---
satisfies: [R4, R5]
---
# fn-187-codex-reviews-persona-override-project.3 Honest no-verdict classification + actionable terminal message

## Description
In plugins/flow-next/scripts/flowctl.py: (1) R4 - fix the failure-class ladders so an exit-0, non-empty, no-verdict run classes as missing_verdict even when the reviewer's own output contains the word 'timeout'. Two ladders: the review path (~:42419-42432, 'combined = stderr+output' then 'timed out'/'timeout' substring first) and the rp path (~:30451-30460). Recommended shape: scope the timeout substring scan to stderr (transport timeouts surface there), or reorder so exit-code/emptiness/verdict checks precede the substring scan - your judgment, but BOTH ladders get the same semantics. (2) R5 - where the consecutive-transport-failure cap produces the TRANSPORT_UNHEALTHY terminal ('repair the backend/environment before retrying'), branch on the recorded failure classes: when the failures are missing_verdict-class, the terminal message must name the likely cause (the reviewer inherited host/plugin instructions and declared no verdict) and remedies (persona override is now on for codex; check host AGENTS.md size / plugin skill exposure) instead of the backend-repair advice. Transport classes keep the existing message; cap semantics and counters unchanged (find the terminal construction near the transport_unhealthy computation ~:11294 and the summary consumer). (3) Regression tests: exit-0-no-verdict with 'timeout' in output -> failure_class missing_verdict (both ladders if reachable); terminal message branch pinned by contract tokens (e.g. 'no verdict' + 'persona'), not sentences. Look at tests/test_review_convergence_cap.py and test_review_convergence_journal.py for the existing harness patterns. Do NOT change counter/budget semantics, journal schema, or prompts.

## Acceptance
R4+R5 met; existing convergence/journal suites green; new pins green; ruff clean.

## Done summary
Timeout substring scan scoped to stderr in the backend-exec ladder (TimeoutExpired handlers put every genuine transport timeout there; reviewer prose lands in output), and rp record demotes a caller-declared timeout on an exit-0 non-empty run to missing_verdict. New build_transport_unhealthy_message branches the cap terminal: all-missing_verdict streaks get instruction-contamination guidance (backend probably healthy - do not repair), transport streaks keep repair advice. Summary gains consecutive_failure_classes (journal rows unchanged). 7 token-pinned tests.
## Evidence
- Commits: e72691f6
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_review_convergence_cap test_review_convergence_journal -q
- PRs: