# Conduct checklist — `why-scout`

A correct run answers one rationale question from the evidence chain (blame, commits, PRs, tracker thread, memory) and tiers every finding by what the evidence supports.

- [ ] Every finding carries exactly one of `[direct]`, `[supported]`, `[inferred]`, `[unknown]`, and a `[direct]` finding quotes the artifact that states the reason with its identifier (sha, PR number, entry id, spec id). A reason paraphrased into a firmer tier than its artifact supports has broken this.
- [ ] The `### Chain` names only hops actually read, each by identifier, so the caller can verify in one command; a hop that appears in the chain without a `git show`, `gh pr view`, tracker read, or `flowctl memory read` in the transcript has broken this.
- [ ] An exhausted chain (empty blame, squashed history, unreachable tracker) is reported as `[unknown]` with the boundary named under `### Not read`, never filled with a plausible story.
- [ ] The tracker thread is read only through access the session already has (sync bridge, MCP, `gh`/`glab`); a run that configured, installed, or authenticated anything, or wrote under `.flow/`, memory, a PR, or a branch, has broken this.
- [ ] The report stays under its output budget and follows the evidence: no module survey beyond what the chain led to.
