# Interview Question Categories

Ask NON-OBVIOUS questions only. Expect 40+ questions for complex specs.

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
