# fn-25-prompt-quality-improvements-for-flow.6 Quality-auditor: test budget ratio check (advisory)

## Description
Add test budget awareness to the quality-auditor agent. Flags disproportionate test generation as advisory — never blocks shipping.

**Size:** S
**Files:** `plugins/flow-next/agents/quality-auditor.md`

## Change details

In quality-auditor.md, add a new audit area between "6. Test Coverage" (line 53) and "7. Performance Red Flags" (line 57):

```markdown
### 6b. Test Budget Check
- Count test files/lines added vs implementation files/lines added
- Flag if test_lines > 2× implementation_lines (may indicate testing implementation details instead of behavior)
- Flag if existing tests were modified (may indicate assertion-weakening to make broken code pass)
- This is ADVISORY — over-testing is less dangerous than under-testing

Red flags:
- Many test variations with trivial differences (copy-paste tests)
- Tests asserting internal state instead of observable behavior
- Modified assertions in existing tests (especially weakening: removing checks, loosening matchers)
```

In the Output Format section, add to `### Test Gaps` area:

```markdown
### Test Budget
- Ratio: [test lines : impl lines] (flag if > 2:1)
- Modified existing tests: [list if any — verify intentional]
```

In the Rules section (line 96+), add:
```markdown
- Test budget is advisory — flag, don't block
- Over-testing beats under-testing
- Test setup/fixture code doesn't count toward ratio
```

## Investigation targets
**Required** (read before coding):
- `plugins/flow-next/agents/quality-auditor.md:48-56` — test coverage section
- `plugins/flow-next/agents/quality-auditor.md:63-93` — output format

## Key context

- Quality-auditor is read-only (disallowedTools: Edit, Write, Task) — it only reports
- The 2:1 threshold is a soft heuristic from industry data, not a hard rule
- "Modified existing tests" is the high-value signal — agents weakening assertions to make broken code pass is a known failure mode
- Keep the section short — quality-auditor is already 102 lines, shouldn't grow much
## Acceptance
- [ ] Test budget check section added to audit strategy
- [ ] 2:1 ratio threshold documented as advisory flag
- [ ] Existing test modification detection documented
- [ ] Output format includes Test Budget section
- [ ] Rules clarify advisory nature (flag, never block)
- [ ] Quality-auditor remains read-only (no new tool access)
- [ ] Section is concise (< 15 lines added)
## Done summary
Added test budget ratio check (advisory) to quality-auditor agent: 6b audit section, output template, and advisory rules. 18 lines added, read-only constraints preserved.
## Evidence
- Commits: df8d2ca9b8173d6aa95ad3a9d3d3809729c48cc3
- Tests: manual review of quality-auditor.md structure
- PRs: