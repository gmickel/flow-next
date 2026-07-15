<!-- flow-next:model-routing:start -->
## Picking models for flow-next workflows and subagents

_Scaffolded by `/flow-next:setup` — edit freely; re-run setup to regenerate. These scores are starting opinions (as of Jul 2026): re-rank them to what you actually pay for and prefer. This section is yours now._

Rankings, higher = better. **cost** = how lightly it rides your subscription quota (higher = run it freely; lower = it burns the plan's budget fast, so spend it sparingly), NOT list $/token, and each provider is a separate budget; **speed** = output speed at *default* reasoning effort (raising effort trades speed for intelligence); **intelligence** = how hard a problem you can hand it unsupervised; **taste** = UI/UX, code quality, API design, copy.

| model         | cost | speed | intelligence | taste |
|---------------|------|-------|--------------|-------|
| fable-5       | 2    | 2     | 10           | 9     |
| opus-4.8      | 4    | 3     | 7            | 8     |
| gpt-5.6-sol   | 8    | 5     | 9            | 6     |
| gpt-5.6-terra | 9    | 7     | 7            | 5     |
| grok-4.5      | 9    | 9     | 7            | 5     |
| composer-2.5  | 9    | 10    | 6            | 6     |
| sonnet-5      | 5    | 6     | 7            | 7     |
| haiku-4.5     | 8    | 9     | 4            | 4     |

How to apply — defaults, not limits. Unless prompted otherwise, route work across these models as you judge best — no permission needed; an explicit user instruction always overrides this table. Standing permission to escalate: if a cheaper model misses the bar, rerun on a smarter one without asking. Judge the output, not the price tag.
- For anything that ships, intelligence > taste > cost; cost is a tie-breaker only.
- Orchestration, planning, review verdicts, anything ambiguous → the session model (whichever row you are running as the conductor). Never delegate judgment.
- Anything user-facing (UI, copy, API design) needs taste ≥ 7 → keep on the session model even if it looks mechanical.
- Reviews prefer a different family than the writer — uncorrelated blind spots.
- Graceful degrade: a routed CLI that is missing, unauthenticated, or errors → report it unavailable and fall back to the session model. Never block.

flow-next wiring — roles with a MENU, not fixed pairings: pick per task. Claude tiers run natively (spawn subagents with the model parameter); other families ride the headless bridges — recipes in `.flow/usage.md` § Orchestration & model steering. Probe-marked lines are live only if their CLI is installed:
- Implementation, native: a worker/subagent on opus-4.8 (quality) or sonnet-5 (speed) via the model parameter.
<!-- probe:codex --> Implementation via gpt-5.6-terra @ medium (the packaged delegate default): `/flow-next:work <id> delegate:codex` (consent-gated, host keeps git/review) or a direct `codex exec` bridge. Eval-matched gpt-5.6-sol correctness at ~2/3 wall-clock on strong specs; escalate work.delegateModel to gpt-5.6-sol for gnarly tasks.
<!-- probe:cursor --> Implementation via composer-2.5: the `cursor-agent` bridge (`--force` to apply); host reviews + commits.
<!-- probe:grok --> Implementation via grok-4.5: a fast, cheap first-draft worker via the `grok -p` one-shot bridge; host reviews + commits on a taste-heavier tier. Route it to bulk/implementation, NOT UI or final taste-critical work (higher hallucination, weaker on UI). (Or reach grok-4.5 through the cursor review line below.)
<!-- probe:codex --> Review, cross-family (recommended default when the writer is Claude-family; on a GPT-writer host pick a non-GPT reviewer instead): `review.backend codex`; per-task `review:` pins exceptions; escalate reviewer↔worker disagreements to the session model.
<!-- probe:cursor --> Review, cross-family: `review.backend cursor:composer-2.5` (or `cursor:grok-4.5-high` for a fast cross-family pass; pair a taste model on UI-heavy diffs).
- Review, same-family heavy: a fresh-context reviewer subagent on opus-4.8 (or the session model) with the review criteria — no registry rung needed; describe the arrangement.
<!-- probe:cursor --> Bulk, low-judgment reads (codebase sweeps): scouts may shell out to `cursor-agent`; only the digest returns.
- Bulk reads, native: haiku-4.5 / sonnet-5 subagents for scans and digests.
- Autonomous loops: never call a bridge CLI raw - wrap it in a thin fast-tier subagent that runs the bridge in the FOREGROUND and self-heals environment failures only (bridges fail silently outside trusted git dirs), never judgment; recipes in `.flow/usage.md` § Orchestration & model steering.
<!-- probe:codex --> Reach gpt-5.6-terra inside a subagent (thin-wrapper) for cheap bulk reads/digests only — not implementation: a cheap wrapper writes a self-contained prompt, runs `codex exec` over Bash, returns the digest.
<!-- flow-next:model-routing:end -->
