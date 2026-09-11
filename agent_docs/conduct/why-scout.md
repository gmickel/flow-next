# Conduct checklist — `why-scout`

A correct run answers one rationale question from evidence and reports each finding at the tier its evidence supports. The contract (sources, tiers, output shape, access rules) is the agent file, `plugins/flow-next/agents/why-scout.md`; this page checks outcomes against it.

- [ ] Every finding's citation supports its tier: a `[direct]` finding quotes an artifact that states the reason, and no finding sits above what its cited evidence establishes.
- [ ] Every cited hop carries an identifier a reviewer can open in one step (sha, PR number, issue key, entry id, spec id).
- [ ] What could not be read is reported as an access gap, separately from the findings, and no gap is papered over with a plausible story.
- [ ] Access boundaries held: the tracker was read only through access the session already had, and nothing was configured, installed, authenticated, or written.
- [ ] The report followed the evidence chain rather than surveying the module, and stayed within its output budget.
