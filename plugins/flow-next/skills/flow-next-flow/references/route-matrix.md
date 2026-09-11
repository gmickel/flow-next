# Route matrix (routing reference 1 of 6)

**Decision record**

- Source: the retired guide skill's matrix and the variant table in `docs/pipeline-variations.md`, folded into this one file when `/flow-next:flow` replaced guide.
- Trigger: a step that must pick the next stage from a starting state - flow's route step, `flow --explain`, capture's closer, plan's next-steps menu.
- Purpose: one inventory of what ships and which starting state each route owns, so the closers and the conductor recommend the same next step.
- Evidence: a router that names a retired skill, or omits a starting state a shipped skill now owns, reads confident and sends the user nowhere; capture, plan, guide, and pipeline-variations each carried their own copy of this table before this file existed.
- Disposition: keep, single copy. **Router staleness is a defect.** Adding or removing a skill updates this table in the same change (`agent_docs/adding-skills.md`).

## Reading the matrix

Route on content and context, never on input kind. A tracker issue, a pasted bug report, console output, a prototype, a branch, a path, and a sentence of intent all become text first: read what was given, then match the starting state. The rows are an inventory, not a precedence order: when more than one could apply, judge from intent, evidence, and current state. Each hop re-evaluates; there is no fixed conveyor. Unknown model identity needs no detector and no question: judge the spec and the execution context available.

