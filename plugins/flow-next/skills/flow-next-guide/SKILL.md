---
name: flow-next-guide
description: Prompt-first router that recommends the smallest sufficient flow-next workflow. Use when unsure which command to run next, which pre-build stage applies, or whether to skip chart/interview/plan. Triggers on /flow-next:guide with a free-form situation description.
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Task
---

# Guide - smallest-sufficient workflow router

Stateless prompt-first router. Recommends **one** next workflow from the starting state. Does **not** create specs, charts, tasks, artifacts, or flowctl state. Chart is an **optional** discovery route - never a mandatory stage and never a new pipeline stage.

**Role**: routing coordinator (inline skill - keep `AskUserQuestion` reachable). On portable hosts without `AskUserQuestion`, fall back to a plain-text numbered prompt with a final `Other - type your own answer` option. (sync-codex.sh rewrites AskUserQuestion to a plain-text numbered prompt in the Codex mirror.)

## Preamble

**CRITICAL: flowctl is BUNDLED - NOT installed globally.** `which flowctl` will fail (expected). Define once; probe blocks use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

No flowctl mutation. Optional read-only probes (`$FLOWCTL brief` for cold-session orientation; `$FLOWCTL list` / `$FLOWCTL show`, file reads) may ground the recommendation when a handle or path is named. Never run create/write/claim/resolve.

## Output contract (every recommendation)

Lead with a **natural-language next prompt** - the exact words or slash command the user should say/run next. Flags are secondary (automation only). Then:

1. **Route** - named skill/path
2. **Why (positive signal)** - which matrix signal matched
3. **Safe skip / narrow** - when this route may be skipped or narrowed
4. **Skip kind** - `signal absent` (the stage's work is not needed) vs `despite unresolved risk` (you chose a smaller path; evidence/consent/review contracts still apply later)

Skipping a command never skips the evidence, consent, or review contract that command would have provided.

## Smallest-sufficient matrix (exact)

Match the **starting state**. First clear match wins. Chart only when one oversized idea is still unclear.

| Starting state | Route | Positive signal | Safe skip / narrow |
|---|---|---|---|
| Looking for candidate investments across a domain | `/flow-next:prospect` | Domain search; need ranked candidates | Skip prospect when the idea is already singular. After selection: chart **only if** the candidate remains singular + oversized + unclear; otherwise capture |
| One large idea, unclear boundaries, several consequential unknowns | `/flow-next:chart` then briefing then capture | Singular effort too big for one capture; unknowns block stating intent | Skip chart (`signal absent`) when intent and boundaries are already stateable - go capture or author the spec directly. Chart is never mandatory |
| A theme or direction rather than one effort ("make X more Y") | `/flow-next:prospect`, or narrow to a single effort | No nameable end state, so no Outcome and no scope boundary | Chart cannot take this (`signal absent` for chart): it needs a destination whose route is unknown, not a direction. Narrow first, or prospect when the real ask is which effort to pick |
| One meaningful idea whose intent and boundaries can already be stated | `/flow-next:capture` or author the spec directly | Clear meaningful idea | Skip chart (`signal absent`). Do not manufacture a chart for clear work |
| Existing structured brief with resolved business and technical choices | `/flow-next:capture` the brief | Structured brief / chart briefing package ready | Skip chart. Narrow or skip interview **only after** capture read-back proves no material gaps - never pre-declare skip interview |
| Tiny, local, low-risk change that fits one implementation context | Direct change + review path appropriate to the repo | One-context fix; low risk | Skip chart **and** the full spec pipeline (`signal absent`). Still run the review/consent gates the change would need |
| A valid spec with unresolved judgment questions | `/flow-next:interview` | Spec exists; judgment gaps remain | Do not reopen discovery as chart unless the questions reveal the **effort itself is not yet specifiable** - only then route backward to chart |
| A ready spec whose work is understood | `/flow-next:plan` | Spec ready / work understood enough to task | Chart is too late. Unshaped oversized freeform ideas are not plan input - route those to chart first |
| Planned tasks ready to implement | `/flow-next:work`, then existing review / QA / ship choices | Tasks exist and are actionable | Stay on work + the repo's review/QA/ship menu. Guide does not invent new ship stages |
| Unsure which of these situations applies | This matrix (this skill) | Ambiguous starting state | Ask at most **one** blocking question when two routes would **materially** differ; otherwise recommend one route |

There is **no** fixed prospect -> chart -> capture conveyor. Each hop re-evaluates the matrix.

## Prompt-first behavior

1. Infer starting state from `$ARGUMENTS` + conversation (and optional read-only probes).
2. If exactly one matrix row fits, emit one recommendation (natural-language prompt first).
3. If two routes would materially change cost, consent, or discovery vs build path, ask **at most one** blocking question via bare `AskUserQuestion` (or the plain-text numbered fallback). Then recommend.
4. Never present chart as required onboarding, a pipeline stage, or the default after prospect.
5. Never mutate `.flow/` or invoke write-capable flowctl subcommands.

## Recommendation shape (template)

```
Next: <natural-language prompt or slash command to run>

Route: <name>
Signal: <positive signal>
Skip/narrow: <explicit safe skip or narrow condition>
Skip kind: signal absent | despite unresolved risk
Why not the alternatives: <one line>
```

Examples of natural-language next prompts (not required flags):

- "Run prospect for DX improvements in the skills tree"
- "Chart this: multi-tenant billing with unknown pricing and migration risks"
- "Capture what we just agreed - intent and boundaries are clear"
- "Interview fn-12 on the open product judgment questions"
- "Plan the ready spec fn-12"
- "Just fix the typo in README and open a small review"

## Forbidden

- Writing files under `.flow/`, creating charts/specs/tasks, or any flowctl mutation
- Using `Write` or `Edit` tools
- Presenting chart as mandatory or as a pilot/build-loop stage
- A fixed multi-stage conveyor that always chains prospect -> chart -> capture
- Asking more than one blocking question per invocation
- Leading with flag vocabulary when a natural-language next prompt exists
- Claiming that skipping a command also skips its evidence/consent/review contracts
