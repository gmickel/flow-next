# Shared interview blocks

These two blocks apply to every scope-resolved question bank — biz and tech alike. Both [questions-business.md](questions-business.md) and [questions-technical.md](questions-technical.md) reference them rather than re-embedding (single source of truth; same Pre-Question Taxonomy and Interview Guidelines across passes).

## Pre-Question Taxonomy

Before asking any question, classify it into one of these categories:

| Category | Who answers | Examples |
|----------|-------------|----------|
| **Codebase-answerable** | Agent (Read / Grep / Glob) | "What persistence layer is used?" / "Where do existing routes live?" / "What's the test framework?" |
| **Glossary-lookup-answerable** (`DOC_AWARE=1` only) | Agent (`flowctl glossary read`) | "What does this project mean by 'worker'?" / "Is 'session' the canonical term here, or is it 'connection'?" |
| **Experiment-answerable** | Agent (a throwaway experiment) | "Does the parser accept the legacy header?" / "Is this query fast enough?" / "Does the layout fit at 320px?" / "Does this eval separate the two variants?" |
| **User-judgment-required** | User (`plain-text numbered prompt`) | "Should cancelled orders stay visible to the customer?" / "Who may approve a refund?" / "Is dropping the legacy import format acceptable?" |

**Rules of thumb:**

- "What exists / how is it wired / what conventions live here" → agent investigates the codebase, doesn't ask.
- "What does the project's canonical vocabulary call this?" → agent looks up the nearest-ancestor `GLOSSARY.md` (when `DOC_AWARE=1`), surfaces only when (a) no canonical entry exists and the term is overloaded (behavior (b) — fuzzy-term sharpening), or (b) the user's wording conflicts with canonical AND the term is load-bearing (behavior (a) — phase-zero scan).
- "What happens when it runs" — behaviour, timing, layout, output, performance, whether an eval separates two options → agent runs a throwaway experiment, doesn't ask. It runs only when it is read-only or fully disposable; one that needs live or shared state, credentials, the network, or anything destructive becomes a user question. A result whose noise is larger than the difference is inconclusive: ask the user, with the data attached.
- "What should exist / what tradeoff to make / what priority" → user decides, agent asks — but only when the question passes the one test in SKILL.md. A user-judgment question whose answer would not change what gets built is not asked.

**If you find yourself answering a "should" question via grep, that's the bug.** Stop and ask the user.

**A skipped "should" question stays a "should" question.** Skipping never demotes it to codebase-/docs-answerable, and the agent's recommendation never silently becomes the answer — park it under `## Open Questions` per the skip contract in SKILL.md ("Skipped Questions Are Not Answers").

**Audit trail:**

- Codebase-resolved items → `## Resolved via Codebase` section with file:line evidence.
- Experiment-resolved items → `## Resolved via Experiment` section: the question, what was run, what was observed, and the decision it settled. Experiment files live in `.flow/tmp/experiments/` (gitignored) and are discarded or folded into the spec as evidence, never shipped.
- Glossary-conflict-resolved items (when behavior (a) fired) → `## Glossary Conflicts` section with the user-wording, canonical term, and resolution.
- These sections are separate from items the user answered. Cite evidence so reviewers can spot-check assumptions later — especially important when the agent's "I checked" turns out to be "I assumed."

## Interview Guidelines

1. **Ask only what changes the build** - every question passes the one test in SKILL.md; a follow-up is asked only when an answer opens a new question that passes it
2. **Don't ask obvious questions** - assume technical competence
3. **Group related questions** when possible (use multiSelect for non-exclusive options)
4. **Probe contradictions** - if answers don't align, clarify
5. **Skips are not answers** - only an explicit answer or an explicit "you decide" resolves a question; anything skipped parks under `## Open Questions` (SKILL.md skip contract)
6. **Plain language, explained answers** - every question opens with one sentence of stakes, terms of art get a plain gloss at first use, options state their consequence ("Choose this if…"); trim repetition and background, never required content (SKILL.md plain-language contract)
