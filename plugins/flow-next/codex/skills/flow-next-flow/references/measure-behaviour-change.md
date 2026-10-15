# Measure a prompt or skill change (gated reference)

> **Loaded only when** the route is a change to text a model reads (a prompt, a skill, an agent
> instruction, an LLM feature's system prompt) and the question is whether it behaves better.

The output is a verdict with its evidence: `promote`, `do not promote` or `inconclusive`. A
promoted change then continues to work and review.

**Spend first.** Draws call a model, cost money and need credentials. Before the first draw, ask
once for the number of draws and a budget. Unattended, or when the answer is no, design the
harness, record the verdict as not run, and report no result.

**Use the repository's harness** when it has one for this (an eval suite, a scoring script, a
fixture bank). Otherwise build a small blinded one in scratch:

- one organic task a real user might send, stated as the goal, not the test;
- directory, file and prompt names that do not reveal a test, a comparison or other candidates;
- a rubric of a few concrete criteria that only the judge sees;
- baseline and candidate, the same N draws each;
- one judge from another model family, seeing outputs only by neutral label and scoring both
  arms in one pass; without one, say so and the verdict is `inconclusive`;
- grading from what candidates did (transcripts, files, output), never from what they say they did.

**Check before trusting the gap.** Every draw finished the task, and the gap is larger than the
run-to-run spread inside each arm. To push a score up over many attempts afterwards, the
hill-climb route takes this harness as its frozen measurement.

Example: a support bot's system prompt is rewritten to stop it promising refunds. Twelve organic
customer messages, five draws per arm per message, the rubric held by a judge from another family
that sees `set-a` and `set-b`. Baseline promised a refund in 14 of 60 replies, candidate in 1 of
60, every draw completed, and both offered the refund form when the order qualified: `promote`.
