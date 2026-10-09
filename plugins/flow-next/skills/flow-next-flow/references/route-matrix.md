# Route matrix

Route on content and context, never on input kind. A tracker issue, a pasted bug report, console
output, a prototype, a branch, a path, and a sentence of intent all become text first: read what
was given, then match the starting state. The rows are an inventory, not a precedence order: when
more than one could apply, judge from intent, evidence, and current state. Each hop re-evaluates.

A skipped stage is recorded as `skipped(<kind>: <reason>)`, never silently absent. A route skip's kind is
`signal absent` (the stage's work is not needed) or `despite unresolved risk` (a smaller path was
chosen; its contracts still apply later). Implementation review follows the risk rule in
working-rules.md instead.

| Starting state | Route | Positive signal | Safe skip or narrow | Skip kind |
|---|---|---|---|---|
| One meaningful idea whose intent and boundaries can be stated | `flow-next:flow-next-capture`, or author the spec directly | Clear meaningful idea | Skip chart; do not manufacture a chart for clear work. Count specs per `spec-count.md` when the tripwire trips | signal absent |
| Existing structured brief with resolved business and technical choices | `flow-next:flow-next-capture` the brief | Structured brief or chart briefing ready | Skip chart. Skip refine unless a named product or authority decision is open (`plan-vs-no-plan.md`) | signal absent |
| A reported defect (bug report, console dump, failing behaviour) | Check for prior fixes, reproduce reliably and diagnose, bisect from a known-good revision, prove on base and head ([defect-route.md](../../flow-next-work/references/defect-route.md)); the failing test is the R-ID; then `flow-next:flow-next-work` and review | The unknown is the cause, the risk is regression | Refine is the wrong instrument for a defect. Capture only when the diagnosis conversation itself carries decisions worth locking down | signal absent |
| A structural change with behaviour meant to stay the same (rename, extract, inline, dedupe, move) | Pin the contract first: a characterization test, snapshot, or equivalence check over current behaviour is the R-ID; then `flow-next:flow-next-work` and review | No new behaviour named; callers to migrate or a shape to collapse | New behaviour named anywhere makes it a feature with cleanup inside; route to capture or work. Skip the pin only when existing coverage already asserts the contract | signal absent |
| A measured slowness or a number the user wants moved once | Baseline on a real surface before any change (on a running app, read the feature map first: "Live-app stages" in [feature-entry-contract.md](../../flow-next-features/references/feature-entry-contract.md)); the baseline and its target are the R-ID; then `flow-next:flow-next-work` and review, with the post-change measurement as the evidence | A metric and a surface the user can name; a trace or a repro | No nameable metric or surface routes to the read-only question row first. A fix motivated by reading source instead of a measurement is not evidence | signal absent |
| A read-only question ("how does X work", "why was Y built this way", "are we sure about Z") | Answer with citations from the repo, git history, and bug and decision memory; no `.flow/` write, no PR. Dispatch the read-only scouts when the surface is wide: `why-scout` (`agents/why-scout.md`) for why questions, relaying its findings with their confidence tiers as returned; the repo, docs, and practice scouts for how questions; `flow-next:flow-next-visual` when the answer is a shape | The deliverable is an answer | When the answer is a prerequisite for a change already asked for, route the change and let its stage read | signal absent |
| A design or behaviour fork whose answer is observable | Settle it per `prototype-before-ask.md`; the observed decision and its evidence are the output, then route the real build to capture or work | A named decision the prototype exists to make; the output is a decision, not shippable code | Skip when the direction is already set. No decision means no prototype | signal absent |
| Tiny, local, low-risk change that fits one implementation context | Direct change plus the repo's review path (`flowctl triage-skip` records a qualifying skip) | One-context fix; low risk | Skip chart and the full spec pipeline. The review and consent gates the change needs still run | signal absent |
| A valid spec with unresolved product or authority questions, or a person asking to be interviewed on it | `flow-next:flow-next-refine`, with the role or audience the person stated as its lens (`--biz` for product or business, otherwise `--scope=<their words>`) | Spec exists; judgment gaps remain, or the interview was asked for | Skip unless the open decision can be named or the interview was asked for (`plan-vs-no-plan.md`). Reopen discovery as chart only when the answers show the effort itself is not yet specifiable | despite unresolved risk |
| A ready spec with no tasks and no recorded route | `flow-next:flow-next-work <spec-id> --no-plan` (the default), or `flow-next:flow-next-plan` only on a positive signal from `plan-vs-no-plan.md`. **Read first** when the spec names a library or API the repo does not already use: `flow-next:flow-next-refine <spec-id> --scope=research` before work on either route | Ready, cohesive; a capable coding agent can own the whole acceptance contract. Read-first signal: an unfamiliar library or API named in the spec | Plan only on a positive signal; the signals and the exclusions live in `plan-vs-no-plan.md`. The read-first pass is satisfied by a `## Resolved via Research` section or a plan that ran the scouts, so it never runs twice and never by default | signal absent |
| A spec with an intentional plan (tasks that are not the sole implicit owner) | `flow-next:flow-next-work <spec-id>` on the planned route | Tasks exist and are actionable | Stay on work plus the configured review, QA, and ship gates (`gate-selection.md`). Chart is too late for understood work | signal absent |
| A spec whose tasks are all done and no PR exists | QA per `gate-selection.md`, then `flow-next:flow-next-make-pr <spec-id>` | Build complete; the PR is the next human handover | QA runs or records `skipped(reason)`; under `--auto` make-pr is never skipped on this route; attended, make-pr runs when the person asks for the PR | signal absent |
| A spec with an existing PR (including a closed spec) | Apply `tail.md`: attended flow offers landing and obtains current scoped consent; an authorized merge destination invokes `flow-next:flow-next-land`; default unattended flow defers | Open PR still needs landing; a confirmed merge ends the run | Review-only convergence keeps its limited scope. PR existence is not consent; land owns convergence and merge gates | signal absent |
| Unsure which of these applies | Classify the fork per `prototype-before-ask.md`; ask at most **one** blocking question only when two routes would materially differ and the answer is not observable | Ambiguous starting state | Otherwise recommend one route outright | - |

Rarer starting states live in [route-matrix-more.md](route-matrix-more.md); read it when one of
these fits: no written direction (strategy), a search for candidate investments or a theme to
narrow (prospect), one large idea with unclear boundaries (chart), a metric improved over repeated
attempts (hill climb), a spec needing an independent design review (plan-review), a spec whose
open tasks are all blocked, a closed spec with no pull request, a feature map to seed or maintain,
output too dense to read (visual), or chat prose that needs discipline (prose).

**Host command form:** print every copy-pasteable flow-next command in the spelling this host
invokes: the flat `/flow-next-<name>` form when the resolved plugin root carries
`.flow-next-opencode-manifest` (an OpenCode install), otherwise exactly as spelled here.

Adding or removing a skill updates these two files in the same change.
