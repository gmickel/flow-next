# Interview — async fact-scouts (optional, rounds mode)

> Read ONLY when you are about to dispatch a fact-scout. Investigating inline (the default) needs nothing from this file.

While the user answers the current round, you MAY dispatch ONE read-only fact-scout subagent (`spawn_agent` with `agent_type: explorer`; on hosts without an Explore builtin — e.g. Cursor, which registers only the plugin's own agents — use the host's generic subagent dispatch with Edit/Write disallowed) to resolve codebase lookups that gate NEXT-round questions — investigation latency hides inside user-answer time instead of stalling the interview between rounds.

- **The brief is the contract.** Number each lookup: what to look up, where to start, and which question it gates or could eliminate. Facts only, never judgments. Deferring a question on a pending fact REQUIRES the brief to already name that lookup — no brief, no deferral: investigate inline as usual.
- **Scout tier: judgment-capable, never a fastest-tier scanner** — the thinking scout tier or stronger, escalating toward the session model's tier when it is stronger or a digest comes back thin. Eval-validated: the fastest tier missed a load-bearing storage-architecture fact that the mid tier found on the identical brief.
- **Digest discipline.** The scout returns facts with file:line evidence; absence findings count, cited as the paths and patterns searched. Treat the digest as investigation results, state residual uncertainty honestly, and spot-verify a load-bearing fact yourself before building a `[high]` recommendation on it.
- **Never block, never degrade silently.** Scout unavailable or digest missing → investigate inline exactly as today, and say so. Doc-aware budgets and their sanctioned hold-back are unchanged.
