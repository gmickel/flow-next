# Conduct checklist — /flow-next:qa

A correct run derives scenarios from the spec's acceptance criteria, drives the live app via the flow-next-drive read-and-drive contract, files P0/P1/P2 findings with captured evidence, and ends with a YES/NO ship verdict emitted as a `qa_verdict` receipt.

- [ ] The ship verdict rests on evidence captured from the running app — screenshots and console dumps under `.flow/tmp/qa-<spec-id>/` — and a SHIP with an empty evidence directory is force-downgraded to BLOCKED. A SHIP reached by reading source or the diff has broken this.
- [ ] Every scenario traces to an R-ID from the spec's acceptance criteria, and the coverage table marks each row `live`, `subtracted (<task-id> · <test-cmd>)`, `backend/CLI — not live-QA-able`, or `⚠️ no live scenario`. A runtime or UI criterion marked `subtracted` has broken this.
- [ ] Each finding carries a severity, persona, steps to reproduce, expected-vs-actual, and evidence pointers (screenshot path, console path, full URL, and the persisted write side-effect for write paths), and was reproduced a second time before filing.
- [ ] The run writes one `qa_verdict` receipt (default `.flow/review-receipts/qa-<spec-id>.json`) carrying `qa_outcome`, the projected `verdict`, `head_sha`, `branch`, `rid_coverage`, and `open_p0p1`.
- [ ] No reachable live target or no available driver surfaces as a committed BLOCKED receipt with a `blocked_reason` and a clean exit — never a fabricated pass and never a silent stop before the receipt.
- [ ] Under `mode:autonomous` / `FLOW_AUTONOMOUS=1` the run asks nothing: an undocumented target URL, undocumented test accounts, or an undetectable base ref becomes a BLOCKED receipt instead of a question.
