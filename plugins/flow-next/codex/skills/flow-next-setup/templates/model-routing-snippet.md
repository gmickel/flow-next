<!-- flow-next:model-routing:start -->
## Picking models for flow-next workflows and subagents

_Scaffolded by `/flow-next:setup` — edit freely; re-run setup to regenerate. These scores are starting opinions: re-rank them to what you actually pay for and prefer. This section is yours now._

Rankings, higher = better. Cost reflects what you actually pay (existing subscriptions), not list price; intelligence = how hard a problem you can hand it unsupervised; taste = UI/UX, code quality, API design, copy.

| model | cost | intelligence | taste |
|--------------------------|------|--------------|-------|
| session model (frontier) | 2 | 10 | 9 |
| gpt-5.5 | 9 | 8 | 5 |
| composer-2.5 | 9 | 6 | 6 |
| fast Claude tier | 8 | 4 | 4 |

How to apply — defaults, not limits. Standing permission to escalate: if a cheaper model misses the bar, rerun on a smarter one without asking. Judge the output, not the price tag.
- For anything that ships, intelligence > taste > cost; cost is a tie-breaker only.
- Orchestration, planning, review verdicts, anything ambiguous → session model. Never delegate judgment.
- Anything user-facing (UI, copy, API design) needs taste ≥ 7 → keep on the session model even if it looks mechanical.
- Reviews route to a different family than the writer — uncorrelated blind spots.
- Graceful degrade: a routed CLI that is missing, unauthenticated, or errors → report it unavailable and fall back to the session model. Never block.

flow-next wiring — the surface each route drives (each line below is live only if its CLI is installed):
<!-- probe:codex --> Bulk/mechanical implementation (clear spec, low ambiguity) → delegate to gpt-5.5: `/flow-next:work <id> delegate:codex` (`work.delegateModel=gpt-5.5`, `work.delegateEffort=medium`).
<!-- probe:codex --> Cross-family review from codex → `review.backend codex`; per-task `review:` pins exceptions; escalate reviewer↔worker NEEDS_WORK disagreements to the session model.
<!-- probe:cursor --> Cross-family review from cursor (speed/reach) → `review.backend cursor:composer-2.5`.
<!-- probe:cursor --> Bulk, low-judgment reads (codebase sweeps) → flow-next scouts may shell out to `cursor-agent`; only the digest returns.
<!-- probe:codex --> Reach gpt-5.5 inside a subagent (thin-wrapper): a cheap wrapper writes a self-contained prompt, runs `codex exec` over Bash, returns the digest.
<!-- flow-next:model-routing:end -->
