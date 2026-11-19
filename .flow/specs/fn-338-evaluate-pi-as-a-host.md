# Evaluate Pi as a host

## Goal & Context

<!-- Source: 15% user / 55% [paraphrase] / 30% [inferred] -->

GitHub issue #616 asks for native support for the Pi coding agent: installing the skills and bundled flowctl, host detection in setup, scouts, workers and reviewers running through Pi, and user questions and review evidence handled through Pi, with no Claude Code or Codex needed.

Whether that is possible is not known. Subagents and delegation in Pi work very differently from the hosts flow-next supports, so this spec only evaluates: it ends in a verdict and a cost, and ships no Pi support. [paraphrase]

## Architecture & Data Models

- The evaluation runs Pi itself against a small throwaway repository; documentation alone does not settle any row. [inferred]
- It maps each thing flow-next needs from a host to the Pi mechanism that provides it, or records that none exists. [paraphrase]

What flow-next needs from a host:

- Loading skills with their reference files, and a way to invoke one by name. [inferred]
- Reaching the bundled flowctl from a skill. [inferred]
- Delegation with fresh context: scouts that only read, a worker that edits, several running at once. [paraphrase]
- A reviewer with fresh context and enforced read-only access, or a headless run flowctl could call as a review backend. [inferred]
- A blocking question to the person, with options. [paraphrase]
- An unattended run that continues hop after hop without a person. [inferred]
- Model selection left to Pi. [paraphrase]

## Edge Cases & Constraints

- Pi is extended through its own extension mechanism; a need met only by writing and maintaining a Pi extension counts as a cost, not as native support. [inferred]
- Cross-platform parity is a standing rule: a host is first-class only when install, smoke tests and skills hold on it. A degraded path is named as degraded. [strategy:Cross-platform parity]

## Acceptance Criteria

- **R1:** Each need listed above has a row saying which Pi mechanism meets it, how it was exercised, and what was observed; or that nothing meets it. [paraphrase]
  Errors: a row that could not be exercised is marked unverified with the reason, never filled from documentation as if observed.
- **R2:** The evaluation states one verdict: first-class host, degraded single-agent path, or not feasible now. For a degraded path it says what is lost (parallel scouts, fresh-context review, questions) and whether the quality gates still hold. [paraphrase]
  Errors: no error surface.
- **R3:** The verdict comes with the cost of supporting it: installer, any Pi-side extension, mirror or rewrite of skill files, smoke coverage, and what would have to be kept in step on each release. [inferred]
  Errors: no error surface.
- **R4:** The result is written into this spec, and a reply for #616 is drafted for the maintainer to post. [inferred]
  Errors: the reply is not posted by the agent.
- **R5:** No Pi installer, skill change, platform-roster change or documentation claim of Pi support ships from this spec. [paraphrase]
  Errors: no error surface.

## Strategy Alignment

Cross-platform parity track: a new host is added only as first-class or as a clearly named degraded path, never as a silent partial. [strategy:Cross-platform parity]

## Boundaries

- No implementation of Pi support. A follow-up spec does that if the verdict supports it. [paraphrase]
- No evaluation of other unsupported hosts. [inferred]
- No change to how existing hosts delegate. [inferred]

## Decision Context

"Loading skills alone" is not support, as the issue itself says: flow-next's quality comes from fresh-context workers and reviewers, and a host without delegation would need either a single-agent path that drops them or a CLI bridge that the issue rules out. Evaluating first avoids building an installer for a host whose shape may not fit.
