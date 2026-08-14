---
satisfies: [R1, R3, R4]
---
# fn-195-orchestration-by-intent-named-tiers-per.1 Write the routing contract: tier vocabulary, precedence, reach pages

## Description
Author the contract before deleting anything that contradicts it. Define the four tiers plus the unset default in exactly one place, write one short reach page per supported harness, and state the precedence line at every dispatch site. This task creates the target; later tasks remove what disagrees with it.

**Size:** M/L
**Files:** NEW single tier-vocabulary section (implementer names its home - the usage guide is the natural one, since it is read on demand); NEW one reach page per harness under the docs tree (six: the four first-class hosts, the community port, and a generic fallback); `plugins/flow-next/skills/flow-next-work/phases.md` and `agents/worker.md` (dispatch-site precedence line); `plugins/flow-next/skills/flow-next-plan/steps.md` (scout fan-out dispatch sites); `plugins/flow-next/docs/orchestration.md` (becomes the tier-guidance page)
**Touches:** [plugins/flow-next/docs/orchestration.md, plugins/flow-next/docs/glossary.md, plugins/flow-next/skills/flow-next-work/phases.md, plugins/flow-next/skills/flow-next-plan/steps.md, plugins/flow-next/agents/worker.md]

### Approach
- Tier names are exactly the four in the spec plus unset. They are a user-facing interface: choose the wording once, and do not invent synonyms in different files (the dictionary already bans synonym drift - add these terms to it).
- A reach page states, for that harness: which reach mechanisms exist (in-session, in-host subagent, shell out to another CLI), which do not, what the degradation is when one is missing, and the discover-then-invoke habit where the harness can list what it offers. Keep each page short - this is a reference, not a tutorial.
- The precedence line is one sentence at each dispatch site: explicit argument, then the project routing block, then the agent default, then the session model. Same wording everywhere; do not paraphrase per file.
- The worked example in the spec is a consumer's own phrasing - reuse it verbatim as the example rather than authoring a new one.
- Do NOT write concrete model identifiers anywhere in this task's output. Tier guidance describes kinds of work.
- Mirror regeneration is deferred to the final task; this one may leave the mirror stale.

### Investigation targets
**Required** (read before writing):
- `plugins/flow-next/docs/orchestration.md` - what the current routing story claims, so the replacement is a rewrite rather than an addition
- `plugins/flow-next/docs/platforms.md` - the existing per-host knowledge that reach pages inherit (including which host cannot select a subagent model)
- `plugins/flow-next/docs/glossary.md` and the repo dictionary - where the four terms get their canonical definitions

### Key context
- The mechanism already works in the field; this is documentation of behavior, not a design experiment. Nothing here needs a spike.

### Acceptance
- [ ] Four tier names plus unset defined in exactly one place, in user-facing English, added to the project dictionary
- [ ] One short reach page per supported harness: mechanisms, absences, degradation, discover-then-invoke
- [ ] Identical precedence sentence at every dispatch site that routes work
- [ ] Zero concrete model identifiers introduced by this task
- [ ] Focused suites green for the files touched

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
