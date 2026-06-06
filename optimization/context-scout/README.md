# Autoresearch — context-scout (Tier 1, hot-path scout family)

Eval-driven optimization of `plugins/flow-next/agents/context-scout.md` (the largest scout prompt,
~2.8k tokens) per the autoresearch methodology. Goal: **output-budget leverage** (leaner findings
flow into the planner context on every `/flow-next:plan`) with **coverage + grounding held**.

**Test bed = a representative external repo, NOT flow-next-on-itself** (spec fn-54 R9): the
prompt-under-test is run as a read-only `Explore` subagent that scouts **`~/work/DocIQ-Sphere`**
(~442k LOC; Next.js TS/TSX + Python FastAPI engine + Convex backend) on 3 frozen, varied feature
requests. Model held constant at `opus` (the agent's frontmatter model).

**Harness-path caveat (honest):** context-scout's primary discovery tool is RepoPrompt `rp-cli`,
which isn't wired up to DocIQ-Sphere in a headless subagent, so runs take the prompt's documented
**Fallback: Standard Tools** path (Grep/Glob/Read). That is fine for this experiment because the
lever is **output FORMAT/budget** — tool-path-agnostic — and R9 explicitly permits flow-next-style
format mutations. Coverage numbers reflect the standard-tools path, not the rp-cli path.

One mutation at a time, keep-if-better-else-revert. Files:
test-inputs.md · evals.md · results.tsv · changelog.md · context-scout.md.baseline
