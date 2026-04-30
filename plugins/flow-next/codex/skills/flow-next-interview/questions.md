# Interview Question Categories

Ask NON-OBVIOUS questions only. Expect 40+ questions for complex specs.

## Pre-Question Taxonomy

Before asking any question, classify it on three axes:

| Category | Who answers | Examples |
|----------|-------------|----------|
| **Codebase-answerable** | Agent (Read / Grep / Glob) | "What persistence layer is used?" / "Where do existing routes live?" / "What's the test framework?" |
| **Glossary-lookup-answerable** (`DOC_AWARE=1` only) | Agent (`flowctl glossary read`) | "What does this project mean by 'worker'?" / "Is 'session' the canonical term here, or is it 'connection'?" |
| **User-judgment-required** | User (`request_user_input`) | "Should we add caching?" / "What's the priority for offline support?" / "Is performance or simplicity more important here?" |

**Rules of thumb:**

- "What exists / how is it wired / what conventions live here" → agent investigates the codebase, doesn't ask.
- "What does the project's canonical vocabulary call this?" → agent looks up the nearest-ancestor `GLOSSARY.md` (when `DOC_AWARE=1`), surfaces only when (a) no canonical entry exists and the term is overloaded (behavior (b) — fuzzy-term sharpening), or (b) the user's wording conflicts with canonical AND the term is load-bearing (behavior (a) — phase-zero scan).
- "What should exist / what tradeoff to make / what priority" → user decides, agent asks.

**If you find yourself answering a "should" question via grep, that's the bug.** Stop and ask the user.

**Audit trail:**

- Codebase-resolved items → `## Resolved via Codebase` section with file:line evidence.
- Glossary-conflict-resolved items (when behavior (a) fired) → `## Glossary Conflicts` section with the user-wording, canonical term, and resolution.
- Both sections are separate from items the user answered. Cite evidence so reviewers can spot-check assumptions later — especially important when the agent's "I checked" turns out to be "I assumed."

## Technical Implementation

- Data structures and algorithms
- Edge cases and boundary conditions
- State management approach
- Concurrency and race conditions

## Architecture

- Component boundaries and responsibilities
- Integration points with existing code
- Dependencies (internal and external)
- API contracts and interfaces
- For parallel work: can tasks touch disjoint files? (reduces merge conflicts)
- For task sizing: can sequential steps be combined into M-sized tasks? (avoid over-splitting)

## Error Handling & Failure Modes

- What can go wrong?
- Recovery strategies
- Partial failure handling
- Timeout and retry logic

## Performance

- Expected load/scale
- Latency requirements
- Memory constraints
- Caching strategy

## Security

- Authentication/authorization
- Input validation
- Data sensitivity
- Attack vectors

## User Experience

- Loading states
- Error messages
- Offline behavior
- Accessibility

## Testing Strategy

- Unit test focus areas
- Integration test scenarios
- E2E critical paths
- Mocking strategy

## Migration & Compatibility

- Breaking changes
- Data migration
- Rollback plan
- Feature flags needed?

## Acceptance Criteria

- What does "done" look like?
- How to verify correctness?
- Performance benchmarks
- Edge cases to explicitly test

## Unknowns & Risks

- What are you most uncertain about?
- What could derail this?
- What needs research first?
- External dependencies

## Interview Guidelines

1. **Ask follow-up questions** based on answers - dig deep
2. **Don't ask obvious questions** - assume technical competence
3. **Continue until complete** - multiple rounds expected
4. **Group related questions** when possible (use multiSelect for non-exclusive options)
5. **Probe contradictions** - if answers don't align, clarify
6. **Surface hidden complexity** - ask about things user might not have considered