A skipped stage keeps its evidence, consent, and review contract: it is satisfied by a cheaper mechanism or recorded as `skipped(reason)`, never silently absent. Skip kind is one of `signal absent` (the stage's work is not needed) or `despite unresolved risk` (a smaller path was chosen; the contracts still apply later).

| Starting state | Route | Positive signal | Safe skip or narrow | Skip kind |
|---|---|---|---|---|
| No written direction - target problem, users, or key metrics stated nowhere | `/flow-next:strategy` | Repeated arguments about what matters; no `STRATEGY.md` | Skip when `STRATEGY.md` exists or the effort is small enough that direction is not in question | signal absent |
| Looking for candidate investments across a domain | `/flow-next:prospect` | Domain search; ranked candidates needed | Skip when the idea is already singular; after selection, chart only if the survivor stays singular, oversized, and unclear, otherwise capture | signal absent |
| One large idea, unclear boundaries, several consequential unknowns | `/flow-next:chart`, then its briefing, then capture | Singular effort too big for one capture; unknowns block stating intent | Skip chart when intent and boundaries are already stateable. Chart is optional: never mandatory and never a pipeline stage | signal absent |
| A theme or direction ("make X more Y") | `/flow-next:prospect`, or narrow to one effort | No nameable end state, so no outcome and no scope boundary | Chart cannot take a direction: it needs a destination whose route is unknown. Narrow first, or prospect when the ask is which effort to pick | signal absent |
| One meaningful idea whose intent and boundaries can be stated | `/flow-next:capture`, or author the spec directly | Clear meaningful idea | Skip chart; do not manufacture a chart for clear work. Count specs per `spec-count.md` when the tripwire trips | signal absent |
| Existing structured brief with resolved business and technical choices | `/flow-next:capture` the brief | Structured brief or chart briefing ready | Skip chart. Narrow or skip interview only after the read-back proves no material gaps | signal absent |
| A reported defect (bug report, console dump, failing behaviour) | Reproduce first; the failing test is the R-ID; then `/flow-next:work` and review | The unknown is the cause, the risk is regression | Interview is the wrong instrument for a defect. Capture only when the diagnosis conversation itself carries decisions worth locking down | signal absent |
| A structural change with behaviour meant to stay the same (rename, extract, inline, dedupe, move) | Pin the contract first: a characterization test, snapshot, or equivalence check over current behaviour is the R-ID; then `/flow-next:work` and review | No new behaviour named; callers to migrate or a shape to collapse | New behaviour named anywhere makes it a feature with cleanup inside; route to capture or work. Skip the pin only when existing coverage already asserts the contract | signal absent |
| A measured slowness or a number the user wants moved once | Baseline on a real surface before any change; the baseline and its target are the R-ID; then `/flow-next:work` and review, with the post-change measurement as the evidence | A metric and a surface the user can name; a trace or a repro | No nameable metric or surface routes to the read-only question row first. A fix motivated by reading source instead of a measurement is not evidence | signal absent |
| One metric to improve against a target through repeated attempts | `/flow-next:work` against a frozen harness; the target is the R-ID and each attempt's comparable measurement is the evidence | A harness that reruns cheaply and a target number | One expected fix is the slowness row. Never relax the target to meet it | signal absent |
| A read-only question ("how does X work", "why was Y built this way", "are we sure about Z") | Answer with citations from the repo, git history, and bug and decision memory; no `.flow/` write, no PR. Dispatch the read-only scouts when the surface is wide; `/flow-next:visual` when the answer is a shape | The deliverable is an answer | When the answer is a prerequisite for a change already asked for, route the change and let its stage read | signal absent |
| A design or behaviour fork whose answer is observable | Settle it per `prototype-before-ask.md`; the observed decision and its evidence are the output, then route the real build to capture or work | A named decision the prototype exists to make; the output is a decision, not shippable code | Skip when the direction is already set. No decision means no prototype | signal absent |
| Tiny, local, low-risk change that fits one implementation context | Direct change plus the repo's review path (`flowctl triage-skip` records a qualifying skip) | One-context fix; low risk | Skip chart and the full spec pipeline. The review and consent gates the change needs still run | signal absent |
| A valid spec with unresolved product or authority questions | `/flow-next:interview` | Spec exists; judgment gaps remain | Reopen discovery as chart only when the answers show the effort itself is not yet specifiable | despite unresolved risk |
| A spec whose design needs an independent assessment | `/flow-next:plan-review <spec-id>` | Consequential design choices; a zero-task spec qualifies | Review the spec directly; task decomposition is not a prerequisite | despite unresolved risk |
| A ready spec with no tasks and no recorded route | `/flow-next:work <spec-id> --no-plan` (the default), or `/flow-next:plan` only on a positive signal from `plan-vs-no-plan.md` | Ready, cohesive; a capable coding agent can own the whole acceptance contract | Plan only on a positive signal; the signals and the exclusions live in `plan-vs-no-plan.md` | signal absent |
| A spec with an intentional plan (tasks that are not the sole implicit owner) | `/flow-next:work <spec-id>` on the planned route | Tasks exist and are actionable | Stay on work plus the configured review, QA, and ship gates (`gate-selection.md`). Chart is too late for understood work | signal absent |
| A spec whose tasks are all done and no PR exists | QA per `gate-selection.md`, then `/flow-next:make-pr <spec-id>` | Build complete; the PR is the next human handover | QA runs or records `skipped(reason)`; make-pr is never skipped on this route | signal absent |
| A spec with an open PR | Converge per `tail.md` (`/flow-next:resolve-pr`, CI fixes, re-review) and stop when merge is the only step left | PR exists | Merge and spec close happen only on explicit instruction or through land | signal absent |
| A repo with a drivable user surface whose navigation should compound across QA and drive runs | `/flow-next:features` | No `.flow/features/` yet, or a present map due a maintain pass | Skip when there is no drivable surface. Never a pipeline stage | signal absent |
| Output too dense - a plan, spec, task, or diff needs reviewing at a glance | `/flow-next:visual` | Structure has to be reconstructed by serial reading | Skip when the text is short enough to judge directly. A lens, never a stage | signal absent |
| A substantial reply, report, or summary needs prose discipline | `/flow-next:prose` | The output is chat prose | Skip for short turns, tool narration, and anything landing in a file, PR, or tracker | signal absent |
| Unsure which of these applies | Classify the fork per `prototype-before-ask.md`; ask at most **one** blocking question only when two routes would materially differ and the answer is not observable | Ambiguous starting state | Otherwise recommend one route outright | - |

**Host command form:** print every copy-pasteable flow-next command in the spelling this host invokes - the flat `/flow-next-<name>` form when the resolved plugin root carries `.flow-next-opencode-manifest` (an OpenCode install), otherwise exactly as spelled here.

## Recommendation shape

Lead with a natural-language next prompt - the exact words or slash command to run next. Flags are secondary. Then:

```
Next: <natural-language prompt or slash command>

Route: <name>
Signal: <positive signal matched>
Skip/narrow: <the safe skip or narrow condition>
Skip kind: signal absent | despite unresolved risk
Why not the alternatives: <one line>
```
