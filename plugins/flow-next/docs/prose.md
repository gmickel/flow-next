# Prose contract for agent-emitted artifacts

This page governs the durable artifact prose emitted by flow-next skills and agents — PR bodies, tracker and PR comments, spec and plan prose, strategy and briefing sections, memory and glossary entries, task done summaries, and changelog entries at release. Emission points cite this file by path. The drafting agent reads it at the moment it writes the artifact. Every emission point carries a pointer; the visual digest is excluded by contract because its output is ephemeral chat rendering, never a written artifact.

## The rules

### 1. The portability test

A sentence that could appear unchanged in another project's docs or PR says nothing about this change. The drafting agent deletes it, or adds the mechanism, path, number, or bound that belongs here. A rewrite that only swaps in the project name fails the same test.

### 2. Name the mechanism or the number, never the feeling

`Significantly faster` is a feeling. `30 seconds to half a second` and `skips the suite when a green receipt matches` are evidence. The drafting agent cuts a claim that names neither a mechanism nor a measurement.

### 3. No negative parallelism

The `not X, but Y` template and the `this isn't X - it's Y` template make the reader parse a discarded X before reaching Y. The drafting agent states Y. The one legitimate use is correcting a real, likely misreading the reader would otherwise make.

### 4. No inline-header restating

A sentence that restates the heading above it wastes the reader's first fixation. A bold lead-in that advances the point (`**Fail-closed both ways:** ...`) is structure.

### 5. Active voice with a named actor

`The conductor integrates the commit` names the actor. Passive voice is acceptable only when the actor is unknown or irrelevant.

### 6. An adverb is a missing measurement

The drafting agent replaces `substantially reduced` with the measured delta or the concrete before/after. If neither exists, the claim does not belong in the artifact.

### 7. The plain word

The drafting agent replaces `utilize` and `leverage` with `use`, `comprise` with `make up`, and `in order to` with `to`. A term the project glossary defines is vocabulary, not a violation.

### 8. User-outcome-first ordering

The drafting agent opens with who benefits and what changed for them. Mechanism, schema, and internals come last. The agent applies this per artifact and per section when a sourced outcome exists in the payload.

### 9. No em dashes, and no colon-as-connector, in artifact prose

The drafting agent writes plain hyphens and full sentences. Structural colons remain in list introductions, `Enable:`, and table cells. A colon that splices two clauses for rhythm is the banned form.

### 10. Honesty

The drafting agent never softens a failure, a bound, or a deliberate miss. `About 35% of runs still force a full suite` belongs in the artifact when that bound is true. An artifact that hides its limits is marketing copy. The drafting agent rewrites it.

## Precedence: structural contracts win

When a rule on this page collides with a contract of the emitting surface, the surface contract wins and the prose rule yields.

- **Dedup markers.** The drafting agent leaves tracker-comment dedup markers as the first line, byte-unchanged.
- **Projection.** The drafting agent never overrides envelopes or projection-only source-truth constraints. The tracker-sync bridge projects. It never authors.
- **Sourced outcomes.** Outcome-first ordering (rule 8) applies only when a sourced outcome exists in the payload. The drafting agent never invents outcome prose to satisfy the rule.

## Scope boundary

The contract covers PR bodies, specs, tracker comments, and changelogs. It makes no claim about code quality or maintainability decay. Prompt-side quality rules are an intercept intervention per SlopCodeBench (arXiv 2603.24755). That paper is why the claim stays this narrow. This page governs how the prose reads. Section 2.5 of [`../skills/flow-next-make-pr/workflow.md`](../skills/flow-next-make-pr/workflow.md) governs what the prose may claim. This page cross-links that fabrication-side contract and leaves the eleven rules there.

## See also

- [`../skills/flow-next-make-pr/workflow.md`](../skills/flow-next-make-pr/workflow.md) - hallucination guardrails (section 2.5), the fabrication-side contract
- [`../../../GLOSSARY.md`](../../../GLOSSARY.md) - the `Emission point` term and vocabulary discipline
- [`README.md`](README.md) - the docs index this page is registered in
